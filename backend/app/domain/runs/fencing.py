"""Immutable server-issued scope for one worker's result commit."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlanningWriteFence:
    job_id: str
    run_id: str
    project_id: str
    actor_id: str
    lease_token: str
