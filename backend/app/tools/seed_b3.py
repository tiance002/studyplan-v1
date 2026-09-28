"""Seed the reviewed B3 pack/resources with the migration role, never at request time."""
import os

import psycopg
from app.agent_workflows.runtime import PostgresSaver
from app.core.config import get_settings
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.domain_pack import load_python_pack
from psycopg.types.json import Jsonb


def main():
    settings = get_settings()
    data = load_python_pack()
    migration = to_psycopg_dsn(os.environ["STUDYPLAN_MIGRATION_DSN"])
    with psycopg.connect(migration) as conn:
        conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(project_id) DO NOTHING",
                     (settings.local_project_id,settings.local_actor_id,"我的学习空间","Python 工程入门","local.learning"))
        conn.execute("""INSERT INTO domain_packs(pack_key,version,status,supported_scope,title,stage_blueprints,resource_refs,practice_blueprints,provenance)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(pack_key,version) DO NOTHING""",
                     (data["pack_key"],data["version"],data["status"],data["supported_scope"],data["title"],
                      Jsonb(data["stage_blueprints"]),Jsonb(data["resource_refs"]),Jsonb(data["practice_blueprints"]),data["provenance"]))
        for source in data["resources"]:
            conn.execute("""INSERT INTO public_resource_sources(source_id,canonical_url,title,creator,media_type,language,source_version,provenance,checked_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now()) ON CONFLICT(source_id) DO NOTHING""",
                         (source["source_id"],source["canonical_url"],source["title"],source["creator"],source["media_type"],source["language"],source["source_version"],data["provenance"]))
            for section in source["sections"]:
                conn.execute("INSERT INTO public_resource_sections(section_id,source_id,order_index,title,url,checked_at) VALUES (%s,%s,%s,%s,%s,now()) ON CONFLICT(section_id) DO NOTHING",
                             (section["section_id"],source["source_id"],section["order_index"],section["title"],section["url"]))
    with PostgresSaver.from_conn_string(to_psycopg_dsn(os.environ["CHECKPOINT_SETUP_DSN"])) as saver:
        saver.setup()
    print("[B3] Reviewed pack/resources and independent checkpoint schema ready")


if __name__ == "__main__":
    main()
