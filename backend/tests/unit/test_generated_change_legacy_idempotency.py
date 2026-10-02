"""An optional API extension must keep old durable generated receipts readable."""
from contextlib import contextmanager
from dataclasses import asdict
from types import SimpleNamespace

from app.core.ids import content_hash
from app.domain.generated_plan_changes import GeneratedPlanChangeCommand
from app.infrastructure.db.generated_plan_changes import PgGeneratedPlanChanges


def test_empty_topics_preserve_legacy_generated_command_fingerprint():
    command = GeneratedPlanChangeCommand('p', 'plan', 1, 'already-consumed', 'regenerate_future_plan')
    old = asdict(command)
    old.pop('topic_keys')
    connection = SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: {
        'detail': {'initial': {'route_change': {'input_hash': content_hash(old)}}}}))

    @contextmanager
    def connected(*args):
        yield connection

    repository = PgGeneratedPlanChanges('unused')
    repository._connection = connected
    scope = SimpleNamespace(actor_id='actor')
    assert repository.existing_submission(scope, command) == repository._run_id(scope, command)
