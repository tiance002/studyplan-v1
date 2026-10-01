"""Manual practice proposals; exact plan identities, never implementation proof."""

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from app.core.errors import ValidationAppError
from app.core.ids import content_hash


def text(value, maximum, minimum=1):
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or len(value.strip()) < minimum
        or "\x00" in value
        or any(0xD800 <= ord(c) <= 0xDFFF for c in value)
    ):
        raise ValidationAppError("实践变更内容无效或超出限制")


@dataclass(frozen=True)
class KnowledgeChoice:
    node_id: str
    role: str

    def __post_init__(self):
        text(self.node_id, 512)
        if self.role not in {"core", "supporting", "extension"}:
            raise ValidationAppError("任务知识角色无效")


@dataclass(frozen=True)
class TaskChange:
    operation: str
    client_key: str
    task_id: str | None
    stage_id: str
    title: str
    goal: str
    in_scope: tuple[str, ...]
    out_scope: tuple[str, ...]
    acceptance: tuple[str, ...]
    knowledge_links: tuple[KnowledgeChoice, ...]

    def __post_init__(self):
        text(self.client_key, 128)
        text(self.stage_id, 512)
        text(self.title, 200)
        text(self.goal, 2000)
        if (
            self.operation not in {"update", "add"}
            or (self.operation == "update" and self.task_id is None)
            or (self.operation == "add" and self.task_id is not None)
        ):
            raise ValidationAppError("任务变更操作与任务标识不一致")
        if self.task_id is not None:
            text(self.task_id, 512)
        for values in (self.in_scope, self.out_scope, self.acceptance):
            if not 1 <= len(values) <= 20:
                raise ValidationAppError("任务范围和验收要求必须明确填写")
            for item in values:
                text(item, 2000)
        if (
            not 1 <= len(self.knowledge_links) <= 30
            or len({x.node_id for x in self.knowledge_links}) != len(self.knowledge_links)
            or not any(x.role == "core" for x in self.knowledge_links)
        ):
            raise ValidationAppError("每个任务必须选择至少一个核心知识，且不可重复")


@dataclass(frozen=True)
class PracticeChangeCommand:
    project_id: str
    plan_id: str
    practice_project_id: str
    title: str
    idea: str
    repo_url: str | None
    task_changes: tuple[TaskChange, ...]
    expected_version: int
    copy_policy: str
    idempotency_key: str

    def __post_init__(self):
        for value in (self.project_id, self.plan_id, self.practice_project_id):
            text(value, 512)
        text(self.title, 200)
        text(self.idea, 4000, 10)
        text(self.idempotency_key, 128)
        if (
            type(self.expected_version) is not int
            or self.expected_version < 1
            or self.copy_policy not in {"copy_active", "keep_history_only"}
        ):
            raise ValidationAppError("必须携带批准路线版本并明确私人资料策略")
        if (
            len(self.task_changes) > 30
            or len({t.client_key for t in self.task_changes}) != len(self.task_changes)
            or len({t.task_id for t in self.task_changes if t.task_id})
            != sum(t.task_id is not None for t in self.task_changes)
        ):
            raise ValidationAppError("任务变更数量超限或目标重复")
        if self.repo_url is not None:
            text(self.repo_url, 500)
            try:
                url = urlsplit(self.repo_url)
                if (
                    url.scheme not in {"http", "https"}
                    or not url.hostname
                    or url.username
                    or url.password
                    or any(c.isspace() or ord(c) < 32 for c in self.repo_url)
                ):
                    raise ValueError()
                _ = url.port
            except ValueError:
                raise ValidationAppError("仓库地址必须为无嵌入凭证的HTTP或HTTPS元数据") from None

    def input_hash(self):
        return content_hash({k: v for k, v in asdict(self).items() if k != "idempotency_key"})
