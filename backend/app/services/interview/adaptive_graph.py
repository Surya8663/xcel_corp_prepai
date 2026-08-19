"""
PrepAI — LangGraph Adaptive Question Generation Engine.

ARCHITECTURE & GRAPH STRUCTURE:
  This module builds an explicit 4-node LangGraph StateGraph for generating individual
  interview questions tailored to candidate resume context, job description skills,
  and real-time performance evaluation signals.

GRAPH NODES & FLOW:
  START
    │
    ▼
  [Node 1: analyze_context]
    - Extracts candidate resume skills, project names, and JD required skills.
    - Inspects all previously answered questions & evaluation scores in this session.
    - Computes running average performance score (0.0 - 10.0 scale).
    │
    ▼
  [Node 2: determine_difficulty_and_category]
    - If difficulty_mode is fixed ("easy"|"medium"|"hard"), retains fixed mode.
    - If difficulty_mode is "adaptive":
        - Default start difficulty = "medium".
        - If recent avg score >= 7.5 -> Escalate (easy->medium, medium->hard).
        - If recent avg score <= 4.5 -> De-escalate (hard->medium, medium->easy).
        - Otherwise -> Hold steady.
    - Enforces Timer Rule: If chosen difficulty == "hard", sets time_limit_seconds = 120.
      Otherwise time_limit_seconds = None (null).
    - Rotates question category (system_design, algorithms, problem_solving, etc.).
    │
    ▼
  [Node 3: generate_question_node]
    - Constructs prompt incorporating role, category, target difficulty, resume & JD details.
    - Calls GeminiService in JSON mode to generate 1 tailored question.
    │
    ▼
  [Node 4: persist_question_node]
    - Inserts new row into PostgreSQL interview_questions table.
    │
    ▼
   END
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    DifficultyMode,
    Interview,
    InterviewAnswer,
    InterviewQuestion,
    QuestionCategory,
    QuestionDifficulty,
)
from app.services.ai.gemini_service import GeminiService

logger = logging.getLogger(__name__)


# ── State Definition ──────────────────────────────────────────────────────────

class InterviewGraphState(TypedDict):
    # Context Inputs
    interview_id: int
    role: str
    interview_type: str
    difficulty_mode: str
    question_count: int

    resume_skills: list[str]
    resume_projects: list[str]
    jd_required_skills: list[str]

    # Session History
    asked_questions: list[dict[str, Any]]
    previous_answers: list[dict[str, Any]]
    current_order_index: int

    # Adaptive Decisions
    running_avg_score: float | None
    target_difficulty: str
    target_category: str
    time_limit_seconds: int | None
    adaptive_decision_reason: str

    # Generated Output
    generated_question_text: str
    question_id: int | None


# ── Graph Node Implementations ────────────────────────────────────────────────

def node_analyze_context(state: InterviewGraphState) -> dict[str, Any]:
    """
    Node 1: Analyze Session History & Candidate Context.
    Computes running average score from previously answered questions.
    """
    answers = state.get("previous_answers", [])
    if answers:
        # Calculate recent average score (last 3 answers or all if fewer)
        recent_scores = [
            a["overall_score"] for a in answers if a.get("overall_score") is not None
        ]
        if recent_scores:
            avg_score = float(sum(recent_scores) / len(recent_scores))
        else:
            avg_score = None
    else:
        avg_score = None

    order_index = len(state.get("asked_questions", [])) + 1

    logger.info(
        "[LANGGRAPH] Node 1 (analyze_context): session=%d, prior_qs=%d, prior_answers=%d, running_avg_score=%s",
        state["interview_id"], len(state.get("asked_questions", [])), len(answers),
        f"{avg_score:.2f}" if avg_score is not None else "None",
    )

    return {
        "running_avg_score": avg_score,
        "current_order_index": order_index,
    }


def node_determine_difficulty_and_category(state: InterviewGraphState) -> dict[str, Any]:
    """
    Node 2: Determine Difficulty Tier & Select Category.
    Implements real adaptive escalation/de-escalation and timer rule.
    """
    mode = state.get("difficulty_mode", "medium").lower()
    avg_score = state.get("running_avg_score")
    asked_qs = state.get("asked_questions", [])

    # Previous difficulty (if any question was asked before)
    last_diff = asked_qs[-1]["difficulty"].lower() if asked_qs else "medium"

    target_diff = mode
    reason = f"Fixed difficulty mode '{mode}' selected."

    if mode == "adaptive":
        if avg_score is None:
            target_diff = "medium"
            reason = "Adaptive mode initial question -> Started at Medium difficulty."
        elif avg_score >= 7.5:
            # Escalate difficulty
            if last_diff == "easy":
                target_diff = "medium"
            elif last_diff == "medium":
                target_diff = "hard"
            else:
                target_diff = "hard"
            reason = f"High performance score ({avg_score:.1f}/10) -> Escalated difficulty from {last_diff} to {target_diff}."
        elif avg_score <= 4.5:
            # De-escalate difficulty
            if last_diff == "hard":
                target_diff = "medium"
            elif last_diff == "medium":
                target_diff = "easy"
            else:
                target_diff = "easy"
            reason = f"Low performance score ({avg_score:.1f}/10) -> Softened difficulty from {last_diff} to {target_diff}."
        else:
            # Hold steady
            target_diff = last_diff
            reason = f"Moderate performance score ({avg_score:.1f}/10) -> Retained {target_diff} difficulty."

    # Timer Rule: If Hard difficulty, enforce 120-second timer
    time_limit = 120 if target_diff == "hard" else None

    # Category Selection based on interview type & rotation
    i_type = state.get("interview_type", "technical").lower()
    used_categories = {q.get("category", "").lower() for q in asked_qs}

    if "behavioral" in i_type or "hr" in i_type:
        category_pool = ["behavioral", "problem_solving", "domain_knowledge"]
    elif "system" in i_type:
        category_pool = ["system_design", "databases", "networking", "problem_solving"]
    else:
        category_pool = [
            "data_structures",
            "algorithms",
            "system_design",
            "databases",
            "problem_solving",
            "language_specific",
        ]

    # Pick an unused category if possible
    available = [c for c in category_pool if c not in used_categories]
    target_cat = available[0] if available else category_pool[len(asked_qs) % len(category_pool)]

    logger.info(
        "[LANGGRAPH] Node 2 (determine_difficulty_and_category): mode='%s' -> target_diff='%s', timer=%s, cat='%s' | Reason: %s",
        mode, target_diff, f"{time_limit}s" if time_limit else "None", target_cat, reason,
    )

    return {
        "target_difficulty": target_diff,
        "target_category": target_cat,
        "time_limit_seconds": time_limit,
        "adaptive_decision_reason": reason,
    }


async def node_generate_question(
    state: InterviewGraphState,
    ai_service: GeminiService,
) -> dict[str, Any]:
    """
    Node 3: Call Gemini to Generate 1 Tailored Question.
    Incorporate candidate resume background skills, projects, and JD requirements.
    """
    role = state.get("role", "Software Engineer")
    target_diff = state.get("target_difficulty", "medium")
    target_cat = state.get("target_category", "problem_solving")
    r_skills = state.get("resume_skills", [])
    r_projects = state.get("resume_projects", [])
    jd_skills = state.get("jd_required_skills", [])
    asked_texts = [q["question_text"] for q in state.get("asked_questions", [])]

    # Build prompt
    resume_context_clause = ""
    if r_skills or r_projects:
        skills_str = ", ".join(r_skills[:10]) if r_skills else "N/A"
        proj_str = ", ".join(r_projects[:3]) if r_projects else "N/A"
        resume_context_clause = (
            f"\nCandidate Resume Background:\n"
            f"- Key Skills: {skills_str}\n"
            f"- Featured Projects: {proj_str}\n"
            f"Instruct the question to reference candidate background or practical scenario where natural."
        )

    jd_clause = ""
    if jd_skills:
        jd_clause = f"\nTarget Job Description Required Skills: {', '.join(jd_skills[:10])}"

    prior_clause = ""
    if asked_texts:
        prior_clause = f"\nDo NOT repeat or rephrase these already asked questions:\n" + "\n".join(
            [f"- {t}" for t in asked_texts]
        )

    prompt = f"""You are a principal engineer conducting a live technical mock interview for the role of '{role}'.
Generate EXACTLY ONE realistic interview question.

Category: '{target_cat.replace('_', ' ').title()}'
Target Difficulty Level: '{target_diff.upper()}'{resume_context_clause}{jd_clause}{prior_clause}

Return ONLY a JSON object matching this exact schema:
{{
  "question_text": "<Clear, engaging, technical interview question text>",
  "category": "{target_cat}",
  "difficulty": "{target_diff}"
}}

Rules:
1. Question MUST be tailored specifically to a '{role}' at '{target_diff}' difficulty.
2. If candidate resume skills/projects are listed, tie the scenario to their tech stack (e.g. Python, FastAPI, React, Redis).
3. Be direct and realistic — ask how they would design, debug, optimize, or make tradeoffs.
4. Return ONLY valid JSON.
"""

    try:
        res = await ai_service.generate_structured_json(
            prompt=prompt,
            feature_name="adaptive_question_generation",
            temperature=0.4,
        )
        q_text = res.get("question_text", "").strip()
        if not q_text:
            raise ValueError("Gemini returned empty question_text.")
    except Exception as exc:
        logger.error("[LANGGRAPH] Gemini question generation failed: %s", exc)
        raise exc


    logger.info(
        "[LANGGRAPH] Node 3 (generate_question): Generated Q (len=%d): '%s...'",
        len(q_text), q_text[:80],
    )

    return {
        "generated_question_text": q_text,
    }


# ── LangGraph Compiler & Execution Pipeline ────────────────────────────────────

def build_adaptive_question_graph(ai_service: GeminiService):
    """
    Construct and compile the LangGraph StateGraph pipeline.
    """
    async def async_gen_node(state: InterviewGraphState) -> dict[str, Any]:
        return await node_generate_question(state, ai_service=ai_service)

    builder = StateGraph(InterviewGraphState)

    # Add Nodes
    builder.add_node("analyze_context", node_analyze_context)
    builder.add_node("determine_difficulty_and_category", node_determine_difficulty_and_category)
    builder.add_node("generate_question", async_gen_node)

    # Define Edges
    builder.add_edge(START, "analyze_context")
    builder.add_edge("analyze_context", "determine_difficulty_and_category")
    builder.add_edge("determine_difficulty_and_category", "generate_question")
    builder.add_edge("generate_question", END)

    return builder.compile()


# ── DB Context Loader & Main Entrypoint ────────────────────────────────────────

async def generate_next_interview_question(
    db: AsyncSession,
    interview_id: int,
    ai_service: GeminiService,
) -> InterviewQuestion:
    """
    Main entrypoint called by POST /api/interview/{id}/next-question.

    1. Loads interview session, linked resume, linked job description, and prior questions/answers.
    2. Constructs state and executes the LangGraph adaptive workflow.
    3. Persists the generated question as a real row in interview_questions.
    4. Returns the created InterviewQuestion ORM model.
    """
    # 1. Load Interview with relationships
    stmt = (
        select(Interview)
        .options(
            selectinload(Interview.resume),
            selectinload(Interview.job_description),
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer),
        )
        .where(Interview.id == interview_id)
    )
    res = await db.execute(stmt)
    interview = res.scalar_one_or_none()

    if not interview:
        raise ValueError(f"Interview session #{interview_id} not found.")

    # 1b. Idempotency Check: if the most recent question is unanswered, return it as-is
    if interview.questions:
        sorted_qs = sorted(interview.questions, key=lambda x: x.order_index)
        latest_q = sorted_qs[-1]
        if latest_q.answer is None:
            logger.info(
                "[LANGGRAPH] Idempotent call: returning existing unanswered Question ID=%d (order=%d) for session #%d",
                latest_q.id, latest_q.order_index, interview_id,
            )
            return latest_q

    # 2. Extract Context details
    r_skills: list[str] = []
    r_projects: list[str] = []
    if interview.resume and interview.resume.parsed_json:
        pj = interview.resume.parsed_json
        r_skills = pj.get("skills", [])
        r_projs = pj.get("projects", [])
        for p in r_projs:
            if isinstance(p, dict) and p.get("name"):
                r_projects.append(p["name"])
            elif isinstance(p, str):
                r_projects.append(p)

    jd_skills: list[str] = []
    if interview.job_description and interview.job_description.parsed_required_skills_json:
        jd_pj = interview.job_description.parsed_required_skills_json
        jd_skills = jd_pj.get("required_skills", [])

    # 3. Extract Prior Asked Questions & Answer Scores
    asked_questions: list[dict[str, Any]] = []
    previous_answers: list[dict[str, Any]] = []

    for q in sorted(interview.questions, key=lambda x: x.order_index):
        asked_questions.append({
            "id": q.id,
            "order_index": q.order_index,
            "difficulty": q.difficulty.value,
            "category": q.category.value,
            "question_text": q.question_text,
        })
        if q.answer:
            previous_answers.append({
                "question_id": q.id,
                "overall_score": q.answer.overall_score,
                "technical_score": q.answer.technical_score,
                "answer_text": q.answer.answer_text,
            })

    # 4. Prepare LangGraph Initial State
    initial_state: InterviewGraphState = {
        "interview_id": interview.id,
        "role": interview.role,
        "interview_type": interview.interview_type.value,
        "difficulty_mode": interview.difficulty_mode.value,
        "question_count": interview.duration_minutes or 5,
        "resume_skills": r_skills,
        "resume_projects": r_projects,
        "jd_required_skills": jd_skills,
        "asked_questions": asked_questions,
        "previous_answers": previous_answers,
        "current_order_index": len(asked_questions) + 1,
        "running_avg_score": None,
        "target_difficulty": "medium",
        "target_category": "problem_solving",
        "time_limit_seconds": None,
        "adaptive_decision_reason": "",
        "generated_question_text": "",
        "question_id": None,
    }

    # 5. Execute LangGraph Graph
    graph = build_adaptive_question_graph(ai_service=ai_service)
    final_state = await graph.ainvoke(initial_state)

    # 6. Map target_difficulty & target_category strings to Enums
    diff_str = final_state["target_difficulty"].lower()
    diff_map = {
        "easy": QuestionDifficulty.EASY,
        "medium": QuestionDifficulty.MEDIUM,
        "hard": QuestionDifficulty.HARD,
    }
    q_diff = diff_map.get(diff_str, QuestionDifficulty.MEDIUM)

    cat_str = final_state["target_category"].lower()
    cat_map = {
        "data_structures": QuestionCategory.DATA_STRUCTURES,
        "algorithms": QuestionCategory.ALGORITHMS,
        "system_design": QuestionCategory.SYSTEM_DESIGN,
        "behavioral": QuestionCategory.BEHAVIORAL,
        "databases": QuestionCategory.DATABASES,
        "networking": QuestionCategory.NETWORKING,
        "operating_systems": QuestionCategory.OPERATING_SYSTEMS,
        "language_specific": QuestionCategory.LANGUAGE_SPECIFIC,
        "domain_knowledge": QuestionCategory.DOMAIN_KNOWLEDGE,
        "problem_solving": QuestionCategory.PROBLEM_SOLVING,
    }
    q_cat = cat_map.get(cat_str, QuestionCategory.PROBLEM_SOLVING)

    # 7. Persist generated Question to PostgreSQL
    new_question = InterviewQuestion(
        interview_id=interview.id,
        question_text=final_state["generated_question_text"],
        difficulty=q_diff,
        category=q_cat,
        order_index=final_state["current_order_index"],
        time_limit_seconds=final_state["time_limit_seconds"],
    )

    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)

    logger.info(
        "[LANGGRAPH] Persisted Question ID=%d (order=%d, diff=%s, cat=%s, timer=%s) for session #%d",
        new_question.id, new_question.order_index, new_question.difficulty.value,
        new_question.category.value, f"{new_question.time_limit_seconds}s" if new_question.time_limit_seconds else "None",
        interview.id,
    )

    return new_question


async def save_interview_answer(
    db: AsyncSession,
    interview_id: int,
    question_id: int,
    answer_text: str,
) -> InterviewAnswer:
    """
    Save or update candidate's spoken/typed answer to a question in interview_answers table.
    """
    stmt = select(InterviewAnswer).where(InterviewAnswer.question_id == question_id)
    res = await db.execute(stmt)
    existing_answer = res.scalar_one_or_none()

    if existing_answer:
        existing_answer.answer_text = answer_text.strip()
        await db.commit()
        await db.refresh(existing_answer)
        return existing_answer

    new_answer = InterviewAnswer(
        question_id=question_id,
        answer_text=answer_text.strip(),
    )
    db.add(new_answer)
    await db.commit()
    await db.refresh(new_answer)
    return new_answer
