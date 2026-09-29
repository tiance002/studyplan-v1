"""Explicit local allowlist setup for registered actors in disposable DB tests."""

from dataclasses import replace

from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.worker.planning_worker import PlanningWorker


def configure_test_worker(client):
    container = client.app.state.container
    settings = container.settings
    scope = container.sessions.resolve(client.cookies.get(settings.session_cookie_name))
    assert scope is not None
    actors = tuple(dict.fromkeys((*settings.planning_worker_actor_ids, scope.actor_id)))
    jobs = PgPlanningJobRepository(settings.database_url, actor_ids=actors)
    service = container.plan_service
    service._planning_jobs = jobs
    service._worker_actor_ids = actors
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=actors)
    client.app.state.container = replace(
        container, settings=replace(settings, planning_worker_actor_ids=actors), planning_worker=worker,
    )
    return worker
