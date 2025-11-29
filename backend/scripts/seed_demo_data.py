#!/usr/bin/env python3
"""
Demo data seed script for Frontier Audio MVP.

Creates a demo user with realistic transcripts for demonstration purposes.
Run this against a database with the schema already created.

Usage:
    python scripts/seed_demo_data.py

Environment variables required:
    DATABASE_URL - PostgreSQL connection string
    OPENAI_API_KEY - For generating embeddings (optional, skips if not set)
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete

from app.models.user import User
from app.models.transcript import Transcript


# Demo user configuration
DEMO_USER = {
    "firebase_uid": "demo_user_001",
    "email": "demo@frontieraudio.app",
    "name": "John Smith",
}

# Fake voiceprint embedding (192 dimensions for ECAPA-TDNN)
# In production this would be extracted from actual audio
FAKE_VOICEPRINT = [random.uniform(-1, 1) for _ in range(192)]

# Demo locations (construction/industrial sites)
LOCATIONS = [
    {"name": "Main Job Site, Denver, CO", "lat": 39.7392, "lon": -104.9903},
    {"name": "123 Industrial Way, Aurora, CO", "lat": 39.7294, "lon": -104.8319},
    {"name": "North Building, Denver, CO", "lat": 39.7508, "lon": -104.9997},
    {"name": "Supply Warehouse, Lakewood, CO", "lat": 39.7047, "lon": -105.0814},
    {"name": "Client Office, Boulder, CO", "lat": 40.0150, "lon": -105.2705},
]

# Demo transcript content - realistic construction/field work conversations
DEMO_TRANSCRIPTS = [
    # Day 1 - Monday (6 days ago)
    {
        "text": "Alright, let me check the junction box on the north side. The wiring looks good but we need to replace that breaker panel. Make a note - order 200 amp panel for Thursday delivery.",
        "topic": "electrical",
        "time_offset_days": -6,
        "time_offset_hours": 9,
        "location_idx": 0,
    },
    {
        "text": "Just finished the morning walkthrough. Foundation looks solid. Need to schedule the concrete pour for next week. Weather forecast shows clear skies.",
        "topic": "construction",
        "time_offset_days": -6,
        "time_offset_hours": 10,
        "location_idx": 0,
    },
    {
        "text": "Called the electrical supplier. They can get us the 200 amp panels by Thursday morning. Total cost is about 2400 dollars plus delivery.",
        "topic": "scheduling",
        "time_offset_days": -6,
        "time_offset_hours": 14,
        "location_idx": 1,
    },
    # Day 2 - Tuesday (5 days ago)
    {
        "text": "Met with the inspector this morning. He flagged two items - need to add fire blocking in the east wall and fix the ground fault circuit on the second floor bathroom.",
        "topic": "inspection",
        "time_offset_days": -5,
        "time_offset_hours": 8,
        "location_idx": 0,
    },
    {
        "text": "Fire blocking is installed. Used the metal plates on all penetrations. Should pass reinspection tomorrow.",
        "topic": "construction",
        "time_offset_days": -5,
        "time_offset_hours": 15,
        "location_idx": 0,
    },
    # Day 3 - Wednesday (4 days ago)
    {
        "text": "Passed the reinspection! Inspector signed off on both items. We're clear to proceed with drywall next week.",
        "topic": "inspection",
        "time_offset_days": -4,
        "time_offset_hours": 11,
        "location_idx": 0,
    },
    {
        "text": "Picking up supplies at the warehouse. Need the insulation batts for the north wall and more romex wire. Also grabbing some extra conduit.",
        "topic": "supplies",
        "time_offset_days": -4,
        "time_offset_hours": 13,
        "location_idx": 3,
    },
    {
        "text": "Client meeting went well. They approved the change order for the upgraded HVAC system. That adds about 8000 to the project but better efficiency long term.",
        "topic": "client",
        "time_offset_days": -4,
        "time_offset_hours": 16,
        "location_idx": 4,
    },
    # Day 4 - Thursday (3 days ago)
    {
        "text": "Breaker panels arrived as promised. Good quality units. Starting installation on the main panel this afternoon.",
        "topic": "electrical",
        "time_offset_days": -3,
        "time_offset_hours": 9,
        "location_idx": 0,
    },
    {
        "text": "Main panel is wired and energized. All circuits testing good. Need to label everything tomorrow and do final walkthrough.",
        "topic": "electrical",
        "time_offset_days": -3,
        "time_offset_hours": 17,
        "location_idx": 0,
    },
    # Day 5 - Friday (2 days ago)
    {
        "text": "Doing the panel labeling now. Kitchen circuits on the left, bedrooms on the right, HVAC dedicated circuits at the bottom. Nice clean layout.",
        "topic": "electrical",
        "time_offset_days": -2,
        "time_offset_hours": 8,
        "location_idx": 0,
    },
    {
        "text": "Weekly safety meeting complete. Reminded everyone about hard hat requirements in the active work zones. Zero incidents this week, good job team.",
        "topic": "safety",
        "time_offset_days": -2,
        "time_offset_hours": 10,
        "location_idx": 0,
    },
    {
        "text": "Concrete delivery confirmed for Monday 7 AM. We'll need all hands on deck for the pour. Expecting about 12 yards.",
        "topic": "scheduling",
        "time_offset_days": -2,
        "time_offset_hours": 14,
        "location_idx": 1,
    },
    # Day 6 - Yesterday (1 day ago)
    {
        "text": "Prepping the forms for Monday's pour. Making sure all the rebar is properly tied and spaced. Everything looks good.",
        "topic": "construction",
        "time_offset_days": -1,
        "time_offset_hours": 9,
        "location_idx": 0,
    },
    {
        "text": "Testing all the outlets in the living area. Found one that wasn't wired correctly - fixed it. Everything else passes.",
        "topic": "electrical",
        "time_offset_days": -1,
        "time_offset_hours": 11,
        "location_idx": 0,
    },
    {
        "text": "Lunch break. Thinking about the timeline for next week. After the pour, we need three days for curing before we can continue framing.",
        "topic": "scheduling",
        "time_offset_days": -1,
        "time_offset_hours": 12,
        "location_idx": 2,
    },
    {
        "text": "Ordered the HVAC equipment. Carrier unit with 16 SEER rating. Should arrive next Wednesday. Installation Thursday and Friday.",
        "topic": "scheduling",
        "time_offset_days": -1,
        "time_offset_hours": 15,
        "location_idx": 3,
    },
    # Day 7 - Today
    {
        "text": "Monday morning, concrete truck just arrived. Starting the pour now. Weather is perfect, about 55 degrees and overcast.",
        "topic": "construction",
        "time_offset_days": 0,
        "time_offset_hours": 7,
        "location_idx": 0,
    },
    {
        "text": "Pour is going smoothly. About halfway done. The crew is working efficiently. Should be done by noon.",
        "topic": "construction",
        "time_offset_days": 0,
        "time_offset_hours": 9,
        "location_idx": 0,
    },
    {
        "text": "Concrete pour complete! Everything leveled nicely. Starting the curing process. Set up the moisture barriers and warning tape.",
        "topic": "construction",
        "time_offset_days": 0,
        "time_offset_hours": 11,
        "location_idx": 0,
    },
    {
        "text": "Quick call with the plumber. He's coming Wednesday to rough in the second bathroom. Need to make sure the wall is framed by then.",
        "topic": "scheduling",
        "time_offset_days": 0,
        "time_offset_hours": 13,
        "location_idx": 0,
    },
    {
        "text": "End of day notes. Concrete is setting nicely. Tomorrow we'll check moisture levels and continue with the north wall framing. Good progress this week.",
        "topic": "construction",
        "time_offset_days": 0,
        "time_offset_hours": 16,
        "location_idx": 0,
    },
]


async def create_demo_user(session: AsyncSession) -> User:
    """Create or get the demo user."""
    # Check if demo user exists
    result = await session.execute(
        select(User).where(User.firebase_uid == DEMO_USER["firebase_uid"])
    )
    user = result.scalar_one_or_none()

    if user:
        print(f"Demo user already exists: {user.email}")
        # Update voiceprint if not set
        if user.voiceprint_embedding is None:
            user.voiceprint_embedding = FAKE_VOICEPRINT
            await session.commit()
            print("Updated user with voiceprint embedding")
        return user

    # Create new demo user
    user = User(
        firebase_uid=DEMO_USER["firebase_uid"],
        email=DEMO_USER["email"],
        name=DEMO_USER["name"],
        voiceprint_embedding=FAKE_VOICEPRINT,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    print(f"Created demo user: {user.email}")
    return user


async def clear_demo_transcripts(session: AsyncSession, user_id) -> int:
    """Remove existing demo transcripts."""
    result = await session.execute(
        delete(Transcript).where(Transcript.user_id == user_id)
    )
    await session.commit()
    return result.rowcount


async def generate_embedding(text: str) -> list[float] | None:
    """Generate embedding using OpenAI if API key is set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "text-embedding-3-small",
                    "input": text,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        print(f"Warning: Failed to generate embedding: {e}")
        return None


async def create_demo_transcripts(session: AsyncSession, user: User) -> int:
    """Create demo transcripts for the user."""
    now = datetime.utcnow()
    session_id = uuid4()  # All transcripts in one session for simplicity
    count = 0

    for i, transcript_data in enumerate(DEMO_TRANSCRIPTS):
        location = LOCATIONS[transcript_data["location_idx"]]

        timestamp = now + timedelta(
            days=transcript_data["time_offset_days"],
            hours=transcript_data["time_offset_hours"],
        )

        # Format text for embedding
        formatted_text = f"[{user.name}] {transcript_data['text']}"

        # Generate embedding (or None if no API key)
        embedding = await generate_embedding(formatted_text)

        transcript = Transcript(
            user_id=user.id,
            session_id=session_id,
            speaker_type="primary",
            speaker_id=None,
            speaker_name=user.name,
            transcript_text=transcript_data["text"],
            timestamp_start=timestamp,
            timestamp_end=timestamp + timedelta(seconds=10),
            latitude=Decimal(str(location["lat"])),
            longitude=Decimal(str(location["lon"])),
            location_name=location["name"],
            embedding=embedding,
        )

        session.add(transcript)
        count += 1

        # Progress indicator
        if (i + 1) % 5 == 0:
            print(f"  Created {i + 1}/{len(DEMO_TRANSCRIPTS)} transcripts...")

    await session.commit()
    return count


async def main():
    """Main seed function."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        print("Example: postgresql+asyncpg://user:pass@localhost:5432/frontier_audio")
        sys.exit(1)

    print("Frontier Audio Demo Data Seeder")
    print("=" * 40)
    print(f"Database: {database_url.split('@')[-1]}")  # Hide credentials
    print()

    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create demo user
        print("Creating demo user...")
        user = await create_demo_user(session)

        # Clear existing transcripts
        print("Clearing existing demo transcripts...")
        deleted = await clear_demo_transcripts(session, user.id)
        if deleted > 0:
            print(f"  Deleted {deleted} existing transcripts")

        # Create new transcripts
        print("Creating demo transcripts...")
        created = await create_demo_transcripts(session, user)
        print(f"  Created {created} transcripts")

        print()
        print("=" * 40)
        print("Demo data seeding complete!")
        print()
        print("Demo User Credentials:")
        print(f"  Email: {user.email}")
        print(f"  Firebase UID: {user.firebase_uid}")
        print()
        print("Note: To log in with this user, you'll need to create")
        print("a Firebase user with the email above, or update the")
        print("firebase_uid to match an existing Firebase user.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
