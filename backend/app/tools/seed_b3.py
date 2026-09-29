"""Seed immutable reviewed packs with the migration role, never at request time."""
import hashlib
import json
import os
from datetime import datetime

import psycopg
from app.agent_workflows.runtime import PostgresSaver
from app.core.config import get_settings
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.domain_pack import load_pack, load_python_pack
from psycopg import sql
from psycopg.types.json import Jsonb


def _insert_immutable(conn, table, values, keys):
    columns = list(values)
    conn.execute(sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING").format(
        sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, columns)),
        sql.SQL(",").join(sql.Placeholder() for _ in columns), sql.SQL(",").join(map(sql.Identifier, keys)),
    ), tuple(Jsonb(v) if isinstance(v, (list, dict)) else v for v in values.values()))
    row = conn.execute(sql.SQL("SELECT {} FROM {} WHERE {}").format(
        sql.SQL(",").join(map(sql.Identifier, columns)), sql.Identifier(table),
        sql.SQL(" AND ").join(sql.SQL("{}=%s").format(sql.Identifier(k)) for k in keys),
    ), tuple(values[k] for k in keys)).fetchone()
    actual = dict(zip(columns, row, strict=True)) if not isinstance(row, dict) else row
    for column, expected in values.items():
        # Preserve published Python packs that predate this additive audit field.
        if column == "content_digest" and actual[column] == "":
            continue
        if actual[column] != expected:
            raise ValueError(f"Immutable {table} content differs at {column}; publish a new version")


def seed_reviewed_pack(conn, data):
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    pack_fields = ("pack_key", "version", "status", "supported_scope", "title", "stage_blueprints",
                   "resource_refs", "practice_blueprints", "provenance")
    _insert_immutable(conn, "domain_packs", {**{k: data[k] for k in pack_fields}, "content_digest": digest}, ("pack_key", "version"))
    for source in data["resources"]:
        if source.get("verification_status") == "reviewed" and not source.get("checked_at"):
            raise ValueError("Reviewed resource requires actual dated review evidence")
        values = {k: source[k] for k in ("source_id", "canonical_url", "title", "creator", "media_type", "language", "source_version")}
        values.update(provenance=data["provenance"], documentation_version=source.get("documentation_version", ""),
                      verification_status=source.get("verification_status", "legacy_index"))
        if source.get("checked_at"):
            values["checked_at"] = datetime.fromisoformat(source["checked_at"].replace("Z", "+00:00"))
        _insert_immutable(conn, "public_resource_sources", values, ("source_id",))
        for section in source["sections"]:
            values = {k: section[k] for k in ("section_id", "order_index", "title", "url")}
            values.update(source_id=source["source_id"], verification_status=section.get("verification_status", "legacy_index"),
                          review_note=section.get("review_note", ""))
            if section.get("verification_status") == "reviewed" and (not section.get("checked_at") or not section.get("review_note")):
                raise ValueError("Reviewed chapter requires date and content review note")
            if section.get("checked_at"):
                values["checked_at"] = datetime.fromisoformat(section["checked_at"].replace("Z", "+00:00"))
            _insert_immutable(conn, "public_resource_sections", values, ("section_id",))


def main():
    settings = get_settings()
    migration = to_psycopg_dsn(os.environ["STUDYPLAN_MIGRATION_DSN"])
    with psycopg.connect(migration) as conn:
        conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(project_id) DO NOTHING",
                     (settings.local_project_id, settings.local_actor_id, "我的学习空间", "Python 工程入门", "local.learning"))
        for data in (load_python_pack(), load_pack("agent-application-v1.json")):
            seed_reviewed_pack(conn, data)
    if os.environ.get("CHECKPOINT_SETUP_DSN"):
        with PostgresSaver.from_conn_string(to_psycopg_dsn(os.environ["CHECKPOINT_SETUP_DSN"])) as saver:
            saver.setup()
    print("[B3-F2] Immutable reviewed packs and resource indexes ready")


if __name__ == "__main__":
    main()
