"""One bounded issue ledger. Server phases and IDs, never model business IDs.

The immutable input and successful receipt are the persistence format. Public
messages contain only server-rendered natural text and the existing proposal.
"""
from copy import deepcopy
import re
from app.core.errors import ValidationAppError

TEACHING_CONTRACT = 'issue-ledger-v1'
REEXPRESSION = '现在请你再用自己的话重新总结一下这些关系。\n不用照着我的表述复述，按你的理解说明就可以。'
FIELDS = {'phase','status','reply','proposal','issues','evaluation','teaching','question','followup_question'}
PRACTICE_FINAL = 'practice_teach_with_proposal'
PRACTICE_LEDGER = 'practice_issue_ledger'


def _expected_kind(state, mode):
    if mode != 'practice':
        return None
    return (PRACTICE_FINAL if state.get('step') == 'resolve'
            and any(i['state'] == 'unresolved' for i in state['issues']) else PRACTICE_LEDGER)


expected_response_kind = _expected_kind


def validate_expected_kind(payload):
    # Absence means a previously frozen turn, not a request to backfill history.
    if 'expected_response_kind' in payload:
        if (payload.get('mode') != 'practice' or payload.get('teaching_contract') != TEACHING_CONTRACT
                or payload['expected_response_kind'] != expected_response_kind(payload['teaching_state'], 'practice')):
            _fail()


def project_frozen_teaching(value, payload):
    validate_expected_kind(payload)
    return project_teaching(value, payload['teaching_state'], payload['mode'],
                            expected_response_kind=payload.get('expected_response_kind'), context=payload.get('context'))


def _proposal_scope(proposal, context):
    # Reuse the established action-local negation rule. These covered capability
    # escapes are deterministic guards, not a claim of general semantic proof.
    from app.agent_workflows.planning_structure import _negated_teaching_action
    clauses = re.split(r'[。；;,，.!?！？\n]|但是|然而|但(?!是)|\bbut\b', proposal, flags=re.I)
    allowed = ' '.join([str(context.get('goal', '')), *(context.get('in_scope') or []), *(context.get('acceptance') or [])])
    excluded = ' '.join(context.get('out_scope') or [])
    topics = [r'部署|\bdeploy\w*\b', r'付款|支付|收款|payment|purchase',
              r'训练模型|模型训练|train(?:ing)?\s+(?:a\s+)?model', r'kubernetes|k8s',
              r'任意命令|arbitrary\s+commands?', r'新增.{0,8}任务|额外.{0,8}必做|(?:必须|强制).{0,12}新建.{0,8}项目']
    for clause in clauses:
        # Equivalent two-character prohibitions keep match offsets intact and
        # reuse the same local negation/positive-obligation barriers.
        negative_clause = re.sub(r'禁止|严禁|避免', '不得', clause)
        for pattern in topics:
            if re.search(pattern, allowed, re.I) and not re.search(pattern, excluded, re.I):
                continue
            if any(not _negated_teaching_action(negative_clause, match) for match in re.finditer(pattern, clause, re.I)):
                raise ValidationAppError('实践候选超出冻结任务范围', error_class='practice_proposal_scope_invalid')
        claims = r'(?:已经?|已然).{0,6}(?:执行|部署|完成|通过(?:验收|测试))|(?:工程|任务|验收|测试).{0,4}(?:已完成|已通过)|\b(?:already\s+(?:executed|completed)|tests?\s+passed)\b'
        if any(not _negated_teaching_action(negative_clause, match) for match in re.finditer(claims, clause, re.I)):
            raise ValidationAppError('实践候选不能声称已经执行或通过验收', error_class='practice_proposal_completion_claim')


def _final_practice(value, state, context):
    proposal = value.get('proposal')
    if proposal is None or isinstance(proposal, str) and not proposal.strip():
        raise ValidationAppError('最终实践教学缺少完整候选 Prompt', error_class='missing_required_practice_proposal')
    _text(proposal, 20000)
    _text(value.get('reply'), 600)
    _only(value, {'phase', 'status', 'reply', 'teaching', 'proposal', 'evaluation'})
    if value.get('phase', 'teach') != 'teach' or value.get('status', 'ready_to_draft') != 'ready_to_draft':
        _fail()
    issues = deepcopy(state['issues'])
    if 'evaluation' in value:
        evaluated = _evaluate(value['evaluation'], state, questions=False)
        if any(a['state'] != b['state'] for a, b in zip(evaluated, issues, strict=True)):
            _fail()
    remaining = [i for i in issues if i['state'] == 'unresolved']
    raw = value.get('teaching')
    if not isinstance(raw, list) or len(raw) != len(remaining):
        _fail()
    eligible = {i['issue_id'] for i in remaining}; explanations = {}
    for item in raw:
        _only(item, set())
        identifier = item.get('issue_id')
        if not isinstance(identifier, str) or identifier not in eligible or identifier in explanations:
            _fail()
        text = _text(item.get('explanation'), 4000)
        if '?' in text or '？' in text:
            _fail()
        explanations[identifier] = text
    _proposal_scope(proposal, context or {})
    rendered = '我们直接把剩下的关键理解讲清楚：\n\n' + '\n\n'.join(
        f'{n}. {i["topic"]}\n{explanations[i["issue_id"]]}' for n, i in enumerate(remaining, 1))
    _text(rendered, 16000)
    return dict(reply=rendered, status='ready_to_draft', proposal=proposal, phase='teach', issues=issues)

def _fail():
    raise ValidationAppError('助手教学阶段或问题集合不一致')

def _text(value, limit):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit or '\x00' in value
            or any(0xD800<=ord(c)<=0xDFFF for c in value)):
        _fail()
    return value

def initial_state(binding):
    return dict(contract=TEACHING_CONTRACT,binding=deepcopy(binding),step='diagnose',issues=[],
                ledger_source=None,previous=None,teaching_count=0)

def _only(value, allowed):
    if not isinstance(value,dict) or (set(value)&FIELDS)-set(allowed): _fail()

def _evaluate(value, state, *, questions):
    prior={i['issue_id']:i for i in state['issues']}
    if not isinstance(value,list) or len(value)!=len(prior): _fail()
    by_id={}
    for item in value:
        _only(item,{'followup_question'} if questions else set())
        identifier=item.get('issue_id');status=item.get('state')
        if not isinstance(identifier,str) or identifier not in prior or identifier in by_id: _fail()
        if status not in ('resolved','unresolved'): _fail()
        if prior[identifier]['state']=='resolved' and status!='resolved': _fail()
        question=None
        if questions:
            if 'followup_question' not in item: _fail()
            question=item['followup_question']
            if status=='resolved' and question is not None: _fail()
            if status=='unresolved':
                _text(question,800)
                if any(p['state']=='resolved' and p['question'].strip()==question.strip() for p in prior.values()): _fail()
        by_id[identifier]=dict(prior[identifier],state=status,followup_question=question)
    if questions:
        resolved_questions={i['question'].strip() for i in by_id.values() if i['state']=='resolved'}
        if any(i['state']=='unresolved' and i['followup_question'].strip() in resolved_questions for i in by_id.values()): _fail()
    return [by_id[i['issue_id']] for i in state['issues']]

def project_teaching(value, state, mode, *, expected_response_kind=None, context=None):
    if not isinstance(value,dict) or mode not in ('summary','practice'): _fail()
    if expected_response_kind is not None:
        if expected_response_kind != _expected_kind(state, mode): _fail()
        if expected_response_kind == PRACTICE_FINAL:
            return _final_practice(value, state, context)
    _text(value.get('reply'),600)  # Receipt-only transition; not question authority.
    phase=value.get('phase');step=state.get('step');proposal=value.get('proposal')
    if 'proposal' not in value: _fail()
    issues=deepcopy(state['issues']);status='continue';rendered=''
    if step=='diagnose':
        if phase=='question_round_1':
            _only(value,{'phase','status','reply','issues','proposal'})
            raw=value.get('issues')
            # Do not manufacture gaps when fewer than three actually exist.
            if not isinstance(raw,list) or not 1<=len(raw)<=5 or proposal is not None: _fail()
            issues=[]
            for n,item in enumerate(raw,1):
                _only(item,{'question'})
                topic=_text(item.get('topic'),80);question=_text(item.get('question'),800)
                if any(i['topic']==topic or i['question']==question for i in issues): _fail()
                issues.append(dict(issue_id=f'i{n}',topic=topic,question=question,state='unresolved',followup_question=None))
            rendered='先一起想清楚以下关键问题：\n\n'+'\n\n'.join(f'{n}. {i["question"]}' for n,i in enumerate(issues,1))
        elif phase=='ready_to_draft':
            _only(value,{'phase','status','reply','proposal'});status='ready_to_draft'
        else: _fail()
    elif step=='question_round_2':
        if phase!='question_round_2' or proposal is not None: _fail()
        _only(value,{'phase','status','reply','evaluation','proposal'})
        issues=_evaluate(value.get('evaluation'),state,questions=True)
        remaining=[i for i in issues if i['state']=='unresolved']
        rendered=('已经讲清的部分保留；还需一起想清楚：\n\n'+'\n\n'.join(f'{n}. {i["followup_question"]}' for n,i in enumerate(remaining,1))
                  if remaining else '这些关键问题已经讲清。你可以继续补充自己的总结或 Prompt。')
    elif step in ('resolve','reexpress'):
        _only(value,{'phase','status','reply','evaluation','teaching','proposal'})
        issues=_evaluate(value.get('evaluation'),state,questions=False)
        unresolved=[i for i in issues if i['state']=='unresolved']
        if not unresolved:
            if phase!='ready_to_draft' or 'teaching' in value: _fail()
            status='ready_to_draft'
        else:
            if phase!='teach' or state['teaching_count']>=2: _fail()
            raw=value.get('teaching')
            if not isinstance(raw,list) or len(raw)!=len(unresolved): _fail()
            eligible={i['issue_id']:i for i in unresolved};explanations={}
            for item in raw:
                _only(item,set())
                identifier=item.get('issue_id')
                if not isinstance(identifier,str) or identifier not in eligible or identifier in explanations: _fail()
                text=_text(item.get('explanation'),4000)
                # A question string cannot be smuggled into the teach renderer.
                if '?' in text or '？' in text: _fail()
                explanations[identifier]=text
            rendered='我们直接把剩下的关键理解讲清楚：\n\n'+'\n\n'.join(f'{n}. {i["topic"]}\n{explanations[i["issue_id"]]}' for n,i in enumerate(unresolved,1))
            if mode=='summary':
                if proposal is not None: _fail()
                rendered+='\n\n'+REEXPRESSION
                if state['teaching_count']==1:
                    rendered+='\n\n本会话的直接纠正已到上限。你仍可在主页面明确保存自己的原文，或从会话菜单重新开始。'
            elif proposal is not None:
                status='ready_to_draft'
    elif step=='ready':
        if phase!='ready_to_draft': _fail()
        _only(value,{'phase','status','reply','proposal'});status='ready_to_draft'
    else: _fail()
    if status=='ready_to_draft':
        _text(proposal,20000)
        rendered=rendered or '根据你已经表达和讲清的内容，整理了一版候选稿。请核对后自行决定是否保存。'
    elif proposal is not None: _fail()
    if 'status' in value and value['status']!=status: _fail()
    _text(rendered,16000)
    return dict(reply=rendered,status=status,proposal=proposal,phase=phase,issues=issues)

def advance_state(state, projection, source):
    result=deepcopy(state);result['issues']=deepcopy(projection['issues']);result['previous']=deepcopy(source)
    if projection['phase']=='question_round_1':
        result['ledger_source']=deepcopy(source);result['step']='question_round_2'
    elif projection['status']=='ready_to_draft': result['step']='ready'
    elif projection['phase']=='question_round_2': result['step']='resolve'
    elif projection['phase']=='teach':
        result['teaching_count']+=1
        result['step']='reexpress' if result['teaching_count']<2 else 'manual_revision'
    else: _fail()
    return result

def teaching_shape(state, mode, *, response_kind=None):
    if response_kind == PRACTICE_FINAL:
        return dict(reply='非空简短过渡，最多600字',
                    teaching=[dict(issue_id=i['issue_id'], explanation='解释此剩余问题，不提问，最多4000字')
                              for i in state['issues'] if i['state']=='unresolved'],
                    proposal='必须是完整非空建议最终 Prompt 字符串，最多20000字；不能null/continue')
    step=state['step']
    if step=='diagnose':
        return dict(phase='question_round_1 | ready_to_draft (only a sound initial draft)',reply='简短过渡语，最多600字',issues=[dict(topic='关键主题',question='关键问题；1到5项，不制造缺口')],proposal=None)
    if step=='question_round_2':
        return dict(phase='question_round_2',reply='简短过渡语，不重复具体问题或教学',evaluation=[dict(issue_id='server iN',state='resolved | unresolved',followup_question='null if resolved, nonempty question if unresolved')],proposal=None)
    if step=='ready': return dict(phase='ready_to_draft',reply='简短过渡语',proposal='完整候选稿')
    return dict(phase='teach | ready_to_draft',reply='简短过渡语',evaluation=[dict(issue_id='server iN',state='resolved | unresolved')],teaching=[dict(issue_id='only unresolved server iN',explanation='正确解释，不提问')],proposal='summary teach: null; ready/practice teach: complete proposal')
