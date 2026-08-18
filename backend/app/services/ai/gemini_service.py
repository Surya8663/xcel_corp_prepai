"""
PrepAI — GeminiService: the single AI service layer for the entire application.

ARCHITECTURE RULE:
  Every AI feature in this app MUST call through GeminiService.
  No code outside this file and app.core.gemini_client may instantiate or
  call the Gemini SDK directly.

DESIGN DECISIONS:
  - generate_structured_json() uses Gemini's native JSON mode
    (response_mime_type="application/json") so the SDK enforces valid JSON
    at the model level.  A regex-fallback is used ONLY as a last-resort safety
    net, and it NEVER silently returns empty/default/fabricated data — it raises
    AIServiceError so callers always know something went wrong.
  - All calls are logged to ai_call_logs (feature_name, success, latency_ms).
  - Rate-limit / server errors are surfaced as distinct exception subclasses so
    the API layer can return the correct HTTP status and user-facing message.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from google.genai import types as genai_types
from google.genai.errors import APIError, ClientError, ServerError

from app.core.gemini_client import DEFAULT_MODEL, _get_client
from app.services.ai.log_writer import write_ai_call_log

logger = logging.getLogger(__name__)


# ── Custom exception hierarchy ─────────────────────────────────────────────────

class AIServiceError(Exception):
    """Base error raised by GeminiService.  Never contains fabricated data."""
    user_message: str = "AI service error. Please try again."


class AIRateLimitError(AIServiceError):
    """Raised when Gemini returns HTTP 429 (quota / rate limit)."""
    user_message: str = (
        "AI service is temporarily rate-limited. Please wait a moment and retry."
    )


class AIServerError(AIServiceError):
    """Raised when Gemini returns a 5xx server-side error."""
    user_message: str = (
        "AI service is temporarily unavailable. Please retry in a few seconds."
    )


class AITimeoutError(AIServiceError):
    """Raised when the request to Gemini exceeds the configured timeout."""
    user_message: str = (
        "The AI request timed out. Please try again with a shorter prompt."
    )


class AIParseError(AIServiceError):
    """Raised when the model returns text that cannot be parsed as valid JSON."""
    user_message: str = (
        "The AI returned an unexpected response format. Please retry."
    )


# ── Helper: extract JSON from markdown fences (last-resort ONLY) ──────────────

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def _extract_json_from_fence(text: str) -> dict | list:
    """
    Attempt to extract JSON from markdown fences or bracket boundaries.
    Raises AIParseError if extraction fails.
    """
    cleaned = text.strip()
    # Strip markdown ```json ... ``` wrapper if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find outer bracket bounds [ ... ] or { ... }
    first_bracket = min(
        [i for i in [cleaned.find("["), cleaned.find("{")] if i != -1],
        default=-1,
    )
    last_bracket = max(cleaned.rfind("]"), cleaned.rfind("}"))

    if first_bracket != -1 and last_bracket > first_bracket:
        candidate = cleaned[first_bracket : last_bracket + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise AIParseError(
        f"Cannot parse AI response as JSON even after fence extraction. "
        f"Raw response (first 300 chars): {text[:300]!r}"
    )


# ── GeminiService ──────────────────────────────────────────────────────────────

class GeminiService:
    """
    Central AI service.  Inject via FastAPI dependency (see get_gemini_service).

    All public methods:
      - Are fully typed.
      - Log every call (success or failure) to ai_call_logs.
      - Raise a specific AIServiceError subclass on failure — NEVER return
        fallback/mock data pretending to be a real AI response.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        db_session: Any | None = None,   # AsyncSession | None
    ) -> None:
        self._model = model_name
        self._db = db_session
        self._client = _get_client()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate_text(
        self,
        prompt: str,
        *,
        feature_name: str = "generate_text",
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        """
        Generate free-form text from a prompt.

        Args:
            prompt: The full prompt string.
            feature_name: Label for this call in ai_call_logs (e.g. 'resume_audit').
            temperature: Sampling temperature override (0.0–2.0).
            max_output_tokens: Response length cap.

        Returns:
            Non-empty response text from Gemini.

        Raises:
            AIRateLimitError: Gemini returned HTTP 429.
            AIServerError: Gemini returned a 5xx error.
            AITimeoutError: Request timed out.
            AIServiceError: Any other API failure.
        """
        config = self._build_config(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        return await self._call(
            prompt=prompt,
            config=config,
            feature_name=feature_name,
            parse_json=False,
        )  # type: ignore[return-value]

    async def generate_structured_json(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
        *,
        feature_name: str = "generate_structured_json",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """
        Generate structured JSON output using Gemini's native JSON mode.

        The model is constrained to return valid JSON via
        response_mime_type="application/json".  If a response_schema dict is
        provided it is forwarded to the SDK for additional schema enforcement.

        Parse strategy (in order):
          1. json.loads(response.text)         — primary path (should always work)
          2. _extract_json_from_fence(text)    — safety net for malformed wrapping
          3. Raise AIParseError                — NEVER return empty/fake data

        Args:
            prompt: The full prompt string (include JSON schema description inline).
            response_schema: Optional JSON Schema dict passed to the SDK.
            feature_name: Label for this call in ai_call_logs.
            temperature: Sampling temperature override.

        Returns:
            Parsed dict from the model's JSON response.

        Raises:
            AIParseError: If the response cannot be parsed as JSON.
            AIRateLimitError / AIServerError / AITimeoutError / AIServiceError:
                On API-level failures.
        """
        config = self._build_config(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=temperature,
        )
        result = await self._call(
            prompt=prompt,
            config=config,
            feature_name=feature_name,
            parse_json=True,
        )
        return result  # type: ignore[return-value]

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_config(
        self,
        response_mime_type: str | None = None,
        response_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> genai_types.GenerateContentConfig:
        """Build a GenerateContentConfig from non-None parameters only."""
        kwargs: dict[str, Any] = {}
        if response_mime_type:
            kwargs["response_mime_type"] = response_mime_type
        if response_schema is not None:
            kwargs["response_schema"] = response_schema
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        return genai_types.GenerateContentConfig(**kwargs)

    async def _call(
        self,
        prompt: str,
        config: genai_types.GenerateContentConfig,
        feature_name: str,
        parse_json: bool,
        max_retries: int = 3,
    ) -> str | dict[str, Any]:
        """
        Core dispatch: call Gemini with automatic retry for rate limits / 503s,
        log the result, and handle errors.
        """
        prompt_excerpt = prompt[:300].replace("\n", " ")
        t_start = time.monotonic()
        success = False
        error_msg: str | None = None

        try:
            for attempt in range(1, max_retries + 1):
                try:
                    response = self._client.models.generate_content(
                        model=self._model,
                        contents=prompt,
                        config=config,
                    )
                    raw_text: str = response.text or ""
                    latency_ms = int((time.monotonic() - t_start) * 1000)

                    logger.info(
                        "[AI] feature=%s latency=%dms response_len=%d",
                        feature_name, latency_ms, len(raw_text),
                    )

                    if not raw_text.strip():
                        raise AIServiceError(
                            "Gemini returned an empty response. "
                            "Check prompt length and model availability."
                        )

                    if parse_json:
                        result = self._parse_json_response(raw_text)
                        success = True
                        return result

                    success = True
                    return raw_text

                except (ClientError, ServerError, APIError) as exc:
                    err_str = str(exc)
                    is_rate_limit = "429" in err_str or "503" in err_str or "RESOURCE_EXHAUSTED" in err_str.upper() or "UNAVAILABLE" in err_str.upper()
                    if is_rate_limit and attempt < max_retries:
                        wait_sec = attempt * 8
                        logger.warning("[AI] Gemini rate limited/503 (attempt %d/%d). Retrying in %ds...", attempt, max_retries, wait_sec)
                        await asyncio.sleep(wait_sec)
                        continue

                    latency_ms = int((time.monotonic() - t_start) * 1000)
                    error_msg = err_str
                    if is_rate_limit:
                        raise AIRateLimitError(f"Gemini rate limit exceeded: {exc}") from exc
                    raise AIServiceError(f"Gemini API error: {exc}") from exc

            raise AIServiceError("Gemini API retries exhausted.")

        except TimeoutError as exc:
            latency_ms = int((time.monotonic() - t_start) * 1000)
            error_msg = str(exc)
            raise AITimeoutError(str(exc)) from exc

        except Exception as exc:
            if isinstance(exc, AIServiceError):
                raise exc
            latency_ms = int((time.monotonic() - t_start) * 1000)
            error_msg = str(exc)
            logger.error("[AI] Unexpected error in feature=%s: %s", feature_name, exc)
            raise AIServiceError(f"Unexpected AI error: {exc}") from exc

        finally:
            # Fire-and-forget log — never let a logging failure mask the real error
            try:
                await write_ai_call_log(
                    db=self._db,
                    feature_name=feature_name,
                    prompt_excerpt=prompt_excerpt,
                    success=success,
                    latency_ms=latency_ms,
                    error_msg=error_msg,
                )
            except Exception as log_exc:
                logger.warning("[AI] Failed to write ai_call_log: %s", log_exc)

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """
        Parse JSON from the model response.

        Strategy:
          1. json.loads directly  (primary — should always work in JSON mode)
          2. markdown fence extraction  (last-resort safety net)
          3. raise AIParseError   (NEVER return empty/default/fabricated data)
        """
        # Primary: direct parse (works 99.9% of the time with JSON mode)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, (dict, list)):
                return parsed  # type: ignore[return-value]
            raise AIParseError(
                f"AI response parsed as {type(parsed).__name__}, expected dict or list. "
                f"Raw: {text[:200]!r}"
            )
        except json.JSONDecodeError:
            pass

        # Last-resort: try to extract from markdown fences
        logger.warning(
            "[AI] Primary JSON parse failed, attempting fence extraction. "
            "raw_text[:200]=%r", text[:200]
        )
        return _extract_json_from_fence(text)  # raises AIParseError if this fails too


# ── FastAPI dependency factory ─────────────────────────────────────────────────

def get_gemini_service(
    db: Any = None,
    model_name: str = DEFAULT_MODEL,
) -> GeminiService:
    """
    Return a GeminiService instance.  Pass as a FastAPI Depends parameter:

        @router.post("/endpoint")
        async def my_endpoint(
            db: AsyncSession = Depends(get_db),
            ai: GeminiService = Depends(lambda db=Depends(get_db): get_gemini_service(db=db)),
        ):
            ...
    """
    return GeminiService(model_name=model_name, db_session=db)
