"""Freeze the protocol, model configuration and budget for a new planning run.

New generation uses ``b3f2-short-v2``; historical Runs retain their protocol. A run
freezes everything it will later depend on *at enqueue time*:

- the protocol version (a run is never re-explained by a different protocol);
- a model configuration reference (a later settings change or revocation must not
  silently swap the model under a running/queued run);
- the validated per-purpose output budget policy.

The frozen values live in the run's execution manifest, so a Worker can prove it
is executing exactly what was submitted.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.planning_budget import BudgetPolicy

__all__ = ["SubmissionBinding"]


@dataclass(frozen=True, slots=True)
class SubmissionBinding:
    """Everything a new run freezes before it is enqueued.

    ``model_ref`` is a *descriptor*, not a secret: it names the configuration
    revision to pin (for example ``personal:<actor>:<version>``), never an API
    key or cookie. Secrets stay in the encrypted settings store.
    """

    model_ref: str
    budget_policy: BudgetPolicy
