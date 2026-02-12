"""Tests for the AI Coach feature.

Unit tests (5):
1. test_send_message_happy_path -- sends message and gets AI response
2. test_get_history_pagination -- returns paginated history with has_more
3. test_rate_limit_exceeded -- 51st message returns 429
4. test_premium_only_free_user -- free user gets 403
5. test_empty_message_validation -- empty message returns 422

Endpoint tests (4):
6. test_send_message_endpoint -- POST /api/coach/message -> 200
7. test_get_history_endpoint -- GET /api/coach/history -> 200
8. test_premium_guard_message_endpoint -- POST /api/coach/message (free) -> 403
9. test_premium_guard_history_endpoint -- GET /api/coach/history (free) -> 403
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.chat_message import ChatMessage
from app.models.user import User


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    user_id: uuid.UUID | None = None,
    subscription_status: str = "premium",
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id or FAKE_USER_ID
    user.telegram_id = FAKE_TELEGRAM_ID
    user.subscription_status = subscription_status
    user.onboarding_complete = True
    return user


def _make_chat_message(
    role: str = "user",
    content: str = "test message",
    user_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock ChatMessage object."""
    msg = MagicMock(spec=ChatMessage)
    msg.id = uuid.uuid4()
    msg.user_id = user_id or FAKE_USER_ID
    msg.role = role
    msg.content = content
    msg.created_at = datetime.now(timezone.utc)
    return msg


def _override_dependencies(app, session, user_id=FAKE_USER_ID):
    """Override get_db and get_current_user dependencies on the app."""
    from app.dependencies import get_db, get_current_user

    async def _override_get_db():
        yield session

    async def _override_get_current_user():
        return {"user_id": user_id, "telegram_id": FAKE_TELEGRAM_ID}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user


# ===========================================================================
# Unit tests for coach service
# ===========================================================================


class TestSendMessage:
    """Unit tests for coach_service.send_message."""

    @patch("app.services.coach_service.llm_client")
    async def test_send_message_happy_path(self, mock_llm):
        """Sends message and gets AI response."""
        from app.services.coach_service import send_message

        mock_llm.chat_completion = AsyncMock(
            return_value="Это отличный вопрос! Попробуйте технику осознанного питания."
        )

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # count today's messages -> 0
                result_mock.scalar_one.return_value = 0
            elif call_count["n"] == 2:
                # active patterns -> empty
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result_mock.scalars.return_value = scalars_mock
            elif call_count["n"] == 3:
                # recent food entries -> empty
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result_mock.scalars.return_value = scalars_mock
            elif call_count["n"] == 4:
                # recent chat messages -> empty
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result_mock.scalars.return_value = scalars_mock
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await send_message(session, FAKE_USER_ID, "Как справиться с вечерним перекусом?")

        assert result.message.role == "assistant"
        assert "осознанного питания" in result.message.content
        assert session.add.call_count == 2  # user msg + assistant msg
        mock_llm.chat_completion.assert_awaited_once()

    @patch("app.services.coach_service.llm_client")
    async def test_rate_limit_exceeded(self, mock_llm):
        """51st message in a day returns 429."""
        from app.services.coach_service import send_message
        from fastapi import HTTPException

        mock_llm.chat_completion = AsyncMock()

        session = AsyncMock()

        # count today's messages -> 50 (at limit)
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 50
        session.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(HTTPException) as exc_info:
            await send_message(session, FAKE_USER_ID, "test")

        assert exc_info.value.status_code == 429
        mock_llm.chat_completion.assert_not_awaited()


class TestGetHistory:
    """Unit tests for coach_service.get_history."""

    async def test_get_history_pagination(self):
        """Returns paginated history with has_more flag."""
        from app.services.coach_service import get_history

        msg1 = _make_chat_message(role="user", content="Привет")
        msg2 = _make_chat_message(role="assistant", content="Здравствуйте!")

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # count total -> 5
                result_mock.scalar_one.return_value = 5
            else:
                # fetch messages
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [msg2, msg1]  # DESC order
                result_mock.scalars.return_value = scalars_mock
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_history(session, FAKE_USER_ID, limit=2, offset=0)

        assert len(result.messages) == 2
        assert result.has_more is True
        # Messages should be in chronological order (reversed)
        assert result.messages[0].content == "Привет"
        assert result.messages[1].content == "Здравствуйте!"

    async def test_get_history_no_more(self):
        """Returns has_more=False when all messages fit."""
        from app.services.coach_service import get_history

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # count total -> 1
                result_mock.scalar_one.return_value = 1
            else:
                msg = _make_chat_message(role="user", content="Test")
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [msg]
                result_mock.scalars.return_value = scalars_mock
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_history(session, FAKE_USER_ID, limit=20, offset=0)

        assert len(result.messages) == 1
        assert result.has_more is False


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestCoachEndpoints:
    """Endpoint tests for /api/coach/*."""

    @patch("app.services.coach_service.llm_client")
    async def test_send_message_endpoint(self, mock_llm, app, client: AsyncClient):
        """POST /api/coach/message -> 200 with AI response."""
        mock_llm.chat_completion = AsyncMock(return_value="Совет коуча.")

        session = AsyncMock()

        # Mock user lookup for premium check
        premium_user = _make_user(subscription_status="premium")
        session.get = AsyncMock(return_value=premium_user)

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # count today's messages
                result_mock.scalar_one.return_value = 0
            elif call_count["n"] == 2:
                # patterns
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result_mock.scalars.return_value = scalars_mock
            elif call_count["n"] == 3:
                # food entries
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result_mock.scalars.return_value = scalars_mock
            elif call_count["n"] == 4:
                # chat history
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result_mock.scalars.return_value = scalars_mock
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        session.add = MagicMock()
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/coach/message",
                json={"content": "Помогите с вечерним перееданием"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["message"]["role"] == "assistant"
        assert body["message"]["content"] == "Совет коуча."

    async def test_get_history_endpoint(self, app, client: AsyncClient):
        """GET /api/coach/history -> 200 with messages."""
        session = AsyncMock()

        # Mock user lookup for premium check
        premium_user = _make_user(subscription_status="premium")
        session.get = AsyncMock(return_value=premium_user)

        msg = _make_chat_message(role="user", content="Тест")

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # count total
                result_mock.scalar_one.return_value = 1
            else:
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [msg]
                result_mock.scalars.return_value = scalars_mock
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/coach/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert len(body["messages"]) == 1
        assert body["has_more"] is False

    async def test_premium_guard_message_endpoint(self, app, client: AsyncClient):
        """POST /api/coach/message as free user -> 403."""
        session = AsyncMock()

        free_user = _make_user(subscription_status="free")
        session.get = AsyncMock(return_value=free_user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/coach/message",
                json={"content": "test"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 403

    async def test_premium_guard_history_endpoint(self, app, client: AsyncClient):
        """GET /api/coach/history as free user -> 403."""
        session = AsyncMock()

        free_user = _make_user(subscription_status="free")
        session.get = AsyncMock(return_value=free_user)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/coach/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 403

    async def test_empty_message_validation(self, app, client: AsyncClient):
        """POST /api/coach/message with empty content -> 422."""
        session = AsyncMock()

        premium_user = _make_user(subscription_status="premium")
        session.get = AsyncMock(return_value=premium_user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/coach/message",
                json={"content": ""},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422
