import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog
from app.routers import health, auth, enrollment, transcription
from app.config import get_settings

# Configure standard library logging to output to stdout
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    logger.info("Starting Frontier Audio API", firebase_configured=bool(settings.firebase_project_id))
    yield
    logger.info("Shutting down Frontier Audio API")


app = FastAPI(
    title="Frontier Audio API",
    description="Always-On Selective Speaker Transcription API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Log request
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
    )

    response = await call_next(request)

    # Log response
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    return response


# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(enrollment.router)
app.include_router(transcription.router)
