package com.example.jpwhiteaudio.data.repository

import com.example.jpwhiteaudio.data.api.ApiService
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.google.firebase.auth.UserProfileChangeRequest
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.tasks.await
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

sealed class AuthResult<out T> {
    data class Success<T>(val data: T) : AuthResult<T>()
    data class Error(val message: String, val exception: Throwable? = null) : AuthResult<Nothing>()
    data object Loading : AuthResult<Nothing>()
}

data class User(
    val id: String,
    val email: String,
    val name: String,
    val isEnrolled: Boolean
)

@Singleton
class AuthRepository @Inject constructor(
    private val firebaseAuth: FirebaseAuth,
    private val apiService: ApiService
) {
    private val _currentUser = MutableStateFlow<User?>(null)
    val currentUser: Flow<User?> = _currentUser.asStateFlow()

    private val _isLoggedIn = MutableStateFlow(firebaseAuth.currentUser != null)
    val isLoggedIn: Flow<Boolean> = _isLoggedIn.asStateFlow()

    init {
        // Listen to Firebase auth state changes
        firebaseAuth.addAuthStateListener { auth ->
            _isLoggedIn.value = auth.currentUser != null
            if (auth.currentUser == null) {
                _currentUser.value = null
            }
        }
    }

    val firebaseUser: FirebaseUser?
        get() = firebaseAuth.currentUser

    suspend fun createAccount(name: String, email: String, password: String): AuthResult<User> {
        return try {
            // Create Firebase account
            val authResult = firebaseAuth.createUserWithEmailAndPassword(email, password).await()
            val firebaseUser = authResult.user
                ?: return AuthResult.Error("Failed to create account")

            // Update display name
            val profileUpdates = UserProfileChangeRequest.Builder()
                .setDisplayName(name)
                .build()
            firebaseUser.updateProfile(profileUpdates).await()

            // Register with backend
            registerWithBackend(firebaseUser)
        } catch (e: Exception) {
            AuthResult.Error(e.message ?: "Failed to create account", e)
        }
    }

    suspend fun signIn(email: String, password: String): AuthResult<User> {
        return try {
            // Sign in with Firebase
            val authResult = firebaseAuth.signInWithEmailAndPassword(email, password).await()
            val firebaseUser = authResult.user
                ?: return AuthResult.Error("Failed to sign in")

            // Sync with backend
            registerWithBackend(firebaseUser)
        } catch (e: Exception) {
            AuthResult.Error(e.message ?: "Failed to sign in", e)
        }
    }

    private suspend fun registerWithBackend(firebaseUser: FirebaseUser): AuthResult<User> {
        return try {
            // Call backend register endpoint (token is added by AuthInterceptor)
            val response = apiService.register()

            val user = User(
                id = response.user_id,
                email = response.email,
                name = response.name,
                isEnrolled = response.is_enrolled
            )

            _currentUser.value = user
            AuthResult.Success(user)
        } catch (e: Exception) {
            AuthResult.Error(e.message ?: "Failed to register with backend", e)
        }
    }

    fun signOut() {
        firebaseAuth.signOut()
        _currentUser.value = null
    }

    suspend fun refreshCurrentUser(): AuthResult<User> {
        val firebaseUser = firebaseAuth.currentUser
            ?: return AuthResult.Error("Not logged in")

        return registerWithBackend(firebaseUser)
    }

    suspend fun enrollVoice(audioData: ByteArray): AuthResult<Unit> {
        return try {
            val requestBody = audioData.toRequestBody("audio/wav".toMediaType())
            val audioPart = MultipartBody.Part.createFormData("audio", "enrollment.wav", requestBody)

            val response = apiService.enrollVoice(audioPart)

            if (response.success) {
                // Update current user to reflect enrolled status
                _currentUser.value = _currentUser.value?.copy(isEnrolled = true)
                AuthResult.Success(Unit)
            } else {
                AuthResult.Error(response.message)
            }
        } catch (e: Exception) {
            AuthResult.Error(e.message ?: "Failed to enroll voice", e)
        }
    }
}
