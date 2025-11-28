package com.example.jpwhiteaudio.ui.screens.home

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.jpwhiteaudio.data.audio.AudioCaptureService
import com.example.jpwhiteaudio.data.repository.AuthRepository
import com.example.jpwhiteaudio.data.repository.AuthResult
import com.example.jpwhiteaudio.data.repository.Transcript
import com.example.jpwhiteaudio.data.repository.TranscriptionRepository
import com.example.jpwhiteaudio.data.repository.User
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val user: User? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
    val isListening: Boolean = false,
    val latestTranscript: Transcript? = null,
    val uploadedCount: Int = 0,
    val filteredCount: Int = 0
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val transcriptionRepository: TranscriptionRepository,
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _userState = MutableStateFlow<UserState>(UserState.Loading)

    private data class UserState(
        val user: User? = null,
        val isLoading: Boolean = true,
        val error: String? = null
    ) {
        companion object {
            val Loading = UserState(isLoading = true)
        }
    }

    val uiState: StateFlow<HomeUiState> = combine(
        _userState,
        AudioCaptureService.isListening,
        AudioCaptureService.uploadedCount,
        AudioCaptureService.filteredCount,
        transcriptionRepository.latestTranscript
    ) { userState, isListening, uploadedCount, filteredCount, latestTranscript ->
        HomeUiState(
            user = userState.user,
            isLoading = userState.isLoading,
            error = userState.error,
            isListening = isListening,
            latestTranscript = latestTranscript,
            uploadedCount = uploadedCount,
            filteredCount = filteredCount
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = HomeUiState()
    )

    init {
        loadUser()
    }

    private fun loadUser() {
        viewModelScope.launch {
            _userState.value = UserState.Loading

            when (val result = authRepository.refreshCurrentUser()) {
                is AuthResult.Success -> {
                    _userState.value = UserState(
                        user = result.data,
                        isLoading = false
                    )
                }
                is AuthResult.Error -> {
                    _userState.value = UserState(
                        isLoading = false,
                        error = result.message
                    )
                }
                is AuthResult.Loading -> {
                    // Already handled
                }
            }
        }
    }

    fun startListening() {
        AudioCaptureService.startListening(context)
    }

    fun stopListening() {
        AudioCaptureService.stopListening(context)
    }

    fun toggleListening() {
        if (uiState.value.isListening) {
            stopListening()
        } else {
            startListening()
        }
    }

    fun signOut() {
        stopListening()
        authRepository.signOut()
    }
}
