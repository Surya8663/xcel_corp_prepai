"""
PrepAI — AI Call Log writer.

Writes asynchronously to the ai_call_logs table.
Imported only by GeminiService — not part of the public API surface.

Design notes:
  - The write is always fire-and-forget from GeminiService's finally block.
  - If the DB session is None (e.g. in integration tests without a DB),
    the write is silently skipped — tests should pass without a DB.
  - A logging failure never propagates to the caller.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def write_ai_call_log(
    *,
    db: Any,                    # AsyncSession | None
    feature_name: str,
    prompt_excerpt: str,
    success: bool,
    latency_ms: int,
    error_msg: str | None = None,
) -> None:
    """
    Persist one ai_call_logs row.
    Silently no-ops when db is None (useful in tests / scripts).
    """
    if db is None:
        return

    try:
        # Import here to avoid circular imports at module load time
        from app.models import AICallLog  # noqa: PLC0415

        log_entry = AICallLog(
            feature_name=feature_name[:100],
            prompt_excerpt=prompt_excerpt[:500],
            success=success,
            latency_ms=latency_ms,
            error_msg=(error_msg or "")[:1000] if error_msg else None,
        )
        db.add(log_entry)
        await db.commit()
    except Exception as exc:
        logger.warning("ai_call_log write failed (non-fatal): %s", exc)
