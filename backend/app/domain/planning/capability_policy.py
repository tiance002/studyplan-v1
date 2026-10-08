"""Small versioned capability definitions, not a route or curriculum selector."""
import json
from dataclasses import asdict, dataclass

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json


@dataclass(frozen=True, slots=True)
class LearningOutcome:
    outcome_id: str
    text: str

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in (self.outcome_id, self.text)):
            raise ValidationAppError("能力outcome定义不合法")


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    capability_id: str
    title: str
    learning_outcomes: tuple[LearningOutcome, ...]
    real_prerequisites: tuple[str, ...]
    default_depth: str
    policy_refs: tuple[str, ...]

    def __post_init__(self):
        for key in ("learning_outcomes", "real_prerequisites", "policy_refs"):
            object.__setattr__(self, key, tuple(getattr(self, key)))
        if (not isinstance(self.capability_id, str) or not self.capability_id.strip()
                or len(self.capability_id) > 128 or not isinstance(self.title, str) or not self.title.strip()
                or self.default_depth not in {"foundation", "applied", "deep"}
                or not self.learning_outcomes or len(self.learning_outcomes) > 20
                or any(not isinstance(o, LearningOutcome) for o in self.learning_outcomes)):
            raise ValidationAppError("能力定义不合法")
        for values in (self.real_prerequisites, self.policy_refs):
            if len(values) > 20 or any(not isinstance(v, str) or not v.strip() or len(v) > 200 for v in values):
                raise ValidationAppError("能力定义引用不合法")
            if len(values) != len(set(values)):
                raise ValidationAppError("能力定义引用重复")


@dataclass(frozen=True, slots=True)
class CapabilityPolicy:
    version: str
    definitions: tuple[CapabilityDefinition, ...]

    def __post_init__(self):
        object.__setattr__(self, "definitions", tuple(self.definitions))
        if not isinstance(self.version, str) or not self.version:
            raise ValidationAppError("能力Policy版本不合法")
        ids = [d.capability_id for d in self.definitions]
        outcomes = [o.outcome_id for d in self.definitions for o in d.learning_outcomes]
        if len(ids) != len(set(ids)) or len(outcomes) != len(set(outcomes)):
            raise ValidationAppError("能力Policy定义身份重复")
        if any(p not in ids or p == d.capability_id for d in self.definitions for p in d.real_prerequisites):
            raise ValidationAppError("能力Policy前置引用不合法")

    @property
    def systematic_mcp_policy_ref(self):
        return f"capability-policy:{self.version}#systematic-agent-mcp"

    def get(self, capability_id):
        return next((d for d in self.definitions if d.capability_id == capability_id), None)

    def to_payload(self):
        return json.loads(canonical_json({"policy_version": self.version, "definitions": [asdict(d) for d in self.definitions],
                "systematic_agent_rule": {"route_kind": "systematic_agent_route",
                    "required_capability_id": "mcp", "policy_ref": self.systematic_mcp_policy_ref,
                    "project_usage_not_forced": True}}))


def _definition(key, title, outcomes, *, prerequisites=(), depth="applied"):
    return CapabilityDefinition(key, title,
        tuple(LearningOutcome(f"{key}.{suffix}", text) for suffix, text in outcomes),
        tuple(prerequisites), depth, (f"capability-policy:v1#{key}",))


CAPABILITY_POLICY = CapabilityPolicy("v1", (
    _definition("python.core", "Python编程基础", (("functions", "使用函数、数据结构和异常组织程序"),), depth="foundation"),
    _definition("python.async", "Python异步并发", (("cancellation", "管理协程、并发和取消生命周期"),),
                prerequisites=("python.core",), depth="deep"),
    _definition("json.cli", "Python JSON文件CLI", (("io", "实现JSON文件读取、校验与CLI错误处理"),),
                prerequisites=("python.core",)),
    _definition("llm.api", "LLM API基础", (("request", "组织模型请求并理解响应、费用与失败边界"),)),
    _definition("structured.output", "模型结构化输出", (("validation", "定义模型输出合同并校验JSON响应"),),
                prerequisites=("llm.api",)),
    _definition("tool.calling", "Tool Calling", (("dispatch", "按工具合同校验参数并派发调用"),),
                prerequisites=("llm.api",)),
    _definition("agent.loop", "工具型Agent循环", (("termination", "组织工具调用循环、终止条件与失败返回"),),
                prerequisites=("tool.calling",)),
    _definition("mcp", "MCP协议与集成边界", (("protocol", "解释MCP客户端、服务端和工具协议边界"),)),
    _definition("error.permission", "错误与权限边界", (("denial", "区分输入错误、权限拒绝、执行失败与未知结果"),)),
    _definition("eval.lite", "Eval-Lite", (("cases", "用可检查案例验证目标行为和失败分支"),)),
    _definition("github.api", "GitHub API集成", (("scope", "处理GitHub API对象、分页、权限与失败"),)),
    _definition("code.review", "代码审查依据", (("evidence", "将Review结论关联到代码上下文与可检查依据"),)),
))
