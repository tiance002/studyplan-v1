from dataclasses import replace

import pytest
from app.core.errors import AppError
from app.domain.enums import OutlineSectionKind
from app.domain.plan_changes import PlanChangeCommand, changed_draft
from app.domain.planning.guidance import LearningGuidance, PracticeDelta
from app.domain.planning.models import PlanRevision, PlanStage, PlanUnitLink


def plan():
    stages = tuple(PlanStage.create(stable_key=k, title=k, section_kind=OutlineSectionKind.CORE,
                                   order_index=i) for i, k in enumerate(('a', 'b', 'c', 'final')))
    return PlanRevision.create(project_id='p', goal_snapshot='Learn', revision=1, stages=stages,
                               unit_links=tuple(PlanUnitLink(s.stage_id, s.stable_key, 0) for s in stages))


def command(**values):
    return PlanChangeCommand(project_id='p', plan_id='plan', expected_version=1, idempotency_key='key',
                             operation='reorder_future_stage', stage_keys=('a', 'c', 'b', 'final'), **values)


def test_reorder_keeps_protected_prefix_and_final_task_position():
    current = plan()
    draft = changed_draft(current, command(), draft_id='draft', protected_through=0,
                          inclusion={}, nodes_by_stage={}, prerequisites=(), required_nodes=())
    assert [s.stable_key for s in draft.stages] == ['a', 'c', 'b', 'final']
    assert current.stages[1].stable_key == 'b'
    assert draft.stages[0] == current.stages[0]
    assert draft.unit_links == current.unit_links


@pytest.mark.parametrize('order', [('b', 'a', 'c', 'final'), ('a', 'c', 'final', 'b'),
                                  ('a', 'b', 'c', 'final'), ('a', 'c', 'final'), ('a', 'c', 'c', 'final')])
def test_invalid_started_final_noop_or_incomplete_reorder_is_rejected(order):
    with pytest.raises(AppError):
        changed_draft(plan(), replace(command(), stage_keys=order), draft_id='draft', protected_through=0,
                      inclusion={}, nodes_by_stage={}, prerequisites=(), required_nodes=())


def test_prerequisite_cannot_be_moved_after_dependent():
    current = plan()
    with pytest.raises(AppError):
        changed_draft(current, command(), draft_id='draft', protected_through=-1, inclusion={},
                      nodes_by_stage={'b': {'nb'}, 'c': {'nc'}}, prerequisites=(('nb', 'nc'),),
                      required_nodes=('nb', 'nc'))


def test_remove_requires_explicit_optional_and_cannot_drop_required_closure():
    current = plan()
    cmd = replace(command(), operation='remove_optional_topic', stage_keys=(), stage_key='b')
    kwargs = dict(draft_id='draft', protected_through=0, nodes_by_stage={'b': {'nb'}},
                  prerequisites=(), required_nodes=())
    with pytest.raises(AppError):
        changed_draft(current, cmd, inclusion={}, **kwargs)
    draft = changed_draft(current, cmd, inclusion={'b': 'optional'}, **kwargs)
    assert [s.stable_key for s in draft.stages] == ['a', 'c', 'final']
    assert len(draft.unit_links) == 3
    with pytest.raises(AppError):
        changed_draft(current, cmd, inclusion={'b': 'optional'}, **{**kwargs, 'required_nodes': ('nb',)})


def test_bounded_command_rejects_mutable_invalid_contract():
    with pytest.raises(AppError):
        replace(command(), operation='invented')
    with pytest.raises(AppError):
        replace(command(), expected_version=True)


def test_reorder_invalidates_previous_tutorial_claims_but_preserves_real_task_outputs():
    guide = LearningGuidance(why_now='已经在上一步完成b', previous_relation='对比b教程', learning_focus=('分发工具',),
        comparison_focus=('比较上一教程',), practice_delta=PracticeDelta('旧基线b', ('增加工具',),
        ('保留聊天',), ('验证错误参数',), ('交给下一步',)), exposure_relation='compare')
    current = plan()
    current = replace(current, stages=tuple(replace(s, learning_guidance=guide) for s in current.stages))
    draft = changed_draft(current, command(), draft_id='draft', protected_through=0, inclusion={},
                          nodes_by_stage={}, prerequisites=(), required_nodes=())
    assert draft.stages[0].learning_guidance == guide
    moved = draft.stages[1].learning_guidance
    assert moved.why_now != guide.why_now and moved.previous_relation != guide.previous_relation
    assert moved.exposure_relation == 'unknown' and moved.comparison_focus == ()
    assert moved.practice_delta.validation == ('验证错误参数',)
