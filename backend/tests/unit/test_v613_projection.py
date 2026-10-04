"""Independent frozen input / retained-result comparisons, no network or PG."""
from contextlib import nullcontext
from copy import deepcopy

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import SHORT_GENERATION_VERSION, build_short_planning_graph
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
from app.infrastructure.providers.fake import FakeLLM
from app.infrastructure.providers.planning_demo import build_planning_demo
from app.ports.graph_runner import GraphRecoveryError
from tests.unit.test_reviewed_structure_contract import state
from app.agent_workflows.planning_projection import checked_projection


def prepared():
    initial = state()
    initial.pop('current_structure_index')
    initial['graph_version'] = SHORT_GENERATION_VERSION
    fake, saved, receipts = build_planning_demo(), [], []
    original = fake.generate_structured
    def record(**kw):
        result = original(**kw)
        if hasattr(result, 'payload'):
            receipts.append({'run_id':kw['run_id'],'attempt_id':kw['attempt_id'],
                             'schema_name':kw['schema_name'],'payload':deepcopy(result.payload)})
        return result
    fake.generate_structured = record
    nodes = PlanningNodes(llm=fake, save_draft=lambda s:saved.append(deepcopy(s)))
    # Kept outside checkpoint; baseline ignores these fields, proving original RED.
    nodes.frozen_input = deepcopy(initial)
    nodes.load_receipts = lambda:deepcopy(receipts)
    saver = InMemorySaver()
    graph = build_short_planning_graph(nodes, checkpointer=saver)
    config = {'configurable':{'thread_id':'v613-unit-projection'},'recursion_limit':1000}
    graph.invoke(initial,config,interrupt_before=['save_draft_projection'])
    return initial,fake,saved,receipts,nodes,saver,graph,config


def test_original_presave_rubric_attack_rejected_without_save_or_dispatch():
    initial,fake,saved,_,nodes,saver,graph,config = prepared()
    units=deepcopy(graph.get_state(config).values['units'])
    units[0]['rubric']['canonical_knowledge']={'forged':{'title':'forged'}}
    units[0]['rubric']['teaching']={'focus_refs':['forged'],'intent':'forged'}
    graph.update_state(config,{'units':units},as_node='merge_and_validate')
    executor=PgPlanningExecutor('unused',llm=fake)
    executor._saver=lambda _:nullcontext(saver)
    before=len(fake.calls)
    try:
        executor.execute_or_resume(nodes,initial,'v613-unit-projection',SHORT_GENERATION_VERSION,lambda:None)
    except (ValueError, GraphRecoveryError):
        pass
    assert saved==[]
    assert len(fake.calls)==before


def test_untampered_postmerge_restore_saves_once_no_new_model():
    initial,fake,saved,_,nodes,saver,_,_ = prepared()
    executor=PgPlanningExecutor('unused',llm=fake)
    executor._saver=lambda _:nullcontext(saver)
    before=len(fake.calls)
    executor.execute_or_resume(nodes,initial,'v613-unit-projection',SHORT_GENERATION_VERSION,lambda:None)
    assert len(saved)==1 and len(fake.calls)==before


def test_original_partial_contract_deletion_refuses_direct_dispatch():
    initial=state()
    fake=FakeLLM({'planning.structure':lambda *_:{}})
    nodes=PlanningNodes(llm=fake)
    nodes.frozen_input=deepcopy(initial)
    initial['manifest'].pop('manifest_hash')
    initial['manifest'].pop('structure_input_format')
    result=nodes.generate_structure_batch(initial)
    assert result.get('generation_errors')
    assert fake.calls==[]


@pytest.mark.parametrize('mutation', [
    'node_title','node_scope','unit_id','unit_links','unit_order','teaching_focus',
    'canonical_acceptance','relations','practice_acceptance','resource_role',
    'resource_section','guidance','extension','outline_order','missing_units',
    'forged_raw_and_batch','foreign_response','all_markers','edited_flag',
])
def test_final_projection_variants_compare_exact_content_before_save(mutation):
    initial,fake,saved,receipts,nodes,_,graph,config = prepared()
    candidate=deepcopy(graph.get_state(config).values)
    if mutation=='node_title':candidate['nodes'][0]['title']='forged'
    elif mutation=='node_scope':candidate['nodes'][0]['scope']=['forged']
    elif mutation=='unit_id':candidate['units'][0]['stable_key']='unit.forged'
    elif mutation=='unit_links':candidate['units'][0]['node_keys']=['forged']
    elif mutation=='unit_order':candidate['units']=list(reversed(candidate['units']))
    elif mutation=='teaching_focus':candidate['units'][0]['rubric']['teaching']['focus_refs']=['forged']
    elif mutation=='canonical_acceptance':
        next(iter(candidate['units'][0]['rubric']['canonical_knowledge'].values()))['acceptance']=['forged']
    elif mutation=='relations':candidate['relations'][0]['relation_type']='forged'
    elif mutation=='practice_acceptance':candidate['practice_proposal']['tasks'][0]['acceptance']=['forged']
    elif mutation=='resource_role':candidate['outline']['sections'][0]['resources'][0]['role']='forged'
    elif mutation=='resource_section':candidate['outline']['sections'][0]['resources'][0]['section_refs']=['forged']
    elif mutation=='guidance':candidate['outline']['sections'][0]['learning_guidance']['reading_goal']='forged'
    elif mutation=='extension':candidate['outline']['sections'][0]['extensions'].append({'type':'forged'})
    elif mutation=='outline_order':candidate['outline']['sections'].reverse()
    elif mutation=='missing_units':candidate.pop('units')
    elif mutation=='forged_raw_and_batch':
        batch=candidate['structure_batches'][0]
        batch['_reviewed_presentation']['units'][0]['title']='forged'
        batch['units'][0]['title']='forged'
        candidate['units'][0]['title']='forged'
    elif mutation=='foreign_response':receipts[0]['run_id']='foreign-run'
    elif mutation=='all_markers':
        for key in ('structure_input_format','structure_focus_format','manifest_hash'):
            candidate['manifest'].pop(key,None)
        for batch in candidate['manifest']['structure_batches']:batch.pop('structure_input_format',None)
    elif mutation=='edited_flag':
        candidate['edited_draft']=True
        candidate['nodes'][0]['title']='forged edit without revision'
    before=len(fake.calls)
    with pytest.raises(ValueError):nodes.save_draft_projection(candidate)
    assert not saved and len(fake.calls)==before


@pytest.mark.parametrize('mutation', ['null_focus','unknown_batch','null_batch','focus_without_outer','hash_only_deleted'])
@pytest.mark.parametrize('phase', ['generate_structure_batch','repair_batch'])
def test_incomplete_contract_variants_rejected_before_dispatch(mutation,phase):
    initial=state();trusted=deepcopy(initial)
    manifest=initial['manifest']
    if mutation=='null_focus':manifest['structure_focus_format']=None
    elif mutation=='unknown_batch':manifest['structure_batches'][0]['structure_input_format']='unknown'
    elif mutation=='null_batch':manifest['structure_batches'][0]['structure_input_format']=None
    elif mutation=='focus_without_outer':manifest.pop('structure_input_format')
    elif mutation=='hash_only_deleted':manifest.pop('manifest_hash')
    fake=FakeLLM({'planning.structure':lambda *_:{},'planning.repair':lambda *_:{}})
    nodes=PlanningNodes(llm=fake,frozen_input=trusted)
    initial['repair_target']={'kind':'structure','stage_key':manifest['structure_batches'][initial['current_structure_index']]['stage_key'],
                              'batch_index':initial['current_structure_index']}
    initial['structure_batches']=[{}]*(initial['current_structure_index']+1)
    result=getattr(nodes,phase)(initial)
    assert result.get('generation_errors') and fake.calls==[]


def test_validated_copy_is_independent_and_missing_authority_rejected():
    initial,_,_,receipts,_,_,graph,config=prepared()
    candidate=deepcopy(graph.get_state(config).values)
    checked=checked_projection(candidate,initial,receipts,final=True)
    candidate['nodes'][0]['title']='after-check mutation'
    assert checked['nodes'][0]['title']!='after-check mutation'
    with pytest.raises(ValueError,match='Independent frozen submission missing'):
        checked_projection(checked,None,receipts,final=True)


@pytest.mark.parametrize('kind',['structure','practice'])
def test_known_repair_receipt_before_checkpoint_commit_can_resume_exact_attempt(kind):
    from app.agent_workflows.planning_batches import attempt_key, REPAIR_PURPOSE
    from app.agent_workflows.planning_structure import presentation_entry
    from tests.unit.test_reviewed_structure_contract import valid
    s=state(); index=s['current_structure_index'] if kind=='structure' else 0
    initial=deepcopy(s);initial.pop('current_structure_index')
    batch=s['manifest'][kind+'_batches'][index];key=batch['stage_key']
    checkpoint=deepcopy(initial)
    checkpoint.update({f'current_{kind}_index':index,'repair_count':0,
                       'repair_target':{'kind':kind,'stage_key':key,'batch_index':index}})
    if kind=='structure':
        previous={'units':[]};corrected=valid(s);schema='ReviewedStructureV1'
        checkpoint['structure_batches']=[presentation_entry(previous,checkpoint,batch)]
        offset=index
    else:
        previous={'tasks':[]};corrected={'tasks':[{'goal':'known receipt'}]};schema='PracticeProposalV1'
        checkpoint['practice_batches']=[{'stage_key':key,'batch_index':index,'payload':previous}]
        offset=len(s['manifest']['structure_batches'])+index
    receipts=[{'run_id':s['run_id'],'attempt_id':attempt_key(s['run_id'],'planning.'+kind,key,index,0),
               'schema_name':schema,'payload':previous},
              {'run_id':s['run_id'],'attempt_id':attempt_key(s['run_id'],REPAIR_PURPOSE,key,offset,1),
               'schema_name':schema,'payload':corrected}]
    with pytest.raises(ValueError,match='Derived projection mismatch'):
        checked_projection(checkpoint,initial,receipts)
    assert checked_projection(checkpoint,initial,receipts,pending_repair=True)==checkpoint
    with pytest.raises(ValueError):
        checked_projection(checkpoint,initial,receipts,pending_repair=True,final=True)
    # A checkpoint cannot use an unrelated pending stage to hide an edited raw.
    checkpoint['repair_target']['stage_key']='foreign-stage'
    with pytest.raises(ValueError,match='Pending repair stage/index mismatch'):
        checked_projection(checkpoint,initial,receipts,pending_repair=True)
