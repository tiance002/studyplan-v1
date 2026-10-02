"""Transaction-bound resource previews and existing plan publication."""
from contextlib import contextmanager
from dataclasses import asdict, replace

import psycopg
from app.application.plan_resources import resolve_stage_resources
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
    VersionConflictError,
)
from app.core.ids import content_hash, new_id
from app.domain.enums import StageResourceRole
from app.domain.planning.guidance import changed_resource_guidance
from app.domain.planning.models import PlanDraft, PlanPublicationService
from app.domain.resources.curation import validate_section_selection
from app.infrastructure.db.learning_exposures import _json
from app.infrastructure.db.plan_repository import PgPlanRepository, to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from app.infrastructure.db.public_resource_catalog import _section_from, _source_from
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class ConnectionPublicCatalog:
    def __init__(self, conn):
        self.conn = conn

    def load_sources(self, *, source_ids):
        rows = self.conn.execute("SELECT * FROM public_resource_sources WHERE source_id=ANY(%s)", (list(source_ids),)).fetchall()
        return {row["source_id"]: _source_from(row) for row in rows}

    def load_sections(self, *, section_ids):
        rows = self.conn.execute("SELECT * FROM public_resource_sections WHERE section_id=ANY(%s)", (list(section_ids),)).fetchall()
        return {row["section_id"]: _section_from(row) for row in rows}

    def load_source_sections(self, *, source_ids):
        rows = self.conn.execute("SELECT * FROM public_resource_sections WHERE source_id=ANY(%s) ORDER BY source_id,order_index",
                                 (list(source_ids),)).fetchall()
        return {row["section_id"]: _section_from(row) for row in rows}


def capture_resource_snapshots(conn, assignments, stages):
    for source in sorted({a.source_ref for a in assignments if a.source_ref}):
        conn.execute("SELECT public.lock_reviewed_resource_index(%s)", (source,))
    catalog = ConnectionPublicCatalog(conn)
    sources = catalog.load_sources(source_ids=tuple(a.source_ref for a in assignments if a.source_ref))
    sections = catalog.load_source_sections(source_ids=tuple(sources))
    keys = {s.stage_id: s.stable_key for s in stages}
    views = resolve_stage_resources(assignments, catalog=catalog, stage_titles={s.stage_id: s.title for s in stages})
    return tuple(_json({"assignment_id": a.assignment_id, "stage_id": a.stage_id,
        "stage_key": keys[a.stage_id], "role": str(a.role), "order_index": a.order_index,
        "source_ref": a.source_ref, "source_version": a.source_version,
        "section_refs": list(a.section_refs),
        "snapshot_status": "frozen" if not view.warnings else "unresolved_reference",
        "snapshot_origin": "current_catalog_for_new_confirmation",
        "source": asdict(sources[a.source_ref]) if a.source_ref in sources else None,
        "sections": [asdict(sections[key]) for key in a.section_refs if key in sections], "view": asdict(view)})
        for a, view in zip(assignments, views, strict=True))


def require_snapshot_bindings(assignments, snapshots):
    frozen = {item["assignment_id"]: item for item in snapshots}
    if len(frozen) != len(assignments):
        raise ValidationAppError("资源快照未完整覆盖草案分配")
    for a in assignments:
        item = frozen.get(a.assignment_id)
        refs = item.get("section_refs", [s["section_id"] for s in item.get("sections", [])]) if item else []
        if not item or (item.get("stage_id"), item.get("role"), item.get("source_ref"),
            item.get("source_version"), tuple(refs), item.get("order_index"),
            tuple((item.get("view") or {}).get("node_ids", ()))) != (
                a.stage_id, str(a.role), a.source_ref, a.source_version, a.section_refs, a.order_index, a.node_ids):
            raise ValidationAppError("资源分配已变化，必须重新生成明确预览及其来源快照")


class PgResourceChanges:
    def __init__(self, dsn):
        self.dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _connection(self, scope, project_id, *, write=False):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                         (project_id, scope.actor_id))
            if write:
                lock_plan_version(conn, project_id, None)
            owner = conn.execute("SELECT project_id FROM learning_projects WHERE project_id=%s "
                "AND owner_actor_id=%s AND archived_at IS NULL" + (" FOR UPDATE" if write else ""),
                (project_id, scope.actor_id)).fetchone()
            if owner is None:
                raise ForbiddenError()
            yield conn

    @staticmethod
    def _receipt(conn, scope, project_id, key, action, fingerprint):
        row = conn.execute("SELECT * FROM resource_change_receipts WHERE project_id=%s AND actor_id=%s AND idempotency_key=%s",
                           (project_id, scope.actor_id, key)).fetchone()
        if row is None:
            return None
        if row["action"] != action or row["input_hash"] != fingerprint:
            raise IdempotencyConflictError()
        return row["response_snapshot"]

    @staticmethod
    def _save_receipt(conn, scope, project_id, key, action, fingerprint, response):
        conn.execute("""INSERT INTO resource_change_receipts(receipt_id,project_id,actor_id,idempotency_key,
            action,input_hash,response_snapshot) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
            (new_id("rcr"), project_id, scope.actor_id, key, action, fingerprint, Jsonb(response)))

    @staticmethod
    def _selected_catalog(conn, source_ref, source_version, section_refs):
        # App retains SELECT-only catalog access. The narrow owner function
        # locks this public reviewed source and its index without granting DML.
        conn.execute("SELECT public.lock_reviewed_resource_index(%s)", (source_ref,))
        source = conn.execute("SELECT * FROM public_resource_sources WHERE source_id=%s", (source_ref,)).fetchone()
        if source is None or source["verification_status"] != "reviewed" or source["checked_at"] is None:
            raise ValidationAppError("只能选择已审核的公共目录来源；私人链接不会升级为公共Seed")
        if source["source_version"] != source_version:
            raise VersionConflictError("资源目录版本已变化，请重新选择并预览")
        sections = conn.execute("SELECT * FROM public_resource_sections WHERE source_id=%s ORDER BY order_index",
                                (source_ref,)).fetchall()
        errors = validate_section_selection(source_ref=source_ref, section_refs=tuple(section_refs),
            role=StageResourceRole.PRIMARY, catalog_order={s["section_id"]: (s["source_id"], s["order_index"]) for s in sections})
        by_id = {s["section_id"]: s for s in sections}
        if errors or any(by_id[s]["verification_status"] != "reviewed" or by_id[s]["checked_at"] is None
                         for s in section_refs if s in by_id):
            raise ValidationAppError("；".join(errors) or "所选章节缺少审核记录")
        # Full author index changes also invalidate a retained preview.
        return content_hash(_json({"source": source, "sections": sections}))

    def catalog(self, scope, project_id):
        with self._connection(scope, project_id) as conn:
            sources = conn.execute("SELECT * FROM public_resource_sources WHERE verification_status='reviewed' "
                "AND checked_at IS NOT NULL ORDER BY source_id LIMIT 100").fetchall()
            result = []
            for source in sources:
                sections = conn.execute("SELECT * FROM public_resource_sections WHERE source_id=%s ORDER BY order_index LIMIT 301",
                                        (source["source_id"],)).fetchall()
                result.append(_json({"source": source, "sections": sections[:300], "index_truncated": len(sections) > 300}))
            return result

    @staticmethod
    def _private_bindings_digest(conn, project_id, plan_id):
        return private_bindings_digest(conn, project_id, plan_id)

    @staticmethod
    def _current(repo, command):
        current = repo.get_current(project_id=command.project_id)
        if current is None or current.plan_id != command.plan_id or current.version != command.expected_version:
            raise VersionConflictError("当前批准路线已变化，请重新预览")
        target = next((a for a in current.stage_resources if a.assignment_id == command.assignment_id
                       and a.stage_id == command.stage_id and a.role == StageResourceRole.PRIMARY), None)
        if target is None:
            raise NotFoundError("指定阶段主线分配不存在")
        return current, target

    @staticmethod
    def _impact(conn, current, target, command):
        units = conn.execute("SELECT unit_id FROM plan_unit_links WHERE project_id=%s AND plan_id=%s AND stage_id=%s ORDER BY order_index",
                             (command.project_id, current.plan_id, command.stage_id)).fetchall()
        ids = [row["unit_id"] for row in units]
        nodes = conn.execute("""SELECT DISTINCT n.node_id,n.stable_key,n.title,n.content_version FROM unit_node_links l
            JOIN knowledge_nodes n ON n.project_id=l.project_id AND n.node_id=l.node_id
            WHERE l.project_id=%s AND l.unit_id=ANY(%s) ORDER BY n.stable_key""", (command.project_id, ids)).fetchall()
        prerequisites = conn.execute("SELECT from_node_id,to_node_id,relation_type FROM knowledge_relations "
            "WHERE project_id=%s AND (from_node_id=ANY(%s) OR to_node_id=ANY(%s)) AND relation_type='prerequisite'",
            (command.project_id, [n["node_id"] for n in nodes], [n["node_id"] for n in nodes])).fetchall()
        progress = conn.execute("SELECT unit_id,status,version FROM learning_exposures WHERE project_id=%s AND plan_id=%s "
            "AND stage_id=%s ORDER BY unit_id", (command.project_id, current.plan_id, command.stage_id)).fetchall()
        selected = conn.execute("SELECT selection_id,stage_id,unit_id FROM learning_resource_selections "
            "WHERE project_id=%s AND plan_id=%s AND removed_at IS NULL ORDER BY selection_id",
            (command.project_id, current.plan_id)).fetchall()
        pack = conn.execute("SELECT published_payload FROM domain_packs WHERE pack_key=%s AND version=%s AND status='published'",
                            (current.source_pack_key, current.source_pack_version)).fetchone()
        payload = pack["published_payload"] if pack else None
        source = next((s for s in (payload or {}).get("resources", [])
                       if s["source_id"] == command.source_ref and s["source_version"] == command.source_version), None)
        mapped = set()
        complete_mapping = bool(source)
        if source:
            sections = {s["section_id"]: s for s in source["sections"]}
            for ref in command.section_refs:
                section = sections.get(ref)
                if not section or not section.get("applicable_node_keys"):
                    complete_mapping = False
                mapped.update(section.get("applicable_node_keys", []) if section else [])
        unmatched = [n["node_id"] for n in nodes if n["stable_key"] not in mapped]
        if unmatched:
            complete_mapping = False
        warnings = ["新路线的所有出现位置从未开始/version0起步；已有Exposure和成果历史保留在旧版本。",
                    "章节目录与知识映射仅为索引事实，不代表已经阅读、掌握或Verified。"]
        if not complete_mapping:
            warnings.append("缺少所选章节与本阶段知识的完整映射；不能证明覆盖，需明确确认。")
        warnings.append("资料未提供可核对的时长、环境与节奏约束；本预览不推断适配程度。")
        required = [e.topic for e in current.extensions if e.stage_id == command.stage_id and e.required]
        return _json({"unit_ids": ids, "nodes": nodes, "prerequisites": prerequisites,
            "prerequisite_status": "recorded_relations_only" if prerequisites else "unknown",
            "coverage": {"mapping_status": "available" if complete_mapping else "missing", "mapped_node_keys": sorted(mapped),
                         "unmatched_node_ids": unmatched, "required_extension_topics": required},
            "workload": {"before_section_count": len(target.section_refs), "after_section_count": len(command.section_refs),
                         "delta_sections": len(command.section_refs)-len(target.section_refs), "unit_count": len(ids),
                         "estimated_minutes": None},
            "progress": {"started_units": sum(p["status"] in {"in_progress", "completed"} for p in progress),
                         "completed_units": sum(p["status"] == "completed" for p in progress),
                         "skipped_units": sum(p["status"] == "skipped" for p in progress), "observations": progress},
            "environment": {"status": "unknown"}, "pace": {"status": "unknown"},
            "private_bindings": {"policy": command.copy_policy, "active_count": len(selected),
                                 "copy_count": len(selected) if command.copy_policy == "copy_active" else 0,
                                 "history_retained": True}, "warnings": warnings})

    def preview(self, scope, command):
        with self._connection(scope, command.project_id, write=True) as conn:
            previous = self._receipt(conn, scope, command.project_id, command.idempotency_key, "preview", command.input_hash())
            if previous is not None:
                return previous
            repo = PgPlanRepository(self.dsn, connection=conn)
            current, target = self._current(repo, command)
            for source in sorted({a.source_ref for a in current.stage_resources if a.source_ref} | {command.source_ref}):
                conn.execute("SELECT public.lock_reviewed_resource_index(%s)", (source,))
            digest = self._selected_catalog(conn, command.source_ref, command.source_version, command.section_refs)
            replacement = replace(target, source_ref=command.source_ref, source_version=command.source_version,
                                  section_refs=command.section_refs, fallback_search_terms=())
            assignments = tuple(replacement if a.assignment_id == target.assignment_id else a for a in current.stage_resources)
            snapshots = list(capture_resource_snapshots(conn, assignments, current.stages))
            old = {s["assignment_id"]: s for s in current.resource_snapshots}
            snapshots = tuple(old.get(a.assignment_id, s) if a.assignment_id != target.assignment_id else s
                              for a, s in zip(assignments, snapshots, strict=True))
            before = old.get(target.assignment_id) or {"assignment_id": target.assignment_id, "stage_id": target.stage_id,
                "stage_key": next(s.stable_key for s in current.stages if s.stage_id == target.stage_id),
                "role": str(target.role), "source_ref": target.source_ref, "source_version": target.source_version,
                "section_refs": list(target.section_refs), "snapshot_status": "legacy_unfrozen",
                "source": None, "sections": [], "view": None}
            after = next(s for s in snapshots if s["assignment_id"] == target.assignment_id)
            if (target.source_ref, target.source_version, target.section_refs) == (
                replacement.source_ref, replacement.source_version, replacement.section_refs) and before.get("source") == after.get("source"):
                raise ValidationAppError("请选择与当前主线不同的明确资源或章节")
            impact = self._impact(conn, current, target, command)
            draft = PlanDraft(new_id("drf"), command.project_id, "", current.goal_snapshot, current.revision+1,
                goal_spec=current.goal_spec,
                stages=tuple(replace(s, learning_guidance=changed_resource_guidance(s.learning_guidance))
                             if s.stage_id == target.stage_id else s for s in current.stages),
                unit_links=current.unit_links, task_links=current.task_links,
                task_knowledge_links=current.task_knowledge_links, stage_resources=assignments,
                extensions=current.extensions, resource_snapshots=snapshots, source_pack_key=current.source_pack_key,
                source_pack_version=current.source_pack_version, validation_warnings=tuple(impact["warnings"]))
            repo.save_draft(draft, expected_version=current.version)
            response = {"proposal_id": new_id("rcp"), "draft_id": draft.draft_id, "project_id": command.project_id,
                "actor_id": scope.actor_id, "base_plan_id": current.plan_id, "base_revision": current.revision,
                "status": "pending", "copy_policy": command.copy_policy, "before": before, "after": after,
                "impact": impact, "warnings": impact["warnings"], "created_at": draft.created_at.isoformat(),
                "draft_hash": draft.content_hash, "catalog_digest": digest,
                "private_binding_digest": self._private_bindings_digest(conn, command.project_id, current.plan_id)}
            response["preview_hash"] = content_hash({k: v for k, v in response.items() if k != "created_at"})
            conn.execute("""INSERT INTO resource_change_proposals(proposal_id,project_id,actor_id,draft_id,base_plan_id,
                base_revision,status,preview_hash,catalog_digest,payload) VALUES(%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s)""",
                (response["proposal_id"], command.project_id, scope.actor_id, draft.draft_id, current.plan_id,
                 current.revision, response["preview_hash"], digest, Jsonb(response)))
            conn.execute("UPDATE plan_drafts SET resource_change_proposal_id=%s WHERE project_id=%s AND draft_id=%s",
                         (response["proposal_id"], command.project_id, draft.draft_id))
            self._save_receipt(conn, scope, command.project_id, command.idempotency_key, "preview", command.input_hash(), response)
            return response

    def get(self, scope, project_id, proposal_id):
        with self._connection(scope, project_id) as conn:
            row = conn.execute("SELECT * FROM resource_change_proposals WHERE project_id=%s AND proposal_id=%s",
                               (project_id, proposal_id)).fetchone()
            if row is None:
                raise NotFoundError("资源变更预览不存在")
            return dict(row["payload"], status=row["status"])

    def decide(self, scope, project_id, proposal_id, action, expected_version, preview_hash, idempotency_key,
               acknowledge_warnings=False):
        fingerprint = content_hash({"proposal_id": proposal_id, "action": action, "expected_version": expected_version,
                                    "preview_hash": preview_hash, "acknowledge_warnings": acknowledge_warnings})
        with self._connection(scope, project_id, write=True) as conn:
            previous = self._receipt(conn, scope, project_id, idempotency_key, action, fingerprint)
            if previous is not None:
                return previous
            row = conn.execute("SELECT * FROM resource_change_proposals WHERE project_id=%s AND proposal_id=%s FOR UPDATE",
                               (project_id, proposal_id)).fetchone()
            if row is None:
                raise NotFoundError("资源变更预览不存在")
            if row["status"] != "pending":
                raise ConflictError("资源变更预览已处理")
            if row["preview_hash"] != preview_hash:
                raise ConflictError("预览已变化，请刷新后明确确认")
            payload = row["payload"]
            repo = PgPlanRepository(self.dsn, connection=conn, resource_proposal_id=proposal_id)
            current = repo.get_current(project_id=project_id)
            if current is None or current.plan_id != row["base_plan_id"] or current.version != expected_version or expected_version != row["base_revision"]:
                raise VersionConflictError("当前路线已变化，请重新预览")
            if action == "confirm" and payload["private_binding_digest"] != self._private_bindings_digest(conn, project_id, current.plan_id):
                raise VersionConflictError("私人资料选择已变化，请重新预览沿用策略和影响")
            draft = repo.get_draft(project_id=project_id, draft_id=row["draft_id"])
            if draft is None or draft.content_hash != payload["draft_hash"]:
                raise ConflictError("预览草案已变化，请重新预览")
            result = {"proposal_id": proposal_id, "action": action, "status": "cancelled",
                      "plan_id": None, "revision": None, "created": False, "copied_selections": 0}
            if action == "cancel":
                repo.cancel_draft(project_id=project_id, draft_id=draft.draft_id,
                                  expected_hash=draft.content_hash, expected_version=expected_version)
            else:
                if payload["warnings"] and not acknowledge_warnings:
                    raise ValidationAppError("请明确确认预览中缺少映射、环境或工作量信息的提示")
                after = payload["after"]
                for source in sorted({a.source_ref for a in draft.stage_resources if a.source_ref}):
                    conn.execute("SELECT public.lock_reviewed_resource_index(%s)", (source,))
                try:
                    digest = self._selected_catalog(conn, after["source_ref"], after["source_version"], after["section_refs"])
                except ValidationAppError as exc:
                    raise VersionConflictError("资源目录或章节索引已变化，请重新预览") from exc
                if digest != row["catalog_digest"]:
                    raise VersionConflictError("资源目录或章节索引已变化，请重新预览")
                published = PlanPublicationService(repo).publish(draft=draft, presented_hash=payload["draft_hash"],
                    expected_version=expected_version, idempotency_key="resource-change:" + proposal_id)
                copied = self._copy_selections(conn, current, published.plan_id, payload["copy_policy"])
                result.update(status="confirmed", plan_id=published.plan_id, revision=published.revision,
                              created=published.created, copied_selections=copied)
            conn.execute("UPDATE resource_change_proposals SET status=%s,updated_at=clock_timestamp() WHERE proposal_id=%s",
                         (result["status"], proposal_id))
            self._save_receipt(conn, scope, project_id, idempotency_key, action, fingerprint, result)
            return result

    @staticmethod
    def _copy_selections(conn, current, plan_id, policy):
        return copy_private_selections(conn, current, plan_id, policy)


def private_bindings_digest(conn, project_id, plan_id):
    rows = conn.execute("""SELECT selection_id,stage_id,unit_id,resource_id,resource_snapshot
        FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s AND removed_at IS NULL
        ORDER BY selection_id""", (project_id, plan_id)).fetchall()
    return content_hash(_json(rows))


def copy_private_selections(conn, current, plan_id, policy):
    if policy != "copy_active":
        return 0
    copied = 0
    rows = conn.execute("""SELECT old.*,n.stage_id AS new_stage_id FROM learning_resource_selections old
        JOIN plan_stages s ON s.project_id=old.project_id AND s.plan_id=old.plan_id AND s.stage_id=old.stage_id
        JOIN plan_stages n ON n.project_id=s.project_id AND n.plan_id=%s AND n.stable_key=s.stable_key
        JOIN plan_unit_links l ON l.project_id=n.project_id AND l.plan_id=n.plan_id AND l.stage_id=n.stage_id AND l.unit_id=old.unit_id
        WHERE old.project_id=%s AND old.plan_id=%s AND old.removed_at IS NULL ORDER BY old.selection_id""",
        (plan_id, current.project_id, current.plan_id)).fetchall()
    for old in rows:
        lineage = {"original_selection_id": old["selection_id"], "original_plan_id": current.plan_id,
                   "original_stage_id": old["stage_id"], "original_source_version": old["resource_snapshot"].get("source_version")}
        snapshot = dict(old["resource_snapshot"], selection_copy_lineage=lineage)
        snapshot["source_note"] = (snapshot.get("source_note", "") + "\n按用户明确策略沿用旧路线私人资料；原选择记录 " + old["selection_id"]).strip()
        conn.execute("""INSERT INTO learning_resource_selections(selection_id,project_id,plan_id,stage_id,unit_id,
            resource_id,resource_snapshot) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
            (new_id("selection"), current.project_id, plan_id, old["new_stage_id"], old["unit_id"],
             old["resource_id"], Jsonb(snapshot)))
        copied += 1
    return copied
