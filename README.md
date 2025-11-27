# Frontier Audio MVP

Always-On Selective Speaker Transcription - An audio capture and transcription system that identifies consented speakers and provides RAG-based querying.

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
- Python 3.11+
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

- **Backend**: FastAPI 0.100+, SQLAlchemy 2.0+, Python 3.11+
- **Database**: PostgreSQL 17 with pgvector 0.5+
- **Authentication**: Firebase Auth
- **Speech Processing**: SpeechBrain (speaker verification), OpenAI Whisper (transcription)
- **Embeddings**: OpenAI text-embedding-3-small
- **Android**: Kotlin 2.0+, Jetpack Compose, SDK API 35+
- **Web**: Next.js 16+, Vercel AI SDK 5.x

## Development Workflow

See `docs/IMPLEMENTATION_PLAN.md` for the vertical slice implementation approach.

## License

Proprietary - All rights reserved
