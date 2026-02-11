"""Tests for the insights feature (US-3.2).

BDD scenarios covered:

Unit tests for insight generation (6 tests):
1.  test_generate_pattern_insight -- with active patterns -> generates pattern type insight
2.  test_generate_progress_insight -- day 4 of cycle -> progress type
3.  test_generate_cbt_insight -- day 6 of cycle -> cbt type
4.  test_generate_risk_insight -- day 7 of cycle -> risk type
5.  test_generate_insight_no_patterns -- no patterns -> still generates with fallback
6.  test_insight_locked_for_free_tier -- free user with 3+ insights -> is_locked=True

Endpoint tests (6+ tests):
7.  test_get_today_insight_placeholder -- no insight today -> returns placeholder
8.  test_get_today_insight_existing -- insight exists -> returns it
9.  test_generate_endpoint_creates_insight -- POST /generate -> creates and returns insight
10. test_feedback_positive -- POST feedback with "positive" -> ok
11. test_feedback_wrong_user -- another user's insight -> 404
12. test_mark_seen -- POST seen -> marks insight as seen
13. test_feedback_negative -- POST feedback with "negative" -> ok
14. test_mark_seen_wrong_user -- another user's insight -> 404
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.food_entry import FoodEntry
from app.models.insight import Insight
from app.models.pattern import Pattern
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
    user_id: uuid.UUID = FAKE_USER_ID,
    subscription_status: str = "free",
    insights_received: int = 0,
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.telegram_id = FAKE_TELEGRAM_ID
    user.first_name = "Test"
    user.subscription_status = subscription_status
    user.insights_received = insights_received
    user.onboarding_complete = True
    return user


def _make_pattern(
    pattern_type: str = "time",
    confidence: float = 0.8,
    user_id: uuid.UUID = FAKE_USER_ID,
    evidence: dict | None = None,
) -> MagicMock:
    """Create a mock Pattern object."""
    pattern = MagicMock(spec=Pattern)
    pattern.id = uuid.uuid4()
    pattern.user_id = user_id
    pattern.type = pattern_type
    pattern.description_ru = "Тестовый паттерн"
    pattern.confidence = confidence
    pattern.active = True
    pattern.evidence = evidence or {
        "avg_lunch_calories": 200.0,
        "avg_evening_calories": 500.0,
        "ratio": 2.5,
    }
    pattern.discovered_at = datetime.now(timezone.utc)
    return pattern


def _make_entry(
    hour: int = 12,
    calories: int = 300,
    mood: str | None = None,
    context: str | None = None,
    day_offset: int = 0,
    user_id: uuid.UUID = FAKE_USER_ID,
) -> FoodEntry:
    """Create a FoodEntry object for testing."""
    base_date = datetime(2026, 2, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
    logged_at = base_date.replace(hour=hour)
    return FoodEntry(
        id=uuid.uuid4(),
        user_id=user_id,
        raw_text="test",
        parsed_items=[],
        total_calories=calories,
        mood=mood,
        context=context,
        logged_at=logged_at,
        day_of_week=logged_at.weekday(),
        hour=hour,
    )


def _make_insight(
    user_id: uuid.UUID = FAKE_USER_ID,
    insight_type: str = "pattern",
    is_locked: bool = False,
    seen: bool = False,
) -> MagicMock:
    """Create a mock Insight object."""
    insight = MagicMock(spec=Insight)
    insight.id = uuid.uuid4()
    insight.user_id = user_id
    insight.pattern_id = None
    insight.title = "Тестовый инсайт"
    insight.body = "Тестовое тело инсайта с достаточно длинным текстом для проверки обрезки при блокировке"
    insight.action = "Тестовое действие"
    insight.type = insight_type
    insight.seen = seen
    insight.is_locked = is_locked
    insight.created_at = datetime.now(timezone.utc)
    return insight


def _override_dependencies(app, session, user_id=FAKE_USER_ID):
    """Override get_db and get_current_user dependencies on the app."""
    from app.dependencies import get_db, get_current_user

    async def _override_get_db():
        yield session

    async def _override_get_current_user():
        return {"user_id": user_id, "telegram_id": FAKE_TELEGRAM_ID}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user


def _make_mock_db_for_generate(
    user: MagicMock,
    insight_count: int = 0,
    patterns: list | None = None,
    entries: list | None = None,
):
    """Create a mock DB session for generate_daily_insight testing.

    Simulates:
        - db.get(User, user_id) -> user
        - db.execute(count query) -> insight_count
        - db.execute(pattern query) -> patterns
        - db.execute(entry query) -> entries
        - db.add / db.flush
    """
    session = AsyncMock()
    patterns = patterns or []
    entries = entries or []

    # db.get(User, ...) -> user
    session.get = AsyncMock(return_value=user)

    call_index = {"idx": 0}

    def _execute_side_effect(stmt):
        result_mock = MagicMock()
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        if "count" in compiled.lower():
            # _count_user_insights
            result_mock.scalar_one.return_value = insight_count
        elif "patterns" in compiled.lower():
            # _get_active_patterns
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = patterns
            result_mock.scalars.return_value = scalars_mock
        elif "food_entries" in compiled.lower():
            # _get_recent_entries
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = entries
            result_mock.scalars.return_value = scalars_mock
        else:
            result_mock.scalar_one.return_value = 0
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            result_mock.scalars.return_value = scalars_mock

        return result_mock

    session.execute = AsyncMock(side_effect=_execute_side_effect)

    added_objects: list = []

    def _add_side_effect(obj):
        """Simulate session.add -- assign id if missing."""
        if isinstance(obj, Insight):
            if obj.id is None:
                obj.id = uuid.uuid4()
            added_objects.append(obj)

    session.add = MagicMock(side_effect=_add_side_effect)

    async def _flush_side_effect():
        """Simulate session.flush -- assign created_at if missing."""
        for obj in added_objects:
            if isinstance(obj, Insight) and obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)

    session.flush = AsyncMock(side_effect=_flush_side_effect)

    return session


# ===========================================================================
# Unit tests for insight generation
# ===========================================================================


class TestGeneratePatternInsight:
    """test_generate_pattern_insight -- with active patterns -> pattern type insight."""

    async def test_generate_pattern_insight(self):
        """Day 1-3 of cycle with active patterns -> generates pattern type insight."""
        from app.services.insight_service import generate_daily_insight

        user = _make_user(insights_received=0)
        pattern = _make_pattern(
            pattern_type="time",
            evidence={
                "avg_lunch_calories": 200.0,
                "avg_evening_calories": 500.0,
                "ratio": 2.5,
            },
        )

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=0,  # day_in_cycle = 1 -> pattern
            patterns=[pattern],
            entries=[_make_entry(day_offset=i) for i in range(5)],
        )

        insight = await generate_daily_insight(session, FAKE_USER_ID)

        assert insight is not None
        session.add.assert_called_once()
        added_insight = session.add.call_args[0][0]
        assert isinstance(added_insight, Insight)
        assert added_insight.type == "pattern"
        assert added_insight.title == "Ваш режим питания"
        assert added_insight.action is not None
        assert added_insight.pattern_id == pattern.id
        assert added_insight.is_locked is False


class TestGenerateProgressInsight:
    """test_generate_progress_insight -- day 4 of cycle -> progress type."""

    async def test_generate_progress_insight(self):
        """insight_count=3 -> day_in_cycle=4 -> progress type insight."""
        from app.services.insight_service import generate_daily_insight

        user = _make_user(insights_received=3)
        entries = [_make_entry(day_offset=i) for i in range(5)]

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=3,  # day_in_cycle = 4 -> progress
            patterns=[],
            entries=entries,
        )

        insight = await generate_daily_insight(session, FAKE_USER_ID)

        assert insight is not None
        added_insight = session.add.call_args[0][0]
        assert added_insight.type == "progress"
        assert added_insight.title == "Ваш прогресс"
        assert added_insight.action is not None
        # Body should mention entry count
        assert "приёмов пищи" in added_insight.body


class TestGenerateCbtInsight:
    """test_generate_cbt_insight -- day 6 of cycle -> cbt type."""

    async def test_generate_cbt_insight(self):
        """insight_count=5 -> day_in_cycle=6 -> cbt type insight."""
        from app.services.insight_service import generate_daily_insight

        user = _make_user(insights_received=5)

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=5,  # day_in_cycle = 6 -> cbt
            patterns=[],
            entries=[],
        )

        insight = await generate_daily_insight(session, FAKE_USER_ID)

        assert insight is not None
        added_insight = session.add.call_args[0][0]
        assert added_insight.type == "cbt"
        assert "CBT" in added_insight.title
        assert added_insight.action is not None


class TestGenerateRiskInsight:
    """test_generate_risk_insight -- day 7 of cycle -> risk type."""

    async def test_generate_risk_insight(self):
        """insight_count=6 -> day_in_cycle=7 -> risk type insight."""
        from app.services.insight_service import generate_daily_insight

        user = _make_user(insights_received=6)
        pattern = _make_pattern(pattern_type="mood")
        entries = [_make_entry(day_offset=i) for i in range(3)]

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=6,  # day_in_cycle = 7 -> risk
            patterns=[pattern],
            entries=entries,
        )

        insight = await generate_daily_insight(session, FAKE_USER_ID)

        assert insight is not None
        added_insight = session.add.call_args[0][0]
        assert added_insight.type == "risk"
        assert added_insight.title == "Итоги недели"
        assert added_insight.action is not None


class TestGenerateInsightNoPatterns:
    """test_generate_insight_no_patterns -- no patterns -> still generates with fallback."""

    async def test_generate_insight_no_patterns(self):
        """Pattern type insight with no patterns -> uses fallback template."""
        from app.services.insight_service import generate_daily_insight

        user = _make_user(insights_received=0)

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=0,  # day_in_cycle = 1 -> pattern
            patterns=[],  # No patterns!
            entries=[],
        )

        insight = await generate_daily_insight(session, FAKE_USER_ID)

        assert insight is not None
        added_insight = session.add.call_args[0][0]
        assert added_insight.type == "pattern"
        # Should use fallback
        assert added_insight.title == "Начните свой путь к осознанному питанию"
        assert added_insight.action is not None
        assert added_insight.pattern_id is None


class TestInsightLockedForFreeTier:
    """test_insight_locked_for_free_tier -- free user with 3+ insights -> is_locked=True."""

    async def test_insight_locked_for_free_tier(self):
        """Free user with insights_received >= 3 -> insight is_locked=True."""
        from app.services.insight_service import generate_daily_insight

        user = _make_user(
            subscription_status="free",
            insights_received=3,
        )

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=3,
            patterns=[],
            entries=[],
        )

        insight = await generate_daily_insight(session, FAKE_USER_ID)

        assert insight is not None
        added_insight = session.add.call_args[0][0]
        assert added_insight.is_locked is True

    async def test_insight_unlocked_for_premium(self):
        """Premium user -> insight is_locked=False regardless of count."""
        from app.services.insight_service import generate_daily_insight

        user = _make_user(
            subscription_status="premium",
            insights_received=10,
        )

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=10,
            patterns=[],
            entries=[],
        )

        insight = await generate_daily_insight(session, FAKE_USER_ID)

        assert insight is not None
        added_insight = session.add.call_args[0][0]
        assert added_insight.is_locked is False


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestGetTodayInsightEndpoint:
    """Endpoint tests for GET /api/insights/today."""

    async def test_get_today_insight_placeholder(self, app, client: AsyncClient):
        """No insight today -> returns placeholder in Russian."""
        session = AsyncMock()

        # execute returns no insight (scalar_one_or_none -> None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        _override_dependencies(app, session)

        try:
            response = await client.get("/api/insights/today")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["is_locked"] is False
        assert body["insight"]["type"] == "general"
        assert body["insight"]["title"] == "Ваш инсайт готовится"
        assert body["insight"]["action"] is None

    async def test_get_today_insight_existing(self, app, client: AsyncClient):
        """Existing insight today -> returns it."""
        insight = _make_insight(
            insight_type="pattern",
            is_locked=False,
        )
        user = _make_user(subscription_status="premium")

        session = AsyncMock()
        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            result_mock = MagicMock()
            call_count["n"] += 1
            if call_count["n"] == 1:
                # First call: find today's insight
                result_mock.scalar_one_or_none.return_value = insight
            else:
                # Second call: find user for subscription check
                result_mock.scalar_one_or_none.return_value = user
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/insights/today")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["is_locked"] is False
        assert body["insight"]["type"] == "pattern"
        assert body["insight"]["title"] == "Тестовый инсайт"
        assert body["insight"]["action"] == "Тестовое действие"


class TestGenerateEndpoint:
    """Endpoint tests for POST /api/insights/generate."""

    async def test_generate_endpoint_creates_insight(self, app, client: AsyncClient):
        """POST /generate -> creates and returns insight."""
        user = _make_user(insights_received=0)
        pattern = _make_pattern(pattern_type="time")

        session = _make_mock_db_for_generate(
            user=user,
            insight_count=0,
            patterns=[pattern],
            entries=[_make_entry(day_offset=i) for i in range(3)],
        )
        _override_dependencies(app, session)

        try:
            response = await client.post("/api/insights/generate")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["insight"]["type"] == "pattern"
        assert body["insight"]["title"] == "Ваш режим питания"
        assert body["insight"]["action"] is not None
        assert body["is_locked"] is False

    async def test_generate_endpoint_user_not_found(self, app, client: AsyncClient):
        """POST /generate with nonexistent user -> 500."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        _override_dependencies(app, session)

        try:
            response = await client.post("/api/insights/generate")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 500


class TestFeedbackEndpoint:
    """Endpoint tests for POST /api/insights/{insight_id}/feedback."""

    async def test_feedback_positive(self, app, client: AsyncClient):
        """POST feedback with 'positive' -> ok."""
        insight = _make_insight()

        session = AsyncMock()
        session.get = AsyncMock(return_value=insight)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{insight.id}/feedback",
                json={"rating": "positive"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        # Insight should be marked as seen
        assert insight.seen is True

    async def test_feedback_negative(self, app, client: AsyncClient):
        """POST feedback with 'negative' -> ok."""
        insight = _make_insight()

        session = AsyncMock()
        session.get = AsyncMock(return_value=insight)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{insight.id}/feedback",
                json={"rating": "negative"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert insight.seen is True

    async def test_feedback_wrong_user(self, app, client: AsyncClient):
        """Another user's insight -> 404."""
        other_user_id = uuid.uuid4()
        insight = _make_insight(user_id=other_user_id)

        session = AsyncMock()
        session.get = AsyncMock(return_value=insight)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{insight.id}/feedback",
                json={"rating": "positive"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    async def test_feedback_nonexistent_insight(self, app, client: AsyncClient):
        """Nonexistent insight -> 404."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{uuid.uuid4()}/feedback",
                json={"rating": "positive"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    async def test_feedback_invalid_rating(self, app, client: AsyncClient):
        """Invalid rating value -> 422."""
        insight = _make_insight()

        session = AsyncMock()
        session.get = AsyncMock(return_value=insight)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{insight.id}/feedback",
                json={"rating": "neutral"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422


class TestMarkSeenEndpoint:
    """Endpoint tests for POST /api/insights/{insight_id}/seen."""

    async def test_mark_seen(self, app, client: AsyncClient):
        """POST seen -> marks insight as seen."""
        insight = _make_insight(seen=False)

        session = AsyncMock()
        session.get = AsyncMock(return_value=insight)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{insight.id}/seen",
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert insight.seen is True

    async def test_mark_seen_wrong_user(self, app, client: AsyncClient):
        """Another user's insight -> 404."""
        other_user_id = uuid.uuid4()
        insight = _make_insight(user_id=other_user_id)

        session = AsyncMock()
        session.get = AsyncMock(return_value=insight)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{insight.id}/seen",
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    async def test_mark_seen_nonexistent_insight(self, app, client: AsyncClient):
        """Nonexistent insight -> 404."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                f"/api/insights/{uuid.uuid4()}/seen",
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404


# ===========================================================================
# Unit tests for local template generation helpers
# ===========================================================================


class TestLocalTemplateHelpers:
    """Additional unit tests for the template helper functions."""

    def test_generate_local_insight_dispatches_correctly(self):
        """_generate_local_insight dispatches to the correct generator."""
        from app.services.insight_service import _generate_local_insight

        user = _make_user()
        pattern = _make_pattern(pattern_type="mood", evidence={
            "avg_bad_mood_calories": 600.0,
            "avg_ok_mood_calories": 300.0,
        })

        title, body, action, pattern_id = _generate_local_insight(
            "pattern", [pattern], [], user, 0
        )
        assert title == "Настроение и еда"
        assert pattern_id == pattern.id

    def test_cbt_rotation(self):
        """CBT insights rotate based on insight_count."""
        from app.services.insight_service import _generate_cbt_insight, CBT_INSIGHTS

        for i in range(len(CBT_INSIGHTS)):
            title, body, action, pid = _generate_cbt_insight(i)
            assert title == CBT_INSIGHTS[i]["title"]
            assert body == CBT_INSIGHTS[i]["body"]
            assert action == CBT_INSIGHTS[i]["action"]
            assert pid is None

        # Wraps around
        title, _, _, _ = _generate_cbt_insight(len(CBT_INSIGHTS))
        assert title == CBT_INSIGHTS[0]["title"]

    def test_format_evidence_all_types(self):
        """_format_evidence handles all pattern types."""
        from app.services.insight_service import _format_evidence

        time_pattern = _make_pattern(
            pattern_type="time",
            evidence={"avg_lunch_calories": 200, "avg_evening_calories": 500},
        )
        result = _format_evidence(time_pattern)
        assert "200" in result
        assert "500" in result

        mood_pattern = _make_pattern(
            pattern_type="mood",
            evidence={"avg_bad_mood_calories": 600, "avg_ok_mood_calories": 300},
        )
        result = _format_evidence(mood_pattern)
        assert "600" in result
        assert "300" in result

        context_pattern = _make_pattern(
            pattern_type="context",
            evidence={"avg_home_calories": 300, "avg_out_calories": 600},
        )
        result = _format_evidence(context_pattern)
        assert "300" in result
        assert "600" in result

        skip_pattern = _make_pattern(
            pattern_type="skip",
            evidence={"skip_binge_days": 5, "total_days": 10},
        )
        result = _format_evidence(skip_pattern)
        assert "5" in result
        assert "10" in result

    def test_progress_insight_no_entries(self):
        """Progress insight with no entries -> mentions 0 entries."""
        from app.services.insight_service import _generate_progress_insight

        title, body, action, pid = _generate_progress_insight([])
        assert title == "Ваш прогресс"
        assert "0" in body
        assert action is not None
        assert pid is None

    def test_risk_insight_with_multiple_patterns(self):
        """Risk insight with multiple patterns -> mentions pattern types."""
        from app.services.insight_service import _generate_risk_insight

        patterns = [
            _make_pattern(pattern_type="time"),
            _make_pattern(pattern_type="mood"),
        ]
        entries = [_make_entry(day_offset=i) for i in range(5)]

        title, body, action, pid = _generate_risk_insight(patterns, entries)
        assert title == "Итоги недели"
        assert "режим питания" in body
        assert "настроения" in body or "связь" in body
        assert action is not None
