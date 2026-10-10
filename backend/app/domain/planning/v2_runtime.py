"""Frozen V2 execution protocol; contains no persistence or provider calls."""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.capabilities import CAPABILITY_DECISION_SCHEMA, CAPABILITY_PURPOSE, CAPABILITY_SCHEMA
from app.domain.planning.capability_decisions import CAPABILITY_DECISION_PROTOCOL
from app.domain.planning.curriculum import CURRICULUM_PURPOSE, CURRICULUM_SCHEMA
from app.domain.planning.goal_requirements import GOAL_REQUIREMENT_PURPOSE, GOAL_REQUIREMENT_SCHEMA
from app.domain.planning.intent import GoalSpec, goal_spec_payload
from app.domain.planning.research_reader import READER_PURPOSE, READER_SCHEMA
from app.domain.planning.resource_research import ResearchBudget

V2_EXECUTION_VERSION = "planning-v2-execution-v1"
PRODUCT_SEMANTICS_V2 = "planning-v2-product-v2"
PURPOSE_SCHEMAS = {
    GOAL_REQUIREMENT_PURPOSE: GOAL_REQUIREMENT_SCHEMA,
    CAPABILITY_PURPOSE: CAPABILITY_SCHEMA,
    READER_PURPOSE: READER_SCHEMA,
    CURRICULUM_PURPOSE: CURRICULUM_SCHEMA,
}
OWNED_ACCEPTANCE_GATE = "scenario-a-review-v1"
OWNED_REVIEW_STAGES = ("goal_analysis", "capability_planning", "curriculum_composition")


def owned_acceptance_policy():
    return {"version": OWNED_ACCEPTANCE_GATE,
        "purpose_limits": {GOAL_REQUIREMENT_PURPOSE: 1, CAPABILITY_PURPOSE: 1,
            READER_PURPOSE: 6, CURRICULUM_PURPOSE: 1, "research.search": 6, "research.body": 6},
        "review_stages": list(OWNED_REVIEW_STAGES)}


@dataclass(frozen=True, slots=True)
class OwnedV2ReviewPending:
    stage: str
    review_hash: str


def purpose_schema(manifest, purpose):
    """Select only the schema frozen by this run, never the current default."""
    if purpose == CAPABILITY_PURPOSE and manifest.get("capability_output_protocol") == CAPABILITY_DECISION_PROTOCOL:
        return CAPABILITY_DECISION_SCHEMA
    if manifest.get("product_semantics") == PRODUCT_SEMANTICS_V2:
        if purpose == READER_PURPOSE:
            return "ResearchReaderV2"
        if purpose == CURRICULUM_PURPOSE:
            return "CurriculumPlanV2"
    return PURPOSE_SCHEMAS.get(purpose)


class V2RecoveryBlocked(RuntimeError):
    """No additional dispatch is safe without explicit reconciliation."""


class V2BudgetExceeded(ValidationAppError):
    """A known local budget guard rejected continuation."""

    def __init__(self):
        super().__init__("V2 frozen budget exhausted or exceeded")


def wire(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: wire(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [wire(v) for v in value]
    return value


def manifest_intact(manifest):
    try:
        return (
            type(manifest) is dict
            and manifest["protocol"] == V2_EXECUTION_VERSION
            and ("product_semantics" not in manifest or manifest["product_semantics"] == PRODUCT_SEMANTICS_V2)
            and ("capability_output_protocol" not in manifest or (
                manifest["capability_output_protocol"] == CAPABILITY_DECISION_PROTOCOL
                and manifest.get("product_semantics") == PRODUCT_SEMANTICS_V2
                and manifest.get("owned_acceptance") == owned_acceptance_policy()))
            and manifest["manifest_hash"]
            == content_hash({k: v for k, v in manifest.items() if k != "manifest_hash"})
            and type(manifest["model_ref"]) is str
            and 0 < len(manifest["model_ref"]) <= 512
            and type(manifest["expected_version"]) is int
            and manifest["expected_version"] >= 0
            and type(ResearchBudget(**manifest["budget"])) is ResearchBudget
            and set(manifest["output_caps"]) == set(PURPOSE_SCHEMAS)
            and all(type(v) is int and 0 < v <= 8192 for v in manifest["output_caps"].values())
            and manifest["output_caps"][READER_PURPOSE] <= 1024
            and ("owned_acceptance" not in manifest or (
                manifest["owned_acceptance"] == owned_acceptance_policy()
                and manifest.get("product_semantics") == PRODUCT_SEMANTICS_V2
                and manifest["expected_version"] == 0
                and "v2_revision_hash" not in manifest and "v2_clarification_hash" not in manifest
                and manifest["output_caps"] == {p: 1024 if p == READER_PURPOSE else 4096 for p in PURPOSE_SCHEMAS}))
            and datetime.fromisoformat(manifest["checked_at"]).tzinfo is not None
        )
    except (TypeError, ValueError, KeyError, ValidationAppError):
        return False


def build_v2_manifest(
    goal,
    *,
    model_ref,
    source_facts,
    budget,
    checked_at,
    expected_version=0,
    output_caps=None,
    domain_sources=(),
    product_semantics=None,
    acceptance_gate=None,
    capability_output_protocol=None,
):
    goal = GoalSpec(goal) if isinstance(goal, str) else goal
    if type(goal) is not GoalSpec or type(budget) is not ResearchBudget:
        raise ValidationAppError("V2 submission needs typed frozen goal and shared budget")
    d = {
        "protocol": V2_EXECUTION_VERSION,
        "goal_hash": content_hash(goal_spec_payload(goal)),
        "model_ref": model_ref,
        "source_facts_hash": content_hash(wire(asdict(source_facts))),
        "budget": asdict(budget),
        "checked_at": checked_at,
        "expected_version": expected_version,
        "domain_registry_hash": content_hash([wire(asdict(s)) for s in domain_sources]),
        "output_caps": output_caps or {p: 1024 if p == READER_PURPOSE else 8192 for p in PURPOSE_SCHEMAS},
    }
    if product_semantics is not None:
        d["product_semantics"] = product_semantics
    if capability_output_protocol is not None:
        if (capability_output_protocol != CAPABILITY_DECISION_PROTOCOL
                or acceptance_gate != OWNED_ACCEPTANCE_GATE
                or product_semantics != PRODUCT_SEMANTICS_V2):
            raise ValidationAppError("CapabilityDecisionV2 requires an explicitly frozen owned V2 acceptance")
        d["capability_output_protocol"] = capability_output_protocol
    if acceptance_gate is not None:
        if acceptance_gate != OWNED_ACCEPTANCE_GATE or domain_sources:
            raise ValidationAppError("Unknown or expanded owned acceptance gate")
        caps = {p: 1024 if p == READER_PURPOSE else 4096 for p in PURPOSE_SCHEMAS}
        if output_caps is not None and output_caps != caps:
            raise ValidationAppError("Owned acceptance requires exact output caps")
        d["output_caps"] = caps
        d["owned_acceptance"] = owned_acceptance_policy()
    d["manifest_hash"] = content_hash(d)
    if not manifest_intact(d):
        raise ValidationAppError("Invalid V2 frozen submission")
    return d
