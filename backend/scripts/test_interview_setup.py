import time
import requests

BASE_URL = "http://localhost:8000"

def test_interview_setup_endpoints():
    print("=" * 60)
    print("  PrepAI — Interview Setup & JD Endpoint Test")
    print("=" * 60)

    # 1. Test POST /api/job-description
    print("\n[1/4] Testing POST /api/job-description...")
    jd_payload = {
        "raw_text": (
            "We are seeking a Senior Backend Engineer proficient in Python, FastAPI, PostgreSQL, "
            "and Redis. Responsible for building high-concurrency RESTful APIs and optimizing DB queries."
        )
    }
    res_jd = requests.post(f"{BASE_URL}/api/job-description", json=jd_payload, timeout=60)
    print(f"      Status Code: {res_jd.status_code}")
    assert res_jd.status_code == 201, f"Expected 201, got {res_jd.status_code}: {res_jd.text}"
    jd_data = res_jd.json()
    jd_id = jd_data["id"]
    print(f"      Created JD ID={jd_id}")
    print(f"      Parsed Required Skills: {jd_data.get('parsed_required_skills_json', {}).get('required_skills', [])}")

    # 2. Test GET /api/job-descriptions
    print("\n[2/4] Testing GET /api/job-descriptions...")
    res_jds = requests.get(f"{BASE_URL}/api/job-descriptions", timeout=10)
    print(f"      Status Code: {res_jds.status_code}")
    assert res_jds.status_code == 200
    jds_list = res_jds.json()
    print(f"      Fetched {len(jds_list)} stored job descriptions.")

    # 3. Test POST /api/interview/create
    print("\n[3/4] Testing POST /api/interview/create...")
    interview_payload = {
        "role": "Senior Backend Engineer",
        "interview_type": "Technical",
        "difficulty_mode": "Adaptive",
        "duration_minutes": 30,
        "question_count": 5,
        "job_description_id": jd_id,
    }
    res_int = requests.post(f"{BASE_URL}/api/interview/create", json=interview_payload, timeout=10)
    print(f"      Status Code: {res_int.status_code}")
    assert res_int.status_code == 201, f"Expected 201, got {res_int.status_code}: {res_int.text}"
    int_data = res_int.json()
    interview_id = int_data["id"]
    print(f"      Created Interview ID={interview_id}")
    print(f"      Role: '{int_data['role']}' | Type: '{int_data['interview_type']}' | Mode: '{int_data['difficulty_mode']}'")
    print(f"      Status: '{int_data['status']}'")
    assert int_data["status"] == "not_started"
    assert int_data["difficulty_mode"] == "adaptive"

    # 4. Test GET /api/interview/{id}
    print("\n[4/4] Testing GET /api/interview/{interview_id}...")
    res_get = requests.get(f"{BASE_URL}/api/interview/{interview_id}", timeout=10)
    print(f"      Status Code: {res_get.status_code}")
    assert res_get.status_code == 200
    get_data = res_get.json()
    print(f"      Retrieved Interview ID={get_data['id']} with status='{get_data['status']}'")

    print("\n[SUCCESS] ALL INTERVIEW SETUP ENDPOINT TESTS PASSED!")

if __name__ == "__main__":
    test_interview_setup_endpoints()
