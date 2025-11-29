#!/usr/bin/env python3
"""
Seed test transcripts for RAG testing.

Usage:
    python scripts/seed_test_data.py --user-email <email>
    python scripts/seed_test_data.py --user-email <email> --cleanup  # Remove test data

Requires DATABASE_URL and OPENAI_API_KEY environment variables.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.transcript import Transcript
from app.services.embedding import EmbeddingService
from app.database import Base

# Test transcripts - realistic construction/job site conversations
TEST_TRANSCRIPTS = [
    {
        "text": "I checked the junction box on the north side of the building. The wiring looks good but we need to replace the circuit breaker. It's rated for 15 amps but we need at least 20 for the new equipment.",
        "hours_ago": 2,
        "location": "North Building",
    },
    {
        "text": "Had a call with the client about the timeline. They want the electrical work done by Friday. I told them we can probably finish the main panel tomorrow and the outlets the day after.",
        "hours_ago": 4,
        "location": "Office",
    },
    {
        "text": "The concrete pour went well this morning. We used about 12 cubic yards. The weather held up and we should be able to remove the forms in about three days.",
        "hours_ago": 6,
        "location": "Foundation Site",
    },
    {
        "text": "Meeting with the building inspector tomorrow at 9 AM. Need to have all the permits ready and make sure the fire suppression system documentation is complete.",
        "hours_ago": 24,  # Yesterday
        "location": "Main Office",
    },
    {
        "text": "Ordered the new HVAC units from Johnson Supply. They should arrive next Tuesday. Total cost came to $4,500 which is under budget by about $300.",
        "hours_ago": 25,  # Yesterday
        "location": "Office",
    },
    {
        "text": "The drywall crew finished the second floor today. Quality looks good. We can start priming tomorrow if the mud is dry. Should check moisture levels first thing in the morning.",
        "hours_ago": 28,  # Yesterday
        "location": "Second Floor",
    },
    {
        "text": "Safety meeting with the team. Reminded everyone about proper ladder usage and fall protection. No incidents this week which is great. Keep it up.",
        "hours_ago": 48,  # 2 days ago
        "location": "Break Room",
    },
    {
        "text": "Troubleshooting the plumbing issue in unit 3B. Found the leak - it's coming from a cracked fitting under the sink. Easy fix, should take about 30 minutes.",
        "hours_ago": 72,  # 3 days ago
        "location": "Unit 3B",
    },
    {
        "text": "Client wants to add two more outlets in the garage. Need to check if the existing circuit can handle the load or if we need to run a new line from the panel.",
        "hours_ago": 96,  # 4 days ago
        "location": "Garage",
    },
    {
        "text": "Wrapped up the week with a team review. Project is on schedule. Budget is looking good. Main focus next week is finishing the electrical and starting the trim work.",
        "hours_ago": 120,  # 5 days ago
        "location": "Office",
    },
]


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def seed_transcripts(session: AsyncSession, user: User, embedding_service: EmbeddingService):
    """Create test transcripts with embeddings."""
    session_id = uuid4()  # All test transcripts in one session
    now = datetime.utcnow()

    print(f"\nSeeding {len(TEST_TRANSCRIPTS)} test transcripts for {user.name} ({user.email})...")

    for i, data in enumerate(TEST_TRANSCRIPTS):
        timestamp = now - timedelta(hours=data["hours_ago"])

        # Create transcript
        transcript = Transcript(
            user_id=user.id,
            session_id=session_id,
            speaker_type="primary",
            speaker_id=None,
            speaker_name=user.name,
            transcript_text=data["text"],
            timestamp_start=timestamp,
            timestamp_end=timestamp + timedelta(seconds=30),
            latitude=None,
            longitude=None,
            location_name=data["location"],
            embedding=None,
        )

        # Generate embedding
        embedding_text = embedding_service.prepare_transcript_for_embedding(transcript)
        embedding = await embedding_service.embed_text(embedding_text)
        transcript.embedding = embedding

        session.add(transcript)
        print(f"  [{i+1}/{len(TEST_TRANSCRIPTS)}] {data['location']}: {data['text'][:50]}...")

    await session.commit()
    print(f"\nCreated {len(TEST_TRANSCRIPTS)} test transcripts with embeddings.")
    print(f"Session ID: {session_id}")


async def cleanup_test_data(session: AsyncSession, user: User):
    """Remove all transcripts for a user (use with caution!)."""
    result = await session.execute(
        select(Transcript).where(Transcript.user_id == user.id)
    )
    transcripts = result.scalars().all()
    count = len(transcripts)

    if count == 0:
        print(f"No transcripts found for {user.email}")
        return

    confirm = input(f"Delete {count} transcripts for {user.email}? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return

    await session.execute(
        delete(Transcript).where(Transcript.user_id == user.id)
    )
    await session.commit()
    print(f"Deleted {count} transcripts.")


async def main():
    parser = argparse.ArgumentParser(description="Seed test transcripts for RAG testing")
    parser.add_argument("--user-email", required=True, help="Email of the user to seed data for")
    parser.add_argument("--cleanup", action="store_true", help="Remove test data instead of seeding")
    args = parser.parse_args()

    # Get database URL
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find user
        user = await get_user_by_email(session, args.user_email)
        if not user:
            print(f"Error: User with email '{args.user_email}' not found")
            sys.exit(1)

        if args.cleanup:
            await cleanup_test_data(session, user)
        else:
            # Check for OpenAI API key
            if not os.environ.get("OPENAI_API_KEY"):
                print("Error: OPENAI_API_KEY environment variable not set")
                sys.exit(1)

            embedding_service = EmbeddingService()
            await seed_transcripts(session, user, embedding_service)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
