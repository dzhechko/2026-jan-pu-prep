"""AI Coach service – CBT-informed chat with LLM."""

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import llm_client
from app.ai.prompts import COACH_SYSTEM
from app.models.chat_message import ChatMessage
from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern
from app.schemas.coach import (
    CoachHistoryResponse,
    CoachMessageData,
    CoachMessageResponse,
)

logger = structlog.get_logger()

MAX_DAILY_MESSAGES = 50
HISTORY_CONTEXT_LIMIT = 10


async def _count_today_messages(db: AsyncSession, user_id: UUID) -> int:
    """Count user messages sent today."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    stmt = (
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= today_start,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def _get_recent_chat_messages(
    db: AsyncSession, user_id: UUID, limit: int = HISTORY_CONTEXT_LIMIT
) -> list[ChatMessage]:
    """Load recent chat messages for context window."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().all())
    messages.reverse()  # Chronological order
    return messages


async def _get_user_context(db: AsyncSession, user_id: UUID) -> dict[str, str]:
    """Build user context for the system prompt."""
    # Active patterns
    pattern_stmt = select(Pattern).where(
        Pattern.user_id == user_id,
        Pattern.active.is_(True),
    )
    pattern_result = await db.execute(pattern_stmt)
    patterns = pattern_result.scalars().all()

    # Recent food entries (last 5)
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    entry_stmt = (
        select(FoodEntry)
        .where(FoodEntry.user_id == user_id, FoodEntry.logged_at >= cutoff)
        .order_by(FoodEntry.logged_at.desc())
        .limit(5)
    )
    entry_result = await db.execute(entry_stmt)
    entries = entry_result.scalars().all()

    # Format for prompt
    pattern_texts = [f"- {p.type}: {p.description_ru}" for p in patterns]
    patterns_str = "\n".join(pattern_texts) if pattern_texts else "Пока не обнаружены"

    entry_texts = []
    for e in entries:
        mood_str = f", настроение: {e.mood}" if e.mood else ""
        entry_texts.append(f"- {e.raw_text} ({e.total_calories or '?'} ккал{mood_str})")
    entries_str = "\n".join(entry_texts) if entry_texts else "Нет записей"

    # Risk level: simple heuristic based on pattern count
    if len(patterns) >= 3:
        risk = "высокий"
    elif len(patterns) >= 1:
        risk = "средний"
    else:
        risk = "низкий"

    return {
        "patterns": patterns_str,
        "recent_entries": entries_str,
        "risk_level": risk,
    }


async def send_message(
    db: AsyncSession,
    user_id: UUID,
    content: str,
) -> CoachMessageResponse:
    """Send a message to the AI coach and get a response."""
    # Rate limit check
    today_count = await _count_today_messages(db, user_id)
    if today_count >= MAX_DAILY_MESSAGES:
        raise HTTPException(
            status_code=429,
            detail="Достигнут дневной лимит сообщений (50). Попробуйте завтра.",
        )

    # Load user context for system prompt
    context = await _get_user_context(db, user_id)
    system_prompt = COACH_SYSTEM.format(**context)

    # Load recent chat history
    history = await _get_recent_chat_messages(db, user_id)

    # Build messages array
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": content})

    # Call LLM
    logger.info("coach_message_sent", user_id=str(user_id))
    response_text = await llm_client.chat_completion(
        messages=messages,
        temperature=0.7,
        max_tokens=512,
    )

    now = datetime.now(timezone.utc)

    # Save user message
    user_msg = ChatMessage(
        user_id=user_id,
        role="user",
        content=content,
        created_at=now,
    )
    db.add(user_msg)

    # Save assistant response
    assistant_msg_id = uuid.uuid4()
    assistant_msg = ChatMessage(
        id=assistant_msg_id,
        user_id=user_id,
        role="assistant",
        content=response_text,
        created_at=now,
    )
    db.add(assistant_msg)

    await db.flush()

    logger.info("coach_response_generated", user_id=str(user_id))

    return CoachMessageResponse(
        message=CoachMessageData(
            id=assistant_msg_id,
            role="assistant",
            content=response_text,
            created_at=now,
        )
    )


async def get_history(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> CoachHistoryResponse:
    """Get paginated chat history."""
    # Count total messages
    count_stmt = (
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.user_id == user_id)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Fetch messages
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().all())
    messages.reverse()  # Chronological order

    has_more = (offset + limit) < total

    return CoachHistoryResponse(
        messages=[
            CoachMessageData(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
        has_more=has_more,
    )
