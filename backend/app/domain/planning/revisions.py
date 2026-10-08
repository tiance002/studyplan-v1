"""Bounded revision commands and exact, immutable history references.

The compiler remains the only execution producer. This module neither chooses
capabilities nor infers progress from names or treats completion as mastery.
"""

import json
from dataclasses import dataclass, replace

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash


@dataclass(frozen=True, slots=True)
class LocalStageEdit:
    stage_id: str
    title: str | None = None
    what_to_learn: str | None = None


def classify_change(*, change_text):
    if type(change_text) is not str or not change_text.strip() or len(change_text) > 10000:
        raise ValidationAppError("修改说明不能为空或过长")
    return {"status": "needs_clarification", "clarification_questions": [
        "请明确是调整未来阶段的说明或顺序，还是提交新的学习目标。"]}


def local_candidate(snapshot, stages, edits, *, stage_order=None, protected_stage_ids=()):
    """Only description fields and a complete permutation can be expressed."""
    by_id = {s.stage_id: s for s in stages}
    protected = set(protected_stage_ids)
    seen = set()
    for edit in edits:
        if type(edit) is not LocalStageEdit or edit.stage_id not in by_id or edit.stage_id in seen:
            raise ValidationAppError("阶段修改身份无效或重复")
        seen.add(edit.stage_id)
        prior = by_id[edit.stage_id]
        for value, limit in ((edit.title, 500), (edit.what_to_learn, 10000)):
            if value is not None and (type(value) is not str or not value.strip() or len(value) > limit):
                raise ValidationAppError("阶段说明不能为空或过长")
        updated = replace(prior, title=edit.title if edit.title is not None else prior.title,
            objective=edit.what_to_learn if edit.what_to_learn is not None else prior.objective)
        if updated != prior and edit.stage_id in protected:
            raise ValidationAppError("已开始或已完成的历史阶段不能修改")
        by_id[edit.stage_id] = updated
    order = tuple(s.stage_id for s in stages) if stage_order is None else tuple(stage_order)
    if len(order) != len(stages) or set(order) != set(by_id):
        raise ValidationAppError("局部排序必须保留全部阶段及required outcomes")
    result = tuple(replace(by_id[key], order_index=index) for index, key in enumerate(order))
    previous = {s.stage_id: s for s in stages}
    if any(previous[s.stage_id] != s for s in result if s.stage_id in protected):
        raise ValidationAppError("已开始的历史前缀不能重排")
    if result == tuple(stages):
        raise ValidationAppError("修改没有改变未来阶段")
    return result


@dataclass(frozen=True, slots=True)
class V2RevisionContext:
    """Hash-bound basis consumed by preview, recovery and atomic publication."""
    _json: str

    @classmethod
    def create(cls, **facts):
        raw = {"version": "V2RevisionContextV1", **facts}
        raw["context_hash"] = content_hash(raw)
        return cls.from_payload(raw)

    @classmethod
    def from_payload(cls, raw):
        if raw is None:
            return None
        fields = {"version", "change_kind", "actor_id", "project_id", "base_plan_id", "base_revision",
            "base_structure_hash", "base_execution_manifest_hash", "progress_basis", "change_diff", "lineage",
            "approved_goal_spec", "budget_root_run_id", "input_hash", "context_hash"}
        try:
            if (type(raw) is not dict or set(raw) != fields or raw["version"] != "V2RevisionContextV1"
                    or raw["change_kind"] not in {"local", "semantic"}
                    or type(raw["base_revision"]) is not int or raw["base_revision"] < 1
                    or any(type(raw[k]) is not str or not raw[k] for k in (
                        "actor_id", "project_id", "base_plan_id", "base_structure_hash", "base_execution_manifest_hash", "input_hash"))
                    or raw["context_hash"] != content_hash({k: v for k, v in raw.items() if k != "context_hash"})
                    or type(raw["progress_basis"]) is not dict
                    or raw["progress_basis"]["basis_hash"] != content_hash({k: v for k, v in raw["progress_basis"].items() if k != "basis_hash"})
                    or type(raw["lineage"]) is not list or type(raw["change_diff"]) is not dict
                    or raw["change_kind"] == "local" and raw["approved_goal_spec"] is not None
                    or raw["change_kind"] == "semantic" and (not raw["approved_goal_spec"] or not raw["budget_root_run_id"])):
                raise ValueError()
            for ref in raw["lineage"]:
                if set(ref) != {"source_plan_id", "source_revision", "source_stage_id", "source_stable_key",
                    "source_stage_hash", "learning_status", "target_stable_key"}:
                    raise ValueError()
                if ref["source_plan_id"] != raw["base_plan_id"] or ref["source_revision"] != raw["base_revision"]:
                    raise ValueError()
                if ref["learning_status"] not in {"completed", "started", "future"}:
                    raise ValueError()
            return cls(canonical_json(raw))
        except (TypeError, ValueError, KeyError):
            raise ValidationAppError("V2 revision basis shape or digest rejected") from None

    def to_payload(self):
        return json.loads(self._json)

    def user_content(self, *, execution=None):
        raw = self.to_payload()
        facts = {s["stage_id"]: s for s in raw["progress_basis"]["stages"]}
        history = []
        for ref in raw["lineage"]:
            fact = facts[ref["source_stage_id"]]
            historical = fact.get("history_source")
            source = historical or ref
            history.append({"source_plan_id": source["source_plan_id"], "source_revision": source["source_revision"],
                "stage_id": source["source_stage_id"], "stable_key": ref["source_stable_key"],
                "learning_status": (fact["historical_learning_status"] if historical else ref["learning_status"]),
                "target_stable_key": ref["target_stable_key"], "progress_inherited": False})
        seen = {(h["source_plan_id"], h["stage_id"]) for h in history}
        for ancestor in raw["progress_basis"].get("ancestor_bases", []):
            for fact in ancestor["stages"]:
                key = (ancestor["plan_id"], fact["stage_id"])
                if key not in seen and fact["learning_status"] != "future":
                    history.append({"source_plan_id": ancestor["plan_id"], "source_revision": ancestor["revision"],
                        "stage_id": fact["stage_id"], "stable_key": fact["stable_key"],
                        "learning_status": fact["learning_status"], "target_stable_key": None, "progress_inherited": False})
                    seen.add(key)
        changes = raw["change_diff"]
        if raw["change_kind"] == "semantic" and execution is not None:
            after = execution_facts(execution)
            before = changes["before"]
            changes = {**changes, "after": after, "added_stages": after["stages"],
                "removed_stages": [s for s in before["stages"] if not s["protected"]],
                "preserved_stages": [s for s in before["stages"] if s["protected"]],
                "outcomes_changed": before["outcomes"] != after["outcomes"],
                "prerequisites_changed": before["prerequisites"] != after["prerequisites"],
                "materials_changed": before["materials"] != after["materials"],
                "practice_changed": before["practice"] != after["practice"], "unresolved": after["unresolved"]}
        return {"change_kind": raw["change_kind"], "base_revision": raw["base_revision"],
            "changes": changes, "history": history,
            "history_policy": "历史成果保留在原版本；新版本不自动继承学习进度或掌握状态。"}


def execution_facts(execution, *, progress=None):
    """Display exact Compiler facts; no matching or transfer of progress by name."""
    compiled = execution.to_payload()["compiled"]
    protected = {s["stable_key"]: s["protected"] for s in progress["stages"]} if progress else {}
    stages = [{**s, "protected": protected.get(s["stable_key"], False)} for s in compiled["stages"]]
    return {"stages": stages, "outcomes": [{"capability_id": c["capability_id"], "outcomes": c["outcomes"]}
        for c in compiled["source_snapshots"]["curriculum_context"]["capabilities"]],
        "prerequisites": [{"stage_id": s["stage_id"], "prerequisite_stage_refs": s["prerequisite_stage_refs"]} for s in stages],
        "materials": compiled["resource_assignments"], "practice": compiled["practice"], "unresolved": compiled["unresolved"]}
