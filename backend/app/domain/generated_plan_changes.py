"""Pure finite composition of controlled generated routes and protected history."""

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

from app.core.errors import ValidationAppError
from app.domain.planning.intent import GoalSpec
from app.domain.planning.models import PlanDraft


@dataclass(frozen=True)
class GeneratedPlanChangeCommand:
    project_id: str
    plan_id: str
    expected_version: int
    idempotency_key: str
    operation: str
    goal: str = ''
    goal_spec: GoalSpec | None = None

    def __post_init__(self):
        if self.operation not in {'change_goal', 'regenerate_future_plan'}:
            raise ValidationAppError('不支持的生成路线变更')
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise ValidationAppError('路线变更需要明确版本')
        for value in (self.project_id, self.plan_id, self.idempotency_key):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValidationAppError('路线变更标识必须为1–200字符')
        if not isinstance(self.goal, str) or len(self.goal) > 2000:
            raise ValidationAppError('目标必须为1–2000字符')
        if self.goal_spec is not None and not isinstance(self.goal_spec, GoalSpec):
            raise ValidationAppError('目标上下文结构不合法')
        if self.operation == 'change_goal':
            if not self.goal.strip():
                raise ValidationAppError('变更目标必须提供目标')
        elif self.goal or self.goal_spec is not None:
            raise ValidationAppError('重生成后续路线不能变更目标')
        object.__setattr__(self, 'goal', self.goal.strip())


def _keys(value, *, allow_empty=False):
    if not isinstance(value, (tuple, list)) or len(value) > 100 or (not value and not allow_empty):
        raise ValidationAppError('路线阶段为空或超出调整范围')
    if any(not isinstance(key, str) or not key.strip() or len(key) > 200 for key in value):
        raise ValidationAppError('阶段键必须为1–200字符')
    if len(set(value)) != len(value):
        raise ValidationAppError('路线阶段键不可重复')
    return tuple(value)


def _ordered_stages(plan):
    stages = tuple(sorted(plan.stages, key=lambda stage: stage.order_index))
    _keys(tuple(stage.stable_key for stage in stages))
    if tuple(stage.order_index for stage in stages) != tuple(range(len(stages))):
        raise ValidationAppError('阶段顺序索引必须从0开始连续递增')
    if len({stage.stage_id for stage in stages}) != len(stages):
        raise ValidationAppError('阶段标识不可重复')
    return stages


def _selected_links(plan, stage_ids) -> dict[str, Any]:
    """Select by exact identifiers; never infer relationships from titles."""
    tasks = tuple(link for link in plan.task_links if link.stage_id in stage_ids)
    task_ids = {link.task_id for link in tasks}
    assignments = tuple(item for item in plan.stage_resources if item.stage_id in stage_ids)
    assignment_ids = {item.assignment_id for item in assignments}
    return {
        'unit_links': tuple(link for link in plan.unit_links if link.stage_id in stage_ids),
        'task_links': tasks,
        'task_knowledge_links': tuple(link for link in plan.task_knowledge_links if link.task_id in task_ids),
        'stage_resources': assignments,
        'extensions': tuple(item for item in plan.extensions if item.stage_id in stage_ids),
        'resource_snapshots': tuple(deepcopy(snapshot) for snapshot in plan.resource_snapshots
                                    if snapshot.get('assignment_id') in assignment_ids),
    }


def compose_generated_draft(current, generated: PlanDraft, metadata: dict) -> PlanDraft:
    """Compose frozen server route decisions without changing either input.

    Regeneration keeps the current ordered route and its protected prefix exactly.
    A full controlled pack can contain optional stages absent from that route; they
    are filtered out together with their links and resource snapshots. Identifier
    remapping for retained canonical knowledge belongs to server materialization.
    """
    if not isinstance(metadata, dict):
        raise ValidationAppError('路线变更元数据不合法')
    operation = metadata.get('operation')
    if operation not in {'change_goal', 'regenerate_future_plan'}:
        raise ValidationAppError('不支持的生成路线变更')
    original = _ordered_stages(current)
    fresh = _ordered_stages(generated)
    before = _keys(metadata.get('before_stage_keys'))
    after = _keys(metadata.get('after_stage_keys'))
    retained = _keys(metadata.get('retained_stage_keys'), allow_empty=True)
    if before != tuple(stage.stable_key for stage in original):
        raise ValidationAppError('当前路线与冻结的变更元数据不一致')
    if generated.project_id != current.project_id:
        raise ValidationAppError('生成草案不属于当前项目')
    if operation == 'change_goal':
        if retained or after != tuple(stage.stable_key for stage in fresh):
            raise ValidationAppError('目标变更必须完整使用新受控路线')
        links = _selected_links(generated, {stage.stage_id for stage in fresh})
        return replace(generated, stages=fresh, **links, route_change=deepcopy(metadata))

    if after != before:
        raise ValidationAppError('重生成后续路线必须保留当前阶段顺序')
    if retained != before[:len(retained)] or len(retained) == len(before):
        raise ValidationAppError('保留阶段必须是当前路线前缀且必须存在后续阶段')
    for field in ('source_pack_key', 'source_pack_version', 'goal_snapshot', 'goal_spec'):
        if getattr(generated, field) != getattr(current, field):
            raise ValidationAppError('后续路线生成的课程来源或目标与当前计划不一致')
    for field in ('source_pack_key', 'source_pack_version'):
        if field in metadata and metadata[field] != getattr(current, field):
            raise ValidationAppError('冻结的课程来源与当前计划不一致')
    fresh_by_key = {stage.stable_key: stage for stage in fresh}
    if set(after) - set(fresh_by_key):
        raise ValidationAppError('生成草案缺少当前路线阶段')
    prefix = original[:len(retained)]
    future = tuple(replace(fresh_by_key[key], order_index=index)
                   for index, key in enumerate(after) if index >= len(prefix))
    stages = (*prefix, *future)
    if len({stage.stage_id for stage in stages}) != len(stages):
        raise ValidationAppError('保留阶段与生成阶段标识重复')
    old_links = _selected_links(current, {stage.stage_id for stage in prefix})
    new_links = _selected_links(generated, {stage.stage_id for stage in future})
    composed_links: dict[str, Any] = {field: (*old_links[field], *new_links[field]) for field in old_links}
    # Generated stable references describe the full pack, while materialized links
    # now describe the selected route. They cannot be safely mapped by title.
    return replace(generated, stages=stages, **composed_links, unit_refs=(), task_refs=(),
                   node_stable_keys=(), route_change=deepcopy(metadata))
