"""Ports for the durable, single-worker planning queue.

These interfaces describe the existing ``ai_jobs`` / ``ai_runs`` storage. They
do not introduce a second queue or expose database details to the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Protocol, runtime_checkable

from app.domain.runs.models import RunRecord


@dataclass(frozen=True, slots=True)
class JobClaim:
    job_id: str
    run_id: str
    project_id: str
    actor_id: str
    lease_token: str


class PlanningLeaseLostError(RuntimeError):
    """The Worker may retain a returned Attempt but must make no further writes/calls."""


@runtime_checkable
class PlanningJobsPort(Protocol):
    def enqueue(self, run: RunRecord, initial: dict[str, object], manifest: dict[str, object]) -> None: ...
    def list_projects(self, actor_id: str) -> tuple[str, ...]: ...
    def claim(self, project_id: str, worker_id: str, lease_seconds: int) -> JobClaim | None: ...
    def renew(self, claim: JobClaim, lease_seconds: int) -> bool: ...
    def check_claim(self, claim: JobClaim) -> bool: ...
    def finish(self, claim: JobClaim, status: str) -> bool: ...
    def read_submission(self, project_id: str, run_id: str) -> dict[str, object]: ...
    def publish_progress(self, claim: JobClaim, progress: dict[str, object]) -> bool:
        """Append one fenced business-progress event for the claimed run.

        Returns ``False`` when the claim is stale (lease lost / run terminal), in
        which case nothing is written. Completed indices are absolute, so a
        replayed checkpoint never double counts.
        """
        ...

    def acquire_worker_lock(self) -> bool: ...
    def release_worker_lock(self) -> None: ...


@runtime_checkable
class PlanningWorkerPort(Protocol):
    def tick(self) -> bool: ...
    def run(self, stop_event: Event | None = None) -> None: ...


__all__ = ["JobClaim", "PlanningJobsPort", "PlanningWorkerPort"]
