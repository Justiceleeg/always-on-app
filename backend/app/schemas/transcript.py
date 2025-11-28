"""Schemas for transcription endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """A single transcribed segment."""

    transcript_id: UUID
    speaker_type: str  # 'primary' or 'consented'
    speaker_name: str
    text: str
    timestamp_start: datetime
    timestamp_end: datetime


class TranscribeResponse(BaseModel):
    """Response from the transcribe endpoint."""

    processed: bool
    segments: list[TranscriptSegment] = Field(default_factory=list)
    filtered_segments: int = 0  # Number of segments filtered out (unknown speakers)
    session_id: UUID | None = None


class TranscriptResponse(BaseModel):
    """Response for a single transcript."""

    id: UUID
    session_id: UUID
    speaker_type: str
    speaker_name: str
    text: str
    timestamp_start: datetime
    timestamp_end: datetime
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    location_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptListResponse(BaseModel):
    """Response for listing transcripts."""

    transcripts: list[TranscriptResponse]
    total: int
