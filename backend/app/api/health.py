"""PrepAI — Health-check API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, ping_database
from app.core.gemini_client import ping_gemini

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("", summary="Comprehensive health check")
@router.get("/", summary="Comprehensive health check", include_in_schema=False)
async def health_check(response: Response) -> dict:
    """
    Return comprehensive application health status verifying both
    PostgreSQL DB connectivity and valid Gemini API key presence.
    Lightweight check — does NOT burn model generation quota.
    """
    db_ok = await ping_database()
    
    key = settings.GEMINI_API_KEY or ""
    gemini_key_valid = bool(key.strip() and not key.startswith("your_"))

    is_healthy = db_ok and gemini_key_valid

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if is_healthy else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected" if db_ok else "unreachable",
        "gemini_api": "valid" if gemini_key_valid else "missing_or_invalid",
    }


@router.get("/db", summary="Database connectivity check")
async def db_health(db: AsyncSession = Depends(get_db)) -> dict:
    """Verify database connectivity."""
    is_healthy = await ping_database()
    return {"database": "connected" if is_healthy else "unreachable"}


@router.get("/gemini", summary="Gemini API connectivity check")
async def gemini_health() -> dict:
    """Verify Gemini API key validity with a test call."""
    try:
        res = ping_gemini()
        return {"gemini": "connected", "response": res}
    except Exception as exc:
        return {"gemini": "failed", "error": str(exc)}
