import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Interview, InterviewType, DifficultyMode, InterviewStatus

async def test():
    async with AsyncSessionLocal() as session:
        interview = Interview(
            candidate_id=1,
            role="Senior Backend Engineer",
            interview_type=InterviewType.TECHNICAL,
            difficulty_mode=DifficultyMode.MEDIUM,
            duration_minutes=30,
            status=InterviewStatus.SCHEDULED,
        )
        session.add(interview)
        await session.commit()
        print("Success! Created interview id:", interview.id, "status:", interview.status.value)

if __name__ == "__main__":
    asyncio.run(test())
