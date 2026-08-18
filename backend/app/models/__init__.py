"""
PrepAI — SQLAlchemy ORM Models.

All 8 production-quality tables for the PrepAI platform.
Every model inherits from Base (defined in app.core.database).
No auth / users table — single-user local app with candidate_profile as root.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class InterviewType(PyEnum):
    TECHNICAL    = "technical"
    BEHAVIORAL   = "behavioral"
    MIXED        = "mixed"
    SYSTEM_DESIGN = "system_design"
    HR           = "hr"


class DifficultyMode(PyEnum):
    EASY    = "easy"
    MEDIUM  = "medium"
    HARD    = "hard"
    ADAPTIVE = "adaptive"   # AI adjusts difficulty in real time


class InterviewStatus(PyEnum):
    SCHEDULED  = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED  = "completed"
    ABANDONED  = "abandoned"


class QuestionDifficulty(PyEnum):
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"


class QuestionCategory(PyEnum):
    DATA_STRUCTURES   = "data_structures"
    ALGORITHMS        = "algorithms"
    SYSTEM_DESIGN     = "system_design"
    BEHAVIORAL        = "behavioral"
    DATABASES         = "databases"
    NETWORKING        = "networking"
    OPERATING_SYSTEMS = "operating_systems"
    LANGUAGE_SPECIFIC = "language_specific"
    DOMAIN_KNOWLEDGE  = "domain_knowledge"
    PROBLEM_SOLVING   = "problem_solving"


# ─── 1. Candidate Profile ─────────────────────────────────────────────────────

class CandidateProfile(Base):
    """
    Single-user identity record.
    No auth fields — this is a local, single-user application.
    """
    __tablename__ = "candidate_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    resumes:          Mapped[list[Resume]]          = relationship("Resume",          back_populates="candidate", cascade="all, delete-orphan")
    job_descriptions: Mapped[list[JobDescription]]  = relationship("JobDescription",  back_populates="candidate", cascade="all, delete-orphan")
    prep_questions:   Mapped[list[PrepQuestion]]    = relationship("PrepQuestion",    back_populates="candidate", cascade="all, delete-orphan")
    interviews:       Mapped[list[Interview]]       = relationship("Interview",       back_populates="candidate", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CandidateProfile id={self.id} name={self.name!r}>"


# ─── 2. Resumes ───────────────────────────────────────────────────────────────

class Resume(Base):
    """
    Uploaded resume with extracted text, structured parsed JSON,
    and AI-generated audit score + feedback.
    """
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Storage
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="URL or local path to the uploaded resume file")

    # Raw content from PDF/DOCX extraction
    raw_extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Full plain-text extracted from the resume file")

    # Structured parse result from AI
    # Expected keys: skills, projects, experience, education, certifications, summary
    parsed_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="AI-parsed structured resume data: {skills, projects, experience, education, certifications, summary}"
    )

    # AI audit results
    audit_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Overall resume quality score: 0.0–100.0"
    )
    audit_feedback_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Structured AI feedback: {strengths, weaknesses, section_scores, improvement_suggestions}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate:  Mapped[CandidateProfile] = relationship("CandidateProfile", back_populates="resumes")
    interviews: Mapped[list[Interview]]  = relationship("Interview", back_populates="resume")

    __table_args__ = (
        Index("ix_resumes_candidate_id", "candidate_id"),
        Index("ix_resumes_created_at",   "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} candidate_id={self.candidate_id} score={self.audit_score}>"


# ─── 3. Job Descriptions ──────────────────────────────────────────────────────

class JobDescription(Base):
    """
    Raw job description text and AI-parsed required skills/qualifications.
    Used to tailor interview questions and prep content.
    """
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False, index=True
    )

    raw_text: Mapped[str] = mapped_column(Text, nullable=False, comment="Full pasted or extracted job description text")

    # AI-parsed breakdown
    # Expected keys: required_skills, preferred_skills, responsibilities, qualifications, role_title, company
    parsed_required_skills_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="AI-parsed JD data: {required_skills, preferred_skills, responsibilities, qualifications, role_title}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate:   Mapped[CandidateProfile] = relationship("CandidateProfile", back_populates="job_descriptions")
    interviews:  Mapped[list[Interview]]  = relationship("Interview", back_populates="job_description")

    __table_args__ = (
        Index("ix_job_descriptions_candidate_id", "candidate_id"),
        Index("ix_job_descriptions_created_at",   "created_at"),
    )

    def __repr__(self) -> str:
        return f"<JobDescription id={self.id} candidate_id={self.candidate_id}>"


# ─── 4. Prep Questions ────────────────────────────────────────────────────────

class PrepQuestion(Base):
    """
    AI-generated study questions with model answers.
    Used in the Prepare section — independent of interview sessions.
    """
    __tablename__ = "prep_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(String(255), nullable=False, comment="Target job role, e.g. 'Senior Backend Engineer'")
    topic: Mapped[str] = mapped_column(String(255), nullable=False, comment="Specific topic, e.g. 'System Design', 'Python Async'")
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        Enum(QuestionDifficulty, name="question_difficulty_enum"), nullable=False
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_answer_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Ideal/model answer generated by AI for self-study"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped[CandidateProfile] = relationship("CandidateProfile", back_populates="prep_questions")

    __table_args__ = (
        Index("ix_prep_questions_candidate_id", "candidate_id"),
        Index("ix_prep_questions_role_topic",   "role", "topic"),
        Index("ix_prep_questions_difficulty",   "difficulty"),
    )

    def __repr__(self) -> str:
        return f"<PrepQuestion id={self.id} role={self.role!r} topic={self.topic!r} difficulty={self.difficulty}>"


# ─── 5. Interviews ────────────────────────────────────────────────────────────

class Interview(Base):
    """
    An interview session — links candidate, optional resume, optional JD.
    Tracks status, scoring, and timing for a full mock interview run.
    """
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_description_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    role: Mapped[str] = mapped_column(String(255), nullable=False, comment="Target role for this interview session")
    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(InterviewType, name="interview_type_enum"), nullable=False
    )
    difficulty_mode: Mapped[DifficultyMode] = mapped_column(
        Enum(DifficultyMode, name="difficulty_mode_enum"), nullable=False, default=DifficultyMode.MEDIUM
    )
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Intended session duration in minutes; null = untimed"
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status_enum"),
        nullable=False,
        default=InterviewStatus.SCHEDULED,
    )
    overall_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Computed aggregate score: 0.0–100.0; null until completed"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when session reached COMPLETED status"
    )

    # Relationships
    candidate:       Mapped[CandidateProfile]           = relationship("CandidateProfile", back_populates="interviews")
    resume:          Mapped[Resume | None]              = relationship("Resume",          back_populates="interviews")
    job_description: Mapped[JobDescription | None]      = relationship("JobDescription",  back_populates="interviews")
    questions:       Mapped[list[InterviewQuestion]]    = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan", order_by="InterviewQuestion.order_index")
    report:          Mapped[InterviewReport | None]     = relationship("InterviewReport",  back_populates="interview",  uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_interviews_candidate_id",  "candidate_id"),
        Index("ix_interviews_status",        "status"),
        Index("ix_interviews_created_at",    "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Interview id={self.id} role={self.role!r} status={self.status} score={self.overall_score}>"


# ─── 6. Interview Questions ───────────────────────────────────────────────────

class InterviewQuestion(Base):
    """
    Individual questions within an interview session.
    Ordered by order_index; hard questions may have a time limit enforced by the UI.
    """
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        Enum(QuestionDifficulty, name="question_difficulty_enum"),
        nullable=False,
    )
    category: Mapped[QuestionCategory] = mapped_column(
        Enum(QuestionCategory, name="question_category_enum"),
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="1-based position of this question within the session"
    )
    time_limit_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Per-question time cap in seconds; null = no limit (only set for HARD questions)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    interview: Mapped[Interview]               = relationship("Interview", back_populates="questions")
    answer:    Mapped[InterviewAnswer | None]  = relationship("InterviewAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_interview_questions_interview_id", "interview_id"),
        Index("ix_interview_questions_order",        "interview_id", "order_index"),
    )

    def __repr__(self) -> str:
        return f"<InterviewQuestion id={self.id} interview_id={self.interview_id} order={self.order_index} difficulty={self.difficulty}>"


# ─── 7. Interview Answers ─────────────────────────────────────────────────────

class InterviewAnswer(Base):
    """
    Candidate's spoken/typed answer to a single interview question.
    AI evaluates on 4 dimensions; all scores are 0.0–10.0.
    """
    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,      # one answer per question
        index=True,
    )

    answer_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw answer text or transcribed speech-to-text output"
    )

    # AI scoring dimensions (0.0 – 10.0)
    technical_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Correctness of technical content (0–10)"
    )
    relevance_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="How directly the answer addresses the question (0–10)"
    )
    completeness_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Coverage and depth of the answer (0–10)"
    )
    clarity_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Communication clarity and structure (0–10)"
    )
    overall_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Weighted aggregate of all four dimensions (0–10)"
    )

    feedback_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI-generated qualitative feedback for this specific answer"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    question: Mapped[InterviewQuestion] = relationship("InterviewQuestion", back_populates="answer")

    __table_args__ = (
        Index("ix_interview_answers_question_id", "question_id"),
    )

    def __repr__(self) -> str:
        return f"<InterviewAnswer id={self.id} question_id={self.question_id} overall={self.overall_score}>"


# ─── 8. Interview Reports ─────────────────────────────────────────────────────

class InterviewReport(Base):
    """
    Post-session AI-generated report summarising the entire interview.
    One report per completed interview session.
    """
    __tablename__ = "interview_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,    # one report per interview
        index=True,
    )

    # AI-generated structured insights
    strengths_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="List of identified candidate strengths with evidence: [{point, evidence}]"
    )
    weaknesses_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="List of identified gaps and improvement areas: [{point, suggestion}]"
    )
    recommendations_text: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Free-form AI narrative: concrete next steps for the candidate to improve"
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    interview: Mapped[Interview] = relationship("Interview", back_populates="report")

    __table_args__ = (
        Index("ix_interview_reports_interview_id", "interview_id"),
    )

    def __repr__(self) -> str:
        return f"<InterviewReport id={self.id} interview_id={self.interview_id}>"


# ─── 9. AI Call Logs ──────────────────────────────────────────────────────────

class AICallLog(Base):
    """
    Audit log for every Gemini API call made by GeminiService.
    Used for debugging, latency tracking, and error analysis.
    Never stores full prompt/response text — only excerpts for privacy/size reasons.
    """
    __tablename__ = "ai_call_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    feature_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Feature that triggered this AI call, e.g. 'resume_audit'"
    )
    prompt_excerpt: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="First 500 chars of the prompt (for debugging)"
    )
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="True if Gemini returned a usable response"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Round-trip latency from request to parsed response in milliseconds"
    )
    error_msg: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="Error message if success=False; null otherwise"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_ai_call_logs_feature_name", "feature_name"),
        Index("ix_ai_call_logs_created_at",   "created_at"),
        Index("ix_ai_call_logs_success",       "success"),
    )

    def __repr__(self) -> str:
        return f"<AICallLog id={self.id} feature={self.feature_name!r} success={self.success} latency={self.latency_ms}ms>"
