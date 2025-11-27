package com.example.jpwhiteaudio.data.api

import retrofit2.http.GET
import retrofit2.http.POST

interface ApiService {

    @GET("health")
    suspend fun healthCheck(): HealthResponse

    @POST("auth/register")
    suspend fun register(): RegisterResponse
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
