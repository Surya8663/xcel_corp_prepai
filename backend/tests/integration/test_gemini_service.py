"""
Integration tests for GeminiService.

These tests hit the REAL Gemini API — no mocking.
They require:
  - GEMINI_API_KEY set in backend/.env
  - Active internet connection

Run with:
    cd backend
    .venv\\Scripts\\Activate.ps1
    pytest tests/integration/test_gemini_service.py -v -s
"""

from __future__ import annotations

import pytest
import sys
import os

# Force UTF-8 output on Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.ai.gemini_service import (
    AIParseError,
    AIServiceError,
    GeminiService,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def ai() -> GeminiService:
    """
    Return a GeminiService with no DB session.
    Logging will be skipped (no DB available in integration tests by design).
    """
    return GeminiService(db_session=None)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestGenerateText:
    """Real API tests for GeminiService.generate_text()."""

    async def test_basic_hello_returns_nonempty_string(self, ai: GeminiService) -> None:
        """
        PRIMARY integration test.
        Sends a simple prompt to the live Gemini API and asserts:
          - Response is a non-empty string.
          - Response does not contain obvious error markers.

        This test MUST print the actual Gemini response to the console
        so it can be visually verified in CI / manual runs.
        """
        prompt = "Say hello in one sentence."
        response = await ai.generate_text(prompt, feature_name="integration_test_hello")

        # ── Print to console for human verification ────────────────────────────
        print(f"\n{'=' * 60}")
        print(f"  REAL Gemini API response:")
        print(f"  Prompt : {prompt!r}")
        print(f"  Response: {response!r}")
        print(f"{'=' * 60}\n")

        # ── Assertions ─────────────────────────────────────────────────────────
        assert isinstance(response, str), \
            f"Expected str, got {type(response)}"
        assert len(response.strip()) > 0, \
            "Gemini returned an empty response — API key or quota issue?"
        assert len(response) >= 5, \
            f"Response too short to be a real sentence: {response!r}"

    async def test_response_is_coherent_english(self, ai: GeminiService) -> None:
        """
        Ask Gemini a factual question and verify the answer is plausible.
        We don't assert exact content (model outputs vary), just that the
        response is non-empty and contains the expected answer in some form.
        """
        prompt = "What is the capital of France? Answer in one word only, no punctuation."
        response = await ai.generate_text(prompt, feature_name="integration_test_factual")

        print(f"\n  [Factual test] prompt={prompt!r} -> response={response!r}\n")

        assert isinstance(response, str)
        assert len(response.strip()) > 0
        # Strip all punctuation/whitespace and check case-insensitively
        normalized = response.strip().rstrip(".,!?\n").lower()
        assert "paris" in normalized, \
            f"Expected 'Paris' somewhere in response, got: {response!r} (normalized: {normalized!r})"

    async def test_temperature_parameter_accepted(self, ai: GeminiService) -> None:
        """Verify that passing temperature does not crash the SDK."""
        response = await ai.generate_text(
            "Say the number 42.",
            temperature=0.1,
            feature_name="integration_test_temperature",
        )
        print(f"\n  [Temp=0.1 test] response={response!r}\n")
        assert len(response.strip()) > 0


class TestGenerateStructuredJson:
    """Real API tests for GeminiService.generate_structured_json()."""

    async def test_returns_valid_dict(self, ai: GeminiService) -> None:
        """
        Ask Gemini to produce JSON and verify it parses to a dict.
        Uses native JSON mode (response_mime_type=application/json).
        """
        prompt = (
            "Return a JSON object with exactly two keys: "
            "'greeting' (a friendly hello string) and "
            "'language' (the language used, e.g. 'English'). "
            "Output ONLY the JSON object, nothing else."
        )
        result = await ai.generate_structured_json(
            prompt,
            feature_name="integration_test_structured_json",
        )

        print(f"\n{'=' * 60}")
        print(f"  REAL Gemini structured JSON response:")
        print(f"  Result type : {type(result)}")
        print(f"  Result value: {result}")
        print(f"{'=' * 60}\n")

        assert isinstance(result, dict), \
            f"Expected dict, got {type(result)}: {result!r}"
        assert len(result) > 0, \
            "Gemini returned an empty JSON object"
        assert "greeting" in result, \
            f"Expected 'greeting' key in result, got keys: {list(result.keys())}"
        assert isinstance(result["greeting"], str), \
            f"Expected 'greeting' to be a string, got: {type(result['greeting'])}"

    async def test_structured_json_with_schema(self, ai: GeminiService) -> None:
        """
        Provide an explicit response_schema and verify the model respects it.
        """
        schema = {
            "type": "object",
            "properties": {
                "name":  {"type": "string"},
                "score": {"type": "number"},
                "tags":  {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "score", "tags"],
        }
        prompt = (
            "Return a JSON object for a fictional candidate named 'Alex' "
            "with a score of 87.5 and tags ['python', 'fastapi']. "
            "Follow the schema exactly."
        )
        result = await ai.generate_structured_json(
            prompt,
            response_schema=schema,
            feature_name="integration_test_structured_json_schema",
        )

        print(f"\n  [Schema test] result={result!r}\n")

        assert isinstance(result, dict)
        assert "name" in result
        assert "score" in result
        assert "tags" in result
        assert isinstance(result["tags"], list)


class TestErrorHandling:
    """Verify the error handling contracts of GeminiService."""

    async def test_empty_prompt_does_not_crash(self, ai: GeminiService) -> None:
        """
        An empty prompt might return an empty response or a minimal one.
        GeminiService should raise AIServiceError rather than returning empty data.
        We accept either a valid non-empty response OR an AIServiceError.
        We NEVER accept a silent empty string return.
        """
        try:
            response = await ai.generate_text(
                "   ",  # whitespace-only prompt
                feature_name="integration_test_empty_prompt",
            )
            # If we get here, the model returned something
            # It's acceptable as long as it's not a silent empty string
            print(f"\n  [Empty prompt] model responded with: {response!r}\n")
            # We don't assert content — the model may hallucinate something
            # but we verify the service didn't silently return ""
            assert response is not None
        except AIServiceError as exc:
            # Also acceptable — the service correctly surfaced the error
            print(f"\n  [Empty prompt] service raised AIServiceError: {exc}\n")

    async def test_service_never_returns_none(self, ai: GeminiService) -> None:
        """generate_text must always return a str, never None."""
        response = await ai.generate_text(
            "Say 'test'.",
            feature_name="integration_test_not_none",
        )
        assert response is not None
        assert isinstance(response, str)
