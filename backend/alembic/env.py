"""
Alembic env.py — PrepAI async configuration.

- Reads DATABASE_URL from pydantic-settings (backend/.env).
- Converts it to the asyncpg driver URL automatically.
- Imports all SQLAlchemy models so autogenerate detects them.
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Make sure the backend root is importable ──────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Load our settings (reads backend/.env) ────────────────────────────────────
from app.core.config import get_settings  # noqa: E402

# ── Import all models so Alembic autogenerate can detect them ─────────────────
from app.core.database import Base        # noqa: E402
import app.models                         # noqa: E402, F401  (registers all ORM classes on Base)

settings = get_settings()

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Build the asyncpg-compatible URL and inject it into Alembic config
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)

config.set_main_option("sqlalchemy.url", _db_url)

# Autogenerate target
target_metadata = Base.metadata


# ── Offline mode (generates SQL script, no live DB needed) ────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects to live DB and applies migrations) ──────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
