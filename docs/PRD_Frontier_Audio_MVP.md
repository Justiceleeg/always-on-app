# Frontier Audio: Always-On Selective Speaker Transcription
## Product Requirements Document (MVP/PoC)

**Organization:** Frontier Audio  
**Project ID:** VyuiwBOFxfoySBVh4b7D_1762313417266  
**Version:** 2.0 — MVP Specification  
**Last Updated:** November 2025

---

## 1. Executive Summary

This document specifies the MVP/Proof-of-Concept for Frontier Audio's selective speaker transcription system. The product enables frontline workers to capture transcriptions of their conversations—filtering out unauthorized speakers—and later query their conversation history through a natural language chat interface.

**Core Value Proposition:** Speak → System recognizes you → Transcript stored with context → Chat with your conversation history.

### MVP Deliverables

| Component | Technology | Purpose |
|-----------|------------|---------|
| Android App | Kotlin | Audio capture, enrollment, consent flows, GPS tagging |
| Backend API | Python (FastAPI) | Speaker verification, transcription, data storage |
| Database | PostgreSQL + pgvector | Users, speakers, transcripts with semantic search |
| Object Storage | AWS S3 | Consent/revocation audio clips (legal proof) |
| Chat Interface | Next.js + Vercel AI SDK | RAG-powered queries over transcript history |
| Auth | Firebase Auth (shared across Android + Web) | Simple authentication for web UI |

---

## 2. Problem Statement

Frontline workers engage in numerous critical conversations daily. Manual note-taking is impractical in the field. Existing recording solutions either:

- Capture everything (privacy/legal concerns)
- Require manual activation (missed conversations)
- Lack intelligent retrieval (recordings sit unused)

This solution captures only authorized speakers, stores transcripts with rich context, and makes the data queryable through natural conversation.

---

## 3. Goals & Success Metrics

### Goals

1. Demonstrate selective speaker transcription (filter unauthorized voices)
2. Implement consent-based multi-speaker enrollment
3. Provide semantic search over transcript history via chat interface
4. Create a polished demo suitable for client presentation and portfolio

### Success Metrics (MVP)

| Metric | Target |
|--------|--------|
| Speaker verification accuracy | >90% correct identification |
| Transcription Word Error Rate | <10% (Whisper baseline) |
| End-to-end latency (speech → stored transcript) | <30 seconds |
| Chat retrieval relevance | Correct transcript retrieved in top-3 results >80% of the time |

---

## 4. Target Users & Personas

### Primary User: App Owner

The person who installs the app, enrolls their voice, and captures conversations.

**Persona — John, Construction Supervisor:**
- Needs hands-free recording during site walks
- Talks to multiple subcontractors daily
- Wants to recall "what did the electrician say about the panel?"

### Secondary User: Consented Speaker

A person who grants permission to be recorded by a primary user.

**Persona — Sarah, Electrical Subcontractor:**
- Works with John regularly
- Consents once, then speaks naturally
- Can revoke consent at any time

---

## 5. User Stories

### Enrollment & Setup

1. As a new user, I want to enroll my voice by speaking for 15-30 seconds so the system can recognize me.
2. As a primary user, I want to add a consented speaker through a witnessed verbal consent process.
3. As a consented speaker, I want to revoke my consent verbally at any time.

### Recording & Transcription

4. As a primary user, I want the app to continuously listen and transcribe only recognized speakers.
5. As a primary user, I want each transcript tagged with timestamp and GPS location.
6. As a primary user, I want unknown speakers filtered out entirely (not transcribed).

### Chat & Retrieval

7. As a user, I want to ask "What did Sarah say about the junction box?" and get relevant transcripts.
8. As a user, I want to ask "Summarize my conversations from last Tuesday" and get an accurate summary.
9. As a user, I want transcript citations with location and time when the chat references past conversations.

---

## 6. System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              ANDROID APP                                   │
│                                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Enrollment │  │   Consent    │  │   Capture    │  │   Settings   │   │
│  │   Screen     │  │   Flow       │  │   Screen     │  │   Screen     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Services: AudioCaptureService, LocationService, ApiClient          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ HTTPS
┌────────────────────────────────────────────────────────────────────────────┐
│                         AWS INFRASTRUCTURE                                 │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI Backend (ECS Fargate)                    │  │
│  │                                                                      │  │
│  │  Endpoints:                                                          │  │
│  │  ├── GET  /health                     (liveness check)              │  │
│  │  ├── GET  /health/ready               (readiness check)             │  │
│  │  ├── POST /auth/register              (Firebase token exchange)     │  │
│  │  ├── POST /enroll                     (primary user voiceprint)     │  │
│  │  ├── POST /speakers/consent           (add consented speaker)       │  │
│  │  ├── POST /speakers/revoke            (revoke consent)              │  │
│  │  ├── POST /transcribe                 (audio chunk processing)      │  │
│  │  └── POST /chat                       (RAG query)                   │  │
│  │                                                                      │  │
│  │  Services:                                                           │  │
│  │  ├── SpeakerVerificationService       (SpeechBrain ECAPA-TDNN)      │  │
│  │  ├── TranscriptionService             (OpenAI Whisper API)          │  │
│  │  ├── EmbeddingService                 (text embeddings for RAG)     │  │
│  │  └��─ ChatService                      (GPT-4 with context)          │  │
│  └────────────────────────────────────────────────────────��────────────┘  │
│                          │                    │                            │
│                          ▼                    ▼                            │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐   │
│  │      PostgreSQL (RDS)        │  │           S3 Bucket              │   │
│  │      + pgvector extension    │  │                                  │   │
│  │                              │  │  /consent-audio/                 │   │
│  │  Tables:                     │  │  /revocation-audio/              │   │
│  │  ├── users                   │  │                                  │   │
│  │  ├── consented_speakers      │  └──────────────────────────────────┘   │
│  │  ├── transcripts             │                                         │
│  │  └── (pgvector indexes)      │                                         │
│  └──────────────────────────────┘                                         │
└────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ HTTPS
┌────────────────────────────────────────────────────────────────────────────┐
│                           NEXT.JS CHAT UI                                  │
│                                                                            │
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐   │
│  │   Firebase   │  │                Chat Interface                    │   │
│  │   Auth       │  │                                                  │   │
│  │              │  │  • Streaming responses (Vercel AI SDK)           │   │
│  │   Login      │  │  • Transcript citations with location/time       │   │
│  │   Register   │  │  • Expandable source references                  │   │
│  └──────────────┘  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Data Model

### 7.1 Users Table

Primary app users (account owners).

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    voiceprint_embedding VECTOR(192),  -- ECAPA-TDNN embedding
    device_id VARCHAR(255),            -- Stored for info, not enforced in MVP
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 7.2 Consented Speakers Table

People enrolled by a primary user with verbal consent.

```sql
CREATE TABLE consented_speakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrolled_by UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    voiceprint_embedding VECTOR(192) NOT NULL,
    
    -- Consent record
    consent_audio_url VARCHAR(500) NOT NULL,      -- S3 URL
    consent_timestamp TIMESTAMP NOT NULL,
    consent_latitude DECIMAL(10, 8),
    consent_longitude DECIMAL(11, 8),
    
    -- Revocation record (nullable until revoked)
    revoked_at TIMESTAMP,
    revocation_method VARCHAR(20) CHECK (revocation_method IN ('verbal', 'manual')),
    revocation_audio_url VARCHAR(500),            -- S3 URL (only for verbal)
    revocation_latitude DECIMAL(10, 8),           -- only for verbal
    revocation_longitude DECIMAL(11, 8),          -- only for verbal
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_consented_speakers_enrolled_by ON consented_speakers(enrolled_by);
CREATE INDEX idx_consented_speakers_active ON consented_speakers(enrolled_by) WHERE revoked_at IS NULL;
```

### 7.3 Transcripts Table

Stored transcriptions with semantic search support.

```sql
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Conversation grouping (new session if gap > 5 minutes)
    session_id UUID NOT NULL,

    -- Speaker identification
    speaker_type VARCHAR(20) NOT NULL CHECK (speaker_type IN ('primary', 'consented')),
    speaker_id UUID,                              -- NULL if primary, else consented_speakers.id
    speaker_name VARCHAR(255) NOT NULL,

    -- Content
    transcript_text TEXT NOT NULL,

    -- Temporal data
    timestamp_start TIMESTAMP NOT NULL,
    timestamp_end TIMESTAMP NOT NULL,

    -- Location data
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_name VARCHAR(255),                   -- Reverse geocoded (optional)

    -- Semantic search
    embedding VECTOR(1536),                       -- OpenAI text-embedding-3-small

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transcripts_user_id ON transcripts(user_id);
CREATE INDEX idx_transcripts_session ON transcripts(user_id, session_id);
CREATE INDEX idx_transcripts_timestamp ON transcripts(user_id, timestamp_start DESC);
-- HNSW index performs better for lower dimensions and smaller datasets
CREATE INDEX idx_transcripts_embedding ON transcripts USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

---

## 8. API Specification

### 8.1 Authentication

All endpoints require Firebase ID token in Authorization header:
```
Authorization: Bearer <firebase_id_token>
```

### 8.2 Endpoints

#### GET /health

Basic liveness check. No authentication required.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-01-15T09:34:22Z"
}
```

---

#### GET /health/ready

Readiness check that verifies database connectivity. No authentication required.
Used by load balancer health checks.

**Response (healthy):**
```json
{
    "status": "ready",
    "database": "connected"
}
```

**Response (unhealthy - HTTP 503):**
```json
{
    "status": "not ready",
    "error": "Database connection failed"
}
```

---

#### POST /auth/register

Exchange Firebase token for session, create user record if new.

**Request:**
```json
{
    "firebase_token": "string",
    "name": "string",
    "device_id": "string"
}
```

**Response:**
```json
{
    "user_id": "uuid",
    "is_enrolled": false,
    "created": true
}
```

---

#### POST /enroll

Enroll primary user's voiceprint.

**Request:** `multipart/form-data`
- `audio`: WAV file (15-30 seconds of speech)

**Response:**
```json
{
    "success": true,
    "message": "Voiceprint enrolled successfully"
}
```

---

#### POST /speakers/consent

Add a consented speaker.

**Request:** `multipart/form-data`
- `audio`: WAV file containing consent phrase + name
- `latitude`: decimal
- `longitude`: decimal

**Processing:**
1. Verify consent phrase via speech-to-text
2. Extract speaker name from audio
3. Generate voiceprint embedding
4. Store consent audio in S3
5. Create consented_speaker record

**Response:**
```json
{
    "speaker_id": "uuid",
    "name": "Sarah",
    "consented_at": "2025-01-15T09:34:22Z"
}
```

---

#### POST /speakers/revoke

Revoke a speaker's consent.

**Request:** `multipart/form-data`
- `audio`: WAV file containing revocation phrase
- `latitude`: decimal
- `longitude`: decimal

**Processing:**
1. Match voiceprint to existing consented speaker
2. Verify revocation phrase
3. Store revocation audio in S3
4. Update consented_speaker record with revocation data

**Response:**
```json
{
    "speaker_id": "uuid",
    "name": "Sarah",
    "revoked_at": "2025-01-20T14:22:00Z",
    "method": "verbal"
}
```

---

#### DELETE /speakers/{speaker_id}

Manually revoke a speaker's consent (by primary user).

**Request:** No body required.

**Processing:**
1. Verify speaker belongs to authenticated user
2. Mark speaker as revoked with method "manual"
3. No audio proof stored

**Response:**
```json
{
    "speaker_id": "uuid",
    "name": "Sarah",
    "revoked_at": "2025-01-20T14:22:00Z",
    "method": "manual"
}
```

---

#### POST /transcribe

Process audio chunk for transcription.

**Request:** `multipart/form-data`
- `audio`: WAV file (audio chunk, recommended 10-30 seconds)
- `timestamp_start`: ISO timestamp
- `timestamp_end`: ISO timestamp
- `latitude`: decimal
- `longitude`: decimal

**Processing:**
1. Run Voice Activity Detection
2. For each speech segment:
   a. Extract speaker embedding
   b. Compare against primary user voiceprint
   c. Compare against active consented speakers
   d. If match found (cosine similarity > threshold):
      - Send to Whisper API
      - Generate text embedding
      - Store transcript with metadata
   e. If no match: discard segment

**Response:**
```json
{
    "processed": true,
    "segments": [
        {
            "speaker": "John",
            "speaker_type": "primary",
            "text": "Let's check the junction box on the north side.",
            "timestamp_start": "2025-01-15T09:34:22Z",
            "timestamp_end": "2025-01-15T09:34:28Z"
        },
        {
            "speaker": "Sarah",
            "speaker_type": "consented",
            "text": "I think we need to replace the whole panel.",
            "timestamp_start": "2025-01-15T09:34:30Z",
            "timestamp_end": "2025-01-15T09:34:35Z"
        }
    ],
    "filtered_segments": 1
}
```

---

#### POST /chat

Query transcripts via natural language.

**Request:**
```json
{
    "message": "What did Sarah say about the junction box?",
    "conversation_history": []
}
```

**Processing:**
1. Embed user query
2. Semantic search against transcript embeddings (pgvector)
3. Retrieve top-k relevant transcripts
4. Construct prompt with transcript context
5. Stream GPT-4 response

**Response:** Server-Sent Events (streaming)
```
data: {"type": "text", "content": "Based on your conversation at "}
data: {"type": "text", "content": "123 Main St on January 15th, "}
data: {"type": "citation", "transcript_id": "uuid", "speaker": "Sarah", "timestamp": "2025-01-15T09:34:30Z", "location": "123 Main St"}
data: {"type": "text", "content": "Sarah mentioned that "}
data: {"type": "text", "content": "the panel needs to be replaced entirely."}
data: {"type": "done"}
```

---

## 9. Android App Specification

### 9.1 Screen Flows

#### Authentication (First Launch)

```
┌─────────────────────────────────────────┐
│                                         │
│                                         │
│           🎙️ Frontier Audio             │
│                                         │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │         [ Sign In ]             │   │
│   └─────────────────────────────────┘   │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │       [ Create Account ]        │   │
│   └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
                    │
                    ▼ (tap Create Account)
┌─────────────────────────────────────────┐
│  ←          Create Account              │
├─────────────────────────────────────────┤
│                                         │
│   Name                                  │
│   ┌─────────────────────────────────┐   │
│   │ John Smith                      │   │
│   └─────────────────────────────────┘   │
│                                         │
│   Email                                 │
│   ┌─────────────────────────────────┐   │
│   │ john@example.com                │   │
│   └─────────────────────────────────┘   │
│                                         │
│   Password                              │
│   ┌─────────────────────────────────┐   │
│   │ ••••••••••••                    │   │
│   └─────────────────────────────────┘   │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │       [ Create Account ]        │   │
│   └─────────────────────────────────┘   │
│                                         │
│   Already have an account? Sign in      │
│                                         │
└─────────────────────────────────────────┘
                    │
                    ▼ (on success → Enrollment Flow)
```

#### Enrollment Flow (After Auth, First Time)

```
┌─────────────────────────────────────────┐
│           Welcome to Frontier           │
│                                         │
│   To get started, we need to learn      │
│   your voice. This takes about 30       │
│   seconds.                              │
│                                         │
│         [ Begin Enrollment ]            │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           Voice Enrollment              │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │                                 │   │
│   │      ~~~~~ waveform ~~~~~       │   │
│   │                                 │   │
│   └─────────────────────────────────┘   │
│                                         │
│   "Please read the following aloud:"    │
│                                         │
│   "The quick brown fox jumps over       │
│    the lazy dog near the riverbank      │
│    where five wizards quietly cast      │
│    magic spells."                       │
│                                         │
│         [ ● Recording... 18s ]          │
│                                         │
│   Keep speaking naturally until the     │
│   timer completes.                      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           Enrollment Complete           │
│                                         │
│              ✓                          │
│                                         │
│   Your voiceprint has been saved.       │
│   The app will now recognize your       │
│   voice.                                │
│                                         │
│         [ Start Listening ]             │
└─────────────────────────────────────────┘
```

#### Main Listening Screen

```
┌─────────────────────────────────────────┐
│  ☰                        Frontier  ⚙️  │
├─────────────────────────────────────────┤
│                                         │
│                                         │
│              ◉ Listening                │
│           (pulse animation)             │
│                                         │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │ Latest transcript:              │   │
│   │                                 │   │
│   │ [You] "Let's check the         │   │
│   │ junction box on the north      │   │
│   │ side."                         │   │
│   │                                 │   │
│   │ 9:34 AM · 123 Main St          │   │
│   └─────────────────────────────────┘   │
│                                         │
│                                         │
│   Recognized speakers:                  │
│   • You (primary)                       │
│   • Sarah (consented)                   │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│         [ + Add Speaker ]               │
│                                         │
└─────────────────────────────────────────┘
```

#### Consent Flow

```
┌─────────────────────────────────────────┐
│  ←          Add Speaker                 │
├─────────────────────────────────────────┤
│                                         │
│   To add a speaker, they must give      │
│   verbal consent.                       │
│                                         │
│   Hand the phone to the person you      │
│   want to add, or hold it while they    │
│   speak.                                │
│                                         │
│   ─────────────────────────────────     │
│                                         │
│   They should say:                      │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │                                 │   │
│   │  "I consent to being recorded   │   │
│   │   by [Your Name].               │   │
│   │   My name is [Their Name]."     │   │
│   │                                 │   │
│   └─────────────────────────────────┘   │
│                                         │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │                                 │   │
│   │   [ Hold to Record Consent ]    │   │
│   │                                 │   │
│   └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
                    │
                    ▼ (on successful consent)
┌─────────────────────────────────────────┐
│           Speaker Added                 │
│                                         │
│              ✓                          │
│                                         │
│   Sarah has been added.                 │
│                                         │
│   Her speech will now be transcribed    │
│   when you're recording.                │
│                                         │
│              [ Done ]                   │
└─────────────────────────────────────────┘
```

#### Revocation Flow

```
┌─────────────────────────────────────────┐
│  ←          Manage Speakers             │
├─────────────────────────────────────────┤
│                                         │
│   Active Speakers:                      │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │  Sarah                          │   │
│   │  Added Jan 15, 2025             │   │
│   │                     [ • • • ]   │   │
│   └─────────────────────────────────┘   │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │  Mike                           │   │
│   │  Added Jan 10, 2025             │   │
│   │                     [ • • • ]   │   │
│   └─────────────────────────────────┘   │
│                                         │
│   ─────────────────────────────────     │
│                                         │
│   Revoked Speakers:                     │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │  Tom (revoked Jan 12 · manual)  │   │
│   └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
                    │
                    ▼ (tap • • • menu)
┌─────────────────────────────────────────┐
│                                         │
│   ┌─────────────────────────────────┐   │
│   │  Verbal Revocation              │   │
│   │  Speaker records revocation     │   │
│   └─────────────────────────────────┘   │
│   ┌─────────────────────────────────┐   │
│   │  Remove Manually                │   │
│   │  You revoke on their behalf     │   │
│   └─────────────────────────────────┘   │
│   ┌─────────────────────────────────┐   │
│   │  Cancel                         │   │
│   └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

##### Manual Revocation (Remove Manually)

```
┌─────────────────────────────────────────┐
│  ←          Remove Speaker              │
├─────────────────────────────────────────┤
│                                         │
│   ⚠️  Remove Sarah?                      │
│                                         │
│   Sarah's speech will no longer be      │
│   transcribed.                          │
│                                         │
│   Note: Unlike verbal revocation, this  │
│   action is logged but no audio proof   │
│   is recorded.                          │
│                                         │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │                                 │   │
│   │       [ Remove Speaker ]        │   │
│   │                                 │   │
│   └─────────────────────────────────┘   │
│                                         │
│              [ Cancel ]                 │
│                                         │
└─────────────────────────────────────────┘
                    │
                    ▼ (on confirm)
┌─────────────────────────────────────────┐
│           Speaker Removed               │
│                                         │
│              ✓                          │
│                                         │
│   Sarah has been removed.               │
│                                         │
│   Her speech will no longer be          │
│   transcribed.                          │
│                                         │
│              [ Done ]                   │
└─────────────────────────────────────────┘
```

##### Verbal Revocation (Speaker records revocation)
┌─────────────────────────────────────────┐
│  ←          Revoke Consent              │
├─────────────────────────────────────────┤
│                                         │
│   To revoke consent, Sarah must         │
│   speak the revocation phrase.          │
│                                         │
│   Hand the phone to Sarah.              │
│                                         │
│   ─────────────────────────────────     │
│                                         │
│   Sarah should say:                     │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │                                 │   │
│   │  "I revoke my consent to        │   │
│   │   being recorded."              │   │
│   │                                 │   │
│   └─────────────────────────────────┘   │
│                                         │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │                                 │   │
│   │  [ Hold to Record Revocation ]  │   │
│   │                                 │   │
│   └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### 9.2 Technical Implementation

#### Authentication

```kotlin
// Firebase Auth integration
class AuthRepository(private val auth: FirebaseAuth) {
    
    suspend fun signIn(email: String, password: String): Result<FirebaseUser> {
        return try {
            val result = auth.signInWithEmailAndPassword(email, password).await()
            Result.success(result.user!!)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getIdToken(): String? {
        return auth.currentUser?.getIdToken(false)?.await()?.token
    }
}

// All API calls include the Firebase ID token
class ApiClient(private val authRepo: AuthRepository) {
    
    private suspend fun authHeaders(): Map<String, String> {
        val token = authRepo.getIdToken()
        return mapOf("Authorization" to "Bearer $token")
    }
}
```

#### Foreground Service

```kotlin
class AudioCaptureService : Service() {
    // Runs as foreground service with persistent notification
    // Required for continuous audio capture

    private val NOTIFICATION_ID = 1001
    private val CHUNK_DURATION_MS = 10_000  // 10 second chunks

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, createNotification())
        startAudioCapture()
        return START_STICKY
    }
}
```

#### Audio Chunking Strategy

- Capture audio in 10-second chunks (~320KB uncompressed WAV at 16kHz/16-bit)
- Use Voice Activity Detection to find speech boundaries
- Upload chunks with >2 seconds of speech
- Include 1-second overlap between chunks for continuity
- 10 seconds chosen for balance: fast feedback, less data loss on failure, reasonable upload size

#### Offline Handling (MVP)

- Queue audio chunks locally when offline
- Retry upload when connectivity restored
- Discard chunks older than 1 hour (configurable)

---

## 10. Chat UI Specification

### 10.1 Technology Stack

- **Framework:** Next.js 14 (App Router)
- **AI Integration:** Vercel AI SDK
- **Styling:** Tailwind CSS
- **Auth:** Firebase Auth (same Firebase project as Android app)
- **Deployment:** Vercel

### 10.2 Pages

```
/
├── /login          # Firebase auth login
├── /register       # Firebase auth register  
├── /chat           # Main chat interface (protected)
└── /api
    └── /chat       # API route for RAG queries
```

### 10.3 Chat Interface Design

```
┌──────────────────────────────────────────────────────────────┐
│  Frontier Audio                              John ▼  [ ⚙ ]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ What did Sarah say about the junction box?             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Based on your conversation at 123 Main St on           │  │
│  │ January 15th, Sarah mentioned that the junction        │  │
│  │ box panel needs to be replaced entirely. She noted     │  │
│  │ that the existing panel is outdated and doesn't        │  │
│  │ meet current safety codes.                             │  │
│  │                                                        │  │
│  │ ┌────────────────────────────────────────────────────┐ │  │
│  │ │ 📍 Source                                          │ │  │
│  │ │                                                    │ │  │
│  │ │ [Sarah] "I think we need to replace the whole     │ │  │
│  │ │ panel. It's not up to code."                      │ │  │
│  │ │                                                    │ │  │
│  │ │ Jan 15, 2025 · 9:34 AM · 123 Main St              │ │  │
│  │ └────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│                                                              │
│                                                              │
│                                                              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐  ┌──┐  │
│  │ Ask about your conversations...                  │  │ ➤│  │
│  └──────────────────────────────────────────────────┘  └──┘  │
└──────────────────────────────────────────────────────────────┘
```

### 10.4 Key Features

**Streaming Responses**
- Use Vercel AI SDK's `useChat` hook
- Stream tokens as they arrive for responsive feel

**Citation Cards**
- Expandable cards showing source transcript
- Include speaker name, timestamp, location
- Collapsible by default, expand on click

**Suggested Queries (Empty State)**
```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│              🎙️ Your Conversation History                  │
│                                                            │
│   Ask me anything about your past conversations:           │
│                                                            │
│   ┌──────────────────────────────────────────────────┐     │
│   │ "What did we discuss at the job site yesterday?" │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│   ┌──────────────────────────────────────────────────┐     │
│   │ "Summarize my conversations from this week"      │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│   ┌──────────────────────────────────────────────────┐     │
│   │ "What did Sarah say about the electrical work?"  │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 11. Speaker Verification Details

### 11.1 Technology

**Library:** SpeechBrain with ECAPA-TDNN model

**Embedding Dimensions:** 192

**Threshold Tuning:**
- Cosine similarity threshold: 0.65 (adjustable)
- Higher = more strict (fewer false positives, more false negatives)
- Lower = more lenient (more false positives, fewer false negatives)

### 11.2 Enrollment Requirements

- Minimum 15 seconds of speech
- Speech should be natural (not reading robotically)
- Low background noise preferred
- Store averaged embedding from multiple segments

### 11.3 Verification Flow

```python
def verify_speaker(audio_segment, user_id):
    # Extract embedding from incoming audio
    incoming_embedding = extract_embedding(audio_segment)
    
    # Get primary user's voiceprint
    user = db.get_user(user_id)
    
    # Check primary user first
    similarity = cosine_similarity(incoming_embedding, user.voiceprint_embedding)
    if similarity > THRESHOLD:
        return {"match": True, "speaker_type": "primary", "speaker_name": user.name}
    
    # Check consented speakers
    consented = db.get_active_consented_speakers(user_id)
    for speaker in consented:
        similarity = cosine_similarity(incoming_embedding, speaker.voiceprint_embedding)
        if similarity > THRESHOLD:
            return {"match": True, "speaker_type": "consented", "speaker_name": speaker.name}
    
    # No match
    return {"match": False}
```

---

## 12. Consent Phrase Processing

### 12.1 Consent Verification

**Expected Phrase:** "I consent to being recorded by [Primary User Name]. My name is [Speaker Name]."

**Verification Steps:**
1. Transcribe audio via Whisper
2. Use fuzzy keyword matching to verify consent intent
3. Extract speaker name from transcript
4. If verification fails, return error with specific feedback

**Fuzzy Consent Detection Logic:**

```python
import re

def verify_consent_phrase(transcript: str, primary_user_name: str) -> tuple[bool, str | None, str | None]:
    """
    Verify consent phrase using fuzzy keyword matching.
    Returns: (is_valid, speaker_name, error_message)
    """
    text = transcript.lower()

    # Required intents - at least one word from each group must be present
    consent_words = ["consent", "agree", "permission", "allow", "authorize"]
    record_words = ["record", "recording", "transcrib", "captur", "listen"]

    has_consent = any(word in text for word in consent_words)
    has_record = any(word in text for word in record_words)

    if not has_consent:
        return False, None, "Missing consent acknowledgment (e.g., 'I consent', 'I agree')"
    if not has_record:
        return False, None, "Missing recording acknowledgment (e.g., 'to being recorded')"

    # Extract speaker name - try multiple patterns
    name_patterns = [
        r"my name is ([a-z]+)",
        r"i'?m ([a-z]+)",
        r"this is ([a-z]+)",
        r"i am ([a-z]+)",
        r"call me ([a-z]+)",
    ]

    speaker_name = None
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            speaker_name = match.group(1).title()
            break

    if not speaker_name:
        return False, None, "Could not extract speaker name from transcript"

    return True, speaker_name, None
```

**Accepted Variations:**
- "I agree to being recorded by John. I'm Sarah."
- "I give my consent to be transcribed. My name is Sarah."
- "I authorize recording. This is Sarah."
- "I consent to John recording me. Call me Sarah."

### 12.2 Revocation Methods

#### Verbal Revocation (by consented speaker)

**Expected Phrase:** "I revoke my consent to being recorded."

**Verification Steps:**
1. Transcribe audio via Whisper
2. Match voiceprint against consented speakers
3. Use fuzzy keyword matching to verify revocation intent:
   - Revocation words: "revoke", "withdraw", "remove", "cancel", "stop"
   - Consent words: "consent", "permission", "agreement"
4. If voiceprint doesn't match any consented speaker, reject
5. Store audio in S3 as proof

#### Manual Revocation (by primary user)

**No phrase required.** Primary user taps "Remove Manually" in the UI.

**Processing:**
1. Confirm action via dialog
2. Mark speaker as revoked with `revocation_method = 'manual'`
3. Log timestamp (no audio proof stored)

---

## 13. RAG Implementation

### 13.1 Embedding Strategy

**Model:** OpenAI `text-embedding-3-small` (1536 dimensions)

**What Gets Embedded:**
- Transcript text
- Speaker name prepended: "[Sarah] The panel needs replacing"
- Time context appended: "... (morning, January 15, 2025)"

### 13.2 Time-Aware Retrieval

Queries like "What did Sarah say yesterday?" require temporal filtering before semantic search.

**Time Filter Parsing:**

```python
from datetime import datetime, timedelta

def parse_time_filter(query: str) -> tuple[datetime | None, datetime | None]:
    """
    Extract time bounds from natural language query.
    Returns: (start_time, end_time) or (None, None) if no time filter detected.
    """
    query_lower = query.lower()
    now = datetime.utcnow()

    if "today" in query_lower:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now

    if "yesterday" in query_lower:
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, end

    if "this week" in query_lower:
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now

    if "last week" in query_lower:
        end = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=7)
        return start, end

    # No time filter detected - use pure semantic search
    return None, None
```

**Time-Filtered Retrieval Query:**

```sql
-- With time filter
SELECT
    t.id,
    t.speaker_name,
    t.transcript_text,
    t.timestamp_start,
    t.latitude,
    t.longitude,
    1 - (t.embedding <=> $1) as similarity
FROM transcripts t
WHERE t.user_id = $2
  AND t.timestamp_start >= $3
  AND t.timestamp_start <= $4
ORDER BY t.embedding <=> $1
LIMIT 10;

-- Without time filter (pure semantic)
SELECT
    t.id,
    t.speaker_name,
    t.transcript_text,
    t.timestamp_start,
    t.latitude,
    t.longitude,
    1 - (t.embedding <=> $1) as similarity
FROM transcripts t
WHERE t.user_id = $2
ORDER BY t.embedding <=> $1
LIMIT 10;
```

### 13.3 Context Construction with Token Management

Chat sessions are ephemeral (not persisted). Context must fit within token limits.

```python
MAX_CONTEXT_TOKENS = 6000  # Leave room for system prompt (~500) + response (~1500)

def build_chat_context(
    user_query: str,
    user_id: str,
    limit: int = 10
) -> tuple[str, list[Transcript]]:
    """
    Build context string with token-aware truncation.
    Returns: (context_string, source_transcripts)
    """
    # Parse time filter from query
    time_start, time_end = parse_time_filter(user_query)

    # Embed the query
    query_embedding = embed_text(user_query)

    # Retrieve with or without time filter
    if time_start and time_end:
        transcripts = vector_search_with_time(
            query_embedding, user_id, time_start, time_end, limit=limit
        )
    else:
        transcripts = vector_search(query_embedding, user_id, limit=limit)

    # Build context with token limit
    context_parts = []
    total_chars = 0
    char_limit = MAX_CONTEXT_TOKENS * 4  # ~4 chars per token estimate

    for t in transcripts:
        entry = (
            f"[{t.speaker_name}] ({t.timestamp_start.strftime('%B %d, %Y at %I:%M %p')})\n"
            f"Location: {t.latitude}, {t.longitude}\n"
            f'"{t.transcript_text}"\n\n'
        )

        if total_chars + len(entry) > char_limit:
            # Try to fit truncated version
            remaining = char_limit - total_chars
            if remaining > 100:
                context_parts.append(entry[:remaining] + "...\n\n")
            break

        context_parts.append(entry)
        total_chars += len(entry)

    if not context_parts:
        return "No relevant transcripts found for your query.", []

    context = "Relevant conversation excerpts:\n\n" + "".join(context_parts)
    return context, transcripts
```

### 13.4 System Prompt

```
You are an AI assistant helping a user recall and understand their past conversations.
You have access to transcripts of their conversations with timestamps and locations.

When answering:
1. Reference specific conversations when relevant
2. Include the speaker name when quoting or paraphrasing
3. Mention the time and location for context
4. If you're not sure about something, say so
5. If the requested information isn't in the provided transcripts, let the user know

Always be accurate to what was actually said in the transcripts.
```

---

## 14. Non-Functional Requirements

### 14.1 Performance

| Metric | Target |
|--------|--------|
| Audio upload latency | <2s for 15s chunk on 4G |
| Speaker verification | <500ms per segment |
| Transcription | <5s for 15s audio |
| Chat response (first token) | <1s |
| Chat response (complete) | <10s |

### 14.2 Security

- All API communication over HTTPS
- Firebase Auth tokens validated server-side
- Audio stored in S3 with server-side encryption
- Voiceprint embeddings are not reversible to audio
- Database encrypted at rest (RDS default)

### 14.3 Privacy

- Only authorized speakers transcribed
- Consent audio stored as legal proof
- Two revocation methods available:
  - **Verbal:** Speaker records revocation phrase (audio stored in S3)
  - **Manual:** Primary user removes speaker (action logged, no audio)
- Revoked speakers immediately filtered from new transcriptions
- Historical transcripts from revoked speakers remain (pre-revocation was consensual)

### 14.4 Reliability (MVP Scope)

- Backend deployed on AWS with basic health checks
- Database daily backups (RDS automated)
- No SLA guarantees for MVP

---

## 15. Development Phases

### Phase 1: Foundation (Week 1-2)

- [ ] Set up AWS infrastructure (RDS, S3, ECS/Lambda)
- [ ] Create FastAPI project structure
- [ ] Implement database models with SQLAlchemy
- [ ] Set up Firebase Auth integration
- [ ] Create basic Next.js app with auth flow

### Phase 2: Core Audio Pipeline (Week 3-4)

- [ ] Implement SpeechBrain speaker verification service
- [ ] Implement Whisper transcription service
- [ ] Create `/enroll` endpoint
- [ ] Create `/transcribe` endpoint
- [ ] Test end-to-end: audio → speaker match → transcript

### Phase 3: Consent System (Week 5)

- [ ] Implement consent phrase verification
- [ ] Create `/speakers/consent` endpoint
- [ ] Create `/speakers/revoke` endpoint
- [ ] S3 integration for consent audio storage

### Phase 4: Android App (Week 6-7)

- [ ] Create Kotlin project structure
- [ ] Implement enrollment UI
- [ ] Implement main listening screen
- [ ] Implement consent flow UI
- [ ] Implement foreground service for audio capture
- [ ] Integrate with backend API

### Phase 5: Chat Interface (Week 8)

- [ ] Set up pgvector and embedding pipeline
- [ ] Implement RAG retrieval logic
- [ ] Create chat API route with Vercel AI SDK
- [ ] Build chat UI with streaming responses
- [ ] Add citation cards

### Phase 6: Polish & Demo (Week 9-10)

- [ ] Pre-seed demo data for compelling walkthrough
- [ ] UI polish (animations, empty states, error handling)
- [ ] End-to-end testing
- [ ] Documentation
- [ ] Demo script preparation

---

## 16. Out of Scope (MVP)

- iOS app
- Bluetooth microphone support
- Real-time streaming transcription (batch upload only)
- Transcript editing or deletion
- Export functionality
- Multi-device recording per account
- Device restriction enforcement (stored but not enforced in MVP)
- Advanced analytics or reporting
- Offline transcription
- Enterprise SSO

---

## 17. Future Considerations (Post-MVP)

- On-device speaker verification for reduced latency
- Streaming transcription with WebSocket
- Conversation summarization (daily/weekly digests)
- Integration with Frontier's AI assistant ecosystem
- Team/organization features
- Advanced search filters (by date, location, speaker)

---

## 18. Open Questions

1. **Speaker verification threshold:** Start with 0.65 cosine similarity. May need tuning based on real-world testing.

2. **Embedding model:** Using OpenAI `text-embedding-3-small`. Could switch to local model if cost becomes concern.

3. **Demo data strategy:** Need to create realistic sample data that tells a compelling story for the demo.

---

## Appendix A: Technology Versions

| Technology | Version |
|------------|---------|
| Python | 3.11+ |
| FastAPI | 0.100+ |
| SQLAlchemy | 2.0+ |
| SpeechBrain | 0.5+ |
| PostgreSQL | 17+ with pgvector 0.5+ |
| Next.js | 16+ |
| Vercel AI SDK | 5.x |
| Android SDK | API 35+ (Android 15+) |
| Kotlin | 2.0+ |
| Firebase Auth | Latest |
| Firebase Android SDK | 33+ |

---

## Appendix B: AWS Resources

| Service | Resource | Purpose |
|---------|----------|---------|
| RDS | PostgreSQL 17 (Aurora Serverless v2) | Database |
| S3 | frontier-audio-consent | Consent/revocation audio |
| ECS Fargate | 0.5 vCPU, 1GB RAM | FastAPI application |
| ALB | Application Load Balancer | HTTPS termination, health checks |
| ECR | Container registry | Docker images |

**Why ECS Fargate over Lambda:**
- SpeechBrain model loading takes seconds; Lambda cold starts would break <500ms verification target
- ECAPA-TDNN requires ~1GB RAM; Lambda pricing scales with memory
- Simpler deployment: single container, no Lambda-specific PyTorch packaging
- Auto-scaling disabled for MVP to reduce cost

---

*End of Document*
