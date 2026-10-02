"""Explicit user goal context and bounded, deterministic prerequisite expansion."""
from dataclasses import asdict, dataclass
from typing import Literal

from app.core.errors import ValidationAppError

Purpose = Literal["learn", "interview", "portfolio", "internship", "production"]
Depth = Literal["unspecified", "foundation", "applied", "deep"]


@dataclass(frozen=True)
class GoalSpec:
    target: str
    scope: tuple[str, ...] = ()
    desired_depth: Depth = "unspecified"
    starting_point: str = ""
    outcome_purpose: Purpose = "learn"
    constraints: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.target, str) or not self.target.strip() or len(self.target) > 2000:
            raise ValidationAppError("目标必须为1–2000字符")
        if not isinstance(self.starting_point, str) or len(self.starting_point) > 1000:
            raise ValidationAppError("起点描述最多1000字符")
        if self.desired_depth not in {"unspecified", "foundation", "applied", "deep"}:
            raise ValidationAppError("学习深度不合法")
        if self.outcome_purpose not in {"learn", "interview", "portfolio", "internship", "production"}:
            raise ValidationAppError("成果用途不合法")
        for name in ("scope", "constraints"):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or len(values) > 20:
                raise ValidationAppError("目标范围/限制最多20项")
            if any(not isinstance(v, str) or not v.strip() or len(v) > 300 for v in values):
                raise ValidationAppError("目标范围/限制每项必须为1–300字符")
            object.__setattr__(self, name, tuple(v.strip() for v in values))
        object.__setattr__(self, "target", self.target.strip())
        object.__setattr__(self, "starting_point", self.starting_point.strip())


def goal_spec_payload(spec):
    return asdict(spec) if spec is not None else None


def goal_spec_from_payload(raw):
    if raw is None or isinstance(raw, GoalSpec):
        return raw
    try:
        return GoalSpec(**raw)
    except (TypeError, ValueError) as exc:
        raise ValidationAppError("目标上下文结构不合法") from exc


def purpose_requirements(spec):
    if spec is None:
        return ()
    return {
        "learn": (),
        "interview": ("解释关键设计并比较一种替代方案", "记录一次失败、定位与修复", "完成2分钟项目说明"),
        "portfolio": ("保存可复现的项目演示与运行说明", "标明自己的实现范围、验证证据和已知限制"),
        "internship": ("提供他人可执行的运行、验证与交接说明", "记录问题定位、修复和协作边界"),
        "production": ("说明权限、成本和运行边界", "验证失败处理、观测与安全回退方式"),
    }[spec.outcome_purpose]


def required_module_closure(blueprints, roots, *, limit=200):
    if len(blueprints) > limit or not isinstance(roots, (tuple, list)):
        raise ValidationAppError("知识依赖展开超出范围")
    nodes = {n["stable_key"]: n for n in blueprints}
    if len(nodes) != len(blueprints):
        raise ValidationAppError("知识依赖存在重复键")
    active, done, result = set(), set(), []

    def visit(key):
        if key not in nodes:
            raise ValidationAppError("知识依赖引用未知模块")
        if key in active:
            raise ValidationAppError("知识依赖存在环")
        if key in done:
            return
        active.add(key)
        node = nodes[key]
        deps = list(node.get("prerequisite_keys") or [])
        if node.get("parent_key"):
            deps.append(node["parent_key"])
        for dependency in sorted(set(deps)):
            visit(dependency)
        active.remove(key)
        done.add(key)
        result.append(key)
        if len(result) > limit:
            raise ValidationAppError("知识依赖展开超出范围")

    for root in sorted(set(roots)):
        visit(root)
    return tuple(result)
