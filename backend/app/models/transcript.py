"""Transcript model for storing transcribed audio segments."""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.database import Base


class Transcript(Base):
    """
    Model for storing transcribed audio segments.

    Each transcript represents a segment of speech from either the primary
    user or a consented speaker, with associated metadata.
    """

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    speaker_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # 'primary' or 'consented'
    speaker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )  # FK to consented_speakers (null for primary user)
    speaker_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    transcript_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    timestamp_start: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    timestamp_end: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )
    location_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )  # Populated in Slice 5 for RAG
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="transcripts")
