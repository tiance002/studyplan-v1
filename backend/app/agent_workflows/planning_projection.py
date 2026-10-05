"""Pure reconstruction against independently supplied submission and receipts.

The caller owns I/O and scope. Neither expected inputs nor raw receipts come
from the checkpoint being checked. This boundary is generation-only; legitimate
draft edits use their existing revision/hash workflow.
"""

import json
from copy import deepcopy
from app.agent_workflows.known_json_failure import failed_entry, known_invalid_json
from app.ports.llm import LLMFailure

from app.agent_workflows.planning_structure import (
    check_frozen_structure,
    presentation_entry,
    uses_reviewed_structure,
)

FROZEN_FIELDS = (
    "run_id",
    "project_id",
    "graph_version",
    "goal",
    "goal_spec",
    "prefs_snapshot",
    "manifest",
    "domain_pack",
    "expected_version",
    "route_change",
    "protocol",
)
PROJECTION_FIELDS = (
    "outline",
    "nodes",
    "units",
    "relations",
    "practice_proposal",
    "route_scope",
    "route_status",
    "resource_support",
)


def json_copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def new_structure_signal(manifest):
    if not isinstance(manifest, dict):
        return False
    return any(k in manifest for k in ("structure_input_format", "structure_focus_format")) or any(
        isinstance(b, dict) and "structure_input_format" in b for b in manifest.get("structure_batches") or []
    )


def difference(actual, expected, path):
    """First exact path only; no secret or teaching text in exception messages."""
    if type(actual) is not type(expected):
        return path
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            return path + ".keys"
        for key in expected:
            found = difference(actual[key], expected[key], path + "." + str(key))
            if found:
                return found
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            return path + ".length"
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            found = difference(a, e, f"{path}[{i}]")
            if found:
                return found
    elif actual != expected:
        return path
    return None


def check_submission(state, initial):
    """All-marker deletion cannot select legacy against a new frozen source."""
    check_frozen_structure(state)
    if initial is None:
        return
    for key in FROZEN_FIELDS:
        if key in initial:
            path = difference(json_copy(state.get(key)), json_copy(initial[key]), key)
            if path:
                raise ValueError("Frozen submission mismatch: " + path)


def pending_repair_attempt(state):
    """Identify only the next local repair's retained receipt on a crash window."""
    from app.agent_workflows.planning_batches import REPAIR_PURPOSE, attempt_key

    target = state.get("repair_target") or {}
    kind = target.get("kind")
    if kind not in {"structure", "practice"}:
        raise ValueError("Pending repair kind mismatch")
    manifest = state["manifest"]
    index = target.get("batch_index")
    if (
        not isinstance(index, int)
        or index < 0
        or index != state.get("current_" + kind + "_index", 0)
        or index >= len(manifest[kind + "_batches"])
        or target.get("stage_key") != manifest[kind + "_batches"][index]["stage_key"]
    ):
        raise ValueError("Pending repair stage/index mismatch")
    count = state.get("repair_count", 0)
    if not isinstance(count, int) or not 0 <= count < manifest["max_repairs"]:
        raise ValueError("Pending repair count mismatch")
    key_index = index if kind == "structure" else len(manifest["structure_batches"]) + index
    return attempt_key(state["run_id"], REPAIR_PURPOSE, target["stage_key"], key_index, count + 1)


def checked_projection(state, initial, receipts, *, final=False, pending_repair=False):
    """Reject inconsistent derived state; return the same validated deep copy."""
    from app.agent_workflows.planning_batches import (
        OUTLINE_PURPOSE,
        PRACTICE_PURPOSE,
        REPAIR_PURPOSE,
        STRUCTURE_PURPOSE,
        allowed_attempt_keys,
        attempt_key,
        merge_batches,
    )

    check_submission(state, initial)
    if not new_structure_signal((initial or state).get("manifest")):
        return deepcopy(state)
    if initial is None:
        raise ValueError("Independent frozen submission missing")
    trusted = json_copy(initial)
    manifest = trusted["manifest"]
    run_id = trusted["run_id"]
    allowed = allowed_attempt_keys(run_id, manifest)
    by_id = {}
    pending = (
        pending_repair_attempt(state)
        if pending_repair
        and not final
        and not any(k in state for k in ("nodes", "units", "relations", "practice_proposal"))
        else None
    )
    for receipt in receipts:
        if receipt.get("run_id") != run_id or receipt.get("attempt_id") not in allowed:
            raise ValueError("Retained response Run/attempt binding mismatch")
        key = receipt["attempt_id"]
        if key in by_id and by_id[key] != receipt:
            raise ValueError("Conflicting retained response binding")
        by_id[key] = json_copy(receipt)
    # Receipt commit precedes the graph checkpoint. Validate the previous raw
    # projection while that exact next repair awaits replay; its adapter must
    # read the retained fingerprint-bound result and cannot dispatch it again.
    if pending is not None:
        by_id.pop(pending, None)

    def receipt_value(value, purpose, stage, index, schema):
        if value.get('schema_name') != schema:
            raise ValueError('Retained response schema binding mismatch: ' + stage)
        if 'failure' in value:
            kind = {'planning.structure': 'structure', 'planning.practice': 'practice'}.get(purpose)
            try:
                failure = LLMFailure(**value['failure'])
            except (TypeError, ValueError):
                raise ValueError('Invalid known failure receipt') from None
            if (kind is None or final or any(k in state for k in ('nodes', 'units', 'relations', 'practice_proposal'))
                    or state.get('current_' + kind + '_index', 0) != index
                    or not known_invalid_json(failure, run_id, value['attempt_id'])):
                raise ValueError('Known failure cannot supply successful projection: ' + stage)
            return {}, value['attempt_id']
        return deepcopy(value['payload']), None

    def raw(purpose, stage, index, schema, *, with_failure=False):
        keys = [attempt_key(run_id, purpose, stage, index, 0)]
        if purpose != OUTLINE_PURPOSE:
            keys += [
                attempt_key(run_id, REPAIR_PURPOSE, stage, index, i)
                for i in range(1, manifest["max_repairs"] + 1)
            ]
        retained = [by_id[k] for k in keys if k in by_id]
        if not retained:
            raise ValueError("Independent retained response missing: " + purpose + "/" + stage)
        produced, failed = receipt_value(retained[-1], purpose, stage, index, schema)
        return (produced, failed) if with_failure else produced

    if state.get("outline") and not any(
        k in state for k in ("nodes", "units", "relations", "practice_proposal")
    ):
        path = difference(
            json_copy(state["outline"]), json_copy(raw(OUTLINE_PURPOSE, "", 0, "OutlineV1")), "outline"
        )
        if path:
            raise ValueError("Derived projection mismatch: " + path)
    structures = []
    for saved in state.get("structure_batches") or []:
        key = saved.get("stage_key")
        batch = next((b for b in manifest["structure_batches"] if b["stage_key"] == key), None)
        if batch is None or any(s["stage_key"] == key for s in structures):
            raise ValueError("Structure stage membership mismatch")
        reviewed = uses_reviewed_structure(manifest, batch)
        produced, failed = raw(
            STRUCTURE_PURPOSE,
            key,
            batch["batch_index"],
            "ReviewedStructureV1" if reviewed else "KnowledgeStructureV1",
            with_failure=True,
        )
        expected = (
            presentation_entry(produced, trusted, batch)
            if reviewed
            else {**produced, "stage_key": key, "batch_index": batch["batch_index"]}
        )
        if failed is not None:
            expected = failed_entry('structure', trusted, batch['batch_index'], failed)
            path = difference(json_copy(saved), json_copy(expected), 'failed_structure.' + key)
            if path:
                raise ValueError('Derived failure placeholder mismatch: ' + path)
        elif '_known_invalid_json_attempt' in saved:
            raise ValueError('Stale failure marker on successful structure: ' + key)
        if saved.get("batch_index") != batch["batch_index"]:
            raise ValueError("Structure batch index mismatch: " + key)
        for field in ("_reviewed_presentation", "nodes", "units", "relations"):
            if field in expected:
                path = difference(
                    json_copy(saved.get(field)),
                    json_copy(expected[field]),
                    "structure_batches." + key + "." + field,
                )
                if path:
                    raise ValueError("Derived projection mismatch: " + path)
        structures.append(expected)
    practices = []
    for saved in state.get("practice_batches") or []:
        key = saved.get("stage_key")
        batch = next((b for b in manifest["practice_batches"] if b["stage_key"] == key), None)
        if batch is None or any(s["stage_key"] == key for s in practices):
            raise ValueError("Practice stage membership mismatch")
        # Repair IDs for practices use the offset; normal IDs use local index.
        normal = attempt_key(run_id, PRACTICE_PURPOSE, key, batch["batch_index"], 0)
        repair_index = len(manifest["structure_batches"]) + batch["batch_index"]
        keys = [normal] + [
            attempt_key(run_id, REPAIR_PURPOSE, key, repair_index, i)
            for i in range(1, manifest["max_repairs"] + 1)
        ]
        retained = [by_id[k] for k in keys if k in by_id]
        if not retained or retained[-1].get("schema_name") != "PracticeProposalV1":
            raise ValueError("Independent practice response missing or incompatible: " + key)
        produced, failed = receipt_value(retained[-1], PRACTICE_PURPOSE, key,
                                        batch['batch_index'], 'PracticeProposalV1')
        expected = {
            "stage_key": key,
            "batch_index": batch["batch_index"],
            "payload": produced,
        }
        if failed is not None:
            expected = failed_entry('practice', trusted, batch['batch_index'], failed)
            path = difference(json_copy(saved), json_copy(expected), 'failed_practice.' + key)
            if path:
                raise ValueError('Derived failure placeholder mismatch: ' + path)
        elif '_known_invalid_json_attempt' in saved:
            raise ValueError('Stale failure marker on successful practice: ' + key)
        if saved.get("batch_index") != batch["batch_index"]:
            raise ValueError("Practice batch index mismatch: " + key)
        path = difference(
            json_copy(saved.get("payload")),
            json_copy(expected["payload"]),
            "practice_batches." + key + ".payload",
        )
        if path:
            raise ValueError("Derived projection mismatch: " + path)
        practices.append(expected)
    if final or any(k in state for k in ("nodes", "units", "relations", "practice_proposal")):
        outline = raw(OUTLINE_PURPOSE, "", 0, "OutlineV1")
        merged = merge_batches(
            outline, structures, practices, trusted.get("domain_pack") or {}, manifest=manifest
        )
        if merged["errors"]:
            raise ValueError("Cannot rebuild final projection from retained responses")
        for key in PROJECTION_FIELDS:
            path = difference(json_copy(state.get(key)), json_copy(merged.get(key)), key)
            if path:
                raise ValueError("Derived projection mismatch: " + path)
    return deepcopy(state)
