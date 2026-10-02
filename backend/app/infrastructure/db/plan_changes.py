"""Manual finite changes in the existing draft/publication transaction, no new tables."""
from dataclasses import asdict, replace
from uuid import NAMESPACE_URL, uuid5

from app.core.errors import (
    ConflictError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
    VersionConflictError,
)
from app.core.ids import content_hash
from app.domain.domain_packs.validation import seed_digest, validate_seed
from app.domain.plan_changes import changed_draft
from app.domain.planning.intent import goal_spec_payload, required_module_closure
from app.domain.planning.models import PlanPublicationService, revision_from_draft
from app.infrastructure.db.learning_exposures import _json
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.practice_changes import PgPracticeChanges
from app.infrastructure.db.resource_changes import (
    PgResourceChanges,
    capture_resource_snapshots,
    copy_private_selections,
    private_bindings_digest,
)
from psycopg.types.json import Jsonb


class PgPlanChanges(PgResourceChanges):
    @staticmethod
    def _policy(conn, current):
        if not current.source_pack_key:
            return {}, (), '', ()
        row = conn.execute('SELECT published_payload,content_digest FROM domain_packs WHERE pack_key=%s AND version=%s AND status=\'published\'',
                           (current.source_pack_key, current.source_pack_version)).fetchone()
        if not row:
            raise ConflictError('当前路线的受控课程版本不可用')
        try:
            pack = validate_seed(row['published_payload'])
            if seed_digest(pack) != row['content_digest']:
                raise ValueError('digest mismatch')
        except ValueError as exc:
            raise ConflictError('当前路线的受控课程版本校验失败') from exc
        inclusion = {s['stable_key']: s.get('inclusion', 'required') for s in pack['stage_blueprints']}
        required = required_module_closure(pack.get('knowledge_blueprints', []), pack.get('required_node_keys', []))
        edges = tuple((dep, n['stable_key']) for n in pack.get('knowledge_blueprints', [])
                      for dep in n.get('prerequisite_keys', []))
        return inclusion, required, row['content_digest'], edges

    def _basis(self, conn, current):
        args = (current.project_id, current.plan_id)
        exposures = conn.execute('SELECT exposure_id,stage_id,status,version FROM learning_exposures WHERE project_id=%s AND plan_id=%s ORDER BY exposure_id', args).fetchall()
        summaries = conn.execute('SELECT attempt_id,stage_id,version FROM summary_attempts WHERE project_id=%s AND plan_id=%s ORDER BY attempt_id', args).fetchall()
        prompts = conn.execute('SELECT revision_id,stage_id,version FROM prompt_revisions WHERE project_id=%s AND plan_id=%s ORDER BY revision_id', args).fetchall()
        submissions = conn.execute('SELECT submission_id,stage_id,version FROM practice_submissions WHERE project_id=%s AND plan_id=%s ORDER BY submission_id', args).fetchall()
        active = {r['stage_id'] for r in [*exposures, *summaries, *prompts, *submissions]}
        boundary = max((s.order_index for s in current.stages if s.stage_id in active), default=-1)
        nodes = conn.execute('''SELECT s.stable_key AS stage_key,n.node_id,n.stable_key,n.content_version FROM plan_unit_links p
            JOIN plan_stages s ON s.project_id=p.project_id AND s.plan_id=p.plan_id AND s.stage_id=p.stage_id
            JOIN unit_node_links u ON u.project_id=p.project_id AND u.unit_id=p.unit_id
            JOIN knowledge_nodes n ON n.project_id=u.project_id AND n.node_id=u.node_id
            WHERE p.project_id=%s AND p.plan_id=%s ORDER BY s.order_index,n.stable_key,n.node_id''', args).fetchall()
        relations = conn.execute('''SELECT f.stable_key AS predecessor,t.stable_key AS dependent FROM knowledge_relations r
            JOIN knowledge_nodes f ON f.project_id=r.project_id AND f.node_id=r.from_node_id
            JOIN knowledge_nodes t ON t.project_id=r.project_id AND t.node_id=r.to_node_id
            WHERE r.project_id=%s AND r.relation_type='prerequisite' AND r.to_node_id=ANY(%s)
            ORDER BY f.stable_key,t.stable_key''', (current.project_id, list({n['node_id'] for n in nodes}))).fetchall()
        inclusion, required, seed, seed_edges = self._policy(conn, current)
        by_stage = {}
        for n in nodes:
            by_stage.setdefault(n['stage_key'], set()).add(n['stable_key'])
        context = PgPracticeChanges._context_for_plan(conn, current, lock=True)
        digest = content_hash(_json(dict(structure=current.structure_fingerprint(), exposures=exposures,
                              summaries=summaries, prompts=prompts, submissions=submissions, nodes=nodes,
                              relations=relations, seed=seed, tasks=context,
                              private=private_bindings_digest(conn, current.project_id, current.plan_id))))
        edges = tuple(sorted(set(seed_edges) | {(r['predecessor'], r['dependent']) for r in relations}))
        return digest, boundary, inclusion, by_stage, edges, required

    def context(self, scope, project_id):
        with self._connection(scope, project_id, write=True) as conn:
            current = PgPlanRepository(self.dsn, connection=conn).get_current(project_id=project_id)
            if current is None:
                raise NotFoundError('尚无批准路线')
            _, boundary, inclusion, _, _, _ = self._basis(conn, current)
            last = max(s.order_index for s in current.stages)
            available = False
            maximum = 0
            if current.source_pack_key:
                pack_row = conn.execute('SELECT published_payload FROM domain_packs WHERE pack_key=%s AND version=%s',
                                        (current.source_pack_key, current.source_pack_version)).fetchone()
                if pack_row:
                    specs = pack_row['published_payload'].get('stage_blueprints', [])
                    maximum = 1 + 2 * len(specs) + 2
                    available = boundary < last and all(s.stable_key in {b['stable_key'] for b in specs} for s in current.stages)
            return dict(plan_id=current.plan_id, revision=current.version, goal=current.goal_snapshot,
                        goal_spec=goal_spec_payload(current.goal_spec), regenerate_available=available,
                        generation_max_requests=maximum,
                        stages=[dict(stage_id=s.stage_id, stable_key=s.stable_key, title=s.title,
                                     order_index=s.order_index, locked=s.order_index <= boundary or s.order_index == last,
                                     inclusion=inclusion.get(s.stable_key, 'required'))
                                for s in sorted(current.stages, key=lambda s: s.order_index)])

    @staticmethod
    def _loaded(repo, project, proposal, actor):
        draft = repo.get_draft(project_id=project, draft_id=proposal)
        if draft is None or not draft.route_change or draft.route_change.get('actor_id') != actor:
            raise NotFoundError('路线变更预览不存在')
        return draft

    @staticmethod
    def _view(draft):
        meta = draft.route_change
        return dict(proposal_id=draft.draft_id, status=str(draft.status), draft=draft,
                    base_plan_id=meta['base_plan_id'], base_revision=meta['base_revision'], operation=meta['operation'],
                    before_stage_keys=meta['before_stage_keys'], after_stage_keys=meta['after_stage_keys'],
                    warnings=list(draft.validation_warnings), preview_hash=draft.content_hash,
                    retained_stage_keys=meta.get('retained_stage_keys', []),
                    before_goal=meta.get('before_goal', draft.goal_snapshot), after_goal=draft.goal_snapshot,
                    before_stages=meta.get('before_stages', []))

    def get(self, scope, project_id, proposal_id):
        with self._connection(scope, project_id) as conn:
            repo = PgPlanRepository(self.dsn, connection=conn)
            return self._view(self._loaded(repo, project_id, proposal_id, scope.actor_id))

    def preview(self, scope, command):
        fingerprint = content_hash(asdict(command))
        proposal = 'rch_' + uuid5(NAMESPACE_URL, content_hash([scope.actor_id, command.project_id, command.idempotency_key])).hex
        with self._connection(scope, command.project_id, write=True) as conn:
            repo = PgPlanRepository(self.dsn, connection=conn, route_change_id=proposal)
            old = repo.get_draft(project_id=command.project_id, draft_id=proposal)
            if old:
                if not old.route_change or old.route_change['input_hash'] != fingerprint:
                    raise IdempotencyConflictError()
                return self._view(old)
            current = repo.get_current(project_id=command.project_id)
            if current is None or current.plan_id != command.plan_id or current.version != command.expected_version:
                raise VersionConflictError('当前路线已变化，请刷新后重新预览')
            basis, boundary, inclusion, nodes, relations, required = self._basis(conn, current)
            draft = changed_draft(current, command, draft_id=proposal, protected_through=boundary,
                                  inclusion=inclusion, nodes_by_stage=nodes, prerequisites=relations, required_nodes=required)
            missing = [a for a in draft.stage_resources if a.assignment_id not in {s['assignment_id'] for s in draft.resource_snapshots}]
            draft = replace(draft, resource_snapshots=draft.resource_snapshots + capture_resource_snapshots(conn, missing, draft.stages))
            # Preview and publication use the same full structural validator.
            revision_from_draft(draft, revision=draft.revision_candidate)
            warnings = ('确认后创建新的路线版本；旧路线、进度、总结与成果留在历史中，新版本学习位置重新记录。',
                        '沿用保留阶段的私人资料快照并记录来源；被移除阶段的私人资料留在旧版本。',
                        '顺序受前置依赖约束；已开始阶段及之前阶段、最终综合实践保持位置约束。')
            draft = replace(draft, validation_warnings=warnings, route_change=dict(actor_id=scope.actor_id,
                            base_plan_id=current.plan_id, base_revision=current.revision, base_version=current.version,
                            basis_hash=basis, input_hash=fingerprint, operation=command.operation,
                            before_stage_keys=[s.stable_key for s in sorted(current.stages, key=lambda s: s.order_index)],
                            after_stage_keys=[s.stable_key for s in draft.stages]))
            repo.save_draft(draft, expected_version=current.version)
            return self._view(self._loaded(repo, command.project_id, proposal, scope.actor_id))

    def decide(self, scope, project_id, proposal_id, action, expected_version, preview_hash,
               idempotency_key, acknowledge_reset=False):
        fingerprint = content_hash(dict(action=action, expected_version=expected_version,
                                        preview_hash=preview_hash, acknowledge_reset=acknowledge_reset))
        receipt_key = content_hash(idempotency_key)
        with self._connection(scope, project_id, write=True) as conn:
            repo = PgPlanRepository(self.dsn, connection=conn, route_change_id=proposal_id)
            draft = self._loaded(repo, project_id, proposal_id, scope.actor_id)
            payload = conn.execute('SELECT payload FROM plan_drafts WHERE project_id=%s AND draft_id=%s FOR UPDATE',
                                   (project_id, proposal_id)).fetchone()['payload']
            receipt = (payload.get('route_change_receipts') or {}).get(receipt_key)
            if receipt:
                if receipt['input_hash'] != fingerprint:
                    raise IdempotencyConflictError()
                return dict(preview=self._view(draft), **receipt['result'])
            if str(draft.status) != 'awaiting_approval':
                raise ConflictError('此预览已经确认或取消')
            if preview_hash != draft.content_hash or expected_version != draft.route_change['base_version']:
                raise VersionConflictError('预览内容或版本已变化')
            result = dict(plan_id=None, revision=None, created=False)
            if action == 'cancel':
                repo.cancel_draft(project_id=project_id, draft_id=proposal_id, expected_hash=preview_hash)
            else:
                if not acknowledge_reset:
                    raise ValidationAppError('请明确确认新版本进度重新记录及旧历史保留')
                current = repo.get_current(project_id=project_id)
                if current is None or current.plan_id != draft.route_change['base_plan_id'] or current.version != expected_version:
                    raise VersionConflictError('当前路线已变化，请重新预览')
                if self._basis(conn, current)[0] != draft.route_change['basis_hash']:
                    raise VersionConflictError('学习记录、知识关系或私人资料已变化，请重新预览')
                published = PlanPublicationService(repo).publish(draft=draft, presented_hash=preview_hash,
                             expected_version=expected_version, idempotency_key='route-change:' + proposal_id + ':' + receipt_key)
                if published.created and draft.route_change['operation'] != 'change_goal':
                    copy_private_selections(conn, current, published.plan_id, 'copy_active')
                result = dict(plan_id=published.plan_id, revision=published.revision, created=published.created)
            conn.execute('UPDATE plan_drafts SET payload=jsonb_set(payload,\'{route_change_receipts}\',%s) WHERE project_id=%s AND draft_id=%s',
                         (Jsonb({receipt_key: dict(input_hash=fingerprint, result=result)}), project_id, proposal_id))
            return dict(preview=self._view(self._loaded(repo, project_id, proposal_id, scope.actor_id)), **result)
