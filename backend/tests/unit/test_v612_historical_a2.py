"""Original retained parsed v6.10 responses; never dispatch or rewrite history."""

import json
from pathlib import Path

from app.agent_workflows.planning_batches import DEFAULT_BUDGET, freeze_manifest, validate_structure_batch
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.infrastructure.domain_pack import load_pack

FIXTURES = Path(__file__).parents[1] / "fixtures/v610_a2"


def test_original_a2_responses_still_fail_legacy_contract():
    pack = adapt_semantic_pack(
        load_pack("agent-application-v6.json"), "零基础系统学习 Agent 应用开发，先做一个最小应用。", None
    )
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:historical")
    batch = next(b for b in manifest["structure_batches"] if b["stage_key"].endswith(".a2"))
    extra = {
        "tool-contract",
        "registry",
        "permission",
        "error-evidence",
        "timeout-audit",
        "responsibility-separation",
    }
    for i in range(3):
        response = json.loads((FIXTURES / f"actual-a2-attempt-{i}.json").read_text(encoding="utf-8"))
        raw = response["response_payload"]["payload"]
        errors = validate_structure_batch(
            {**raw, "stage_key": batch["stage_key"], "batch_index": batch["batch_index"]}, batch, pack
        )
        assert errors
        if i in (0, 2):
            assert {n["stable_key"].rsplit(".", 1)[-1] for n in raw["nodes"][1:]} == extra
            assert any("新增未审核知识节点" in e for e in errors)
        else:
            assert set(raw) == {"type", "schema", "purpose", "stage_key", "batch_index", "field_shape"}
            assert all(
                any(f"缺少必需字段：{field}" in e for e in errors)
                for field in ("nodes", "units", "relations")
            )
