"""Tests for the risk predictor feature (US-3.3).

BDD scenarios covered:

Unit tests for risk calculation (8 tests):
1. test_no_patterns_returns_none -- no active patterns -> None
2. test_time_pattern_evening_high_risk -- time pattern at 20:00 -> medium/high risk
3. test_time_pattern_morning_low_risk -- time pattern at 9:00 -> low risk
4. test_mood_pattern_bad_mood -- mood pattern + bad mood entry -> adds risk
5. test_skip_pattern_no_lunch_afternoon -- skip pattern, no lunch, 16:00 -> high contribution
6. test_weekend_amplification -- weekend factor multiplied by 1.3
7. test_high_calorie_reduces_risk -- already ate 1500+ cal -> risk * 0.7
8. test_risk_classification_levels -- verify low/medium/high thresholds

Integration test:
9. test_patterns_endpoint_returns_risk_today -- GET /api/patterns includes risk_today
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern
from app.services.risk_service import (
    RISK_RECOMMENDATIONS,
    TIME_WINDOW_LABELS,
    calculate_risk,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pattern(
    pattern_type: str,
    confidence: float = 0.8,
    active: bool = True,
    user_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a Pattern-like mock for unit testing risk calculation."""
    p = MagicMock(spec=Pattern)
    p.type = pattern_type
    p.confidence = confidence
    p.active = active
    p.user_id = user_id or FAKE_USER_ID
    return p


def _make_entry(
    hour: int,
    calories: int,
    mood: str | None = None,
    context: str | None = None,
    logged_at: datetime | None = None,
) -> MagicMock:
    """Create a FoodEntry-like mock for unit testing risk calculation."""
    e = MagicMock(spec=FoodEntry)
    e.hour = hour
    e.total_calories = calories
    e.mood = mood
    e.context = context
    e.logged_at = logged_at or datetime(2026, 2, 1, hour, 0, tzinfo=timezone.utc)
    e.user_id = FAKE_USER_ID
    return e


def _mock_db(patterns: list, entries: list) -> AsyncMock:
    """Build an AsyncMock session that returns given patterns and entries.

    The first ``db.execute()`` call returns patterns; the second returns entries.
    """
    db = AsyncMock()

    # First call -> patterns query
    patterns_result = MagicMock()
    patterns_scalars = MagicMock()
    patterns_scalars.all.return_value = patterns
    patterns_result.scalars.return_value = patterns_scalars

    # Second call -> food entries query
    entries_result = MagicMock()
    entries_scalars = MagicMock()
    entries_scalars.all.return_value = entries
    entries_result.scalars.return_value = entries_scalars

    db.execute = AsyncMock(side_effect=[patterns_result, entries_result])
    return db


def _override_dependencies(app, session, user_id=FAKE_USER_ID):
    """Override get_db and get_current_user dependencies on the app."""
    from app.dependencies import get_current_user, get_db

    async def _override_get_db():
        yield session

    async def _override_get_current_user():
        return {"user_id": user_id, "telegram_id": FAKE_TELEGRAM_ID}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user


# ===========================================================================
# Unit tests for calculate_risk
# ===========================================================================


class TestCalculateRiskUnit:
    """Unit tests for the risk calculation algorithm."""

    async def test_no_patterns_returns_none(self):
        """No active patterns -> should return None."""
        db = _mock_db(patterns=[], entries=[])

        result = await calculate_risk(
            db,
            FAKE_USER_ID,
            now=datetime(2026, 2, 1, 20, 0, tzinfo=timezone.utc),
        )

        assert result is None

    async def test_time_pattern_evening_high_risk(self):
        """Time pattern at 21:00 with high confidence -> risk should be medium or high."""
        patterns = [_make_pattern("time", confidence=1.0)]
        db = _mock_db(patterns=patterns, entries=[])

        # 21:00 on a weekday -- hour_factor = (21-15)/6 = 1.0
        # risk = 1.0 * 0.4 * 1.0 = 0.4 -> medium
        now = datetime(2026, 2, 4, 21, 0, tzinfo=timezone.utc)  # Wednesday
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        assert result.level in ("medium", "high")
        assert result.time_window == TIME_WINDOW_LABELS["evening"]
        assert result.recommendation == RISK_RECOMMENDATIONS["time"]

    async def test_time_pattern_morning_low_risk(self):
        """Time pattern at 9:00 -> risk should be low (before trigger hour)."""
        patterns = [_make_pattern("time", confidence=0.8)]
        db = _mock_db(patterns=patterns, entries=[])

        now = datetime(2026, 2, 4, 9, 0, tzinfo=timezone.utc)  # Wednesday 9 AM
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        assert result.level == "low"
        # Time window should not be set since hour < 15
        assert result.time_window is None

    async def test_mood_pattern_bad_mood(self):
        """Mood pattern + bad mood entry today -> should increase risk."""
        patterns = [_make_pattern("mood", confidence=0.9)]
        entries = [_make_entry(hour=12, calories=300, mood="bad")]
        db = _mock_db(patterns=patterns, entries=entries)

        now = datetime(2026, 2, 4, 14, 0, tzinfo=timezone.utc)  # Wednesday
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        # 0.9 * 0.3 = 0.27 -> "low" but close to medium
        assert result.level in ("low", "medium")
        assert result.recommendation == RISK_RECOMMENDATIONS["mood"]

    async def test_mood_pattern_no_bad_mood(self):
        """Mood pattern but no bad mood today -> low risk from mood."""
        patterns = [_make_pattern("mood", confidence=0.9)]
        entries = [_make_entry(hour=12, calories=300, mood="ok")]
        db = _mock_db(patterns=patterns, entries=entries)

        now = datetime(2026, 2, 4, 14, 0, tzinfo=timezone.utc)
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        assert result.level == "low"

    async def test_skip_pattern_no_lunch_afternoon(self):
        """Skip pattern, no lunch logged, 16:00 -> high contribution."""
        patterns = [_make_pattern("skip", confidence=0.9)]
        # Only a morning entry, no lunch
        entries = [_make_entry(hour=8, calories=200)]
        db = _mock_db(patterns=patterns, entries=entries)

        now = datetime(2026, 2, 4, 16, 0, tzinfo=timezone.utc)  # Wednesday 4 PM
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        # 0.9 * 0.5 = 0.45 -> medium
        assert result.level in ("medium", "high")
        assert result.recommendation == RISK_RECOMMENDATIONS["skip"]
        assert result.time_window == TIME_WINDOW_LABELS["evening"]

    async def test_skip_pattern_with_lunch_logged(self):
        """Skip pattern but lunch was logged -> skip contribution should be zero."""
        patterns = [_make_pattern("skip", confidence=0.9)]
        # Lunch logged at 12:00
        entries = [_make_entry(hour=12, calories=500)]
        db = _mock_db(patterns=patterns, entries=entries)

        now = datetime(2026, 2, 4, 16, 0, tzinfo=timezone.utc)
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        assert result.level == "low"

    async def test_weekend_amplification(self):
        """Weekend factor should multiply risk by 1.3."""
        patterns = [_make_pattern("time", confidence=0.8)]
        db = _mock_db(patterns=patterns, entries=[])

        # Saturday 2026-02-07 at 20:00
        now_weekend = datetime(2026, 2, 7, 20, 0, tzinfo=timezone.utc)
        result_weekend = await calculate_risk(db, FAKE_USER_ID, now=now_weekend)

        # Same time on Wednesday 2026-02-04
        db2 = _mock_db(patterns=[_make_pattern("time", confidence=0.8)], entries=[])
        now_weekday = datetime(2026, 2, 4, 20, 0, tzinfo=timezone.utc)
        result_weekday = await calculate_risk(db2, FAKE_USER_ID, now=now_weekday)

        assert result_weekend is not None
        assert result_weekday is not None
        # Weekend risk should be higher or equal (due to 1.3 multiplier)
        # With time pattern at 20:00: confidence=0.8, hour_factor=(20-15)/6=0.833
        # base = 0.8 * 0.4 * 0.833 = 0.267
        # weekday: 0.267, weekend: 0.267 * 1.3 = 0.347
        # weekday level: low (0.267 < 0.3), weekend level: medium (0.347 > 0.3)
        assert result_weekday.level == "low"
        assert result_weekend.level == "medium"

    async def test_high_calorie_reduces_risk(self):
        """Already ate 1500+ cal today -> risk * 0.7."""
        patterns = [_make_pattern("time", confidence=0.8)]
        # High calorie entries summing to > 1500
        entries = [
            _make_entry(hour=8, calories=800),
            _make_entry(hour=12, calories=800),
        ]
        db = _mock_db(patterns=patterns, entries=entries)

        now = datetime(2026, 2, 4, 20, 0, tzinfo=timezone.utc)  # Wednesday 8 PM
        result_high_cal = await calculate_risk(db, FAKE_USER_ID, now=now)

        # Compare with same scenario but low calories
        db2 = _mock_db(
            patterns=[_make_pattern("time", confidence=0.8)],
            entries=[_make_entry(hour=8, calories=200)],
        )
        result_low_cal = await calculate_risk(db2, FAKE_USER_ID, now=now)

        assert result_high_cal is not None
        assert result_low_cal is not None
        # High cal result should have lower or equal risk level
        level_order = {"low": 0, "medium": 1, "high": 2}
        assert level_order[result_high_cal.level] <= level_order[result_low_cal.level]

    async def test_risk_classification_levels(self):
        """Verify low/medium/high classification thresholds."""
        # Low risk: context pattern only -> confidence * 0.2
        # 0.5 * 0.2 = 0.1 -> low
        patterns_low = [_make_pattern("context", confidence=0.5)]
        db_low = _mock_db(patterns=patterns_low, entries=[])
        now = datetime(2026, 2, 4, 14, 0, tzinfo=timezone.utc)
        result_low = await calculate_risk(db_low, FAKE_USER_ID, now=now)
        assert result_low is not None
        assert result_low.level == "low"

        # Medium risk: skip pattern, no lunch, 16:00
        # 0.7 * 0.5 = 0.35 -> medium
        patterns_med = [_make_pattern("skip", confidence=0.7)]
        entries_med = [_make_entry(hour=8, calories=200)]
        db_med = _mock_db(patterns=patterns_med, entries=entries_med)
        now_med = datetime(2026, 2, 4, 16, 0, tzinfo=timezone.utc)
        result_med = await calculate_risk(db_med, FAKE_USER_ID, now=now_med)
        assert result_med is not None
        assert result_med.level == "medium"

        # High risk: combine multiple patterns at evening on weekend
        # time: 0.9 * 0.4 * 1.0 = 0.36
        # skip (no lunch, hour>15): 0.9 * 0.5 = 0.45
        # total = 0.81, weekend * 1.3 = 1.053 -> clamped to 1.0 -> high
        patterns_high = [
            _make_pattern("time", confidence=0.9),
            _make_pattern("skip", confidence=0.9),
        ]
        entries_high = [_make_entry(hour=8, calories=200)]  # no lunch
        db_high = _mock_db(patterns=patterns_high, entries=entries_high)
        now_high = datetime(2026, 2, 7, 21, 0, tzinfo=timezone.utc)  # Saturday 9 PM
        result_high = await calculate_risk(db_high, FAKE_USER_ID, now=now_high)
        assert result_high is not None
        assert result_high.level == "high"

    async def test_context_pattern_always_contributes(self):
        """Context pattern adds risk regardless of time or mood."""
        patterns = [_make_pattern("context", confidence=1.0)]
        db = _mock_db(patterns=patterns, entries=[])

        now = datetime(2026, 2, 4, 10, 0, tzinfo=timezone.utc)  # Wednesday 10 AM
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        # 1.0 * 0.2 = 0.2 -> low
        assert result.level == "low"
        assert result.recommendation == RISK_RECOMMENDATIONS["context"]

    async def test_recommendation_uses_top_contributor(self):
        """Recommendation should match the highest-contributing pattern type."""
        # Skip pattern contributes more than context
        patterns = [
            _make_pattern("skip", confidence=0.9),
            _make_pattern("context", confidence=0.5),
        ]
        entries = [_make_entry(hour=8, calories=200)]  # no lunch
        db = _mock_db(patterns=patterns, entries=entries)

        now = datetime(2026, 2, 4, 16, 0, tzinfo=timezone.utc)
        result = await calculate_risk(db, FAKE_USER_ID, now=now)

        assert result is not None
        assert result.recommendation == RISK_RECOMMENDATIONS["skip"]


# ===========================================================================
# Integration test -- GET /api/patterns returns risk_today
# ===========================================================================


class TestPatternsEndpointRisk:
    """Integration test for risk_today in GET /api/patterns."""

    async def test_patterns_endpoint_returns_risk_today(
        self, app, client: AsyncClient
    ):
        """GET /api/patterns should include a non-null risk_today when patterns exist."""
        # Create a mock pattern for the get_user_patterns query
        pattern = MagicMock(spec=Pattern)
        pattern.id = uuid.uuid4()
        pattern.type = "time"
        pattern.description_ru = "Вечернее переедание"
        pattern.confidence = 0.8
        pattern.active = True
        pattern.user_id = FAKE_USER_ID
        pattern.discovered_at = datetime.now(timezone.utc)

        session = AsyncMock()

        # get_user_patterns does one query (patterns), then calculate_risk does
        # two queries (patterns, entries). That's 3 execute() calls total.
        # 1st call: get_user_patterns patterns query -> [pattern]
        patterns_result_1 = MagicMock()
        patterns_scalars_1 = MagicMock()
        patterns_scalars_1.all.return_value = [pattern]
        patterns_result_1.scalars.return_value = patterns_scalars_1

        # 2nd call: calculate_risk patterns query -> [pattern]
        patterns_result_2 = MagicMock()
        patterns_scalars_2 = MagicMock()
        patterns_scalars_2.all.return_value = [pattern]
        patterns_result_2.scalars.return_value = patterns_scalars_2

        # 3rd call: calculate_risk entries query -> []
        entries_result = MagicMock()
        entries_scalars = MagicMock()
        entries_scalars.all.return_value = []
        entries_result.scalars.return_value = entries_scalars

        session.execute = AsyncMock(
            side_effect=[patterns_result_1, patterns_result_2, entries_result]
        )

        _override_dependencies(app, session)

        try:
            response = await client.get("/api/patterns")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert len(body["patterns"]) == 1
        # risk_today should be present (not None) because there are active patterns
        assert body["risk_today"] is not None
        assert body["risk_today"]["level"] in ("low", "medium", "high")
        assert body["risk_today"]["recommendation"] is not None

    async def test_patterns_endpoint_risk_none_when_no_patterns(
        self, app, client: AsyncClient
    ):
        """GET /api/patterns with no patterns -> risk_today should be None."""
        session = AsyncMock()

        # 1st call: get_user_patterns -> no patterns
        patterns_result_1 = MagicMock()
        patterns_scalars_1 = MagicMock()
        patterns_scalars_1.all.return_value = []
        patterns_result_1.scalars.return_value = patterns_scalars_1

        # 2nd call: calculate_risk -> no patterns
        patterns_result_2 = MagicMock()
        patterns_scalars_2 = MagicMock()
        patterns_scalars_2.all.return_value = []
        patterns_result_2.scalars.return_value = patterns_scalars_2

        session.execute = AsyncMock(
            side_effect=[patterns_result_1, patterns_result_2]
        )

        _override_dependencies(app, session)

        try:
            response = await client.get("/api/patterns")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["patterns"] == []
        assert body["risk_today"] is None
