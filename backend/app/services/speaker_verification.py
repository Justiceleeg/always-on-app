"""Speaker verification service using SpeechBrain ECAPA-TDNN model."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import numpy as np
import structlog

logger = structlog.get_logger()

# Only import for type checking to avoid loading heavy ML libs at module import
if TYPE_CHECKING:
    from speechbrain.inference.speaker import SpeakerRecognition


class SpeakerVerificationService:
    """
    Service for speaker verification using SpeechBrain's ECAPA-TDNN model.

    Extracts 192-dimensional speaker embeddings and compares them
    using cosine similarity.
    """

    def __init__(self):
        """Initialize the ECAPA-TDNN speaker recognition model."""
        self._model: SpeakerRecognition | None = None
        self._torch = None
        self._torchaudio = None
        self._device: str | None = None
        logger.info("SpeakerVerificationService initialized (model not yet loaded)")

    def _ensure_loaded(self):
        """Lazy-load torch and torchaudio on first use."""
        if self._torch is None:
            import torch
            import torchaudio

            self._torch = torch
            self._torchaudio = torchaudio
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("PyTorch loaded", device=self._device)

    @property
    def model(self) -> SpeakerRecognition:
        """Lazy-load the model on first use."""
        if self._model is None:
            self._ensure_loaded()
            logger.info("Loading ECAPA-TDNN speaker recognition model...")

            # Apply torchaudio compatibility patches before importing SpeechBrain
            # (SpeechBrain uses deprecated torchaudio APIs removed in 2.2+)
            import app.services._torchaudio_compat  # noqa: F401

            # Import SpeechBrain only when needed (lazy load for faster startup)
            from speechbrain.inference.speaker import SpeakerRecognition

            self._model = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="pretrained_models/spkrec-ecapa-voxceleb",
                run_opts={"device": self._device},
            )
            logger.info("ECAPA-TDNN model loaded successfully")
        return self._model

    def extract_embedding(self, audio_bytes: bytes) -> list[float]:
        """
        Extract a 192-dimensional speaker embedding from audio.

        Args:
            audio_bytes: Raw audio data in WAV format (16kHz, 16-bit mono expected)

        Returns:
            192-dimensional embedding as a list of floats

        Raises:
            ValueError: If audio cannot be processed
        """
        self._ensure_loaded()

        try:
            import soundfile as sf

            # Load audio from bytes using soundfile (more reliable than torchaudio)
            audio_buffer = io.BytesIO(audio_bytes)
            waveform_np, sample_rate = sf.read(audio_buffer)

            # Convert to torch tensor
            # soundfile returns (samples,) for mono or (samples, channels) for stereo
            if waveform_np.ndim == 1:
                # Mono - add channel dimension
                waveform = self._torch.tensor(waveform_np, dtype=self._torch.float32).unsqueeze(0)
            else:
                # Stereo - convert to mono by averaging channels, then add batch dim
                waveform_np = waveform_np.mean(axis=1)
                waveform = self._torch.tensor(waveform_np, dtype=self._torch.float32).unsqueeze(0)
                logger.debug("Converted stereo to mono")

            # Resample to 16kHz if necessary (model expects 16kHz)
            if sample_rate != 16000:
                resampler = self._torchaudio.transforms.Resample(
                    orig_freq=sample_rate, new_freq=16000
                )
                waveform = resampler(waveform)
                logger.debug(
                    "Resampled audio", original_rate=sample_rate, new_rate=16000
                )

            # Extract embedding using SpeechBrain
            embedding = self.model.encode_batch(waveform)

            # Convert to list of floats (embedding is shape [1, 1, 192])
            embedding_list = embedding.squeeze().cpu().numpy().tolist()

            logger.debug(
                "Extracted speaker embedding",
                embedding_dim=len(embedding_list),
            )

            return embedding_list

        except Exception as e:
            logger.error("Failed to extract speaker embedding", error=str(e))
            raise ValueError(f"Failed to extract speaker embedding: {str(e)}")

    def compare_embeddings(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """
        Compare two speaker embeddings using cosine similarity.

        Args:
            embedding1: First 192-dimensional embedding
            embedding2: Second 192-dimensional embedding

        Returns:
            Cosine similarity score between 0 and 1
            (higher means more similar, typically >0.65 for same speaker)
        """
        # Convert to numpy arrays
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)

        # Compute cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Clamp to [0, 1] range (cosine similarity can be negative)
        similarity = max(0.0, min(1.0, float(similarity)))

        logger.debug("Computed embedding similarity", similarity=similarity)

        return similarity

    def verify_speaker(
        self,
        audio_bytes: bytes,
        enrolled_embedding: list[float],
        threshold: float = 0.65,
    ) -> tuple[bool, float]:
        """
        Verify if audio matches an enrolled speaker.

        Args:
            audio_bytes: Raw audio data in WAV format
            enrolled_embedding: 192-dimensional embedding of enrolled speaker
            threshold: Minimum similarity score to consider a match (default 0.65)

        Returns:
            Tuple of (is_match, similarity_score)
        """
        # Extract embedding from audio
        audio_embedding = self.extract_embedding(audio_bytes)

        # Compare with enrolled embedding
        similarity = self.compare_embeddings(audio_embedding, enrolled_embedding)

        is_match = similarity >= threshold

        logger.info(
            "Speaker verification result",
            is_match=is_match,
            similarity=similarity,
            threshold=threshold,
        )

        return is_match, similarity


# Singleton instance for reuse across requests
_speaker_verification_service: SpeakerVerificationService | None = None


def get_speaker_verification_service() -> SpeakerVerificationService:
    """Get or create the singleton SpeakerVerificationService instance."""
    global _speaker_verification_service
    if _speaker_verification_service is None:
        _speaker_verification_service = SpeakerVerificationService()
    return _speaker_verification_service
