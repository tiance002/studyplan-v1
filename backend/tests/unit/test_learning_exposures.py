import pytest
from app.core.errors import ValidationAppError
from app.domain.enums import UnitProgress
from app.domain.learning_exposures import ExposureCommand, exposure_id, require_transition


def test_exposure_identity_is_stable_and_position_specific():
    first = exposure_id("p", "plan", "stage", "unit")
    assert first == exposure_id("p", "plan", "stage", "unit")
    assert len({first, exposure_id("p", "other-plan", "stage", "unit"),
                exposure_id("p", "plan", "other-stage", "unit"),
                exposure_id("p", "plan", "stage", "other-unit")}) == 4


def test_skip_return_and_completion_use_existing_progress_rules():
    require_transition(UnitProgress.NOT_STARTED, UnitProgress.SKIPPED)
    require_transition(UnitProgress.SKIPPED, UnitProgress.IN_PROGRESS)
    require_transition(UnitProgress.IN_PROGRESS, UnitProgress.COMPLETED)
    with pytest.raises(ValidationAppError):
        require_transition(UnitProgress.COMPLETED, UnitProgress.COMPLETED)


def test_command_fingerprint_covers_position_status_and_expected_version():
    from dataclasses import replace

    command = ExposureCommand("p", "plan", "stage", "unit", UnitProgress.IN_PROGRESS, 0, "key")
    assert command.input_hash() == replace(command, idempotency_key="other").input_hash()
    assert len({command.input_hash(), replace(command, expected_version=1).input_hash(),
                replace(command, status=UnitProgress.SKIPPED).input_hash(),
                replace(command, unit_id="other").input_hash()}) == 4


def test_long_opaque_ids_supported_and_negative_expected_version_rejected():
    ExposureCommand("p", "plan", "stage", "u" * 400, UnitProgress.COMPLETED, 0, "key")
    with pytest.raises(ValidationAppError):
        ExposureCommand("p", "plan", "stage", "unit", UnitProgress.COMPLETED, -1, "key")


@pytest.mark.parametrize("override", [
    {"expected_version": -1}, {"expected_version": True}, {"expected_version": "0"},
    {"actor_id": "forged-client-actor"}, {"status": "verified"}, {"unit_id": "u" * 513},
])
def test_http_commands_reject_forged_identity_mastery_and_invalid_versions(override):
    from app.api.v1.exposure_schemas import ExposureChangeRequest
    from pydantic import ValidationError

    body = {"plan_id": "plan", "stage_id": "stage", "unit_id": "u" * 400,
            "status": "in_progress", "expected_version": 0, "idempotency_key": "key"}
    assert ExposureChangeRequest.model_validate(body).unit_id == "u" * 400
    with pytest.raises(ValidationError):
        ExposureChangeRequest.model_validate(body | override)


def test_missing_exposure_service_returns_explicit_503():
    from types import SimpleNamespace

    from app.api.v1.exposure_routes import get_exposure_service
    from app.core.errors import DependencyUnavailableError

    with pytest.raises(DependencyUnavailableError) as exc:
        get_exposure_service(SimpleNamespace())
    assert exc.value.http_status == 503
