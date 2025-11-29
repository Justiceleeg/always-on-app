"""Transcription endpoints for processing audio and storing transcripts."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.database import get_db
from app.models.user import User
from app.models.transcript import Transcript
from app.schemas.transcript import (
    TranscribeResponse,
    TranscriptSegment,
    TranscriptResponse,
    TranscriptListResponse,
)
from app.services.firebase_auth import verify_firebase_token, FirebaseUser
from app.services.speaker_verification import get_speaker_verification_service
from app.services.transcription import get_transcription_service
from app.services.embedding import get_embedding_service
from app.services.geocoding import get_geocoding_service
from app.config import get_settings

logger = structlog.get_logger()

router = APIRouter(tags=["transcription"])

# Session gap threshold - new session if gap > 5 minutes
SESSION_GAP_MINUTES = 5


async def get_or_create_session_id(
    db: AsyncSession,
    user_id: UUID,
    timestamp_start: datetime,
) -> UUID:
    """
    Get existing session ID or create a new one.

    A new session is created if:
    - No previous transcripts exist for the user
    - The gap between the last transcript and new one exceeds SESSION_GAP_MINUTES
    """
    # Get the most recent transcript for this user
    result = await db.execute(
        select(Transcript)
        .where(Transcript.user_id == user_id)
        .order_by(desc(Transcript.timestamp_end))
        .limit(1)
    )
    last_transcript = result.scalar_one_or_none()

    if last_transcript is None:
        # No previous transcripts, create new session
        return uuid4()

    # Check if gap exceeds threshold
    gap = timestamp_start - last_transcript.timestamp_end
    if gap > timedelta(minutes=SESSION_GAP_MINUTES):
        return uuid4()

    # Continue existing session
    return last_transcript.session_id


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="WAV audio file to transcribe"),
    timestamp_start: str = Form(..., description="Start timestamp of the audio (ISO format)"),
    timestamp_end: str = Form(..., description="End timestamp of the audio (ISO format)"),
    latitude: float | None = Form(None, description="GPS latitude"),
    longitude: float | None = Form(None, description="GPS longitude"),
    firebase_user: FirebaseUser = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
) -> TranscribeResponse:
    """
    Process an audio chunk for transcription.

    This endpoint:
    1. Extracts a speaker embedding from the audio
    2. Compares against the user's enrolled voiceprint
    3. If match: transcribes via Whisper and stores the transcript
    4. If no match: returns filtered response (speaker not recognized)

    The session_id groups transcripts into logical sessions. A new session
    is created if there's a gap > 5 minutes since the last transcript.
    """
    settings = get_settings()

    # Parse timestamps from ISO format strings
    try:
        # Strip any surrounding quotes (Retrofit may add them)
        ts_start = timestamp_start.strip('"').replace("Z", "+00:00")
        ts_end = timestamp_end.strip('"').replace("Z", "+00:00")
        parsed_timestamp_start = datetime.fromisoformat(ts_start)
        parsed_timestamp_end = datetime.fromisoformat(ts_end)
        # Convert to naive UTC datetimes (remove timezone info for database)
        if parsed_timestamp_start.tzinfo is not None:
            parsed_timestamp_start = parsed_timestamp_start.replace(tzinfo=None)
        if parsed_timestamp_end.tzinfo is not None:
            parsed_timestamp_end = parsed_timestamp_end.replace(tzinfo=None)
    except ValueError as e:
        logger.error("Failed to parse timestamps", error=str(e), start=timestamp_start, end=timestamp_end)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timestamp format: {str(e)}",
        )

    # Convert latitude/longitude to Decimal if provided
    parsed_latitude = Decimal(str(latitude)) if latitude is not None else None
    parsed_longitude = Decimal(str(longitude)) if longitude is not None else None

    # Read audio file
    try:
        audio_bytes = await audio.read()
    except Exception as e:
        logger.error("Failed to read uploaded audio file", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read audio file",
        )

    # Get user from database
    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_user.uid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first.",
        )

    # Check if user has enrolled voiceprint
    if user.voiceprint_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has not enrolled voiceprint. Please complete enrollment first.",
        )

    # Extract speaker embedding and verify against enrolled voiceprint
    try:
        speaker_service = get_speaker_verification_service()
        is_match, similarity = speaker_service.verify_speaker(
            audio_bytes=audio_bytes,
            enrolled_embedding=user.voiceprint_embedding,
            threshold=settings.speaker_verification_threshold,
        )

        logger.info(
            "Speaker verification result",
            user_id=str(user.id),
            is_match=is_match,
            similarity=similarity,
            threshold=settings.speaker_verification_threshold,
        )
    except Exception as e:
        logger.error(
            "Failed to verify speaker",
            user_id=str(user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process audio for speaker verification",
        )

    # If speaker doesn't match, return filtered response
    if not is_match:
        logger.info(
            "Audio filtered - speaker not recognized",
            user_id=str(user.id),
            similarity=similarity,
        )
        return TranscribeResponse(
            processed=True,
            segments=[],
            filtered_segments=1,
            session_id=None,
        )

    # Speaker matches - transcribe the audio
    try:
        transcription_service = get_transcription_service()
        transcript_text = await transcription_service.transcribe(audio_bytes)
    except Exception as e:
        logger.error(
            "Failed to transcribe audio",
            user_id=str(user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transcribe audio",
        )

    # Skip empty transcripts
    if not transcript_text.strip():
        logger.info(
            "Empty transcript - skipping storage",
            user_id=str(user.id),
        )
        return TranscribeResponse(
            processed=True,
            segments=[],
            filtered_segments=0,
            session_id=None,
        )

    # Get or create session ID
    session_id = await get_or_create_session_id(db, user.id, parsed_timestamp_start)

    # Reverse geocode location if coordinates are provided
    location_name = None
    if parsed_latitude is not None and parsed_longitude is not None:
        try:
            geocoding_service = get_geocoding_service()
            location_name = await geocoding_service.reverse_geocode(
                latitude=float(parsed_latitude),
                longitude=float(parsed_longitude),
            )
        except Exception as e:
            # Log but don't fail if geocoding fails
            logger.warning(
                "Failed to reverse geocode location",
                lat=parsed_latitude,
                lon=parsed_longitude,
                error=str(e),
            )

    # Create transcript object first (without embedding)
    transcript = Transcript(
        user_id=user.id,
        session_id=session_id,
        speaker_type="primary",
        speaker_id=None,  # Primary user has no separate speaker_id
        speaker_name=user.name,
        transcript_text=transcript_text,
        timestamp_start=parsed_timestamp_start,
        timestamp_end=parsed_timestamp_end,
        latitude=parsed_latitude,
        longitude=parsed_longitude,
        location_name=location_name,
        embedding=None,
    )

    # Generate embedding for RAG search
    try:
        embedding_service = get_embedding_service()
        embedding_text = embedding_service.prepare_transcript_for_embedding(transcript)
        embedding = await embedding_service.embed_text(embedding_text)
        transcript.embedding = embedding
        logger.info(
            "Generated embedding for transcript",
            user_id=str(user.id),
            embedding_dims=len(embedding),
        )
    except Exception as e:
        # Log but don't fail the transcription if embedding fails
        logger.warning(
            "Failed to generate embedding for transcript",
            user_id=str(user.id),
            error=str(e),
        )
        # transcript.embedding remains None

    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)

    logger.info(
        "Transcript stored successfully",
        transcript_id=str(transcript.id),
        user_id=str(user.id),
        session_id=str(session_id),
        text_length=len(transcript_text),
    )

    # Build response
    segment = TranscriptSegment(
        transcript_id=transcript.id,
        speaker_type="primary",
        speaker_name=user.name,
        text=transcript_text,
        timestamp_start=parsed_timestamp_start,
        timestamp_end=parsed_timestamp_end,
        location_name=location_name,
    )

    return TranscribeResponse(
        processed=True,
        segments=[segment],
        filtered_segments=0,
        session_id=session_id,
    )


@router.get("/transcripts", response_model=TranscriptListResponse)
async def get_transcripts(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of transcripts to return"),
    offset: int = Query(0, ge=0, description="Number of transcripts to skip"),
    session_id: UUID | None = Query(None, description="Filter by session ID"),
    firebase_user: FirebaseUser = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
) -> TranscriptListResponse:
    """
    Get recent transcripts for the authenticated user.

    Transcripts are returned in reverse chronological order (newest first).
    Optionally filter by session_id to get all transcripts from a specific session.
    """
    # Get user from database
    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_user.uid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first.",
        )

    # Build query
    query = select(Transcript).where(Transcript.user_id == user.id)

    if session_id:
        query = query.where(Transcript.session_id == session_id)

    # Get total count
    count_result = await db.execute(
        select(Transcript.id).where(Transcript.user_id == user.id)
    )
    total = len(count_result.all())

    # Get paginated results
    query = query.order_by(desc(Transcript.timestamp_start)).offset(offset).limit(limit)
    result = await db.execute(query)
    transcripts = result.scalars().all()

    # Convert to response models
    transcript_responses = [
        TranscriptResponse(
            id=t.id,
            session_id=t.session_id,
            speaker_type=t.speaker_type,
            speaker_name=t.speaker_name,
            text=t.transcript_text,
            timestamp_start=t.timestamp_start,
            timestamp_end=t.timestamp_end,
            latitude=t.latitude,
            longitude=t.longitude,
            location_name=t.location_name,
            created_at=t.created_at,
        )
        for t in transcripts
    ]

    return TranscriptListResponse(
        transcripts=transcript_responses,
        total=total,
    )
