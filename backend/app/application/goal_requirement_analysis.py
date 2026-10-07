"""One isolated Item 1 call. Public generation/runtime remain disconnected."""
from app.core.errors import ValidationAppError
from app.domain.planning.goal_requirements import (
    GOAL_REQUIREMENT_PURPOSE,
    GOAL_REQUIREMENT_SCHEMA,
    GoalRequirementProfile,
    GoalRequirementProfileValidator,
)
from app.domain.planning.intent import GoalSpec, goal_spec_payload
from app.ports.llm import LLMFailure, LLMPort


class GoalRequirementAnalyzer:
    def __init__(self, llm: LLMPort):
        self._llm = llm
        self._validator = GoalRequirementProfileValidator()

    def analyze(self, goal: GoalSpec | str, *, run_id: str, attempt_id: str) -> GoalRequirementProfile | LLMFailure:
        """Return the sole downstream goal authority, or an existing typed failure.

        No persistence, receipt creation, retry, repair or continuation here.
        Item 7 must supply the durable runtime; IDs alone are not receipts.
        """
        if isinstance(goal, str):
            goal = GoalSpec(target=goal)
        if not isinstance(goal, GoalSpec):
            raise ValidationAppError("目标输入必须为 GoalSpec 或自然语言")
        for value in (run_id, attempt_id):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValidationAppError("分析调用必须有有效 run/attempt identity")
        result = self._llm.generate_structured(
            purpose=GOAL_REQUIREMENT_PURPOSE, schema_name=GOAL_REQUIREMENT_SCHEMA,
            payload={"goal": goal_spec_payload(goal)}, run_id=run_id, attempt_id=attempt_id,
        )
        if isinstance(result, LLMFailure):
            return result
        # Defend the boundary even when a test/custom port skips HTTP parsing.
        if result.finish_reason == "length":
            return LLMFailure("provider_output_truncated", "模型输出被截断", input_tokens=result.input_tokens,
                              output_tokens=result.output_tokens, latency_ms=result.latency_ms)
        try:
            return self._validator.validate(result.payload, goal=goal)
        except ValidationAppError:
            return LLMFailure("goal_requirement_profile_invalid", "目标分析响应未通过结构校验",
                              input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                              latency_ms=result.latency_ms)
