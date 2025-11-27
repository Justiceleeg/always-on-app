package com.example.jpwhiteaudio.ui.screens.voiceenrollment

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.jpwhiteaudio.data.audio.AudioRecorder
import com.example.jpwhiteaudio.data.audio.RecordingState
import com.example.jpwhiteaudio.data.repository.AuthRepository
import com.example.jpwhiteaudio.data.repository.AuthResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class VoiceEnrollmentUiState(
    val enrollmentStep: EnrollmentStep = EnrollmentStep.Welcome,
    val isRecording: Boolean = false,
    val recordingDurationMs: Long = 0L,
    val amplitude: Float = 0f,
    val isUploading: Boolean = false,
    val error: String? = null,
    val enrollmentComplete: Boolean = false
)

enum class EnrollmentStep {
    Welcome,
    Recording,
    Complete
}

@HiltViewModel
class VoiceEnrollmentViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val audioRecorder: AudioRecorder
) : ViewModel() {

    private val _uiState = MutableStateFlow(VoiceEnrollmentUiState())
    val uiState: StateFlow<VoiceEnrollmentUiState> = _uiState.asStateFlow()

    val recordingDurationMs = audioRecorder.recordingDurationMs
    val amplitude = audioRecorder.amplitude

    init {
        // Observe recording state changes
        viewModelScope.launch {
            audioRecorder.recordingState.collect { state ->
                when (state) {
                    is RecordingState.Idle -> {
                        _uiState.value = _uiState.value.copy(isRecording = false)
                    }
                    is RecordingState.Recording -> {
                        _uiState.value = _uiState.value.copy(isRecording = true, error = null)
                    }
                    is RecordingState.Completed -> {
                        _uiState.value = _uiState.value.copy(isRecording = false)
                    }
                    is RecordingState.Error -> {
                        _uiState.value = _uiState.value.copy(
                            isRecording = false,
                            error = state.message
                        )
                    }
                }
            }
        }
    }

    fun hasRecordPermission(): Boolean = audioRecorder.hasRecordPermission()

    fun beginEnrollment() {
        _uiState.value = _uiState.value.copy(
            enrollmentStep = EnrollmentStep.Recording,
            error = null
        )
    }

    fun startRecording() {
        audioRecorder.resetState()
        val started = audioRecorder.startRecording()
        if (!started) {
            _uiState.value = _uiState.value.copy(
                error = "Failed to start recording. Please check microphone permissions."
            )
        }
    }

    fun stopRecording() {
        val wavData = audioRecorder.stopRecording()
        if (wavData != null) {
            uploadEnrollment(wavData)
        }
        // Error is handled via RecordingState flow
    }

    fun cancelRecording() {
        audioRecorder.cancelRecording()
        _uiState.value = _uiState.value.copy(
            enrollmentStep = EnrollmentStep.Welcome,
            error = null
        )
    }

    private fun uploadEnrollment(audioData: ByteArray) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isUploading = true, error = null)

            when (val result = authRepository.enrollVoice(audioData)) {
                is AuthResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isUploading = false,
                        enrollmentStep = EnrollmentStep.Complete,
                        enrollmentComplete = true
                    )
                }
                is AuthResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isUploading = false,
                        error = result.message
                    )
                }
                is AuthResult.Loading -> {
                    // Already showing loading state
                }
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    fun retryEnrollment() {
        audioRecorder.resetState()
        _uiState.value = _uiState.value.copy(
            enrollmentStep = EnrollmentStep.Recording,
            error = null
        )
    }

    override fun onCleared() {
        super.onCleared()
        audioRecorder.cancelRecording()
    }
}
