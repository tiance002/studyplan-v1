"""Authentication tables are service-private; project reads still use owner RLS."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from app.application.browser_auth import HASHER, credentials, verify_password
from app.core.errors import AppError, ConflictError, ErrorCode, UnauthenticatedError
from app.core.ids import new_id
from app.domain.workspace.models import AuthContext
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from psycopg.rows import dict_row


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class PgBrowserAuth:
    def __init__(self, dsn: str, ttl: int):
        self.dsn, self.ttl = to_psycopg_dsn(dsn), ttl

    def connection(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def throttle(self, peer: str, username: str):
        buckets = [("peer:" + peer, 40), ("account:" + username.casefold(), 10)]
        limited = False
        with self.connection() as conn:
            for bucket, limit in buckets:
                conn.execute("SELECT set_config('app.auth_bucket',%s,true)", (token_hash(bucket),))
                row = conn.execute(
                    """INSERT INTO auth_throttle(bucket,attempts) VALUES (%s,1)
                    ON CONFLICT(bucket) DO UPDATE SET
                    attempts=CASE WHEN auth_throttle.window_start < now()-interval '10 minutes' THEN 1 ELSE auth_throttle.attempts+1 END,
                    window_start=CASE WHEN auth_throttle.window_start < now()-interval '10 minutes' THEN now() ELSE auth_throttle.window_start END
                    RETURNING attempts""",
                    (token_hash(bucket),),
                ).fetchone()
                limited = limited or row["attempts"] > limit
        if limited:
            raise AppError(ErrorCode.RATE_LIMITED, "尝试次数过多，请十分钟后再试")

    def register(self, username: str, password: str, peer: str) -> str:
        username, key = credentials(username, password)
        self.throttle(peer, key)
        actor, project = new_id("usr"), new_id("lpr")
        password_hash = HASHER.hash(password)
        try:
            with self.connection() as conn:
                conn.execute("SELECT set_config('app.actor_id',%s,true)", (actor,))
                conn.execute(
                    "INSERT INTO auth_users(actor_id,username,username_key,password_hash) VALUES(%s,%s,%s,%s)",
                    (actor, username, key, password_hash),
                )
                conn.execute("SELECT set_config('app.actor_id',%s,true)", (actor,))
                conn.execute(
                    """INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key)
                    VALUES(%s,%s,%s,'待创建学习目标',%s)""",
                    (project, actor, "我的学习空间", project),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise ConflictError("用户名已存在") from exc
        return self.issue(actor)

    def login(self, username: str, password: str, peer: str) -> str:
        username, key = credentials(username, password)
        self.throttle(peer, key)
        with self.connection() as conn:
            conn.execute("SELECT set_config('app.auth_username',%s,true)", (key,))
            row = conn.execute("SELECT * FROM auth_users WHERE username_key=%s", (key,)).fetchone()
        verify_password(password, row["password_hash"] if row else None)
        if HASHER.check_needs_rehash(row["password_hash"]):
            with self.connection() as conn:
                conn.execute("SELECT set_config('app.actor_id',%s,true)", (row["actor_id"],))
                conn.execute(
                    "UPDATE auth_users SET password_hash=%s WHERE actor_id=%s",
                    (HASHER.hash(password), row["actor_id"]),
                )
        return self.issue(row["actor_id"])

    def issue(self, actor: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.connection() as conn:
            conn.execute("SELECT set_config('app.actor_id',%s,true)", (actor,))
            conn.execute("DELETE FROM auth_sessions WHERE expires_at <= now()")
            conn.execute(
                """INSERT INTO auth_sessions(token_hash,actor_id,session_id,csrf_token,expires_at)
                VALUES(%s,%s,%s,%s,%s)""",
                (
                    token_hash(token),
                    actor,
                    new_id("ses"),
                    secrets.token_urlsafe(32),
                    datetime.now(timezone.utc) + timedelta(seconds=self.ttl),
                ),
            )
        return token

    def detail(self, token: str):
        with self.connection() as conn:
            conn.execute("SELECT set_config('app.auth_token_hash',%s,true)", (token_hash(token),))
            session = conn.execute(
                "SELECT actor_id FROM auth_sessions WHERE token_hash=%s AND expires_at>now()",
                (token_hash(token),),
            ).fetchone()
            if session is None:
                raise UnauthenticatedError()
            conn.execute("SELECT set_config('app.actor_id',%s,true)", (session["actor_id"],))
            row = conn.execute(
                """SELECT s.*,u.username FROM auth_sessions s JOIN auth_users u USING(actor_id)
                WHERE token_hash=%s AND expires_at>now()""",
                (token_hash(token),),
            ).fetchone()
            if row is None:
                raise UnauthenticatedError()
            conn.execute("SELECT set_config('app.actor_id',%s,true)", (row["actor_id"],))
            projects = conn.execute(
                "SELECT project_id FROM learning_projects WHERE archived_at IS NULL ORDER BY created_at"
            ).fetchall()
        return row, [p["project_id"] for p in projects]

    def resolve(self, token: str):
        try:
            row, projects = self.detail(token)
        except UnauthenticatedError:
            return None
        return AuthContext(
            actor_id=row["actor_id"],
            session_id=row["session_id"],
            issued_at=row["issued_at"],
            learning_project_scope=tuple(projects),
        )

    def logout(self, token: str):
        with self.connection() as conn:
            conn.execute("SELECT set_config('app.auth_token_hash',%s,true)", (token_hash(token),))
            conn.execute("DELETE FROM auth_sessions WHERE token_hash=%s", (token_hash(token),))
