"""Finite generated edits reuse immutable submissions, drafts and publication."""
from dataclasses import asdict, replace
from uuid import NAMESPACE_URL, uuid5

from app.core.errors import ConflictError, IdempotencyConflictError, ValidationAppError, VersionConflictError
from app.core.ids import content_hash
from app.domain.domain_packs.validation import seed_digest, validate_seed
from app.domain.generated_plan_changes import added_topic_route, compose_generated_draft
from app.domain.planning.intent import goal_spec_payload
from app.domain.planning.models import revision_from_draft
from app.infrastructure.db.learning_exposures import _json
from app.infrastructure.db.plan_changes import PgPlanChanges
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.resource_changes import capture_resource_snapshots


class PgGeneratedPlanChanges(PgPlanChanges):
    @staticmethod
    def _input_hash(command):
        payload = asdict(command)
        # Empty optional topics did not exist in prior durable submissions.
        if not payload['topic_keys']:
            payload.pop('topic_keys')
        return content_hash(payload)

    @staticmethod
    def _run_id(scope, command):
        return 'run_' + uuid5(NAMESPACE_URL, content_hash([scope.actor_id, command.project_id,
                                                         command.idempotency_key])).hex

    def existing_submission(self, scope, command):
        run_id = self._run_id(scope, command)
        with self._connection(scope, command.project_id) as conn:
            row = conn.execute('''SELECT e.detail FROM ai_runs r JOIN ai_run_events e USING(run_id)
                WHERE r.project_id=%s AND r.actor_id=%s AND r.run_id=%s AND e.status='submission'
                AND e.detail->>'kind'='planning_submission' ''', (command.project_id, scope.actor_id, run_id)).fetchone()
            if row is None:
                return None
            meta = row['detail'].get('initial', {}).get('route_change', {})
            if meta.get('input_hash') != self._input_hash(command):
                raise IdempotencyConflictError()
            return run_id

    @staticmethod
    def _published_pack(conn, key, version):
        row = conn.execute("SELECT published_payload,content_digest FROM domain_packs "
                           "WHERE pack_key=%s AND version=%s AND status='published'", (key, version)).fetchone()
        if not row:
            raise ConflictError('路线变更需要可用的受控课程版本')
        try:
            pack = validate_seed(row['published_payload'])
            if seed_digest(pack) != row['content_digest']:
                raise ValueError('digest mismatch')
        except ValueError as exc:
            raise ConflictError('受控课程版本校验失败') from exc
        return pack

    def prepare(self, scope, command, select_pack):
        with self._connection(scope, command.project_id, write=True) as conn:
            current = PgPlanRepository(self.dsn, connection=conn).get_current(project_id=command.project_id)
            if current is None or current.plan_id != command.plan_id or current.version != command.expected_version:
                raise VersionConflictError('当前路线已变化，请刷新后重新发起变更')
            basis, boundary, _, _, _, _ = self._basis(conn, current)
            before = [s.stable_key for s in sorted(current.stages, key=lambda s: s.order_index)]
            additions = {}
            if command.operation == 'change_goal':
                goal, spec = command.goal, command.goal_spec
                if goal == current.goal_snapshot and spec == current.goal_spec:
                    raise ValidationAppError('目标与上下文没有变化；如需更新内容，请明确重新生成未来路线')
                selected = select_pack(spec.target if spec else goal) if select_pack else None
                if not selected or not selected.get('stage_blueprints') or selected.get('resource_support') == 'search_only':
                    raise ConflictError('当前公共模板不足，不能把未知目标作为正式全路线变更')
                pack = self._published_pack(conn, selected['pack_key'], selected['version'])
                retained = []
                after = [s['stable_key'] for s in pack['stage_blueprints']]
            else:
                goal, spec = current.goal_snapshot, current.goal_spec
                pack = self._published_pack(conn, current.source_pack_key, current.source_pack_version)
                available = {s['stable_key'] for s in pack['stage_blueprints']}
                if not set(before) <= available:
                    raise ConflictError('当前路线不能映射到受控课程')
                if command.operation == 'add_topic':
                    additions = added_topic_route(pack, before, command.topic_keys, boundary)
                    retained, after = before, list(additions['after_stage_keys'])
                elif boundary >= len(before) - 1:
                    raise ConflictError('当前路线没有可以重新生成的受控未来阶段')
                else:
                    retained, after = before[:boundary + 1], before
            # Only exact keys and immutable IDs are frozen. No Summary/Prompt/Outcome/private body leaves PG.
            rows = conn.execute('''SELECT DISTINCT n.stable_key,n.node_id,n.content_version FROM plan_unit_links p
                JOIN plan_stages s USING(project_id,plan_id,stage_id)
                JOIN unit_node_links u USING(project_id,unit_id) JOIN knowledge_nodes n USING(project_id,node_id)
                WHERE p.project_id=%s AND p.plan_id=%s AND s.stable_key=ANY(%s)''',
                (command.project_id, current.plan_id, retained)).fetchall()
            reuse = {}
            known = {n['stable_key'] for n in pack.get('knowledge_blueprints', [])}
            for row in rows:
                key = row['stable_key']
                if key not in known or (key in reuse and reuse[key]['node_id'] != row['node_id']):
                    raise ConflictError('保留阶段的知识身份无法精确映射到受控课程')
                reuse[key] = dict(node_id=row['node_id'], content_version=row['content_version'])
            metadata = dict(actor_id=scope.actor_id, project_id=command.project_id,
                    base_plan_id=current.plan_id, base_revision=current.revision,
                    base_version=current.version, basis_hash=basis, input_hash=self._input_hash(command),
                    operation=command.operation, before_stage_keys=before, after_stage_keys=after,
                    retained_stage_keys=retained, node_reuse=reuse,
                    protected_through=boundary,
                    before_goal=current.goal_snapshot, before_stages=[_json(asdict(s)) for s in current.stages],
                    source_pack_key=pack['pack_key'], source_pack_version=pack['version'], pack_hash=seed_digest(pack))
            if additions:
                metadata.update(topic_keys=list(command.topic_keys), added_node_keys=list(additions['added_node_keys']),
                                added_stage_keys=list(additions['added_stage_keys']),
                                topic_titles={node['stable_key']: node['title'] for node in pack['knowledge_blueprints']
                                              if node['stable_key'] in additions['added_node_keys']})
            return dict(run_id=self._run_id(scope, command), goal=goal, goal_spec=goal_spec_payload(spec),
                        pack=pack, metadata=metadata)

    def _current(self, conn, scope, metadata):
        if metadata.get('actor_id') != scope.actor_id:
            raise ConflictError('冻结的路线变更不属于当前身份')
        scope.require_project(metadata['project_id'])
        current = PgPlanRepository(self.dsn, connection=conn).get_current(project_id=metadata['project_id'])
        if (current is None or current.plan_id != metadata['base_plan_id']
                or current.version != metadata['base_version']):
            raise VersionConflictError('当前路线已变化，请重新预览')
        if self._basis(conn, current)[0] != metadata['basis_hash']:
            raise VersionConflictError('学习记录、知识关系或私人资料已变化，请重新发起变更')
        pack = self._published_pack(conn, metadata['source_pack_key'], metadata['source_pack_version'])
        if seed_digest(pack) != metadata['pack_hash']:
            raise ConflictError('冻结课程版本已变化')
        return current

    def validate_generation(self, scope, metadata):
        project = metadata['project_id']
        with self._connection(scope, project, write=True) as conn:
            self._current(conn, scope, metadata)

    def save_generated(self, scope, metadata, draft, write_fence=None):
        if metadata.get('project_id') != draft.project_id:
            raise ConflictError('草案与冻结的变更不属于同一项目')
        with self._connection(scope, draft.project_id, write=True) as conn:
            current = self._current(conn, scope, metadata)
            repo = PgPlanRepository(self.dsn, connection=conn, route_change_id=draft.draft_id)
            old = repo.get_draft(project_id=draft.project_id, draft_id=draft.draft_id)
            if old:
                if old.run_id != draft.run_id or old.route_change != metadata:
                    raise ConflictError('已保存草案与冻结路线变更不一致')
                repo.save_draft(old, expected_hash=old.content_hash, expected_version=metadata['base_version'],
                                write_fence=write_fence)
                return old
            composed = compose_generated_draft(current, draft, metadata)
            frozen = {s['assignment_id'] for s in composed.resource_snapshots}
            missing = [a for a in composed.stage_resources if a.assignment_id not in frozen]
            composed = replace(composed, resource_snapshots=composed.resource_snapshots
                    + capture_resource_snapshots(conn, missing, composed.stages),
                    validation_warnings=(*composed.validation_warnings,
                        '确认后创建新路线版本；旧路线和学习、总结、Prompt、成果、证据历史保留，新版学习进度重新记录。',
                        '本次使用现有有界完整课程生成，保留阶段的生成候选会丢弃，不继承旧完成状态。',
                        *(['追加主题按受控阶段组织，依赖与同阶段教材会一起补入；顺序变化后的学习基线请重新核对。']
                          if metadata['operation'] == 'add_topic' else [])))
            revision_from_draft(composed, revision=composed.revision_candidate)
            repo.save_draft(composed, expected_version=metadata['base_version'], write_fence=write_fence)
            return self._loaded(repo, draft.project_id, draft.draft_id, scope.actor_id)
