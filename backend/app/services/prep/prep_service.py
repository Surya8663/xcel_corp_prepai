"""
PrepAI — Prep Question Service.

Orchestrates generating interview study questions with Gemini,
persisting them to the prep_questions table, and fetching filtered/paginated questions.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PrepQuestion, CandidateProfile, Resume, QuestionDifficulty
from app.services.ai.gemini_service import GeminiService
from app.services.ai.prompt_templates import prep_question_generation_prompt

logger = logging.getLogger(__name__)


async def generate_prep_questions(
    *,
    db: AsyncSession,
    role: str,
    topic: Optional[str] = None,
    difficulty: str = "medium",
    count: int = 5,
) -> List[PrepQuestion]:
    """
    Generates a batch of prep questions using Gemini AI, saves them to DB, and returns them.
    Includes candidate resume skills if available in DB for background tailoring.
    """
    ai = GeminiService(db_session=db)

    # 1. Fetch single candidate profile
    cand_res = await db.execute(select(CandidateProfile).limit(1))
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise RuntimeError("No candidate profile found. Please run seed script.")

    # 2. Check for latest resume skills context
    resume_res = await db.execute(select(Resume).order_by(Resume.created_at.desc()).limit(1))
    latest_resume = resume_res.scalar_one_or_none()
    resume_skills = None
    if latest_resume and latest_resume.parsed_json:
        resume_skills = latest_resume.parsed_json.get("skills")

    # 3. Generate questions with Gemini
    prompt = prep_question_generation_prompt(
        role=role,
        topic=topic,
        difficulty=difficulty,
        num_questions=count,
        resume_skills=resume_skills,
    )
    
    logger.info("Calling Gemini to generate %d prep questions for role='%s', topic='%s', diff='%s'...", count, role, topic, difficulty)
    raw_list = await ai.generate_structured_json(
        prompt,
        feature_name="prep_question_generation",
    )

    if not isinstance(raw_list, list):
        if isinstance(raw_list, dict) and "questions" in raw_list:
            raw_list = raw_list["questions"]
        else:
            raw_list = [raw_list]

    # Map string difficulty to Enum safely
    diff_map = {
        "easy": QuestionDifficulty.EASY,
        "medium": QuestionDifficulty.MEDIUM,
        "hard": QuestionDifficulty.HARD,
    }
    target_diff_enum = diff_map.get(difficulty.lower(), QuestionDifficulty.MEDIUM)

    created_questions: List[PrepQuestion] = []
    for item in raw_list:
        q_text = item.get("question_text") or item.get("question")
        m_text = item.get("model_answer_text") or item.get("model_answer") or item.get("answer")
        item_topic = item.get("topic") or topic or "General Technical"
        
        if not q_text or not m_text:
            continue

        item_diff_str = str(item.get("difficulty", difficulty)).lower()
        item_diff_enum = diff_map.get(item_diff_str, target_diff_enum)

        prep_q = PrepQuestion(
            candidate_id=candidate.id,
            role=role,
            topic=item_topic,
            difficulty=item_diff_enum,
            question_text=q_text,
            model_answer_text=m_text,
        )
        db.add(prep_q)
        created_questions.append(prep_q)

    await db.commit()
    for q in created_questions:
        await db.refresh(q)

    logger.info("Successfully persisted %d generated prep questions to DB", len(created_questions))
    return created_questions


async def get_prep_questions(
    *,
    db: AsyncSession,
    role: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[PrepQuestion]:
    """Fetch stored prep questions with optional role, topic, and difficulty filters."""
    query = select(PrepQuestion)

    if role:
        query = query.where(PrepQuestion.role.ilike(f"%{role}%"))
    if topic and topic.lower() != "all":
        query = query.where(PrepQuestion.topic.ilike(f"%{topic}%"))
    if difficulty and difficulty.lower() != "all":
        diff_map = {
            "easy": QuestionDifficulty.EASY,
            "medium": QuestionDifficulty.MEDIUM,
            "hard": QuestionDifficulty.HARD,
        }
        if difficulty.lower() in diff_map:
            query = query.where(PrepQuestion.difficulty == diff_map[difficulty.lower()])

    query = query.order_by(PrepQuestion.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    return list(res.scalars().all())


async def get_prep_filters(*, db: AsyncSession) -> dict:
    """Get distinct roles and topics available in stored prep questions."""
    roles_res = await db.execute(select(distinct(PrepQuestion.role)))
    topics_res = await db.execute(select(distinct(PrepQuestion.topic)))

    roles = [r for r in roles_res.scalars().all() if r]
    topics = [t for t in topics_res.scalars().all() if t]

    return {
        "roles": roles,
        "topics": topics,
    }
