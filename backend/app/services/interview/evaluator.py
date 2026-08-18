"""
PrepAI — Real-Time AI Answer Evaluation Service.

Evaluates candidate answers across 4 scoring dimensions (0.0 – 10.0):
1. technical_score
2. relevance_score
3. completeness_score
4. clarity_score
5. overall_score (weighted aggregate)
6. feedback_text (qualitative feedback referencing specific candidate statements)

Handles empty / auto-submitted answers with deterministic short-circuiting.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import InterviewAnswer, InterviewQuestion
from app.services.ai.gemini_service import GeminiService
from app.services.ai.prompt_templates import answer_evaluation_prompt

logger = logging.getLogger(__name__)


# ── Empty / Auto-submit Detection ─────────────────────────────────────────────

def _is_empty_or_autosubmit(text: str | None) -> bool:
    if not text:
        return True
    cleaned = text.strip().lower()
    if len(cleaned) < 3:
        return True
    autosubmit_tokens = [
        "[time expired",
        "no response provided",
        "time ran out",
        "n/a",
    ]
    return any(tok in cleaned for tok in autosubmit_tokens)


# ── Core Evaluation Function ──────────────────────────────────────────────────

async def evaluate_answer(
    question_text: str,
    answer_text: str,
    role: str = "Software Engineer",
    category: str = "Technical",
    difficulty: str = "Medium",
    ai_service: GeminiService | None = None,
) -> dict[str, Any]:
    """
    Evaluates candidate's answer text using Gemini AI in structured JSON mode.
    Short-circuits empty/blank responses deterministically to score 0.0 with clear guidance.
    """
    # 1. Deterministic Short-Circuit for Empty Answers
    if _is_empty_or_autosubmit(answer_text):
        logger.info(
            "[EVALUATION] Deterministic short-circuit exception triggered for empty/blank answer."
        )
        return {
            "technical_score": 0.0,
            "relevance_score": 0.0,
            "completeness_score": 0.0,
            "clarity_score": 0.0,
            "overall_score": 0.0,
            "feedback_text": (
                "No answer was submitted for this question before the timer expired or input was blank. "
                "To receive technical credit, provide key architectural trade-offs, algorithms, or mechanics even if brief."
            ),
        }

    # 2. Non-empty answer -> Call Gemini AI for Evaluation
    prompt = answer_evaluation_prompt(
        role=role,
        question_text=question_text,
        answer_text=answer_text,
        category=category,
        difficulty=difficulty,
    )

    if ai_service is None:
        # Fallback if AI service unprovided
        return {
            "technical_score": 5.0,
            "relevance_score": 5.0,
            "completeness_score": 5.0,
            "clarity_score": 5.0,
            "overall_score": 5.0,
            "feedback_text": "Answer recorded. Evaluation pending AI service initialization.",
        }

    try:
        eval_json = await ai_service.generate_structured_json(
            prompt=prompt,
            feature_name="answer_evaluation",
            temperature=0.2,
        )

        def _clean_score(val: Any, default: float = 5.0) -> float:
            try:
                f_val = float(val)
                return max(0.0, min(10.0, round(f_val, 1)))
            except (ValueError, TypeError):
                return default

        tech = _clean_score(eval_json.get("technical_score"))
        rel = _clean_score(eval_json.get("relevance_score"))
        comp = _clean_score(eval_json.get("completeness_score"))
        clar = _clean_score(eval_json.get("clarity_score"))
        overall = _clean_score(eval_json.get("overall_score"))
        feedback = str(eval_json.get("feedback_text", "")).strip()

        if not feedback:
            feedback = f"Answer evaluated for {role} at {difficulty} level."

        logger.info(
            "[EVALUATION] Gemini score: overall=%.1f (tech=%.1f, rel=%.1f, comp=%.1f, clar=%.1f)",
            overall, tech, rel, comp, clar,
        )

        return {
            "technical_score": tech,
            "relevance_score": rel,
            "completeness_score": comp,
            "clarity_score": clar,
            "overall_score": overall,
            "feedback_text": feedback,
        }

    except Exception as exc:
        logger.error("[EVALUATION] Gemini evaluation failed: %s", exc)
        raise exc

        word_count = len(words)
        lower_ans = answer_text.lower()

        tech_keywords = [
            "redis", "postgres", "postgresql", "pgbouncer", "cache", "caching", "cluster",
            "sharding", "replication", "async", "lock", "queue", "kafka", "distributed",
            "consistency", "latency", "throughput", "index", "b-tree", "thread", "pool"
        ]
        matched = [k for k in tech_keywords if k in lower_ans]
        kw_density = len(matched)

        if word_count > 30 and kw_density >= 2:
            tech = min(9.5, round(7.0 + (kw_density * 0.6), 1))
            rel = min(9.5, round(7.5 + (word_count * 0.02), 1))
            comp = min(9.0, round(6.5 + (word_count * 0.03), 1))
            clar = 8.5
            overall = round(tech * 0.4 + rel * 0.3 + comp * 0.2 + clar * 0.1, 1)
            feedback = (
                f"Strong technical response covering key concepts including {', '.join(matched[:3])}. "
                "Demonstrates good architectural awareness and clarity."
            )
        elif word_count > 10:
            tech = 4.5
            rel = 5.0
            comp = 3.5
            clar = 5.5
            overall = 4.5
            feedback = (
                "The answer provides a basic overview but lacks specific technical depth, "
                "concrete mechanics, or trade-offs. Elaborate on core data structures and edge cases."
            )
        else:
            tech = 2.5
            rel = 3.0
            comp = 2.0
            clar = 4.0
            overall = 2.8
            feedback = (
                "Answer is minimal and missing technical justification. Provide specific framework and database mechanisms."
            )

        return {
            "technical_score": tech,
            "relevance_score": rel,
            "completeness_score": comp,
            "clarity_score": clar,
            "overall_score": overall,
            "feedback_text": feedback,
        }


# ── DB Service Integration ────────────────────────────────────────────────────

async def evaluate_and_save_answer(
    db: AsyncSession,
    interview_id: int,
    question_id: int,
    answer_text: str,
    ai_service: GeminiService,
) -> InterviewAnswer:
    """
    1. Loads question and interview context from PostgreSQL.
    2. Runs answer evaluation via Gemini AI or empty short-circuit.
    3. Saves raw answer, scores, and feedback in interview_answers table.
    """
    # Fetch Question with parent Interview
    stmt = (
        select(InterviewQuestion)
        .options(selectinload(InterviewQuestion.interview))
        .where(InterviewQuestion.id == question_id)
    )
    res = await db.execute(stmt)
    question = res.scalar_one_or_none()

    if not question:
        raise ValueError(f"Question #{question_id} not found.")

    role = question.interview.role if question.interview else "Software Engineer"
    category = question.category.value
    difficulty = question.difficulty.value

    # Run AI Evaluation
    eval_result = await evaluate_answer(
        question_text=question.question_text,
        answer_text=answer_text,
        role=role,
        category=category,
        difficulty=difficulty,
        ai_service=ai_service,
    )

    # Check if answer row already exists
    stmt_ans = select(InterviewAnswer).where(InterviewAnswer.question_id == question_id)
    ans_res = await db.execute(stmt_ans)
    existing_answer = ans_res.scalar_one_or_none()

    if existing_answer:
        existing_answer.answer_text = answer_text.strip()
        existing_answer.technical_score = eval_result["technical_score"]
        existing_answer.relevance_score = eval_result["relevance_score"]
        existing_answer.completeness_score = eval_result["completeness_score"]
        existing_answer.clarity_score = eval_result["clarity_score"]
        existing_answer.overall_score = eval_result["overall_score"]
        existing_answer.feedback_text = eval_result["feedback_text"]

        await db.commit()
        await db.refresh(existing_answer)

        logger.info(
            "[EVALUATION] Updated Answer ID=%d for Question #%d (overall=%.1f)",
            existing_answer.id, question_id, existing_answer.overall_score,
        )
        return existing_answer

    # Create new InterviewAnswer row
    new_answer = InterviewAnswer(
        question_id=question_id,
        answer_text=answer_text.strip(),
        technical_score=eval_result["technical_score"],
        relevance_score=eval_result["relevance_score"],
        completeness_score=eval_result["completeness_score"],
        clarity_score=eval_result["clarity_score"],
        overall_score=eval_result["overall_score"],
        feedback_text=eval_result["feedback_text"],
    )

    db.add(new_answer)
    await db.commit()
    await db.refresh(new_answer)

    logger.info(
        "[EVALUATION] Persisted Answer ID=%d for Question #%d with score=%.1f/10",
        new_answer.id, question_id, new_answer.overall_score,
    )
    return new_answer
