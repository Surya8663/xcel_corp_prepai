"""
PrepAI — Post-Interview Performance Report & Historical Progress Service.

Computes real aggregate metrics from PostgreSQL answer scores, invokes Gemini AI
for personalized strengths, weaknesses, and study recommendations, and manages candidate progress tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Interview, InterviewAnswer, InterviewQuestion, InterviewReport, InterviewStatus
from app.services.ai.gemini_service import GeminiService
from app.services.ai.prompt_templates import interview_report_summary_prompt

logger = logging.getLogger(__name__)


def _extract_list_items(val: Any) -> list[str]:
    """Robustly extract a clean list of non-empty strings from dicts, lists, or strings."""
    if not val:
        return []
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    if isinstance(val, dict):
        if "items" in val and isinstance(val["items"], list):
            return _extract_list_items(val["items"])
        if "points" in val and isinstance(val["points"], list):
            return _extract_list_items(val["points"])
        txt = val.get("point") or val.get("strength") or val.get("weakness") or val.get("text") or val.get("description") or val.get("title")
        if txt:
            return [str(txt).strip()]
        return [str(val)]
    if isinstance(val, list):
        res: list[str] = []
        for item in val:
            if isinstance(item, str) and item.strip():
                res.append(item.strip())
            elif isinstance(item, dict):
                txt = item.get("point") or item.get("strength") or item.get("weakness") or item.get("text") or item.get("description") or item.get("title")
                if txt:
                    res.append(str(txt).strip())
                else:
                    res.append(str(item))
            elif item:
                res.append(str(item).strip())
        return res
    return []


def _ensure_guaranteed_strengths_and_weaknesses(
    strengths: list[str],
    weaknesses: list[str],
    role: str,
    interview_type: str,
    avg_overall: float,
    avg_tech: float,
    avg_comp: float,
    avg_rel: float,
    avg_clar: float,
    q_count: int,
) -> tuple[list[str], list[str]]:
    """Guarantees that strengths and weaknesses are never empty for any interview report."""
    if not strengths:
        if avg_overall >= 7.0:
            strengths.append(f"Demonstrated strong technical proficiency and problem-solving readiness for {role} roles.")
        elif avg_tech >= 5.0:
            strengths.append("Provided correct core technical concepts and fundamental mechanics in answers.")
        else:
            strengths.append(f"Demonstrated solid commitment by answering all {q_count} question(s) in the session.")

        if avg_clar >= 6.0:
            strengths.append("Maintained clear communication structure and professional tone throughout responses.")
        else:
            strengths.append("Attempted technical problem solving under real-time interview conditions.")

    if not weaknesses:
        if avg_comp < 7.0:
            weaknesses.append("Incorporate deeper architectural mechanisms, edge-case analysis, and quantitative metrics in answers.")
        if avg_rel < 7.0:
            weaknesses.append("Directly address the core question prompt in the opening sentence before providing supplementary details.")
        if not weaknesses:
            weaknesses.append(f"Practice higher-difficulty {role} system design trade-offs and latency optimization scenarios.")

    return strengths, weaknesses


# ── Complete Session & Generate Report ─────────────────────────────────────────

async def complete_interview_session(
    db: AsyncSession,
    interview_id: int,
    ai_service: GeminiService,
) -> dict[str, Any]:
    """
    1. Loads interview session with all questions and answers.
    2. Computes exact mathematical averages from stored answer scores.
    3. Calls Gemini AI to generate personalized strengths, weaknesses, and study recommendations.
    4. Persists report to interview_reports table and marks interview status="completed".
    """
    stmt = (
        select(Interview)
        .options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer),
            selectinload(Interview.report),
        )
        .where(Interview.id == interview_id)
    )
    res = await db.execute(stmt)
    interview = res.scalar_one_or_none()

    if not interview:
        raise ValueError(f"Interview session #{interview_id} not found.")

    # Extract Q&A items and calculate real average scores
    qa_list: list[dict[str, Any]] = []
    tech_scores: list[float] = []
    rel_scores: list[float] = []
    comp_scores: list[float] = []
    clar_scores: list[float] = []
    overall_scores: list[float] = []

    for q in sorted(interview.questions, key=lambda x: x.order_index):
        ans_text = q.answer.answer_text if q.answer else None
        t_score = q.answer.technical_score if q.answer and q.answer.technical_score is not None else 0.0
        r_score = q.answer.relevance_score if q.answer and q.answer.relevance_score is not None else 0.0
        c_score = q.answer.completeness_score if q.answer and q.answer.completeness_score is not None else 0.0
        cl_score = q.answer.clarity_score if q.answer and q.answer.clarity_score is not None else 0.0
        o_score = q.answer.overall_score if q.answer and q.answer.overall_score is not None else 0.0
        fb_text = q.answer.feedback_text if q.answer and q.answer.feedback_text else "No evaluation available."

        if q.answer:
            tech_scores.append(t_score)
            rel_scores.append(r_score)
            comp_scores.append(c_score)
            clar_scores.append(cl_score)
            overall_scores.append(o_score)

        qa_list.append({
            "question_id": q.id,
            "order_index": q.order_index,
            "category": q.category.value,
            "difficulty": q.difficulty.value,
            "question_text": q.question_text,
            "answer_text": ans_text,
            "technical_score": t_score,
            "relevance_score": r_score,
            "completeness_score": c_score,
            "clarity_score": cl_score,
            "overall_score": o_score,
            "feedback_text": fb_text,
        })

    def _avg(lst: list[float]) -> float:
        return round(float(sum(lst) / len(lst)), 1) if lst else 0.0

    avg_tech = _avg(tech_scores)
    avg_rel = _avg(rel_scores)
    avg_comp = _avg(comp_scores)
    avg_clar = _avg(clar_scores)
    avg_overall = _avg(overall_scores)

    avg_scores_dict = {
        "technical": avg_tech,
        "relevance": avg_rel,
        "completeness": avg_comp,
        "clarity": avg_clar,
        "overall": avg_overall,
    }

    # Call Gemini AI for Summary, Strengths, Weaknesses, and Recommendation
    prompt = interview_report_summary_prompt(
        role=interview.role,
        interview_type=interview.interview_type.value,
        difficulty_mode=interview.difficulty_mode.value,
        qa_summary_list=qa_list,
        avg_scores=avg_scores_dict,
    )

    try:
        summary_json = await ai_service.generate_structured_json(
            prompt=prompt,
            feature_name="interview_report_summary",
            temperature=0.3,
        )
        
        raw_strengths = summary_json.get("strengths") or summary_json.get("key_strengths") or summary_json.get("strengths_list") or summary_json.get("highlights")
        raw_weaknesses = summary_json.get("weaknesses") or summary_json.get("areas_for_growth") or summary_json.get("gaps") or summary_json.get("improvements")
        
        strengths = _extract_list_items(raw_strengths)
        weaknesses = _extract_list_items(raw_weaknesses)
        recommendations = str(summary_json.get("recommendations", "")).strip()
        exec_summary = str(summary_json.get("executive_summary", "")).strip()
    except Exception as exc:
        logger.error("[REPORT] Gemini summary generation failed: %s", exc)
        strengths, weaknesses = [], []
        recommendations = f"Focus on reviewing key concepts and technical architecture for {interview.role} interviews."
        exec_summary = f"Performance evaluation completed for {interview.role} ({interview.interview_type.value} format)."

    # Enforce non-empty fallback guarantees
    strengths, weaknesses = _ensure_guaranteed_strengths_and_weaknesses(
        strengths=strengths,
        weaknesses=weaknesses,
        role=interview.role,
        interview_type=interview.interview_type.value,
        avg_overall=avg_overall,
        avg_tech=avg_tech,
        avg_comp=avg_comp,
        avg_rel=avg_rel,
        avg_clar=avg_clar,
        q_count=len(qa_list),
    )

    # Persist Report to DB
    existing_report = interview.report
    if existing_report:
        existing_report.strengths_json = {"items": strengths}
        existing_report.weaknesses_json = {"items": weaknesses}
        existing_report.recommendations_text = recommendations
    else:
        new_report = InterviewReport(
            interview_id=interview.id,
            strengths_json={"items": strengths},
            weaknesses_json={"items": weaknesses},
            recommendations_text=recommendations,
        )
        db.add(new_report)

    # Mark Interview as Completed
    interview.status = InterviewStatus.COMPLETED
    interview.completed_at = func.now()

    await db.commit()

    logger.info(
        "[REPORT] Completed session #%d (overall=%.1f/10) with %d strengths, %d weaknesses.",
        interview.id, avg_overall, len(strengths), len(weaknesses),
    )

    return {
        "interview_id": interview.id,
        "role": interview.role,
        "interview_type": interview.interview_type.value,
        "difficulty_mode": interview.difficulty_mode.value,
        "status": "completed",
        "overall_score": avg_overall,
        "avg_technical_score": avg_tech,
        "avg_relevance_score": avg_rel,
        "avg_completeness_score": avg_comp,
        "avg_clarity_score": avg_clar,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "executive_summary": exec_summary,
        "questions": qa_list,
    }


# ── Fetch Full Report Details ─────────────────────────────────────────────────

async def get_interview_report(
    db: AsyncSession,
    interview_id: int,
) -> dict[str, Any]:
    """
    Fetch full post-interview performance report and Q&A breakdown.
    """
    stmt = (
        select(Interview)
        .options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer),
            selectinload(Interview.report),
        )
        .where(Interview.id == interview_id)
    )
    res = await db.execute(stmt)
    interview = res.scalar_one_or_none()

    if not interview:
        raise ValueError(f"Interview session #{interview_id} not found.")

    qa_list: list[dict[str, Any]] = []
    tech_scores: list[float] = []
    rel_scores: list[float] = []
    comp_scores: list[float] = []
    clar_scores: list[float] = []
    overall_scores: list[float] = []

    for q in sorted(interview.questions, key=lambda x: x.order_index):
        ans_text = q.answer.answer_text if q.answer else None
        t_score = q.answer.technical_score if q.answer and q.answer.technical_score is not None else 0.0
        r_score = q.answer.relevance_score if q.answer and q.answer.relevance_score is not None else 0.0
        c_score = q.answer.completeness_score if q.answer and q.answer.completeness_score is not None else 0.0
        cl_score = q.answer.clarity_score if q.answer and q.answer.clarity_score is not None else 0.0
        o_score = q.answer.overall_score if q.answer and q.answer.overall_score is not None else 0.0
        fb_text = q.answer.feedback_text if q.answer and q.answer.feedback_text else "No evaluation available."

        if q.answer:
            tech_scores.append(t_score)
            rel_scores.append(r_score)
            comp_scores.append(c_score)
            clar_scores.append(cl_score)
            overall_scores.append(o_score)

        qa_list.append({
            "question_id": q.id,
            "order_index": q.order_index,
            "category": q.category.value,
            "difficulty": q.difficulty.value,
            "question_text": q.question_text,
            "answer_text": ans_text,
            "technical_score": t_score,
            "relevance_score": r_score,
            "completeness_score": c_score,
            "clarity_score": cl_score,
            "overall_score": o_score,
            "feedback_text": fb_text,
        })

    def _avg(lst: list[float]) -> float:
        return round(float(sum(lst) / len(lst)), 1) if lst else 0.0

    avg_tech = _avg(tech_scores)
    avg_rel = _avg(rel_scores)
    avg_comp = _avg(comp_scores)
    avg_clar = _avg(clar_scores)
    avg_overall = _avg(overall_scores)

    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations = ""

    if interview.report:
        strengths = _extract_list_items(interview.report.strengths_json)
        weaknesses = _extract_list_items(interview.report.weaknesses_json)
        recommendations = interview.report.recommendations_text or ""

    # Enforce non-empty fallback guarantees
    strengths, weaknesses = _ensure_guaranteed_strengths_and_weaknesses(
        strengths=strengths,
        weaknesses=weaknesses,
        role=interview.role,
        interview_type=interview.interview_type.value,
        avg_overall=avg_overall,
        avg_tech=avg_tech,
        avg_comp=avg_comp,
        avg_rel=avg_rel,
        avg_clar=avg_clar,
        q_count=len(qa_list),
    )

    return {
        "interview_id": interview.id,
        "candidate_id": interview.candidate_id,
        "role": interview.role,
        "interview_type": interview.interview_type.value,
        "difficulty_mode": interview.difficulty_mode.value,
        "status": interview.status.value,
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
        "overall_score": avg_overall,
        "avg_technical_score": avg_tech,
        "avg_relevance_score": avg_rel,
        "avg_completeness_score": avg_comp,
        "avg_clarity_score": avg_clar,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "questions": qa_list,
    }


# ── Historical Candidate Progress Tracking ─────────────────────────────────────

async def get_candidate_progress_history(
    db: AsyncSession,
    candidate_id: int = 1,
) -> list[dict[str, Any]]:
    """
    Fetch all completed interview sessions for candidate #1 ordered by completed_at ASC.
    Computes real aggregate overall and dimension scores for historical progression graphs.
    """
    stmt = (
        select(Interview)
        .options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer),
            selectinload(Interview.report),
        )
        .where(
            Interview.candidate_id == candidate_id,
            Interview.status == InterviewStatus.COMPLETED,
        )
        .order_by(Interview.completed_at.asc())
    )

    res = await db.execute(stmt)
    completed_interviews = res.scalars().all()

    progress_records: list[dict[str, Any]] = []

    for item in completed_interviews:
        overall_scores: list[float] = []
        tech_scores: list[float] = []

        for q in item.questions:
            if q.answer and q.answer.overall_score is not None:
                overall_scores.append(q.answer.overall_score)
            if q.answer and q.answer.technical_score is not None:
                tech_scores.append(q.answer.technical_score)

        avg_ovr = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0.0
        avg_tch = round(sum(tech_scores) / len(tech_scores), 1) if tech_scores else 0.0

        progress_records.append({
            "interview_id": item.id,
            "role": item.role,
            "interview_type": item.interview_type.value,
            "difficulty_mode": item.difficulty_mode.value,
            "overall_score": avg_ovr,
            "avg_technical_score": avg_tch,
            "completed_at": item.completed_at.isoformat() if item.completed_at else item.created_at.isoformat(),
        })

    return progress_records
