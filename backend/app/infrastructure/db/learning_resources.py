"""Short transactions: reserve before HTTP, select metadata atomically, keep history."""
import hashlib
import json
from contextlib import contextmanager

import psycopg
from app.application.resource_discovery_contract import (
    DiscoveryEvidence,
    ResourceCandidateSnapshot,
)
from app.core.errors import (
    AppError,
    ErrorCode,
    ForbiddenError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.ids import new_id
from app.domain.resources.discovery import validate_private_mapping
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from app.infrastructure.resources.tavily import safe_candidate_url
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import ValidationError


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
            if target.get("node_id"):
                member = conn.execute("SELECT node_id FROM unit_node_links WHERE project_id=%s AND unit_id=%s AND node_id=%s",
                    (target["project_id"], target["unit_id"], target["node_id"])).fetchone()
                if member is None:
                    raise NotFoundError("知识节点不属于指定学习单元")
            yield conn

    @staticmethod
    def _position(target):
        return tuple(target[key] for key in ("project_id", "plan_id", "stage_id", "unit_id"))

    @staticmethod
    def _search_view(row):
        result = {key: row[key] for key in ("search_id", "status", "query", "candidates", "error", "created_at",
            "source", "context_snapshot", "input_hash")}
        result["candidates"] = [PgLearningResources._candidate(item, row["project_id"]) for item in row["candidates"]]
        return result

    @staticmethod
    def _candidate(resource, project_id):
        if (not isinstance(resource, dict) or resource.get("project_id") != project_id
                or safe_candidate_url(resource.get("url")) is None):
            raise ValidationAppError("资源候选范围或地址无效")
        try:
            result = ResourceCandidateSnapshot.model_validate(resource).model_dump(mode="json")
        except ValidationError as exc:
            raise ValidationAppError("资源发现证据无效") from exc
        return result

    @staticmethod
    def _inspection_view(row):
        return {**{key: row[key] for key in ("inspection_id", "status", "search_id", "candidate_id", "receipts",
                    "error", "created_at", "input_hash", "context_snapshot")},
                "candidate": PgLearningResources._candidate(row["candidate_snapshot"], row["project_id"])
                    if row["candidate_snapshot"] else None}

    @staticmethod
    def _selection_view(row):
        return {"selection_id": row["selection_id"], "resource": PgLearningResources._candidate(row["resource_snapshot"], row["project_id"]),
                "created_at": row["created_at"]}

    def check_search_intent(self, scope, target, key, input_hash):
        with self._connection(scope, target) as conn:
            previous = conn.execute("SELECT input_hash FROM resource_search_requests WHERE project_id=%s AND actor_id=%s AND idempotency_key=%s",
                (target["project_id"], scope.actor_id, key)).fetchone()
            if previous is not None and previous["input_hash"] != input_hash:
                raise IdempotencyConflictError()

    def reserve(self, scope, target, query, key, input_hash, limit, *, source="web", context_snapshot=None):
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
                search_id,project_id,plan_id,stage_id,unit_id,actor_id,idempotency_key,input_hash,query,status,
                source,context_snapshot,node_id)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'dispatched',%s,%s,%s) RETURNING *""",
                (new_id("search"), *self._position(target), scope.actor_id, key, input_hash, query,
                 source, Jsonb(context_snapshot or {}), target.get("node_id"))).fetchone()
            return self._search_view(row), True

    def finish(self, scope, target, search_id, status, candidates, error):
        candidates = [self._candidate(item, target["project_id"]) for item in candidates]
        with self._connection(scope, target) as conn:
            row = conn.execute("""UPDATE resource_search_requests SET status=%s,candidates=%s,error=%s,
                updated_at=now() WHERE search_id=%s AND project_id=%s AND plan_id=%s AND stage_id=%s
                AND unit_id=%s AND actor_id=%s AND node_id IS NOT DISTINCT FROM %s
                AND status='dispatched' RETURNING *""",
                (status, Jsonb(candidates), error, search_id, *self._position(target), scope.actor_id, target.get("node_id"))).fetchone()
            if row is None:
                raise NotFoundError("搜索请求已变化，请刷新查看保留的结果")
            return self._search_view(row)

    def get_search(self, scope, target, search_id):
        return self._read_search(scope, target, "search_id", search_id)

    def get_search_by_key(self, scope, target, key):
        return self._read_search(scope, target, "idempotency_key", key)

    @staticmethod
    def _matches_search_node(row, target):
        if row["source"] == "web" and row["node_id"] is None and not row["context_snapshot"]:
            # Pre-0024 rows did not store node_id. The original immutable intent
            # hash can prove the exact node without guessing or backfilling it.
            old_hash = hashlib.sha256(json.dumps([target, row["query"]], sort_keys=True).encode()).hexdigest()
            return row["input_hash"] == old_hash
        return row["node_id"] == target.get("node_id")

    def _read_search(self, scope, target, column, value):
        with self._connection(scope, target) as conn:
            row = conn.execute(f"SELECT * FROM resource_search_requests WHERE {column}=%s "
                "AND project_id=%s AND plan_id=%s AND stage_id=%s AND unit_id=%s AND actor_id=%s",
                (value, *self._position(target), scope.actor_id)).fetchone()
            if row is None or not self._matches_search_node(row, target):
                raise NotFoundError("该搜索不属于指定学习单元")
            return self._search_view(row)

    @staticmethod
    def _latest(conn, scope, target, search_id, candidate_id):
        return conn.execute("""SELECT * FROM resource_inspection_requests WHERE project_id=%s AND plan_id=%s
            AND stage_id=%s AND unit_id=%s AND actor_id=%s AND search_id=%s AND candidate_id=%s AND status='succeeded'
            AND context_snapshot->>'node_id' IS NOT DISTINCT FROM %s ORDER BY updated_at DESC,inspection_id DESC LIMIT 1""",
            (*PgLearningResources._position(target), scope.actor_id, search_id, candidate_id, target.get("node_id"))).fetchone()

    def latest_inspection(self, scope, target, search_id, candidate_id):
        with self._connection(scope, target) as conn:
            row = self._latest(conn, scope, target, search_id, candidate_id)
            return self._inspection_view(row) if row else None

    def reserve_inspection(self, scope, target, search_id, candidate_id, key, input_hash, paths,
                           context_snapshot, content_limit, metadata_limit):
        with self._connection(scope, target, current=True, lock=True) as conn:
            previous = conn.execute("SELECT * FROM resource_inspection_requests WHERE project_id=%s AND actor_id=%s AND idempotency_key=%s",
                (target["project_id"], scope.actor_id, key)).fetchone()
            if previous is not None:
                if previous["input_hash"] != input_hash:
                    raise IdempotencyConflictError()
                return self._inspection_view(previous), False
            search = conn.execute("""SELECT * FROM resource_search_requests WHERE search_id=%s AND project_id=%s
                AND plan_id=%s AND stage_id=%s AND unit_id=%s AND actor_id=%s AND node_id IS NOT DISTINCT FROM %s""",
                (search_id, *self._position(target), scope.actor_id, target.get("node_id"))).fetchone()
            if search is None:
                raise NotFoundError("搜索不属于指定学习位置")
            if search["status"] != "succeeded" or search["source"] != "github":
                raise ValidationAppError("只能检查已成功的GitHub搜索")
            resource = next((c for c in self._search_view(search)["candidates"] if c["resource_id"] == candidate_id), None)
            if resource is None:
                raise NotFoundError("候选不属于指定搜索")
            latest = self._latest(conn, scope, target, search_id, candidate_id)
            if latest:
                resource = self._inspection_view(latest)["candidate"]
            evidence = DiscoveryEvidence.model_validate(resource["discovery"])
            if evidence.source != "github" or evidence.repo is None:
                raise ValidationAppError("候选缺少GitHub仓库发现证据")
            if paths:
                chapters = resource["discovery"]["chapters"]
                allowlist = {c["path"]: c["order"] for c in chapters if c["status"] in {"listed", "read"}}
                if len(set(paths)) != len(paths) or any(p not in allowlist for p in paths):
                    raise ValidationAppError("检查路径必须来自已实际读取的README章节索引")
                orders = [allowlist[p] for p in paths]
                if orders != sorted(orders):
                    raise ValidationAppError("检查章节必须保留作者顺序")
            debit = conn.execute("""UPDATE resource_read_usage_counter SET content_reserved=content_reserved+3,
                metadata_reserved=metadata_reserved+2 WHERE singleton AND content_reserved+3<=%s
                AND metadata_reserved+2<=%s RETURNING content_reserved,metadata_reserved""",
                (min(3000, content_limit), min(2000, metadata_limit))).fetchone()
            if debit is None:
                raise AppError(ErrorCode.RATE_LIMITED, "教程检查读取额度已用完；可以手动接入资料")
            # Only the authoritative search snapshot supplies frozen context.
            context = dict(search["context_snapshot"], node_id=target.get("node_id"))
            row = conn.execute("""INSERT INTO resource_inspection_requests(inspection_id,project_id,plan_id,stage_id,
                unit_id,actor_id,search_id,candidate_id,idempotency_key,input_hash,status,paths,context_snapshot,candidate_snapshot)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'dispatched',%s,%s,%s) RETURNING *""",
                (new_id("inspect"), *self._position(target), scope.actor_id, search_id, candidate_id, key, input_hash,
                 Jsonb(paths), Jsonb(context), Jsonb(resource))).fetchone()
            return self._inspection_view(row), True

    def finish_inspection(self, scope, target, inspection_id, status, candidate, receipts, error):
        candidate = self._candidate(candidate, target["project_id"]) if candidate else {}
        with self._connection(scope, target) as conn:
            row = conn.execute("""UPDATE resource_inspection_requests SET status=%s,candidate_snapshot=%s,receipts=%s,
                error=%s,updated_at=clock_timestamp() WHERE inspection_id=%s AND project_id=%s AND plan_id=%s AND stage_id=%s
                AND unit_id=%s AND actor_id=%s AND context_snapshot->>'node_id' IS NOT DISTINCT FROM %s
                AND status='dispatched' RETURNING *""",
                (status, Jsonb(candidate), Jsonb(receipts), error, inspection_id, *self._position(target), scope.actor_id,
                 target.get("node_id"))).fetchone()
            if row is None:
                raise NotFoundError("教程检查请求已变化，请刷新查看保留结果")
            return self._inspection_view(row)

    def get_inspection(self, scope, target, inspection_id):
        return self._read_inspection(scope, target, "inspection_id", inspection_id)

    def get_inspection_by_key(self, scope, target, key):
        return self._read_inspection(scope, target, "idempotency_key", key)

    def _read_inspection(self, scope, target, column, value):
        with self._connection(scope, target) as conn:
            row = conn.execute(f"SELECT * FROM resource_inspection_requests WHERE {column}=%s AND project_id=%s AND plan_id=%s "
                "AND stage_id=%s AND unit_id=%s AND actor_id=%s AND context_snapshot->>'node_id' IS NOT DISTINCT FROM %s",
                (value, *self._position(target), scope.actor_id, target.get("node_id"))).fetchone()
            if row is None:
                raise NotFoundError("该教程检查不属于指定学习位置")
            return self._inspection_view(row)

    def list_selected(self, scope, target):
        with self._connection(scope, target) as conn:
            rows = conn.execute("""SELECT * FROM learning_resource_selections WHERE project_id=%s
                AND plan_id=%s AND stage_id=%s AND unit_id=%s AND removed_at IS NULL
                ORDER BY created_at,selection_id""", self._position(target)).fetchall()
            return [self._selection_view(row) for row in rows]

    @staticmethod
    def _allowed_module_keys(conn, target):
        return [row["stable_key"] for row in conn.execute("""SELECT n.stable_key FROM unit_node_links l
            JOIN knowledge_nodes n ON n.project_id=l.project_id AND n.node_id=l.node_id
            WHERE l.project_id=%s AND l.unit_id=%s ORDER BY l.order_index""",
            (target["project_id"], target["unit_id"])).fetchall()]

    def allowed_module_keys(self, scope, target):
        with self._connection(scope, target, current=True) as conn:
            return self._allowed_module_keys(conn, target)

    def select(self, scope, target, resource):
        resource = self._candidate(resource, target["project_id"])
        # Search results and manual URLs remain display-only, unverified records.
        if safe_candidate_url(resource.get("url")) is None:
            raise ValidationAppError("仅允许安全的外部HTTP/HTTPS资料地址")
        if resource.get("project_id") != target["project_id"] or resource.get("verification_status") != "unverified":
            raise ValidationAppError("资源候选的项目或核验状态不合法")
        with self._connection(scope, target, current=True, lock=True) as conn:
            validate_private_mapping(DiscoveryEvidence.model_validate(resource["discovery"]),
                                     self._allowed_module_keys(conn, target))
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
            snapshot = dict(resource, resource_id=private["resource_id"])
            if previous is not None:
                if self._selection_view(previous)["resource"] == snapshot:
                    return self._selection_view(previous)
                # Explicit reselection preserves the old snapshot and creates
                # a fresh private binding for changed read/mapping evidence.
                conn.execute("UPDATE learning_resource_selections SET removed_at=clock_timestamp() WHERE selection_id=%s",
                             (previous["selection_id"],))
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
