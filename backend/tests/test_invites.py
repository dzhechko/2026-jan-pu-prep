"""Tests for the invite / referral feature (US-6.1).

BDD scenarios covered:

Unit tests for invite_service (8 tests):
1. test_generate_code           -- generates 8-char uppercase code
2. test_generate_invite         -- creates invite with correct inviter_id and code
3. test_redeem_invite_success   -- sets invitee_id, redeemed_at, awards premium to both
4. test_redeem_invite_not_found -- invalid code returns None
5. test_redeem_invite_already_redeemed -- already used code returns None
6. test_redeem_invite_self      -- self-redeem returns None
7. test_redeem_extends_existing_premium -- if user already has premium, extends by 7 days
8. test_get_my_invites          -- returns list of user's invites with redemption status

Endpoint tests (4 tests):
9.  test_generate_endpoint       -- POST /api/invite/generate -> 200 with invite_code, share_url
10. test_redeem_endpoint_success -- POST /api/invite/redeem -> 200
11. test_redeem_endpoint_invalid -- POST /api/invite/redeem with bad code -> 400
12. test_my_invites_endpoint     -- GET /api/invite/my -> 200
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.invite import Invite
from app.models.subscription import Subscription
from app.models.user import User


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_INVITEE_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    user_id: uuid.UUID | None = None,
    subscription_status: str = "free",
    subscription_expires_at: datetime | None = None,
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id or FAKE_USER_ID
    user.telegram_id = FAKE_TELEGRAM_ID
    user.first_name = "Test"
    user.subscription_status = subscription_status
    user.subscription_expires_at = subscription_expires_at
    return user


def _make_invite(
    inviter_id: uuid.UUID | None = None,
    invitee_id: uuid.UUID | None = None,
    invite_code: str = "TESTCODE",
    redeemed_at: datetime | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    """Create a mock Invite object."""
    invite = MagicMock(spec=Invite)
    invite.id = uuid.uuid4()
    invite.inviter_id = inviter_id or FAKE_USER_ID
    invite.invitee_id = invitee_id
    invite.invite_code = invite_code
    invite.redeemed_at = redeemed_at
    invite.created_at = created_at or datetime.now(timezone.utc)
    return invite


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
# Unit tests for invite_service
# ===========================================================================


class TestGenerateCode:
    """test_generate_code -- generates 8-char uppercase code."""

    def test_generate_code(self):
        from app.services.invite_service import _generate_code

        code = _generate_code()
        assert len(code) == 8
        assert code == code.upper()
        # Should be URL-safe characters (alphanumeric + - _)
        assert all(c.isalnum() or c in "-_" for c in code)

    def test_generate_code_custom_length(self):
        from app.services.invite_service import _generate_code

        code = _generate_code(length=12)
        assert len(code) == 12
        assert code == code.upper()


class TestGenerateInvite:
    """test_generate_invite -- creates invite with correct inviter_id and code."""

    async def test_generate_invite(self):
        from app.services.invite_service import generate_invite

        session = AsyncMock()

        # db.execute for uniqueness check -> no collision
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        added_objects = []

        def _add_side_effect(obj):
            if isinstance(obj, Invite):
                if obj.id is None:
                    obj.id = uuid.uuid4()
                added_objects.append(obj)

        session.add = MagicMock(side_effect=_add_side_effect)
        session.flush = AsyncMock()

        invite = await generate_invite(session, FAKE_USER_ID)

        assert invite is not None
        assert invite.inviter_id == FAKE_USER_ID
        assert invite.invite_code is not None
        assert len(invite.invite_code) == 8
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


class TestRedeemInviteSuccess:
    """test_redeem_invite_success -- sets invitee_id, redeemed_at, awards premium."""

    async def test_redeem_invite_success(self):
        from app.services.invite_service import redeem_invite

        inviter_id = FAKE_USER_ID
        invitee_id = FAKE_INVITEE_ID

        # Create a real-ish Invite mock
        invite = MagicMock(spec=Invite)
        invite.id = uuid.uuid4()
        invite.inviter_id = inviter_id
        invite.invitee_id = None  # Not yet redeemed
        invite.invite_code = "ABCD1234"
        invite.redeemed_at = None

        inviter_user = _make_user(user_id=inviter_id, subscription_status="free")
        invitee_user = _make_user(user_id=invitee_id, subscription_status="free")

        session = AsyncMock()

        # db.execute for finding the invite
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = invite
        session.execute = AsyncMock(return_value=result_mock)

        # db.get for _award_premium: first call inviter, second call invitee
        session.get = AsyncMock(side_effect=[inviter_user, invitee_user])

        added_objects = []

        def _add_side_effect(obj):
            added_objects.append(obj)

        session.add = MagicMock(side_effect=_add_side_effect)
        session.flush = AsyncMock()

        result = await redeem_invite(session, "ABCD1234", invitee_id)

        assert result is not None
        assert invite.invitee_id == invitee_id
        assert invite.redeemed_at is not None

        # Should have created 2 Subscription records (one per user)
        subs = [o for o in added_objects if isinstance(o, Subscription)]
        assert len(subs) == 2
        for sub in subs:
            assert sub.plan == "premium"
            assert sub.provider == "invite"
            assert sub.status == "active"
            assert sub.expires_at is not None

        # Both users should be updated to premium
        assert inviter_user.subscription_status == "premium"
        assert inviter_user.subscription_expires_at is not None
        assert invitee_user.subscription_status == "premium"
        assert invitee_user.subscription_expires_at is not None


class TestRedeemInviteNotFound:
    """test_redeem_invite_not_found -- invalid code returns None."""

    async def test_redeem_invite_not_found(self):
        from app.services.invite_service import redeem_invite

        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        result = await redeem_invite(session, "BADCODE1", FAKE_INVITEE_ID)
        assert result is None


class TestRedeemInviteAlreadyRedeemed:
    """test_redeem_invite_already_redeemed -- already used code returns None."""

    async def test_redeem_invite_already_redeemed(self):
        from app.services.invite_service import redeem_invite

        invite = MagicMock(spec=Invite)
        invite.inviter_id = FAKE_USER_ID
        invite.invitee_id = uuid.uuid4()  # Already redeemed
        invite.invite_code = "USED1234"

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = invite
        session.execute = AsyncMock(return_value=result_mock)

        result = await redeem_invite(session, "USED1234", FAKE_INVITEE_ID)
        assert result is None


class TestRedeemInviteSelf:
    """test_redeem_invite_self -- self-redeem returns None."""

    async def test_redeem_invite_self(self):
        from app.services.invite_service import redeem_invite

        invite = MagicMock(spec=Invite)
        invite.inviter_id = FAKE_USER_ID
        invite.invitee_id = None
        invite.invite_code = "SELF1234"

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = invite
        session.execute = AsyncMock(return_value=result_mock)

        # Try to redeem own invite
        result = await redeem_invite(session, "SELF1234", FAKE_USER_ID)
        assert result is None


class TestRedeemExtendsExistingPremium:
    """test_redeem_extends_existing_premium -- extends by 7 days if already premium."""

    async def test_redeem_extends_existing_premium(self):
        from app.services.invite_service import redeem_invite, PREMIUM_DAYS

        inviter_id = FAKE_USER_ID
        invitee_id = FAKE_INVITEE_ID

        now = datetime.now(timezone.utc)
        existing_expiry = now + timedelta(days=10)  # Already has 10 days left

        invite = MagicMock(spec=Invite)
        invite.id = uuid.uuid4()
        invite.inviter_id = inviter_id
        invite.invitee_id = None
        invite.invite_code = "EXTEND12"
        invite.redeemed_at = None

        # Inviter already has premium
        inviter_user = _make_user(
            user_id=inviter_id,
            subscription_status="premium",
            subscription_expires_at=existing_expiry,
        )
        # Invitee is free
        invitee_user = _make_user(
            user_id=invitee_id,
            subscription_status="free",
        )

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = invite
        session.execute = AsyncMock(return_value=result_mock)
        session.get = AsyncMock(side_effect=[inviter_user, invitee_user])

        added_objects = []

        def _add_side_effect(obj):
            added_objects.append(obj)

        session.add = MagicMock(side_effect=_add_side_effect)
        session.flush = AsyncMock()

        result = await redeem_invite(session, "EXTEND12", invitee_id)
        assert result is not None

        # Inviter should have expiry extended from existing_expiry + 7 days
        expected_inviter_expiry = existing_expiry + timedelta(days=PREMIUM_DAYS)
        assert inviter_user.subscription_expires_at is not None
        # Compare with small tolerance
        diff = abs(
            (inviter_user.subscription_expires_at - expected_inviter_expiry).total_seconds()
        )
        assert diff < 2  # Within 2 seconds tolerance

        # Invitee should have expiry from now + 7 days
        assert invitee_user.subscription_status == "premium"
        assert invitee_user.subscription_expires_at is not None


class TestGetMyInvites:
    """test_get_my_invites -- returns list of user's invites with redemption status."""

    async def test_get_my_invites(self):
        from app.services.invite_service import get_my_invites, build_share_url

        now = datetime.now(timezone.utc)

        # Two invites: one redeemed, one pending
        invite1 = MagicMock(spec=Invite)
        invite1.id = uuid.uuid4()
        invite1.inviter_id = FAKE_USER_ID
        invite1.invite_code = "CODE0001"
        invite1.invitee_id = FAKE_INVITEE_ID
        invite1.redeemed_at = now
        invite1.created_at = now - timedelta(days=1)

        invite2 = MagicMock(spec=Invite)
        invite2.id = uuid.uuid4()
        invite2.inviter_id = FAKE_USER_ID
        invite2.invite_code = "CODE0002"
        invite2.invitee_id = None
        invite2.redeemed_at = None
        invite2.created_at = now

        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [invite2, invite1]  # desc by created_at
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        data = await get_my_invites(session, FAKE_USER_ID)

        assert data["total_redeemed"] == 1
        assert len(data["invites"]) == 2

        # First invite (most recent) is not redeemed
        assert data["invites"][0]["invite_code"] == "CODE0002"
        assert data["invites"][0]["redeemed"] is False
        assert data["invites"][0]["share_url"] == build_share_url("CODE0002")

        # Second invite is redeemed
        assert data["invites"][1]["invite_code"] == "CODE0001"
        assert data["invites"][1]["redeemed"] is True
        assert data["invites"][1]["invitee_id"] == FAKE_INVITEE_ID


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestGenerateEndpoint:
    """test_generate_endpoint -- POST /api/invite/generate -> 200."""

    async def test_generate_endpoint(self, app, client: AsyncClient):
        """POST /api/invite/generate returns invite_code and share_url."""
        session = AsyncMock()

        # Mock for generate_invite uniqueness check
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        added_objects = []

        def _add_side_effect(obj):
            if isinstance(obj, Invite):
                if obj.id is None:
                    obj.id = uuid.uuid4()
                added_objects.append(obj)

        session.add = MagicMock(side_effect=_add_side_effect)
        session.flush = AsyncMock()

        _override_dependencies(app, session)

        try:
            response = await client.post("/api/invite/generate")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert "invite_code" in body
        assert len(body["invite_code"]) == 8
        assert "share_url" in body
        assert body["invite_code"] in body["share_url"]
        assert "https://t.me/nutrimind_bot?start=invite_" in body["share_url"]


class TestRedeemEndpointSuccess:
    """test_redeem_endpoint_success -- POST /api/invite/redeem -> 200."""

    async def test_redeem_endpoint_success(self, app, client: AsyncClient):
        """POST /api/invite/redeem with valid code returns 200."""
        invite_code = "VALID123"
        inviter_id = uuid.uuid4()

        invite = MagicMock(spec=Invite)
        invite.id = uuid.uuid4()
        invite.inviter_id = inviter_id
        invite.invitee_id = None
        invite.invite_code = invite_code
        invite.redeemed_at = None

        inviter_user = _make_user(user_id=inviter_id, subscription_status="free")
        invitee_user = _make_user(user_id=FAKE_USER_ID, subscription_status="free")

        session = AsyncMock()

        # db.execute for finding the invite
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = invite
        session.execute = AsyncMock(return_value=result_mock)

        # db.get for _award_premium
        session.get = AsyncMock(side_effect=[inviter_user, invitee_user])

        session.add = MagicMock()
        session.flush = AsyncMock()

        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/invite/redeem",
                json={"invite_code": invite_code},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["message"] == "Invite redeemed successfully"
        assert body["premium_days"] == 7


class TestRedeemEndpointInvalid:
    """test_redeem_endpoint_invalid -- POST /api/invite/redeem with bad code -> 400."""

    async def test_redeem_endpoint_invalid(self, app, client: AsyncClient):
        """POST /api/invite/redeem with invalid code returns 400."""
        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/invite/redeem",
                json={"invite_code": "INVALID1"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 400


class TestMyInvitesEndpoint:
    """test_my_invites_endpoint -- GET /api/invite/my -> 200."""

    async def test_my_invites_endpoint(self, app, client: AsyncClient):
        """GET /api/invite/my returns invites list."""
        now = datetime.now(timezone.utc)

        invite1 = MagicMock(spec=Invite)
        invite1.id = uuid.uuid4()
        invite1.inviter_id = FAKE_USER_ID
        invite1.invite_code = "MYCODE01"
        invite1.invitee_id = None
        invite1.redeemed_at = None
        invite1.created_at = now

        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [invite1]
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        _override_dependencies(app, session)

        try:
            response = await client.get("/api/invite/my")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert "invites" in body
        assert "total_redeemed" in body
        assert len(body["invites"]) == 1
        assert body["invites"][0]["invite_code"] == "MYCODE01"
        assert body["invites"][0]["redeemed"] is False
        assert body["total_redeemed"] == 0
        assert "share_url" in body["invites"][0]
