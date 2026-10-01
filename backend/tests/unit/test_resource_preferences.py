"""Whole-setting inheritance and explicit scoped preference mutations."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest
from app.application.resource_preferences import ResourcePreferenceService
from app.core.errors import ForbiddenError, ValidationAppError
from app.domain.enums import PreferenceMode, PreferenceScope
from app.domain.resources.models import ResourcePreference
from app.domain.workspace.models import AuthContext
from app.ports.resource_preferences import PreferenceLayers


class LayersRepository:
    def __init__(self, layers):
        self.layers = layers

    def get_context(self, scope, target):
        return self.layers

    def put(self, scope, target, preference, expected_version):
        self.layers = replace(self.layers, **{preference.scope.value: preference})
        return self.layers


def scope():
    return AuthContext("actor", "session", datetime.now(timezone.utc), ("project",))


def target(node=False):
    return {"project_id": "project", "plan_id": "plan", "stage_id": "stage", "unit_id": "unit",
            "node_id": "node" if node else None}


def test_node_setting_replaces_every_field_instead_of_merging():
    project = ResourcePreference(PreferenceScope.PROJECT, "project", PreferenceMode.TEXT_FIRST, "zh", True, "slow", 4)
    unit = ResourcePreference(PreferenceScope.UNIT, "unit", PreferenceMode.MIXED, "zh", True, "normal", 2)
    node = ResourcePreference(PreferenceScope.NODE, "node", PreferenceMode.VIDEO_FIRST, "en", False, "fast", 3)
    service = ResourcePreferenceService(LayersRepository(PreferenceLayers(project, unit, node, {"project": 4, "unit": 2, "node": 3})))
    context = service.get_context(scope(), target(node=True))
    assert context["effective"] == {"scope": PreferenceScope.NODE, "scope_ref": "node",
        "mode": PreferenceMode.VIDEO_FIRST, "language": "en", "official_priority": False, "pace": "fast", "version": 3}
    assert context["inherited"] is False
    assert service.resolve(scope(), target(node=True)) == node


def test_deleted_node_inherits_unit_but_retains_cas_version():
    unit = ResourcePreference(PreferenceScope.UNIT, "unit", PreferenceMode.VIDEO_FIRST, "en", False, "fast", 2)
    service = ResourcePreferenceService(LayersRepository(PreferenceLayers(None, unit, None, {"project": 0, "unit": 2, "node": 7})))
    context = service.get_context(scope(), target(node=True))
    assert context["node"] is None and context["versions"]["node"] == 7
    assert context["effective"]["scope"] == PreferenceScope.UNIT
    assert context["effective"]["language"] == "en"
    assert context["inherited"] is True


def test_empty_settings_inherit_system_default():
    service = ResourcePreferenceService(LayersRepository(PreferenceLayers()))
    context = service.get_context(scope(), target())
    assert context["project"] is context["unit"] is context["node"] is None
    assert context["effective"]["scope"] == PreferenceScope.SYSTEM
    assert context["versions"] == {"project": 0, "unit": 0, "node": 0}
    assert context["inherited"] is True


def test_put_derives_node_ref_from_authorized_position():
    service = ResourcePreferenceService(LayersRepository(PreferenceLayers()))
    context = service.put(scope(), target(node=True), scope_name="node", mode="text_first", language="zh",
                          official_priority=True, pace="slow", expected_version=0)
    assert context["node"]["scope_ref"] == "node"
    assert context["node"]["pace"] == "slow"
    assert context["project"] is None and context["unit"] is None


@pytest.mark.parametrize("changes", [{"scope_name": "system"}, {"scope_name": "node"}, {"mode": "text"},
    {"language": ""}, {"language": "a" * 17}, {"language": "\ud800"}, {"pace": "unbounded"}, {"expected_version": -1}])
def test_invalid_updates_are_rejected_before_persistence(changes):
    service = ResourcePreferenceService(LayersRepository(PreferenceLayers()))
    arguments = {"scope_name": "unit", "mode": "mixed", "language": "zh", "official_priority": True,
                 "pace": "normal", "expected_version": 0, **changes}
    with pytest.raises(ValidationAppError):
        service.put(scope(), target(), **arguments)


def test_forged_project_scope_rejected():
    service = ResourcePreferenceService(LayersRepository(PreferenceLayers()))
    with pytest.raises(ForbiddenError):
        service.get_context(scope(), dict(target(), project_id="other"))


def test_preference_api_requires_explicit_version_and_server_derived_ref():
    from app.api.v1.preference_schemas import PreferencePutRequest
    from pydantic import ValidationError

    body = {"plan_id": "plan", "stage_id": "stage", "unit_id": "unit", "scope": "unit", "mode": "mixed"}
    with pytest.raises(ValidationError):
        PreferencePutRequest(**body)
    with pytest.raises(ValidationError):
        PreferencePutRequest(**body, expected_version=0, scope_ref="foreign")
    with pytest.raises(ValidationError):
        PreferencePutRequest(**dict(body, scope="system"), expected_version=0)
    assert PreferencePutRequest(**body, expected_version=0).expected_version == 0
