import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.core.errors import ValidationAppError
from app.domain.assistant import build_input
from app.domain.assistant_teaching import advance_state, project_teaching


FIXTURE = json.loads((Path(__file__).parents[1] / 'fixtures/assistant_teaching_state/request-171-missing-proposal.json').read_text(encoding='utf-8'))
KIND = 'practice_teach_with_proposal'


def project(value):
    return project_teaching(value, FIXTURE['frozen_teaching_state'], 'practice', expected_response_kind=KIND, context=FIXTURE['frozen_context'])


def positive():
    value = deepcopy(FIXTURE['original_provider_payload'])
    value['proposal'] = '实现知识助手。仅校验输入、正常回答和处理超时。空输入拒绝且不执行；超时返回可检查错误及失败证据。不新增部署或付款任务。这是实施要求，不表示已执行或验收通过。'
    return value


def test_request171_original_is_rejected_only_by_new_final_contract():
    value = FIXTURE['original_provider_payload']
    assert project_teaching(value, FIXTURE['frozen_teaching_state'], 'practice')['status'] == 'continue'
    with pytest.raises(ValidationAppError) as caught:
        project(value)
    assert caught.value.details['error_class'] == 'missing_required_practice_proposal'


def test_final_exact_remaining_projects_ready_and_minimal_wire():
    value = positive()
    del value['evaluation']
    del value['phase']
    value['run_id'] = 'model-extra'
    result = project(value)
    assert result['status'] == 'ready_to_draft' and result['phase'] == 'teach'
    assert result['proposal'] == value['proposal'] and 'model-extra' not in str(result)
    assert advance_state(FIXTURE['frozen_teaching_state'], result, {'run_id': 'new', 'message_id': 'new', 'trigger_message_id': 'new'})['step'] == 'ready'


@pytest.mark.parametrize('proposal', [None, '', ' ', 4, [], {}, 'x' * 20001, '\x00', '\ud800'])
def test_missing_empty_type_and_length_are_rejected(proposal):
    value = positive(); value['proposal'] = proposal
    with pytest.raises(ValidationAppError): project(value)


@pytest.mark.parametrize('fault', ['resolved', 'unknown', 'duplicate', 'missing', 'question', 'followup', 'phase', 'continue', 'rollback', 'advance'])
def test_final_is_not_model_controlled(fault):
    value = positive()
    if fault == 'resolved': value['teaching'][0]['issue_id'] = 'i1'
    elif fault == 'unknown': value['teaching'][0]['issue_id'] = 'i9'
    elif fault == 'duplicate': value['teaching'][1] = deepcopy(value['teaching'][0])
    elif fault == 'missing': value['teaching'].pop()
    elif fault == 'question': value['teaching'][0]['explanation'] = '再回答这个问题？'
    elif fault == 'followup': value['followup_question'] = '再想一下'
    elif fault == 'phase': value['phase'] = 'question_round_2'
    elif fault == 'continue': value['status'] = 'continue'
    elif fault == 'rollback': value['evaluation'][0]['state'] = 'unresolved'
    else: value['evaluation'][1]['state'] = 'resolved'
    with pytest.raises(ValidationAppError): project(value)


@pytest.mark.parametrize('proposal', ['必须部署并开通付款。', '不要求部署，但必须付款。', '新增一个工程任务，训练模型。', '工程已执行并通过验收。', '已经通过测试。'])
def test_proposal_cannot_add_tasks_or_claim_execution(proposal):
    value = positive(); value['proposal'] = proposal
    with pytest.raises(ValidationAppError): project(value)


@pytest.mark.parametrize('proposal', ['禁止部署或付款。', '严禁新增工程任务。', '避免部署和付款。'])
def test_local_prohibition_preserves_safe_task_constraints(proposal):
    value=positive();value['proposal']=proposal
    assert project(value)['status']=='ready_to_draft'


@pytest.mark.parametrize('proposal', ['禁止部署但必须付款。', '禁止部署必须付款。'])
def test_local_prohibition_never_exempts_new_positive_obligation(proposal):
    value=positive();value['proposal']=proposal
    with pytest.raises(ValidationAppError):project(value)


def test_new_turn_freezes_expected_kind_summary_is_unchanged():
    state = FIXTURE['frozen_teaching_state']
    trigger = dict(message_id='u', intent='question', content='我仍不理解')
    assert build_input('practice', FIXTURE['frozen_context'], None, trigger, [], teaching_state=state)['expected_response_kind'] == KIND
    assert 'expected_response_kind' not in build_input('summary', {}, None, trigger, [], teaching_state=state)


def test_maximum_length_positive_and_invalid_frozen_kind():
    value = positive(); value['proposal'] = '范围内实现。' + '说明。' * 6664
    assert len(value['proposal']) <= 20000 and project(value)['status'] == 'ready_to_draft'
    with pytest.raises(ValidationAppError):
        project_teaching(value, FIXTURE['frozen_teaching_state'], 'practice', expected_response_kind='continue')


@pytest.mark.parametrize('fault', ['none', 'kind', 'json', 'truncation', 'unknown'])
def test_final_wire_is_server_selected_strict_and_never_retried(fault):
    import httpx
    from app.domain.assistant import ASSISTANT_PROTOCOL, ASSISTANT_PURPOSE
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.ports.llm import LLMFailure, LLMResult
    calls = []
    def response(request):
        calls.append(json.loads(request.content))
        if fault == 'unknown': return httpx.Response(503, json={'error': 'unknown'})
        return httpx.Response(200, json=dict(choices=[dict(finish_reason='length' if fault=='truncation' else 'stop',
            message=dict(content='{invalid' if fault=='json' else json.dumps(positive(), ensure_ascii=False)))],
            usage=dict(prompt_tokens=2, completion_tokens=3)))
    payload = build_input('practice', FIXTURE['frozen_context'], None,
                          dict(message_id='u', intent='question', content='剩余问题'), [], teaching_state=FIXTURE['frozen_teaching_state'])
    if fault == 'kind': payload['expected_response_kind'] = 'continue'
    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        provider=OpenAICompatibleLLM(base_url='https://fixture.invalid/v1',api_key='fixture',model='fixture',client=client)
        provider.prompt_version=ASSISTANT_PROTOCOL
        result=provider.generate_structured(purpose=ASSISTANT_PURPOSE,payload=payload,schema_name='AssistantReplyV1',run_id='r',attempt_id='a')
    assert len(calls)==(0 if fault=='kind' else 1)
    if fault=='none':
        assert isinstance(result, LLMResult)
        wire=json.loads(calls[0]['messages'][1]['content'])
        assert set(wire['field_shape'])=={'reply','teaching','proposal'}
        assert wire['context']['expected_response_kind']==KIND
        assert '禁止proposal=null' in calls[0]['messages'][0]['content']
        assert project(result.payload)['status']=='ready_to_draft'
    else:
        assert isinstance(result, LLMFailure)
        assert result.error_class == {'kind':'assistant_teaching_contract_invalid','json':'provider_invalid_json','truncation':'provider_output_truncated','unknown':'provider_server_unknown'}[fault]
        assert result.dispatch_unknown == (fault == 'unknown')


@pytest.mark.parametrize('fault', ['bool', 'zero', 'missing', 'extra', 'type', 'cap'])
def test_assistant_frozen_budget_primitive_checks_preserve_exact_policy(fault):
    from app.core.ids import content_hash
    from app.domain.assistant import manifest_intact, assistant_manifest
    from app.application.model_binding import SubmissionBinding
    from app.application.planning_budget import BudgetPolicy
    manifest=assistant_manifest(SubmissionBinding('fixture', BudgetPolicy(100,100,100,100,100,100)))
    if fault=='bool':manifest['budget_policy']['repair']=True
    elif fault=='zero':manifest['budget_policy']['model_cap']=0
    elif fault=='missing':manifest['budget_policy'].pop('outline')
    elif fault=='extra':manifest['budget_policy']['unknown']=100
    elif fault=='type':manifest['budget_policy']=[]
    else:manifest['output_cap']=99
    body={k:v for k,v in manifest.items() if k!='manifest_hash'};manifest['manifest_hash']=content_hash(body)
    assert not manifest_intact(manifest)
