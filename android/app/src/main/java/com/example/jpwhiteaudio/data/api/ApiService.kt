package com.example.jpwhiteaudio.data.api

import okhttp3.MultipartBody
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface ApiService {

    @GET("health")
    suspend fun healthCheck(): HealthResponse

    @POST("auth/register")
    suspend fun register(): RegisterResponse

    @Multipart
    @POST("enroll")
    suspend fun enrollVoice(
        @Part audio: MultipartBody.Part
    ): EnrollResponse
}

data class HealthResponse(
    val status: String
)

data class RegisterResponse(
    val user_id: String,
    val email: String,
    val name: String,
    val is_enrolled: Boolean,
    val created: Boolean
)

data class EnrollResponse(
    val success: Boolean,
    val message: String
)
