"""Manual candidates and existing publication, all decisions in one owner transaction."""

from dataclasses import replace

from app.core.errors import (
    ConflictError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
    VersionConflictError,
)
from app.core.ids import content_hash, new_id
from app.domain.enums import TaskKnowledgeRole
from app.domain.planning.guidance import changed_practice_guidance
from app.domain.planning.models import PlanDraft, PlanPublicationService, PlanTaskKnowledgeLink, PlanTaskLink
from app.infrastructure.db.learning_exposures import _json
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.resource_changes import (
    PgResourceChanges,
    capture_resource_snapshots,
    copy_private_selections,
    private_bindings_digest,
)
from psycopg.types.json import Jsonb


class PgPracticeChanges(PgResourceChanges):
    # Reuse the exact advisory->active owner transaction; no second publisher.
    @staticmethod
    def _receipt(conn, scope, project_id, key, action, fingerprint):
        row = conn.execute(
            "SELECT * FROM practice_change_receipts WHERE project_id=%s AND actor_id=%s AND idempotency_key=%s",
            (project_id, scope.actor_id, key),
        ).fetchone()
        if row:
            if row["action"] != action or row["input_hash"] != fingerprint:
                raise IdempotencyConflictError()
            return row["response_snapshot"]
        return None

    @staticmethod
    def _save_receipt(conn, scope, project_id, key, action, fingerprint, response):
        conn.execute(
            "INSERT INTO practice_change_receipts(receipt_id,project_id,actor_id,idempotency_key,action,input_hash,response_snapshot) VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (new_id("pcr"), project_id, scope.actor_id, key, action, fingerprint, Jsonb(_json(response))),
        )

    @staticmethod
    def _context_for_plan(conn, current, *, lock=False):
        project, plan = current.project_id, current.plan_id
        tasks = conn.execute(
            """SELECT t.task_id,t.practice_project_id,t.stable_key,t.title,t.goal,t.in_scope,t.out_scope,t.acceptance,t.status,t.version,
            l.stage_id,s.stable_key AS stage_key,l.order_index FROM plan_task_links l JOIN practice_tasks t
            ON t.project_id=l.project_id AND t.task_id=l.task_id JOIN plan_stages s ON s.project_id=l.project_id AND s.plan_id=l.plan_id AND s.stage_id=l.stage_id
            WHERE l.project_id=%s AND l.plan_id=%s ORDER BY s.order_index,l.order_index,l.task_id"""
            + (" FOR SHARE OF t,l,s" if lock else ""),
            (project, plan),
        ).fetchall()
        links = conn.execute(
            """SELECT l.task_id,n.node_id,n.stable_key,n.title,n.content_version,l.role FROM plan_task_knowledge_links l
            JOIN knowledge_nodes n ON n.project_id=l.project_id AND n.node_id=l.node_id WHERE l.project_id=%s AND l.plan_id=%s ORDER BY l.order_index,l.link_id""",
            (project, plan),
        ).fetchall()
        for t in tasks:
            t["knowledge_links"] = [
                {k: v for k, v in link.items() if k != "task_id"}
                for link in links
                if link["task_id"] == t["task_id"]
            ]
        projects = conn.execute(
            "SELECT practice_project_id,title,idea,repo_url,status,version FROM practice_projects WHERE project_id=%s AND practice_project_id=ANY(%s) ORDER BY practice_project_id"
            + (" FOR SHARE" if lock else ""),
            (project, list({t["practice_project_id"] for t in tasks})),
        ).fetchall()
        nodes = conn.execute(
            """SELECT DISTINCT n.node_id,n.stable_key,n.title,n.content_version FROM knowledge_nodes n WHERE n.project_id=%s AND (
            EXISTS(SELECT 1 FROM plan_unit_links p JOIN unit_node_links u ON u.project_id=p.project_id AND u.unit_id=p.unit_id
                WHERE p.project_id=n.project_id AND p.plan_id=%s AND u.node_id=n.node_id)
            OR EXISTS(SELECT 1 FROM plan_task_knowledge_links l WHERE l.project_id=n.project_id AND l.plan_id=%s AND l.node_id=n.node_id)) ORDER BY n.stable_key,n.node_id""",
            (project, plan, plan),
        ).fetchall()
        return _json(
            dict(
                project_id=project,
                plan_id=plan,
                revision=current.revision,
                version=current.version,
                practice_projects=projects,
                stages=[
                    dict(
                        stage_id=s.stage_id, stable_key=s.stable_key, title=s.title, order_index=s.order_index
                    )
                    for s in current.stages
                ],
                tasks=tasks,
                knowledge_options=nodes,
            )
        )

    def context(self, scope, project_id):
        with self._connection(scope, project_id) as conn:
            current = PgPlanRepository(self.dsn, connection=conn).get_current(project_id=project_id)
            if current is None:
                raise NotFoundError("尚无批准路线")
            return self._context_for_plan(conn, current)

    @staticmethod
    def _observations(conn, current, target_ids):
        args = (current.project_id, current.plan_id)
        return dict(
            prompt_revision_count=conn.execute(
                "SELECT count(*) AS n FROM prompt_revisions WHERE project_id=%s AND task_id=ANY(%s)",
                (current.project_id, target_ids),
            ).fetchone()["n"],
            summary_count=conn.execute(
                "SELECT count(*) AS n FROM summary_attempts WHERE project_id=%s AND plan_id=%s", args
            ).fetchone()["n"],
            exposure_count=conn.execute(
                "SELECT count(*) AS n FROM learning_exposures WHERE project_id=%s AND plan_id=%s", args
            ).fetchone()["n"],
            exposure_observations=_json(
                conn.execute(
                    "SELECT exposure_id,status,version FROM learning_exposures WHERE project_id=%s AND plan_id=%s ORDER BY exposure_id",
                    args,
                ).fetchall()
            ),
            private_binding_count=conn.execute(
                "SELECT count(*) AS n FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s AND removed_at IS NULL",
                args,
            ).fetchone()["n"],
        )

    @staticmethod
    def _node_rows(conn, project, ids):
        return _json(
            conn.execute(
                "SELECT * FROM knowledge_nodes WHERE project_id=%s AND node_id=ANY(%s) ORDER BY node_id FOR SHARE",
                (project, ids),
            ).fetchall()
        )

    def _basis_digest(self, conn, current, context, target_ids):
        return content_hash(
            dict(
                context=context,
                structure=current.structure_fingerprint(),
                observations=self._observations(conn, current, target_ids),
                nodes=self._node_rows(
                    conn, current.project_id, [n["node_id"] for n in context["knowledge_options"]]
                ),
            )
        )

    @staticmethod
    def _source_digest(conn, source_ids):
        for source in sorted(source_ids):
            conn.execute("SELECT public.lock_reviewed_resource_index(%s)", (source,))
        sources = conn.execute(
            "SELECT * FROM public_resource_sources WHERE source_id=ANY(%s) ORDER BY source_id", (source_ids,)
        ).fetchall()
        sections = conn.execute(
            "SELECT * FROM public_resource_sections WHERE source_id=ANY(%s) ORDER BY source_id,order_index,section_id",
            (source_ids,),
        ).fetchall()
        return content_hash(_json(dict(sources=sources, sections=sections)))

    def _candidate_digest(self, conn, project, project_id, task_ids, node_ids):
        main = conn.execute(
            "SELECT * FROM practice_projects WHERE project_id=%s AND practice_project_id=%s FOR SHARE",
            (project, project_id),
        ).fetchone()
        tasks = conn.execute(
            "SELECT * FROM practice_tasks WHERE project_id=%s AND task_id=ANY(%s) ORDER BY task_id FOR SHARE",
            (project, task_ids),
        ).fetchall()
        return content_hash(
            _json(dict(main=main, tasks=tasks, nodes=self._node_rows(conn, project, node_ids)))
        )

    @staticmethod
    def _changed(before, edit):
        return any(
            before[k] != list(getattr(edit, k))
            if k in {"in_scope", "out_scope", "acceptance"}
            else before[k] != getattr(edit, k)
            for k in ("title", "goal", "in_scope", "out_scope", "acceptance")
        ) or [(link["node_id"], link["role"]) for link in before["knowledge_links"]] != [
            (link.node_id, link.role) for link in edit.knowledge_links
        ]

    def preview(self, scope, command):
        with self._connection(scope, command.project_id, write=True) as conn:
            old = self._receipt(
                conn, scope, command.project_id, command.idempotency_key, "preview", command.input_hash()
            )
            if old is not None:
                return old
            repo = PgPlanRepository(self.dsn, connection=conn)
            current = repo.get_current(project_id=command.project_id)
            if current is None or (current.plan_id, current.version) != (
                command.plan_id,
                command.expected_version,
            ):
                raise VersionConflictError("当前批准路线已变化，请重新预览")
            context = self._context_for_plan(conn, current, lock=True)
            before = next(
                (
                    p
                    for p in context["practice_projects"]
                    if p["practice_project_id"] == command.practice_project_id
                ),
                None,
            )
            if before is None:
                raise NotFoundError("主项目未被当前路线使用")
            targets = [t for t in context["tasks"] if t["practice_project_id"] == command.practice_project_id]
            by_id = {t["task_id"]: t for t in targets}
            nodes = {n["node_id"]: n for n in context["knowledge_options"]}
            stage_ids = {s.stage_id for s in current.stages}
            edits = {}
            additions = []
            for edit in command.task_changes:
                if edit.stage_id not in stage_ids:
                    raise NotFoundError("指定阶段不属于当前路线")
                if any(link.node_id not in nodes for link in edit.knowledge_links):
                    raise ValidationAppError("知识必须来自此批准路线的单元或任务关联")
                if edit.operation == "update":
                    task = by_id.get(edit.task_id)
                    if task is None or task["stage_id"] != edit.stage_id:
                        raise NotFoundError("任务不属于指定主项目和阶段")
                    if self._changed(task, edit):
                        edits[edit.task_id] = edit
                else:
                    additions.append(edit)
            project_changed = (before["title"], before["idea"], before["repo_url"]) != (
                command.title,
                command.idea,
                command.repo_url,
            )
            if not project_changed and not edits and not additions:
                raise ValidationAppError("本次设计没有变化")
            # Validate cloned legacy requirements too, before writing candidates.
            for task in targets:
                links = (
                    edits[task["task_id"]].knowledge_links
                    if task["task_id"] in edits
                    else task["knowledge_links"]
                )
                if (project_changed or task["task_id"] in edits) and not any(
                    (link.role if hasattr(link, "role") else link["role"]) == "core" for link in links
                ):
                    raise ValidationAppError("新任务必须有明确的核心知识关联")
            basis = self._basis_digest(conn, current, context, list(by_id))
            missing = [
                a
                for a in current.stage_resources
                if a.assignment_id not in {s["assignment_id"] for s in current.resource_snapshots}
            ]
            source_ids = sorted({a.source_ref for a in missing if a.source_ref})
            source_digest = self._source_digest(conn, source_ids)
            snapshots = tuple(current.resource_snapshots) + capture_resource_snapshots(
                conn, missing, current.stages
            )
            after = dict(before)
            if project_changed:
                after.update(
                    practice_project_id=new_id("ppj"),
                    title=command.title,
                    idea=command.idea,
                    repo_url=command.repo_url,
                    status="idea",
                    version=1,
                )
                conn.execute(
                    "INSERT INTO practice_projects(practice_project_id,project_id,title,idea,repo_url,status,version) VALUES(%s,%s,%s,%s,%s,'idea',1)",
                    (
                        after["practice_project_id"],
                        command.project_id,
                        command.title,
                        command.idea,
                        command.repo_url,
                    ),
                )
            deltas = []
            replacements = {}
            new_links = []
            new_knowledge = []

            def insert_task(old, edit, operation, order_index):
                data = (
                    dict(old)
                    if old
                    else dict(
                        stage_id=edit.stage_id,
                        stage_key=next(s.stable_key for s in current.stages if s.stage_id == edit.stage_id),
                        order_index=order_index,
                    )
                )
                if edit:
                    data.update(
                        {
                            k: list(getattr(edit, k))
                            if k in {"in_scope", "out_scope", "acceptance"}
                            else getattr(edit, k)
                            for k in ("title", "goal", "in_scope", "out_scope", "acceptance")
                        }
                    )
                    data["knowledge_links"] = [
                        dict(nodes[link.node_id], role=link.role) for link in edit.knowledge_links
                    ]
                data.update(
                    task_id=new_id("tsk"),
                    practice_project_id=after["practice_project_id"],
                    status="pending",
                    version=1,
                    stable_key=old["stable_key"]
                    if old and project_changed
                    else "task.change." + new_id("key"),
                )
                conn.execute(
                    """INSERT INTO practice_tasks(task_id,project_id,practice_project_id,stable_key,title,goal,in_scope,out_scope,acceptance,status,version,stage_index)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',1,%s)""",
                    (
                        data["task_id"],
                        command.project_id,
                        data["practice_project_id"],
                        data["stable_key"],
                        data["title"],
                        data["goal"],
                        Jsonb(data["in_scope"]),
                        Jsonb(data["out_scope"]),
                        Jsonb(data["acceptance"]),
                        next(s.order_index for s in current.stages if s.stage_id == data["stage_id"]),
                    ),
                )
                deltas.append(dict(operation=operation, before=old, after=data))
                new_links.append(PlanTaskLink(data["stage_id"], data["task_id"], data["order_index"]))
                new_knowledge.extend(
                    PlanTaskKnowledgeLink(data["task_id"], link["node_id"], TaskKnowledgeRole(link["role"]))
                    for link in data["knowledge_links"]
                )
                if old:
                    replacements[old["task_id"]] = data["task_id"]

            for task in targets:
                if project_changed or task["task_id"] in edits:
                    insert_task(
                        task,
                        edits.get(task["task_id"]),
                        "update" if task["task_id"] in edits else "rebind",
                        task["order_index"],
                    )
            order = {
                s: max((t["order_index"] for t in context["tasks"] if t["stage_id"] == s), default=-1) + 1
                for s in stage_ids
            }
            for edit in additions:
                insert_task(None, edit, "add", order[edit.stage_id])
                order[edit.stage_id] += 1
            obs = self._observations(conn, current, list(by_id))
            impact = dict(
                changed_task_ids=list(replacements),
                added_task_ids=[d["after"]["task_id"] for d in deltas if d["before"] is None],
                cloned_task_count=len(replacements),
                started_task_count=sum(t["status"] not in {"pending", "skipped"} for t in targets),
                **{k: v for k, v in obs.items() if k != "exposure_observations"},
                new_exposures_reset=True,
                preserve_history=True,
            )
            warnings = [
                "这是手动设计变更，不代表实现、功能验收或知识Verified。",
                "新路线所有Exposure位置从未开始/version0起步；旧进度和总结保留。",
                "变更任务使用新身份并从pending起步；旧Prompt原文、反馈、导出和成果历史不会迁移为新任务证据。",
                "私人资料仅按所选策略沿用来源绑定，不能代表已阅读或掌握。",
            ]
            if impact["started_task_count"]:
                warnings.append("已开始或已验收的任务存在；新任务不会继承这些状态。")
            if missing:
                warnings.append(
                    "旧路线部分资源缺少当时快照；本次仅冻结新版本预览时观察，不声称补全旧版本历史。"
                )
            changed_stage_ids = {d["after"]["stage_id"] for d in deltas}
            future_tasks = [t for t in context["tasks"] if t["task_id"] not in replacements] + [d["after"] for d in deltas]
            stages = tuple(replace(s, learning_guidance=changed_practice_guidance(
                s.learning_guidance, [t for t in future_tasks if t["stage_id"] == s.stage_id]))
                if s.stage_id in changed_stage_ids else s for s in current.stages)
            draft = PlanDraft(
                new_id("drf"),
                command.project_id,
                "",
                current.goal_snapshot,
                current.revision + 1,
                stages=stages,
                unit_links=current.unit_links,
                task_links=tuple(t for t in current.task_links if t.task_id not in replacements)
                + tuple(new_links),
                task_knowledge_links=tuple(
                    link for link in current.task_knowledge_links if link.task_id not in replacements
                )
                + tuple(new_knowledge),
                stage_resources=current.stage_resources,
                resource_snapshots=snapshots,
                extensions=current.extensions,
                source_pack_key=current.source_pack_key,
                source_pack_version=current.source_pack_version,
                practice_project_idea=after["idea"],
                validation_warnings=tuple(warnings),
            )
            repo.save_draft(draft, expected_version=current.version)
            task_ids = [d["after"]["task_id"] for d in deltas]
            node_ids = sorted({link["node_id"] for d in deltas for link in d["after"]["knowledge_links"]})
            candidate = self._candidate_digest(
                conn, command.project_id, after["practice_project_id"], task_ids, node_ids
            )
            private = private_bindings_digest(conn, command.project_id, current.plan_id)
            view = _json(
                dict(
                    proposal_id=new_id("pcp"),
                    draft_id=draft.draft_id,
                    project_id=command.project_id,
                    base_plan_id=current.plan_id,
                    base_revision=current.revision,
                    base_version=current.version,
                    status="pending",
                    draft_hash=draft.content_hash,
                    copy_policy=command.copy_policy,
                    before=before,
                    after=after,
                    task_changes=deltas,
                    impact=impact,
                    warnings=warnings,
                    created_at=draft.created_at,
                )
            )
            view["preview_hash"] = content_hash(
                dict(
                    view={k: v for k, v in view.items() if k != "created_at"},
                    basis=basis,
                    candidate=candidate,
                    private=private,
                    source=source_digest,
                )
            )
            payload = dict(
                view=view,
                basis_digest=basis,
                candidate_digest=candidate,
                private_digest=private,
                source_digest=source_digest,
                source_ids=source_ids,
                target_task_ids=list(by_id),
                candidate_task_ids=task_ids,
                candidate_node_ids=node_ids,
            )
            conn.execute(
                "INSERT INTO practice_change_proposals(proposal_id,project_id,actor_id,draft_id,base_plan_id,base_revision,base_version,status,preview_hash,payload) VALUES(%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s)",
                (
                    view["proposal_id"],
                    command.project_id,
                    scope.actor_id,
                    draft.draft_id,
                    current.plan_id,
                    current.revision,
                    current.version,
                    view["preview_hash"],
                    Jsonb(payload),
                ),
            )
            conn.execute(
                "UPDATE plan_drafts SET practice_change_proposal_id=%s WHERE project_id=%s AND draft_id=%s",
                (view["proposal_id"], command.project_id, draft.draft_id),
            )
            self._save_receipt(
                conn,
                scope,
                command.project_id,
                command.idempotency_key,
                "preview",
                command.input_hash(),
                view,
            )
            return view

    def get(self, scope, project_id, proposal_id):
        with self._connection(scope, project_id) as conn:
            row = conn.execute(
                "SELECT status,payload FROM practice_change_proposals WHERE project_id=%s AND proposal_id=%s",
                (project_id, proposal_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("实践变更预览不存在")
            return dict(row["payload"]["view"], status=row["status"])

    def decide(
        self,
        scope,
        project_id,
        proposal_id,
        action,
        expected_version,
        preview_hash,
        idempotency_key,
        acknowledge_warnings=False,
    ):
        fingerprint = content_hash(
            dict(
                proposal_id=proposal_id,
                action=action,
                expected_version=expected_version,
                preview_hash=preview_hash,
                acknowledge_warnings=acknowledge_warnings,
            )
        )
        with self._connection(scope, project_id, write=True) as conn:
            prior = self._receipt(conn, scope, project_id, idempotency_key, action, fingerprint)
            if prior is not None:
                return prior
            row = conn.execute(
                "SELECT * FROM practice_change_proposals WHERE project_id=%s AND proposal_id=%s AND actor_id=%s FOR UPDATE",
                (project_id, proposal_id, scope.actor_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("实践变更预览不存在")
            if row["status"] != "pending":
                raise ConflictError("实践变更预览已处理")
            if (row["preview_hash"], row["base_version"]) != (preview_hash, expected_version):
                raise VersionConflictError("必须确认此预览的原版本和hash")
            payload = row["payload"]
            view = payload["view"]
            repo = PgPlanRepository(self.dsn, connection=conn, practice_proposal_id=proposal_id)
            draft = repo.get_draft(project_id=project_id, draft_id=row["draft_id"])
            if draft is None or draft.content_hash != view["draft_hash"]:
                raise ConflictError("预览草案已变化，请重新预览")
            result = dict(
                proposal_id=proposal_id,
                action=action,
                status="cancelled",
                plan_id=None,
                revision=None,
                created=False,
                copied_selections=0,
            )
            if action == "cancel":
                repo.cancel_draft(
                    project_id=project_id, draft_id=draft.draft_id, expected_hash=view["draft_hash"]
                )
            elif action == "confirm":
                if view["warnings"] and acknowledge_warnings is not True:
                    raise ValidationAppError("请明确确认实践设计与历史保留提示")
                current = repo.get_current(project_id=project_id)
                if current is None or (current.plan_id, current.version, current.revision) != (
                    row["base_plan_id"],
                    row["base_version"],
                    row["base_revision"],
                ):
                    raise VersionConflictError("批准路线已变化，请重新预览")
                context = self._context_for_plan(conn, current, lock=True)
                if (
                    self._basis_digest(conn, current, context, payload["target_task_ids"])
                    != payload["basis_digest"]
                ):
                    raise VersionConflictError("任务、知识或学习记录依据已变化，请重新预览")
                if private_bindings_digest(conn, project_id, current.plan_id) != payload["private_digest"]:
                    raise VersionConflictError("私人资料选择已变化，请重新预览")
                if (
                    self._candidate_digest(
                        conn,
                        project_id,
                        view["after"]["practice_project_id"],
                        payload["candidate_task_ids"],
                        payload["candidate_node_ids"],
                    )
                    != payload["candidate_digest"]
                ):
                    raise VersionConflictError("候选任务或主项目已变化，请重新预览")
                if self._source_digest(conn, payload["source_ids"]) != payload["source_digest"]:
                    raise VersionConflictError("本次新观察的来源目录已变化，请重新预览")
                published = PlanPublicationService(repo).publish(
                    draft=draft,
                    presented_hash=view["draft_hash"],
                    expected_version=expected_version,
                    idempotency_key="practice-change:" + proposal_id,
                )
                copied = copy_private_selections(conn, current, published.plan_id, view["copy_policy"])
                result.update(
                    status="confirmed",
                    plan_id=published.plan_id,
                    revision=published.revision,
                    created=published.created,
                    copied_selections=copied,
                )
            else:
                raise ValidationAppError("必须明确确认或取消")
            conn.execute(
                "UPDATE practice_change_proposals SET status=%s,updated_at=clock_timestamp() WHERE proposal_id=%s",
                (result["status"], proposal_id),
            )
            self._save_receipt(conn, scope, project_id, idempotency_key, action, fingerprint, result)
            return result
