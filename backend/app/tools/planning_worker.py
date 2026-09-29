"""Explicit local development entry point for the planning Worker."""

from __future__ import annotations

import logging

from app.composition import build_container
from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.is_development:
        raise SystemExit(
            "PLANNING_WORKER_ACTOR_IDS is a local-development/security-validation limit; "
            "public cloud/open-registration V1 is blocked until an RLS-safe claim mechanism "
            "works without manually listing every user."
        )
    if not settings.database_url:
        raise SystemExit("规划 Worker 需要 DATABASE_URL")
    if not settings.planning_worker_actor_ids:
        raise SystemExit("请在本地 .env 设置 PLANNING_WORKER_ACTOR_IDS，再显式启动 Worker")
    logging.basicConfig(level=settings.log_level)
    container = build_container(settings)
    if container.planning_worker is None:
        raise SystemExit("规划 Worker 未装配")
    container.planning_worker.run()


if __name__ == "__main__":
    main()

