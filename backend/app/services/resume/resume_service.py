"""
PrepAI — Resume Service.

Orchestrates the full resume audit pipeline:
  1. Extract text from uploaded PDF/DOCX (via extractor.py)
  2. Parse text into structured JSON via GeminiService
  3. Generate Resume Audit via GeminiService
  4. Persist results to the resumes table

This service never fabricates data — all content comes from the actual
uploaded file and real Gemini API responses.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Resume, CandidateProfile
from app.services.ai.gemini_service import GeminiService
from app.services.ai.prompt_templates import resume_parse_and_audit_prompt
from app.services.resume.extractor import ExtractionError, extract_text

logger = logging.getLogger(__name__)

# Upload directory (relative to backend root)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")


def _ensure_upload_dir() -> str:
    """Create the uploads directory if it doesn't exist and return its path."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def _save_file(filename: str, file_bytes: bytes) -> str:
    """
    Save uploaded file to the uploads directory with a UUID prefix.
    Returns the relative file path stored in the DB.
    """
    upload_dir = _ensure_upload_dir()
    safe_name = f"{uuid.uuid4().hex}_{filename}"
    full_path = os.path.join(upload_dir, safe_name)
    with open(full_path, "wb") as f:
        f.write(file_bytes)
    # Store a relative path from backend root
    return f"uploads/{safe_name}"


async def process_resume_upload(
    *,
    db: AsyncSession,
    filename: str,
    file_bytes: bytes,
) -> Resume:
    """
    Full resume audit pipeline. Returns the persisted Resume ORM object.

    Raises:
        ExtractionError: If the file cannot be parsed.
        AIServiceError subclasses: If Gemini calls fail.
    """
    ai = GeminiService(db_session=db)

    # ── Step 1: Save file ─────────────────────────────────────────────────────
    file_url = _save_file(filename, file_bytes)
    logger.info("Saved resume file: %s", file_url)

    # ── Step 2: Extract raw text ──────────────────────────────────────────────
    logger.info("Extracting text from %s ...", filename)
    raw_text = extract_text(filename, file_bytes)
    logger.info("Extracted %d characters from resume", len(raw_text))

    # ── Step 3: Gemini — Single-pass parse & audit ─────────────────────────────
    logger.info("Calling Gemini for single-pass resume parsing & audit ...")
    prompt = resume_parse_and_audit_prompt(raw_text)
    response_json: dict = await ai.generate_structured_json(
        prompt,
        feature_name="resume_parse_and_audit",
    )

    parsed_json = response_json.get("parsed", {})
    audit_json = response_json.get("audit", {})
    audit_score = float(audit_json.get("overall_score", 0))

    logger.info(
        "Resume audit complete — score: %.1f | skills: %d | exp: %d | level: %s",
        audit_score,
        len(parsed_json.get("skills", [])),
        len(parsed_json.get("experience", [])),
        audit_json.get("industry_level"),
    )

    # ── Step 5: Get the single candidate profile (single-user app) ───────────
    result = await db.execute(select(CandidateProfile).limit(1))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise RuntimeError(
            "No candidate_profile found. Please run: python scripts/seed_db.py"
        )

    # ── Step 6: Persist to DB ─────────────────────────────────────────────────
    resume = Resume(
        candidate_id=candidate.id,
        file_url=file_url,
        raw_extracted_text=raw_text,
        parsed_json=parsed_json,
        audit_score=audit_score,
        audit_feedback_json=audit_json,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    logger.info("Resume saved to DB — id=%d", resume.id)

    return resume


async def get_resume_by_id(
    *,
    db: AsyncSession,
    resume_id: int,
) -> Resume | None:
    """Fetch a resume by primary key. Returns None if not found."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    return result.scalar_one_or_none()


async def get_all_resumes(*, db: AsyncSession) -> list[Resume]:
    """Return all resumes ordered by most recent first."""
    result = await db.execute(
        select(Resume).order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())
