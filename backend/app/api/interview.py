"""
PrepAI — Interview Setup & Job Description API Endpoints.

Supports creating interview configurations, parsing & storing job descriptions,
and fetching stored sessions.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    CreateInterviewRequest,
    InterviewResponse,
    JobDescriptionCreateRequest,
    JobDescriptionResponse,
)
from app.core.database import get_db
from app.services.ai.gemini_service import GeminiService, get_gemini_service
from app.services.interview.interview_service import (
    create_interview,
    create_job_description,
    get_interview_by_id,
    get_job_descriptions,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interview Setup"])


# ── 1. Create Interview Endpoint ──────────────────────────────────────────────

@router.post(
    "/interview/create",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/v1/interview/create",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def api_create_interview(
    req: CreateInterviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new mock interview session configuration.
    Stores exact role, type, difficulty, duration, question count, and attached resume/JD.
    Does NOT generate questions yet — session status is 'not_started'.
    """
    try:
        interview = await create_interview(
            db=db,
            role=req.role,
            interview_type=req.interview_type,
            difficulty_mode=req.difficulty_mode,
            duration_minutes=req.duration_minutes,
            question_count=req.question_count,
            resume_id=req.resume_id,
            job_description_id=req.job_description_id,
        )

        return InterviewResponse(
            id=interview.id,
            candidate_id=interview.candidate_id,
            role=interview.role,
            interview_type=interview.interview_type.value,
            difficulty_mode=interview.difficulty_mode.value,
            duration_minutes=interview.duration_minutes,
            question_count=req.question_count,
            status="not_started",
            resume_id=interview.resume_id,
            job_description_id=interview.job_description_id,
            created_at=interview.created_at,
        )

    except Exception as exc:
        logger.exception("Failed to create interview configuration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interview session: {str(exc)}",
        ) from exc


# ── 2. Get Interview Details Endpoint ─────────────────────────────────────────

@router.get("/interview/{interview_id}", response_model=InterviewResponse)
@router.get("/v1/interview/{interview_id}", response_model=InterviewResponse, include_in_schema=False)
async def api_get_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch an existing interview session configuration by ID."""
    interview = await get_interview_by_id(db=db, interview_id=interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session with ID {interview_id} not found.",
        )

    return InterviewResponse(
        id=interview.id,
        candidate_id=interview.candidate_id,
        role=interview.role,
        interview_type=interview.interview_type.value,
        difficulty_mode=interview.difficulty_mode.value,
        duration_minutes=interview.duration_minutes,
        question_count=5,
        status="not_started" if interview.status.value == "scheduled" else interview.status.value,
        resume_id=interview.resume_id,
        job_description_id=interview.job_description_id,
        created_at=interview.created_at,
    )


# ── 3. Job Description Upload / Parsing Endpoints ──────────────────────────────

@router.post(
    "/job-description",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/v1/job-description",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def api_create_job_description(
    req: JobDescriptionCreateRequest,
    db: AsyncSession = Depends(get_db),
    ai: GeminiService = Depends(lambda db=Depends(get_db): get_gemini_service(db=db)),
):
    """
    Accept pasted job description text, extract required skills & responsibilities
    using Gemini AI, and persist it to PostgreSQL for interview setup.
    """
    try:
        jd = await create_job_description(
            db=db,
            raw_text=req.raw_text,
            candidate_id=1,
            ai_service=ai,
        )
        return jd
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Failed to parse and store job description: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process job description: {str(exc)}",
        ) from exc


@router.get("/job-descriptions", response_model=List[JobDescriptionResponse])
@router.get("/v1/job-descriptions", response_model=List[JobDescriptionResponse], include_in_schema=False)
async def api_list_job_descriptions(db: AsyncSession = Depends(get_db)):
    """Fetch list of all saved job descriptions."""
    jds = await get_job_descriptions(db=db, candidate_id=1)
    return jds


# ── 4. Live Session Next Question (LangGraph Engine) ──────────────────────────

from app.api.schemas import (
    InterviewQuestionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services.interview.adaptive_graph import (
    generate_next_interview_question,
    save_interview_answer,
)


@router.post(
    "/interview/{interview_id}/next-question",
    response_model=InterviewQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/v1/interview/{interview_id}/next-question",
    response_model=InterviewQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def api_next_question(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    ai: GeminiService = Depends(lambda db=Depends(get_db): get_gemini_service(db=db)),
):
    """
    Generate the next single interview question dynamically using the LangGraph adaptive engine.
    Incorporate candidate resume context, JD skills, and prior evaluation scores.
    """
    try:
        q = await generate_next_interview_question(
            db=db,
            interview_id=interview_id,
            ai_service=ai,
        )
        return InterviewQuestionResponse(
            id=q.id,
            interview_id=q.interview_id,
            order_index=q.order_index,
            question_text=q.question_text,
            difficulty=q.difficulty.value,
            category=q.category.value,
            time_limit_seconds=q.time_limit_seconds,
            created_at=q.created_at,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Failed to generate next question: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate question: {str(exc)}",
        ) from exc


from app.services.interview.evaluator import evaluate_and_save_answer


@router.post(
    "/interview/{interview_id}/answer",
    response_model=SubmitAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/v1/interview/{interview_id}/answer",
    response_model=SubmitAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def api_submit_answer(
    interview_id: int,
    req: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    ai: GeminiService = Depends(lambda db=Depends(get_db): get_gemini_service(db=db)),
):
    """
    Store candidate answer text and evaluate performance across 4 scoring dimensions with Gemini AI.
    """
    try:
        ans = await evaluate_and_save_answer(
            db=db,
            interview_id=interview_id,
            question_id=req.question_id,
            answer_text=req.answer_text,
            ai_service=ai,
        )
        return SubmitAnswerResponse(
            id=ans.id,
            question_id=ans.question_id,
            answer_text=ans.answer_text,
            created_at=ans.created_at,
        )
    except Exception as exc:
        logger.exception("Failed to store and evaluate answer: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process answer: {str(exc)}",
        ) from exc


# ── 6. Complete Interview & Generate Report Endpoint ──────────────────────────

from app.api.schemas import (
    CandidateProgressRecord,
    InterviewReportResponse,
)
from app.services.interview.report_service import (
    complete_interview_session,
    get_candidate_progress_history,
    get_interview_report,
)


@router.post(
    "/interview/{interview_id}/complete",
    response_model=InterviewReportResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/v1/interview/{interview_id}/complete",
    response_model=InterviewReportResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def api_complete_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    ai: GeminiService = Depends(lambda db=Depends(get_db): get_gemini_service(db=db)),
):
    """
    Finalize an interview session: compute mathematical aggregate sub-metrics,
    generate post-interview strengths, weaknesses, and study roadmap via Gemini AI,
    and persist report to PostgreSQL.
    """
    try:
        rep = await complete_interview_session(
            db=db,
            interview_id=interview_id,
            ai_service=ai,
        )
        return rep
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Failed to complete interview session: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(exc)}",
        ) from exc


# ── 7. Get Interview Performance Report Endpoint ──────────────────────────────

@router.get(
    "/interview/{interview_id}/report",
    response_model=InterviewReportResponse,
)
@router.get(
    "/v1/interview/{interview_id}/report",
    response_model=InterviewReportResponse,
    include_in_schema=False,
)
async def api_get_report(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch full post-interview performance report including computed aggregate scores,
    personalized study recommendation, strengths, weaknesses, and full Q&A breakdown.
    """
    try:
        rep = await get_interview_report(db=db, interview_id=interview_id)
        return rep
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Failed to fetch interview report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(exc)}",
        ) from exc


# ── 8. Candidate Progress History Endpoint ───────────────────────────────────

@router.get(
    "/candidate/progress",
    response_model=List[CandidateProgressRecord],
)
@router.get(
    "/v1/candidate/progress",
    response_model=List[CandidateProgressRecord],
    include_in_schema=False,
)
async def api_get_candidate_progress(
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch candidate's historical performance scores across all completed interviews
    ordered by date for progression analytics.
    """
    try:
        history = await get_candidate_progress_history(db=db, candidate_id=1)
        return history
    except Exception as exc:
        logger.exception("Failed to fetch candidate progress: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch progress history: {str(exc)}",
        ) from exc
