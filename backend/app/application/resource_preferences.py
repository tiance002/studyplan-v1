"""Explicit resource settings: the most specific complete setting wins."""

from dataclasses import asdict

from app.core.errors import ValidationAppError
from app.domain.enums import PreferenceMode, PreferenceScope
from app.domain.resources.models import ResourcePreference, rank_resources, resolve_preference
from app.ports.resource_preferences import PreferenceLayers, ResourcePreferencesPort


class ResourcePreferenceService:
    def __init__(self, repository: ResourcePreferencesPort):
        self.repository = repository

    def get_context(self, scope, target):
        self._target(scope, target)
        return self._context(self.repository.get_context(scope, target), target)

    def resolve(self, scope, target) -> ResourcePreference:
        self._target(scope, target)
        layers = self.repository.get_context(scope, target)
        if layers.invalid_scopes:
            raise ValidationAppError("历史资料偏好需要显式修复后再使用", invalid_scopes=list(layers.invalid_scopes))
        return resolve_preference(project=layers.project, unit=layers.unit, node=layers.node)

    def rank(self, scope, target, resources):
        return rank_resources(resources, preference=self.resolve(scope, target))

    def project_default(self, scope, project_id):
        scope.require_project(project_id)
        return self.repository.project_default(scope, project_id)

    def put(self, scope, target, *, scope_name, mode, language="zh", official_priority=True,
            pace="normal", expected_version=0):
        self._target(scope, target)
        self._mutation(scope_name, target, expected_version)
        try:
            selected_mode = PreferenceMode(mode)
        except (ValueError, TypeError) as exc:
            raise ValidationAppError("资料形式偏好无效") from exc
        if not isinstance(language, str) or not 1 <= len(language.strip()) <= 16:
            raise ValidationAppError("资料语言需为1–16字符")
        try:
            language.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationAppError("资料语言含非法字符") from exc
        if not isinstance(official_priority, bool) or pace not in {"slow", "normal", "fast"}:
            raise ValidationAppError("资料偏好字段无效")
        setting = ResourcePreference(scope=PreferenceScope(scope_name),
            scope_ref=target["project_id"] if scope_name == "project" else target[f"{scope_name}_id"],
            mode=selected_mode, language=language.strip(), official_priority=official_priority,
            pace=pace, version=expected_version + 1)
        return self._context(self.repository.put(scope, target, setting, expected_version), target)

    def restore(self, scope, target, *, scope_name, expected_version):
        self._target(scope, target)
        self._mutation(scope_name, target, expected_version)
        return self._context(self.repository.restore(scope, target, scope_name, expected_version), target)

    @staticmethod
    def _target(scope, target):
        for name in ("project_id", "plan_id", "stage_id", "unit_id"):
            value = target.get(name)
            if not isinstance(value, str) or not 1 <= len(value) <= 512:
                raise ValidationAppError("资料偏好缺少有效路线位置")
        node = target.get("node_id")
        if node is not None and (not isinstance(node, str) or not 1 <= len(node) <= 512):
            raise ValidationAppError("知识节点位置无效")
        scope.require_project(target["project_id"])

    @staticmethod
    def _mutation(scope_name, target, expected_version):
        if scope_name not in {"project", "unit", "node"}:
            raise ValidationAppError("只能设置项目、单元或节点偏好")
        if scope_name == "node" and not target.get("node_id"):
            raise ValidationAppError("节点偏好需要指定单元内节点")
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 0:
            raise ValidationAppError("资料偏好版本无效")

    @staticmethod
    def _context(layers: PreferenceLayers, target):
        effective = (resolve_preference(project=layers.project, unit=layers.unit, node=layers.node)
                     if not layers.invalid_scopes else None)
        own = layers.node if target.get("node_id") else layers.unit
        own_scope = "node" if target.get("node_id") else "unit"
        return {"project": asdict(layers.project) if layers.project else None,
                "unit": asdict(layers.unit) if layers.unit else None,
                "node": asdict(layers.node) if layers.node else None,
                "effective": asdict(effective) if effective else None,
                "inherited": own is None and own_scope not in layers.invalid_scopes,
                "versions": dict(layers.versions), "invalid_scopes": list(layers.invalid_scopes)}
