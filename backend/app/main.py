"""PrepAI — FastAPI application entry point."""

from __future__ import annotations

import logging
import sys

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.interview import router as interview_router
from app.api.prep import router as prep_router
from app.api.resume import router as resume_router
from app.core.config import get_settings
from app.core.database import ping_database
from app.core.logging_config import setup_logging
from app.core.middleware import (
    RequestLoggingMiddleware,
    ai_service_exception_handler,
    global_unhandled_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.services.ai.gemini_service import AIServiceError

# Setup structured logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ───────────────────────────────────────────────────────
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(AIServiceError, ai_service_exception_handler)
app.add_exception_handler(Exception, global_unhandled_exception_handler)

app.include_router(health_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api")
app.include_router(health_router, prefix="")
app.include_router(prep_router, prefix="/api/v1")
app.include_router(resume_router, prefix="/api/v1")
app.include_router(interview_router, prefix="/api")
app.include_router(interview_router, prefix="/api/v1")

# Convenience aliases for frontend API calls
app.include_router(resume_router, prefix="/api")
app.include_router(prep_router, prefix="/api")


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_checks() -> None:
    """Run connectivity checks and table initialization at server startup."""
    logger.info("=" * 60)
    logger.info("  PrepAI Backend — Starting up with Centralized Reliability Handlers")
    logger.info("=" * 60)

    logger.info("[DB] Initializing tables and checking PostgreSQL connection...")
    from app.core.database import init_db
    await init_db()
    db_ok = await ping_database()
    if db_ok:
        logger.info("[DB] PostgreSQL: CONNECTED & READY")
    else:
        logger.error("[DB] PostgreSQL: FAILED — check DATABASE_URL in .env")

    logger.info("=" * 60)


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint — confirms the API is alive."""
    return {
        "message": "PrepAI Backend is running 🚀",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
