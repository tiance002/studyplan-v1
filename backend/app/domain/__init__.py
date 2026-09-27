"""domain：纯业务模型与规则。

约束：
- 不 import FastAPI / LangGraph / SQLAlchemy / 任何 SDK。
- 不感知 HTTP、DTO、数据库。
- 领域对象只表达业务不变量；持久化细节留在 infrastructure。
"""

from app.domain.enums import (
    AcceptanceConclusion,
    AiRunKind,
    AiRunNextAction,
    AiRunStatus,
    DraftDecision,
    EvidenceGrade,
    GraphName,
    KnowledgeNodeType,
    MediaType,
    OutlineSectionKind,
    PlanDraftStatus,
    PlanRevisionStatus,
    PracticeProjectStatus,
    PracticeTaskStatus,
    PreferenceMode,
    PreferenceScope,
    RelationType,
    ResourceProvenance,
    ResourceVerificationStatus,
    ReviewerKind,
    SummaryReviewConclusion,
    TaskKnowledgeRole,
    UnitProgress,
)

__all__ = [
    "AcceptanceConclusion",
    "AiRunKind",
    "AiRunNextAction",
    "AiRunStatus",
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
    "ResourceVerificationStatus",
    "ReviewerKind",
    "SummaryReviewConclusion",
    "TaskKnowledgeRole",
    "UnitProgress",
]
