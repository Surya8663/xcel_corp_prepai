"""
PrepAI — Centralized Exception & Request Logging Middleware.

Ensures every endpoint returns consistent JSON error responses:
{
  "status": "error",
  "status_code": 400,
  "message": "Human readable error description",
  "detail": "Detailed context if available"
}
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.ai.gemini_service import (
    AIServiceError,
    AIRateLimitError,
    AIServerError,
    AITimeoutError,
    AIParseError,
)

logger = logging.getLogger(__name__)


# ── Request / Response Logging Middleware ────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        t0 = time.monotonic()
        path = request.url.path
        method = request.method

        try:
            response = await call_next(request)
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "[HTTP] %s %s -> %d (%dms)",
                method, path, response.status_code, latency_ms
            )
            return response
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.error(
                "[HTTP] %s %s -> ERROR (%dms): %s",
                method, path, latency_ms, exc
            )
            raise exc


# ── Global Exception Handlers ──────────────────────────────────────────────────

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard FastAPI HTTPExceptions."""
    message = exc.detail if isinstance(exc.detail, str) else "HTTP Request Error"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "status_code": exc.status_code,
            "message": message,
            "detail": exc.detail,
        },
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors (HTTP 422 -> mapped to clean 400/422)."""
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = " -> ".join([str(x) for x in first_err.get("loc", []) if x != "body"])
    msg = first_err.get("msg", "Invalid input data")
    user_msg = f"Validation Error in '{loc}': {msg}" if loc else f"Validation Error: {msg}"

    logger.warning("[VALIDATION] Path=%s | %s", request.url.path, user_msg)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "status_code": 400,
            "message": user_msg,
            "detail": errors,
        },
    )


async def ai_service_exception_handler(
    request: Request, exc: AIServiceError
) -> JSONResponse:
    """Handle custom AIServiceError exceptions from GeminiService."""
    if isinstance(exc, AIRateLimitError):
        code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, AIServerError):
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, AITimeoutError):
        code = status.HTTP_408_REQUEST_TIMEOUT
    elif isinstance(exc, AIParseError):
        code = status.HTTP_502_BAD_GATEWAY
    else:
        code = status.HTTP_500_INTERNAL_SERVER_ERROR

    logger.error("[AI_ERROR] Path=%s | Code=%d | Message=%s", request.url.path, code, exc)

    return JSONResponse(
        status_code=code,
        content={
            "status": "error",
            "status_code": code,
            "message": getattr(exc, "user_message", str(exc)),
            "detail": str(exc),
        },
    )


async def global_unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled server exceptions (HTTP 500). Does NOT leak stack trace."""
    logger.critical(
        "[UNHANDLED_EXCEPTION] Path=%s | Error: %s",
        request.url.path, exc, exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "status_code": 500,
            "message": "An internal server error occurred. Please try again or check backend logs.",
            "detail": str(exc),
        },
    )
