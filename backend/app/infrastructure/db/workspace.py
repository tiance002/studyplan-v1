"""Read catalog entities via published IDs; no title matching or dependency inference."""

import psycopg
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from psycopg.rows import dict_row


class PgWorkspaceReader:
    def __init__(self, dsn):
        self.dsn = to_psycopg_dsn(dsn)

    def read(self, scope, project_id, unit_ids, task_ids):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.project_id',%s,true)", (project_id,))
            conn.execute("SELECT set_config('app.actor_id',%s,true)", (scope.actor_id,))
            units = conn.execute(
                """SELECT u.unit_id,u.stable_key,u.title,u.objectives,u.rubric_version,
                coalesce(p.status,'not_started') AS progress FROM learning_units u LEFT JOIN unit_progress p
                ON p.unit_id=u.unit_id AND p.project_id=u.project_id WHERE u.unit_id=ANY(%s)""",
                (unit_ids,),
            ).fetchall()
            links = conn.execute(
                "SELECT unit_id,node_id FROM unit_node_links WHERE unit_id=ANY(%s) ORDER BY order_index",
                (unit_ids,),
            ).fetchall()
            node_ids = list({link["node_id"] for link in links})
            nodes = conn.execute(
                "SELECT node_id,stable_key,title,node_type,objectives,source_status FROM knowledge_nodes WHERE node_id=ANY(%s)",
                (node_ids,),
            ).fetchall()
            relations = conn.execute(
                "SELECT from_node_id,to_node_id FROM knowledge_relations WHERE to_node_id=ANY(%s) AND relation_type='prerequisite'",
                (node_ids,),
            ).fetchall()
            tasks = conn.execute(
                "SELECT task_id,practice_project_id,stable_key,title,goal,in_scope,out_scope,acceptance,status FROM practice_tasks WHERE task_id=ANY(%s)",
                (task_ids,),
            ).fetchall()
        for unit in units:
            unit["node_ids"] = [link["node_id"] for link in links if link["unit_id"] == unit["unit_id"]]
        for node in nodes:
            node["prerequisite_ids"] = [
                r["from_node_id"] for r in relations if r["to_node_id"] == node["node_id"]
            ]
        return {"units": units, "nodes": nodes, "tasks": tasks}
