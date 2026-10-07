"""Item 1 authority: validated goal facts, never a curriculum or capability plan.

The validator proves shape, identity and source membership, not semantic truth.
IDs and hash are server-derived; the model cannot supply either.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from json import loads
from typing import Literal

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.intent import Depth, GoalSpec, Purpose

GOAL_REQUIREMENT_PURPOSE = "planning.goal_requirement_analysis"
GOAL_REQUIREMENT_SCHEMA = "GoalRequirementProfileV1"


@dataclass(frozen=True, slots=True)
class Requirement:
    requirement_id: str
    text: str
    origin: Literal["explicit", "inferred_required"]
    source_refs: tuple[str, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class GoalFact:
    """Shared factual shape; final field names distinguish constraints/claims."""
    text: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HardConstraint(GoalFact):
    constraint_id: str


@dataclass(frozen=True, slots=True)
class LearnerClaim(GoalFact):
    claim_id: str


@dataclass(frozen=True, slots=True)
class GoalRequirementProfile:
    schema_version: int
    target_summary: str
    scope: tuple[str, ...]
    desired_depth: Depth
    starting_point: str
    outcome_purpose: Purpose
    required_requirements: tuple[Requirement, ...]
    hard_constraints: tuple[HardConstraint, ...]
    learner_claims: tuple[LearnerClaim, ...]
    project_context: str | None
    clarification_questions: tuple[str, ...]
    status: Literal["ready", "needs_clarification"]

    @property
    def profile_hash(self) -> str:
        return content_hash(asdict(self))

    def to_payload(self) -> dict[str, object]:
        """Return an isolated JSON-compatible downstream authority, without raw input."""
        payload = loads(canonical_json(asdict(self)))
        return payload | {"profile_hash": self.profile_hash}


class GoalRequirementProfileValidator:
    """Strict model-output boundary; no NLP, policy lookup or AI reviewer.

    Structured GoalSpec facts are copied, not model-reinterpreted. source_refs
    resolve only against this input. Consumers receive Profile, not GoalSpec.
    """

    _fields = frozenset({"schema_version", "target_summary", "required_requirements", "hard_constraints",
                         "learner_claims", "clarification_questions", "status"})

    def validate(self, raw: object, *, goal: GoalSpec) -> GoalRequirementProfile:
        if not isinstance(goal, GoalSpec):
            raise ValidationAppError("GoalRequirementProfile 需要有效 GoalSpec")
        data = self._object(raw, self._fields)
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            self._reject("schema_version")
        summary = self._text(data["target_summary"], limit=2000)
        status = data["status"]
        if not isinstance(status, str) or status not in {"ready", "needs_clarification"}:
            self._reject("status")
        questions = tuple(self._text(x, limit=500) for x in self._array(data["clarification_questions"], 3))
        if (status == "ready" and questions) or (status == "needs_clarification" and not questions):
            self._reject("clarification_questions")
        allowed = self._source_refs(goal)
        requirements = []
        for item in self._array(data["required_requirements"], 50):
            item = self._object(item, {"text", "origin", "source_refs", "rationale"})
            origin = item["origin"]
            if not isinstance(origin, str) or origin not in {"explicit", "inferred_required"}:
                self._reject("origin")
            value = {"text": self._text(item["text"], limit=2000), "origin": origin,
                     "source_refs": self._references(item["source_refs"], allowed),
                     "rationale": self._text(item["rationale"], limit=2000, allow_empty=origin == "explicit")}
            requirements.append(Requirement(requirement_id="req_" + content_hash(value), **value))
        if status == "ready" and not requirements:
            self._reject("required_requirements")
        constraints = self._facts(data["hard_constraints"], allowed, "constraint", HardConstraint)
        # Verbatim structured user constraints are provable facts, not an NLP
        # interpretation. Reject omission/rephrasing instead of silently fixing
        # the model response or trusting a source citation as semantic proof.
        for index, text in enumerate(goal.constraints):
            if not any(c.text == text and f"goal.constraints[{index}]" in c.source_refs for c in constraints):
                self._reject("structured_constraint_missing_or_changed")
        claims = self._facts(data["learner_claims"], allowed, "claim", LearnerClaim)
        self._unique([r.requirement_id for r in requirements])
        self._unique([c.constraint_id for c in constraints])
        self._unique([c.claim_id for c in claims])
        return GoalRequirementProfile(
            schema_version=1, target_summary=summary, scope=goal.scope, desired_depth=goal.desired_depth,
            starting_point=goal.starting_point, outcome_purpose=goal.outcome_purpose,
            required_requirements=tuple(requirements), hard_constraints=constraints, learner_claims=claims,
            project_context=goal.project_context, clarification_questions=questions, status=status,
        )

    def _facts(self, raw, allowed, kind, cls):
        facts = []
        for item in self._array(raw, 20):
            item = self._object(item, {"text", "source_refs"})
            value = {"text": self._text(item["text"], limit=2000),
                     "source_refs": self._references(item["source_refs"], allowed)}
            facts.append(cls(**value, **{kind + "_id": kind + "_" + content_hash(value)}))
        return tuple(facts)

    @staticmethod
    def _source_refs(goal):
        refs = {"goal.target", "goal.desired_depth", "goal.outcome_purpose"}
        if goal.starting_point:
            refs.add("goal.starting_point")
        for field in ("scope", "constraints"):
            values = getattr(goal, field)
            if values:
                refs.add("goal." + field)
                refs.update(f"goal.{field}[{index}]" for index in range(len(values)))
        if goal.project_context is not None:
            refs.add("project_context")
        return refs

    def _references(self, raw, allowed):
        refs = self._array(raw, 10)
        if not refs or any(not isinstance(x, str) or x not in allowed for x in refs):
            self._reject("source_refs")
        self._unique(refs)
        return tuple(sorted(refs))

    def _object(self, raw, names):
        if not isinstance(raw, dict) or set(raw) != set(names):
            self._reject("fields")
        return raw

    def _array(self, raw, limit):
        if not isinstance(raw, list) or len(raw) > limit:
            self._reject("array")
        return raw

    def _text(self, raw, *, limit, allow_empty=False):
        if not isinstance(raw, str) or len(raw) > limit or (not allow_empty and not raw.strip()):
            self._reject("text")
        return raw.strip()

    def _unique(self, values):
        if len(values) != len(set(values)):
            self._reject("duplicate_identity")

    @staticmethod
    def _reject(field):
        # Error metadata names only the boundary; never echoes user/model text.
        raise ValidationAppError("GoalRequirementProfile 结构校验失败", field=field)
