# Frontier Audio MVP - Implementation Plan

## Overview

This plan breaks the MVP into vertical slices, each delivering end-to-end functionality. Development starts locally, with AWS deployment at Slice 3.5 after the core audio pipeline is proven.

**Scope Note:** Per the original PRD, this MVP focuses on **primary user transcription only**. Multi-speaker consent enrollment is deferred to post-MVP (see Post-MVP section).

**Key Principles:**
- Each slice is independently demonstrable
- Local development first (Docker Compose), AWS deployment mid-project
- Android, Backend, and Web progress together per slice

**Technology Versions:**
- Python 3.12, FastAPI 0.100+, SQLAlchemy 2.0+
- PostgreSQL 17 with pgvector 0.5+
- Next.js 16+, Vercel AI SDK 5.x
- Android SDK API 35+ (Android 15), Kotlin 2.0+
- Firebase Android SDK 33+

---

## Slice 1: Auth & User Foundation

### Goals
- Establish local development environment
- Implement user registration and authentication flow across all platforms
- Prove Firebase Auth integration works end-to-end

### Tasks

#### 1.1 Local Development Setup
- [x] Create `docker-compose.yml` with PostgreSQL 17 + pgvector extension
- [x] Create `.env.example` for backend with all required variables
- [x] Document local setup in `README.md`

#### 1.2 Backend (FastAPI)
- [x] Initialize FastAPI project structure:
  ```
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── database.py
  │   ├── models/
  │   │   ├── __init__.py
  │   │   └── user.py
  │   ├── schemas/
  │   │   ├── __init__.py
  │   │   └── user.py
  │   ├── routers/
  │   │   ├── __init__.py
  │   │   ├── health.py
  │   │   └── auth.py
  │   └── services/
  │       ├── __init__.py
  │       └── firebase_auth.py
  ├── requirements.txt
  ├── Dockerfile
  └── .env.example
  ```
- [x] Implement database connection with SQLAlchemy 2.0 (async)
- [x] Create `users` table model:
  ```python
  class User(Base):
      id: UUID
      firebase_uid: str (unique)
      email: str
      name: str
      voiceprint_embedding: Vector(192)  # nullable until enrolled
      device_id: str (nullable)
      created_at: datetime
      updated_at: datetime
  ```
- [x] Implement `GET /health` endpoint (no auth)
- [x] Implement `GET /health/ready` endpoint (checks DB connection)
- [x] Implement Firebase Admin SDK integration for token verification
- [x] Implement `POST /auth/register` endpoint:
  - Validate Firebase ID token
  - Create or retrieve user record
  - Return `{ user_id, is_enrolled, created }`
- [x] Add request/response logging middleware
- [x] Write Dockerfile for backend

#### 1.3 Android App (Kotlin)
- [x] Initialize Android project with:
  - Minimum SDK 35 (Android 15)
  - Kotlin 2.0+
  - Jetpack Compose for UI
  - Hilt for dependency injection
  - Retrofit for API calls
- [x] Configure Firebase Auth SDK (33+)
- [x] Create authentication repository
- [x] Implement Welcome screen (Sign In / Create Account buttons)
- [x] Implement Create Account screen:
  - Name, Email, Password fields
  - Firebase `createUserWithEmailAndPassword`
  - Call `POST /auth/register` on success
- [x] Implement Sign In screen:
  - Email, Password fields
  - Firebase `signInWithEmailAndPassword`
  - Call `POST /auth/register` to sync with backend
- [x] Implement API client with Firebase token injection
- [x] Handle auth state persistence (stay logged in)
- [x] Navigate to placeholder "Home" screen on successful auth

#### 1.4 Web App (Next.js)
- [x] Initialize Next.js 16 project with App Router:
  ```
  web/
  ├── app/
  │   ├── layout.tsx
  │   ├── page.tsx
  │   ├── login/
  │   │   └── page.tsx
  │   ├── register/
  │   │   └── page.tsx
  │   └── chat/
  │       └── page.tsx (placeholder, protected)
  ├── lib/
  │   ├── firebase.ts
  │   └── api.ts
  ├── components/
  ├── package.json
  └── .env.local.example
  ```
- [x] Configure Firebase Auth (same project as Android)
- [x] Implement Login page
- [x] Implement Register page
- [x] Call `POST /auth/register` after Firebase auth
- [x] Implement auth context/provider
- [x] Add protected route middleware for `/chat`
- [x] Create placeholder Chat page (just shows "Welcome, {name}")

#### 1.5 Integration Testing
- [x] Test: Create account on Android → user appears in local DB
- [x] Test: Sign in on Web with same credentials → same user retrieved
- [ ] Test: Invalid/expired Firebase token returns 401

### Demo Checkpoint
User creates account on Android app, record appears in PostgreSQL, user can log into web app with same credentials.

---

## Slice 2: Primary User Voice Enrollment

### Goals
- Integrate SpeechBrain for speaker embedding extraction
- Implement voice enrollment flow on Android
- Store voiceprint for later speaker verification

### Tasks

#### 2.1 Backend - Speaker Verification Service
- [x] Add SpeechBrain and dependencies to requirements.txt
- [x] Create `SpeakerVerificationService`:
  ```python
  class SpeakerVerificationService:
      def __init__(self):
          # Load ECAPA-TDNN model (192-dim embeddings)

      def extract_embedding(self, audio_bytes: bytes) -> list[float]:
          # Returns 192-dimensional embedding

      def compare_embeddings(self, emb1, emb2) -> float:
          # Returns cosine similarity score
  ```
- [x] Implement `POST /enroll` endpoint:
  - Accept `multipart/form-data` with WAV audio file
  - Validate audio duration (15-30 seconds)
  - Extract speaker embedding via SpeechBrain
  - Update user's `voiceprint_embedding` in database
  - Return `{ success: true, message: "Voiceprint enrolled" }`
- [x] Add audio validation utilities (format, sample rate, duration)

#### 2.2 Android - Enrollment UI
- [x] Request microphone permission with rationale
- [x] Create Enrollment Welcome screen:
  - Explains voice enrollment process
  - "Begin Enrollment" button
- [x] Create Voice Recording screen:
  - Waveform visualization during recording
  - Display enrollment prompt text for user to read
  - Recording timer (target 15-30 seconds)
  - Auto-stop at 30 seconds
- [x] Implement audio recording service:
  - Record as WAV (16kHz, 16-bit mono)
  - Store temporarily before upload
- [x] Upload audio to `POST /enroll`
- [x] Create Enrollment Complete screen:
  - Success confirmation
  - "Start Listening" button → navigate to main screen
- [x] Handle enrollment errors (too short, upload failed, etc.)
- [x] Update app flow: after registration, check `is_enrolled` → route to enrollment or main screen

#### 2.3 Integration Testing
- [x] Test: Record 20 seconds of speech → embedding stored in DB
- [x] Test: Embedding is 192 dimensions
- [x] Test: Re-enrollment overwrites previous embedding
- [x] Test: Audio under 15 seconds is rejected (enforced client-side - stop button disabled until 15s)

### Demo Checkpoint
New user completes registration, is prompted to enroll voice, records speech, voiceprint is saved. App shows they are enrolled.

---

## Slice 3: Basic Transcription Pipeline

### Goals
- Implement speaker verification against enrolled voiceprint
- Integrate Whisper for transcription
- Build Android foreground service for continuous audio capture
- Store transcripts with timestamps

### Tasks

#### 3.1 Backend - Transcription Service
- [x] Create `TranscriptionService`:
  ```python
  class TranscriptionService:
      def __init__(self, openai_api_key: str):
          # Initialize OpenAI client

      async def transcribe(self, audio_bytes: bytes) -> str:
          # Call Whisper API, return transcript text
  ```
- [x] Create `transcripts` table model:
  ```python
  class Transcript(Base):
      id: UUID
      user_id: UUID (FK to users)
      session_id: UUID
      speaker_name: str  # Primary user's name
      transcript_text: str
      timestamp_start: datetime
      timestamp_end: datetime
      latitude: Decimal (nullable)
      longitude: Decimal (nullable)
      location_name: str (nullable)
      embedding: Vector(1536) (nullable)  # populated in Slice 4
      created_at: datetime
  ```
- [x] Implement `POST /transcribe` endpoint:
  - Accept `multipart/form-data`: audio, timestamp_start, timestamp_end, latitude, longitude
  - Extract speaker embedding from audio
  - Compare against user's voiceprint (cosine similarity > 0.65)
  - If match: transcribe with Whisper, store transcript, return segments
  - If no match: return `{ processed: true, segments: [], filtered_segments: 1 }`
- [x] Implement session ID logic (new session if gap > 5 minutes)
- [x] Add endpoint to get recent transcripts: `GET /transcripts?limit=10`

#### 3.2 Android - Audio Capture Service
- [x] Create `AudioCaptureService` (Foreground Service):
  - Persistent notification showing "Listening..."
  - Continuous audio recording in background
  - Chunk audio into 10-second segments
  - 1-second overlap between chunks for continuity
- [x] Implement Voice Activity Detection (VAD):
  - Only upload chunks with detected speech
  - Use simple energy-based VAD or WebRTC VAD
- [x] Create upload queue:
  - Queue chunks when captured
  - Upload sequentially to `POST /transcribe`
  - Retry on failure (up to 3 times)
  - Discard chunks older than 1 hour
- [x] Handle offline mode:
  - Queue locally when no connection
  - Resume uploads when connection restored

#### 3.3 Android - Main Listening Screen
- [x] Create Main Screen UI:
  - Large "Listening" indicator with pulse animation
  - Start/Stop listening toggle
  - Latest transcript preview card
  - Shows: speaker name, text snippet, timestamp
- [x] Display recognized speaker (just "You" - primary user only for MVP)
- [x] Settings gear icon (placeholder)
- [x] Connect to AudioCaptureService:
  - Start service when "Start Listening" tapped
  - Stop service when "Stop Listening" tapped
  - Observe transcript updates

#### 3.4 Integration Testing
- [x] Test: Speak while listening → transcript appears in DB with correct speaker_name
- [x] Test: Play audio from different person → filtered out (not transcribed)
- [x] Test: Transcripts have correct timestamps (UTC, verified against local time)
- [x] Test: Service survives app backgrounding
- [ ] Test: Offline queueing works (skipped - not critical for MVP)

### Demo Checkpoint
User starts listening, speaks into phone, their speech is recognized as "primary" speaker, transcribed via Whisper, and stored. Unknown speakers are filtered out.

---

## Slice 3.5: AWS Infrastructure Deployment

### Goals
- Complete AWS CDK infrastructure
- Deploy backend to ECS Fargate
- Validate all Slice 1-3 functionality works on AWS

### Tasks

#### 3.5.1 CDK Infrastructure Completion
- [x] Remove S3 bucket from CDK (not needed for MVP - consent audio storage is post-MVP)
- [x] Add ECR repository for backend Docker images
- [x] Add ECS Fargate cluster
- [x] Add ECS Task Definition:
  - 0.5 vCPU, 1GB RAM
  - Container from ECR
  - Environment variables for config
  - CloudWatch log group
- [x] Add ECS Service:
  - Desired count: 1
  - Connect to ALB
- [x] Add Application Load Balancer:
  - HTTP listener (port 80) for initial testing
  - Health check on `/health`
  - HTTPS can be added when ACM certificate is configured
- [x] Add IAM roles:
  - Task execution role (ECR pull, CloudWatch logs)
  - Task role (minimal permissions for MVP)
- [x] Using HTTP for initial testing (ACM certificate can be added later)
- [x] Enable pgvector extension on Aurora:
  - Already enabled on existing Aurora instance (tables with Vector columns exist)
- [x] Export ALB DNS name as CloudFormation output

#### 3.5.2 Deployment Pipeline
- [x] Create deployment script (`scripts/deploy.sh`):
  - Builds and pushes Docker image to ECR
  - Deploys CDK infrastructure
  - Forces new ECS deployment
  - Waits for service to stabilize
  - Usage: `./scripts/deploy.sh [--skip-build] [--skip-cdk] [--skip-migrate]`
- [x] Create database migration script (`scripts/migrate.sh`):
  - Runs Alembic migrations against Aurora
  - Auto-discovers Aurora endpoint from CloudFormation
  - Usage: `./scripts/migrate.sh [upgrade|downgrade|current|history] [revision]`
- [x] Document environment variables in `infra/.env.example`

#### 3.5.3 Configuration Updates
- [x] Update Android app to support configurable API base URL
  - Debug: `http://10.0.2.2:8000` (emulator localhost)
  - Release: `https://jpwhite.gauntlet3.com`
- [x] Create production build variant pointing to ALB endpoint (already configured in build.gradle.kts)
- [x] Update Next.js to use environment variable for API URL
  - Uses `NEXT_PUBLIC_API_URL` env var
  - Set `https://jpwhite.gauntlet3.com` in Vercel environment variables
- [x] Set up environment variables in ECS task definition (configured in CDK)

#### 3.5.4 Validation Testing
- [x] Test: `/health` returns 200 via ALB
- [x] Test: `/health/ready` confirms Aurora connection
- [x] Test: Web app can register/login user via AWS endpoint
- [x] Test: Android app can register user via AWS endpoint
- [x] Test: Voice enrollment works end-to-end on AWS
- [x] Test: Transcription pipeline works on AWS
- [x] Test: CloudWatch logs show requests

### Demo Checkpoint
All functionality from Slices 1-3 works against AWS infrastructure. Android app connects to ALB endpoint, users are stored in Aurora, transcripts are processed and stored.

---

## Slice 4: Chat & RAG Interface

### Goals
- Embed transcripts for semantic search
- Implement RAG retrieval with time-aware filtering
- Build chat UI with streaming responses and citations

### Tasks

#### 4.1 Backend - Embedding Service
- [x] Create `EmbeddingService`:
  ```python
  class EmbeddingService:
      def __init__(self, openai_api_key: str):
          # Initialize OpenAI client

      async def embed_text(self, text: str) -> list[float]:
          # Call text-embedding-3-small API
          # Return 1536-dimensional embedding

      def prepare_transcript_for_embedding(self, transcript: Transcript) -> str:
          # Format: "[Speaker] text (time context)"
          # e.g., "[You] Check the junction box on north side (morning, January 15, 2025)"
  ```
- [x] Update `POST /transcribe` to generate and store embeddings:
  - After transcription, embed the text
  - Store in `transcript.embedding`
- [x] Create database migration to add HNSW index on embeddings:
  ```sql
  CREATE INDEX idx_transcripts_embedding
  ON transcripts USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```
- [ ] Backfill embeddings for existing transcripts (if any)

#### 4.2 Backend - Chat Service
- [x] Implement time filter parsing (timezone-aware using client timezone):
  ```python
  def parse_time_filter(query: str) -> tuple[datetime | None, datetime | None]:
      # Parse "today", "yesterday", "this week", "last week"
      # Return (start_time, end_time) or (None, None)
  ```
- [x] Implement vector search:
  ```python
  async def vector_search(
      query_embedding: list[float],
      user_id: UUID,
      time_start: datetime | None,
      time_end: datetime | None,
      limit: int = 10
  ) -> list[Transcript]:
      # Query pgvector with optional time filter
      # Return top-k similar transcripts
  ```
- [x] Implement context builder with token management:
  ```python
  def build_chat_context(
      transcripts: list[Transcript],
      max_tokens: int = 6000
  ) -> str:
      # Build context string from transcripts
      # Truncate if exceeds token limit
  ```
- [x] Implement `POST /chat` endpoint:
  - Accept `{ message, conversation_history, timezone }`
  - Parse time filter from message (timezone-aware)
  - Embed user query
  - Retrieve relevant transcripts via vector search
  - Build context with retrieved transcripts
  - Stream GPT-4o response with system prompt
  - Include citation metadata in response
- [x] Define chat response streaming format:
  ```
  data: {"type": "text", "content": "Based on..."}
  data: {"type": "citation", "transcript_id": "...", "speaker": "...", "timestamp": "...", "location": "..."}
  data: {"type": "done"}
  ```

#### 4.3 Web - Chat Interface
- [x] Install and configure Vercel AI SDK 5.x (already installed)
- [x] Create streaming chat client in `lib/api.ts`:
  - Direct SSE streaming from backend `/chat` endpoint
  - Handle streaming responses with async generator
- [x] Build Chat page UI:
  - Message list (user messages + assistant responses)
  - Input field with send button
  - Streaming text display with loading indicator
- [x] Implement Citation Card component:
  - Collapsible card showing source transcript
  - Speaker name, timestamp, location
  - Quote from transcript
  - Expand/collapse on click
- [x] Create empty state with suggested queries:
  - "What did I discuss at the job site yesterday?"
  - "Summarize my conversations from this week"
  - "What did I say about the electrical work?"
  - "What topics came up today?"
- [x] Add loading states and error handling
- [x] Style with Tailwind CSS

#### 4.4 Integration Testing
- [x] Test: Query "What did I say about X" → relevant transcript returned
- [x] Test: Query "yesterday" → only transcripts from yesterday
- [x] Test: Citations display correctly with metadata
- [x] Test: Streaming works smoothly
- [x] Test: No transcripts found → appropriate message

### Demo Checkpoint
User asks "What did I say about the junction box?" in web chat. System retrieves relevant transcript via semantic search, streams response with context, and displays citation card with speaker, time, and location.

---

## Slice 5: Polish & Location Context

### Goals
- Add GPS context to transcripts
- Polish UI across all platforms
- Create demo-ready experience with seeded data

### Tasks

#### 5.1 Android - Location Integration
- [x] Request location permissions (fine + coarse) - Already in manifest, permission request added to HomeScreen
- [x] Create `LocationService`:
  - Get current location when audio chunk captured
  - Include lat/long in `/transcribe` request
- [x] Update AudioCaptureService to include location data
- [x] Display location in transcript preview on main screen

#### 5.2 Backend - Location Enhancement
- [x] Add reverse geocoding service:
  - Convert lat/long to human-readable address using Nominatim (OpenStreetMap)
  - Store in `transcript.location_name`
- [x] Include location in chat context for RAG (already implemented in Slice 4)

#### 5.3 Web - Location Display
- [x] Citation Card already displays location when available (implemented in Slice 4)

#### 5.4 Android - UI Polish
- [x] Pulse animation already exists on "Listening" indicator
- [x] Waveform animation already exists during enrollment recording
- [x] Implement proper empty states:
  - No transcripts yet - EmptyTranscriptsCard added
- [x] Loading indicators exist for API calls (CircularProgressIndicator)
- [ ] Implement error toasts/snackbars (nice-to-have, not critical)
- [ ] Add pull-to-refresh on transcript list (nice-to-have, not critical)
- [ ] Review and polish all screen transitions (nice-to-have)

#### 5.5 Web - UI Polish
- [x] Add loading skeletons for chat (ChatLoadingSkeleton component)
- [x] Typing indicator for streaming responses (TypingIndicator component)
- [x] Citation card expand/collapse animation (already works)
- [x] Add user dropdown menu (UserDropdown component)
- [x] Responsive design for mobile web (responsive classes added)
- [x] Empty state with suggested queries (already implemented)

#### 5.6 Demo Data & Script
- [x] Create seed script for demo data:
  - Demo user account
  - 22 realistic transcripts over past week (primary user only)
  - Variety of topics (construction, electrical, scheduling, inspections)
  - Multiple locations (Denver metro area)
- [x] Write demo script/walkthrough (docs/DEMO_WALKTHROUGH.md):
  1. Show Android app enrollment
  2. Show listening and transcription
  3. Switch to web, ask questions about your conversations
  4. Show citations with location and time context
- [ ] Test full demo flow end-to-end (manual testing required)

#### 5.7 Final Testing & Documentation
- [ ] End-to-end test all user flows (manual testing required)
- [ ] Test on physical Android device (manual testing required)
- [ ] Performance testing (transcription latency, chat response time)
- [ ] Document deployment process (existing docs in README)
- [ ] Document environment setup for future developers (existing docs in README)

### Demo Checkpoint
Complete, polished application ready for client demonstration. User can enroll voice, capture transcriptions of their own speech with location data, and query their conversation history via natural language chat with rich citations.

---

## Technical Notes

### Environment Variables

**Backend:**
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/frontier_audio
FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=
OPENAI_API_KEY=
SPEAKER_VERIFICATION_THRESHOLD=0.65
```

**Android:**
```
API_BASE_URL=http://10.0.2.2:8000  # or ALB endpoint for prod
```

**Web:**
```
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_API_URL=http://localhost:8000  # or ALB endpoint for prod
```

### Key Technical Decisions

1. **SpeechBrain ECAPA-TDNN** for speaker verification (192-dim embeddings)
2. **OpenAI Whisper API** for transcription (not local model)
3. **OpenAI text-embedding-3-small** for RAG embeddings (1536-dim)
4. **pgvector HNSW index** for fast similarity search
5. **10-second audio chunks** with 1-second overlap
6. **Cosine similarity threshold 0.65** for speaker matching (tunable)
7. **Foreground Service** for Android audio capture (required for background recording)
8. **Server-Sent Events** for chat streaming

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SpeechBrain model size/loading time | Pre-load model at service startup, use ECS with sufficient memory |
| Speaker verification accuracy | Start with 0.65 threshold, tune based on testing |
| Whisper API latency | Accept <5s for 15s audio, batch if needed |
| Android battery drain | Use efficient VAD to minimize uploads, respect Doze mode |
| pgvector performance at scale | HNSW index handles MVP scale, monitor and optimize if needed |

---

## Success Criteria (from PRD)

| Metric | Target | Validation |
|--------|--------|------------|
| Speaker verification accuracy | >90% | Test with 10+ speakers, measure FPR/FNR |
| Transcription WER | <10% | Whisper baseline, spot-check transcripts |
| End-to-end latency | <30 seconds | Measure speech → stored transcript |
| Chat retrieval relevance | >80% top-3 | Test 20 queries, check if correct transcript in top 3 |

---

## Post-MVP: Consented Speaker System

> **Note:** This feature was part of the expanded MVP PRD but is deferred based on the original project requirements, which specified primary user transcription only.

### Goals
- Implement multi-speaker consent enrollment
- Store consent audio in S3 as legal proof
- Enable verbal and manual revocation
- Transcribe consented speakers alongside primary user

### Tasks

#### Backend - Consent Endpoints
- [ ] Create `consented_speakers` table model:
  ```python
  class ConsentedSpeaker(Base):
      id: UUID
      enrolled_by: UUID (FK to users)
      name: str
      voiceprint_embedding: Vector(192)
      consent_audio_url: str  # S3 URL
      consent_timestamp: datetime
      consent_latitude: Decimal (nullable)
      consent_longitude: Decimal (nullable)
      revoked_at: datetime (nullable)
      revocation_method: str (nullable)  # 'verbal' or 'manual'
      revocation_audio_url: str (nullable)
      revocation_latitude: Decimal (nullable)
      revocation_longitude: Decimal (nullable)
      created_at: datetime
  ```
- [ ] Add S3 bucket to CDK infrastructure with server-side encryption
- [ ] Create S3 service for audio upload:
  ```python
  class S3Service:
      def upload_consent_audio(self, user_id: str, audio: bytes) -> str:
          # Upload to s3://bucket/consent-audio/{user_id}/{uuid}.wav
          # Return S3 URL

      def upload_revocation_audio(self, user_id: str, audio: bytes) -> str:
          # Upload to s3://bucket/revocation-audio/{user_id}/{uuid}.wav
  ```
- [ ] Implement consent phrase verification:
  ```python
  def verify_consent_phrase(transcript: str, primary_user_name: str) -> tuple[bool, str | None, str | None]:
      # Check for consent words: "consent", "agree", "permission", etc.
      # Check for recording words: "record", "transcrib", etc.
      # Extract speaker name from "my name is X" or similar
      # Return (is_valid, speaker_name, error_message)
  ```
- [ ] Implement `POST /speakers/consent`:
  - Accept audio, latitude, longitude
  - Transcribe audio via Whisper
  - Verify consent phrase, extract speaker name
  - Extract speaker embedding
  - Upload consent audio to S3
  - Create consented_speaker record
  - Return `{ speaker_id, name, consented_at }`
- [ ] Implement `POST /speakers/revoke` (verbal):
  - Accept audio, latitude, longitude
  - Extract speaker embedding
  - Match against user's consented speakers
  - Verify revocation phrase ("revoke", "withdraw", etc.)
  - Upload revocation audio to S3
  - Update consented_speaker with revocation data
  - Return `{ speaker_id, name, revoked_at, method: "verbal" }`
- [ ] Implement `DELETE /speakers/{speaker_id}` (manual):
  - Verify speaker belongs to authenticated user
  - Update consented_speaker: `revoked_at = now()`, `revocation_method = "manual"`
  - Return `{ speaker_id, name, revoked_at, method: "manual" }`
- [ ] Implement `GET /speakers`:
  - Return list of consented speakers for user
  - Include active and revoked, with status indicator
- [ ] Update `POST /transcribe` to check consented speakers:
  - After primary user check fails, check all active consented speakers
  - If match found, transcribe with `speaker_type = "consented"`
- [ ] Update transcript model to add `speaker_type` and `speaker_id` fields

#### Android - Consent Flow
- [ ] Create Add Speaker screen:
  - Instructions for consent process
  - Display required consent phrase template
  - "Hold to Record Consent" button
- [ ] Implement consent recording:
  - Record while button held
  - Upload to `POST /speakers/consent`
  - Show success/error based on phrase verification
- [ ] Create Speaker Added confirmation screen
- [ ] Handle consent errors:
  - Missing consent acknowledgment
  - Missing recording acknowledgment
  - Could not extract speaker name
  - Display specific error and allow retry

#### Android - Speaker Management
- [ ] Create Manage Speakers screen:
  - List active speakers with name and date added
  - List revoked speakers with revocation date and method
  - Three-dot menu per active speaker
- [ ] Implement speaker options menu:
  - "Verbal Revocation" option
  - "Remove Manually" option
  - "Cancel"
- [ ] Create Verbal Revocation screen:
  - Instructions for speaker to say revocation phrase
  - "Hold to Record Revocation" button
  - Upload to `POST /speakers/revoke`
- [ ] Create Manual Revocation confirmation dialog:
  - Warning that no audio proof will be stored
  - Confirm/Cancel buttons
  - Call `DELETE /speakers/{id}` on confirm
- [ ] Update Main Screen:
  - Show list of recognized speakers (You + consented)
  - "Add Speaker" button navigates to consent flow

#### Integration Testing
- [ ] Test: Consent phrase accepted → speaker added → audio in S3
- [ ] Test: Invalid consent phrase → specific error returned
- [ ] Test: Consented speaker speaks → transcribed with their name
- [ ] Test: Verbal revocation by speaker → marked revoked with audio proof
- [ ] Test: Manual revocation by primary → marked revoked, no audio
- [ ] Test: Revoked speaker speaks → filtered out

### Demo Checkpoint (Post-MVP)
Primary user adds "Sarah" via consent phrase. Sarah's consent audio is stored in S3. When Sarah speaks, her speech is transcribed and attributed to her. Sarah can verbally revoke, or primary user can manually remove her.

---

*Last updated: November 2025*
