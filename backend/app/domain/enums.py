"""跨域共享的状态枚举与产品用语。

这些枚举是**契约的一部分**：改值等于破坏 API 与前端。
新增值需要同步 OpenAPI、fixtures 与双方测试。

设计要点（见 SOFTWARE_DESIGN.md §8）：
- 每个枚举都对应一句「防止误读」的注释，避免把不同语义的状态混为一谈。
"""

from __future__ import annotations

from enum import StrEnum


class UnitProgress(StrEnum):
    """学习单元的进度状态。

    注意：``SKIPPED`` ≠ ``COMPLETED``，二者都不代表掌握。
    """

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


#: 允许的进度迁移。终态可回退到学习（用户可返回已跳过/已完成单元）。
UNIT_PROGRESS_TRANSITIONS: dict[UnitProgress, frozenset[UnitProgress]] = {
    UnitProgress.NOT_STARTED: frozenset(
        {UnitProgress.IN_PROGRESS, UnitProgress.COMPLETED, UnitProgress.SKIPPED}
    ),
    UnitProgress.IN_PROGRESS: frozenset(
        {UnitProgress.COMPLETED, UnitProgress.SKIPPED, UnitProgress.NOT_STARTED}
    ),
    UnitProgress.COMPLETED: frozenset(
        {UnitProgress.IN_PROGRESS, UnitProgress.SKIPPED, UnitProgress.NOT_STARTED}
    ),
    UnitProgress.SKIPPED: frozenset(
        {UnitProgress.IN_PROGRESS, UnitProgress.NOT_STARTED, UnitProgress.COMPLETED}
    ),
}


def can_transition_progress(current: UnitProgress, target: UnitProgress) -> bool:
    return target in UNIT_PROGRESS_TRANSITIONS[current]


class SummaryReviewConclusion(StrEnum):
    """总结评审结论。

    仅说明**本次提交与 rubric 的符合情况**，不是对用户能力的评价，
    也不改变单元进度。
    """

    SATISFIED = "satisfied"
    NEEDS_REVISION = "needs_revision"
    MISCONCEPTION = "misconception"


class PracticeTaskStatus(StrEnum):
    """实践任务状态。

    ``PROMPT_REVIEWED`` 只表示实现思路通过评审，
    **不等于**真实功能已被验收。
    """

    PENDING = "pending"
    DESIGNING = "designing"
    PROMPT_REVIEWED = "prompt_reviewed"
    IMPLEMENTING = "implementing"
    AWAITING_EVIDENCE = "awaiting_evidence"
    ACCEPTED = "accepted"
    SKIPPED = "skipped"


class EvidenceGrade(StrEnum):
    """证据等级：明确平台到底验证了什么。"""

    VERIFIED = "verified"          # 平台实际可核验（如可访问的提交、可复现日志）
    REPORTED = "reported"          # 用户自述或外部报告，未经平台核验
    INSUFFICIENT = "insufficient"  # 证据不足，无法支撑结论


class AcceptanceConclusion(StrEnum):
    """成果验收结论。"""

    ACCEPTED = "accepted"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    NOT_PASSED = "not_passed"


class ReviewerKind(StrEnum):
    """谁给出了这次评审/验收结论。"""

    USER = "user"
    MODEL = "model"
    SYSTEM = "system"


class AiRunStatus(StrEnum):
    """对外可授权的运行状态。

    图跑成功 **不自动等于**知识已学会、任务已验收。
    """

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECONCILIATION_REQUIRED = "reconciliation_required"


#: 终态：不可再迁移。
AI_RUN_TERMINAL_STATES: frozenset[AiRunStatus] = frozenset(
    {AiRunStatus.SUCCEEDED, AiRunStatus.FAILED, AiRunStatus.CANCELLED}
)


class AiRunNextAction(StrEnum):
    """前端据此渲染下一步按钮。前端**永不**看到图内部节点名。"""

    NONE = "none"
    REVIEW_DRAFT = "review_draft"          # waiting_user：等待确认草案
    RETRY = "retry"                        # failed 且可安全重试
    RECONCILE = "reconcile"                # 结果未知，需人工核对
    WAIT = "wait"                          # 仍在队列/执行中


class ResourceVerificationStatus(StrEnum):
    """资源状态。

    三条独立维度：可达性 / 内容覆盖 / 教学质量。
    本枚举只表达平台对该 FURL 的核验程度，不代表教学质量评分。
    """

    VERIFIED_CANDIDATE = "verified_candidate"
    UNVERIFIED = "unverified"
    UNAVAILABLE = "unavailable"


class AiRunKind(StrEnum):
    """run 的业务语义，决定 worker 该驱动哪张图。"""

    PLAN_GENERATE = "plan_generate"
    PLAN_APPROVE = "plan_approve"
    SUMMARY_REVIEW = "summary_review"
    PROMPT_REVIEW = "prompt_review"


class GraphName(StrEnum):
    PLANNING = "planning_graph"
    SUMMARY_REVIEW = "summary_review_graph"
    PROMPT_REVIEW = "prompt_review_graph"


class PlanRevisionStatus(StrEnum):
    """计划版本状态。只有 APPROVED/CURRENT 的版本是正式路线。"""

    DRAFT = "draft"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class PlanDraftStatus(StrEnum):
    """草案状态。草案永不可直接覆盖正式路线。"""

    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED_VALIDATION = "failed_validation"


class DraftDecision(StrEnum):
    """等待用户时的三种决定。"""

    APPROVE = "approve"
    EDIT = "edit"
    CANCEL = "cancel"


class MediaType(StrEnum):
    TEXT = "text"
    VIDEO = "video"
    INTERACTIVE = "interactive"
    REPO = "repo"
    COURSE = "course"


class PreferenceMode(StrEnum):
    """资源形态偏好。"""

    TEXT_FIRST = "text_first"
    VIDEO_FIRST = "video_first"
    MIXED = "mixed"
    BOTH = "both"


class PreferenceScope(StrEnum):
    """偏好优先级：节点 > 单元 > 学习空间默认 > 系统默认。"""

    SYSTEM = "system"
    PROJECT = "project"
    UNIT = "unit"
    NODE = "node"


#: 数值越大优先级越高。
PREFERENCE_SCOPE_RANK: dict[PreferenceScope, int] = {
    PreferenceScope.SYSTEM: 0,
    PreferenceScope.PROJECT: 1,
    PreferenceScope.UNIT: 2,
    PreferenceScope.NODE: 3,
}


class RelationType(StrEnum):
    """知识关系。``PREREQUISITE`` 构成的图必须无环。"""

    PREREQUISITE = "prerequisite"
    CONTAINS = "contains"
    RELATED = "related"
    ALTERNATIVE = "alternative"


class KnowledgeNodeType(StrEnum):
    """知识节点粒度。"""

    CONCEPT = "concept"
    SKILL = "skill"
    TOOL = "tool"
    PATTERN = "pattern"
    DOMAIN = "domain"


class TaskKnowledgeRole(StrEnum):
    """任务与知识节点的关系强度。"""

    CORE = "core"
    SUPPORTING = "supporting"
    EXTENSION = "extension"


class OutlineSectionKind(StrEnum):
    """纲要分节类型。"""

    FOUNDATION = "foundation"
    CORE = "core"
    PRACTICE = "practice"
    ADVANCED = "advanced"


class PracticeProjectStatus(StrEnum):
    """实践项目状态。与学习空间（LearningProject）不是同一概念。"""

    IDEA = "idea"
    SCOPED = "scoped"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ResourceProvenance(StrEnum):
    """资源出处。``OFFICIAL`` 必须能给出官方来源证据。"""

    OFFICIAL = "official"
    COMMUNITY = "community"
    USER_PROVIDED = "user_provided"
    CURATED_POOL = "curated_pool"
    GITHUB_CANDIDATE = "github_candidate"
    SEARCH_CANDIDATE = "search_candidate"


class DomainPackStatus(StrEnum):
    """领域内容包状态。发布版只读；V1 从仓库内审核过的文件加载。

    不是服务、不是第二套业务规则 —— 只是**策划配置输入**。
    """

    DRAFT = "draft"
    PUBLISHED = "published"


class StageResourceRole(StrEnum):
    """阶段与资源的关系角色（设计 §2.2）。

    每阶段默认一条 ``PRIMARY`` 主线；``SUPPLEMENT`` 补充前置，
    ``REFERENCE`` 为对照/延伸。**不计算章节重叠率或覆盖率。**
    """

    PRIMARY = "primary"
    SUPPLEMENT = "supplement"
    REFERENCE = "reference"


class ResourceSourceVisibility(StrEnum):
    """公共资源来源可见性。V1 只支持平台维护/审核的 ``CURATED``。

    公共源可跨用户读，但**只有**管理员/受审核流程可写；
    个人私有资源记录另设，不与公共源混表。
    """

    CURATED = "curated"


__all__ = [
    "AI_RUN_TERMINAL_STATES",
    "PREFERENCE_SCOPE_RANK",
    "UNIT_PROGRESS_TRANSITIONS",
    "AcceptanceConclusion",
    "AiRunKind",
    "AiRunNextAction",
    "AiRunStatus",
    "DomainPackStatus",
    "DraftDecision",
    "EvidenceGrade",
    "GraphName",
    "KnowledgeNodeType",
    "MediaType",
    "OutlineSectionKind",
    "PlanDraftStatus",
    "PlanRevisionStatus",
    "PracticeProjectStatus",
    "PracticeTaskStatus",
    "PreferenceMode",
    "PreferenceScope",
    "RelationType",
    "ResourceProvenance",
    "ResourceSourceVisibility",
    "ResourceVerificationStatus",
    "ReviewerKind",
    "StageResourceRole",
    "SummaryReviewConclusion",
    "TaskKnowledgeRole",
    "UnitProgress",
    "can_transition_progress",
]
