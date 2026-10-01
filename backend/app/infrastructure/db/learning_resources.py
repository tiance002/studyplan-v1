"""Short transactions: reserve before HTTP, select metadata atomically, keep history."""
from contextlib import contextmanager

import psycopg
from app.core.errors import (
    AppError,
    ErrorCode,
    ForbiddenError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.ids import new_id
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from app.infrastructure.resources.tavily import safe_candidate_url
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class PgLearningResources:
    def __init__(self, dsn):
        self.dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _connection(self, scope, target, *, current=False, lock=False):
        scope.require_project(target["project_id"])
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                         (target["project_id"], scope.actor_id))
            if current:
                # Generation locks plan decision before its job/Run/owner rows.
                # Reuse that order and validate approved only after the wait.
                lock_plan_version(conn, target["project_id"], None)
            owner = conn.execute("SELECT project_id FROM learning_projects WHERE project_id=%s "
                "AND owner_actor_id=%s AND archived_at IS NULL" + (" FOR UPDATE" if lock else ""),
                (target["project_id"], scope.actor_id)).fetchone()
            if owner is None:
                raise ForbiddenError()
            found = conn.execute("""SELECT l.unit_id FROM plan_unit_links l JOIN plan_revisions r
                ON r.project_id=l.project_id AND r.plan_id=l.plan_id
                WHERE l.project_id=%s AND l.plan_id=%s AND l.stage_id=%s AND l.unit_id=%s"""
                + (" AND r.status='approved'" if current else ""),
                self._position(target)).fetchone()
            if found is None:
                raise NotFoundError("学习单元不属于指定路线版本，或当前版本已变化")
            yield conn

    @staticmethod
    def _position(target):
        return tuple(target[key] for key in ("project_id", "plan_id", "stage_id", "unit_id"))

    @staticmethod
    def _search_view(row):
        return {key: row[key] for key in ("search_id", "status", "query", "candidates", "error", "created_at")}

    @staticmethod
    def _selection_view(row):
        return {"selection_id": row["selection_id"], "resource": row["resource_snapshot"],
                "created_at": row["created_at"]}

    def reserve(self, scope, target, query, key, input_hash, limit):
        with self._connection(scope, target, current=True, lock=True) as conn:
            previous = conn.execute("SELECT * FROM resource_search_requests WHERE project_id=%s "
                "AND actor_id=%s AND idempotency_key=%s", (target["project_id"], scope.actor_id, key)).fetchone()
            if previous is not None:
                if previous["input_hash"] != input_hash:
                    raise IdempotencyConflictError()
                return self._search_view(previous), False
            debit = conn.execute("UPDATE search_usage_counter SET request_count=request_count+1 "
                "WHERE singleton AND request_count<%s RETURNING request_count", (min(1000, limit),)).fetchone()
            if debit is None:
                raise AppError(ErrorCode.RATE_LIMITED, "搜索请求额度已用完；可以手动接入资料")
            row = conn.execute("""INSERT INTO resource_search_requests(
                search_id,project_id,plan_id,stage_id,unit_id,actor_id,idempotency_key,input_hash,query,status)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'dispatched') RETURNING *""",
                (new_id("search"), *self._position(target), scope.actor_id, key, input_hash, query)).fetchone()
            return self._search_view(row), True

    def finish(self, scope, target, search_id, status, candidates, error):
        with self._connection(scope, target) as conn:
            row = conn.execute("""UPDATE resource_search_requests SET status=%s,candidates=%s,error=%s,
                updated_at=now() WHERE search_id=%s AND project_id=%s AND plan_id=%s AND stage_id=%s
                AND unit_id=%s AND actor_id=%s AND status='dispatched' RETURNING *""",
                (status, Jsonb(candidates), error, search_id, *self._position(target), scope.actor_id)).fetchone()
            if row is None:
                raise NotFoundError("搜索请求已变化，请刷新查看保留的结果")
            return self._search_view(row)

    def get_search(self, scope, target, search_id):
        with self._connection(scope, target) as conn:
            row = conn.execute("""SELECT * FROM resource_search_requests WHERE search_id=%s
                AND project_id=%s AND plan_id=%s AND stage_id=%s AND unit_id=%s AND actor_id=%s""",
                (search_id, *self._position(target), scope.actor_id)).fetchone()
            if row is None:
                raise NotFoundError("该搜索不属于指定学习单元")
            return self._search_view(row)

    def get_search_by_key(self, scope, target, key):
        with self._connection(scope, target) as conn:
            row = conn.execute("""SELECT * FROM resource_search_requests WHERE idempotency_key=%s
                AND project_id=%s AND plan_id=%s AND stage_id=%s AND unit_id=%s AND actor_id=%s""",
                (key, *self._position(target), scope.actor_id)).fetchone()
            if row is None:
                raise NotFoundError("尚未发现此查询的持久提交；没有重新发起搜索")
            return self._search_view(row)

    def list_selected(self, scope, target):
        with self._connection(scope, target) as conn:
            rows = conn.execute("""SELECT * FROM learning_resource_selections WHERE project_id=%s
                AND plan_id=%s AND stage_id=%s AND unit_id=%s AND removed_at IS NULL
                ORDER BY created_at,selection_id""", self._position(target)).fetchall()
            return [self._selection_view(row) for row in rows]

    def select(self, scope, target, resource):
        # Search results and manual URLs remain display-only, unverified records.
        if safe_candidate_url(resource.get("url")) is None:
            raise ValidationAppError("仅允许安全的外部HTTP/HTTPS资料地址")
        if resource.get("project_id") != target["project_id"] or resource.get("verification_status") != "unverified":
            raise ValidationAppError("资源候选的项目或核验状态不合法")
        with self._connection(scope, target, current=True, lock=True) as conn:
            conn.execute("""INSERT INTO resource_records(resource_id,project_id,url,title,media_type,
                language,section_anchor,checked_at,verification_status,provenance)
                VALUES(%s,%s,%s,%s,%s,%s,%s,NULL,'unverified',%s)
                ON CONFLICT(project_id,url) DO NOTHING""",
                (resource["resource_id"], target["project_id"], resource["url"], resource["title"],
                 resource["media_type"], resource["language"], resource.get("section_anchor"), resource["provenance"]))
            private = conn.execute("SELECT resource_id FROM resource_records WHERE project_id=%s AND url=%s",
                                   (target["project_id"], resource["url"])).fetchone()
            previous = conn.execute("""SELECT * FROM learning_resource_selections WHERE project_id=%s
                AND plan_id=%s AND stage_id=%s AND unit_id=%s AND resource_id=%s AND removed_at IS NULL""",
                (*self._position(target), private["resource_id"])).fetchone()
            if previous is not None:
                return self._selection_view(previous)
            snapshot = dict(resource, resource_id=private["resource_id"])
            row = conn.execute("""INSERT INTO learning_resource_selections(
                selection_id,project_id,plan_id,stage_id,unit_id,resource_id,resource_snapshot)
                VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (new_id("selection"), *self._position(target), private["resource_id"], Jsonb(snapshot))).fetchone()
            return self._selection_view(row)

    def remove(self, scope, target, selection_id):
        with self._connection(scope, target, current=True, lock=True) as conn:
            row = conn.execute("""UPDATE learning_resource_selections SET removed_at=coalesce(removed_at,now())
                WHERE selection_id=%s AND project_id=%s AND plan_id=%s AND stage_id=%s AND unit_id=%s
                RETURNING selection_id""", (selection_id, *self._position(target))).fetchone()
            if row is None:
                raise NotFoundError("资料选择不属于此学习单元")
            return True
