"""One Profile-only semantic selection call; no runtime, retry or research dispatch."""
from app.core.errors import ValidationAppError
from app.domain.planning.capabilities import (
    CAPABILITY_PURPOSE,
    CAPABILITY_SCHEMA,
    CapabilityPlan,
    CapabilityPlanningIssue,
    CapabilityPlanningPending,
    CapabilityPlanValidator,
    validate_capability_planning_input,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.domain.planning.goal_requirements import GoalRequirementProfile
from app.ports.llm import LLMFailure, LLMPort


class CapabilityPlanner:
    def __init__(self, llm: LLMPort):
        self._llm = llm
        self._validator = CapabilityPlanValidator()

    def plan(self, profile: GoalRequirementProfile, *, run_id: str, attempt_id: str,
             verification_evidence=()) -> CapabilityPlan | CapabilityPlanningPending | LLMFailure:
        if not isinstance(profile, GoalRequirementProfile):
            raise ValidationAppError("能力规划只接受GoalRequirementProfile")
        try:
            evidence = tuple(verification_evidence)
            payload = {"profile": profile.to_payload(), "policy": CAPABILITY_POLICY.to_payload(),
                       "verification_evidence": [e.to_payload() for e in evidence]}
            if not validate_capability_planning_input(payload, CAPABILITY_SCHEMA, allow_clarification=True):
                return LLMFailure("capability_planning_input_invalid", "能力规划输入未通过校验", details={"dispatched": False})
        except (TypeError, ValueError, AttributeError):
            return LLMFailure("capability_planning_input_invalid", "能力规划输入未通过校验", details={"dispatched": False})
        if profile.status == "needs_clarification":
            return CapabilityPlanningPending("needs_clarification", profile.profile_hash, CAPABILITY_POLICY.version,
                (CapabilityPlanningIssue("upstream_needs_clarification", ()),), profile.clarification_questions)
        for value in (run_id, attempt_id):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValidationAppError("能力规划需要有效调用身份")
        result = self._llm.generate_structured(purpose=CAPABILITY_PURPOSE, schema_name=CAPABILITY_SCHEMA,
            payload=payload, run_id=run_id, attempt_id=attempt_id)
        if isinstance(result, LLMFailure):
            return result
        if result.finish_reason == "length":
            return LLMFailure("provider_output_truncated", "能力规划输出被截断", input_tokens=result.input_tokens,
                              output_tokens=result.output_tokens, latency_ms=result.latency_ms)
        try:
            return self._validator.validate(result.payload, profile=profile, verification_evidence=evidence)
        except (ValidationAppError, TypeError, ValueError, KeyError):
            return LLMFailure("capability_plan_invalid", "能力规划输出未通过校验", input_tokens=result.input_tokens,
                              output_tokens=result.output_tokens, latency_ms=result.latency_ms)
