package com.example.jpwhiteaudio.data.repository

import android.util.Log
import com.example.jpwhiteaudio.data.api.ApiService
import com.example.jpwhiteaudio.data.api.TranscribeResponse
import com.example.jpwhiteaudio.data.api.TranscriptResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Parse a timestamp string to Instant, handling both with and without 'Z' suffix.
 */
private fun parseTimestamp(timestamp: String): Instant {
    return try {
        // Try parsing as Instant (with Z suffix)
        Instant.parse(timestamp)
    } catch (e: Exception) {
        // Parse as LocalDateTime and convert to Instant assuming UTC
        LocalDateTime.parse(timestamp).toInstant(ZoneOffset.UTC)
    }
}

private const val TAG = "TranscriptionRepository"

sealed class TranscriptionResult<out T> {
    data class Success<T>(val data: T) : TranscriptionResult<T>()
    data class Error(val message: String, val exception: Throwable? = null) : TranscriptionResult<Nothing>()
}

data class Transcript(
    val id: String,
    val sessionId: String,
    val speakerType: String,
    val speakerName: String,
    val text: String,
    val timestampStart: Instant,
    val timestampEnd: Instant,
    val latitude: Double?,
    val longitude: Double?,
    val locationName: String?
)

@Singleton
class TranscriptionRepository @Inject constructor(
    private val apiService: ApiService
) {
    private val _latestTranscript = MutableStateFlow<Transcript?>(null)
    val latestTranscript: StateFlow<Transcript?> = _latestTranscript.asStateFlow()

    private val _recentTranscripts = MutableStateFlow<List<Transcript>>(emptyList())
    val recentTranscripts: StateFlow<List<Transcript>> = _recentTranscripts.asStateFlow()

    private val dateFormatter = DateTimeFormatter.ISO_INSTANT

    suspend fun transcribe(
        audioData: ByteArray,
        timestampStart: Instant,
        timestampEnd: Instant,
        latitude: Double?,
        longitude: Double?
    ): TranscriptionResult<TranscribeResponse> {
        return try {
            val requestBody = audioData.toRequestBody("audio/wav".toMediaType())
            val audioPart = MultipartBody.Part.createFormData("audio", "chunk.wav", requestBody)

            val startStr = dateFormatter.format(timestampStart)
            val endStr = dateFormatter.format(timestampEnd)

            Log.d(TAG, "Transcribing audio chunk: $startStr to $endStr")

            val response = apiService.transcribe(
                audio = audioPart,
                timestampStart = startStr,
                timestampEnd = endStr,
                latitude = latitude,
                longitude = longitude
            )

            Log.d(TAG, "Transcription response: processed=${response.processed}, segments=${response.segments.size}, filtered=${response.filtered_segments}")

            // Update latest transcript if we got segments
            if (response.segments.isNotEmpty()) {
                val segment = response.segments.first()
                val transcript = Transcript(
                    id = segment.transcript_id,
                    sessionId = response.session_id ?: "",
                    speakerType = segment.speaker_type,
                    speakerName = segment.speaker_name,
                    text = segment.text,
                    timestampStart = parseTimestamp(segment.timestamp_start),
                    timestampEnd = parseTimestamp(segment.timestamp_end),
                    latitude = latitude,
                    longitude = longitude,
                    locationName = null
                )
                _latestTranscript.value = transcript

                // Add to recent transcripts (keep last 20)
                val updated = listOf(transcript) + _recentTranscripts.value.take(19)
                _recentTranscripts.value = updated
            }

            TranscriptionResult.Success(response)
        } catch (e: kotlinx.coroutines.CancellationException) {
            // Expected when stopping - don't log as error
            Log.d(TAG, "Transcription cancelled")
            throw e  // Rethrow to allow proper cancellation
        } catch (e: Exception) {
            Log.e(TAG, "Transcription failed", e)
            TranscriptionResult.Error(e.message ?: "Transcription failed", e)
        }
    }

    suspend fun getTranscripts(
        limit: Int = 10,
        offset: Int = 0,
        sessionId: String? = null
    ): TranscriptionResult<List<Transcript>> {
        return try {
            val response = apiService.getTranscripts(limit, offset, sessionId)

            val transcripts = response.transcripts.map { it.toTranscript() }

            // Update recent transcripts if this is a fresh fetch
            if (offset == 0 && sessionId == null) {
                _recentTranscripts.value = transcripts
            }

            TranscriptionResult.Success(transcripts)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to fetch transcripts", e)
            TranscriptionResult.Error(e.message ?: "Failed to fetch transcripts", e)
        }
    }

    fun clearLatestTranscript() {
        _latestTranscript.value = null
    }

    private fun TranscriptResponse.toTranscript(): Transcript {
        return Transcript(
            id = id,
            sessionId = session_id,
            speakerType = speaker_type,
            speakerName = speaker_name,
            text = text,
            timestampStart = parseTimestamp(timestamp_start),
            timestampEnd = parseTimestamp(timestamp_end),
            latitude = latitude,
            longitude = longitude,
            locationName = location_name
        )
    }
}
