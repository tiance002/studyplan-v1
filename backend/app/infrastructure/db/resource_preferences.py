"""Scoped persistent settings; logical deletion retains monotonic CAS versions."""

from contextlib import contextmanager

import psycopg
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.ids import new_id
from app.domain.enums import PreferenceMode, PreferenceScope
from app.domain.resources.models import ResourcePreference, resolve_preference
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from app.ports.resource_preferences import PreferenceLayers
from psycopg.rows import dict_row


class PgResourcePreferences:
    def __init__(self, dsn: str):
        self.dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _connection(self, scope, target, *, write=False, position=True):
        scope.require_project(target["project_id"])
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",
                         (scope.actor_id, target["project_id"]))
            if write:
                # Generation/publication take the shared advisory lock before
                # their project fence rows; keep one order to avoid a cycle.
                lock_plan_version(conn, target["project_id"], None)
            owner = conn.execute("SELECT project_id FROM learning_projects WHERE project_id=%s "
                "AND owner_actor_id=%s AND archived_at IS NULL" + (" FOR UPDATE" if write else ""),
                (target["project_id"], scope.actor_id)).fetchone()
            if owner is None:
                raise ForbiddenError("无权设置此学习空间资料偏好")
            if position:
                unit = conn.execute("""SELECT l.unit_id FROM plan_unit_links l JOIN plan_revisions r
                    ON r.project_id=l.project_id AND r.plan_id=l.plan_id
                    WHERE l.project_id=%s AND l.plan_id=%s AND l.stage_id=%s AND l.unit_id=%s"""
                    + (" AND r.status='approved'" if write else ""),
                    tuple(target[name] for name in ("project_id", "plan_id", "stage_id", "unit_id"))).fetchone()
                if unit is None:
                    raise NotFoundError("资料偏好位置不属于指定路线或当前版本已变化")
                if target.get("node_id"):
                    node = conn.execute("""SELECT l.node_id FROM unit_node_links l JOIN knowledge_nodes n
                        ON n.node_id=l.node_id AND n.project_id=l.project_id
                        WHERE l.project_id=%s AND l.unit_id=%s AND l.node_id=%s""",
                        (target["project_id"], target["unit_id"], target["node_id"])).fetchone()
                    if node is None:
                        raise NotFoundError("资料偏好节点不属于指定学习单元")
            yield conn

    @staticmethod
    def _row(conn, project_id, scope_name, scope_ref):
        if scope_name == "project":
            rows = conn.execute("SELECT * FROM preferences WHERE project_id=%s AND scope='project' "
                "AND (scope_ref=%s OR scope_ref='' OR scope_ref IS NULL)", (project_id, project_id)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM preferences WHERE project_id=%s AND scope=%s AND scope_ref=%s",
                                (project_id, scope_name, scope_ref)).fetchall()
        if len(rows) > 1:
            raise ConflictError("存在多个历史资料偏好记录，请核对后再设置", reason="preference_ambiguous")
        return rows[0] if rows else None

    @staticmethod
    def _setting(row, scope_name, scope_ref):
        if row is None or row["deleted_at"] is not None:
            return None
        try:
            mode = PreferenceMode(row["media_type"])
        except (ValueError, TypeError) as exc:
            raise ValidationAppError("历史资料偏好形式无法解释，请显式重新设置",
                                     reason="legacy_preference_mode", version=row["version"]) from exc
        language, pace = row["language"], row["pace"]
        if not isinstance(language, str) or not 1 <= len(language.strip()) <= 16 or pace not in {"slow", "normal", "fast"}:
            raise ValidationAppError("历史资料偏好字段无法解释，请显式重新设置",
                                     reason="legacy_preference_fields", version=row["version"])
        return ResourcePreference(scope=PreferenceScope(scope_name), scope_ref=scope_ref, mode=mode,
            language=language, official_priority=row["official_priority"], pace=pace, version=row["version"])

    def _layers(self, conn, target):
        settings, versions, invalid = {}, {}, []
        for name in ("project", "unit", "node"):
            ref = target["project_id"] if name == "project" else target.get(f"{name}_id")
            row = self._row(conn, target["project_id"], name, ref) if ref else None
            versions[name] = int(row["version"]) if row else 0
            try:
                settings[name] = self._setting(row, name, ref) if ref else None
            except ValidationAppError:
                settings[name] = None
                invalid.append(name)
        return PreferenceLayers(**settings, versions=versions, invalid_scopes=tuple(invalid))

    def get_context(self, scope, target):
        with self._connection(scope, target) as conn:
            return self._layers(conn, target)

    def project_default(self, scope, project_id):
        with self._connection(scope, {"project_id": project_id}, position=False) as conn:
            row = self._row(conn, project_id, "project", project_id)
            return resolve_preference(project=self._setting(row, "project", project_id))

    @staticmethod
    def _check_version(row, expected_version):
        actual = int(row["version"]) if row else 0
        if actual != expected_version:
            raise ConflictError("资料偏好版本已变化，请刷新后重试", reason="preference_stale",
                                expected_version=expected_version, actual_version=actual)

    @staticmethod
    def _scope_ref(target, scope_name):
        if scope_name not in {"project", "unit", "node"}:
            raise ValidationAppError("只能设置项目、单元或节点偏好")
        ref = target["project_id"] if scope_name == "project" else target.get(f"{scope_name}_id")
        if not ref:
            raise ValidationAppError("资料偏好范围缺少位置")
        return ref

    def put(self, scope, target, preference, expected_version):
        name = preference.scope.value
        ref = self._scope_ref(target, name)
        if preference.scope_ref != ref:
            raise ValidationAppError("资料偏好范围与指定位置不一致")
        with self._connection(scope, target, write=True) as conn:
            row = self._row(conn, target["project_id"], name, ref)
            self._check_version(row, expected_version)
            fields = (ref, preference.mode.value, preference.language, preference.official_priority, preference.pace)
            if row is None:
                conn.execute("""INSERT INTO preferences(preference_id,project_id,scope,scope_ref,media_type,
                    language,official_priority,pace,version) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,1)""",
                    (new_id("pref"), target["project_id"], name, *fields))
            else:
                changed = conn.execute("""UPDATE preferences SET scope_ref=%s,media_type=%s,language=%s,
                    official_priority=%s,pace=%s,deleted_at=NULL,version=version+1,updated_at=clock_timestamp()
                    WHERE preference_id=%s AND project_id=%s AND version=%s""",
                    (*fields, row["preference_id"], target["project_id"], expected_version))
                if changed.rowcount != 1:
                    raise ConflictError("资料偏好版本已变化", reason="preference_stale")
            return self._layers(conn, target)

    def restore(self, scope, target, scope_name, expected_version):
        ref = self._scope_ref(target, scope_name)
        with self._connection(scope, target, write=True) as conn:
            row = self._row(conn, target["project_id"], scope_name, ref)
            self._check_version(row, expected_version)
            if row is not None and row["deleted_at"] is None:
                changed = conn.execute("""UPDATE preferences SET scope_ref=%s,deleted_at=clock_timestamp(),
                    version=version+1,updated_at=clock_timestamp() WHERE preference_id=%s AND project_id=%s AND version=%s""",
                    (ref, row["preference_id"], target["project_id"], expected_version))
                if changed.rowcount != 1:
                    raise ConflictError("资料偏好版本已变化", reason="preference_stale")
            return self._layers(conn, target)
