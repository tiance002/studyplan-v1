"""One bounded issue ledger. Server phases and IDs, never model business IDs.

The immutable input and successful receipt are the persistence format. Public
messages contain only server-rendered natural text and the existing proposal.
"""
from copy import deepcopy
from app.core.errors import ValidationAppError

TEACHING_CONTRACT = 'issue-ledger-v1'
REEXPRESSION = '现在请你再用自己的话重新总结一下这些关系。\n不用照着我的表述复述，按你的理解说明就可以。'
FIELDS = {'phase','status','reply','proposal','issues','evaluation','teaching','question','followup_question'}

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

def project_teaching(value, state, mode):
    if not isinstance(value,dict) or mode not in ('summary','practice'): _fail()
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

def teaching_shape(state, mode):
    step=state['step']
    if step=='diagnose':
        return dict(phase='question_round_1 | ready_to_draft (only a sound initial draft)',reply='简短过渡语，最多600字',issues=[dict(topic='关键主题',question='关键问题；1到5项，不制造缺口')],proposal=None)
    if step=='question_round_2':
        return dict(phase='question_round_2',reply='简短过渡语，不重复具体问题或教学',evaluation=[dict(issue_id='server iN',state='resolved | unresolved',followup_question='null if resolved, nonempty question if unresolved')],proposal=None)
    if step=='ready': return dict(phase='ready_to_draft',reply='简短过渡语',proposal='完整候选稿')
    return dict(phase='teach | ready_to_draft',reply='简短过渡语',evaluation=[dict(issue_id='server iN',state='resolved | unresolved')],teaching=[dict(issue_id='only unresolved server iN',explanation='正确解释，不提问')],proposal='summary teach: null; ready/practice teach: complete proposal')
