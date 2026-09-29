"""Read the one authorized run and its durable usage; never dispatch a model call."""
import json
import os
import re
from pathlib import Path

import psycopg
from app.core.config import get_settings
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from psycopg.rows import dict_row

tag = os.environ.get('B3F2_LIVE_TAG', '')
assert not tag or re.fullmatch('[a-z0-9-]{1,32}', tag), 'Invalid evidence tag'
journal = Path(f'.git/b3f2-live-{tag}-journal.json' if tag else '.git/b3f2-live-journal.json')
state = json.loads(journal.read_text())
settings = get_settings()
with psycopg.connect(to_psycopg_dsn(os.environ['STUDYPLAN_MIGRATION_DSN']), row_factory=dict_row) as conn:
    runs = conn.execute('SELECT run_id,status,next_action,error_class,result_ref,thread_id FROM ai_runs WHERE project_id=%s ORDER BY created_at', (state['project'],)).fetchall()
    assert len(runs) == 1, 'One authorization permits exactly one generation run'
    run = runs[0]
    attempts = conn.execute('SELECT attempt_id,model_id,prompt_version,status,input_tokens,output_tokens,latency_ms,error_class FROM ai_provider_attempts WHERE run_id=%s ORDER BY created_at', (run['run_id'],)).fetchall()
    assert len(attempts) <= 5, 'Authorized request ceiling exceeded'
    payloads = conn.execute('SELECT attempt_id,response_payload FROM ai_provider_attempts WHERE run_id=%s AND response_payload IS NOT NULL ORDER BY created_at', (run['run_id'],)).fetchall()
    drafts = conn.execute('SELECT payload FROM plan_drafts WHERE run_id=%s', (run['run_id'],)).fetchall()
report = {'configured_model': settings.llm_model_id, 'source': 'deployment', 'max_output_tokens_per_request': settings.llm_max_output_tokens,
          'run': run, 'request_count': len(attempts), 'attempts': attempts,
          'input_tokens': sum(a['input_tokens'] for a in attempts) if attempts and all(a['input_tokens'] is not None for a in attempts) else None,
          'output_tokens': sum(a['output_tokens'] for a in attempts) if attempts and all(a['output_tokens'] is not None for a in attempts) else None,
          'invoice_cost': None, 'cost_note': 'Provider invoice/pricing not supplied by completion response; no cost estimate claimed.'}
output = Path('docs/acceptance/b3f2/live') / tag
output.mkdir(parents=True, exist_ok=True)
(output / 'usage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(output / 'retained-provider-results.json').write_text(json.dumps(payloads, ensure_ascii=False, indent=2), encoding='utf-8')
if drafts:
    (output / 'retained-draft.json').write_text(json.dumps(drafts[0]['payload'], ensure_ascii=False, indent=2), encoding='utf-8')
if not state.get('runId'):
    # Recover the server-assigned ID without ever submitting another generation.
    journal.write_text(json.dumps({**state, 'runId': run['run_id']}), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
