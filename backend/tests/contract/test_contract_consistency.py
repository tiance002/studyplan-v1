"""契约测试：OpenAPI / 示例的一致性。

对应验收条款：

- 「OpenAPI 无重复 operationId」
- 「前端可生成 TypeScript client」
- 「fixture 也由 DTO 校验」

B1 阶段业务路由尚未实现，因此这里测试的是**契约基建本身**：
错误码到 HTTP 状态的映射完整、示例结构合法、状态枚举与设计文档一致。
业务路由的 operationId 唯一性测试在 B2 补入（那时才有路由）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.errors import ErrorCode, STATUS_BY_CODE
from app.domain.enums import (
    AiRunNextAction,
    AiRunStatus,
    EvidenceGrade,
    PracticeTaskStatus,
    ResourceVerificationStatus,
    SummaryReviewConclusion,
    UnitProgress,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "contracts" / "examples" / "v1_examples.json"


# ---------------------------------------------------------------------------
# 枚举 = 契约：值必须与设计 §8 逐字一致
# ---------------------------------------------------------------------------


def test_unit_progress_values_match_design() -> None:
    assert [v.value for v in UnitProgress] == [
        "not_started",
        "in_progress",
        "completed",
        "skipped",
    ]


def test_summary_review_conclusion_values_match_design() -> None:
    assert {v.value for v in SummaryReviewConclusion} == {
        "satisfied",
        "needs_revision",
        "misconception",
    }


def test_practice_task_status_values_match_design() -> None:
    assert [v.value for v in PracticeTaskStatus] == [
        "pending",
        "designing",
        "prompt_reviewed",
        "implementing",
        "awaiting_evidence",
        "accepted",
        "skipped",
    ]


def test_evidence_grade_values_match_design() -> None:
    assert {v.value for v in EvidenceGrade} == {"verified", "reported", "insufficient"}


def test_ai_run_status_values_match_design() -> None:
    assert [v.value for v in AiRunStatus] == [
        "queued",
        "running",
        "waiting_user",
        "succeeded",
        "failed",
        "cancelled",
        "reconciliation_required",
    ]


def test_resource_status_values_match_design() -> None:
    assert {v.value for v in ResourceVerificationStatus} == {
        "verified_candidate",
        "unverified",
        "unavailable",
    }


def test_next_action_never_exposes_graph_nodes() -> None:
    """前端只拿稳定 next_action，**永不**看到图内部节点名。"""
    values = {v.value for v in AiRunNextAction}
    assert values == {"none", "review_draft", "retry", "reconcile", "wait"}
    forbidden = {"await_approval", "generate_outline", "repair_content", "save_draft_projection"}
    assert not (values & forbidden), "next_action 泄露了图内部节点名"


# ---------------------------------------------------------------------------
# 示例由 DTO 校验（B1 阶段用轻量结构断言代替完整 Pydantic 模型）
# ---------------------------------------------------------------------------


def test_examples_file_exists_and_is_valid_json() -> None:
    assert EXAMPLES.exists(), "缺少 contracts/examples/v1_examples.json"
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_error_body_example_has_required_fields() -> None:
    """错误体固定含 code / message / request_id / details。"""
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    body = data["error_body"]
    for field in ("code", "message", "request_id", "details"):
        assert field in body, f"错误体缺少 {field}"
    assert body["code"] in {c.value for c in ErrorCode}, "示例错误码必须是已知稳定码"


def test_run_view_examples_match_enum_values() -> None:
    """RunView 示例的 status / next_action 必须是合法枚举值。"""
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    valid_status = {v.value for v in AiRunStatus}
    valid_action = {v.value for v in AiRunNextAction}
    for key, value in data.items():
        if not key.startswith("run_view_"):
            continue
        assert value["status"] in valid_status, f"{key} 的 status 非法"
        assert value["next_action"] in valid_action, f"{key} 的 next_action 非法"
        assert isinstance(value["version"], int)


def test_error_body_example_reflects_expected_version() -> None:
    """版本冲突错误体必须能让前端区分「我拿的版本旧了」。"""
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    details = data["error_body"]["details"]
    assert "expected_version" in details and "actual_version" in details


# ---------------------------------------------------------------------------
# 错误码覆盖
# ---------------------------------------------------------------------------


def test_every_error_code_has_http_status() -> None:
    for code in ErrorCode:
        assert code in STATUS_BY_CODE, f"{code} 缺少 HTTP 状态映射"


def test_design_required_status_codes_present() -> None:
    """设计 §4：统一 400/401/403/404/409/422/429/503。"""
    statuses = set(STATUS_BY_CODE.values())
    missing = [s for s in (400, 401, 403, 404, 409, 422, 429, 503) if s not in statuses]
    assert not missing, f"缺少设计要求的 HTTP 状态：{missing}"
