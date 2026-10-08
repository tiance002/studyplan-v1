"""Explicit position progress and immutable contemporaneous source bindings."""
from contextlib import contextmanager
from datetime import date, datetime

import psycopg
from app.core.errors import ForbiddenError, IdempotencyConflictError, NotFoundError, VersionConflictError
from app.core.ids import new_id
from app.domain.enums import UnitProgress
from app.domain.learning_exposures import exposure_id, require_transition
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def _json(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


class PgLearningExposures:
    def __init__(self, dsn):
        self.dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _connection(self, scope, project_id, *, write=False):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                         (project_id, scope.actor_id))
            if write:
                # Generation holds this advisory lock before locking its job,
                # Run and owner row; interactive writers must match that order.
                lock_plan_version(conn, project_id, None)
            owner = conn.execute("SELECT project_id FROM learning_projects WHERE project_id=%s "
                "AND owner_actor_id=%s AND archived_at IS NULL" + (" FOR UPDATE" if write else ""),
                (project_id, scope.actor_id)).fetchone()
            if owner is None:
                raise ForbiddenError()
            yield conn

    @staticmethod
    def _plan(conn, project_id, plan_id, *, current=False):
        row = conn.execute("SELECT * FROM plan_revisions WHERE project_id=%s AND plan_id=%s",
                           (project_id, plan_id)).fetchone()
        if row is None:
            raise NotFoundError("路线版本不存在")
        if current and row["status"] != "approved":
            raise VersionConflictError("当前批准路线已变化，请刷新后再记录进度")
        return row

    @staticmethod
    def _position(conn, position):
        if conn.execute("SELECT unit_id FROM plan_unit_links WHERE project_id=%s AND plan_id=%s "
                        "AND stage_id=%s AND unit_id=%s", position).fetchone() is None:
            raise NotFoundError("学习单元不属于指定路线和阶段")

    @staticmethod
    def _snapshots(conn, position, plan):
        project, plan_id, stage, unit = position
        nodes = conn.execute("""SELECT n.node_id,n.stable_key,n.title,n.node_type,n.objectives,
            n.content_version,n.source_status,l.role,l.order_index FROM unit_node_links l
            JOIN knowledge_nodes n ON n.project_id=l.project_id AND n.node_id=l.node_id
            WHERE l.project_id=%s AND l.unit_id=%s ORDER BY l.order_index,l.node_id""",
            (project, unit)).fetchall()
        nodes = [dict(row, source_pack_key=plan["source_pack_key"],
                      source_pack_version=plan["source_pack_version"]) for row in nodes]
        public = conn.execute("SELECT * FROM stage_resource_assignments WHERE project_id=%s "
            "AND plan_id=%s AND stage_id=%s ORDER BY order_index,assignment_id",
            (project, plan_id, stage)).fetchall()
        private = conn.execute("""SELECT selection_id,resource_id,resource_snapshot,created_at
            FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s AND stage_id=%s
            AND unit_id=%s AND removed_at IS NULL ORDER BY created_at,selection_id""", position).fetchall()
        # Bindings are not reading/mastery evidence. Never fetch URLs here.
        sources = {"kind": "assigned_source_bindings", "public_assignments": public,
                   "private_selections": private}
        from app.domain.planning.v2_execution import V2ExecutionSnapshot
        v2 = V2ExecutionSnapshot.from_payload((plan["structure"] or {}).get("v2_execution"))
        if v2:
            sources["v2_content"] = v2.stage_content(stage,unit_id=unit)
        return _json(nodes), _json(sources)

    @staticmethod
    def _view(row):
        return _json({key: row[key] for key in ("exposure_id", "project_id", "plan_id", "stage_id",
            "unit_id", "status", "version", "node_snapshot", "source_snapshot", "updated_at")}
            | {"recorded": True})

    def list(self, scope, project_id, plan_id, stage_id=None):
        with self._connection(scope, project_id) as conn:
            plan = self._plan(conn, project_id, plan_id)
            if stage_id is not None and conn.execute("SELECT 1 FROM plan_stages WHERE project_id=%s "
                "AND plan_id=%s AND stage_id=%s", (project_id, plan_id, stage_id)).fetchone() is None:
                raise NotFoundError("阶段不属于指定路线")
            links = conn.execute("SELECT l.* FROM plan_unit_links l JOIN plan_stages s "
                "ON s.project_id=l.project_id AND s.plan_id=l.plan_id AND s.stage_id=l.stage_id "
                "WHERE l.project_id=%s AND l.plan_id=%s" + (" AND l.stage_id=%s" if stage_id else "")
                + " ORDER BY s.order_index,l.order_index,l.unit_id",
                (project_id, plan_id, stage_id) if stage_id else (project_id, plan_id)).fetchall()
            result = []
            for link in links:
                position = (project_id, plan_id, link["stage_id"], link["unit_id"])
                identifier = exposure_id(*position)
                row = conn.execute("SELECT * FROM learning_exposures WHERE project_id=%s AND exposure_id=%s",
                                   (project_id, identifier)).fetchone()
                if row is not None:
                    view = self._view(row)
                else:
                    nodes, sources = self._snapshots(conn, position, plan)
                    view = dict(zip(("project_id", "plan_id", "stage_id", "unit_id"), position, strict=True))
                    view.update(exposure_id=identifier, status="not_started", version=0, recorded=False,
                                node_snapshot=nodes, source_snapshot=sources, updated_at=None)
                result.append(view)
            return result

    def change(self, scope, command):
        with self._connection(scope, command.project_id, write=True) as conn:
            plan = self._plan(conn, command.project_id, command.plan_id)
            self._position(conn, command.position)
            previous = conn.execute("SELECT input_hash,response_snapshot FROM learning_exposure_events "
                "WHERE project_id=%s AND actor_id=%s AND idempotency_key=%s",
                (command.project_id, scope.actor_id, command.idempotency_key)).fetchone()
            if previous is not None:
                if previous["input_hash"] != command.input_hash():
                    raise IdempotencyConflictError()
                return dict(previous["response_snapshot"], replayed=True)
            self._plan(conn, command.project_id, command.plan_id, current=True)
            identifier = exposure_id(*command.position)
            current = conn.execute("SELECT * FROM learning_exposures WHERE project_id=%s AND exposure_id=%s",
                                   (command.project_id, identifier)).fetchone()
            version = current["version"] if current else 0
            if version != command.expected_version:
                raise VersionConflictError(expected_version=command.expected_version, actual_version=version)
            before = UnitProgress(current["status"]) if current else UnitProgress.NOT_STARTED
            require_transition(before, command.status)
            nodes, sources = self._snapshots(conn, command.position, plan)
            row = conn.execute("""INSERT INTO learning_exposures(exposure_id,project_id,plan_id,stage_id,unit_id,
                status,version,node_snapshot,source_snapshot,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp())
                ON CONFLICT(exposure_id) DO UPDATE SET status=excluded.status,version=excluded.version,
                node_snapshot=excluded.node_snapshot,source_snapshot=excluded.source_snapshot,
                updated_at=excluded.updated_at RETURNING *""",
                (identifier, *command.position, command.status.value, version+1, Jsonb(nodes), Jsonb(sources))).fetchone()
            view = self._view(row)
            event = {"event_id": new_id("expevt"), "exposure_id": identifier,
                     **dict(zip(("project_id", "plan_id", "stage_id", "unit_id"), command.position, strict=True)),
                     "actor_id": scope.actor_id, "from_status": before.value, "to_status": command.status.value,
                     "expected_version": version, "version": version+1,
                     "node_snapshot": nodes, "source_snapshot": sources, "created_at": view["updated_at"]}
            response = {"exposure": view, "event": event, "replayed": False}
            conn.execute("""INSERT INTO learning_exposure_events(event_id,project_id,exposure_id,actor_id,
                idempotency_key,input_hash,from_status,to_status,expected_version,version,node_snapshot,
                source_snapshot,response_snapshot,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (event["event_id"], command.project_id, identifier, scope.actor_id, command.idempotency_key,
                 command.input_hash(), before.value, command.status.value, version, version+1,
                 Jsonb(nodes), Jsonb(sources), Jsonb(response), row["updated_at"]))
            return response

    def history(self, scope, project_id, plan_id, stage_id, unit_id):
        with self._connection(scope, project_id) as conn:
            self._plan(conn, project_id, plan_id)
            position = (project_id, plan_id, stage_id, unit_id)
            self._position(conn, position)
            rows = conn.execute("SELECT response_snapshot FROM learning_exposure_events "
                "WHERE project_id=%s AND exposure_id=%s ORDER BY version",
                (project_id, exposure_id(*position))).fetchall()
            return [row["response_snapshot"]["event"] for row in rows]
