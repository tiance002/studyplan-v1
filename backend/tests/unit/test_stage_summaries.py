import pytest
from app.api.v1.summary_schemas import SummarySaveRequest
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.summaries import SummarySaveCommand, review_rubric_context


def test_stage_command_and_nullable_request_preserve_raw_original():
    body = dict(plan_id='plan', stage_id='stage', content=' 原文🙂 ', expected_version=0, idempotency_key='key')
    assert SummarySaveRequest(**body).unit_id is None
    assert SummarySaveRequest(**body, unit_id=None).unit_id is None
    cmd = SummarySaveCommand(project_id='p', unit_id=None, **body)
    assert cmd.position == ('p', 'plan', 'stage', None)
    assert cmd.content == body['content']


@pytest.mark.parametrize('unit', ['', ' ', 4, '\x00'])
def test_nonnull_unit_still_requires_valid_identifier(unit):
    with pytest.raises(ValidationAppError):
        SummarySaveCommand('p', 'plan', 'stage', unit, 'raw', 0, 'key')


def test_legacy_unit_input_hash_stays_identical():
    cmd = SummarySaveCommand('p', 'plan', 'stage', 'unit', 'raw', 0, 'key')
    assert cmd.input_hash() == content_hash(dict(project_id='p', plan_id='plan', stage_id='stage', unit_id='unit', content='raw', expected_version=0))


def test_stage_review_context_includes_requirements_without_private_sources():
    snapshot = dict(summary_scope='stage', stage_title='Stage', stage_stable_key='s', stage_objective='goal',
        rubric_version=1, objectives=['goal'], rubric=[], stage_snapshot={'private': 'SECRET'},
        unit_snapshots=[dict(unit_id='u', title='Unit', objectives=['explain'], rubric=[{'criterion': 'example'}], private='SECRET')],
        source_snapshot={'private': 'SECRET'})
    context = review_rubric_context(snapshot)
    assert context['summary_scope'] == 'stage'
    assert context['stage_objective'] == 'goal'
    assert context['unit_snapshots'][0]['objectives'] == ['explain']
    assert 'SECRET' not in str(context)
