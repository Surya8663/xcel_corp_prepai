"""
PrepAI — Startup validation script.

Run this script before starting the server to confirm:
  1. PostgreSQL is reachable
  2. Gemini API key is valid (real API call — NOT mocked)

Usage:
    cd backend
    python scripts/validate_startup.py
"""

from __future__ import annotations

import asyncio
import sys
import os

# Force UTF-8 output so emoji render correctly on Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure the backend package root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import ping_database
from app.core.gemini_client import ping_gemini


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"

OK   = "[OK] "
FAIL = "[!!] "
MSG  = "[>>] "


def banner(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 55}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 55}{RESET}\n")


async def check_database() -> bool:
    print(f"{BOLD}[1/2] Checking PostgreSQL…{RESET}")
    ok = await ping_database()
    if ok:
        print(f"{GREEN}  {OK} PostgreSQL: CONNECTED{RESET}")
    else:
        print(f"{RED}  {FAIL} PostgreSQL: FAILED -- is Docker running? Is DATABASE_URL correct?{RESET}")
    return ok


def check_gemini() -> bool:
    print(f"\n{BOLD}[2/2] Calling Gemini API (REAL call — not mocked)…{RESET}")
    try:
        response = ping_gemini()
        print(f"{GREEN}  {OK} Gemini API: CONNECTED{RESET}")
        print(f"  {MSG} Gemini response text: {BOLD}{response}{RESET}")
        return True
    except Exception as exc:
        print(f"{RED}  {FAIL} Gemini API: FAILED -- {exc}{RESET}")
        print(f"{RED}      Check GEMINI_API_KEY in backend/.env{RESET}")
        return False


async def main() -> None:
    banner("PrepAI — Startup Validation")

    db_ok = await check_database()
    gemini_ok = check_gemini()

    print()
    banner("Summary")
    print(f"  PostgreSQL : {GREEN + 'PASS' + RESET if db_ok   else RED + 'FAIL' + RESET}")
    print(f"  Gemini API : {GREEN + 'PASS' + RESET if gemini_ok else RED + 'FAIL' + RESET}")
    print()

    if db_ok and gemini_ok:
        print(f"{GREEN}{BOLD}  [**] All checks passed -- you're good to start the server!{RESET}\n")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}  [!!] One or more checks failed -- fix the issues above before starting.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
