"""Independent local evidence binding; not a real semantic acceptance."""
from copy import deepcopy

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import content_hash

from scripts import planning_v2_scenario_a as runner


def inputs():
    packet = {"acceptance_id": "new", "packet_hash": "a" * 64,
        "request_options": {"test": {"model": "deepseek-flash"}}}
    review = {"stage": "goal_analysis", "run_version": 2,
        "run_id": "run_new", "project_id": "project", "actor_id": "actor"}
    frozen = {"review": review, "state": {"stage": "goal_analysis", "profile": "synthetic actual checkpoint"}}
    review["checkpoint_hash"] = content_hash(frozen["state"])
    review["digest"] = content_hash(review)
    evidence = {"version": runner.REVIEW_VERSION, **{k: packet[k] for k in ("acceptance_id", "packet_hash")}, **{k: review[k] for k in
        ("run_id", "project_id", "actor_id", "stage", "run_version")},
        "review_hash": review["digest"], "state_hash": content_hash(frozen["state"]),
        "result": "PASS", "reviewer": "independent-development-reviewer",
        "rationale": "Synthetic fixture checked against input and actual output",
        "evidence_refs": ["ignored:synthetic-input-and-output"]}
    return packet, frozen, evidence


def test_actual_review_identity_and_checkpoint_bound():
    packet, frozen, evidence = inputs()
    assert runner.validate_review_evidence(packet, frozen, evidence) == "approve"
    evidence["result"] = "FAIL"
    assert runner.validate_review_evidence(packet, frozen, evidence) == "reject"


@pytest.mark.parametrize("field,value", [
    ("run_id", "old"), ("project_id", "other"), ("actor_id", "other"),
    ("stage", "capability_planning"), ("run_version", True), ("review_hash", "x"),
    ("state_hash", "x"), ("result", "AMBIGUOUS"), ("reviewer", ""),
    ("reviewer", "deepseek-flash"), ("evidence_refs", []), ("rationale", ""),
])
def test_unbound_or_self_review_does_not_resume(field, value):
    packet, frozen, evidence = inputs()
    changed = deepcopy(evidence)
    changed[field] = value
    with pytest.raises(ValidationAppError):
        runner.validate_review_evidence(packet, frozen, changed)


def test_local_state_cannot_be_replaced_while_reusing_real_review_digest():
    packet, frozen, evidence = inputs()
    frozen["state"]["profile"] = "replacement safe output"
    evidence["state_hash"] = content_hash(frozen["state"])
    with pytest.raises(ValidationAppError):
        runner.validate_review_evidence(packet, frozen, evidence)


def test_self_review_exclusion_uses_frozen_actual_model():
    packet, frozen, evidence = inputs()
    packet["request_options"]["test"]["model"] = "future-owner-model"
    evidence["reviewer"] = "future-owner-model"
    with pytest.raises(ValidationAppError):
        runner.validate_review_evidence(packet, frozen, evidence)
