"""Tests for the data-privacy feature (US-7.1 / US-7.2).

Unit tests for privacy_service (7 tests):
1. test_export_user_data -- returns all user data sections
2. test_export_user_data_empty -- user with no data returns empty lists
3. test_export_includes_food_entries -- food entries serialized correctly
4. test_export_includes_patterns -- patterns serialized correctly
5. test_delete_account_success -- deletes user, returns True
6. test_delete_account_not_found -- returns False when user doesn't exist
7. test_delete_cancels_subscription -- calls cancel_subscription before delete

Endpoint tests (4 tests):
8.  test_export_endpoint -- POST /api/privacy/export -> 200
9.  test_delete_endpoint_success -- POST /api/privacy/delete with confirmation="УДАЛИТЬ" -> 200
10. test_delete_endpoint_wrong_confirmation -- POST with wrong text -> 400
11. test_delete_endpoint_missing_confirmation -- POST with empty body -> 422 (validation)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.ai_profile import AIProfile
from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern
from app.models.insight import Insight
from app.models.lesson import CBTLesson, UserLessonProgress
from app.models.subscription import Subscription
from app.models.invite import Invite


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: uuid.UUID = FAKE_USER_ID) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.telegram_id = FAKE_TELEGRAM_ID
    user.telegram_username = "testuser"
    user.first_name = "Test"
    user.language_code = "ru"
    user.subscription_status = "free"
    user.subscription_expires_at = None
    user.insights_received = 0
    user.onboarding_complete = True
    user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    return user


def _make_food_entry(user_id: uuid.UUID = FAKE_USER_ID) -> MagicMock:
    """Create a mock FoodEntry object."""
    entry = MagicMock(spec=FoodEntry)
    entry.id = uuid.uuid4()
    entry.user_id = user_id
    entry.raw_text = "Завтрак: каша"
    entry.parsed_items = [{"name": "каша", "calories": 200}]
    entry.total_calories = 200
    entry.mood = "ok"
    entry.context = "home"
    entry.logged_at = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)
    entry.day_of_week = 6
    entry.hour = 8
    entry.created_at = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)
    return entry


def _make_pattern(user_id: uuid.UUID = FAKE_USER_ID) -> MagicMock:
    """Create a mock Pattern object."""
    pattern = MagicMock(spec=Pattern)
    pattern.id = uuid.uuid4()
    pattern.user_id = user_id
    pattern.type = "time"
    pattern.description_ru = "Тестовый паттерн"
    pattern.confidence = 0.8
    pattern.evidence = {"avg_lunch_calories": 200.0}
    pattern.active = True
    pattern.discovered_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
    return pattern


def _make_insight(user_id: uuid.UUID = FAKE_USER_ID) -> MagicMock:
    """Create a mock Insight object."""
    insight = MagicMock(spec=Insight)
    insight.id = uuid.uuid4()
    insight.user_id = user_id
    insight.pattern_id = None
    insight.title = "Тестовый инсайт"
    insight.body = "Тело инсайта"
    insight.action = "Действие"
    insight.type = "general"
    insight.seen = False
    insight.is_locked = False
    insight.created_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
    return insight


def _make_subscription(user_id: uuid.UUID = FAKE_USER_ID) -> MagicMock:
    """Create a mock Subscription object."""
    sub = MagicMock(spec=Subscription)
    sub.id = uuid.uuid4()
    sub.user_id = user_id
    sub.plan = "premium"
    sub.provider = "telegram"
    sub.provider_id = "tg_123"
    sub.status = "active"
    sub.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sub.expires_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
    sub.cancelled_at = None
    return sub


def _make_invite(inviter_id: uuid.UUID = FAKE_USER_ID) -> MagicMock:
    """Create a mock Invite object."""
    invite = MagicMock(spec=Invite)
    invite.id = uuid.uuid4()
    invite.inviter_id = inviter_id
    invite.invite_code = "ABC123"
    invite.invitee_id = None
    invite.redeemed_at = None
    invite.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    return invite


def _make_lesson_progress(user_id: uuid.UUID = FAKE_USER_ID) -> MagicMock:
    """Create a mock UserLessonProgress object with a joined lesson."""
    lp = MagicMock(spec=UserLessonProgress)
    lp.user_id = user_id
    lp.lesson_id = uuid.uuid4()
    lp.completed_at = datetime(2026, 2, 5, tzinfo=timezone.utc)

    lesson = MagicMock(spec=CBTLesson)
    lesson.title = "Урок 1: Основы CBT"
    lp.lesson = lesson
    return lp


def _override_dependencies(app, session, user_id=FAKE_USER_ID):
    """Override get_db and get_current_user dependencies on the app."""
    from app.dependencies import get_db, get_current_user

    async def _override_get_db():
        yield session

    async def _override_get_current_user():
        return {"user_id": user_id, "telegram_id": FAKE_TELEGRAM_ID}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user


def _make_mock_db_for_export(
    user=None,
    ai_profile=None,
    food_entries=None,
    patterns=None,
    insights=None,
    lesson_progress=None,
    subscriptions=None,
    invites=None,
):
    """Create a mock DB session for export_user_data testing.

    Simulates multiple sequential db.execute() calls, each returning
    the appropriate mock result.
    """
    session = AsyncMock()

    food_entries = food_entries or []
    patterns = patterns or []
    insights = insights or []
    lesson_progress = lesson_progress or []
    subscriptions = subscriptions or []
    invites = invites or []

    # Build the side_effect list in the order the service calls execute():
    # 1. User query
    # 2. AIProfile query
    # 3. FoodEntry query
    # 4. Pattern query
    # 5. Insight query
    # 6. UserLessonProgress query
    # 7. Subscription query
    # 8. Invite query

    results = []

    # 1. User
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    results.append(user_result)

    if user is not None:
        # 2. AI profile
        ai_result = MagicMock()
        ai_result.scalar_one_or_none.return_value = ai_profile
        results.append(ai_result)

        # 3. Food entries
        fe_result = MagicMock()
        fe_scalars = MagicMock()
        fe_scalars.all.return_value = food_entries
        fe_result.scalars.return_value = fe_scalars
        results.append(fe_result)

        # 4. Patterns
        pat_result = MagicMock()
        pat_scalars = MagicMock()
        pat_scalars.all.return_value = patterns
        pat_result.scalars.return_value = pat_scalars
        results.append(pat_result)

        # 5. Insights
        ins_result = MagicMock()
        ins_scalars = MagicMock()
        ins_scalars.all.return_value = insights
        ins_result.scalars.return_value = ins_scalars
        results.append(ins_result)

        # 6. Lesson progress
        lp_result = MagicMock()
        lp_scalars = MagicMock()
        lp_scalars.all.return_value = lesson_progress
        lp_result.scalars.return_value = lp_scalars
        # unique() returns a chainable object that has .scalars()
        lp_unique = MagicMock()
        lp_unique.scalars.return_value = lp_scalars
        lp_result.unique.return_value = lp_unique
        results.append(lp_result)

        # 7. Subscriptions
        sub_result = MagicMock()
        sub_scalars = MagicMock()
        sub_scalars.all.return_value = subscriptions
        sub_result.scalars.return_value = sub_scalars
        results.append(sub_result)

        # 8. Invites
        inv_result = MagicMock()
        inv_scalars = MagicMock()
        inv_scalars.all.return_value = invites
        inv_result.scalars.return_value = inv_scalars
        results.append(inv_result)

    session.execute = AsyncMock(side_effect=results)
    return session


# ===========================================================================
# Unit tests for privacy_service
# ===========================================================================


class TestExportUserData:
    """Unit tests for export_user_data."""

    async def test_export_user_data(self):
        """Returns all user data sections with correct structure."""
        from app.services.privacy_service import export_user_data

        user = _make_user()
        ai_profile = MagicMock(spec=AIProfile)
        ai_profile.id = uuid.uuid4()
        ai_profile.user_id = FAKE_USER_ID
        ai_profile.interview_answers = {"q1": "a1"}
        ai_profile.cluster_id = "emotional_eater"
        ai_profile.risk_model = {"score": 0.5}
        ai_profile.last_updated = datetime(2026, 1, 20, tzinfo=timezone.utc)

        food_entry = _make_food_entry()
        pattern = _make_pattern()
        insight = _make_insight()
        lp = _make_lesson_progress()
        sub = _make_subscription()
        invite = _make_invite()

        session = _make_mock_db_for_export(
            user=user,
            ai_profile=ai_profile,
            food_entries=[food_entry],
            patterns=[pattern],
            insights=[insight],
            lesson_progress=[lp],
            subscriptions=[sub],
            invites=[invite],
        )

        result = await export_user_data(session, FAKE_USER_ID)

        assert result["profile"]["telegram_id"] == FAKE_TELEGRAM_ID
        assert result["profile"]["first_name"] == "Test"
        assert result["ai_profile"] is not None
        assert result["ai_profile"]["cluster_id"] == "emotional_eater"
        assert len(result["food_entries"]) == 1
        assert result["food_entries"][0]["raw_text"] == "Завтрак: каша"
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "time"
        assert len(result["insights"]) == 1
        assert result["insights"][0]["title"] == "Тестовый инсайт"
        assert len(result["lesson_progress"]) == 1
        assert result["lesson_progress"][0]["lesson_title"] == "Урок 1: Основы CBT"
        assert len(result["subscriptions"]) == 1
        assert result["subscriptions"][0]["plan"] == "premium"
        assert len(result["invites_sent"]) == 1
        assert result["invites_sent"][0]["invite_code"] == "ABC123"

    async def test_export_user_data_empty(self):
        """User with no associated data returns empty lists."""
        from app.services.privacy_service import export_user_data

        user = _make_user()

        session = _make_mock_db_for_export(
            user=user,
            ai_profile=None,
            food_entries=[],
            patterns=[],
            insights=[],
            lesson_progress=[],
            subscriptions=[],
            invites=[],
        )

        result = await export_user_data(session, FAKE_USER_ID)

        assert result["profile"]["telegram_id"] == FAKE_TELEGRAM_ID
        assert result["ai_profile"] is None
        assert result["food_entries"] == []
        assert result["patterns"] == []
        assert result["insights"] == []
        assert result["lesson_progress"] == []
        assert result["subscriptions"] == []
        assert result["invites_sent"] == []

    async def test_export_includes_food_entries(self):
        """Food entries are serialized correctly with all fields."""
        from app.services.privacy_service import export_user_data

        user = _make_user()
        entry = _make_food_entry()

        session = _make_mock_db_for_export(
            user=user,
            food_entries=[entry],
        )

        result = await export_user_data(session, FAKE_USER_ID)

        assert len(result["food_entries"]) == 1
        fe = result["food_entries"][0]
        assert fe["raw_text"] == "Завтрак: каша"
        assert fe["total_calories"] == 200
        assert fe["mood"] == "ok"
        assert fe["context"] == "home"
        assert fe["hour"] == 8
        # UUID should be serialized as string
        assert isinstance(fe["id"], str)
        # datetime should be serialized as isoformat
        assert isinstance(fe["logged_at"], str)

    async def test_export_includes_patterns(self):
        """Patterns are serialized correctly with all fields."""
        from app.services.privacy_service import export_user_data

        user = _make_user()
        pattern = _make_pattern()

        session = _make_mock_db_for_export(
            user=user,
            patterns=[pattern],
        )

        result = await export_user_data(session, FAKE_USER_ID)

        assert len(result["patterns"]) == 1
        p = result["patterns"][0]
        assert p["type"] == "time"
        assert p["description_ru"] == "Тестовый паттерн"
        assert p["confidence"] == 0.8
        assert p["active"] is True
        assert isinstance(p["id"], str)
        assert isinstance(p["discovered_at"], str)


class TestDeleteUserAccount:
    """Unit tests for delete_user_account."""

    async def test_delete_account_success(self):
        """Deletes user record and returns True."""
        from app.services.privacy_service import delete_user_account

        user = _make_user()

        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        # cancel_subscription also calls db.execute
        sub_result = MagicMock()
        sub_result.scalar_one_or_none.return_value = None  # no active sub

        session.execute = AsyncMock(side_effect=[user_result, sub_result])
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await delete_user_account(session, FAKE_USER_ID)

        assert result is True
        session.delete.assert_called_once_with(user)
        session.flush.assert_called()

    async def test_delete_account_not_found(self):
        """Returns False when user does not exist."""
        from app.services.privacy_service import delete_user_account

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        result = await delete_user_account(session, uuid.uuid4())

        assert result is False
        session.delete.assert_not_called()

    async def test_delete_cancels_subscription(self):
        """Calls cancel_subscription before deleting the user."""
        from app.services.privacy_service import delete_user_account

        user = _make_user()
        sub = _make_subscription()

        session = AsyncMock()

        # 1st execute: fetch user for delete_user_account
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        # 2nd execute: cancel_subscription finds active sub
        sub_result = MagicMock()
        sub_result.scalar_one_or_none.return_value = sub

        # 3rd execute: cancel_subscription fetches user to update status
        user_for_cancel = MagicMock()
        user_for_cancel.scalar_one_or_none.return_value = user

        session.execute = AsyncMock(
            side_effect=[user_result, sub_result, user_for_cancel]
        )
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await delete_user_account(session, FAKE_USER_ID)

        assert result is True
        # Subscription should have been marked cancelled
        assert sub.status == "cancelled"
        assert sub.cancelled_at is not None
        # User should have been deleted
        session.delete.assert_called_once_with(user)


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestExportEndpoint:
    """Endpoint tests for POST /api/privacy/export."""

    async def test_export_endpoint(self, app, client: AsyncClient):
        """POST /api/privacy/export -> 200 with all data sections."""
        user = _make_user()
        food_entry = _make_food_entry()
        pattern = _make_pattern()

        session = _make_mock_db_for_export(
            user=user,
            ai_profile=None,
            food_entries=[food_entry],
            patterns=[pattern],
            insights=[],
            lesson_progress=[],
            subscriptions=[],
            invites=[],
        )
        _override_dependencies(app, session)

        try:
            response = await client.post("/api/privacy/export")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert "profile" in body
        assert body["profile"]["telegram_id"] == FAKE_TELEGRAM_ID
        assert body["ai_profile"] is None
        assert len(body["food_entries"]) == 1
        assert len(body["patterns"]) == 1
        assert body["insights"] == []
        assert body["lesson_progress"] == []
        assert body["subscriptions"] == []
        assert body["invites_sent"] == []


class TestDeleteEndpoint:
    """Endpoint tests for POST /api/privacy/delete."""

    async def test_delete_endpoint_success(self, app, client: AsyncClient):
        """POST with confirmation="УДАЛИТЬ" -> 200."""
        user = _make_user()

        session = AsyncMock()
        # 1st execute: fetch user for delete_user_account
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        # 2nd execute: cancel_subscription (no active sub)
        sub_result = MagicMock()
        sub_result.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[user_result, sub_result])
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/privacy/delete",
                json={"confirmation": "УДАЛИТЬ"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "удалены" in body["message"].lower() or "удалены" in body["message"]

    async def test_delete_endpoint_wrong_confirmation(self, app, client: AsyncClient):
        """POST with wrong confirmation text -> 400."""
        session = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/privacy/delete",
                json={"confirmation": "delete"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 400
        body = response.json()
        assert "УДАЛИТЬ" in body["detail"]

    async def test_delete_endpoint_missing_confirmation(self, app, client: AsyncClient):
        """POST with empty body -> 422 validation error."""
        session = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/privacy/delete",
                json={},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422
