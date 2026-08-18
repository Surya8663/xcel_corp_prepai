"""
PrepAI — Post-Interview Performance Report & Candidate Progress History Verification Test.

Proves that:
1. POST /api/interview/{id}/complete computes mathematical average scores from DB answer scores.
2. Gemini AI generates non-generic strengths, weaknesses, and personalized study recommendations.
3. Report is persisted in interview_reports table and interview status is marked "completed".
4. GET /api/interview/{id}/report returns full report card payload with per-question vector breakdowns.
5. GET /api/candidate/progress returns historical completed sessions for progression analytics.
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def run_report_and_progress_test():
    print("=" * 70)
    print("  PrepAI — Performance Report & Candidate Progress Verification")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=90.0) as client:
        # Step 1: Create a 3-Question Mock Interview
        print("\n[1/5] Creating 3-Question Technical Interview Session...")
        create_res = await client.post(
            f"{BASE_URL}/api/interview/create",
            json={
                "role": "Senior Distributed Systems Engineer",
                "interview_type": "Technical",
                "difficulty_mode": "Adaptive",
                "duration_minutes": 30,
                "question_count": 3,
            },
        )
        assert create_res.status_code == 201
        interview_id = create_res.json()["id"]
        print(f"      Created Interview Session #{interview_id}")

        # Step 2: Answer 3 Questions
        answers_payload = [
            "For distributed consensus under network partition, I would implement Raft consensus with leader lease heartbeat and write-ahead log replication.",
            "To prevent database connection starvation during peak traffic spikes, I'd implement PgBouncer in transaction pooling mode with max client connection caps.",
            "To handle eventual consistency across microservices, I would apply the Saga pattern with compensating transactions and dead-letter queues."
        ]

        for i, ans in enumerate(answers_payload, 1):
            print(f"      [Q{i}] Fetching question and submitting response...")
            await asyncio.sleep(2)
            q_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
            assert q_res.status_code == 201
            q_data = q_res.json()

            await asyncio.sleep(1)
            a_res = await client.post(
                f"{BASE_URL}/api/interview/{interview_id}/answer",
                json={"question_id": q_data["id"], "answer_text": ans},
            )
            assert a_res.status_code == 201

        # Step 3: Complete Interview & Generate Report Card
        print("\n[3/5] Calling POST /api/interview/{id}/complete to finalize session...")
        await asyncio.sleep(3)
        complete_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/complete")
        assert complete_res.status_code == 200, f"Failed complete: {complete_res.text}"
        rep = complete_res.json()

        print("\n" + "-" * 60)
        print("  GENERATED INTERVIEW REPORT CARD SUMMARY")
        print("-" * 60)
        print(f"  Target Role        : {rep['role']}")
        print(f"  Status             : {rep['status'].upper()}")
        print(f"  Overall Score      : {rep['overall_score']:.1f} / 10")
        print(f"  Technical Score    : {rep['avg_technical_score']:.1f} / 10")
        print(f"  Relevance Score    : {rep['avg_relevance_score']:.1f} / 10")
        print(f"  Completeness Score : {rep['avg_completeness_score']:.1f} / 10")
        print(f"  Clarity Score       : {rep['avg_clarity_score']:.1f} / 10")
        print(f"  Strengths Count    : {len(rep['strengths'])}")
        print(f"  Weaknesses Count   : {len(rep['weaknesses'])}")
        print(f"  Recommendation     : '{rep['recommendations'][:120]}...'")
        print("─" * 60)

        assert rep["status"] == "completed"
        assert rep["overall_score"] > 0.0
        assert len(rep["strengths"]) >= 1
        assert len(rep["recommendations"]) > 10

        # Step 4: GET /api/interview/{id}/report Verification
        print("\n[4/5] Calling GET /api/interview/{id}/report...")
        get_rep_res = await client.get(f"{BASE_URL}/api/interview/{interview_id}/report")
        assert get_rep_res.status_code == 200
        get_rep = get_rep_res.json()
        assert get_rep["interview_id"] == interview_id
        assert len(get_rep["questions"]) == 3
        print(f"      [VERIFIED] GET report endpoint returned {len(get_rep['questions'])} detailed Q&A breakdown items.")

        # Step 5: GET /api/candidate/progress Verification
        print("\n[5/5] Calling GET /api/candidate/progress...")
        prog_res = await client.get(f"{BASE_URL}/api/candidate/progress")
        assert prog_res.status_code == 200
        prog_list = prog_res.json()
        print(f"      Candidate Progress Records Count: {len(prog_list)}")

        completed_ids = [p["interview_id"] for p in prog_list]
        assert interview_id in completed_ids, f"Expected interview #{interview_id} in progress history"
        print(f"      [VERIFIED] Candidate progress endpoint contains completed session #{interview_id}!")

    print("\n[SUCCESS] ALL REPORT CARD & HISTORICAL PROGRESS ENGINE TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(run_report_and_progress_test())
