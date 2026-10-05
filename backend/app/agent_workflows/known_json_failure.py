"""Narrow known JSON failure evidence; never parses or repairs provider text."""
from copy import deepcopy
from dataclasses import asdict, replace

from app.ports.llm import LLMFailure


def attest_failure(result, run_id, attempt_id):
    """Called only after the attempt outcome transaction committed (or read)."""
    if (not isinstance(result, LLMFailure) or result.error_class != 'provider_invalid_json'
            or result.dispatch_unknown or not isinstance(result.details, dict)):
        return result
    return replace(result, details={**result.details, 'known_failed_attempt': {
        'run_id': run_id, 'attempt_id': attempt_id, 'receipt_persisted': True,
    }})


def known_invalid_json(result, run_id, attempt_id):
    """Explicit allowlist, receipt identity, and measured response facts."""
    if not isinstance(result, LLMFailure) or result.error_class != 'provider_invalid_json':
        return False
    details = result.details
    if not isinstance(details, dict):
        return False
    proof = details.get('known_failed_attempt')
    return (
        result.dispatch_unknown is False
        and details.get('dispatched') is True
        and details.get('response_received') is True
        and type(details.get('http_status')) is int and details['http_status'] == 200
        and details.get('finish_reason') == 'stop'
        and type(details.get('content_chars')) is int and details['content_chars'] > 0
        and all(type(v) is int and v >= 0 for v in (result.input_tokens, result.output_tokens))
        and isinstance(proof, dict) and set(proof) == {'run_id', 'attempt_id', 'receipt_persisted'}
        and proof['run_id'] == run_id and proof['attempt_id'] == attempt_id
        and proof['receipt_persisted'] is True
    )


def failure_receipt(result, run_id, attempt_id, schema_name):
    if not known_invalid_json(result, run_id, attempt_id):
        return None
    # This is a failed receipt, with no parsed payload and no provider raw body.
    return {'run_id': run_id, 'attempt_id': attempt_id, 'schema_name': schema_name,
            'failure': asdict(result)}


def failed_entry(kind, state, index, attempt_id):
    """Deterministic invalid placeholder, never hydrated as successful content."""
    batch = state['manifest'][kind + '_batches'][index]
    entry = {'stage_key': batch['stage_key'], 'batch_index': index}
    if kind == 'practice':
        entry['payload'] = {}
    else:
        from app.agent_workflows.planning_structure import presentation_entry, uses_reviewed_structure
        if uses_reviewed_structure(state['manifest'], batch):
            entry = presentation_entry({}, state, batch)
    entry['_known_invalid_json_attempt'] = attempt_id
    return deepcopy(entry)
