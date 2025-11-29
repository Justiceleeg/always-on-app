# Frontier Audio MVP

An always-on audio capture system designed for frontline workers. It continuously listens, identifies consented speakers via voiceprint recognition, transcribes their conversations, and provides a searchable chat interface powered by RAG.

## Features

- **Always-on capture** – Background audio recording on Android devices
- **Speaker verification** – ECAPA-TDNN voiceprint matching ensures only enrolled speakers are transcribed
- **Consent management** – Verbal consent with recorded proof; supports revocation
- **Semantic search** – Query past conversations in natural language via chat UI
- **Location tagging** – Transcripts tagged with GPS coordinates and timestamps
- **Privacy-first** – Unknown speakers are filtered out entirely

## Architecture

```
┌──────────────┐         ┌──────────────┐
│ Android App  │         │  Next.js Web │
│  (Capture)   │         │  (Chat UI)   │
└──────┬───────┘         └───────┬──────┘
       │                         │
       └────────────┬────────────┘
                    │
       ┌────────────▼────────────┐
       │     FastAPI Backend     │
       │      (ECS Fargate)      │
       │                         │
       │  • Speaker Verification │
       │  • Transcription        │
       │  • RAG Chat Engine      │
       └────────────┬────────────┘
                    │
       ┌────────────▼────────────┐
       │  PostgreSQL + pgvector  │
       │   (Aurora Serverless)   │
       └─────────────────────────┘
```

**Data flow:**
1. Android captures audio chunks → Backend verifies speaker via voiceprint
2. Matched audio sent to Whisper API → Transcript + embedding stored in pgvector
3. Web chat queries embeddings → GPT-4 generates answers with citations

## Project Structure

```
always-on-app/
├── docs/           # Documentation and specifications
├── infra/          # AWS CDK infrastructure code
├── backend/        # FastAPI backend service
├── android/        # Android app (Kotlin/Jetpack Compose)
├── web/            # Next.js web application
└── scripts/        # Utility scripts
```

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.12 (required for SpeechBrain/PyTorch compatibility)
- Node.js 18+ (for web app)
- Android Studio (for Android app)
- Firebase project with Authentication enabled

### 1. Environment Setup

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Configure the following in `.env`:
- `FIREBASE_PROJECT_ID`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_CLIENT_EMAIL` - From Firebase Console > Project Settings > Service Accounts
- `OPENAI_API_KEY` - From OpenAI dashboard

### 2. Start Local Services

Start PostgreSQL with pgvector:

```bash
docker-compose up db -d
```

This starts:
- PostgreSQL 17 with pgvector extension on port 5432
- Database: `frontier_audio`
- Credentials: `frontier` / `frontier_dev`

### 3. Run Backend

Option A - With Docker:
```bash
docker-compose up backend
```

Option B - Without Docker (for development):
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### 4. Verify Setup

Check health endpoints:
```bash
# Basic health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/health/ready
```

### API Documentation

Once running, view API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, SQLAlchemy 2.0, Python 3.12 |
| **Database** | PostgreSQL 17, pgvector (HNSW indexing) |
| **ML/AI** | SpeechBrain ECAPA-TDNN, OpenAI Whisper, GPT-4, text-embedding-3-small |
| **Android** | Kotlin 2.0, Jetpack Compose, Hilt, API 35+ |
| **Web** | Next.js, React 19, Vercel AI SDK, Tailwind CSS |
| **Auth** | Firebase Authentication |
| **Infra** | AWS CDK, ECS Fargate, Aurora Serverless v2, ALB |

## Deployment

- **Backend**: AWS ECS Fargate behind Application Load Balancer
- **Database**: Aurora Serverless v2 (PostgreSQL-compatible)
- **Web**: Vercel
- **Infrastructure**: Managed via AWS CDK (`infra/`)

## Documentation

- `docs/PRD_Frontier_Audio_MVP.md` – Product requirements
- `docs/IMPLEMENTATION_PLAN.md` – Development approach

## License

Proprietary - All rights reserved
