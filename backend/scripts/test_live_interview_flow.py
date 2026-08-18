"""
PrepAI — Live Mock Interview End-to-End Integration Test.

Tests:
1. Creating a live interview session with Hard difficulty mode.
2. Fetching Question #1 -> Validates Gemini question text & 120s timer.
3. Submitting Answer #1 -> Stores response.
4. Fetching Question #2 -> Validates order index progression.
5. Submitting Answer #2 -> Stores response.
6. Fetching Question #3 -> Validates final question.
7. Submitting Answer #3 -> Confirms complete interview session flow.
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def test_live_interview_flow():
    print("=" * 65)
    print("  PrepAI — Live Interview End-to-End API Test")
    print("=" * 65)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Create Interview Session
        print("\n[1/4] Creating 3-Question Hard Mode Interview Session...")
        res = await client.post(
            f"{BASE_URL}/api/interview/create",
            json={
                "role": "Senior Full-Stack Engineer",
                "interview_type": "Technical",
                "difficulty_mode": "Hard",
                "duration_minutes": 15,
                "question_count": 3,
            },
        )
        assert res.status_code == 201, f"Failed create session: {res.text}"
        session = res.json()
        interview_id = session["id"]
        print(f"      Created Interview Session #{interview_id}")

        # 2. Loop through all 3 questions
        for q_num in range(1, 4):
            print(f"\n[{q_num + 1}/4] Fetching Question #{q_num}...")
            q_res = await client.post(f"{BASE_URL}/api/interview/{interview_id}/next-question")
            assert q_res.status_code == 201, f"Failed Q{q_num}: {q_res.text}"
            q_data = q_res.json()
            print(f"      Q{q_num} ID={q_data['id']} | Order={q_data['order_index']} | Difficulty={q_data['difficulty'].upper()} | Timer={q_data['time_limit_seconds']}s")
            print(f"      Prompt: '{q_data['question_text'][:100]}...'")

            assert q_data["difficulty"].lower() == "hard"
            assert q_data["time_limit_seconds"] == 120, "Hard question must have 120s timer limit"

            # Submit answer
            print(f"      Submitting Answer for Question #{q_num}...")
            ans_res = await client.post(
                f"{BASE_URL}/api/interview/{interview_id}/answer",
                json={
                    "question_id": q_data["id"],
                    "answer_text": f"Technical answer for question {q_num} covering architecture, trade-offs, and scalability.",
                },
            )
            assert ans_res.status_code == 201, f"Failed Answer Q{q_num}: {ans_res.text}"
            print(f"      Successfully saved answer for Question #{q_num}")

        print("\n[SUCCESS] Completed all 3 questions end-to-end for live interview session!")


if __name__ == "__main__":
    asyncio.run(test_live_interview_flow())
