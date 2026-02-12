"""Tests for the scheduler and periodic jobs.

Unit tests (4):
1. test_scheduler_registers_four_jobs -- scheduler has 4 jobs configured
2. test_run_daily_patterns_processes_users -- processes users with 10+ entries
3. test_run_daily_risk_sends_notification -- sends notification for high-risk users
4. test_run_food_reminder_finds_users -- finds users without today's entries
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ===========================================================================
# Scheduler configuration tests
# ===========================================================================


class TestSchedulerConfig:
    """Tests for scheduler setup."""

    def test_scheduler_registers_four_jobs(self):
        """Scheduler should have 4 jobs after configure_scheduler()."""
        from app.scheduler import configure_scheduler, scheduler

        configure_scheduler()

        jobs = scheduler.get_jobs()
        job_ids = [j.id for j in jobs]

        assert len(jobs) == 4
        assert "daily_patterns" in job_ids
        assert "daily_insights" in job_ids
        assert "daily_risk" in job_ids
        assert "food_reminder" in job_ids

        # Cleanup
        scheduler.remove_all_jobs()


# ===========================================================================
# Batch job tests
# ===========================================================================


class TestDailyPatterns:
    """Tests for run_daily_patterns."""

    @patch("app.workers.scheduler_jobs._get_session_factory")
    @patch("app.services.pattern_service.detect_patterns")
    async def test_run_daily_patterns_processes_users(
        self, mock_detect, mock_factory
    ):
        """Processes users with 10+ food entries."""
        from app.workers.scheduler_jobs import _run_daily_patterns_async

        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()

        # Mock session factory
        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        call_count = {"n": 0}

        def _create_session_ctx():
            call_count["n"] += 1
            ctx = AsyncMock()
            session = AsyncMock()

            if call_count["n"] == 1:
                # First call: find users query
                result_mock = MagicMock()
                result_mock.all.return_value = [(user_id_1,), (user_id_2,)]
                session.execute = AsyncMock(return_value=result_mock)
            else:
                # Subsequent calls: detect patterns for each user
                session.commit = AsyncMock()

            ctx.__aenter__ = AsyncMock(return_value=session)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        factory = MagicMock()
        factory.side_effect = _create_session_ctx
        factory.kw = {"bind": AsyncMock()}
        mock_factory.return_value = factory

        mock_detect.return_value = []

        await _run_daily_patterns_async()

        # detect_patterns called for each user
        assert mock_detect.call_count == 2


class TestDailyRisk:
    """Tests for run_daily_risk."""

    @patch("app.workers.scheduler_jobs.send_telegram_message")
    @patch("app.workers.scheduler_jobs._get_session_factory")
    @patch("app.services.risk_service.calculate_risk")
    async def test_run_daily_risk_sends_notification(
        self, mock_risk, mock_factory, mock_send
    ):
        """Sends notification for high-risk users."""
        from app.workers.scheduler_jobs import _run_daily_risk_async

        user_id = uuid.uuid4()
        telegram_id = 999888777

        # Mock session factory
        call_count = {"n": 0}

        def _create_session_ctx():
            call_count["n"] += 1
            ctx = AsyncMock()
            session = AsyncMock()

            if call_count["n"] == 1:
                # First call: find users with patterns
                result_mock = MagicMock()
                result_mock.all.return_value = [(user_id, telegram_id)]
                session.execute = AsyncMock(return_value=result_mock)
            # Subsequent calls for risk calculation handled by mock_risk

            ctx.__aenter__ = AsyncMock(return_value=session)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        factory = MagicMock()
        factory.side_effect = _create_session_ctx
        factory.kw = {"bind": AsyncMock()}
        mock_factory.return_value = factory

        # Mock risk calculation to return high risk
        from app.schemas.pattern import RiskScore

        mock_risk.return_value = RiskScore(
            level="high",
            time_window="вечером (18:00–22:00)",
            recommendation="Будьте внимательны к перекусам",
        )

        mock_send.return_value = True

        await _run_daily_risk_async()

        # Notification should be sent for high-risk user
        mock_send.assert_awaited_once()
        args = mock_send.call_args
        assert args.kwargs["chat_id"] == telegram_id
        assert "повышенный риск" in args.kwargs["text"]


class TestFoodReminder:
    """Tests for run_food_reminder."""

    @patch("app.workers.scheduler_jobs.send_telegram_message")
    @patch("app.workers.scheduler_jobs._get_session_factory")
    async def test_run_food_reminder_finds_users(self, mock_factory, mock_send):
        """Finds users without today's entries and sends reminders."""
        from app.workers.scheduler_jobs import _run_food_reminder_async

        user_id = uuid.uuid4()
        telegram_id = 111222333

        # Mock session factory
        def _create_session_ctx():
            ctx = AsyncMock()
            session = AsyncMock()

            result_mock = MagicMock()
            result_mock.all.return_value = [(user_id, telegram_id)]
            session.execute = AsyncMock(return_value=result_mock)

            ctx.__aenter__ = AsyncMock(return_value=session)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        factory = MagicMock()
        factory.side_effect = _create_session_ctx
        factory.kw = {"bind": AsyncMock()}
        mock_factory.return_value = factory

        mock_send.return_value = True

        await _run_food_reminder_async()

        mock_send.assert_awaited_once()
        args = mock_send.call_args
        assert args.kwargs["chat_id"] == telegram_id
        assert "записать" in args.kwargs["text"].lower() or "записать" in args.kwargs["text"]
