"""Alembic environment.

## WHY THIS FILE AND alembic.ini ARE PURE ASCII

configparser reads them with encoding="locale", which on a Chinese Windows is
GBK. A UTF-8 Chinese comment therefore crashes `alembic` with
UnicodeDecodeError BEFORE any of our own Python runs. Keep comments in .py
docstrings like this one, not in .ini files.

## Connection string

Read from the environment variable `STUDYPLAN_MIGRATION_DSN`. The migration role
and the application role MUST be different: migrations need DDL rights, and the
application role (studyplan_app) must not have them (ADR-0003).

This file contains no database URL and no password.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

#: 迁移专用 DSN。默认不指向任何真实库 —— 必须显式提供（C11）。
DEFAULT_LOCAL_DSN = (
    "postgresql+psycopg://studyplan_migrator@127.0.0.1:5432/studyplan_app"
)


def _dsn() -> str:
    return os.environ.get("STUDYPLAN_MIGRATION_DSN", DEFAULT_LOCAL_DSN)


def run_migrations_offline() -> None:
    context.configure(
        url=_dsn(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _dsn()
    connectable = engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
