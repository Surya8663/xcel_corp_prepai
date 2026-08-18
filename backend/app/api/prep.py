"""
PrepAI — Prep / Study Mode API Endpoints.

Handles generating interview practice questions with model answers,
storing them in PostgreSQL, and retrieving/filtering questions.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    GeneratePrepQuestionsRequest,
    PrepFiltersResponse,
    PrepQuestionResponse,
)
from app.core.database import get_db
from app.services.ai.gemini_service import AIServiceError
from app.services.prep.prep_service import (
    generate_prep_questions,
    get_prep_filters,
    get_prep_questions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prep", tags=["Prep Questions"])


@router.post(
    "/generate",
    response_model=List[PrepQuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_questions_endpoint(
    req: GeneratePrepQuestionsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new batch of study questions with model answers via Gemini AI
    and store them in PostgreSQL.
    """
    try:
        from app.core.rate_limiter import ai_rate_limiter
        await ai_rate_limiter.check("prep_generate")

        questions = await generate_prep_questions(
            db=db,
            role=req.role,
            topic=req.topic,
            difficulty=req.difficulty,
            count=req.count,
        )
        return questions
    except AIServiceError as exc:
        logger.error("Gemini AI failed during prep question generation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.user_message or "AI Service error while generating questions.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error generating prep questions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate prep questions: {str(exc)}",
        ) from exc


@router.get("/questions", response_model=List[PrepQuestionResponse])
async def list_prep_questions_endpoint(
    role: Optional[str] = Query(None, description="Filter by role"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: easy, medium, hard"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Fetch stored prep questions from PostgreSQL with optional filtering."""
    questions = await get_prep_questions(
        db=db,
        role=role,
        topic=topic,
        difficulty=difficulty,
        limit=limit,
        offset=offset,
    )
    return questions


@router.get("/filters", response_model=PrepFiltersResponse)
async def get_filters_endpoint(db: AsyncSession = Depends(get_db)):
    """Fetch distinct roles and topics available in stored prep questions."""
    return await get_prep_filters(db=db)
