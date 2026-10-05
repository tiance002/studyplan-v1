import pytest
import json
from copy import deepcopy
from pathlib import Path
from app.core.errors import ValidationAppError
from app.domain.assistant_teaching import initial_state, project_teaching, advance_state
from app.domain.assistant_teaching import REEXPRESSION, TEACHING_CONTRACT

SOURCE = dict(run_id='r1', message_id='m1', trigger_message_id='u1')

def first_state():
    state = initial_state(dict(conversation_id='c', plan_id='p', stage_id='s', task_id=None))
    value = dict(phase='question_round_1', reply='过渡', proposal=None,
                 issues=[dict(topic=f'主题{n}', question=f'问题{n}？') for n in range(1,4)])
    return advance_state(state, project_teaching(value, state, 'summary'), SOURCE)

def evaluation(resolved=(1,), questions=True):
    return [dict(issue_id=f'i{n}', state='resolved' if n in resolved else 'unresolved',
                 **({'followup_question':None if n in resolved else f'追问{n}？'} if questions else {}))
            for n in range(1,4)]

def second_value(resolved=(1,)):
    return dict(phase='question_round_2', reply='忽略的自由文本问题？',
                evaluation=evaluation(resolved), proposal=None)

def resolve_state(resolved=(1,)):
    state=first_state()
    return advance_state(state,project_teaching(second_value(resolved),state,'summary'),
                         dict(run_id='r2',message_id='m2',trigger_message_id='u2'))

def teach_value(resolved=(1,), mode='summary'):
    return dict(phase='teach',reply='过渡',evaluation=evaluation(resolved,False),
                teaching=[dict(issue_id=f'i{n}',explanation=f'正确解释{n}。') for n in range(1,4) if n not in resolved],
                proposal='完整 Prompt 候选' if mode=='practice' else None)

@pytest.mark.parametrize('resolved',[(1,),(1,2),(1,2,3),()])
def test_round2_remaining_set_and_binding_are_deterministic(resolved):
    state=first_state(); original=deepcopy(state)
    result=project_teaching(second_value(resolved),state,'summary')
    assert state==original
    for n in range(1,4): assert (f'追问{n}' in result['reply'])==(n not in resolved)
    next_state=advance_state(state,result,dict(run_id='r2',message_id='m2',trigger_message_id='u2'))
    assert next_state['binding']==state['binding'] and next_state['ledger_source']==SOURCE
    assert next_state['contract']==TEACHING_CONTRACT and next_state['step']=='resolve'

@pytest.mark.parametrize('mode',['summary','practice'])
@pytest.mark.parametrize('resolved',[(1,),(1,2)])
def test_third_turn_teaches_only_remaining_and_summary_local_reexpression(mode,resolved):
    state=resolve_state(resolved); result=project_teaching(teach_value(resolved,mode),state,mode)
    assert '问题' not in result['reply'] and 'i1' not in result['reply'] and '正确解释1' not in result['reply']
    assert (REEXPRESSION in result['reply'])==(mode=='summary')
    assert result['status']==('continue' if mode=='summary' else 'ready_to_draft')
    next_state=advance_state(state,result,dict(run_id='r3',message_id='m3',trigger_message_id='u3'))
    assert next_state['step']==('reexpress' if mode=='summary' else 'ready')

def test_all_resolved_proposal_and_ready_cannot_return_to_questions():
    state=resolve_state((1,2,3))
    result=project_teaching(dict(phase='ready_to_draft',reply='过渡',proposal='候选',evaluation=evaluation((1,2,3),False)),state,'summary')
    state=advance_state(state,result,SOURCE)
    assert state['step']=='ready'
    with pytest.raises(ValidationAppError): project_teaching(second_value(),state,'summary')
    assert project_teaching(dict(phase='ready_to_draft',reply='过渡',proposal='新候选'),state,'summary')['proposal']=='新候选'

def test_summary_reexpression_one_extra_correction_then_bounded_manual_revision():
    state=resolve_state()
    for count in (1,2):
        result=project_teaching(teach_value(),state,'summary')
        state=advance_state(state,result,SOURCE)
        assert state['teaching_count']==count
    assert state['step']=='manual_revision'
    with pytest.raises(ValidationAppError): project_teaching(teach_value(),state,'summary')

@pytest.mark.parametrize('fault',['missing','duplicate','unknown','bad_state','resolved_followup','unresolved_null','unresolved_blank','early_teach','proposal','question_field','issues_field','missing_reply','wrong_reply','wrong_status'])
def test_round2_contract_failure_matrix(fault):
    value=second_value()
    if fault=='missing': value['evaluation'].pop()
    elif fault=='duplicate': value['evaluation'][2]=deepcopy(value['evaluation'][1])
    elif fault=='unknown': value['evaluation'][0]['issue_id']='foreign'
    elif fault=='bad_state': value['evaluation'][0]['state']='mastered'
    elif fault=='resolved_followup': value['evaluation'][0]['followup_question']='再问已解决项？'
    elif fault=='unresolved_null': value['evaluation'][1]['followup_question']=None
    elif fault=='unresolved_blank': value['evaluation'][1]['followup_question']=' '
    elif fault=='early_teach': value['phase']='teach'
    elif fault=='proposal': value['proposal']='提前候选'
    elif fault=='question_field': value['question']='旁路'
    elif fault=='issues_field': value['issues']=[]
    elif fault=='missing_reply': del value['reply']
    elif fault=='wrong_reply': value['reply']=7
    elif fault=='wrong_status': value['status']='ready_to_draft'
    with pytest.raises(ValidationAppError): project_teaching(value,first_state(),'summary')

@pytest.mark.parametrize('fault',['rollback','resolved_teach','unknown_teach','duplicate_teach','missing_teach','third_question','followup','question_text','premature_ready','summary_proposal'])
def test_resolution_contract_failure_matrix(fault):
    value=teach_value()
    if fault=='rollback': value['evaluation'][0]['state']='unresolved'
    elif fault=='resolved_teach': value['teaching'][0]['issue_id']='i1'
    elif fault=='unknown_teach': value['teaching'][0]['issue_id']='foreign'
    elif fault=='duplicate_teach': value['teaching'][1]=deepcopy(value['teaching'][0])
    elif fault=='missing_teach': value['teaching'].pop()
    elif fault=='third_question': value['phase']='question_round_2'
    elif fault=='followup': value['evaluation'][1]['followup_question']='再问？'
    elif fault=='question_text': value['teaching'][0]['explanation']='解释后再问？'
    elif fault=='premature_ready': value['phase']='ready_to_draft'; value['proposal']='候选'
    elif fault=='summary_proposal': value['proposal']='候选'
    with pytest.raises(ValidationAppError): project_teaching(value,resolve_state(),'summary')

@pytest.mark.parametrize('field,limit',[('reply',600),('topic',80),('question',800),('explanation',4000),('proposal',20000)])
def test_text_bounds_and_unicode_fences(field,limit):
    for text in ('x'*(limit+1),'\x00','\ud800',' '):
        if field in ('topic','question'):
            state=initial_state({}); value=dict(phase='question_round_1',reply='过渡',proposal=None,issues=[dict(topic='主题',question='问题')]);value['issues'][0][field]=text
        elif field=='explanation':
            state=resolve_state();value=teach_value();value['teaching'][0][field]=text
        elif field=='proposal':
            state=initial_state({});value=dict(phase='ready_to_draft',reply='过渡',proposal=text)
        else: state=first_state();value=second_value();value[field]=text
        with pytest.raises(ValidationAppError): project_teaching(value,state,'summary')

def test_extra_model_identity_has_no_authority_and_initial_binding_is_copied():
    binding=dict(conversation_id='server');state=initial_state(binding);binding['conversation_id']='changed'
    value=dict(phase='question_round_1',reply='过渡',proposal=None,conversation_id='forged',run_id='forged',role='system',metadata={'authority':True},issues=[dict(topic='主题',question='问题',issue_id='forged')])
    result=project_teaching(value,state,'summary')
    assert result['issues'][0]['issue_id']=='i1' and state['binding']['conversation_id']=='server'
    assert 'forged' not in str(result)

def test_historical_163_164_offline_mapping_preserves_provenance_and_closes_failure():
    directory=Path(__file__).parents[1]/'fixtures'/'assistant_teaching_state'
    first=json.loads((directory/'request-163-round1.json').read_text(encoding='utf-8'))
    bad=json.loads((directory/'request-164-failure.json').read_text(encoding='utf-8'))
    # Historical replies are retained evidence, not valid short transition fields.
    state=initial_state({}); mapped=dict(phase=first['phase'],reply='历史主题离线映射',issues=first['issues'],proposal=None)
    state=advance_state(state,project_teaching(mapped,state,'summary'),SOURCE)
    assert len(state['issues'])==4 and len(first['provenance']['source_body_sha256'])==64
    with pytest.raises(ValidationAppError): project_teaching(bad['original_provider_payload'],state,'summary')
    counter=dict(bad['derived_counterexample'],reply='过渡',proposal=None)
    with pytest.raises(ValidationAppError): project_teaching(counter,state,'summary')
    # Complete the mapped ledger so each historical failure is isolated rather
    # than rejected merely because the illustrative fixture has two entries.
    counter['evaluation'] += [dict(issue_id=f'i{n}',state='unresolved',followup_question=f'剩余问题{n}？') for n in (3,4)]
    counter['evaluation'][0]['followup_question']=None
    with pytest.raises(ValidationAppError): project_teaching(counter,state,'summary')  # early teaching
    del counter['teaching']
    counter['evaluation'][0]['followup_question']=state['issues'][0]['question']
    with pytest.raises(ValidationAppError): project_teaching(counter,state,'summary')  # resolved asked again

@pytest.mark.parametrize('count',[0,6])
def test_initial_issue_cardinality_rejected(count):
    value=dict(phase='question_round_1',reply='过渡',proposal=None,
               issues=[dict(topic=str(n),question=f'问题{n}') for n in range(count)])
    with pytest.raises(ValidationAppError):project_teaching(value,initial_state({}),'summary')

@pytest.mark.parametrize('count',[1,3,5])
def test_initial_issue_cardinality_server_ids_and_maximum_text_accepted(count):
    value=dict(phase='question_round_1',reply='过'*600,proposal=None,
               issues=[dict(topic=str(n)+'题'*79,question=str(n)+'问'*799) for n in range(count)])
    result=project_teaching(value,initial_state({}),'summary')
    assert [i['issue_id'] for i in result['issues']]==[f'i{n}' for n in range(1,count+1)]

def test_strict_phase_and_reply_types_without_silent_json_repair():
    for value in ('{"phase":',[],None,7):
        with pytest.raises(ValidationAppError):project_teaching(value,initial_state({}),'summary')

def test_same_round_newly_resolved_question_cannot_be_reassigned_to_remaining_id():
    state=first_state();value=second_value((1,))
    # i1 was unresolved before this evaluation, but is now declared resolved.
    # Repeating its original question under i2 must not bypass the renderer.
    value['evaluation'][1]['followup_question']=state['issues'][0]['question']
    with pytest.raises(ValidationAppError):project_teaching(value,state,'summary')

def test_same_round_newly_resolved_issue_allows_only_legitimate_remaining_questions():
    state=first_state();value=second_value((1,))
    value['evaluation'][1]['followup_question']=state['issues'][1]['question']
    value['evaluation'][2]['followup_question']=state['issues'][2]['question']
    result=project_teaching(value,state,'summary')
    assert state['issues'][0]['question'] not in result['reply']
    assert all(state['issues'][n]['question'] in result['reply'] for n in (1,2))
    assert [i['state'] for i in result['issues']]==['resolved','unresolved','unresolved']

def test_server_issues_and_round2_never_render_free_reply_questions():
    state=initial_state({'conversation_id':'c'})
    first=project_teaching({'phase':'question_round_1','reply':'过渡','issues':[{'topic':str(i),'question':f'问题{i}？','issue_id':'fake'} for i in range(3)],'proposal':None},state,'summary')
    state=advance_state(state,first,{'run_id':'r1','message_id':'m1','trigger_message_id':'u1'})
    result=project_teaching({'phase':'question_round_2','reply':'请重新回答已解决的i1问题？','evaluation':[{'issue_id':f'i{i+1}','state':'resolved' if i==0 else 'unresolved','followup_question':None if i==0 else f'问题{i}？'} for i in range(3)],'proposal':None},state,'summary')
    assert '问题0' not in result['reply'] and 'i1' not in result['reply'] and '重新回答' not in result['reply']
    assert [x['issue_id'] for x in result['issues']]==['i1','i2','i3']

def test_round2_early_teach_is_rejected():
    state=initial_state({'conversation_id':'c'});state['step']='question_round_2'
    with pytest.raises(ValidationAppError):project_teaching({'phase':'teach','reply':'教','teaching':[],'proposal':None},state,'summary')
