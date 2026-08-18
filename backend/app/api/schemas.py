"""
PrepAI — Resume API Schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    id: int
    candidate_id: int
    file_url: str | None = None
    audit_score: float | None = None
    parsed_json: dict[str, Any] | None = None
    audit_feedback_json: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResumeDetailResponse(BaseModel):
    id: int
    candidate_id: int
    file_url: str | None = None
    raw_extracted_text: str | None = None
    parsed_json: dict[str, Any] | None = None
    audit_score: float | None = None
    audit_feedback_json: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResumeListItem(BaseModel):
    id: int
    file_url: str | None = None
    audit_score: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Prep API Schemas ──────────────────────────────────────────────────────────

class GeneratePrepQuestionsRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=100, example="Senior Backend Engineer")
    topic: str | None = Field(None, max_length=100, example="System Design")
    difficulty: str = Field("medium", example="medium")
    count: int = Field(5, ge=1, le=10)


class PrepQuestionResponse(BaseModel):
    id: int
    candidate_id: int
    role: str
    topic: str
    difficulty: str
    question_text: str
    model_answer_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class PrepFiltersResponse(BaseModel):
    roles: list[str]
    topics: list[str]


# ── Interview API Schemas ─────────────────────────────────────────────────────

class CreateInterviewRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=100, example="Senior Backend Engineer")
    interview_type: str = Field("Technical", example="Technical")  # Technical, HR, Behavioral, System Design
    difficulty_mode: str = Field("Medium", example="Adaptive")     # Easy, Medium, Hard, Adaptive
    duration_minutes: int | None = Field(30, ge=5, le=180, example=30)
    question_count: int = Field(5, ge=1, le=15, example=5)
    resume_id: int | None = Field(None, ge=1, example=1)
    job_description_id: int | None = Field(None, ge=1, example=1)


class InterviewResponse(BaseModel):
    id: int
    candidate_id: int
    role: str
    interview_type: str
    difficulty_mode: str
    duration_minutes: int | None = 30
    question_count: int = 5
    status: str = "not_started"
    resume_id: int | None = None
    job_description_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Job Description Schemas ───────────────────────────────────────────────────

class JobDescriptionCreateRequest(BaseModel):
    raw_text: str = Field(..., min_length=10, max_length=30000, description="Full job description text to parse")


class JobDescriptionResponse(BaseModel):
    id: int
    candidate_id: int
    raw_text: str
    parsed_required_skills_json: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Live Session Question & Answer Schemas ─────────────────────────────────────

class InterviewQuestionResponse(BaseModel):
    id: int
    interview_id: int
    order_index: int
    question_text: str
    difficulty: str
    category: str
    time_limit_seconds: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubmitAnswerRequest(BaseModel):
    question_id: int = Field(..., ge=1)
    answer_text: str = Field(..., min_length=1, max_length=10000, description="Candidate's spoken or typed answer text")



class SubmitAnswerResponse(BaseModel):
    id: int
    question_id: int
    answer_text: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Report & Progress Schemas ─────────────────────────────────────────────────

class InterviewQuestionDetail(BaseModel):
    question_id: int
    order_index: int
    category: str
    difficulty: str
    question_text: str
    answer_text: str | None = None
    technical_score: float = 0.0
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    clarity_score: float = 0.0
    overall_score: float = 0.0
    feedback_text: str = ""


class InterviewReportResponse(BaseModel):
    interview_id: int
    candidate_id: int = 1
    role: str
    interview_type: str
    difficulty_mode: str
    status: str = "completed"
    completed_at: str | None = None
    overall_score: float = 0.0
    avg_technical_score: float = 0.0
    avg_relevance_score: float = 0.0
    avg_completeness_score: float = 0.0
    avg_clarity_score: float = 0.0
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: str = ""
    executive_summary: str | None = None
    questions: list[InterviewQuestionDetail] = []

    class Config:
        from_attributes = True


class CandidateProgressRecord(BaseModel):
    interview_id: int
    role: str
    interview_type: str
    difficulty_mode: str
    overall_score: float
    avg_technical_score: float
    completed_at: str
