"""
End-to-End Test Script for Prep Questions Generation & DB Persistence.

Calls:
  1. POST /api/v1/prep/generate -> Generates 5 questions via Gemini AI & stores in prep_questions table.
  2. GET /api/v1/prep/questions -> Fetches stored questions from DB.
  3. GET /api/v1/prep/filters   -> Verifies distinct roles and topics filter endpoints.
"""

from __future__ import annotations

import sys
import time
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GEN_URL = "http://localhost:8000/api/v1/prep/generate"
LIST_URL = "http://localhost:8000/api/v1/prep/questions"
FILTERS_URL = "http://localhost:8000/api/v1/prep/filters"


def run_e2e_prep_test():
    print("=" * 60)
    print("  PrepAI — Prep Questions Generation & DB Storage Test")
    print("=" * 60)

    # 1. Generate questions batch 1
    print("\n[1/4] Triggering POST /api/v1/prep/generate (Role: Senior Backend Engineer)...")
    payload_1 = {
        "role": "Senior Backend Engineer",
        "topic": "System Design & Distributed Caching",
        "difficulty": "medium",
        "count": 3
    }
    
    res1 = None
    for attempt in range(1, 4):
        t0 = time.time()
        res1 = requests.post(GEN_URL, json=payload_1, timeout=60)
        elapsed1 = time.time() - t0
        print(f"      Attempt {attempt} - Status Code: {res1.status_code} ({elapsed1:.2f}s)")
        if res1.status_code == 201:
            break
        elif res1.status_code == 503:
            print("      Rate limited by Gemini quota. Waiting 20 seconds before retry...")
            time.sleep(20)
        else:
            break

    if res1.status_code != 201:
        print(f"ERROR: Generation failed! Body: {res1.text}")
        sys.exit(1)

    batch1 = res1.json()
    print(f"      Successfully generated {len(batch1)} questions!")
    print(f"      Sample Question 1: '{batch1[0]['question_text'][:80]}...'")
    print(f"      Model Answer len : {len(batch1[0]['model_answer_text'])} chars")

    # 2. Generate questions batch 2 (different role & difficulty)
    print("\n[2/4] Triggering POST /api/v1/prep/generate (Role: Full Stack Engineer)...")
    payload_2 = {
        "role": "Full Stack Engineer",
        "topic": "React State & Next.js SSR",
        "difficulty": "hard",
        "count": 2
    }
    t0 = time.time()
    res2 = requests.post(GEN_URL, json=payload_2, timeout=60)
    elapsed2 = time.time() - t0

    print(f"      Response Status Code: {res2.status_code} ({elapsed2:.2f}s)")
    if res2.status_code != 201:
        print(f"ERROR: Batch 2 generation failed! Body: {res2.text}")
        sys.exit(1)

    batch2 = res2.json()
    print(f"      Successfully generated {len(batch2)} questions for Batch 2!")

    # 3. Fetch stored questions from PostgreSQL
    print("\n[3/4] Fetching stored questions from DB (GET /api/v1/prep/questions)...")
    res_list = requests.get(LIST_URL, timeout=10)
    assert res_list.status_code == 200, f"Expected 200, got {res_list.status_code}"
    all_stored = res_list.json()
    print(f"      Total questions stored in prep_questions table: {len(all_stored)}")

    # 4. Check Filters Endpoint
    print("\n[4/4] Checking distinct filters endpoint (GET /api/v1/prep/filters)...")
    res_filters = requests.get(FILTERS_URL, timeout=10)
    assert res_filters.status_code == 200
    filters_data = res_filters.json()
    print(f"      Available Roles  : {filters_data.get('roles')}")
    print(f"      Available Topics : {filters_data.get('topics')}")

    # Assertions
    assert len(all_stored) >= len(batch1) + len(batch2), "Database should store all generated questions"
    assert batch1[0]['question_text'] != batch2[0]['question_text'], "Different calls should generate distinct questions"

    print("\nSUCCESS: End-to-end Prep Questions test PASSED cleanly!")
    print("=" * 60)


if __name__ == "__main__":
    run_e2e_prep_test()
