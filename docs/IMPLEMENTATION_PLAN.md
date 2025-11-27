# Frontier Audio MVP - Implementation Plan

## Overview

This plan breaks the MVP into vertical slices, each delivering end-to-end functionality. Development starts locally, with AWS deployment at Slice 3.5 after the core audio pipeline is proven.

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
- [ ] Create `TranscriptionService`:
  ```python
  class TranscriptionService:
      def __init__(self, openai_api_key: str):
          # Initialize OpenAI client

      async def transcribe(self, audio_bytes: bytes) -> str:
          # Call Whisper API, return transcript text
  ```
- [ ] Create `transcripts` table model:
  ```python
  class Transcript(Base):
      id: UUID
      user_id: UUID (FK to users)
      session_id: UUID
      speaker_type: str  # 'primary' or 'consented'
      speaker_id: UUID (nullable)  # FK to consented_speakers
      speaker_name: str
      transcript_text: str
      timestamp_start: datetime
      timestamp_end: datetime
      latitude: Decimal (nullable)
      longitude: Decimal (nullable)
      location_name: str (nullable)
      embedding: Vector(1536) (nullable)  # populated in Slice 5
      created_at: datetime
  ```
- [ ] Implement `POST /transcribe` endpoint:
  - Accept `multipart/form-data`: audio, timestamp_start, timestamp_end, latitude, longitude
  - Extract speaker embedding from audio
  - Compare against user's voiceprint (cosine similarity > 0.65)
  - If match: transcribe with Whisper, store transcript, return segments
  - If no match: return `{ processed: true, segments: [], filtered_segments: 1 }`
- [ ] Implement session ID logic (new session if gap > 5 minutes)
- [ ] Add endpoint to get recent transcripts: `GET /transcripts?limit=10`

#### 3.2 Android - Audio Capture Service
- [ ] Create `AudioCaptureService` (Foreground Service):
  - Persistent notification showing "Listening..."
  - Continuous audio recording in background
  - Chunk audio into 10-second segments
  - 1-second overlap between chunks for continuity
- [ ] Implement Voice Activity Detection (VAD):
  - Only upload chunks with detected speech
  - Use simple energy-based VAD or WebRTC VAD
- [ ] Create upload queue:
  - Queue chunks when captured
  - Upload sequentially to `POST /transcribe`
  - Retry on failure (up to 3 times)
  - Discard chunks older than 1 hour
- [ ] Handle offline mode:
  - Queue locally when no connection
  - Resume uploads when connection restored

#### 3.3 Android - Main Listening Screen
- [ ] Create Main Screen UI:
  - Large "Listening" indicator with pulse animation
  - Start/Stop listening toggle
  - Latest transcript preview card
  - Shows: speaker name, text snippet, timestamp
- [ ] Display recognized speakers list (just "You" for now)
- [ ] "Add Speaker" button (placeholder, implemented in Slice 4)
- [ ] Settings gear icon (placeholder)
- [ ] Connect to AudioCaptureService:
  - Start service when "Start Listening" tapped
  - Stop service when "Stop Listening" tapped
  - Observe transcript updates

#### 3.4 Integration Testing
- [ ] Test: Speak while listening → transcript appears in DB with correct speaker_name
- [ ] Test: Play audio from different person → filtered out (not transcribed)
- [ ] Test: Transcripts have correct timestamps
- [ ] Test: Service survives app backgrounding
- [ ] Test: Offline queueing works

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
- [ ] Fix S3 bucket: remove `publicReadAccess`, add server-side encryption
- [ ] Add ECR repository for backend Docker images
- [ ] Add ECS Fargate cluster
- [ ] Add ECS Task Definition:
  - 0.5 vCPU, 1GB RAM
  - Container from ECR
  - Environment variables for config
  - CloudWatch log group
- [ ] Add ECS Service:
  - Desired count: 1
  - Connect to ALB
- [ ] Add Application Load Balancer:
  - HTTPS listener (port 443)
  - HTTP redirect to HTTPS
  - Health check on `/health`
- [ ] Add IAM roles:
  - Task execution role (ECR pull, CloudWatch logs)
  - Task role (S3 access)
- [ ] Add ACM certificate (or use AWS default for initial testing)
- [ ] Enable pgvector extension on Aurora:
  - Run `CREATE EXTENSION vector` via migration
- [ ] Export ALB DNS name as CloudFormation output

#### 3.5.2 Deployment Pipeline
- [ ] Create deployment script:
  ```bash
  # Build and push Docker image
  docker build -t frontier-backend ./backend
  aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-repo>
  docker tag frontier-backend:latest <ecr-repo>:latest
  docker push <ecr-repo>:latest

  # Deploy infrastructure
  cd infra && cdk deploy

  # Force new ECS deployment
  aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment
  ```
- [ ] Create database migration script for Aurora
- [ ] Document environment variables needed in ECS task definition

#### 3.5.3 Configuration Updates
- [ ] Update Android app to support configurable API base URL
- [ ] Create production build variant pointing to ALB endpoint
- [ ] Update Next.js to use environment variable for API URL
- [ ] Set up environment variables in ECS task definition:
  - `DATABASE_URL` (Aurora endpoint)
  - `FIREBASE_PROJECT_ID`
  - `FIREBASE_PRIVATE_KEY`
  - `FIREBASE_CLIENT_EMAIL`
  - `OPENAI_API_KEY`
  - `AWS_S3_BUCKET`

#### 3.5.4 Validation Testing
- [ ] Test: `/health` returns 200 via ALB
- [ ] Test: `/health/ready` confirms Aurora connection
- [ ] Test: Android app can register user via AWS endpoint
- [ ] Test: Voice enrollment works end-to-end on AWS
- [ ] Test: Transcription pipeline works on AWS
- [ ] Test: CloudWatch logs show requests

### Demo Checkpoint
All functionality from Slices 1-3 works against AWS infrastructure. Android app connects to ALB endpoint, users are stored in Aurora, transcripts are processed and stored.

---

## Slice 4: Consented Speaker System

### Goals
- Implement multi-speaker consent enrollment
- Store consent audio in S3 as legal proof
- Enable verbal and manual revocation
- Transcribe consented speakers alongside primary user

### Tasks

#### 4.1 Backend - Consent Endpoints
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

#### 4.2 Android - Consent Flow
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

#### 4.3 Android - Speaker Management
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

#### 4.4 Integration Testing
- [ ] Test: Consent phrase accepted → speaker added → audio in S3
- [ ] Test: Invalid consent phrase → specific error returned
- [ ] Test: Consented speaker speaks → transcribed with their name
- [ ] Test: Verbal revocation by speaker → marked revoked with audio proof
- [ ] Test: Manual revocation by primary → marked revoked, no audio
- [ ] Test: Revoked speaker speaks → filtered out

### Demo Checkpoint
Primary user adds "Sarah" via consent phrase. Sarah's consent audio is stored in S3. When Sarah speaks, her speech is transcribed and attributed to her. Sarah can verbally revoke, or primary user can manually remove her.

---

## Slice 5: Chat & RAG Interface

### Goals
- Embed transcripts for semantic search
- Implement RAG retrieval with time-aware filtering
- Build chat UI with streaming responses and citations

### Tasks

#### 5.1 Backend - Embedding Service
- [ ] Create `EmbeddingService`:
  ```python
  class EmbeddingService:
      def __init__(self, openai_api_key: str):
          # Initialize OpenAI client

      async def embed_text(self, text: str) -> list[float]:
          # Call text-embedding-3-small API
          # Return 1536-dimensional embedding

      def prepare_transcript_for_embedding(self, transcript: Transcript) -> str:
          # Format: "[Speaker] text (time context)"
          # e.g., "[Sarah] The panel needs replacing (morning, January 15, 2025)"
  ```
- [ ] Update `POST /transcribe` to generate and store embeddings:
  - After transcription, embed the text
  - Store in `transcript.embedding`
- [ ] Create database migration to add HNSW index on embeddings:
  ```sql
  CREATE INDEX idx_transcripts_embedding
  ON transcripts USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```
- [ ] Backfill embeddings for existing transcripts (if any)

#### 5.2 Backend - Chat Service
- [ ] Implement time filter parsing:
  ```python
  def parse_time_filter(query: str) -> tuple[datetime | None, datetime | None]:
      # Parse "today", "yesterday", "this week", "last week"
      # Return (start_time, end_time) or (None, None)
  ```
- [ ] Implement vector search:
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
- [ ] Implement context builder with token management:
  ```python
  def build_chat_context(
      transcripts: list[Transcript],
      max_tokens: int = 6000
  ) -> str:
      # Build context string from transcripts
      # Truncate if exceeds token limit
  ```
- [ ] Implement `POST /chat` endpoint:
  - Accept `{ message, conversation_history }`
  - Parse time filter from message
  - Embed user query
  - Retrieve relevant transcripts via vector search
  - Build context with retrieved transcripts
  - Stream GPT-4 response with system prompt
  - Include citation metadata in response
- [ ] Define chat response streaming format:
  ```
  data: {"type": "text", "content": "Based on..."}
  data: {"type": "citation", "transcript_id": "...", "speaker": "...", "timestamp": "...", "location": "..."}
  data: {"type": "done"}
  ```

#### 5.3 Web - Chat Interface
- [ ] Install and configure Vercel AI SDK 5.x
- [ ] Create chat API route (`/api/chat`):
  - Proxy to backend `/chat` endpoint
  - Handle streaming responses
- [ ] Build Chat page UI:
  - Message list (user messages + assistant responses)
  - Input field with send button
  - Streaming text display
- [ ] Implement Citation Card component:
  - Collapsible card showing source transcript
  - Speaker name, timestamp, location
  - Quote from transcript
  - Expand/collapse on click
- [ ] Create empty state with suggested queries:
  - "What did we discuss at the job site yesterday?"
  - "Summarize my conversations from this week"
  - "What did Sarah say about the electrical work?"
- [ ] Add loading states and error handling
- [ ] Style with Tailwind CSS

#### 5.4 Integration Testing
- [ ] Test: Query "What did Sarah say about X" → relevant transcript returned
- [ ] Test: Query "yesterday" → only transcripts from yesterday
- [ ] Test: Citations display correctly with metadata
- [ ] Test: Streaming works smoothly
- [ ] Test: No transcripts found → appropriate message

### Demo Checkpoint
User asks "What did Sarah say about the junction box?" in web chat. System retrieves relevant transcript via semantic search, streams response with context, and displays citation card with speaker, time, and location.

---

## Slice 6: Polish & Location Context

### Goals
- Add GPS context to transcripts
- Polish UI across all platforms
- Create demo-ready experience with seeded data

### Tasks

#### 6.1 Android - Location Integration
- [ ] Request location permissions (fine + coarse)
- [ ] Create `LocationService`:
  - Get current location when audio chunk captured
  - Include lat/long in `/transcribe` request
- [ ] Update AudioCaptureService to include location data
- [ ] Display location in transcript preview on main screen

#### 6.2 Backend - Location Enhancement
- [ ] (Optional) Add reverse geocoding service:
  - Convert lat/long to human-readable address
  - Store in `transcript.location_name`
  - Use Google Maps API or similar
- [ ] Include location in chat context for RAG

#### 6.3 Web - Location Display
- [ ] Update Citation Card to show location:
  - Display coordinates or address if available
  - Format: "Jan 15, 2025 · 9:34 AM · 123 Main St"

#### 6.4 Android - UI Polish
- [ ] Add pulse animation to "Listening" indicator
- [ ] Add waveform animation during recording (enrollment, consent)
- [ ] Implement proper empty states:
  - No transcripts yet
  - No speakers added
- [ ] Add loading indicators for API calls
- [ ] Implement error toasts/snackbars
- [ ] Add pull-to-refresh on transcript list
- [ ] Review and polish all screen transitions

#### 6.5 Web - UI Polish
- [ ] Add loading skeletons for chat
- [ ] Smooth streaming text animation
- [ ] Polish citation card expand/collapse animation
- [ ] Add user dropdown menu (logout, settings placeholder)
- [ ] Responsive design for mobile web
- [ ] Empty state illustration

#### 6.6 Demo Data & Script
- [ ] Create seed script for demo data:
  - Demo user account
  - 2-3 consented speakers
  - 20-30 realistic transcripts over past week
  - Variety of topics (construction, electrical, scheduling)
  - Multiple locations
- [ ] Write demo script/walkthrough:
  1. Show Android app enrollment
  2. Add a consented speaker
  3. Show listening and transcription
  4. Switch to web, ask questions
  5. Show citations and context
- [ ] Test full demo flow end-to-end

#### 6.7 Final Testing & Documentation
- [ ] End-to-end test all user flows
- [ ] Test on physical Android device
- [ ] Performance testing (transcription latency, chat response time)
- [ ] Document deployment process
- [ ] Document environment setup for future developers

### Demo Checkpoint
Complete, polished application ready for client demonstration. User can enroll voice, add speakers with consent, capture transcriptions with location data, and query their conversation history via natural language chat with rich citations.

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
AWS_S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
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

*Last updated: November 2025*
