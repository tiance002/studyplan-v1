"""Read catalog entities via published IDs; no title matching or dependency inference."""

import psycopg
from app.core.errors import ForbiddenError
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from psycopg.rows import dict_row


class PgWorkspaceReader:
    def __init__(self, dsn):
        self.dsn = to_psycopg_dsn(dsn)

    def read(self, scope, project_id, unit_ids, task_ids, *, plan_id=None):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            conn.execute("SELECT set_config('app.project_id',%s,true)", (project_id,))
            conn.execute("SELECT set_config('app.actor_id',%s,true)", (scope.actor_id,))
            if conn.execute("SELECT 1 FROM learning_projects WHERE project_id=%s AND owner_actor_id=%s "
                            "AND archived_at IS NULL", (project_id, scope.actor_id)).fetchone() is None:
                raise ForbiddenError()
            historical_learning_by_stage = {}
            if plan_id is not None:
                from app.infrastructure.db.plan_repository import PgPlanRepository
                from app.infrastructure.db.v2_revisions import capture_progress_basis
                row = conn.execute("SELECT * FROM plan_revisions WHERE project_id=%s AND plan_id=%s", (project_id, plan_id)).fetchone()
                if row is not None:
                    plan = PgPlanRepository(self.dsn, connection=conn)._load_revision(conn, row)
                    if plan.v2_revision is not None:
                        basis = capture_progress_basis(conn, plan)
                        for stage in basis["stages"]:
                            if stage["historical_learning_status"] in {"started", "completed"}:
                                historical_learning_by_stage[stage["stage_id"]] = {
                                    key: value for key, value in stage["history_source"].items() if key != "source_stage_hash"}
                                historical_learning_by_stage[stage["stage_id"]]["learning_status"] = stage["historical_learning_status"]
            summary_stage_ids, accepted_task_positions = set(), set()
            if plan_id is not None:
                # Both facts share one statement snapshot and the current owner RLS scope.
                completion_facts = conn.execute("""SELECT 'summary' AS kind,h.stage_id,NULL::text AS task_id,s.content
                    FROM summary_stage_heads h JOIN summary_attempts s ON s.project_id=h.project_id
                        AND s.plan_id=h.plan_id AND s.stage_id=h.stage_id AND s.version=h.version AND s.unit_id IS NULL
                    WHERE h.project_id=%s AND h.plan_id=%s
                    UNION ALL
                    SELECT DISTINCT 'practice' AS kind,s.stage_id,s.task_id,NULL::text AS content FROM practice_submissions s
                    JOIN acceptance_reviews a ON a.project_id=s.project_id AND a.submission_id=s.submission_id
                    WHERE s.project_id=%s AND s.plan_id=%s AND a.conclusion='accepted' AND a.reviewer_kind='user'""",
                    (project_id, plan_id, project_id, plan_id)).fetchall()
                summary_stage_ids = {row["stage_id"] for row in completion_facts
                                     if row["kind"] == "summary" and row["content"].strip()}
                accepted_task_positions = {(row["stage_id"], row["task_id"]) for row in completion_facts if row["kind"] == "practice"}
            units = conn.execute(
                """SELECT u.unit_id,u.stable_key,u.title,u.objectives,u.rubric_version,
                coalesce(p.status,'not_started') AS progress, p.unit_id IS NOT NULL AS progress_recorded FROM learning_units u LEFT JOIN unit_progress p
                ON p.unit_id=u.unit_id AND p.project_id=u.project_id WHERE u.unit_id=ANY(%s)""",
                (unit_ids,),
            ).fetchall()
            links = conn.execute(
                "SELECT unit_id,node_id,order_index FROM unit_node_links WHERE unit_id=ANY(%s) ORDER BY order_index",
                (unit_ids,),
            ).fetchall()
            order = {unit_id: i for i, unit_id in enumerate(unit_ids)}
            units.sort(key=lambda u: order[u["unit_id"]])
            links.sort(key=lambda link: (order[link["unit_id"]], link["order_index"]))
            node_ids = list(dict.fromkeys(link["node_id"] for link in links))
            nodes = conn.execute(
                "SELECT node_id,stable_key,title,node_type,objectives,source_status FROM knowledge_nodes WHERE node_id=ANY(%s)",
                (node_ids,),
            ).fetchall()
            relations = conn.execute(
                "SELECT from_node_id,to_node_id,relation_type FROM knowledge_relations WHERE (to_node_id=ANY(%s) OR from_node_id=ANY(%s)) AND relation_type IN ('prerequisite','contains')",
                (node_ids, node_ids),
            ).fetchall()
            tasks = conn.execute(
                "SELECT task_id,practice_project_id,stable_key,title,goal,in_scope,out_scope,acceptance,status FROM practice_tasks WHERE task_id=ANY(%s)",
                (task_ids,),
            ).fetchall()
        node_order = {node_id: i for i, node_id in enumerate(node_ids)}
        nodes.sort(key=lambda n: node_order[n["node_id"]])
        for unit in units:
            unit["node_ids"] = [link["node_id"] for link in links if link["unit_id"] == unit["unit_id"]]
        for node in nodes:
            node["prerequisite_ids"] = [
                r["from_node_id"] for r in relations if r["to_node_id"] == node["node_id"] and r["relation_type"] == "prerequisite"
            ]
            node["child_ids"] = [r["to_node_id"] for r in relations if r["from_node_id"] == node["node_id"] and r["relation_type"] == "contains"]
            node["progress"] = None
        return {"units": units, "nodes": nodes, "tasks": tasks,
                "summary_stage_ids": summary_stage_ids, "accepted_task_positions": accepted_task_positions,
                "historical_learning_by_stage": historical_learning_by_stage}
