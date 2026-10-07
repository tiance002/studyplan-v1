"""HOLD_FOR_V2: retained composition/closure is mixed with content validation and published revision history; not a specification for V2 replanning.

Pure finite composition of controlled generated routes and protected history.
"""

from copy import deepcopy
from dataclasses import dataclass, replace
from graphlib import CycleError, TopologicalSorter
from typing import Any

from app.core.errors import ValidationAppError
from app.domain.planning.intent import GoalSpec, required_module_closure
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
    topic_keys: tuple[str, ...] = ()

    def __post_init__(self):
        if self.operation not in {'change_goal', 'regenerate_future_plan', 'add_topic'}:
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
        topics = _keys(self.topic_keys, allow_empty=self.operation != 'add_topic')
        if len(topics) > 20 or (self.operation != 'add_topic' and topics):
            raise ValidationAppError('新增主题最多20项且仅适用于新增主题操作')
        object.__setattr__(self, 'topic_keys', topics)


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


def added_topic_route(pack, current_stage_keys, topic_keys, protected_through):
    """Expand explicit Seed knowledge dependencies and insert controlled stages."""
    before = _keys(current_stage_keys)
    topics = _keys(topic_keys)
    if len(topics) > 20 or type(protected_through) is not int or not -1 <= protected_through < len(before):
        raise ValidationAppError('新增主题或保护边界超出范围')
    blueprints = pack.get('knowledge_blueprints', ())
    stages = pack.get('stage_blueprints', ())
    stage_keys = _keys(tuple(stage['stable_key'] for stage in stages))
    stage_nodes = {stage['stable_key']: tuple(stage.get('node_keys') or ()) for stage in stages}
    if set(before) - set(stage_keys):
        raise ValidationAppError('当前路线包含未知受控阶段')
    nodes = {node['stable_key']: node for node in blueprints}
    exposed = {key for stage in before for key in stage_nodes[stage]}
    if any(key in exposed for key in topics):
        raise ValidationAppError('主题已在当前路线中')
    closure = required_module_closure(blueprints, topics)

    def owner(key):
        existing = [stage for stage in before if key in stage_nodes[stage]]
        if existing:
            return existing[0]
        candidates = [stage for stage in stage_keys if key in stage_nodes[stage]]
        declared = nodes[key].get('section_key')
        if declared:
            if declared not in candidates:
                raise ValidationAppError('知识声明归属与阶段曝光不一致')
            return declared
        if len(candidates) != 1:
            raise ValidationAppError('新增知识缺少明确受控阶段归属')
        return candidates[0]

    additions = {owner(key) for key in closure} - set(before)
    if not additions:
        raise ValidationAppError('新增主题没有产生新阶段')
    selected = set(before) | additions
    # Insertion is stage-granular: companion knowledge exposed by an added stage
    # brings its own parent/prerequisite requirements. Expand until every selected
    # stage's knowledge is covered, bounded by the controlled pack limits.
    while True:
        if len(selected) > 100:
            raise ValidationAppError('新增路线最多100个阶段')
        roots = tuple(key for stage in stage_keys if stage in selected for key in stage_nodes[stage])
        closure = required_module_closure(blueprints, roots)
        expanded = selected | {owner(key) for key in closure}
        if expanded == selected:
            break
        selected = expanded
    additions = selected - set(before)
    predecessors = {stage: set() for stage in selected}
    for stage in selected:
        for key in stage_nodes[stage]:
            if key not in nodes:
                raise ValidationAppError('阶段引用未知知识')
            node = nodes[key]
            dependencies = (*(node.get('prerequisite_keys') or ()),
                            *((node['parent_key'],) if node.get('parent_key') else ()))
            for dependency in dependencies:
                if dependency not in nodes:
                    raise ValidationAppError('知识依赖引用未知模块')
                dependency_stage = owner(dependency)
                if dependency_stage not in selected:
                    raise ValidationAppError('新增路线缺少知识前置阶段')
                if dependency_stage != stage:
                    predecessors[stage].add(dependency_stage)
    # Preserve existing relative order, the entire started prefix, and final capstone.
    for previous, stage in zip(before, before[1:], strict=False):
        predecessors[stage].add(previous)
    for stage in selected - set(before[:protected_through + 1]):
        predecessors[stage].update(before[:protected_through + 1])
    for stage in selected - {before[-1]}:
        predecessors[before[-1]].add(stage)
    sorter = TopologicalSorter(predecessors)
    try:
        sorter.prepare()
        after = []
        while sorter.is_active():
            ready = sorted(sorter.get_ready(), key=stage_keys.index)
            after.extend(ready)
            sorter.done(*ready)
    except CycleError as exc:
        raise ValidationAppError('新增主题依赖无法保留已开始阶段或当前路线顺序') from exc
    return {'after_stage_keys': tuple(after),
            'added_node_keys': tuple(key for key in closure if key not in exposed),
            'added_stage_keys': tuple(stage for stage in after if stage in additions),
            'retained_stage_keys': before}


def _invalidate_guidance(stage):
    guide = stage.learning_guidance
    if guide is None:
        return stage
    guide = replace(guide, why_now='路线调整后，按本阶段当前目标与已核对的前置依赖安排学习',
        previous_relation='路线顺序已调整；请重新核对前次教程关系与当前项目基线',
        exposure_relation='unknown', comparison_focus=(), source_slice=None,
        reading_prerequisites=(), practice_prerequisites=(),
        practice_delta=replace(guide.practice_delta,
            baseline='沿用自己的当前项目；调整后请重新核对本阶段任务的输入基线',
            preserved=('保留已有功能，并按当前任务核对兼容性',),
            reuse=('调整后的后续使用关系需要重新核对',)))
    return replace(stage, learning_guidance=guide)


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
    if operation not in {'change_goal', 'regenerate_future_plan', 'add_topic'}:
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
        links: dict[str, Any] = _selected_links(generated, {stage.stage_id for stage in fresh})
        return replace(generated, stages=fresh, **links, route_change=deepcopy(metadata))

    if operation == 'regenerate_future_plan' and after != before:
        raise ValidationAppError('重生成后续路线必须保留当前阶段顺序')
    if operation == 'regenerate_future_plan' and (
            retained != before[:len(retained)] or len(retained) == len(before)):
        raise ValidationAppError('保留阶段必须是当前路线前缀且必须存在后续阶段')
    for field in ('source_pack_key', 'source_pack_version', 'goal_snapshot', 'goal_spec'):
        if getattr(generated, field) != getattr(current, field):
            raise ValidationAppError('后续路线生成的课程来源或目标与当前计划不一致')
    for field in ('source_pack_key', 'source_pack_version'):
        if field in metadata and metadata[field] != getattr(current, field):
            raise ValidationAppError('冻结的课程来源与当前计划不一致')
    fresh_by_key = {stage.stable_key: stage for stage in fresh}
    if operation == 'add_topic':
        added = _keys(metadata.get('added_stage_keys'))
        boundary = metadata.get('protected_through', -1)
        if (retained != before or tuple(key for key in after if key in before) != before
                or set(after) - set(before) != set(added) or set(added) & set(before)
                or after[-1] != before[-1] or type(boundary) is not int
                or not -1 <= boundary < len(before)
                or after[:boundary + 1] != before[:boundary + 1]
                or set(added) - set(fresh_by_key)):
            raise ValidationAppError('新增主题元数据未完整保留当前路线与保护前缀')
        old_by_key = {stage.stable_key: stage for stage in original}
        fresh_predecessors = {stage.stable_key: fresh[index - 1].stable_key if index else None
                              for index, stage in enumerate(fresh)}
        composed = []
        changed = False
        for index, key in enumerate(after):
            stage = old_by_key[key] if key in old_by_key else fresh_by_key[key]
            changed = changed or key not in old_by_key or stage.order_index != index
            if stage.order_index != index:
                stage = replace(stage, order_index=index)
            if key in old_by_key and changed and index > boundary:
                stage = _invalidate_guidance(stage)
            elif key not in old_by_key and fresh_predecessors[key] != (after[index - 1] if index else None):
                stage = _invalidate_guidance(stage)
            composed.append(stage)
        if len({stage.stage_id for stage in composed}) != len(composed):
            raise ValidationAppError('保留阶段与新增阶段标识重复')
        old_links = _selected_links(current, {stage.stage_id for stage in original})
        new_links = _selected_links(generated, {fresh_by_key[key].stage_id for key in added})
        links = {field: (*old_links[field], *new_links[field]) for field in old_links}
        return replace(generated, stages=tuple(composed), **links, unit_refs=(), task_refs=(),
                       node_stable_keys=(), route_change=deepcopy(metadata))
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
