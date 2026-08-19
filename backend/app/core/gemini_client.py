"""
PrepAI — Reusable Gemini AI client wrapper.

ALL AI features in this project must call through this module.
Never instantiate google.genai ad hoc elsewhere.

Uses the current recommended google-genai SDK (NOT the deprecated google-generativeai).
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Return a singleton Gemini Client instance."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Gemini SDK client initialized successfully.")
    return _client


DEFAULT_MODEL = get_settings().GEMINI_MODEL


async def generate_text(
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    generation_config: dict[str, Any] | None = None,
) -> str:
    """
    Generate text from a prompt using Gemini.

    Args:
        prompt: The text prompt to send to Gemini.
        model_name: Model variant to use (default: gemini-2.0-flash).
        generation_config: Optional generation parameters (temperature, max_tokens, etc.).

    Returns:
        The generated text as a string.

    Raises:
        RuntimeError: If the API call fails.
    """
    client = _get_client()

    config_kwargs: dict[str, Any] = {}
    if generation_config:
        config_kwargs["config"] = genai_types.GenerateContentConfig(**generation_config)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            **config_kwargs,
        )
        return response.text or ""
    except Exception as exc:
        logger.error("Gemini API call failed: %s", exc)
        raise RuntimeError(f"Gemini generation failed: {exc}") from exc


def ping_gemini() -> str:
    """
    Make a minimal real test call to Gemini and return the response text.
    Used only at startup to validate the API key.  NOT mocked.

    Returns:
        The raw response text from Gemini.
    """
    client = _get_client()
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents="Reply with exactly: GEMINI_OK",
    )
    return (response.text or "").strip()
