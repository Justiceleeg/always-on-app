"""Schemas for chat endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Request to the chat endpoint."""

    message: str = Field(..., min_length=1, description="User's message")
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation",
    )
    timezone: str = Field(
        default="UTC",
        description="Client's timezone (e.g., 'America/Los_Angeles')",
    )


class CitationSource(BaseModel):
    """Citation metadata for a transcript source."""

    transcript_id: UUID
    speaker_name: str
    timestamp: datetime
    location: str | None = None
    text_snippet: str = Field(..., description="Relevant excerpt from the transcript")

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Non-streaming response from the chat endpoint."""

    response: str
    citations: list[CitationSource] = Field(default_factory=list)
