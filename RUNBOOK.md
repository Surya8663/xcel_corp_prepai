# PrepAI — Operational Runbook & Reliability Guide

This document covers operational guidance, failure modes, error handling behaviors, and resolution steps for the PrepAI application.

---

## 1. System Architecture Overview

PrepAI consists of two main tiers running locally:
- **Frontend**: Next.js (TypeScript, React, Tailwind / CSS Design System) on `http://localhost:3000`.
- **Backend**: FastAPI (Python 3.12, Async SQLAlchemy, Pydantic v2, LangGraph) on `http://localhost:8000`.
- **Database**: PostgreSQL (connected via `DATABASE_URL` in `backend/.env`).
- **AI Service**: Gemini 2.5/3.6 API via `google-genai` SDK (`GEMINI_API_KEY` in `backend/.env`).

---

## 2. Standard JSON Error Format

All FastAPI endpoints return standardized JSON errors:

```json
{
  "status": "error",
  "status_code": 400,
  "message": "Human-readable error summary for user display",
  "detail": "Technical details or underlying exception message"
}
```

---

## 3. Failure Modes & Operational Procedures

### 🚨 Failure Mode 1: Gemini API Key Missing or Invalid
- **Symptom**: `400 Bad Request` or `500 Internal Server Error` with `API_KEY_INVALID` or `API key not found`.
- **Root Cause**: `GEMINI_API_KEY` is not set or contains invalid credentials in `backend/.env`.
- **Backend Behavior**: `GeminiService` raises `AIServiceError`. Exception middleware catches this and returns `HTTP 503` / `400` JSON error shape with clear user message.
- **Frontend Behavior**: Displays non-alarming toast notification (`⚠️ AI service configuration error: Please check GEMINI_API_KEY`).
- **Resolution**:
  1. Open `backend/.env`.
  2. Ensure `GEMINI_API_KEY=AIzaSy...` contains a valid Google AI Studio key.
  3. Restart the uvicorn server:
     ```powershell
     .\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
     ```

---

### ⏳ Failure Mode 2: Gemini Rate Limit or Quota Exceeded (HTTP 429 / 503)
- **Symptom**: `HTTP 429 Too Many Requests` or `RESOURCE_EXHAUSTED`.
- **Root Cause**: Free tier limit (15–20 requests per minute) hit during fast automated testing or batch operations.
- **Backend Behavior**: `GeminiService` automatically executes 3 retries with exponential backoff (2s, 4s, 8s). If all retries fail, it raises `AIRateLimitError` honestly — **never falling back to fake/fabricated data**.
- **Frontend Behavior**: Surfaced to candidate in toast: `"AI rate limit exceeded. Please wait a moment and retry."`
- **Resolution**:
  1. Wait 30–60 seconds before triggering another generation call.
  2. Rate limiter in `app/core/rate_limiter.py` protects backend quota by enforcing 15 RPM per client endpoint.

---

### 🗄️ Failure Mode 3: PostgreSQL Database Connection Loss
- **Symptom**: `HTTP 500` or connection refusal on startup (`[DB] PostgreSQL: FAILED`).
- **Root Cause**: PostgreSQL service stopped, port blocked, or bad credentials in `DATABASE_URL`.
- **Backend Behavior**: Startup ping logs failure. Requests attempting DB access raise SQLAlchemy `OperationalError`, caught by global exception handler to return clean 500 error without leaking raw SQL or connection strings.
- **Frontend Behavior**: Shows error banner or toast notification (`"Failed to connect to backend server"`).
- **Resolution**:
  1. Check PostgreSQL service status in Windows Services (`postgresql-x64-16` or similar).
  2. Verify credentials in `backend/.env`: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/prepai`.
  3. Test DB ping manually:
     ```powershell
     .\.venv\Scripts\python.exe -c "import asyncio; from app.core.database import ping_database; print(asyncio.run(ping_database()))"
     ```

---

### 📋 Failure Mode 4: Malformed Request / Input Validation Error (HTTP 400)
- **Symptom**: `HTTP 400 Bad Request` with `Validation Error in 'role': field required`.
- **Root Cause**: Request payload missing required fields, role string out of bounds (<2 or >100 chars), invalid question count, or invalid file type.
- **Backend Behavior**: Pydantic schema validation catches malformed request before DB or AI calls execute. `validation_exception_handler` returns structured HTTP 400 JSON.
- **Resolution**: Adjust request payload parameters to match Pydantic schema constraints.

---

### 📄 Failure Mode 5: PDF / DOCX Text Extraction Error
- **Symptom**: `HTTP 400 Bad Request` with `"Unable to extract readable text from document."`
- **Root Cause**: Uploaded file is corrupted, password-protected, or image-only scanned PDF without text layer.
- **Backend Behavior**: `extractor.py` raises `ExtractionError`. Endpoint returns 400 with guidance to upload a text-selectable PDF or DOCX file.
- **Resolution**: Export document as clean PDF with selectable text or DOCX format.

---

## 4. Verification & Diagnostics Commands

### Check Health & Connectivity
```powershell
# Health check endpoint
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" | ConvertTo-Json

# Candidate progress endpoint
Invoke-RestMethod -Uri "http://localhost:8000/api/candidate/progress" | ConvertTo-Json
```

### Inspect Backend Server Logs
Logs are output in structured format: `TIMESTAMP | LEVEL | MODULE — MESSAGE`.
Check uvicorn terminal output or log files in `.system_generated/tasks/`.
