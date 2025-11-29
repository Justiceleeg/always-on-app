"""Chat endpoints for RAG-based conversation with transcript context."""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models.user import User
from app.models.transcript import Transcript
from app.schemas.chat import ChatRequest, CitationSource
from app.services.firebase_auth import verify_firebase_token, FirebaseUser
from app.services.chat import get_chat_service
from app.services.embedding import get_embedding_service

logger = structlog.get_logger()

router = APIRouter(tags=["chat"])


async def generate_sse_stream(
    message: str,
    conversation_history: list[dict],
    transcripts: list[Transcript],
    user_name: str,
):
    """
    Generate Server-Sent Events stream for chat response.

    SSE Format:
    - data: {"type": "text", "content": "..."}
    - data: {"type": "citation", "transcript_id": "...", ...}
    - data: {"type": "done"}
    """
    chat_service = get_chat_service()

    # Build context from transcripts
    context = chat_service.build_chat_context(transcripts)

    # Stream the response
    try:
        async for chunk in chat_service.get_chat_response_stream(
            message=message,
            conversation_history=conversation_history,
            context=context,
            user_name=user_name,
        ):
            event_data = {"type": "text", "content": chunk}
            yield f"data: {json.dumps(event_data)}\n\n"

        # Send citations after the response is complete
        for transcript in transcripts[:5]:  # Limit to top 5 citations
            citation = {
                "type": "citation",
                "transcript_id": str(transcript.id),
                "speaker_name": transcript.speaker_name,
                "timestamp": transcript.timestamp_start.isoformat(),
                "location": transcript.location_name,
                "text_snippet": transcript.transcript_text[:200] + "..."
                if len(transcript.transcript_text) > 200
                else transcript.transcript_text,
            }
            yield f"data: {json.dumps(citation)}\n\n"

        # Send done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error("Error during chat stream", error=str(e))
        error_data = {"type": "error", "message": str(e)}
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    firebase_user: FirebaseUser = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with your transcripts using RAG.

    This endpoint:
    1. Parses time filters from the message (e.g., "today", "yesterday", "this week")
    2. Embeds the query and performs vector similarity search
    3. Streams a GPT-4 response with relevant transcript context
    4. Includes citation metadata for source transcripts

    Returns a Server-Sent Events stream with the following event types:
    - {"type": "text", "content": "..."}: Response text chunks
    - {"type": "citation", ...}: Citation metadata for source transcripts
    - {"type": "done"}: Stream complete
    - {"type": "error", "message": "..."}: Error occurred
    """
    # Get user from database
    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_user.uid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first.",
        )

    chat_service = get_chat_service()
    embedding_service = get_embedding_service()

    # Parse time filter from message using client's timezone
    time_start, time_end = chat_service.parse_time_filter(
        request.message,
        client_timezone=request.timezone,
    )

    logger.info(
        "Processing chat request",
        user_id=str(user.id),
        user_email=user.email,
        firebase_uid=firebase_user.uid,
        message_length=len(request.message),
        has_time_filter=bool(time_start or time_end),
        timezone=request.timezone,
    )

    # Embed the query
    try:
        query_embedding = await embedding_service.embed_text(request.message)
    except Exception as e:
        logger.error("Failed to embed query", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process query",
        )

    # Perform vector search
    transcripts = await chat_service.vector_search(
        db=db,
        query_embedding=query_embedding,
        user_id=user.id,
        time_start=time_start,
        time_end=time_end,
        limit=10,
    )

    logger.info(
        "Retrieved transcripts for chat",
        user_id=str(user.id),
        transcript_count=len(transcripts),
    )

    # Convert conversation history to dict format
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.conversation_history
    ]

    # Return streaming response
    return StreamingResponse(
        generate_sse_stream(
            message=request.message,
            conversation_history=conversation_history,
            transcripts=transcripts,
            user_name=user.name,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
