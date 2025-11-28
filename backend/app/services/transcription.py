"""Transcription service using OpenAI Whisper API."""

from __future__ import annotations

import io
import structlog
from openai import AsyncOpenAI

from app.config import get_settings

logger = structlog.get_logger()


class TranscriptionService:
    """
    Service for transcribing audio using OpenAI Whisper API.
    """

    def __init__(self, openai_api_key: str | None = None):
        """
        Initialize the transcription service.

        Args:
            openai_api_key: OpenAI API key. If not provided, uses config.
        """
        settings = get_settings()
        api_key = openai_api_key or settings.openai_api_key

        if not api_key:
            raise ValueError("OpenAI API key is required for transcription")

        self._client = AsyncOpenAI(api_key=api_key)
        logger.info("TranscriptionService initialized")

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """
        Transcribe audio using OpenAI Whisper API.

        Args:
            audio_bytes: Raw audio data in WAV format
            language: Language code (default: "en")

        Returns:
            Transcribed text

        Raises:
            ValueError: If transcription fails
        """
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"

            logger.info(
                "Sending audio to Whisper",
                audio_size_bytes=len(audio_bytes),
            )

            # Call Whisper API
            response = await self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="text",
            )

            transcript = response.strip() if isinstance(response, str) else str(response).strip()

            # Filter out common Whisper hallucinations
            transcript = self._filter_hallucinations(transcript)

            logger.info(
                "Audio transcribed successfully",
                transcript_length=len(transcript),
                transcript_preview=transcript[:100] if transcript else "(empty)",
            )

            return transcript

        except Exception as e:
            logger.error("Failed to transcribe audio", error=str(e))
            raise ValueError(f"Failed to transcribe audio: {str(e)}")

    def _filter_hallucinations(self, text: str) -> str:
        """
        Filter out common Whisper hallucinations.

        Returns empty string if the text appears to be a hallucination.
        """
        if not text:
            return ""

        text_lower = text.lower()

        # Common hallucination patterns
        hallucination_patterns = [
            "www.",
            ".com",
            ".org",
            ".net",
            "subscribe",
            "like and subscribe",
            "thanks for watching",
            "thank you for watching",
            "see you next time",
            "visit our website",
            "check out our",
            "[music]",
            "♪",
            "satsang",
            "mesmerism",
            "monastery",
        ]

        for pattern in hallucination_patterns:
            if pattern in text_lower:
                logger.debug("Filtered hallucination", text=text)
                return ""

        # Filter very short responses that are likely hallucinations
        # Single word responses like "You", "The", etc.
        words = text.split()
        if len(words) <= 2 and len(text) < 15:
            logger.debug("Filtered short response", text=text)
            return ""

        return text


# Singleton instance for reuse across requests
_transcription_service: TranscriptionService | None = None


def get_transcription_service() -> TranscriptionService:
    """Get or create the singleton TranscriptionService instance."""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service
