"""Provision NEW local B3 databases. Never changes existing DBs or role passwords.

Only use on a local developer instance. Generated database/role names avoid collisions.
Existing studyplan_app and studyplan_migrator roles must already satisfy the test setup.
No cloud LLM call is made by this command.
"""
import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "backend"))


def load_env():
    for line in (ROOT/".env").read_text(encoding="utf-8-sig").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key,value = line.split("=",1)
            os.environ[key] = value.strip().strip('"').strip("'")


def update_env(values):
    # Preserve LLM fields the user may have filled while setup was running.
    path = ROOT/".env"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for i,line in enumerate(lines):
        key = line.split("=",1)[0]
        if key in values:
            lines[i] = key + "=" + values.pop(key)
    lines += [k+"="+v for k,v in values.items()]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    load_env()
    if os.environ.get("DATABASE_URL"):
        raise SystemExit("Existing DATABASE_URL is configured; not provisioning another database")
    suffix = uuid.uuid4().hex[:8]
    business = "studyplan_b3_local_" + suffix
    checkpoint = "studyplan_b3_checkpoint_" + suffix
    cp_role = "studyplan_b3_cp_" + suffix
    cp_password = secrets.token_urlsafe(32)
    admin = os.environ.get("STUDYPLAN_LOCAL_PG_ADMIN_DSN", "postgresql://postgres:postgres@127.0.0.1:5432/postgres")
    # We create new objects only; do not alter/drop any existing object.
    with psycopg.connect(admin,autocommit=True) as conn:
        roles = conn.execute("SELECT rolname,rolsuper,rolbypassrls FROM pg_roles WHERE rolname IN ('studyplan_app','studyplan_migrator')").fetchall()
        actual = {r[0]:r[1:] for r in roles}
        if actual.get("studyplan_app") != (False,False) or actual.get("studyplan_migrator") != (False,True):
            raise SystemExit("Existing migration/application roles do not meet isolation requirements")
        conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD {}").format(sql.Identifier(cp_role),sql.Literal(cp_password)))
        for database in (business,checkpoint):
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    admin_args = conninfo_to_dict(admin)
    for database in (business,checkpoint):
        with psycopg.connect(make_conninfo(**{**admin_args,"dbname":database}),autocommit=True) as conn:
            conn.execute('ALTER SCHEMA public OWNER TO studyplan_migrator')
            conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            conn.execute('GRANT USAGE ON SCHEMA public TO studyplan_app')
    host = admin_args.get("host","127.0.0.1")
    port = admin_args.get("port","5432")
    app_password = os.environ.get("STUDYPLAN_LOCAL_APP_PASSWORD","studyplan_app_test_pw")
    migrator_password = os.environ.get("STUDYPLAN_LOCAL_MIGRATOR_PASSWORD","studyplan_migrator_test_pw")
    app_dsn = f"postgresql://studyplan_app:{quote(app_password)}@{host}:{port}/{business}"
    mig_dsn = f"postgresql://studyplan_migrator:{quote(migrator_password)}@{host}:{port}/{business}"
    cp_setup = f"postgresql://studyplan_migrator:{quote(migrator_password)}@{host}:{port}/{checkpoint}"
    cp_dsn = f"postgresql://{cp_role}:{quote(cp_password)}@{host}:{port}/{checkpoint}"
    values = {"DATABASE_URL":app_dsn,"DATABASE_URL_SYNC":app_dsn,
              "STUDYPLAN_MIGRATION_DSN":mig_dsn,"CHECKPOINT_DATABASE_URL":cp_dsn,"CHECKPOINT_SETUP_DSN":cp_setup}
    update_env(dict(values))
    env = dict(os.environ,**values,PYTHONPATH=str(ROOT/"backend"))
    env["STUDYPLAN_MIGRATION_DSN"] = mig_dsn.replace("postgresql://","postgresql+psycopg://")
    subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=ROOT/"backend",env=env,check=True)
    subprocess.run([sys.executable,"-m","app.tools.seed_b3"],cwd=ROOT,env=env,check=True)
    with psycopg.connect(cp_setup,autocommit=True) as conn:
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(cp_role)))
        conn.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(cp_role)))
        conn.execute(sql.SQL("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(cp_role)))
    with psycopg.connect(app_dsn):
        pass
    with psycopg.connect(cp_dsn):
        pass
    print(f"[B3] New local databases ready: {business}, {checkpoint}; credentials saved only to .env")


if __name__ == "__main__":
    main()
