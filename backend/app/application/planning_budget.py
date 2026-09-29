"""Validated per-purpose generation budgets frozen with a planning run."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from app.core.errors import ValidationAppError

OFFICIAL_DEEPSEEK_FLASH_OUTPUT_CAP = 393216


@dataclass(frozen=True, slots=True)
class BudgetPolicy:
    outline: int
    structure: int
    practice: int
    repair: int
    deployment_cap: int
    model_cap: int

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if type(value) is not int or value < 1:
                raise ValidationAppError(f"Invalid output budget {name}")

    def for_purpose(self, purpose: str) -> int:
        targets = {
            "planning.outline": self.outline,
            "planning.structure": self.structure,
            "planning.practice": self.practice,
            "planning.repair": self.repair,
        }
        target = targets.get(purpose)
        if target is None:
            raise ValidationAppError(f"Unsupported output budget purpose: {purpose}")
        if target > self.deployment_cap or target > self.model_cap:
            raise ValidationAppError(
                f"Output budget conflict for {purpose}: target={target}, "
                f"deployment_cap={self.deployment_cap}, model_cap={self.model_cap}"
            )
        return target

    def validate_all(self) -> None:
        for purpose in ("planning.outline", "planning.structure", "planning.practice", "planning.repair"):
            self.for_purpose(purpose)

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def budget_policy_for_model(settings, *, model: str, base_url: str) -> BudgetPolicy:
    """Build and validate a policy for the exact configured endpoint/model pair."""
    host = (urlsplit(base_url).hostname or "").lower()
    if host == "api.deepseek.com" and model == "deepseek-flash":
        model_cap = OFFICIAL_DEEPSEEK_FLASH_OUTPUT_CAP
    else:
        model_cap = settings.llm_model_max_output_tokens
    policy = BudgetPolicy(
        outline=settings.llm_outline_output_tokens,
        structure=settings.llm_structure_output_tokens,
        practice=settings.llm_practice_output_tokens,
        repair=settings.llm_repair_output_tokens,
        deployment_cap=settings.llm_max_output_tokens,
        model_cap=model_cap,
    )
    policy.validate_all()
    return policy


__all__ = ["BudgetPolicy", "OFFICIAL_DEEPSEEK_FLASH_OUTPUT_CAP", "budget_policy_for_model"]
