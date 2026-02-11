"""Tests for the payments / subscription feature (US-5.1 / US-5.2).

Unit tests for payment_service (8 tests):
1.  test_create_subscription -- creates subscription, updates user status to "premium"
2.  test_create_subscription_sets_expiry -- expires_at is ~30 days from now
3.  test_cancel_subscription_active -- cancels active subscription, returns True
4.  test_cancel_subscription_none -- no active subscription, returns False
5.  test_cancel_sets_cancelled_status -- user.subscription_status becomes "cancelled"
6.  test_get_subscription_status_active -- returns active subscription info
7.  test_get_subscription_status_none -- no subscription, returns status="none"
8.  test_get_subscription_status_cancelled -- returns cancelled subscription info

Endpoint tests (4 tests):
9.  test_subscribe_endpoint -- POST /api/payments/subscribe -> 200
10. test_get_subscription_endpoint -- GET /api/payments/subscription -> 200
11. test_cancel_subscription_endpoint -- DELETE /api/payments/subscription -> 200
12. test_cancel_no_subscription_endpoint -- DELETE when no subscription -> 404
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.subscription import Subscription
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
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.telegram_id = FAKE_TELEGRAM_ID
    user.first_name = "Test"
    user.subscription_status = subscription_status
    user.subscription_expires_at = None
    user.insights_received = 0
    user.onboarding_complete = True
    return user


def _make_subscription(
    user_id: uuid.UUID = FAKE_USER_ID,
    plan: str = "premium",
    status: str = "active",
    expires_at: datetime | None = None,
    cancelled_at: datetime | None = None,
) -> MagicMock:
    """Create a mock Subscription object."""
    sub = MagicMock(spec=Subscription)
    sub.id = uuid.uuid4()
    sub.user_id = user_id
    sub.plan = plan
    sub.provider = "telegram"
    sub.provider_id = None
    sub.status = status
    sub.started_at = datetime.now(timezone.utc)
    sub.expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(days=30))
    sub.cancelled_at = cancelled_at
    return sub


def _override_dependencies(app, session, user_id=FAKE_USER_ID):
    """Override get_db and get_current_user dependencies on the app."""
    from app.dependencies import get_db, get_current_user

    async def _override_get_db():
        yield session

    async def _override_get_current_user():
        return {"user_id": user_id, "telegram_id": FAKE_TELEGRAM_ID}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user


def _make_mock_db_for_create(user: MagicMock):
    """Create a mock DB session for create_subscription testing.

    Simulates:
        - db.execute(select User) -> user
        - db.add(subscription)
        - db.flush()
    """
    session = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=result_mock)

    added_objects: list = []

    def _add_side_effect(obj):
        if isinstance(obj, Subscription):
            if obj.id is None:
                obj.id = uuid.uuid4()
            added_objects.append(obj)

    session.add = MagicMock(side_effect=_add_side_effect)
    session.flush = AsyncMock()

    return session


def _make_mock_db_for_cancel(subscription: MagicMock | None, user: MagicMock | None):
    """Create a mock DB session for cancel_subscription testing.

    Two execute calls:
        1. select Subscription where active -> subscription
        2. select User -> user
    """
    session = AsyncMock()

    call_count = {"n": 0}

    def _execute_side_effect(stmt):
        result_mock = MagicMock()
        call_count["n"] += 1
        if call_count["n"] == 1:
            # First call: find active subscription
            result_mock.scalar_one_or_none.return_value = subscription
        else:
            # Second call: find user
            result_mock.scalar_one_or_none.return_value = user
        return result_mock

    session.execute = AsyncMock(side_effect=_execute_side_effect)
    session.flush = AsyncMock()

    return session


def _make_mock_db_for_get_status(subscription: MagicMock | None):
    """Create a mock DB session for get_subscription_status testing.

    One execute call:
        - select Subscription order by started_at desc limit 1 -> subscription
    """
    session = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = subscription
    session.execute = AsyncMock(return_value=result_mock)

    return session


# ===========================================================================
# Unit tests for payment_service
# ===========================================================================


class TestCreateSubscription:
    """Unit tests for payment_service.create_subscription."""

    async def test_create_subscription(self):
        """Creates subscription and updates user status to 'premium'."""
        from app.services.payment_service import create_subscription

        user = _make_user(subscription_status="free")
        session = _make_mock_db_for_create(user)

        subscription = await create_subscription(
            session, FAKE_USER_ID, plan="premium", provider="telegram"
        )

        assert isinstance(subscription, Subscription)
        assert subscription.plan == "premium"
        assert subscription.status == "active"
        assert subscription.user_id == FAKE_USER_ID
        # User status should be updated
        assert user.subscription_status == "premium"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_create_subscription_sets_expiry(self):
        """expires_at should be approximately 30 days from now."""
        from app.services.payment_service import create_subscription

        user = _make_user(subscription_status="free")
        session = _make_mock_db_for_create(user)

        now = datetime.now(timezone.utc)
        subscription = await create_subscription(
            session, FAKE_USER_ID, plan="premium"
        )

        assert subscription.expires_at is not None
        # Should be roughly 30 days from now (within 5 seconds tolerance)
        expected = now + timedelta(days=30)
        delta = abs((subscription.expires_at - expected).total_seconds())
        assert delta < 5, f"expires_at off by {delta}s"
        # User should also have the expiry set
        assert user.subscription_expires_at == subscription.expires_at


class TestCancelSubscription:
    """Unit tests for payment_service.cancel_subscription."""

    async def test_cancel_subscription_active(self):
        """Cancels active subscription, returns True."""
        from app.services.payment_service import cancel_subscription

        user = _make_user(subscription_status="premium")
        sub = _make_subscription(status="active")
        session = _make_mock_db_for_cancel(subscription=sub, user=user)

        result = await cancel_subscription(session, FAKE_USER_ID)

        assert result is True
        assert sub.status == "cancelled"
        assert sub.cancelled_at is not None
        session.flush.assert_awaited_once()

    async def test_cancel_subscription_none(self):
        """No active subscription, returns False."""
        from app.services.payment_service import cancel_subscription

        session = _make_mock_db_for_cancel(subscription=None, user=None)

        result = await cancel_subscription(session, FAKE_USER_ID)

        assert result is False

    async def test_cancel_sets_cancelled_status(self):
        """user.subscription_status becomes 'cancelled' after cancel."""
        from app.services.payment_service import cancel_subscription

        user = _make_user(subscription_status="premium")
        sub = _make_subscription(status="active")
        session = _make_mock_db_for_cancel(subscription=sub, user=user)

        await cancel_subscription(session, FAKE_USER_ID)

        assert user.subscription_status == "cancelled"


class TestGetSubscriptionStatus:
    """Unit tests for payment_service.get_subscription_status."""

    async def test_get_subscription_status_active(self):
        """Returns active subscription info."""
        from app.services.payment_service import get_subscription_status

        expires = datetime.now(timezone.utc) + timedelta(days=25)
        sub = _make_subscription(status="active", expires_at=expires, cancelled_at=None)
        session = _make_mock_db_for_get_status(subscription=sub)

        info = await get_subscription_status(session, FAKE_USER_ID)

        assert info["status"] == "active"
        assert info["plan"] == "premium"
        assert info["expires_at"] == expires
        assert info["cancelled_at"] is None

    async def test_get_subscription_status_none(self):
        """No subscription -> status='none'."""
        from app.services.payment_service import get_subscription_status

        session = _make_mock_db_for_get_status(subscription=None)

        info = await get_subscription_status(session, FAKE_USER_ID)

        assert info["status"] == "none"
        assert info["plan"] is None
        assert info["expires_at"] is None
        assert info["cancelled_at"] is None

    async def test_get_subscription_status_cancelled(self):
        """Returns cancelled subscription info."""
        from app.services.payment_service import get_subscription_status

        expires = datetime.now(timezone.utc) + timedelta(days=10)
        cancelled_at = datetime.now(timezone.utc) - timedelta(days=5)
        sub = _make_subscription(
            status="cancelled", expires_at=expires, cancelled_at=cancelled_at
        )
        session = _make_mock_db_for_get_status(subscription=sub)

        info = await get_subscription_status(session, FAKE_USER_ID)

        assert info["status"] == "cancelled"
        assert info["plan"] == "premium"
        assert info["expires_at"] == expires
        assert info["cancelled_at"] == cancelled_at


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestSubscribeEndpoint:
    """Endpoint tests for POST /api/payments/subscribe."""

    async def test_subscribe_endpoint(self, app, client: AsyncClient):
        """POST /api/payments/subscribe -> 200 with plan and expires_at."""
        user = _make_user(subscription_status="free")
        session = _make_mock_db_for_create(user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/payments/subscribe",
                json={"plan": "premium", "provider": "telegram"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["plan"] == "premium"
        assert "expires_at" in body


class TestGetSubscriptionEndpoint:
    """Endpoint tests for GET /api/payments/subscription."""

    async def test_get_subscription_endpoint(self, app, client: AsyncClient):
        """GET /api/payments/subscription -> 200 with subscription info."""
        expires = datetime.now(timezone.utc) + timedelta(days=25)
        sub = _make_subscription(status="active", expires_at=expires)
        session = _make_mock_db_for_get_status(subscription=sub)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/payments/subscription")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "active"
        assert body["plan"] == "premium"
        assert body["expires_at"] is not None
        assert body["cancelled_at"] is None


class TestCancelSubscriptionEndpoint:
    """Endpoint tests for DELETE /api/payments/subscription."""

    async def test_cancel_subscription_endpoint(self, app, client: AsyncClient):
        """DELETE /api/payments/subscription -> 200 when active subscription exists."""
        user = _make_user(subscription_status="premium")
        sub = _make_subscription(status="active")
        session = _make_mock_db_for_cancel(subscription=sub, user=user)
        _override_dependencies(app, session)

        try:
            response = await client.delete("/api/payments/subscription")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["message"] == "Subscription cancelled"

    async def test_cancel_no_subscription_endpoint(self, app, client: AsyncClient):
        """DELETE /api/payments/subscription -> 404 when no active subscription."""
        session = _make_mock_db_for_cancel(subscription=None, user=None)
        _override_dependencies(app, session)

        try:
            response = await client.delete("/api/payments/subscription")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
