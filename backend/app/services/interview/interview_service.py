"""
PrepAI — Interview & Job Description Services.

Handles interview setup configuration, job description parsing with Gemini,
and DB persistence.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DifficultyMode,
    Interview,
    InterviewQuestion,
    InterviewStatus,
    InterviewType,
    JobDescription,
)
from app.services.ai.gemini_service import GeminiService
from app.services.ai.prompt_templates import jd_skill_extraction_prompt

logger = logging.getLogger(__name__)


async def create_job_description(
    db: AsyncSession,
    raw_text: str,
    candidate_id: int = 1,
    ai_service: GeminiService | None = None,
) -> JobDescription:
    """
    Parse a raw job description text using GeminiService to extract required skills,
    preferred skills, responsibilities, and role title, then save to PostgreSQL.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError("Job description text cannot be empty.")

    parsed_skills: dict[str, Any] = {}

    # Call Gemini to parse JD if AI service is provided
    if ai_service:
        try:
            prompt = jd_skill_extraction_prompt(raw_text)
            parsed_skills = await ai_service.generate_structured_json(
                prompt=prompt,
                feature_name="jd_skill_extraction",
                temperature=0.2,
            )
            logger.info(
                "[JD] Extracted %d skills from JD text for role '%s'",
                len(parsed_skills.get("required_skills", [])),
                parsed_skills.get("role_title", "Unknown"),
            )
        except Exception as exc:
            logger.warning("[JD] Gemini skill extraction failed: %s. Saving raw JD.", exc)
            parsed_skills = {
                "role_title": "Software Engineer",
                "required_skills": [],
                "summary": "Extracted raw job description",
            }
    else:
        parsed_skills = {
            "role_title": "Software Engineer",
            "required_skills": [],
            "summary": "Extracted raw job description",
        }

    jd = JobDescription(
        candidate_id=candidate_id,
        raw_text=raw_text,
        parsed_required_skills_json=parsed_skills,
    )
    db.add(jd)
    await db.commit()
    await db.refresh(jd)
    return jd


async def get_job_descriptions(
    db: AsyncSession,
    candidate_id: int = 1,
) -> list[JobDescription]:
    """Fetch all saved job descriptions for a candidate."""
    stmt = (
        select(JobDescription)
        .where(JobDescription.candidate_id == candidate_id)
        .order_by(JobDescription.created_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_job_description_by_id(
    db: AsyncSession,
    jd_id: int,
) -> JobDescription | None:
    """Fetch a specific job description by ID."""
    stmt = select(JobDescription).where(JobDescription.id == jd_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def create_interview(
    db: AsyncSession,
    role: str,
    interview_type: str,
    difficulty_mode: str,
    duration_minutes: int | None = 30,
    question_count: int = 5,
    resume_id: int | None = None,
    job_description_id: int | None = None,
    candidate_id: int = 1,
) -> Interview:
    """
    Create a new mock interview session configuration.
    Sets status="SCHEDULED" (representing not_started).
    No questions generated yet.
    """
    # Normalize interview_type string to enum
    type_str = interview_type.lower().replace(" ", "_")
    type_map = {
        "technical": InterviewType.TECHNICAL,
        "hr": InterviewType.HR,
        "behavioral": InterviewType.BEHAVIORAL,
        "mixed": InterviewType.MIXED,
        "system_design": InterviewType.SYSTEM_DESIGN,
    }
    i_type = type_map.get(type_str, InterviewType.TECHNICAL)

    # Normalize difficulty_mode string to enum
    diff_str = difficulty_mode.lower()
    diff_map = {
        "easy": DifficultyMode.EASY,
        "medium": DifficultyMode.MEDIUM,
        "hard": DifficultyMode.HARD,
        "adaptive": DifficultyMode.ADAPTIVE,
    }
    d_mode = diff_map.get(diff_str, DifficultyMode.MEDIUM)

    interview = Interview(
        candidate_id=candidate_id,
        role=role.strip(),
        interview_type=i_type,
        difficulty_mode=d_mode,
        duration_minutes=duration_minutes,
        status=InterviewStatus.SCHEDULED,
        resume_id=resume_id,
        job_description_id=job_description_id,
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)

    logger.info(
        "[INTERVIEW] Created interview session ID=%d for role='%s' type='%s' difficulty='%s'",
        interview.id, interview.role, interview.interview_type.value, interview.difficulty_mode.value,
    )
    return interview


async def get_interview_by_id(
    db: AsyncSession,
    interview_id: int,
) -> Interview | None:
    """Fetch an interview session by ID."""
    stmt = select(Interview).where(Interview.id == interview_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def get_all_interviews_for_candidate(
    db: AsyncSession,
    candidate_id: int = 1,
) -> list[dict[str, Any]]:
    """
    Fetch all interview sessions for candidate #1 ordered by created_at DESC.
    Returns session metadata, question counts, and average overall score if completed/answered.
    """
    stmt = (
        select(Interview)
        .options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer),
            selectinload(Interview.report),
        )
        .where(Interview.candidate_id == candidate_id)
        .order_by(Interview.created_at.desc())
    )

    res = await db.execute(stmt)
    interviews = res.scalars().all()

    results: list[dict[str, Any]] = []
    for item in interviews:
        overall_scores: list[float] = []
        for q in item.questions:
            if q.answer and q.answer.overall_score is not None:
                overall_scores.append(q.answer.overall_score)

        avg_ovr = round(float(sum(overall_scores) / len(overall_scores)), 1) if overall_scores else None

        results.append({
            "id": item.id,
            "candidate_id": item.candidate_id,
            "role": item.role,
            "interview_type": item.interview_type.value,
            "difficulty_mode": item.difficulty_mode.value,
            "duration_minutes": item.duration_minutes,
            "question_count": len(item.questions) or 5,
            "status": item.status.value,
            "created_at": item.created_at,
            "completed_at": item.completed_at,
            "overall_score": avg_ovr,
        })

    return results

