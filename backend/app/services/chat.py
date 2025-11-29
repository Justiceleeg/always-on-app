"""Chat service for RAG-based conversation with transcript context."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from openai import AsyncOpenAI
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.transcript import Transcript
from app.services.embedding import get_embedding_service

logger = structlog.get_logger()

# Token limits (rough estimates)
MAX_CONTEXT_TOKENS = 6000
AVG_CHARS_PER_TOKEN = 4


class ChatService:
    """
    Service for RAG-based chat with transcript context.

    Features:
    - Time filter parsing from natural language queries (timezone-aware)
    - Vector similarity search using pgvector
    - Context building with token management
    - Streaming responses via OpenAI GPT-4
    """

    CHAT_MODEL = "gpt-4o"

    def __init__(self, openai_api_key: str | None = None):
        """
        Initialize the chat service.

        Args:
            openai_api_key: OpenAI API key. If not provided, uses config.
        """
        settings = get_settings()
        api_key = openai_api_key or settings.openai_api_key

        if not api_key:
            raise ValueError("OpenAI API key is required for chat")

        self._client = AsyncOpenAI(api_key=api_key)
        self._embedding_service = get_embedding_service()
        logger.info("ChatService initialized", model=self.CHAT_MODEL)

    def parse_time_filter(
        self,
        query: str,
        client_timezone: str = "UTC",
    ) -> tuple[datetime | None, datetime | None]:
        """
        Parse time filter from natural language query.

        Uses the client's timezone to correctly interpret "today", "yesterday", etc.
        Returns UTC datetimes for database queries.

        Supported patterns:
        - "today", "from today"
        - "yesterday"
        - "this week"
        - "last week"
        - "this month"
        - "last month"

        Args:
            query: User's chat message
            client_timezone: Client's timezone (e.g., "America/Los_Angeles", "UTC")

        Returns:
            Tuple of (start_time, end_time) in UTC, or (None, None) if no time filter found
        """
        query_lower = query.lower()

        # Get current time in client's timezone
        try:
            tz = ZoneInfo(client_timezone)
        except Exception:
            logger.warning(
                "Invalid timezone, falling back to UTC",
                timezone=client_timezone,
            )
            tz = ZoneInfo("UTC")

        # Get "now" in client's local time
        now_utc = datetime.now(ZoneInfo("UTC"))
        now_local = now_utc.astimezone(tz)

        # Calculate "today" start in client's local time, then convert to UTC
        today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

        # Today
        if any(pattern in query_lower for pattern in ["today", "from today"]):
            start_utc = today_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            end_utc = now_utc.replace(tzinfo=None)
            logger.info(
                "Parsed time filter: today",
                client_tz=client_timezone,
                start_utc=start_utc.isoformat(),
                end_utc=end_utc.isoformat(),
            )
            return (start_utc, end_utc)

        # Yesterday
        if "yesterday" in query_lower:
            yesterday_start_local = today_start_local - timedelta(days=1)
            start_utc = yesterday_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            end_utc = today_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            logger.info(
                "Parsed time filter: yesterday",
                client_tz=client_timezone,
                start_utc=start_utc.isoformat(),
                end_utc=end_utc.isoformat(),
            )
            return (start_utc, end_utc)

        # This week (Monday to now)
        if "this week" in query_lower:
            days_since_monday = now_local.weekday()
            week_start_local = today_start_local - timedelta(days=days_since_monday)
            start_utc = week_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            end_utc = now_utc.replace(tzinfo=None)
            logger.info(
                "Parsed time filter: this week",
                client_tz=client_timezone,
                start_utc=start_utc.isoformat(),
                end_utc=end_utc.isoformat(),
            )
            return (start_utc, end_utc)

        # Last week (previous Monday to Sunday)
        if "last week" in query_lower:
            days_since_monday = now_local.weekday()
            this_week_start_local = today_start_local - timedelta(days=days_since_monday)
            last_week_start_local = this_week_start_local - timedelta(days=7)
            start_utc = last_week_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            end_utc = this_week_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            logger.info(
                "Parsed time filter: last week",
                client_tz=client_timezone,
                start_utc=start_utc.isoformat(),
                end_utc=end_utc.isoformat(),
            )
            return (start_utc, end_utc)

        # This month
        if "this month" in query_lower:
            month_start_local = today_start_local.replace(day=1)
            start_utc = month_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            end_utc = now_utc.replace(tzinfo=None)
            logger.info(
                "Parsed time filter: this month",
                client_tz=client_timezone,
                start_utc=start_utc.isoformat(),
                end_utc=end_utc.isoformat(),
            )
            return (start_utc, end_utc)

        # Last month
        if "last month" in query_lower:
            month_start_local = today_start_local.replace(day=1)
            if month_start_local.month == 1:
                last_month_start_local = month_start_local.replace(
                    year=month_start_local.year - 1, month=12
                )
            else:
                last_month_start_local = month_start_local.replace(
                    month=month_start_local.month - 1
                )
            start_utc = last_month_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            end_utc = month_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            logger.info(
                "Parsed time filter: last month",
                client_tz=client_timezone,
                start_utc=start_utc.isoformat(),
                end_utc=end_utc.isoformat(),
            )
            return (start_utc, end_utc)

        # No time filter found
        return (None, None)

    async def vector_search(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        user_id: UUID,
        time_start: datetime | None = None,
        time_end: datetime | None = None,
        limit: int = 10,
    ) -> list[Transcript]:
        """
        Perform vector similarity search on transcripts.

        Args:
            db: Database session
            query_embedding: Embedding of user's query
            user_id: User ID to filter transcripts
            time_start: Optional start time filter (UTC)
            time_end: Optional end time filter (UTC)
            limit: Maximum number of results

        Returns:
            List of similar transcripts ordered by relevance
        """
        # Build base conditions
        conditions = [
            Transcript.user_id == user_id,
            Transcript.embedding.isnot(None),
        ]

        # Add time filters if provided
        if time_start:
            conditions.append(Transcript.timestamp_start >= time_start)
        if time_end:
            conditions.append(Transcript.timestamp_start <= time_end)

        # Query using pgvector cosine distance operator (<=>)
        # Lower distance = more similar
        query = (
            select(Transcript)
            .where(and_(*conditions))
            .order_by(Transcript.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )

        result = await db.execute(query)
        transcripts = list(result.scalars().all())

        logger.info(
            "Vector search completed",
            user_id=str(user_id),
            results_count=len(transcripts),
            time_filter=bool(time_start or time_end),
        )

        return transcripts

    def build_chat_context(
        self,
        transcripts: list[Transcript],
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> str:
        """
        Build context string from transcripts for the chat prompt.

        Args:
            transcripts: List of relevant transcripts
            max_tokens: Maximum tokens for context (rough estimate)

        Returns:
            Formatted context string
        """
        if not transcripts:
            return ""

        max_chars = max_tokens * AVG_CHARS_PER_TOKEN
        context_parts = []
        total_chars = 0

        for transcript in transcripts:
            # Format each transcript with metadata
            timestamp = transcript.timestamp_start.strftime("%B %d, %Y at %I:%M %p")
            location = f" at {transcript.location_name}" if transcript.location_name else ""

            entry = f"[{timestamp}{location}] {transcript.speaker_name}: {transcript.transcript_text}"

            # Check if adding this would exceed limit
            if total_chars + len(entry) > max_chars:
                # Try to fit a truncated version
                remaining = max_chars - total_chars - 50  # Leave room for ellipsis
                if remaining > 100:
                    entry = entry[:remaining] + "..."
                    context_parts.append(entry)
                break

            context_parts.append(entry)
            total_chars += len(entry) + 2  # +2 for newlines

        return "\n\n".join(context_parts)

    def get_system_prompt(self, context: str, user_name: str) -> str:
        """
        Build the system prompt for the chat model.

        Args:
            context: Transcript context from vector search
            user_name: Name of the user for personalization

        Returns:
            System prompt string
        """
        base_prompt = f"""You are a helpful assistant that helps {user_name} recall and search through their recorded conversations and transcripts.

You have access to transcripts from {user_name}'s conversations. When answering questions:
1. Use the provided transcript context to answer questions accurately
2. Always cite the specific date, time, and speaker when referencing information from transcripts
3. If the information isn't in the provided context, say so - don't make things up
4. Be concise but thorough in your responses
5. When quoting from transcripts, use quotation marks

"""

        if context:
            base_prompt += f"""Here are the relevant transcripts from {user_name}'s conversations:

{context}

---

Use the above transcripts to answer the user's question. Reference specific quotes and timestamps when relevant."""
        else:
            base_prompt += f"""No relevant transcripts were found for this query. Let {user_name} know that you couldn't find any matching conversations, and suggest they try a different search term or time period."""

        return base_prompt

    async def get_chat_response_stream(
        self,
        message: str,
        conversation_history: list[dict],
        context: str,
        user_name: str,
    ):
        """
        Generate a streaming chat response.

        Args:
            message: User's current message
            conversation_history: Previous messages in the conversation
            context: Transcript context from vector search
            user_name: Name of the user

        Yields:
            Response chunks as they're generated
        """
        system_prompt = self.get_system_prompt(context, user_name)

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current message
        messages.append({"role": "user", "content": message})

        logger.info(
            "Sending chat request",
            model=self.CHAT_MODEL,
            message_count=len(messages),
            context_length=len(context),
        )

        try:
            stream = await self._client.chat.completions.create(
                model=self.CHAT_MODEL,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=1000,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("Chat completion failed", error=str(e))
            raise ValueError(f"Failed to generate chat response: {str(e)}")


# Singleton instance for reuse across requests
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get or create the singleton ChatService instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
