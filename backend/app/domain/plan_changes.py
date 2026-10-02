"""Finite, deterministic route edits; no provider calls or inferred optionality."""
from dataclasses import dataclass, replace

from app.core.errors import ValidationAppError
from app.domain.planning.models import PlanDraft


@dataclass(frozen=True)
class PlanChangeCommand:
    project_id: str
    plan_id: str
    expected_version: int
    idempotency_key: str
    operation: str
    stage_keys: tuple[str, ...] = ()
    stage_key: str = ''

    def __post_init__(self):
        if self.operation not in {'reorder_future_stage', 'remove_optional_topic'}:
            raise ValidationAppError('不支持的有限路线变更')
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise ValidationAppError('路线变更需要明确版本')
        for value in (self.project_id, self.plan_id, self.idempotency_key):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValidationAppError('路线变更标识必须为1–200字符')
        if not isinstance(self.stage_keys, (tuple, list)) or len(self.stage_keys) > 100:
            raise ValidationAppError('路线调整最多100个阶段')
        if any(not isinstance(k, str) or not k.strip() or len(k) > 200 for k in self.stage_keys):
            raise ValidationAppError('阶段键必须为1–200字符')
        if not isinstance(self.stage_key, str) or len(self.stage_key) > 200:
            raise ValidationAppError('阶段键超出范围')
        if ((self.operation == 'reorder_future_stage' and (not self.stage_keys or self.stage_key))
                or (self.operation == 'remove_optional_topic' and (self.stage_keys or not self.stage_key))):
            raise ValidationAppError('阶段顺序与移除操作参数不一致')
        object.__setattr__(self, 'stage_keys', tuple(self.stage_keys))


def changed_draft(current, command, *, draft_id, protected_through, inclusion, nodes_by_stage,
                  prerequisites, required_nodes):
    original = tuple(sorted(current.stages, key=lambda s: s.order_index))
    before = tuple(s.stable_key for s in original)
    if not original or len(original) > 100:
        raise ValidationAppError('路线阶段为空或超出调整范围')
    if command.operation == 'reorder_future_stage':
        after = command.stage_keys
        if len(after) != len(before) or set(after) != set(before):
            raise ValidationAppError('调整顺序必须完整且不重复地覆盖当前阶段')
        if after[:protected_through + 1] != before[:protected_through + 1]:
            raise ValidationAppError('已开始阶段及之前的阶段不能调整顺序')
        # The final practice carries the declared outcome requirements; it stays final.
        if after[-1] != before[-1]:
            raise ValidationAppError('最终综合实践必须保留在路线末尾')
        if after == before:
            raise ValidationAppError('阶段顺序没有变化')
    else:
        key = command.stage_key
        if key not in before or inclusion.get(key, 'required') != 'optional':
            raise ValidationAppError('只能移除受控课程明确标记为可选的阶段')
        if before.index(key) <= protected_through or key == before[-1]:
            raise ValidationAppError('已开始阶段、之前的阶段和最终综合实践不能移除')
        after = tuple(k for k in before if k != key)
    first = {}
    for index, key in enumerate(after):
        for node in nodes_by_stage.get(key, ()):
            first.setdefault(node, index)
    if set(required_nodes) - set(first):
        raise ValidationAppError('调整会丢失目标必需模块或其前置依赖')
    for predecessor, dependent in prerequisites:
        if dependent in first and (predecessor not in first or first[predecessor] > first[dependent]):
            raise ValidationAppError('调整违反知识前置依赖顺序')
    by_key = {s.stable_key: s for s in original}
    stages = []
    previous_changed = False
    for index, key in enumerate(after):
        stage = by_key[key]
        changed = stage.order_index != index or (index > 0 and after[index - 1] != before[stage.order_index - 1])
        previous_changed = previous_changed or changed
        guide = stage.learning_guidance
        if guide and previous_changed and index > protected_through:
            guide = replace(guide, why_now='路线调整后，按本阶段当前目标与已核对的前置依赖安排学习',
                            previous_relation='路线顺序已调整；请重新核对前次教程关系与当前项目基线',
                            exposure_relation='unknown', comparison_focus=(), source_slice=None,
                            reading_prerequisites=(), practice_prerequisites=(),
                            practice_delta=replace(guide.practice_delta,
                                baseline='沿用自己的当前项目；调整后请重新核对本阶段任务的输入基线',
                                preserved=('保留已有功能，并按当前任务核对兼容性',),
                                reuse=('调整后的后续使用关系需要重新核对',)))
        stages.append(replace(stage, order_index=index, learning_guidance=guide))
    retained = {s.stage_id for s in stages}
    task_links = tuple(link for link in current.task_links if link.stage_id in retained)
    tasks = {link.task_id for link in task_links}
    assignments = tuple(a for a in current.stage_resources if a.stage_id in retained)
    ids = {a.assignment_id for a in assignments}
    return PlanDraft(draft_id, current.project_id, '', current.goal_snapshot, current.revision + 1,
                     stages=tuple(stages), unit_links=tuple(link for link in current.unit_links if link.stage_id in retained),
                     task_links=task_links,
                     task_knowledge_links=tuple(link for link in current.task_knowledge_links if link.task_id in tasks),
                     stage_resources=assignments, extensions=tuple(e for e in current.extensions if e.stage_id in retained),
                     resource_snapshots=tuple(s for s in current.resource_snapshots if s['assignment_id'] in ids),
                     source_pack_key=current.source_pack_key, source_pack_version=current.source_pack_version,
                     goal_spec=current.goal_spec)
