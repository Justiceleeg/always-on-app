package com.example.jpwhiteaudio.data.audio

import android.Manifest
import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.example.jpwhiteaudio.JpwhiteAudioApplication
import com.example.jpwhiteaudio.MainActivity
import com.example.jpwhiteaudio.R
import com.example.jpwhiteaudio.data.repository.TranscriptionRepository
import com.example.jpwhiteaudio.data.repository.TranscriptionResult
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.time.Instant
import java.util.concurrent.ConcurrentLinkedQueue
import javax.inject.Inject
import kotlin.math.abs

private const val TAG = "AudioCaptureService"

/**
 * Audio chunk ready for upload
 */
data class AudioChunk(
    val audioData: ByteArray,
    val timestampStart: Instant,
    val timestampEnd: Instant,
    val latitude: Double?,
    val longitude: Double?,
    var retryCount: Int = 0,
    val createdAt: Instant = Instant.now()
) {
    companion object {
        const val MAX_RETRIES = 3
        const val MAX_AGE_HOURS = 1L
    }

    fun isExpired(): Boolean {
        return Instant.now().isAfter(createdAt.plusSeconds(MAX_AGE_HOURS * 3600))
    }

    fun canRetry(): Boolean {
        return retryCount < MAX_RETRIES && !isExpired()
    }
}

/**
 * Foreground service for continuous audio capture with Voice Activity Detection.
 *
 * Features:
 * - Records audio in 10-second chunks with 1-second overlap
 * - Simple energy-based Voice Activity Detection (VAD)
 * - Upload queue with retry logic (up to 3 retries)
 * - Discards chunks older than 1 hour
 * - Handles offline mode with local queue
 */
@AndroidEntryPoint
class AudioCaptureService : Service() {

    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val CHUNK_DURATION_MS = 10000L // 10 seconds
        private const val OVERLAP_DURATION_MS = 1000L // 1 second overlap
        private const val VAD_ENERGY_THRESHOLD = 50 // Minimum RMS energy for speech detection

        const val ACTION_START = "com.example.jpwhiteaudio.START_LISTENING"
        const val ACTION_STOP = "com.example.jpwhiteaudio.STOP_LISTENING"

        private val _isListening = MutableStateFlow(false)
        val isListening: StateFlow<Boolean> = _isListening.asStateFlow()

        private val _uploadedCount = MutableStateFlow(0)
        val uploadedCount: StateFlow<Int> = _uploadedCount.asStateFlow()

        private val _filteredCount = MutableStateFlow(0)
        val filteredCount: StateFlow<Int> = _filteredCount.asStateFlow()

        fun startListening(context: Context) {
            val intent = Intent(context, AudioCaptureService::class.java).apply {
                action = ACTION_START
            }
            ContextCompat.startForegroundService(context, intent)
        }

        fun stopListening(context: Context) {
            val intent = Intent(context, AudioCaptureService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }

    @Inject
    lateinit var transcriptionRepository: TranscriptionRepository

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var recordingJob: Job? = null
    private var uploadJob: Job? = null

    private var audioRecord: AudioRecord? = null
    private val uploadQueue = ConcurrentLinkedQueue<AudioChunk>()

    // Current location (to be set externally)
    var currentLatitude: Double? = null
    var currentLongitude: Double? = null

    private val binder = LocalBinder()

    inner class LocalBinder : Binder() {
        fun getService(): AudioCaptureService = this@AudioCaptureService
    }

    override fun onBind(intent: Intent?): IBinder = binder

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startListening()
            ACTION_STOP -> stopListening()
        }
        return START_STICKY
    }

    private fun startListening() {
        if (_isListening.value) {
            Log.d(TAG, "Already listening")
            return
        }

        if (!hasRecordPermission()) {
            Log.e(TAG, "No record permission")
            stopSelf()
            return
        }

        Log.d(TAG, "Starting audio capture service")

        // Start foreground with notification
        val notification = createNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        _isListening.value = true
        _uploadedCount.value = 0
        _filteredCount.value = 0

        // Start recording in chunks
        recordingJob = serviceScope.launch {
            recordAudioChunks()
        }

        // Start upload processor
        uploadJob = serviceScope.launch {
            processUploadQueue()
        }
    }

    private fun stopListening() {
        Log.d(TAG, "Stopping audio capture service")

        _isListening.value = false

        recordingJob?.cancel()
        recordingJob = null

        // Safely stop and release AudioRecord
        try {
            if (audioRecord?.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                audioRecord?.stop()
            }
        } catch (e: IllegalStateException) {
            Log.w(TAG, "AudioRecord already stopped", e)
        }
        try {
            audioRecord?.release()
        } catch (e: Exception) {
            Log.w(TAG, "Error releasing AudioRecord", e)
        }
        audioRecord = null

        // Let upload job finish remaining items
        serviceScope.launch {
            delay(2000) // Give time to upload remaining chunks
            uploadJob?.cancel()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    private suspend fun recordAudioChunks() {
        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
        if (bufferSize == AudioRecord.ERROR_BAD_VALUE || bufferSize == AudioRecord.ERROR) {
            Log.e(TAG, "Invalid buffer size")
            return
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
                Log.e(TAG, "AudioRecord failed to initialize")
                return
            }

            audioRecord?.startRecording()
            Log.d(TAG, "Recording started")

            val samplesPerChunk = (SAMPLE_RATE * CHUNK_DURATION_MS / 1000).toInt()
            val samplesOverlap = (SAMPLE_RATE * OVERLAP_DURATION_MS / 1000).toInt()
            val bytesPerChunk = samplesPerChunk * 2 // 16-bit audio
            val bytesOverlap = samplesOverlap * 2

            var overlapBuffer: ByteArray? = null
            val readBuffer = ShortArray(bufferSize / 2)

            while (serviceScope.isActive && _isListening.value) {
                val chunkStart = Instant.now()
                val audioStream = ByteArrayOutputStream()

                // Add overlap from previous chunk
                overlapBuffer?.let { audioStream.write(it) }

                var totalEnergy = 0L
                var sampleCount = 0

                // Record until we have enough samples for a chunk
                while (audioStream.size() < bytesPerChunk && _isListening.value) {
                    val read = audioRecord?.read(readBuffer, 0, readBuffer.size) ?: 0
                    if (read > 0) {
                        // Convert shorts to bytes
                        val byteBuffer = ByteBuffer.allocate(read * 2)
                        byteBuffer.order(ByteOrder.LITTLE_ENDIAN)
                        for (i in 0 until read) {
                            byteBuffer.putShort(readBuffer[i])
                            totalEnergy += abs(readBuffer[i].toInt())
                            sampleCount++
                        }
                        audioStream.write(byteBuffer.array())
                    }
                }

                if (!_isListening.value) break

                val chunkEnd = Instant.now()
                val rawData = audioStream.toByteArray()

                // Save overlap for next chunk
                if (rawData.size >= bytesOverlap) {
                    overlapBuffer = rawData.copyOfRange(rawData.size - bytesOverlap, rawData.size)
                }

                // Voice Activity Detection - check if chunk contains speech
                val avgEnergy = if (sampleCount > 0) totalEnergy / sampleCount else 0
                val hasSpeech = avgEnergy > VAD_ENERGY_THRESHOLD

                Log.d(TAG, "Chunk recorded: ${rawData.size} bytes, avgEnergy=$avgEnergy, hasSpeech=$hasSpeech")

                if (hasSpeech) {
                    // Create WAV and queue for upload
                    val wavData = createWavFile(rawData)
                    val chunk = AudioChunk(
                        audioData = wavData,
                        timestampStart = chunkStart,
                        timestampEnd = chunkEnd,
                        latitude = currentLatitude,
                        longitude = currentLongitude
                    )
                    uploadQueue.offer(chunk)
                    Log.d(TAG, "Chunk queued for upload, queue size: ${uploadQueue.size}")
                } else {
                    Log.d(TAG, "Chunk filtered (no speech detected)")
                }
            }

        } catch (e: SecurityException) {
            Log.e(TAG, "Security exception while recording", e)
        } catch (e: Exception) {
            Log.e(TAG, "Error while recording", e)
        } finally {
            try {
                if (audioRecord?.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                    audioRecord?.stop()
                }
            } catch (e: IllegalStateException) {
                Log.w(TAG, "AudioRecord already stopped", e)
            }
            try {
                audioRecord?.release()
            } catch (e: Exception) {
                Log.w(TAG, "Error releasing AudioRecord", e)
            }
            audioRecord = null
        }
    }

    private suspend fun processUploadQueue() {
        while (serviceScope.isActive) {
            val chunk = uploadQueue.poll()

            if (chunk == null) {
                delay(500) // Wait before checking again
                continue
            }

            // Skip expired chunks
            if (chunk.isExpired()) {
                Log.d(TAG, "Discarding expired chunk")
                continue
            }

            Log.d(TAG, "Uploading chunk, retry=${chunk.retryCount}")

            when (val result = transcriptionRepository.transcribe(
                audioData = chunk.audioData,
                timestampStart = chunk.timestampStart,
                timestampEnd = chunk.timestampEnd,
                latitude = chunk.latitude,
                longitude = chunk.longitude
            )) {
                is TranscriptionResult.Success -> {
                    val response = result.data
                    if (response.segments.isNotEmpty()) {
                        _uploadedCount.value++
                        Log.d(TAG, "Chunk transcribed successfully")
                    } else if (response.filtered_segments > 0) {
                        _filteredCount.value++
                        Log.d(TAG, "Chunk filtered by server (speaker not recognized)")
                    }
                }
                is TranscriptionResult.Error -> {
                    Log.e(TAG, "Upload failed: ${result.message}")
                    chunk.retryCount++
                    if (chunk.canRetry()) {
                        // Re-queue for retry
                        uploadQueue.offer(chunk)
                        delay(1000L * chunk.retryCount) // Exponential backoff
                    } else {
                        Log.d(TAG, "Chunk discarded after max retries")
                    }
                }
            }
        }
    }

    private fun createNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val stopIntent = Intent(this, AudioCaptureService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 1, stopIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, JpwhiteAudioApplication.LISTENING_CHANNEL_ID)
            .setContentTitle("Listening...")
            .setContentText("Capturing and transcribing speech")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .addAction(
                android.R.drawable.ic_media_pause,
                "Stop",
                stopPendingIntent
            )
            .build()
    }

    private fun hasRecordPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun createWavFile(rawData: ByteArray): ByteArray {
        val totalDataLen = rawData.size + 36
        val byteRate = SAMPLE_RATE * 1 * 16 / 8

        val header = ByteBuffer.allocate(44)
        header.order(ByteOrder.LITTLE_ENDIAN)

        // RIFF header
        header.put("RIFF".toByteArray())
        header.putInt(totalDataLen)
        header.put("WAVE".toByteArray())

        // fmt sub-chunk
        header.put("fmt ".toByteArray())
        header.putInt(16)
        header.putShort(1)
        header.putShort(1)
        header.putInt(SAMPLE_RATE)
        header.putInt(byteRate)
        header.putShort(2)
        header.putShort(16)

        // data sub-chunk
        header.put("data".toByteArray())
        header.putInt(rawData.size)

        return header.array() + rawData
    }

    override fun onDestroy() {
        super.onDestroy()
        _isListening.value = false
        serviceScope.cancel()
    }
}
