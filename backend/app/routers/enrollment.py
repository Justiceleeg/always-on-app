"""Voice enrollment endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models.user import User
from app.schemas.enrollment import EnrollResponse
from app.services.firebase_auth import verify_firebase_token, FirebaseUser
from app.services.speaker_verification import get_speaker_verification_service
from app.services.audio_validation import (
    validate_enrollment_audio,
    AudioValidationError,
)

logger = structlog.get_logger()

router = APIRouter(tags=["enrollment"])


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_voice(
    audio: UploadFile = File(..., description="WAV audio file (15-30 seconds)"),
    firebase_user: FirebaseUser = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
) -> EnrollResponse:
    """
    Enroll the user's voiceprint for speaker verification.

    Accepts a WAV audio file (15-30 seconds) and extracts a 192-dimensional
    speaker embedding using the ECAPA-TDNN model. The embedding is stored
    in the user's record for later speaker verification.

    Requirements:
    - Audio format: WAV (PCM)
    - Duration: 15-30 seconds
    - The audio should contain clear speech from the user
    """
    # Read audio file
    try:
        audio_bytes = await audio.read()
    except Exception as e:
        logger.error("Failed to read uploaded audio file", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read audio file",
        )

    # Validate audio format and duration
    try:
        audio_info = validate_enrollment_audio(audio_bytes)
        logger.info(
            "Enrollment audio validated",
            duration=audio_info["duration_seconds"],
            sample_rate=audio_info["sample_rate"],
            channels=audio_info["channels"],
        )
    except AudioValidationError as e:
        logger.warning(
            "Enrollment audio validation failed",
            error=e.message,
            error_code=e.error_code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
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

    # Extract speaker embedding
    try:
        speaker_service = get_speaker_verification_service()
        embedding = speaker_service.extract_embedding(audio_bytes)

        if len(embedding) != 192:
            raise ValueError(f"Unexpected embedding dimension: {len(embedding)}")

        logger.info(
            "Speaker embedding extracted",
            user_id=str(user.id),
            embedding_dim=len(embedding),
        )
    except Exception as e:
        logger.error(
            "Failed to extract speaker embedding",
            user_id=str(user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process audio for speaker verification",
        )

    # Update user's voiceprint embedding
    user.voiceprint_embedding = embedding
    await db.commit()

    logger.info(
        "Voice enrollment completed",
        user_id=str(user.id),
        was_update=user.voiceprint_embedding is not None,
    )

    return EnrollResponse(
        success=True,
        message="Voiceprint enrolled successfully",
    )
