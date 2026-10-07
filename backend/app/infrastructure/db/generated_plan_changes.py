"""Finite generated edits reuse immutable submissions, drafts and publication."""
from dataclasses import asdict, replace
from uuid import NAMESPACE_URL, uuid5

from app.core.errors import ConflictError, DependencyUnavailableError, IdempotencyConflictError, ValidationAppError, VersionConflictError
from app.core.ids import content_hash
from app.domain.domain_packs.validation import seed_digest, validate_seed
from app.domain.generated_plan_changes import compose_generated_draft
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

    def prepare(self, scope, command):
        """Generated route changes are unavailable until new planning is implemented."""
        scope.require_project(command.project_id)
        raise DependencyUnavailableError("学习计划生成正在升级，当前暂不可创建新路线。")

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
