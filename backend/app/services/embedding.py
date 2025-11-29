"""Embedding service using OpenAI text-embedding-3-small API."""

from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from app.config import get_settings
from app.models.transcript import Transcript

logger = structlog.get_logger()


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI text-embedding-3-small.
    Produces 1536-dimensional embeddings for semantic search.
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self, openai_api_key: str | None = None):
        """
        Initialize the embedding service.

        Args:
            openai_api_key: OpenAI API key. If not provided, uses config.
        """
        settings = get_settings()
        api_key = openai_api_key or settings.openai_api_key

        if not api_key:
            raise ValueError("OpenAI API key is required for embeddings")

        self._client = AsyncOpenAI(api_key=api_key)
        logger.info("EmbeddingService initialized", model=self.EMBEDDING_MODEL)

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI text-embedding-3-small.

        Args:
            text: Text to embed

        Returns:
            1536-dimensional embedding vector

        Raises:
            ValueError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            logger.info(
                "Generating embedding",
                text_length=len(text),
                text_preview=text[:100] if len(text) > 100 else text,
            )

            response = await self._client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text,
            )

            embedding = response.data[0].embedding

            logger.info(
                "Embedding generated successfully",
                dimensions=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise ValueError(f"Failed to generate embedding: {str(e)}")

    def prepare_transcript_for_embedding(self, transcript: Transcript) -> str:
        """
        Format transcript for embedding with contextual information.

        Format: "[Speaker] text (time context)"
        e.g., "[You] Check the junction box on north side (morning, January 15, 2025)"

        Args:
            transcript: Transcript model instance

        Returns:
            Formatted text ready for embedding
        """
        # Get time context
        time_context = self._format_time_context(transcript.timestamp_start)

        # Build the formatted text
        parts = [f"[{transcript.speaker_name}]", transcript.transcript_text]

        # Add time context
        if time_context:
            parts.append(f"({time_context})")

        # Add location if available
        if transcript.location_name:
            parts[-1] = parts[-1].rstrip(")") + f", {transcript.location_name})"

        return " ".join(parts)

    def _format_time_context(self, timestamp) -> str:
        """
        Format timestamp into human-readable time context.

        Args:
            timestamp: datetime object

        Returns:
            Formatted string like "morning, January 15, 2025"
        """
        if not timestamp:
            return ""

        # Determine time of day
        hour = timestamp.hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"

        # Format date
        date_str = timestamp.strftime("%B %d, %Y")

        return f"{time_of_day}, {date_str}"


# Singleton instance for reuse across requests
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
