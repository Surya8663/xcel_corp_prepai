"""
PrepAI — Resume API Endpoints.

Handles resume file uploads, parsing, auditing, and retrieval.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ResumeDetailResponse, ResumeListItem, ResumeUploadResponse
from app.core.database import get_db
from app.services.ai.gemini_service import AIServiceError
from app.services.resume.extractor import ExtractionError
from app.services.resume.resume_service import (
    get_all_resumes,
    get_resume_by_id,
    process_resume_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a resume file (PDF or DOCX), extract text, parse structured data with Gemini,
    generate a detailed Resume Audit score and feedback, and return the result.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    ext = file.filename.split(".")[-1].lower()
    if ext not in ("pdf", "docx", "doc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and DOCX documents are accepted.",
        )

    try:
        content = await file.read()
        if not content or len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file exceeds the maximum size limit of 10MB.",
            )

        from app.core.rate_limiter import ai_rate_limiter
        await ai_rate_limiter.check("resume_upload")

        resume = await process_resume_upload(
            db=db,
            filename=file.filename,
            file_bytes=content,
        )
        return resume


    except ExtractionError as exc:
        logger.warning("Resume text extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except AIServiceError as exc:
        logger.error("AI processing failed during resume upload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.user_message or "AI service error. Please try again.",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error uploading resume: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process resume: {str(exc)}",
        ) from exc


@router.get("/list", response_model=List[ResumeListItem])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    """Fetch list of all uploaded resumes."""
    resumes = await get_all_resumes(db=db)
    return resumes


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch details and audit analysis for a specific resume by ID."""
    resume = await get_resume_by_id(db=db, resume_id=resume_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID {resume_id} not found.",
        )
    return resume
