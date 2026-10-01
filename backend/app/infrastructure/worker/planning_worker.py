"""Sequential worker for the durable planning queue.

The Worker is constructed by the composition root but is never started by the
HTTP application. Deployment starts it explicitly with ``python -m
app.tools.planning_worker``.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from collections.abc import Callable

from app.core.errors import ForbiddenError, ValidationAppError
from app.ports.planning_jobs import JobClaim, PlanningJobsPort, PlanningLeaseLostError

logger = logging.getLogger(__name__)


class PlanningWorker:
    def __init__(
        self,
        *,
        jobs: PlanningJobsPort,
        execute: Callable[..., None],
        actor_ids: tuple[str, ...],
        poll_interval_seconds: int = 2,
        lease_seconds: int = 300,
        worker_id: str | None = None,
        is_development: bool = True,
        admission_mode: str = "allowlist",
    ) -> None:
        if admission_mode not in {"allowlist", "trusted_server"}:
            raise ValidationAppError("Worker admission 参数无效")
        self._jobs = jobs
        self._execute = execute
        self._actor_ids = tuple(dict.fromkeys(actor_ids))
        self._poll_interval = max(1, poll_interval_seconds)
        self._lease_seconds = max(3, lease_seconds)
        self._worker_id = worker_id or f"planning-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._is_development = is_development
        self._admission_mode = admission_mode

    def tick(self) -> bool:
        """Claim and process at most one job; return whether a job was claimed."""
        if self._admission_mode == "trusted_server":
            claim = self._jobs.claim_next(self._worker_id, self._lease_seconds)
            if claim is None:
                return False
            self._process(claim)
            return True
        if not self._actor_ids:
            raise ForbiddenError(
                "规划 Worker 未配置 PLANNING_WORKER_ACTOR_IDS；该白名单仅用于本地开发与安全验证"
            )
        for actor_id in self._actor_ids:
            for project_id in self._jobs.list_projects(actor_id):
                claim = self._jobs.claim(project_id, self._worker_id, self._lease_seconds)
                if claim is not None:
                    self._process(claim)
                    return True
        return False

    def _process(self, claim: JobClaim) -> None:
        stopped = threading.Event()
        lease_lost = threading.Event()

        def renew_lease() -> None:
            interval = max(1.0, self._lease_seconds / 3)
            while not stopped.wait(interval):
                try:
                    if not self._jobs.renew(claim, self._lease_seconds):
                        lease_lost.set()
                        logger.error("planning Worker lost lease for run %s", claim.run_id)
                        return
                except Exception:  # connection errors do not authorize running past the lease
                    lease_lost.set()
                    logger.exception("planning Worker could not renew lease for run %s", claim.run_id)
                    return

        heartbeat = threading.Thread(target=renew_lease, name=f"lease-{claim.job_id}", daemon=True)
        heartbeat.start()

        def guard() -> None:
            if lease_lost.is_set() or not self._jobs.check_claim(claim):
                raise PlanningLeaseLostError("规划 Worker 的租约已失效")

        try:
            guard()
            self._execute(claim.project_id, claim.run_id, guard=guard, claim=claim)
        except PlanningLeaseLostError:
            # A replacement Worker owns the run. The old claim cannot finish it.
            logger.warning("planning Worker stopped after losing lease for run %s", claim.run_id)
        except Exception:
            logger.exception("planning Worker execution failed for run %s", claim.run_id)
            self._jobs.finish(claim, "failed")
        else:
            if not lease_lost.is_set():
                self._jobs.finish(claim, "completed")
        finally:
            stopped.set()
            heartbeat.join(timeout=max(2.0, self._lease_seconds / 3 + 1))

    def run(self, stop_event: threading.Event | None = None) -> None:
        """Run a bounded polling loop while holding the process-wide PG lock."""
        if self._admission_mode == "allowlist" and not self._is_development:
            raise RuntimeError(
                "PLANNING_WORKER_ACTOR_IDS is local-only; public cloud/open-registration V1 is blocked "
                "until claims work without per-user listing and preserve project RLS"
            )
        if self._admission_mode == "allowlist" and not self._actor_ids:
            raise ForbiddenError(
                "未设置 PLANNING_WORKER_ACTOR_IDS。云端开放注册部署受阻，需先实现无需逐用户登记且保持 RLS 的安全领取机制"
            )
        stopped = stop_event or threading.Event()
        if not self._jobs.acquire_worker_lock():
            raise RuntimeError("另一个规划 Worker 已持有数据库单 Worker 租约锁")
        try:
            while not stopped.is_set():
                if not self.tick():
                    stopped.wait(self._poll_interval)
        finally:
            self._jobs.release_worker_lock()


__all__ = ["PlanningWorker"]
