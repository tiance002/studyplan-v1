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

    @property
    def mcp_outcome_rule(self):
        return {"practice_outcome_id": "mcp.minimal_connection",
                "required_for_route_kinds": ["systematic_agent_route"],
                "required_for_depths": ["applied", "deep"], "concept_only_depth": "foundation",
                "project_usage_not_forced": True}

    def outcomes_for(self, definition, *, route_kind, desired_depth):
        if definition.capability_id != "mcp":
            return definition.learning_outcomes
        rule = self.mcp_outcome_rule
        if (route_kind in rule["required_for_route_kinds"] or desired_depth in rule["required_for_depths"]
                or desired_depth != rule["concept_only_depth"]):
            return definition.learning_outcomes
        return tuple(o for o in definition.learning_outcomes if o.outcome_id != rule["practice_outcome_id"])

    def to_payload(self):
        return json.loads(canonical_json({"policy_version": self.version, "definitions": [asdict(d) for d in self.definitions],
                "outcome_selection": {"mcp": self.mcp_outcome_rule},
                "systematic_agent_rule": {"route_kind": "systematic_agent_route",
                    "required_capability_id": "mcp", "policy_ref": self.systematic_mcp_policy_ref,
                    "project_usage_not_forced": True}}))


def _definition(key, title, outcomes, *, prerequisites=(), depth="applied"):
    return CapabilityDefinition(key, title,
        tuple(LearningOutcome(f"{key}.{suffix}", text) for suffix, text in outcomes),
        tuple(prerequisites), depth, (f"capability-policy:v2#{key}",))


CAPABILITY_POLICY = CapabilityPolicy("v2", (
    _definition("python.core", "Python编程基础", (("program_structure", "使用函数组织Python程序"),
                ("data_structures", "使用Python数据结构表达和处理数据"),
                ("exceptions", "使用Python异常表达和处理程序错误")), depth="foundation"),
    _definition("python.async", "Python异步并发", (("concurrency", "组织协程并发执行"),
                ("cancellation_lifecycle", "管理协程取消与生命周期收尾")),
                prerequisites=("python.core",), depth="deep"),
    _definition("json.cli", "Python JSON文件CLI", (("file_reading", "读取并解析JSON文件"),
                ("content_validation", "校验JSON文件内容是否满足输入合同"),
                ("cli_errors", "通过CLI错误信息和退出状态表达文件处理失败")),
                prerequisites=("python.core",)),
    _definition("llm.api", "LLM API基础", (("exchange", "组织模型API请求并读取模型响应"),
                ("usage_cost", "读取模型请求usage并理解费用边界"),
                ("failure_boundary", "识别模型请求失败、截断与结果未知的边界"))),
    _definition("structured.output", "模型结构化输出", (("contract_definition", "定义模型结构化输出合同"),
                ("response_validation", "按输出合同校验模型JSON响应")),
                prerequisites=("llm.api",)),
    _definition("tool.calling", "Tool Calling", (("input_validation", "按工具输入合同校验调用参数"),
                ("invoke_result", "派发有效工具请求并处理调用结果")),
                prerequisites=("llm.api",)),
    _definition("agent.loop", "工具型Agent循环", (("advance", "根据模型与工具结果推进调用循环"),
                ("stop_conditions", "设置并执行Agent循环的终止条件"),
                ("failure_result", "处理Agent循环失败并返回明确失败结果")),
                prerequisites=("tool.calling",)),
    _definition("mcp", "MCP协议与集成边界", (("roles", "解释MCP Client与Server的职责及协作方式"),
                ("interfaces", "区分MCP Tool与Resource协议接口的边界"),
                ("minimal_connection", "完成有界的MCP最小接入并验证一次工具调用结果"))),
    _definition("error.permission", "错误与权限边界", (("denial", "区分输入错误、权限拒绝、执行失败与未知结果"),)),
    _definition("eval.lite", "Eval-Lite", (("cases", "用可检查案例验证目标行为和失败分支"),)),
    _definition("github.api", "GitHub API集成", (("objects", "处理GitHub API对象与响应"),
                ("pagination", "处理GitHub API分页数据"),
                ("access_failures", "处理GitHub API权限拒绝与访问失败"))),
    _definition("code.review", "代码审查依据", (("evidence", "将Review结论关联到代码上下文与可检查依据"),)),
))
