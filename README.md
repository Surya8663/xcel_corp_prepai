# PrepAI — Adaptive AI Interview Preparation Platform 🎯

> An end-to-end, production-grade AI interview preparation platform built with **FastAPI**, **LangGraph**, **PostgreSQL**, **Next.js**, and **Google Gemini 3.6**.
> 
> Features real-time resume auditing, adaptive mock interview sessions, automated per-answer multi-dimensional scoring, historical progress analytics, and personalized study roadmaps. **No login, no fake data, zero mock fallbacks.**

---

## 🚀 Quick Start (One-Command Docker Setup)

The easiest way to run PrepAI locally with all services (PostgreSQL, FastAPI Backend, Next.js Frontend) fully configured:

### 1. Clone & Configure Secrets

```bash
# Clone repository
git clone https://github.com/your-repo/prepai.git
cd prepai

# Copy environment example to .env
cp .env.example .env     # Linux / macOS
copy .env.example .env   # Windows PowerShell
```

### 2. Set Your Gemini API Key in `.env`

Open `.env` and set your key from [Google AI Studio](https://aistudio.google.com):

```env
GEMINI_API_KEY=AIzaSy...your_real_gemini_api_key_here
```

### 3. Spin Up PrepAI Stack

```bash
docker-compose up --build
```

This single command:
1. Starts **PostgreSQL 16** with automatic health checks (`pg_isready`).
2. Builds and starts **FastAPI Backend** (`http://localhost:8000`), automatically running database table migrations and seeding candidate profile #1.
3. Builds and starts **Next.js Frontend** (`http://localhost:3000`).

Open **http://localhost:3000** in your browser — the application opens directly to the Dashboard (no login required).

---

## 🛠️ Direct Local Development Setup (Without Docker Compose)

If you prefer running services directly on your host machine:

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- PostgreSQL 16 server running locally on port 5432

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.\.venv\Scripts\Activate.ps1    # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edit .env and set GEMINI_API_KEY & DATABASE_URL

# Validate startup & connectivity
python scripts/validate_startup.py

# Start uvicorn dev server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend API will be available at `http://localhost:8000` (Interactive Docs: `http://localhost:8000/docs`).

### 2. Frontend Setup

```bash
cd frontend

# Install packages
npm install

# Start Next.js dev server
npm run dev
```

Frontend application will be available at `http://localhost:3000`.

---

## 📁 Repository Structure

```
XCEL_Corp/
├── docker-compose.yml       # Docker Compose orchestrator for Postgres, Backend, Frontend
├── .env.example             # Master environment configuration template
├── RUNBOOK.md               # Operational Runbook & Reliability Guide
├── README.md                # System documentation
│
├── backend/                 # FastAPI (Python 3.12) Service Layer
│   ├── Dockerfile           # Backend container build specification
│   ├── app/
│   │   ├── main.py          # App entrypoint, CORS, exception handlers, request logging
│   │   ├── api/             # FastAPI routers (health, resume, prep, interview)
│   │   ├── core/            # Config, database engine, rate limiter, middleware
│   │   ├── models/          # SQLAlchemy ORM schemas (8 tables)
│   │   └── services/        # Business logic & LangGraph adaptive question engine
│   ├── scripts/             # Startup validation and DB seed scripts
│   └── requirements.txt
│
└── frontend/                # Next.js 16 (App Router + TypeScript)
    ├── Dockerfile           # Multi-stage production build container
    ├── app/
    │   ├── layout.tsx       # Root layout (Inter font, ErrorBoundary, ToastProvider)
    │   ├── page.tsx         # Tab Router & Dashboard shell
    │   └── globals.css      # Unified design system tokens & CSS primitives
    ├── components/          # Reusable UI components (Navbar, Toast, ErrorBoundary, Cards...)
    └── lib/                 # API client wrapper (`api.ts`)
```

---

## ✨ Core Features & Workflow

1. **Dashboard**: Live candidate stats, quick actions, and recent session feed.
2. **Resume Audit (`components/ResumeAudit.tsx`)**: PDF/DOCX text extraction, structured skill parsing with Gemini, score ring gauge, and actionable feedback.
3. **Prepare / Study Mode (`components/Prepare.tsx`)**: Role and difficulty-tailored practice question generator with detailed AI model answers.
4. **Mock Interview Setup (`components/InterviewSetup.tsx`)**: Configurable session length, format (Technical/HR/Behavioral), and difficulty mode (Easy, Medium, Hard, Adaptive).
5. **LangGraph Adaptive Interview Engine (`components/LiveInterview.tsx`)**: Dynamic ONE-question-at-a-time generation referencing candidate resume skills and prior score trajectory, with 120s countdown timer on Hard questions.
6. **Answer Evaluator**: Rates candidate responses across 4 vectors (Technical, Relevance, Completeness, Clarity) with specific qualitative feedback.
7. **Report Card & Progress Analytics (`components/ReportCard.tsx` & `components/ProgressAnalytics.tsx`)**: Post-interview executive summary, strengths/weaknesses grid, study roadmap, and score trend visualization.

---

## 🔑 Environment Variables & Security

| Variable | Location | Description |
|---|---|---|
| `GEMINI_API_KEY` | `.env` / Container Secret | **Required**. Google AI Studio key (`https://aistudio.google.com`). |
| `DATABASE_URL` | `.env` / Container Env | PostgreSQL connection string (`postgresql+asyncpg://...`). |
| `NEXT_PUBLIC_API_URL` | `.env` / Frontend Env | Public URL for backend API (default: `http://localhost:8000/api/v1`). |

> 🔒 **Security Notice**: `.env` and `*.env.local` files are strictly included in `.gitignore`. Secrets must never be hardcoded into Dockerfiles or committed to version control.

---

## 🩺 Health Check Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/v1/health` | `GET` | Comprehensive status check verifying DB connection and valid Gemini API key. Returns HTTP `200` (OK) or `503` (Degraded). |
| `GET /api/v1/health/db` | `GET` | Verifies PostgreSQL connectivity. |
| `GET /api/v1/health/gemini` | `GET` | Verifies Gemini API connectivity. |

---

## ☁️ Optional Cloud Deployment Guide

To deploy PrepAI to production cloud environments (e.g. AWS ECS / GCP Cloud Run / Render):

### 1. Database (Managed PostgreSQL)
- Provision a managed PostgreSQL instance (e.g. AWS RDS, GCP Cloud SQL, or Supabase).
- Copy the connection string to your Secret Manager.

### 2. Secret Management
- Store `GEMINI_API_KEY` and `DATABASE_URL` in your cloud provider's secret manager:
  - **AWS**: AWS Secrets Manager / SSM Parameter Store.
  - **GCP**: Secret Manager.
  - **Render / Railway**: Environment Secrets Dashboard.

### 3. Container Deployment
- Build and push Docker images to Container Registry (ECR / Artifact Registry):
  ```bash
  docker build -t your-registry/prepai-backend:latest ./backend
  docker build -t your-registry/prepai-frontend:latest ./frontend
  ```
- Deploy backend and frontend containers, referencing environment secrets directly from the secret manager.

---

## 📄 License

MIT License. Built for scalable AI interview preparation.
