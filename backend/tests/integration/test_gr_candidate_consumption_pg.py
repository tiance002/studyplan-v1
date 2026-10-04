"""Future Fake generation and frozen candidate consumption in a new owned DB."""
import json
from pathlib import Path

from tests.integration import test_v613_contract_pg as existing

reviewed_db = existing.reviewed_db
pytestmark = existing.pytestmark


def test_new_fake_rag_plan_retains_two_frozen_candidates_one_task(reviewed_db, monkeypatch):
    # Reuse the already approved generation/qualification checks. Isolate all
    # artifacts; the original module and v6.13 Plan/evidence remain unchanged.
    out = Path(__file__).resolve().parents[3] / "var/gr-binding-20261004/future-fake-pg"
    out.mkdir(parents=True, exist_ok=True)
    assert not (out / "plan-rag.json").exists()
    monkeypatch.setenv("STUDYPLAN_V613_KEEP_OWNED", "0")
    monkeypatch.setattr(existing, "OUT", out)
    existing.test_generate_fake_draft_confirm_canonical_pg(
        reviewed_db, "rag", existing.RAG_GOAL, "agent.application")
    workspace = json.loads((out / "workspace-rag.json").read_text(encoding="utf-8"))
    stage = next(s for s in workspace["stages"] if s["stage"]["stable_key"].endswith(".gr"))
    candidates = stage["resources"]
    assert len(candidates) == 2 and len(stage["tasks"]) == 1
    assert {r["canonical_url"] for r in candidates} == {
        "https://github.com/infiniflow/ragflow", "https://github.com/Tencent/WeKnora"}
    assert all(r["role"] == "case_study" and r["media_type"] == "repo"
               and r["source_ref"] and r["source_version"] == 1
               and r["verification_status"] == "legacy_index"
               and not r["ordered_sections"] and not r["warnings"] for r in candidates)
