"""runs 领域：**对外运行状态投影**（``ai_runs``）。

设计定位（SOFTWARE_DESIGN.md §4「三份状态」）：

===========================  ==================================================
状态                          权威来源
===========================  ==================================================
业务事实                      领域表（``plan_drafts`` / ``plan_revisions`` ...）
图断点                        Checkpointer（thread_id → checkpoint）
**对外运行状态**              ``ai_runs`` 投影（本模块）
===========================  ==================================================

``ai_runs`` **不是**业务事实，也不是断点。它只回答前端需要的三个问题：
「跑到哪了（status）」「我该做什么（next_action）」「拿什么结果（result_ref）」。
因此它**不暴露**任何图内部节点名（``next_action`` 是稳定闭集）。

``version`` 用于乐观并发：同一 run 的状态被外部改写后，旧版本的视图必须能被识别。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.errors import ConflictError, ValidationAppError
from app.domain.enums import AiRunNextAction, AiRunStatus

#: ``next_action`` 与 ``status`` 的**唯一**合法组合（不得出现「等用户」却没有动作）。
_ALLOWED_NEXT_ACTIONS: dict[AiRunStatus, frozenset[AiRunNextAction]] = {
    AiRunStatus.QUEUED: frozenset({AiRunNextAction.WAIT}),
    AiRunStatus.RUNNING: frozenset({AiRunNextAction.WAIT}),
    AiRunStatus.WAITING_USER: frozenset({AiRunNextAction.REVIEW_DRAFT}),
    AiRunStatus.SUCCEEDED: frozenset({AiRunNextAction.NONE}),
    AiRunStatus.FAILED: frozenset({AiRunNextAction.RETRY, AiRunNextAction.NONE}),
    AiRunStatus.CANCELLED: frozenset({AiRunNextAction.NONE}),
    AiRunStatus.RECONCILIATION_REQUIRED: frozenset({AiRunNextAction.RECONCILE}),
}


@dataclass(frozen=True, slots=True)
class RunRecord:
    """一次运行的对外投影。"""

    run_id: str
    actor_id: str
    project_id: str
    kind: str
    graph_name: str
    graph_version: str
    status: AiRunStatus
    next_action: AiRunNextAction
    version: int = 1
    thread_id: str = ""
    result_ref: str | None = None
    error_class: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.run_id or not self.project_id or not self.actor_id:
            raise ValidationAppError("运行记录缺少 run_id / project_id / actor_id")
        allowed = _ALLOWED_NEXT_ACTIONS.get(self.status, frozenset())
        if self.next_action not in allowed:
            raise ValidationAppError(
                f"运行状态 {self.status} 不允许 next_action={self.next_action}"
            )
        if self.version < 1:
            raise ValidationAppError("运行版本号必须从 1 开始")

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            AiRunStatus.SUCCEEDED,
            AiRunStatus.FAILED,
            AiRunStatus.CANCELLED,
        }

    def require_expected_version(self, expected: int) -> None:
        if expected != self.version:
            raise ConflictError(
                "运行状态已变化，请刷新后重试",
                reason="run_version_mismatch",
                expected_version=expected,
                actual_version=self.version,
            )


__all__ = ["RunRecord"]
