"""Encrypted actor-scoped settings. No secret is returned by metadata methods."""
from contextlib import contextmanager

import psycopg
from app.core.errors import AppError, ConflictError, ErrorCode, ValidationAppError
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.ports.model_settings import ModelConfiguration, ModelSettingsView
from cryptography.fernet import Fernet, InvalidToken
from psycopg.rows import dict_row


class PgModelSettings:
    def __init__(self, dsn, master_key):
        self.dsn = to_psycopg_dsn(dsn)
        self.master_key = master_key
        if master_key:
            self._cipher()

    def _cipher(self):
        try:
            return Fernet(self.master_key.encode())
        except (ValueError, TypeError):
            raise AppError(ErrorCode.DEPENDENCY_UNAVAILABLE,"Model credential encryption is not configured") from None

    @contextmanager
    def _connect(self, actor_id, project_id=""):
        with psycopg.connect(self.dsn,row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)", (actor_id,project_id))
            yield conn

    def _current(self, conn, actor_id):
        return conn.execute("""SELECT v.* FROM user_model_settings c JOIN user_model_setting_versions v
            USING(actor_id,version) WHERE c.actor_id=%s""",(actor_id,)).fetchone()

    def _view(self, row):
        return ModelSettingsView(row["version"],row["base_url"],row["model_id"],row["protocol"],bool(row["encrypted_api_key"]))

    def get(self, actor_id):
        with self._connect(actor_id) as conn:
            row = self._current(conn,actor_id)
            return self._view(row) if row else None

    def _configuration(self, row):
        try:
            secret = self._cipher().decrypt(row["encrypted_api_key"].encode()).decode()
        except (InvalidToken, AttributeError, UnicodeError):
            raise AppError(ErrorCode.DEPENDENCY_UNAVAILABLE,"Model credential unavailable or revoked") from None
        return ModelConfiguration(row["version"],row["base_url"],row["model_id"],row["protocol"],secret)

    def resolve(self, actor_id):
        with self._connect(actor_id) as conn:
            row = self._current(conn,actor_id)
            return self._configuration(row) if row and row["encrypted_api_key"] else None

    def save(self, actor_id, *, expected_version, base_url, model_id, protocol, api_key):
        return self._write(actor_id,expected_version,base_url,model_id,protocol,api_key,False)

    def clear(self, actor_id, *, expected_version):
        return self._write(actor_id,expected_version,"","","openai","",True)

    def _write(self, actor_id, expected, base_url, model_id, protocol, api_key, clear):
        cipher = self._cipher()
        with self._connect(actor_id) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",("model-settings:"+actor_id,))
            old = self._current(conn,actor_id)
            current = old["version"] if old else 0
            if expected != current:
                raise ConflictError("Model settings changed; reload the current version")
            if clear:
                ciphertext = None
            elif api_key:
                ciphertext = cipher.encrypt(api_key.encode()).decode()
            elif old and old["encrypted_api_key"]:
                # Validate the master key before retaining an existing credential.
                self._configuration(old)
                ciphertext = old["encrypted_api_key"]
            else:
                raise ValidationAppError("API Key is required for new model settings")
            version = current+1
            row = conn.execute("""INSERT INTO user_model_setting_versions
                (actor_id,version,base_url,model_id,protocol,encrypted_api_key)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
                (actor_id,version,base_url,model_id,protocol,ciphertext)).fetchone()
            if old:
                cursor = conn.execute("UPDATE user_model_settings SET version=%s WHERE actor_id=%s AND version=%s",(version,actor_id,expected))
            else:
                cursor = conn.execute("INSERT INTO user_model_settings(actor_id,version) VALUES (%s,%s)",(actor_id,version))
            if cursor.rowcount != 1:
                raise ConflictError("Model settings changed")
            if clear:
                conn.execute("UPDATE user_model_setting_versions SET encrypted_api_key=NULL WHERE actor_id=%s",(actor_id,))
            return self._view(row)

    def bind_run(self, actor_id, project_id, run_id):
        with self._connect(actor_id,project_id) as conn:
            # A run cannot borrow another actor's revision, even in the same project.
            run = conn.execute("SELECT actor_id FROM ai_runs WHERE run_id=%s AND project_id=%s",(run_id,project_id)).fetchone()
            if not run or run["actor_id"] != actor_id:
                raise ConflictError("Run model settings ownership mismatch")
            row = conn.execute("""SELECT v.* FROM ai_run_model_settings r JOIN user_model_setting_versions v
                ON v.actor_id=r.actor_id AND v.version=r.settings_version WHERE r.run_id=%s""",(run_id,)).fetchone()
            if row:
                return self._configuration(row)
            row = self._current(conn,actor_id)
            if not row or not row["encrypted_api_key"]:
                return None
            conn.execute("""INSERT INTO ai_run_model_settings(run_id,actor_id,settings_version) VALUES (%s,%s,%s)
                ON CONFLICT(run_id) DO NOTHING""",(run_id,actor_id,row["version"]))
            # Read the actual selected revision if another request won the insert.
            row = conn.execute("""SELECT v.* FROM ai_run_model_settings r JOIN user_model_setting_versions v
                ON v.actor_id=r.actor_id AND v.version=r.settings_version WHERE r.run_id=%s""",(run_id,)).fetchone()
            return self._configuration(row)
