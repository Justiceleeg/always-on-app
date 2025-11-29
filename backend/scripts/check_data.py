#!/usr/bin/env python3
"""Check transcript data in database."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def check():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not set")
        return

    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession)

    async with async_session() as session:
        # Check users
        print('=== USERS ===')
        result = await session.execute(text('SELECT id, email, name, firebase_uid FROM users'))
        for row in result:
            print(f'  ID: {row[0]}')
            print(f'  Email: {row[1]}, Name: {row[2]}')
            print(f'  Firebase UID: {row[3]}')
            print()

        # Check transcripts
        print('=== TRANSCRIPTS ===')
        result = await session.execute(text('SELECT COUNT(*) FROM transcripts'))
        print(f'Total transcripts: {result.scalar()}')

        result = await session.execute(text('SELECT COUNT(*) FROM transcripts WHERE embedding IS NOT NULL'))
        print(f'With embeddings: {result.scalar()}')

        print('\nSample transcripts:')
        result = await session.execute(text(
            'SELECT user_id, speaker_name, location_name, LEFT(transcript_text, 60) as txt FROM transcripts LIMIT 5'
        ))
        for row in result:
            print(f'  User: {row[0]}')
            print(f'  Speaker: {row[1]}, Location: {row[2]}')
            print(f'  Text: {row[3]}...')
            print()

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(check())
