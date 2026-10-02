import pytest


@pytest.mark.parametrize(
    ('summary', 'required', 'available', 'accepted', 'status', 'completed'),
    [
        (False, [], [], [], 'incomplete', 0),
        (True, [], [], [], 'completed', 0),
        (False, ['a'], ['a'], ['a'], 'incomplete', 1),
        (True, ['a', 'b'], ['a', 'b'], ['a'], 'incomplete', 1),
        (True, ['a', 'b'], ['a', 'b'], ['a', 'b'], 'completed', 2),
        (True, ['a', 'b'], ['a'], ['a', 'b'], 'incomplete', 1),
        (True, ['a'], ['a'], ['foreign'], 'incomplete', 0),
    ],
)
def test_stage_completion_requires_summary_and_all_present_accepted_tasks(summary, required, available, accepted, status, completed):
    from app.domain.stage_completion import derive_stage_completion
    result = derive_stage_completion(summary_completed=summary, required_task_ids=required,
        available_task_ids=available, accepted_task_ids=accepted)
    assert result == dict(status=status, summary_completed=summary, completed_practice_tasks=completed,
        total_practice_tasks=len(required))
