package com.example.jpwhiteaudio.data.api

import okhttp3.MultipartBody
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query

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

    @Multipart
    @POST("transcribe")
    suspend fun transcribe(
        @Part audio: MultipartBody.Part,
        @Part("timestamp_start") timestampStart: String,
        @Part("timestamp_end") timestampEnd: String,
        @Part("latitude") latitude: Double?,
        @Part("longitude") longitude: Double?
    ): TranscribeResponse

    @GET("transcripts")
    suspend fun getTranscripts(
        @Query("limit") limit: Int = 10,
        @Query("offset") offset: Int = 0,
        @Query("session_id") sessionId: String? = null
    ): TranscriptListResponse
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

data class TranscribeResponse(
    val processed: Boolean,
    val segments: List<TranscriptSegment>,
    val filtered_segments: Int,
    val session_id: String?
)

data class TranscriptSegment(
    val transcript_id: String,
    val speaker_type: String,
    val speaker_name: String,
    val text: String,
    val timestamp_start: String,
    val timestamp_end: String,
    val location_name: String?
)

data class TranscriptListResponse(
    val transcripts: List<TranscriptResponse>,
    val total: Int
)

data class TranscriptResponse(
    val id: String,
    val session_id: String,
    val speaker_type: String,
    val speaker_name: String,
    val text: String,
    val timestamp_start: String,
    val timestamp_end: String,
    val latitude: Double?,
    val longitude: Double?,
    val location_name: String?,
    val created_at: String
)
