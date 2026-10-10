"""New owned PG receipts plus actual Body adapter; HTTP and Reader are synthetic."""
import json
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
from app.core.ids import content_hash
from app.domain.planning.resource_research import ResearchSession
from app.infrastructure.checkpointer.v2_planning_runtime import DurableBody, DurableResourceResearcher
from app.infrastructure.providers.v2_attempts import PgV2Calls
from psycopg.types.json import Jsonb

from backend.tests.integration import test_v2_planning_runtime_pg as old
from backend.tests.unit import test_resource_research as f
from backend.tests.unit.test_deep_audit_resource_adapters import body_adapter
from backend.tests.unit.test_research_chapter_v3 import ChapterReader, values
from backend.tests.unit.test_teaching_body import candidate

pytestmark = pytest.mark.postgres
EVIDENCE = Path(__file__).resolve().parents[3] / "var/r01-r05-fix/research-pg"


@pytest.fixture(scope="module")
def db():
    previous = old.EVIDENCE
    old.EVIDENCE = EVIDENCE
    generator = old.db.__wrapped__()
    try:
        yield next(generator)
    finally:
        try:
            next(generator)
        except StopIteration:
            pass
        old.EVIDENCE = previous


@pytest.mark.parametrize("capacity_refusal", [False, True])
def test_v3_chapter_scope_receipts_recover_without_http_or_reader_and_meter_new_operations(db, capacity_refusal):
    scope, run, fence, _facts, manifest = old.bound.__wrapped__(db)
    manifest["product_semantics"], manifest["research_rules_version"] = "planning-v2-product-v2", "research_chapter_v3"
    manifest["manifest_hash"] = content_hash({k: v for k, v in manifest.items() if k != "manifest_hash"})
    # New synthetic never-dispatched Run only: freeze its new protocol before first reservation.
    with psycopg.connect(db.migrator_dsn) as conn:
        detail = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'", (run,)).fetchone()[0]
        detail["manifest"] = detail["initial"]["manifest"] = manifest
        conn.execute("UPDATE ai_run_events SET detail=%s WHERE run_id=%s AND status='submission'", (Jsonb(detail), run))
    _p, plan, _coverage, gaps = values()
    from app.domain.planning.resource_research import ResearchRequirement
    requirement = ResearchRequirement(gaps.gaps[0].capability_id, gaps.gaps[0].missing_outcomes,
        "required", "applied", gaps.gaps[0].requirement_refs, "", (), ())
    body, http = body_adapter("[模型结构化输出](docs/04-结构化输出.md)\n[API](docs/api.md)",
        {"docs/04-结构化输出.md": "X" * 16385 if capacity_refusal else "Synthetic unsupported chapter",
         "docs/api.md": "Synthetic joint supported chapter"})
    class Provider(ChapterReader):
        configuration_ref, model = "test:frozen", "synthetic"
        def request_options(self, purpose):
            return {"max_tokens": 1024}
    provider = Provider({"Synthetic joint supported chapter": {o.outcome_id for o in plan.learning_outcomes}})
    record = replace(candidate(), project_id=fence.project_id)
    review_scope = plan.learning_outcomes
    def inspect_two():
        ledger = PgV2Calls(db.app_dsn, scope=scope, project_id=fence.project_id, run_id=run,
            manifest=manifest, fence=fence, provider=provider)
        researcher = DurableResourceResearcher(ledger, github=None, web=None, body_reader=DurableBody(ledger, body), llm=ledger)
        session = ResearchSession(run, "c" * 64, f.ResearchBudget(max_cost_micros=1000000), rules_version="research_chapter_v3")
        first = researcher._inspect(record, requirement, review_scope, plan, session, manifest["checked_at"])
        second = researcher._inspect(record, requirement, review_scope, plan, session, manifest["checked_at"])
        return first, second, session, ledger
    first, second, session, ledger = inspect_two()
    assert second[0] and {r.outcome_id for r in second[0][0].evidence} == {o.outcome_id for o in plan.learning_outcomes}
    assert len(http) == 4 and len(provider.calls) == (1 if capacity_refusal else 2)
    before = len(http), len(provider.calls), ledger.usage()
    again_first, again_second, restored, again_ledger = inspect_two()
    assert again_first == first and again_second == second
    assert before == (len(http), len(provider.calls), again_ledger.usage())
    assert session.snapshot().to_payload() == restored.snapshot().to_payload()
    assert before[2]["candidates"] == 2
    with psycopg.connect(db.migrator_dsn) as conn:
        rows = conn.execute("SELECT schema_name,response_payload FROM ai_provider_attempts WHERE run_id=%s ORDER BY created_at", (run,)).fetchall()
    assert sum(schema == "V2TransientBodyV2" for schema, _receipt in rows) == 2
    encoded = json.dumps(rows, default=str)
    assert "Synthetic unsupported chapter" not in encoded and "Synthetic joint supported chapter" not in encoded
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / ("capacity" if capacity_refusal else "negative")).with_suffix(".json").write_text(json.dumps({
        "database": db.name, "run_id": run, "http_requests": len(http), "reader_requests": len(provider.calls),
        "usage": before[2], "snapshot": restored.snapshot().to_payload()}, ensure_ascii=False, indent=2), encoding="utf8")
