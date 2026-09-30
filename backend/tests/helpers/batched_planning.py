"""Deterministic per-batch Fake used by the batched-protocol tests.

The real provider port only dispatches ``planning.outline``/``planning.structure``/
``planning.practice``/``planning.repair`` one request at a time. This Fake mirrors
that contract: it answers a *single local batch payload* and records every call so
tests can assert exact request counts and stop behaviour.

It can inject two failure shapes at an exact 1-based occurrence of a purpose:

- ``fail_at``   -> a truncated (``provider_output_truncated``) ``LLMFailure``; the
  graph must stop immediately and never repair a length failure.
- ``invalid_at``-> a syntactically valid but semantically invalid payload; the graph
  may repair it within the shared two-repair budget.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.ports.llm import LLMFailure, LLMResult

OUTLINE = "planning.outline"
STRUCTURE = "planning.structure"
PRACTICE = "planning.practice"
REPAIR = "planning.repair"


class ScriptedLLM:
    """Per-batch deterministic Fake with precise failure injection."""

    def __init__(
        self,
        pack: dict[str, Any],
        *,
        fail_at: tuple[str, int] | None = None,
        invalid_at: tuple[str, int] | None = None,
        persistent_invalid: tuple[str, int] | None = None,
        empty_at: tuple[str, int] | None = None,
        empty_practice_stages: tuple[str, ...] = (),
        forged_node_key: str | None = None,
        forged_resource_stage: str | None = None,
    ) -> None:
        self.pack = pack
        self.fail_at = fail_at
        #: Semantically invalid but non-empty content -> repair candidate.
        self.invalid_at = invalid_at
        #: Same occurrence keeps returning invalid content even after a repair.
        self.persistent_invalid = persistent_invalid
        #: Empty result -> immediate termination, never a repair.
        self.empty_at = empty_at
        self.empty_practice_stages = set(empty_practice_stages)
        self.forged_node_key = forged_node_key
        self.forged_resource_stage = forged_resource_stage
        self.calls: list[dict[str, Any]] = []

    # -- helpers ---------------------------------------------------------
    def _occurrence(self, purpose: str) -> int:
        return sum(1 for call in self.calls if call["purpose"] == purpose)

    def count(self, purpose: str | None = None) -> int:
        if purpose is None:
            return len(self.calls)
        return sum(1 for call in self.calls if call["purpose"] == purpose)

    def _resources(self, stage_key: str, node_keys: list[str]) -> list[dict[str, Any]]:
        if stage_key == self.forged_resource_stage:
            return [{
                "role": "primary",
                "source_ref": "src_forged_v1",
                "section_refs": ["sec_forged_v1"],
                "source_version": 1,
                "order_index": 0,
                "node_keys": list(node_keys),
                "fallback_search_terms": [],
            }]
        for stage in self.pack.get("stage_blueprints") or []:
            if stage.get("stable_key") == stage_key:
                return deepcopy(stage.get("resources") or [])
        return [{
            "role": "primary",
            "source_ref": "",
            "section_refs": [],
            "source_version": 0,
            "order_index": 0,
            "node_keys": list(node_keys),
            "fallback_search_terms": [f"{stage_key} 官方文档"],
        }]

    # -- per-purpose payload builders ------------------------------------
    def _skeleton(self, payload: dict[str, Any]) -> dict[str, Any]:
        manifest = payload.get("manifest") or {}
        sections = []
        for index, spec in enumerate(manifest.get("stages") or []):
            sections.append({
                "stable_key": spec["stage_key"],
                "title": spec.get("title") or f"阶段 {index + 1}",
                "section_kind": spec.get("section_kind") or "general",
                "objective": spec.get("objective") or f"围绕目标完成{spec.get('title') or '阶段'}",
                "resources": self._resources(spec["stage_key"], list(spec.get("node_keys") or [])),
                "extensions": [],
            })
        return {"outline_ref": "mock-skeleton", "sections": sections}

    def _structure(self, payload: dict[str, Any]) -> dict[str, Any]:
        stage = payload["stage"]
        blueprints = payload.get("node_blueprints") or []
        if not blueprints:
            blueprints = [{
                "stable_key": f"{stage['stable_key']}.node.{i}",
                "title": f"{stage.get('title') or '阶段'}要点 {i + 1}",
                "node_type": "concept",
                "objectives": [f"理解{stage.get('title') or '阶段'}要点 {i + 1}"],
                "parent_key": "",
                "prerequisite_keys": [],
            } for i in range(2)]
        nodes: list[dict[str, Any]] = []
        relations: list[dict[str, Any]] = []
        for blueprint in blueprints:
            nodes.append({
                "stable_key": blueprint["stable_key"],
                "title": blueprint.get("title") or blueprint["stable_key"],
                "node_type": blueprint.get("node_type") or "concept",
                "objectives": list(blueprint.get("objectives") or []),
            })
            if blueprint.get("parent_key"):
                relations.append({"from_stable_key": blueprint["parent_key"],
                                  "to_stable_key": blueprint["stable_key"], "relation_type": "contains"})
            for dependency in blueprint.get("prerequisite_keys") or []:
                relations.append({"from_stable_key": dependency,
                                  "to_stable_key": blueprint["stable_key"], "relation_type": "prerequisite"})
        if self.forged_node_key:
            nodes.append({"stable_key": self.forged_node_key, "title": "伪造节点",
                          "node_type": "concept", "objectives": ["未在领域包中审核"]})
        unit = {
            "stable_key": "unit." + stage["stable_key"],
            "title": stage.get("title") or stage["stable_key"],
            "section_key": stage["stable_key"],
            "order_index": 0,
            "node_keys": [node["stable_key"] for node in nodes],
            "objectives": [stage.get("objective") or "阶段目标"],
        }
        return {"nodes": nodes, "units": [unit], "relations": relations}

    def _practice(self, payload: dict[str, Any]) -> dict[str, Any]:
        stage = payload["stage"]
        structure = payload.get("structure") or {}
        if stage["stable_key"] in self.empty_practice_stages:
            return {"stable_key": "practice." + stage["stable_key"],
                    "title": stage.get("title") or "", "idea": stage.get("title") or "",
                    "tasks": [], "task_knowledge_links": []}
        blueprint = payload.get("practice_blueprint") or {}
        nodes = [node["stable_key"] for node in structure.get("nodes") or []]
        linked = [key for key in (blueprint.get("node_keys") or nodes[:1]) if key in nodes] or nodes[:1]
        task_key = blueprint.get("stable_key") or ("task." + stage["stable_key"])
        task = {
            "stable_key": task_key,
            "title": blueprint.get("title") or (stage.get("title") or "") + "阶段练习",
            "section_key": stage["stable_key"],
            "order_index": 0,
            "goal": blueprint.get("goal") or stage.get("objective") or "完成阶段练习",
            "in_scope": list(blueprint.get("in_scope") or ["阶段要点"]),
            "out_scope": list(blueprint.get("out_scope") or []),
            "acceptance": list(blueprint.get("acceptance") or ["展示练习结果并说明验证步骤"]),
            "knowledge_links": [{"node_stable_key": key, "role": "core"} for key in linked],
        }
        return {
            "stable_key": "practice." + stage["stable_key"],
            "title": stage.get("title") or "",
            "idea": stage.get("title") or "",
            "tasks": [task],
            "task_knowledge_links": [{"task_stable_key": task_key, "node_stable_key": key, "role": "core"}
                                     for key in linked],
        }

    def _repair(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context") or {}
        target = payload.get("target") or {}
        if target.get("kind") == "practice":
            if self.persistent_invalid and self.persistent_invalid[0] == PRACTICE:
                return self._invalid_practice(context)
            return self._practice(context)
        if self.persistent_invalid and self.persistent_invalid[0] == STRUCTURE:
            return self._invalid_structure(context)
        return self._structure(context)

    # -- port ------------------------------------------------------------
    def generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        self.calls.append({"purpose": purpose, "attempt_id": attempt_id, "payload": payload,
                           "schema_name": schema_name, "run_id": run_id})
        occurrence = self._occurrence(purpose)
        if self.fail_at == (purpose, occurrence):
            return LLMFailure("provider_output_truncated", "output truncated",
                              input_tokens=17, output_tokens=8192,
                              details={"finish_reason": "length", "max_tokens": 8192})
        if self.empty_at == (purpose, occurrence):
            return LLMResult(payload={}, model_id="mock", provider="mock")
        invalid = self.invalid_at == (purpose, occurrence) or self.persistent_invalid == (purpose, occurrence)
        if purpose == OUTLINE:
            return LLMResult(payload=self._skeleton(payload), model_id="mock", provider="mock")
        if purpose == STRUCTURE:
            if invalid:
                return LLMResult(payload=self._invalid_structure(payload), model_id="mock", provider="mock")
            return LLMResult(payload=self._structure(payload), model_id="mock", provider="mock")
        if purpose == PRACTICE:
            if invalid:
                return LLMResult(payload=self._invalid_practice(payload), model_id="mock", provider="mock")
            return LLMResult(payload=self._practice(payload), model_id="mock", provider="mock")
        if purpose == REPAIR:
            return LLMResult(payload=self._repair(payload), model_id="mock", provider="mock")
        return LLMFailure("unsupported_purpose", f"unsupported purpose {purpose}")

    # -- semantically invalid (repairable) payloads ----------------------
    def _invalid_structure(self, payload: dict[str, Any]) -> dict[str, Any]:
        stage_key = payload["stage"]["stable_key"]
        nodes = self._structure(payload)["nodes"]
        return {
            "nodes": nodes,
            "units": [{
                "stable_key": "unit.invalid." + stage_key,
                "title": "无效单元",
                "section_key": stage_key,
                "order_index": 0,
                "node_keys": ["node.does.not.exist"],
                "objectives": ["无效目标"],
            }],
            "relations": [],
        }

    def _invalid_practice(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._practice(payload)
        for task in result["tasks"]:
            task["acceptance"] = []
        return result


__all__ = ["OUTLINE", "PRACTICE", "REPAIR", "STRUCTURE", "ScriptedLLM"]
