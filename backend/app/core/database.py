"""PrepAI — Database connection and session management."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Convert standard postgres:// URL to async driver URL if needed
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency — yield a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ping_database() -> bool:
    """
    Verify database connectivity by executing a trivial query.

    Returns:
        True if the database responds correctly, False otherwise.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                logger.info("✅  Database ping successful.")
                return True
            return False
    except Exception as exc:
        logger.error("❌  Database ping failed: %s", exc)
        return False


async def init_db() -> None:
    """Initialize all PostgreSQL tables and seed candidate profile #1 if not exists."""
    from app.models import Base, CandidateProfile
    from sqlalchemy import select

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[DB] All database tables initialized successfully.")

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CandidateProfile).limit(1))
            if not res.scalar_one_or_none():
                session.add(CandidateProfile(name="PrepAI Candidate"))
                await session.commit()
                logger.info("[DB] Candidate profile #1 seeded successfully.")
    except Exception as exc:
        logger.error("[DB] Database initialization error: %s", exc)

