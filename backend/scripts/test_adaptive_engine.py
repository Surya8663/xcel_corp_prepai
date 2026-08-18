"""
PrepAI — LangGraph Adaptive Question Engine Verification Test.

Proves that:
1. First question in Adaptive Mode defaults to Medium difficulty (timer = None).
2. High simulated score (9.5/10) causes LangGraph to escalate next question to HARD (timer = 120s).
3. Low simulated score (2.0/10) causes LangGraph to de-escalate next question to MEDIUM/EASY.
"""

import asyncio
import httpx
from sqlalchemy import update
from app.core.database import AsyncSessionLocal
from app.models import InterviewAnswer

BASE_URL = "http://localhost:8000"


async def simulate_answer_score(question_id: int, score: float):
    """Update overall_score in interview_answers for test simulation."""
    async with AsyncSessionLocal() as session:
        stmt = (
            update(InterviewAnswer)
            .where(InterviewAnswer.question_id == question_id)
            .values(overall_score=score, technical_score=score)
        )
        await session.execute(stmt)
        await session.commit()
        print(f"      [SIMULATION] Updated Question #{question_id} overall_score to {score:.1f}/10 in DB")


async def run_adaptive_engine_test():
    print("=" * 65)
    print("  PrepAI — LangGraph Adaptive Engine & Escalation Verification")
    print("=" * 65)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create an Adaptive Mock Interview Session
        print("\n[1/5] Creating Adaptive Interview Session...")
        create_res = await client.post(
            f"{BASE_URL}/api/interview/create",
            json={
                "role": "Senior Backend Engineer",
                "interview_type": "Technical",
                "difficulty_mode": "Adaptive",
                "duration_minutes": 30,
                "question_count": 5,
            },
        )
        assert create_res.status_code == 201, f"Failed create: {create_res.text}"
        session_data = create_res.json()
        interview_id = session_data["id"]
        print(f"      Created Interview ID={interview_id} with difficulty_mode='adaptive'")

        # Step 2: Call next-question (Question 1)
        print("\n[2/5] Fetching Question #1 (Initial state in Adaptive mode)...")
        q1_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
        assert q1_res.status_code == 201, f"Failed Q1: {q1_res.text}"
        q1_data = q1_res.json()
        q1_id = q1_data["id"]
        print(f"      Q1 ID={q1_id} | Order={q1_data['order_index']} | Diff='{q1_data['difficulty'].upper()}' | Timer={q1_data['time_limit_seconds']}")
        print(f"      Prompt: '{q1_data['question_text'][:90]}...'")
        assert q1_data["difficulty"].lower() == "medium", f"Expected medium, got {q1_data['difficulty']}"
        assert q1_data["time_limit_seconds"] is None, "Medium question should have no timer limit"

        # Step 3: Submit Answer #1 & Simulate HIGH Score (9.5/10)
        print("\n[3/5] Submitting Answer #1 & Simulating HIGH Performance (9.5/10)...")
        ans1_res = await client.post(
            f"{BASE_URL}/api/interview/{interview_id}/answer",
            json={"question_id": q1_id, "answer_text": "Detailed technical explanation covering Redis caching, cache stampede prevention, and TTL invalidation."},
        )
        assert ans1_res.status_code == 201
        await simulate_answer_score(q1_id, 9.5)

        # Step 4: Call next-question (Question 2) -> LangGraph should ESCALATE to HARD (timer=120)
        print("\n[4/5] Fetching Question #2 (Expect ESCALATION to HARD due to high score)...")
        await asyncio.sleep(2)
        q2_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
        assert q2_res.status_code == 201, f"Failed Q2: {q2_res.text}"
        q2_data = q2_res.json()
        q2_id = q2_data["id"]
        print(f"      Q2 ID={q2_id} | Order={q2_data['order_index']} | Diff='{q2_data['difficulty'].upper()}' | Timer={q2_data['time_limit_seconds']}s")
        print(f"      Prompt: '{q2_data['question_text'][:90]}...'")

        # VERIFY HARD ESCALATION AND TIMER RULE
        assert q2_data["difficulty"].lower() == "hard", f"Expected HARD escalation, got {q2_data['difficulty']}"
        assert q2_data["time_limit_seconds"] == 120, f"Expected 120s timer for HARD question, got {q2_data['time_limit_seconds']}"
        print("      [VERIFIED] LangGraph successfully ESCALATED difficulty from MEDIUM -> HARD and set time_limit_seconds = 120s!")

        # Step 5: Submit Answer #2 & Simulate LOW Score (1.0/10)
        print("\n[5/5] Submitting Answer #2 & Simulating LOW Performance (1.0/10)...")
        ans2_res = await client.post(
            f"{BASE_URL}/api/interview/{interview_id}/answer",
            json={"question_id": q2_id, "answer_text": "I am not sure about this topic."},
        )
        assert ans2_res.status_code == 201
        await simulate_answer_score(q1_id, 1.0)
        await simulate_answer_score(q2_id, 1.0)

        # Call next-question (Question 3) -> LangGraph should DE-ESCALATE to MEDIUM
        print("      Fetching Question #3 (Expect DE-ESCALATION to MEDIUM due to lower average score)...")
        await asyncio.sleep(2)
        q3_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
        assert q3_res.status_code == 201, f"Failed Q3: {q3_res.text}"
        q3_data = q3_res.json()
        print(f"      Q3 ID={q3_data['id']} | Order={q3_data['order_index']} | Diff='{q3_data['difficulty'].upper()}' | Timer={q3_data['time_limit_seconds']}")
        assert q3_data["difficulty"].lower() in ["medium", "easy"], f"Expected de-escalation, got {q3_data['difficulty']}"
        print("      [VERIFIED] LangGraph successfully DE-ESCALATED difficulty from HARD -> MEDIUM/EASY!")

    print("\n[SUCCESS] ALL LANGGRAPH ADAPTIVE ENGINE TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(run_adaptive_engine_test())
