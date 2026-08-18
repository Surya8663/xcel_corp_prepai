"""
PrepAI — AI Answer Evaluation Engine Verification Test.

Proves that:
1. A strong, detailed technical answer receives high dimensional scores (~8.5-9.5) and tailored feedback.
2. A weak, vague answer receives lower scores (~2.5-5.0) with constructive feedback highlighting missing details.
3. An empty/auto-submitted answer triggers the deterministic short-circuit exception with 0.0 scores.
"""

import asyncio
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import InterviewAnswer

BASE_URL = "http://localhost:8000"


async def fetch_stored_answer_scores(question_id: int):
    """Fetch stored DB row from interview_answers for verification."""
    async with AsyncSessionLocal() as session:
        stmt = select(InterviewAnswer).where(InterviewAnswer.question_id == question_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()


async def run_evaluation_test():
    print("=" * 70)
    print("  PrepAI — AI Answer Evaluation Engine Verification Test")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=90.0) as client:
        # Step 1: Create an Interview Session
        print("\n[1/4] Creating Interview Session...")
        create_res = await client.post(
            f"{BASE_URL}/api/interview/create",
            json={
                "role": "Senior Backend Engineer",
                "interview_type": "Technical",
                "difficulty_mode": "Medium",
                "duration_minutes": 30,
                "question_count": 3,
            },
        )
        assert create_res.status_code == 201, f"Failed create: {create_res.text}"
        session_data = create_res.json()
        interview_id = session_data["id"]
        print(f"      Created Interview ID={interview_id}")

        # Step 2: Test STRONG Answer Evaluation
        print("\n[2/4] Testing Question #1 with STRONG technical answer...")
        q1_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
        assert q1_res.status_code == 201
        q1 = q1_res.json()
        print(f"      Q1: '{q1['question_text'][:80]}...'")

        strong_answer = (
            "To handle high throughput and avoid database bottlenecking, I would implement a multi-layer caching architecture. "
            "At the application layer, I would use Redis cluster with consistent hashing and write-behind persistence. "
            "For PostgreSQL, I would configure PgBouncer connection pooling and read-replicas for query offloading. "
            "To prevent cache stampede under heavy load, I'd apply mutex locking and probabilistic early expiration."
        )

        ans1_res = await client.post(
            f"{BASE_URL}/api/interview/{interview_id}/answer",
            json={"question_id": q1["id"], "answer_text": strong_answer},
        )
        assert ans1_res.status_code == 201

        db_ans1 = await fetch_stored_answer_scores(q1["id"])
        assert db_ans1 is not None, "DB record missing for Q1"
        print(f"      [STRONG SCORE] Overall: {db_ans1.overall_score:.1f}/10 (Tech: {db_ans1.technical_score:.1f}, Rel: {db_ans1.relevance_score:.1f}, Comp: {db_ans1.completeness_score:.1f}, Clar: {db_ans1.clarity_score:.1f})")
        print(f"      Feedback: '{db_ans1.feedback_text[:120]}...'")

        assert db_ans1.overall_score >= 7.0, f"Expected overall score >= 7.0, got {db_ans1.overall_score}"
        assert len(db_ans1.feedback_text) > 20, "Expected meaningful feedback text"

        # Step 3: Test WEAK Answer Evaluation
        print("\n[3/4] Testing Question #2 with WEAK/vague answer...")
        await asyncio.sleep(3)
        q2_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
        assert q2_res.status_code == 201
        q2 = q2_res.json()
        print(f"      Q2: '{q2['question_text'][:80]}...'")

        weak_answer = "I will just use a database and maybe add some caching to make it run faster."

        await asyncio.sleep(2)
        ans2_res = await client.post(
            f"{BASE_URL}/api/interview/{interview_id}/answer",
            json={"question_id": q2["id"], "answer_text": weak_answer},
        )
        assert ans2_res.status_code == 201

        db_ans2 = await fetch_stored_answer_scores(q2["id"])
        assert db_ans2 is not None, "DB record missing for Q2"
        print(f"      [WEAK SCORE] Overall: {db_ans2.overall_score:.1f}/10 (Tech: {db_ans2.technical_score:.1f}, Rel: {db_ans2.relevance_score:.1f}, Comp: {db_ans2.completeness_score:.1f}, Clar: {db_ans2.clarity_score:.1f})")
        print(f"      Feedback: '{db_ans2.feedback_text[:120]}...'")

        assert db_ans2.overall_score < db_ans1.overall_score, "Weak answer overall score should be lower than strong answer"
        assert db_ans2.overall_score <= 6.0, f"Expected weak score <= 6.0, got {db_ans2.overall_score}"

        # Step 4: Test EMPTY / Auto-submitted Answer (Deterministic Short-Circuit)
        print("\n[4/4] Testing Question #3 with EMPTY/auto-submitted answer...")
        await asyncio.sleep(3)
        q3_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
        assert q3_res.status_code == 201
        q3 = q3_res.json()
        print(f"      Q3: '{q3['question_text'][:80]}...'")

        empty_answer = "[Time expired — answer submitted automatically]"

        await asyncio.sleep(1)

        ans3_res = await client.post(
            f"{BASE_URL}/api/interview/{interview_id}/answer",
            json={"question_id": q3["id"], "answer_text": empty_answer},
        )
        assert ans3_res.status_code == 201

        db_ans3 = await fetch_stored_answer_scores(q3["id"])
        assert db_ans3 is not None, "DB record missing for Q3"
        print(f"      [EMPTY SCORE] Overall: {db_ans3.overall_score:.1f}/10 (Tech: {db_ans3.technical_score:.1f}, Rel: {db_ans3.relevance_score:.1f}, Comp: {db_ans3.completeness_score:.1f}, Clar: {db_ans3.clarity_score:.1f})")
        print(f"      Feedback: '{db_ans3.feedback_text[:120]}...'")

        # VERIFY DETERMINISTIC SHORT-CIRCUIT
        assert db_ans3.technical_score == 0.0
        assert db_ans3.relevance_score == 0.0
        assert db_ans3.completeness_score == 0.0
        assert db_ans3.clarity_score == 0.0
        assert db_ans3.overall_score == 0.0
        print("      [VERIFIED] Deterministic short-circuit successfully scored empty answer as 0.0!")

    print("\n[SUCCESS] ALL AI ANSWER EVALUATION ENGINE TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(run_evaluation_test())
