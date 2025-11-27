"""Audio validation utilities for enrollment and transcription."""

import io
import struct
import structlog

logger = structlog.get_logger()


class AudioValidationError(Exception):
    """Exception raised when audio validation fails."""

    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def validate_wav_audio(
    audio_bytes: bytes,
    min_duration_seconds: float = 15.0,
    max_duration_seconds: float = 30.0,
    expected_sample_rate: int | None = None,
) -> dict:
    """
    Validate WAV audio file format and duration.

    Args:
        audio_bytes: Raw audio data
        min_duration_seconds: Minimum required duration (default 15 seconds)
        max_duration_seconds: Maximum allowed duration (default 30 seconds)
        expected_sample_rate: If provided, validate sample rate matches

    Returns:
        Dictionary with audio metadata:
        - sample_rate: int
        - channels: int
        - bits_per_sample: int
        - duration_seconds: float
        - num_samples: int

    Raises:
        AudioValidationError: If validation fails
    """
    if len(audio_bytes) < 44:
        raise AudioValidationError(
            "Audio file too small to be a valid WAV file",
            "INVALID_FORMAT",
        )

    try:
        # Parse WAV header
        header = io.BytesIO(audio_bytes)

        # RIFF header
        riff = header.read(4)
        if riff != b"RIFF":
            raise AudioValidationError(
                "Invalid WAV file: missing RIFF header",
                "INVALID_FORMAT",
            )

        # Skip file size
        header.read(4)

        # WAVE format
        wave = header.read(4)
        if wave != b"WAVE":
            raise AudioValidationError(
                "Invalid WAV file: missing WAVE format marker",
                "INVALID_FORMAT",
            )

        # Find fmt chunk
        fmt_found = False
        data_found = False
        sample_rate = 0
        channels = 0
        bits_per_sample = 0
        data_size = 0

        while header.tell() < len(audio_bytes):
            chunk_id = header.read(4)
            if len(chunk_id) < 4:
                break

            chunk_size = struct.unpack("<I", header.read(4))[0]

            if chunk_id == b"fmt ":
                fmt_found = True
                audio_format = struct.unpack("<H", header.read(2))[0]

                # Only support PCM (1) and IEEE float (3)
                if audio_format not in (1, 3):
                    raise AudioValidationError(
                        f"Unsupported audio format: {audio_format}. Only PCM WAV is supported.",
                        "UNSUPPORTED_FORMAT",
                    )

                channels = struct.unpack("<H", header.read(2))[0]
                sample_rate = struct.unpack("<I", header.read(4))[0]
                header.read(4)  # byte rate
                header.read(2)  # block align
                bits_per_sample = struct.unpack("<H", header.read(2))[0]

                # Skip any extra format bytes
                remaining = chunk_size - 16
                if remaining > 0:
                    header.read(remaining)

            elif chunk_id == b"data":
                data_found = True
                data_size = chunk_size
                break
            else:
                # Skip unknown chunk
                header.read(chunk_size)

        if not fmt_found:
            raise AudioValidationError(
                "Invalid WAV file: missing fmt chunk",
                "INVALID_FORMAT",
            )

        if not data_found:
            raise AudioValidationError(
                "Invalid WAV file: missing data chunk",
                "INVALID_FORMAT",
            )

        # Calculate duration
        bytes_per_sample = bits_per_sample // 8
        num_samples = data_size // (channels * bytes_per_sample)
        duration_seconds = num_samples / sample_rate

        logger.debug(
            "Parsed WAV audio",
            sample_rate=sample_rate,
            channels=channels,
            bits_per_sample=bits_per_sample,
            duration_seconds=round(duration_seconds, 2),
            data_size=data_size,
        )

        # Validate sample rate if specified
        if expected_sample_rate and sample_rate != expected_sample_rate:
            raise AudioValidationError(
                f"Invalid sample rate: {sample_rate}Hz. Expected {expected_sample_rate}Hz.",
                "INVALID_SAMPLE_RATE",
            )

        # Validate duration
        if duration_seconds < min_duration_seconds:
            raise AudioValidationError(
                f"Audio too short: {duration_seconds:.1f}s. Minimum required: {min_duration_seconds:.1f}s.",
                "AUDIO_TOO_SHORT",
            )

        if duration_seconds > max_duration_seconds:
            raise AudioValidationError(
                f"Audio too long: {duration_seconds:.1f}s. Maximum allowed: {max_duration_seconds:.1f}s.",
                "AUDIO_TOO_LONG",
            )

        return {
            "sample_rate": sample_rate,
            "channels": channels,
            "bits_per_sample": bits_per_sample,
            "duration_seconds": duration_seconds,
            "num_samples": num_samples,
        }

    except AudioValidationError:
        raise
    except Exception as e:
        logger.error("Failed to parse WAV audio", error=str(e))
        raise AudioValidationError(
            f"Failed to parse audio file: {str(e)}",
            "PARSE_ERROR",
        )


def validate_enrollment_audio(audio_bytes: bytes) -> dict:
    """
    Validate audio specifically for voice enrollment.

    Requirements:
    - WAV format
    - 15-30 seconds duration
    - Reasonable sample rate (will be resampled to 16kHz for processing)

    Args:
        audio_bytes: Raw audio data

    Returns:
        Audio metadata dictionary

    Raises:
        AudioValidationError: If validation fails
    """
    return validate_wav_audio(
        audio_bytes,
        min_duration_seconds=15.0,
        max_duration_seconds=30.0,
    )


def validate_transcription_audio(audio_bytes: bytes) -> dict:
    """
    Validate audio for transcription (shorter chunks allowed).

    Requirements:
    - WAV format
    - 1-60 seconds duration (transcription chunks)

    Args:
        audio_bytes: Raw audio data

    Returns:
        Audio metadata dictionary

    Raises:
        AudioValidationError: If validation fails
    """
    return validate_wav_audio(
        audio_bytes,
        min_duration_seconds=1.0,
        max_duration_seconds=60.0,
    )
