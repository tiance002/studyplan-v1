"""Bounded learning instructions carried by the existing plan version snapshot.

Relations and source slices come from curated input, never inferred mastery.
"""
from dataclasses import asdict, dataclass, replace
from typing import Literal
from urllib.parse import urlsplit

from app.core.errors import ValidationAppError


def _text(value: str, name: str, limit: int = 1200) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValidationAppError(f"学习指导 {name} 必须是有界非空文本")


def _items(values: tuple[str, ...], name: str, *, required: bool = False) -> None:
    if not isinstance(values, (tuple, list)) or len(values) > 20 or (required and not values):
        raise ValidationAppError(f"学习指导 {name} 列表超出范围")
    for value in values:
        _text(value, name, 1000)


def _sequence(value):
    if not isinstance(value, (tuple, list)):
        raise ValidationAppError("学习指导需要列表，不能将文本拆成字符")
    return tuple(value)


@dataclass(frozen=True)
class PracticeDelta:
    baseline: str
    increment: tuple[str, ...]
    preserved: tuple[str, ...]
    validation: tuple[str, ...]
    reuse: tuple[str, ...]

    def __post_init__(self):
        _text(self.baseline, "baseline")
        for name in ("increment", "preserved", "validation", "reuse"):
            _items(getattr(self, name), name, required=True)


@dataclass(frozen=True)
class SourceSlice:
    repo_url: str
    ref: str
    files: tuple[str, ...]
    call_chain: tuple[str, ...]
    questions: tuple[str, ...]
    optional: bool = True
    verification_status: Literal["suggested", "reviewed"] = "suggested"

    def __post_init__(self):
        _text(self.repo_url, "repo_url", 500)
        try:
            url = urlsplit(self.repo_url)
            parts = url.path.strip("/").split("/")
            valid = (url.scheme == "https" and url.netloc == "github.com" and len(parts) == 2
                     and all(parts) and not url.query and not url.fragment
                     and all(c.isalnum() or c in "-._/" for c in url.path))
        except ValueError:
            valid = False
        if not valid:
            raise ValidationAppError("源码切片只接受公开 GitHub 仓库入口")
        _text(self.ref, "ref", 200)
        _items(self.files, "files")
        _items(self.call_chain, "call_chain", required=True)
        _items(self.questions, "questions", required=True)
        if self.verification_status not in {"suggested", "reviewed"} or type(self.optional) is not bool:
            raise ValidationAppError("源码切片状态不合法")
        if self.verification_status == "reviewed" and not self.files:
            raise ValidationAppError("已审核源码切片必须列出读取文件")


@dataclass(frozen=True)
class LearningGuidance:
    why_now: str
    previous_relation: str
    learning_focus: tuple[str, ...]
    comparison_focus: tuple[str, ...]
    practice_delta: PracticeDelta
    source_slice: SourceSlice | None = None
    exposure_relation: Literal["review", "compare", "deepen", "version_context", "unknown"] = "unknown"
    knowledge_keys: tuple[str, ...] = ()

    def __post_init__(self):
        _text(self.why_now, "why_now")
        _text(self.previous_relation, "previous_relation")
        _items(self.learning_focus, "learning_focus", required=True)
        _items(self.comparison_focus, "comparison_focus")
        _items(self.knowledge_keys, "knowledge_keys")
        if self.exposure_relation not in {"review", "compare", "deepen", "version_context", "unknown"}:
            raise ValidationAppError("学习指导关系不合法")
        if self.exposure_relation == "compare" and not self.comparison_focus:
            raise ValidationAppError("对比学习必须给出具体问题")


def guidance_from_payload(raw) -> LearningGuidance | None:
    if raw is None:
        return None
    if isinstance(raw, LearningGuidance):
        return raw
    try:
        data = dict(raw)
        delta = dict(data.pop("practice_delta"))
        practice = PracticeDelta(**{**delta, **{k: _sequence(delta[k]) for k in ("increment", "preserved", "validation", "reuse")}})
        source = data.pop("source_slice", None)
        if source is not None:
            source = SourceSlice(**{**source, **{k: _sequence(source[k]) for k in ("files", "call_chain", "questions")}})
        return LearningGuidance(**{**data, "practice_delta": practice, "source_slice": source,
                                   **{k: _sequence(data.get(k, ())) for k in ("learning_focus", "comparison_focus", "knowledge_keys")}})
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationAppError("学习指导结构不合法") from exc


def guidance_payload(guide: LearningGuidance | None):
    return asdict(guide) if guide is not None else None


def changed_practice_guidance(guide, tasks):
    if guide is None:
        return None

    def bounded(values):
        # Full requirements remain on the tasks; guidance is a bounded summary.
        items = [v if len(v) <= 1000 else v[:970] + "…（完整要求见任务）" for v in values]
        return tuple(items if len(items) <= 20 else items[:19] + ["其余要求请查看本阶段当前版本的实践任务"])

    return replace(guide, exposure_relation="unknown", comparison_focus=(), source_slice=None,
                   practice_delta=PracticeDelta(
                       baseline="沿用当前项目基线；本版本已调整实践设计，旧成果保留为历史资料",
                       increment=bounded([f"{t['title']}：{t['goal']}" for t in tasks]) or ("核对当前版本的实践方向",),
                       preserved=("保留未变更的功能；按新任务范围检查兼容性",),
                       validation=bounded([a for t in tasks for a in t['acceptance']]) or ("核对当前版本任务要求",),
                       reuse=("保存新任务成果与验证记录；不继承旧任务 accepted 状态",)))


def changed_resource_guidance(guide):
    if guide is None:
        return None
    return replace(guide, exposure_relation="unknown", comparison_focus=(), source_slice=None,
                   previous_relation="本版本主线已更换，旧教程的复习、对比与深入关系需要重新核对；旧历史继续保留。")


def stage_guidance(pack, stage, previous_stage=None):
    """Use curated relationships; legacy packs get honest, bounded instructions."""
    supplied = stage.get("learning_guidance")
    if supplied is not None:
        guide = guidance_from_payload(supplied)
        allowed = {n["stable_key"] for n in pack.get("knowledge_blueprints", [])}
        if guide is not None and any(key not in allowed for key in guide.knowledge_keys):
            raise ValidationAppError("学习指导引用未知知识键")
        return guide
    practice = next((p for p in pack.get("practice_blueprints", []) if p.get("section_key") == stage["stable_key"]), {})
    previous = next((p for p in pack.get("practice_blueprints", []) if previous_stage and p.get("section_key") == previous_stage["stable_key"]), {})
    return LearningGuidance(
        why_now=stage.get("objective") or f"建立 {stage['title']} 的必要基础，并通过本阶段实践检验实现。",
        previous_relation="模板未预置与先前教程的关系；按自己的经历复习，本说明不推断已经掌握。",
        learning_focus=(stage.get("objective") or stage["title"],), comparison_focus=(),
        knowledge_keys=tuple(stage.get("node_keys") or ()),
        practice_delta=PracticeDelta(
            baseline=previous.get("title") or "从当前已有项目或必要环境开始，先确认可运行基线",
            increment=(practice.get("goal") or stage.get("objective") or stage["title"],),
            preserved=("保留已有可运行行为；新增能力不覆盖旧成果",),
            validation=tuple(practice.get("acceptance") or ("依据本阶段任务的已保存验收要求验证",)),
            reuse=("保留本阶段成果与验证记录，供后续任务引用",)),
    )
