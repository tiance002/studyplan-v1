"""Explicit known-failure gate and existing batch repair; no external I/O."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    SHORT_GENERATION_VERSION, build_short_planning_graph, attempt_key,
)
from app.agent_workflows.planning_projection import checked_projection
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from tests.helpers.planning_responses import build_planning_demo
from app.ports.llm import LLMFailure, LLMDispatchUnknownError
from tests.unit.test_reviewed_structure_contract import state

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'var/rc-user-20261005/private/responses/160.body'
RAW_SHA = 'ffffffa319a2217bd889dca2f4c9416d21fc37d78903cbf4a090ccb3bf8d901c'


def known_failure(run_id, attempt_id, **changes):
    details = {'http_status': 200, 'dispatched': True, 'response_received': True,
               'finish_reason': 'stop', 'content_chars': 10,
               'known_failed_attempt': {'run_id': run_id, 'attempt_id': attempt_id,
                                        'receipt_persisted': True}}
    details.update(changes.pop('details', {}))
    return LLMFailure('provider_invalid_json', 'strict parse failed', details=details,
                      input_tokens=11, output_tokens=7, **changes)


class KnownFailureFake:
    """Fake a committed known-failure receipt, never a parsed success."""
    def __init__(self, purpose='planning.practice', outcome=None, bad_repair=None):
        self.fake = build_planning_demo()
        self.calls = []
        self.purpose, self.outcome, self.bad_repair = purpose, outcome, bad_repair
        self.failed = False

    def generate_structured(self, **kw):
        self.calls.append(deepcopy(kw))
        if kw['purpose'] == self.purpose and not self.failed:
            self.failed = True
            return self.outcome or known_failure(kw['run_id'], kw['attempt_id'])
        if kw['purpose'] == 'planning.repair' and self.bad_repair:
            if self.bad_repair == 'invalid_json':
                return known_failure(kw['run_id'], kw['attempt_id'])
            result = self.fake.generate_structured(**kw)
            payload = deepcopy(result.payload)
            if self.bad_repair == 'practice':
                payload['task_knowledge_links'][0]['role'] = 'foreign-role'
            else:
                payload['units'][0]['node_keys'] = ['foreign.canonical']
            return replace(result, payload=payload)
        return self.fake.generate_structured(**kw)


def graph_case(fake, *, stop=None):
    initial = state()
    initial.pop('current_structure_index')
    initial['graph_version'] = SHORT_GENERATION_VERSION
    saved = []
    nodes = PlanningNodes(llm=fake, frozen_input=deepcopy(initial),
                          save_draft=lambda s: saved.append(deepcopy(s)) or 'd')
    graph = build_short_planning_graph(nodes, checkpointer=InMemorySaver())
    config = {'configurable': {'thread_id': 'known-json'}, 'recursion_limit': 1000}
    graph.invoke(initial, config, interrupt_before=[stop] if stop else [])
    return initial, nodes, graph, config, saved


@pytest.mark.parametrize('purpose', ['planning.structure', 'planning.practice'])
def test_committed_invalid_json_uses_one_new_repair_and_complete_validation(purpose):
    fake = KnownFailureFake(purpose)
    initial, nodes, graph, config, saved = graph_case(fake)
    s = graph.get_state(config).values
    assert not s['validation_errors'] and len(saved) == 1
    assert s['repair_count'] == 1
    repairs = [c for c in fake.calls if c['purpose'] == 'planning.repair']
    assert len(repairs) == 1 and repairs[0]['attempt_id'].endswith(':1')
    assert len(fake.calls) == initial['manifest']['max_requests'] - initial['manifest']['max_repairs'] + 1
    ids = [c['attempt_id'] for c in fake.calls]
    assert len(ids) == len(set(ids))
    assert nodes.check_projection(s, final=True) == s


@pytest.mark.parametrize('purpose', ['planning.structure', 'planning.practice'])
def test_placeholder_is_failure_not_success_and_reconstruction_needs_receipt(purpose):
    initial, nodes, graph, config, saved = graph_case(KnownFailureFake(purpose), stop='repair_batch')
    s = graph.get_state(config).values
    assert not s['generation_errors'] and s['structure_errors'] and not saved
    assert s['repair_target']['kind'] == purpose.split('.')[1]
    assert nodes.check_projection(s, pending_repair=True) == s
    receipts = deepcopy(nodes._raw_receipts)
    failed = next(r for r in receipts if r.get('failure'))
    assert failed['failure']['error_class'] == 'provider_invalid_json'
    assert 'payload' not in failed
    receipts.remove(failed)
    with pytest.raises(ValueError):
        checked_projection(s, initial, receipts, pending_repair=True)
    with pytest.raises(ValueError):
        nodes.check_projection(s, final=True)


@pytest.mark.parametrize('kind', ['practice', 'structure', 'invalid_json'])
def test_repair_illegal_business_or_invalid_json_still_fails_without_draft(kind):
    fake = KnownFailureFake('planning.practice' if kind != 'structure' else 'planning.structure',
                            bad_repair=kind)
    _, _, graph, config, saved = graph_case(fake)
    s = graph.get_state(config).values
    assert s['validation_errors'] and not saved
    repair_count = len([c for c in fake.calls if c['purpose'] == 'planning.repair'])
    assert repair_count <= 2 and s['repair_count'] == repair_count


@pytest.mark.parametrize('error', [
    'provider_output_truncated', 'provider_transport_unknown', 'provider_auth_rejected',
    'endpoint_preflight_rejected', 'endpoint_security_rejected', 'run_budget_exhausted',
    'run_manifest_violation', 'planning_claim_missing', 'provider_invalid_shape',
    'provider_invalid_envelope', 'unsupported_schema', 'arbitrary_failure',
])
def test_error_allowlist_is_exact_even_when_retryable(error):
    failure = replace(known_failure('contract-fixture', 'unused'), error_class=error, retryable=True)
    fake = KnownFailureFake(outcome=failure)
    _, _, graph, config, saved = graph_case(fake)
    assert graph.get_state(config).values['generation_errors'] and not saved
    assert not [c for c in fake.calls if c['purpose'] == 'planning.repair']


@pytest.mark.parametrize('changes', [
    {'dispatch_unknown': True}, {'details': {'finish_reason': 'length'}},
    {'details': {'finish_reason': None}}, {'details': {'dispatched': False}},
    {'details': {'response_received': False}}, {'details': {'http_status': 401}},
    {'details': {'known_failed_attempt': {}}}, {'input_tokens': None},
    {'output_tokens': None}, {'input_tokens': True}, {'output_tokens': -1},
    {'details': {'http_status': True}}, {'details': {'content_chars': 0}},
    {'details': {'known_failed_attempt': {'run_id': 'foreign', 'attempt_id': 'foreign', 'receipt_persisted': True}}},
])
def test_invalid_json_without_exact_known_receipt_proof_is_not_repairable(changes):
    # Explicitly synthesize the current normal key for binding checks.
    s = state()
    key = attempt_key(s['run_id'], 'planning.practice', s['manifest']['stages'][0]['stage_key'], 0, 0)
    failure = known_failure(s['run_id'], key)
    if 'details' in changes:
        failure = replace(failure, details={**failure.details, **changes['details']})
    else:
        failure = replace(failure, **changes)
    fake = KnownFailureFake(outcome=failure)
    if changes.get('dispatch_unknown'):
        with pytest.raises(LLMDispatchUnknownError):
            graph_case(fake)
    else:
        _, _, graph, config, saved = graph_case(fake)
        assert graph.get_state(config).values['generation_errors'] and not saved
    assert not [c for c in fake.calls if c['purpose'] == 'planning.repair']


def test_original_g6_body_remains_strict_invalid_json_with_actual_usage():
    if not RAW.exists():
        pytest.skip('Retained private fixture only available in owned local acceptance')
    body = RAW.read_bytes()
    assert hashlib.sha256(body).hexdigest() == RAW_SHA
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body))) as client:
        provider = OpenAICompatibleLLM(base_url='https://provider.example', api_key='offline',
                                      model='mock', client=client)
        result = provider.generate_structured(purpose='planning.practice', payload={},
            schema_name='PracticeProposalV1', run_id='offline', attempt_id='offline')
    assert isinstance(result, LLMFailure) and result.error_class == 'provider_invalid_json'
    assert not result.dispatch_unknown and result.details['finish_reason'] == 'stop'
    assert (result.input_tokens, result.output_tokens) == (2581, 1534)
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == RAW_SHA


def test_retained_g6_frozen_contract_repairs_only_a_future_fixture_copy():
    if not RAW.exists():
        pytest.skip('Retained private fixture only available in owned local acceptance')
    from app.agent_workflows.known_json_failure import attest_failure
    from app.agent_workflows.planning_structure import presentation_entry
    source = json.loads((RAW.parents[1] / 'submission.json').read_text(encoding='utf-8'))['initial']
    initial = deepcopy(source)
    initial['run_id'] = 'offline-future-g6-contract'
    manifest = initial['manifest']
    current = next(i for i, b in enumerate(manifest['practice_batches'])
                   if b['stage_key'] == 'stage.v62.agent.application.g6')
    assert current == 15 and len(manifest['stages']) == 18
    s = {**deepcopy(initial), 'current_practice_index': current, 'repair_count': 0}
    s['structure_batches'] = []
    for i, b in enumerate(manifest['structure_batches']):
        envelope = json.loads((RAW.parent / f'{127 + i}.body').read_text(encoding='utf-8'))
        produced = json.loads(envelope['choices'][0]['message']['content'])
        s['structure_batches'].append(presentation_entry(produced, s, b))
    # Prior practice values only supply list positions; this test never saves a Draft.
    s['practice_batches'] = [{'stage_key': b['stage_key'], 'batch_index': i, 'payload': {}}
                             for i, b in enumerate(manifest['practice_batches'][:current])]
    fake, failures = build_planning_demo(), []
    body = RAW.read_bytes()
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body))) as client:
        provider = OpenAICompatibleLLM(base_url='https://provider.example', api_key='offline',
                                      model='mock', client=client)
        class LocalFutureFixture:
            def generate_structured(self, **kw):
                if kw['purpose'] == 'planning.practice':
                    result = provider.generate_structured(**kw)
                    failures.append(result)
                    # Fake retained receipt; actual commit is covered by owned PG tests.
                    return attest_failure(result, kw['run_id'], kw['attempt_id'])
                return fake.generate_structured(**kw)
        nodes = PlanningNodes(llm=LocalFutureFixture(), frozen_input=initial)
        s.update(nodes.generate_practice_batch(s))
        s.update(nodes.validate_practice_batch_node(s))
        assert s['repair_target'] == {'kind': 'practice', 'stage_key': 'stage.v62.agent.application.g6',
                                      'batch_index': 15}
        assert s['structure_errors'] and not s.get('generation_errors')
        s.update(nodes.repair_batch(s))
        s.update(nodes.validate_practice_batch_node(s))
    assert not s['validation_errors'] and s['repair_count'] == 1
    assert len(failures) == len(fake.calls) == 1
    recorded_run, recorded_attempt, recorded_purpose = fake.calls[0]
    assert recorded_run == initial['run_id'] and recorded_purpose == 'planning.repair'
    assert recorded_attempt.endswith(':1')
    assert failures[0].error_class == 'provider_invalid_json'
    assert failures[0].details.get('known_failed_attempt') is None
    assert source['run_id'] == 'run_ba6527a948294cf0bbe9aab1ebc8c729'
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == RAW_SHA
    raw_content = json.loads(body)['choices'][0]['message']['content']
    assert raw_content not in json.dumps(s, ensure_ascii=False)


@pytest.mark.parametrize('kind', ['structure', 'practice'])
@pytest.mark.parametrize('mutation', ['remove-marker', 'add-content', 'foreign-marker', 'receipt-error',
                                     'receipt-proof', 'receipt-usage', 'receipt-schema'])
def test_pending_failure_placeholder_and_authority_mutations_are_rejected(kind, mutation):
    initial, nodes, graph, config, _ = graph_case(KnownFailureFake('planning.' + kind), stop='repair_batch')
    s = deepcopy(graph.get_state(config).values)
    receipts = deepcopy(nodes._raw_receipts)
    failed = next(r for r in receipts if r.get('failure'))
    entry = s[kind + '_batches'][s.get('current_' + kind + '_index', 0)]
    if mutation == 'remove-marker':
        entry.pop('_known_invalid_json_attempt')
    elif mutation == 'add-content':
        entry['payload' if kind == 'practice' else 'nodes'] = {'forged': True}
    elif mutation == 'foreign-marker':
        entry['_known_invalid_json_attempt'] = 'foreign'
    elif mutation == 'receipt-error':
        failed['failure']['error_class'] = 'provider_auth_rejected'
    elif mutation == 'receipt-proof':
        failed['failure']['details']['known_failed_attempt']['receipt_persisted'] = False
    elif mutation == 'receipt-usage':
        failed['failure']['input_tokens'] = None
    elif mutation == 'receipt-schema':
        failed['schema_name'] = 'foreign'
    with pytest.raises(ValueError):
        checked_projection(s, initial, receipts, pending_repair=True)


@pytest.mark.parametrize('mutation', [None, 'status', 'error_class', 'input_tokens', 'output_tokens'])
def test_only_exact_durable_failed_row_can_attest_replayed_invalid_json(mutation):
    from dataclasses import asdict
    from types import SimpleNamespace
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    from app.agent_workflows.known_json_failure import known_invalid_json
    key, run_id = 'normal-key', 'future-run'
    result = known_failure(run_id, key)
    row = {'status': 'failed', 'run_id': run_id, 'attempt_id': key,
           'request_fingerprint': 'fingerprint', 'response_payload': asdict(result),
           'error_class': result.error_class, 'input_tokens': result.input_tokens,
           'output_tokens': result.output_tokens}
    if mutation:
        row[mutation] = 'unrecognized' if mutation in ('status', 'error_class') else None
    ledger = PgAttemptLLM('unused', SimpleNamespace(configuration_ref='deployment'))
    replay = ledger._retained_result(row, run_id, 'fingerprint', 'legacy-fingerprint')
    assert known_invalid_json(replay, run_id, key) is (mutation is None)
    if mutation:
        assert replay.error_class == 'attempt_receipt_conflict'


@pytest.mark.parametrize('kind', ['structure', 'practice'])
def test_success_cannot_carry_null_failure_marker(kind):
    initial, nodes, graph, config, _ = graph_case(KnownFailureFake())
    s = deepcopy(graph.get_state(config).values)
    s[kind + '_batches'][0]['_known_invalid_json_attempt'] = None
    with pytest.raises(ValueError, match='Stale failure marker'):
        nodes.check_projection(s, final=True)


@pytest.mark.parametrize('purpose', ['planning.structure', 'planning.practice'])
def test_unmarked_batch_is_rejected_before_dispatch_or_repair(purpose):
    from app.agent_workflows.planning_batches import run_batched_planning_graph
    from app.infrastructure.domain_pack import load_pack
    from tests.helpers.batched_planning import ScriptedLLM
    pack = load_pack('agent-application-v3.json')
    class FutureUnmarkedFake(ScriptedLLM):
        def generate_structured(self, **kw):
            if kw['purpose'] == purpose and not self.count(purpose):
                self.calls.append(deepcopy(kw))
                return known_failure(kw['run_id'], kw['attempt_id'])
            return super().generate_structured(**kw)
    fake = FutureUnmarkedFake(pack)
    nodes = PlanningNodes(llm=fake, save_draft=lambda s: 'offline-unmarked-draft')
    with pytest.raises(ValueError, match='requires a frozen manifest'):
        run_batched_planning_graph(nodes, {'run_id': 'offline-future-unmarked',
            'goal': '从 Python 基础开始学习 Agent 应用开发', 'domain_pack': pack})
    assert fake.count() == 0
    assert fake.count('planning.repair') == 0
