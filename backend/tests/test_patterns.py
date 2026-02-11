"""Tests for the pattern detection feature (US-3.1).

BDD scenarios covered:

Unit tests for statistical detection helpers (8 tests):
1. test_detect_time_patterns_evening_heavy -- evening > 2x lunch -> time pattern
2. test_detect_time_patterns_balanced -- balanced meals -> no pattern
3. test_detect_mood_patterns_bad_mood_overeating -- bad mood high cal -> mood pattern
4. test_detect_mood_patterns_no_correlation -- uniform by mood -> no pattern
5. test_detect_context_patterns_restaurant -- restaurant high cal -> context pattern
6. test_detect_skip_patterns_lunch_skip -- skip lunch + evening binge -> skip pattern
7. test_cold_start_emotional_eater -- cluster=emotional_eater -> cold start patterns
8. test_cold_start_insufficient_data -- < 10 entries -> cold start, confidence <= 0.4

Endpoint tests (5 tests):
9.  test_get_patterns_empty -- new user -> empty list
10. test_get_patterns_with_data -- user with patterns -> returns them
11. test_pattern_feedback_reduces_confidence -- POST feedback -> confidence -0.2
12. test_pattern_feedback_deactivates_below_threshold -- confidence < 0.3 -> active=False
13. test_pattern_feedback_wrong_user -- another user's pattern -> 404
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_entry(
    hour: int,
    calories: int,
    mood: str | None = None,
    context: str | None = None,
    day_offset: int = 0,
    user_id: uuid.UUID | None = None,
) -> FoodEntry:
    """Create a FoodEntry-like object for unit testing pattern detectors."""
    base_date = datetime(2026, 2, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
    logged_at = base_date.replace(hour=hour)
    uid = user_id or FAKE_USER_ID
    return FoodEntry(
        id=uuid.uuid4(),
        user_id=uid,
        raw_text="test",
        parsed_items=[],
        total_calories=calories,
        mood=mood,
        context=context,
        logged_at=logged_at,
        day_of_week=logged_at.weekday(),
        hour=hour,
    )


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
# Unit tests for statistical detection helpers
# ===========================================================================


class TestDetectTimePatterns:
    """Unit tests for _detect_time_patterns."""

    async def test_detect_time_patterns_evening_heavy(self):
        """Evening calories > 2x lunch -> should detect a time pattern."""
        from app.services.pattern_service import _detect_time_patterns

        entries = []
        for day in range(10):
            # Lunch entries: ~200 cal
            entries.append(make_entry(hour=12, calories=200, day_offset=day))
            # Evening entries: ~500 cal (2.5x lunch)
            entries.append(make_entry(hour=19, calories=500, day_offset=day))

        patterns = _detect_time_patterns(entries)

        assert len(patterns) == 1
        assert patterns[0]["type"] == "time"
        assert patterns[0]["confidence"] > 0
        assert "evidence" in patterns[0]
        assert patterns[0]["evidence"]["avg_evening_calories"] == 500.0
        assert patterns[0]["evidence"]["avg_lunch_calories"] == 200.0
        assert patterns[0]["evidence"]["ratio"] == 2.5

    async def test_detect_time_patterns_balanced(self):
        """Balanced meals -> no time pattern."""
        from app.services.pattern_service import _detect_time_patterns

        entries = []
        for day in range(10):
            entries.append(make_entry(hour=12, calories=400, day_offset=day))
            entries.append(make_entry(hour=19, calories=500, day_offset=day))

        patterns = _detect_time_patterns(entries)

        assert len(patterns) == 0


class TestDetectMoodPatterns:
    """Unit tests for _detect_mood_patterns."""

    async def test_detect_mood_patterns_bad_mood_overeating(self):
        """Bad mood with high calories -> should detect mood pattern."""
        from app.services.pattern_service import _detect_mood_patterns

        entries = []
        for day in range(10):
            if day < 5:
                # Good mood, moderate calories
                entries.append(
                    make_entry(hour=12, calories=300, mood="ok", day_offset=day)
                )
            else:
                # Bad mood, high calories (>1.5x)
                entries.append(
                    make_entry(hour=12, calories=600, mood="bad", day_offset=day)
                )

        patterns = _detect_mood_patterns(entries)

        assert len(patterns) == 1
        assert patterns[0]["type"] == "mood"
        assert patterns[0]["confidence"] > 0
        assert patterns[0]["evidence"]["avg_bad_mood_calories"] == 600.0
        assert patterns[0]["evidence"]["avg_ok_mood_calories"] == 300.0

    async def test_detect_mood_patterns_no_correlation(self):
        """Uniform calories across moods -> no mood pattern."""
        from app.services.pattern_service import _detect_mood_patterns

        entries = []
        for day in range(10):
            if day < 5:
                entries.append(
                    make_entry(hour=12, calories=400, mood="ok", day_offset=day)
                )
            else:
                entries.append(
                    make_entry(hour=12, calories=400, mood="bad", day_offset=day)
                )

        patterns = _detect_mood_patterns(entries)

        assert len(patterns) == 0


class TestDetectContextPatterns:
    """Unit tests for _detect_context_patterns."""

    async def test_detect_context_patterns_restaurant(self):
        """Restaurant calories > 1.5x home -> should detect context pattern."""
        from app.services.pattern_service import _detect_context_patterns

        entries = []
        for day in range(10):
            # Home: 300 cal
            entries.append(
                make_entry(hour=12, calories=300, context="home", day_offset=day)
            )
            # Restaurant: 600 cal (2x home, > 1.5x)
            entries.append(
                make_entry(hour=19, calories=600, context="restaurant", day_offset=day)
            )

        patterns = _detect_context_patterns(entries)

        assert len(patterns) == 1
        assert patterns[0]["type"] == "context"
        assert patterns[0]["confidence"] > 0
        assert patterns[0]["evidence"]["avg_out_calories"] == 600.0
        assert patterns[0]["evidence"]["avg_home_calories"] == 300.0


class TestDetectSkipPatterns:
    """Unit tests for _detect_skip_patterns."""

    async def test_detect_skip_patterns_lunch_skip(self):
        """Skip lunch + evening binge (>60% of daily) -> should detect skip pattern."""
        from app.services.pattern_service import _detect_skip_patterns

        entries = []
        for day in range(10):
            # Morning: 100 cal
            entries.append(make_entry(hour=8, calories=100, day_offset=day))
            # No lunch entries (11-14h)
            # Evening: 700 cal (700/800 = 87.5% > 60%)
            entries.append(make_entry(hour=19, calories=700, day_offset=day))

        patterns = _detect_skip_patterns(entries)

        assert len(patterns) == 1
        assert patterns[0]["type"] == "skip"
        assert patterns[0]["confidence"] > 0
        assert patterns[0]["evidence"]["skip_binge_days"] == 10
        assert patterns[0]["evidence"]["total_days"] == 10


class TestColdStart:
    """Unit tests for cold start pattern generation."""

    async def test_cold_start_emotional_eater(self):
        """cluster_id=emotional_eater -> cold start mood patterns."""
        from app.services.pattern_service import _cold_start_patterns
        from app.models.ai_profile import AIProfile

        session = AsyncMock()
        profile = MagicMock(spec=AIProfile)
        profile.cluster_id = "emotional_eater"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = profile
        session.execute = AsyncMock(return_value=result_mock)

        patterns = await _cold_start_patterns(session, FAKE_USER_ID)

        assert len(patterns) == 1
        assert patterns[0]["type"] == "mood"
        assert patterns[0]["confidence"] <= 0.4
        assert patterns[0]["evidence"]["source"] == "cold_start"
        assert patterns[0]["evidence"]["cluster_id"] == "emotional_eater"

    async def test_cold_start_insufficient_data(self):
        """< 10 entries with no cluster -> general cold start, confidence <= 0.4."""
        from app.services.pattern_service import _cold_start_patterns

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        patterns = await _cold_start_patterns(session, FAKE_USER_ID)

        assert len(patterns) >= 1
        for p in patterns:
            assert p["confidence"] <= 0.4
        # Should fall back to "general" cluster
        assert patterns[0]["evidence"]["cluster_id"] == "general"


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestGetPatternsEndpoint:
    """Integration tests for GET /api/patterns."""

    async def test_get_patterns_empty(self, app, client: AsyncClient):
        """New user with no patterns -> empty list."""
        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/patterns")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["patterns"] == []
        assert body["risk_today"] is None

    async def test_get_patterns_with_data(self, app, client: AsyncClient):
        """User with existing patterns -> returns them."""
        pattern = MagicMock(spec=Pattern)
        pattern.id = uuid.uuid4()
        pattern.type = "mood"
        pattern.description_ru = "Тестовый паттерн"
        pattern.confidence = 0.8
        pattern.discovered_at = datetime.now(timezone.utc)

        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [pattern]
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/patterns")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert len(body["patterns"]) == 1
        assert body["patterns"][0]["type"] == "mood"
        assert body["patterns"][0]["description_ru"] == "Тестовый паттерн"
        assert body["patterns"][0]["confidence"] == 0.8


class TestPatternFeedbackEndpoint:
    """Integration tests for POST /api/patterns/{pattern_id}/feedback."""

    async def test_pattern_feedback_reduces_confidence(
        self, app, client: AsyncClient
    ):
        """POST feedback -> confidence should decrease by 0.2."""
        pattern_id = uuid.uuid4()
        pattern = MagicMock(spec=Pattern)
        pattern.id = pattern_id
        pattern.user_id = FAKE_USER_ID
        pattern.confidence = 0.8
        pattern.active = True

        session = AsyncMock()
        session.get = AsyncMock(return_value=pattern)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(f"/api/patterns/{pattern_id}/feedback")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        # 0.8 - 0.2 = 0.6
        assert abs(body["new_confidence"] - 0.6) < 0.01
        assert body["active"] is True

    async def test_pattern_feedback_deactivates_below_threshold(
        self, app, client: AsyncClient
    ):
        """Confidence < 0.3 after feedback -> pattern deactivated."""
        pattern_id = uuid.uuid4()
        pattern = MagicMock(spec=Pattern)
        pattern.id = pattern_id
        pattern.user_id = FAKE_USER_ID
        pattern.confidence = 0.4
        pattern.active = True

        session = AsyncMock()
        session.get = AsyncMock(return_value=pattern)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(f"/api/patterns/{pattern_id}/feedback")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        # 0.4 - 0.2 = 0.2, which is < 0.3
        assert abs(body["new_confidence"] - 0.2) < 0.01
        assert body["active"] is False

    async def test_pattern_feedback_wrong_user(
        self, app, client: AsyncClient
    ):
        """Another user's pattern -> 404."""
        pattern_id = uuid.uuid4()
        other_user_id = uuid.uuid4()

        pattern = MagicMock(spec=Pattern)
        pattern.id = pattern_id
        pattern.user_id = other_user_id  # Different from FAKE_USER_ID
        pattern.confidence = 0.8
        pattern.active = True

        session = AsyncMock()
        session.get = AsyncMock(return_value=pattern)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(f"/api/patterns/{pattern_id}/feedback")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    async def test_pattern_feedback_nonexistent_pattern(
        self, app, client: AsyncClient
    ):
        """Nonexistent pattern -> 404."""
        pattern_id = uuid.uuid4()

        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(f"/api/patterns/{pattern_id}/feedback")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
