package com.example.jpwhiteaudio.data.api

import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.tasks.await
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val firebaseAuth: FirebaseAuth
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        // Skip auth for health endpoints
        if (originalRequest.url.encodedPath.startsWith("/health")) {
            return chain.proceed(originalRequest)
        }

        val currentUser = firebaseAuth.currentUser
        if (currentUser == null) {
            return chain.proceed(originalRequest)
        }

        // Get fresh Firebase ID token (force refresh to ensure valid token)
        val token = runBlocking {
            try {
                currentUser.getIdToken(true).await().token
            } catch (e: Exception) {
                null
            }
        }

        if (token == null) {
            return chain.proceed(originalRequest)
        }

        val authenticatedRequest = originalRequest.newBuilder()
            .header("Authorization", "Bearer $token")
            .build()

        return chain.proceed(authenticatedRequest)
    }
}
