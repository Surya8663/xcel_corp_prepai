"""
Integration Test: Idempotency of /api/interview/{id}/next-question.

Tests that calling /next-question multiple times before answering returns the EXACT same question ID
and order_index, and that answering advances the session to a new question ID.
"""

from __future__ import annotations

import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app


@pytest.mark.asyncio
async def test_next_question_idempotency():
    """
    1. Creates a new interview session.
    2. Calls /next-question twice in a row without submitting an answer.
    3. Asserts both calls return the EXACT same question ID and order_index (order=1).
    4. Submits an answer to the first question.
    5. Calls /next-question again.
    6. Asserts the third call returns a genuinely NEW question (order=2).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create interview session
        create_res = await client.post(
            "/api/interview/create",
            json={
                "role": "Senior Backend Engineer",
                "interview_type": "Technical",
                "difficulty_mode": "Easy",
                "duration_minutes": 15,
                "question_count": 3,
            },
        )
        assert create_res.status_code == 201, f"Create failed: {create_res.text}"
        interview_data = create_res.json()
        interview_id = interview_data["id"]
        assert interview_id > 0

        # 2. Call /next-question Call #1
        q1_res = await client.post(f"/api/interview/{interview_id}/next-question")
        assert q1_res.status_code == 201, f"First next-question failed: {q1_res.text}"
        q1_data = q1_res.json()
        q1_id = q1_data["id"]
        q1_order = q1_data["order_index"]
        assert q1_order == 1

        # 3. Call /next-question Call #2 WITHOUT answering Q1 (Idempotent call)
        q2_res = await client.post(f"/api/interview/{interview_id}/next-question")
        assert q2_res.status_code == 201, f"Second next-question failed: {q2_res.text}"
        q2_data = q2_res.json()
        q2_id = q2_data["id"]
        q2_order = q2_data["order_index"]

        # ASSERTION: Must return the EXACT SAME question ID and order_index
        assert q2_id == q1_id, f"Expected duplicate call to return question ID {q1_id}, but got {q2_id}"
        assert q2_order == q1_order, f"Expected order_index {q1_order}, but got {q2_order}"

        # 4. Submit Answer for Q1
        ans_res = await client.post(
            f"/api/interview/{interview_id}/answer",
            json={
                "question_id": q1_id,
                "answer_text": "I design distributed systems using message queues like Kafka and relational PostgreSQL databases with connection pooling.",
            },
        )
        assert ans_res.status_code == 201, f"Answer submit failed: {ans_res.text}"

        # 5. Call /next-question Call #3 AFTER answering Q1
        q3_res = await client.post(f"/api/interview/{interview_id}/next-question")
        assert q3_res.status_code == 201, f"Third next-question failed: {q3_res.text}"
        q3_data = q3_res.json()
        q3_id = q3_data["id"]
        q3_order = q3_data["order_index"]

        # ASSERTION: Must advance to a NEW question
        assert q3_id != q1_id, "Expected a new question ID after answering Q1, but got the same ID"
        assert q3_order == 2, f"Expected order_index 2, but got {q3_order}"
