"""
PrepAI — Database Seed Script.

Creates exactly ONE candidate_profile row (the "current user" for this
single-user local application).  Idempotent — safe to run multiple times;
will skip seeding if a profile already exists.

NO fake resumes, questions, or interviews are seeded here.
All actual data is created through real app usage only.

Usage:
    cd backend
    .venv\\Scripts\\Activate.ps1           # (Windows PowerShell)
    python scripts/seed_db.py
"""

from __future__ import annotations

import asyncio
import os
import sys

# Ensure backend root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import CandidateProfile

# ── Configuration ─────────────────────────────────────────────────────────────
CANDIDATE_NAME = "PrepAI User"   # Change this to your real name if desired

# ── ASCII-safe output helpers (Windows PowerShell compatible) ─────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESET = "\033[0m"
GREEN = "\033[92m"
CYAN  = "\033[96m"
BOLD  = "\033[1m"

def banner(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 50}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 50}{RESET}\n")


async def seed() -> None:
    banner("PrepAI Database Seed")

    async with AsyncSessionLocal() as session:
        # Check if a profile already exists
        existing = await session.execute(select(CandidateProfile).limit(1))
        profile = existing.scalar_one_or_none()

        if profile is not None:
            print(f"  [--] Seed skipped — candidate_profile already exists:")
            print(f"       id={profile.id}  name={profile.name!r}  created_at={profile.created_at}")
            print()
            return

        # Insert the single candidate profile
        new_profile = CandidateProfile(name=CANDIDATE_NAME)
        session.add(new_profile)
        await session.commit()
        await session.refresh(new_profile)

        print(f"  {GREEN}[OK] Created candidate_profile:{RESET}")
        print(f"       id         = {new_profile.id}")
        print(f"       name       = {new_profile.name!r}")
        print(f"       created_at = {new_profile.created_at}")
        print()
        print(f"  {BOLD}Seed complete.  No fake data was inserted.{RESET}")
        print(f"  All resumes, questions, and interviews will be created through real app usage.\n")


if __name__ == "__main__":
    asyncio.run(seed())
