package com.example.jpwhiteaudio.data.audio

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.core.content.ContextCompat
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Audio recorder that captures audio in WAV format (16kHz, 16-bit mono)
 * suitable for speaker verification enrollment.
 */
@Singleton
class AudioRecorder @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        const val SAMPLE_RATE = 16000
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        const val MAX_RECORDING_DURATION_MS = 30000L
        const val MIN_RECORDING_DURATION_MS = 15000L
    }

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordingThread: Thread? = null
    private var audioData: ByteArrayOutputStream? = null

    private val _recordingState = MutableStateFlow<RecordingState>(RecordingState.Idle)
    val recordingState: StateFlow<RecordingState> = _recordingState.asStateFlow()

    private val _amplitude = MutableStateFlow(0f)
    val amplitude: StateFlow<Float> = _amplitude.asStateFlow()

    private val _recordingDurationMs = MutableStateFlow(0L)
    val recordingDurationMs: StateFlow<Long> = _recordingDurationMs.asStateFlow()

    fun hasRecordPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    fun startRecording(): Boolean {
        if (!hasRecordPermission()) {
            _recordingState.value = RecordingState.Error("Microphone permission not granted")
            return false
        }

        if (isRecording) {
            return false
        }

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
        if (bufferSize == AudioRecord.ERROR_BAD_VALUE || bufferSize == AudioRecord.ERROR) {
            _recordingState.value = RecordingState.Error("Failed to get audio buffer size")
            return false
        }

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize * 2
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                _recordingState.value = RecordingState.Error("Failed to initialize audio recorder")
                return false
            }

            audioData = ByteArrayOutputStream()
            isRecording = true
            _recordingState.value = RecordingState.Recording
            _recordingDurationMs.value = 0L

            val startTime = System.currentTimeMillis()

            recordingThread = Thread {
                val buffer = ShortArray(bufferSize / 2)
                audioRecord?.startRecording()

                while (isRecording) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        // Convert shorts to bytes (little-endian)
                        val byteBuffer = ByteBuffer.allocate(read * 2)
                        byteBuffer.order(ByteOrder.LITTLE_ENDIAN)
                        for (i in 0 until read) {
                            byteBuffer.putShort(buffer[i])
                        }
                        audioData?.write(byteBuffer.array())

                        // Calculate amplitude for visualization
                        val maxAmplitude = buffer.take(read).maxOfOrNull { kotlin.math.abs(it.toInt()) } ?: 0
                        _amplitude.value = maxAmplitude / 32768f

                        // Update duration
                        val currentDuration = System.currentTimeMillis() - startTime
                        _recordingDurationMs.value = currentDuration

                        // Auto-stop at max duration
                        if (currentDuration >= MAX_RECORDING_DURATION_MS) {
                            stopRecording()
                        }
                    }
                }
            }
            recordingThread?.start()
            return true
        } catch (e: SecurityException) {
            _recordingState.value = RecordingState.Error("Permission denied: ${e.message}")
            return false
        } catch (e: Exception) {
            _recordingState.value = RecordingState.Error("Recording failed: ${e.message}")
            return false
        }
    }

    fun stopRecording(): ByteArray? {
        if (!isRecording) {
            return null
        }

        isRecording = false
        recordingThread?.join(1000)
        recordingThread = null

        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        val rawData = audioData?.toByteArray()
        audioData = null
        _amplitude.value = 0f

        if (rawData == null || rawData.isEmpty()) {
            _recordingState.value = RecordingState.Error("No audio data recorded")
            return null
        }

        val duration = _recordingDurationMs.value
        if (duration < MIN_RECORDING_DURATION_MS) {
            _recordingState.value = RecordingState.Error(
                "Recording too short. Minimum ${MIN_RECORDING_DURATION_MS / 1000} seconds required."
            )
            return null
        }

        _recordingState.value = RecordingState.Completed
        return createWavFile(rawData)
    }

    fun cancelRecording() {
        isRecording = false
        recordingThread?.join(1000)
        recordingThread = null

        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        audioData = null
        _amplitude.value = 0f
        _recordingDurationMs.value = 0L
        _recordingState.value = RecordingState.Idle
    }

    fun resetState() {
        _recordingState.value = RecordingState.Idle
        _recordingDurationMs.value = 0L
        _amplitude.value = 0f
    }

    /**
     * Creates a WAV file from raw PCM data.
     */
    private fun createWavFile(rawData: ByteArray): ByteArray {
        val totalDataLen = rawData.size + 36
        val byteRate = SAMPLE_RATE * 1 * 16 / 8 // sampleRate * channels * bitsPerSample / 8

        val header = ByteBuffer.allocate(44)
        header.order(ByteOrder.LITTLE_ENDIAN)

        // RIFF header
        header.put("RIFF".toByteArray())
        header.putInt(totalDataLen)
        header.put("WAVE".toByteArray())

        // fmt sub-chunk
        header.put("fmt ".toByteArray())
        header.putInt(16) // Sub-chunk size (16 for PCM)
        header.putShort(1) // Audio format (1 = PCM)
        header.putShort(1) // Number of channels (1 = mono)
        header.putInt(SAMPLE_RATE) // Sample rate
        header.putInt(byteRate) // Byte rate
        header.putShort(2) // Block align (channels * bitsPerSample / 8)
        header.putShort(16) // Bits per sample

        // data sub-chunk
        header.put("data".toByteArray())
        header.putInt(rawData.size)

        return header.array() + rawData
    }

    /**
     * Saves WAV data to a temporary file.
     */
    suspend fun saveToTempFile(wavData: ByteArray): File = withContext(Dispatchers.IO) {
        val tempFile = File.createTempFile("enrollment_", ".wav", context.cacheDir)
        FileOutputStream(tempFile).use { it.write(wavData) }
        tempFile
    }
}

sealed class RecordingState {
    data object Idle : RecordingState()
    data object Recording : RecordingState()
    data object Completed : RecordingState()
    data class Error(val message: String) : RecordingState()
}
