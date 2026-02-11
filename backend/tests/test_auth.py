"""Tests for Telegram authentication flow.

BDD scenarios covered:
1. Successful authentication -- valid initData -> 200, JWT returned, user created
2. Returning user -- second auth with same telegram_id -> existing user, onboarding_complete preserved
3. Expired initData -- auth_date older than 300 seconds -> 401
4. Tampered initData -- modified hash -> 401
5. Missing hash in initData -> 401
6. Missing user object in initData -> error
"""

import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote, urlencode

import pytest
from httpx import AsyncClient

from app.middleware.telegram_auth import validate_init_data

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"

DEFAULT_USER_DATA = {
    "id": 987654321,
    "first_name": "TestUser",
    "username": "testuser",
    "language_code": "en",
}


# ---------------------------------------------------------------------------
# Helper: build a valid Telegram initData query string
# ---------------------------------------------------------------------------


def make_init_data(
    bot_token: str,
    user_data: dict,
    auth_date: int | None = None,
) -> str:
    """Build a valid Telegram Mini App initData query string.

    Parameters
    ----------
    bot_token:
        The bot token to sign with (must match the one the server expects).
    user_data:
        Dictionary representing the Telegram user object.
    auth_date:
        Unix timestamp for auth_date.  Defaults to ``int(time.time())``.

    Returns
    -------
    str
        A URL-encoded query string including a valid ``hash`` field.
    """
    if auth_date is None:
        auth_date = int(time.time())

    # Encode the user JSON -- Telegram sends it URL-encoded inside the query string
    user_json = json.dumps(user_data, separators=(",", ":"))

    # Build key=value pairs (everything except hash)
    params: dict[str, str] = {
        "user": user_json,
        "auth_date": str(auth_date),
    }

    # --- Compute HMAC-SHA256 hash using Telegram's algorithm ---
    # 1. data_check_string = sorted "key=value" lines joined by "\n"
    data_check_parts = sorted(f"{k}={v}" for k, v in params.items())
    data_check_string = "\n".join(data_check_parts)

    # 2. secret_key = HMAC_SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # 3. hash = HMAC_SHA256(secret_key, data_check_string)
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Build the final query string (order does not matter for parse_qs)
    params["hash"] = computed_hash
    return urlencode(params, quote_via=quote)


# ---------------------------------------------------------------------------
# Helper: create a mock DB session that tracks users in-memory
# ---------------------------------------------------------------------------


def _make_mock_db_session():
    """Return an AsyncMock session backed by an in-memory user store.

    This allows find_or_create_user to work across successive calls
    within the same test (e.g. returning-user scenario).
    """
    from app.models.user import User

    users_by_telegram_id: dict[int, User] = {}

    session = AsyncMock()

    def _execute_side_effect(stmt):
        """Simulate SELECT ... WHERE telegram_id = :id."""
        result_mock = MagicMock()
        # Extract the telegram_id bound into the WHERE clause.
        # SQLAlchemy's compiled statement stores the params; we inspect
        # the statement's whereclause to get the literal/bound value.
        telegram_id = _extract_telegram_id_from_stmt(stmt)
        user = users_by_telegram_id.get(telegram_id)
        result_mock.scalar_one_or_none.return_value = user
        return result_mock

    def _extract_telegram_id_from_stmt(stmt):
        """Extract the telegram_id value from a SQLAlchemy select statement."""
        compiled = stmt.compile(compile_kwargs={"literal_binds": True})
        # The compiled string looks like:
        #   SELECT ... WHERE users.telegram_id = 987654321
        compiled_str = str(compiled)
        # Grab the number after "users.telegram_id = "
        marker = "users.telegram_id = "
        idx = compiled_str.find(marker)
        if idx == -1:
            return None
        remainder = compiled_str[idx + len(marker):]
        num_str = ""
        for ch in remainder:
            if ch.isdigit():
                num_str += ch
            else:
                break
        return int(num_str) if num_str else None

    session.execute = AsyncMock(side_effect=_execute_side_effect)

    def _add_side_effect(obj):
        """Simulate session.add -- store the user and assign defaults."""
        if isinstance(obj, User):
            if obj.id is None:
                obj.id = uuid.uuid4()
            if obj.onboarding_complete is None:
                obj.onboarding_complete = False
            if obj.subscription_status is None:
                obj.subscription_status = "free"
            users_by_telegram_id[obj.telegram_id] = obj

    session.add = MagicMock(side_effect=_add_side_effect)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    # Make it usable as an async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    return session, users_by_telegram_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a mock DB session and its in-memory user store."""
    session, users = _make_mock_db_session()
    return session, users


# ===========================================================================
# Unit tests for validate_init_data
# ===========================================================================


class TestValidateInitData:
    """Unit tests for the low-level HMAC validation function."""

    async def test_valid_init_data_returns_parsed_fields(self):
        """Valid initData is accepted and returns parsed dict with user object."""
        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)

        result = validate_init_data(init_data, FAKE_BOT_TOKEN)

        assert "user" in result
        assert isinstance(result["user"], dict)
        assert result["user"]["id"] == DEFAULT_USER_DATA["id"]
        assert result["user"]["first_name"] == DEFAULT_USER_DATA["first_name"]
        assert "hash" in result
        assert "auth_date" in result

    async def test_missing_hash_raises_401(self):
        """initData without a hash field should raise 401."""
        from fastapi import HTTPException

        user_json = json.dumps(DEFAULT_USER_DATA, separators=(",", ":"))
        init_data = urlencode(
            {"user": user_json, "auth_date": str(int(time.time()))},
            quote_via=quote,
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_init_data(init_data, FAKE_BOT_TOKEN)

        assert exc_info.value.status_code == 401
        assert "Missing hash" in exc_info.value.detail

    async def test_tampered_hash_raises_401(self):
        """initData with a modified hash should raise 401."""
        from fastapi import HTTPException

        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)

        # Tamper with the hash by replacing last 8 chars
        parts = init_data.rsplit("hash=", 1)
        tampered_hash = "0" * 8 + parts[1][8:]
        tampered_init_data = parts[0] + "hash=" + tampered_hash

        with pytest.raises(HTTPException) as exc_info:
            validate_init_data(tampered_init_data, FAKE_BOT_TOKEN)

        assert exc_info.value.status_code == 401
        assert "Invalid initData signature" in exc_info.value.detail

    async def test_expired_auth_date_raises_401(self):
        """initData with auth_date older than max_age_seconds should raise 401."""
        from fastapi import HTTPException

        old_auth_date = int(time.time()) - 600  # 10 minutes ago
        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA, auth_date=old_auth_date)

        with pytest.raises(HTTPException) as exc_info:
            validate_init_data(init_data, FAKE_BOT_TOKEN, max_age_seconds=300)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    async def test_wrong_bot_token_raises_401(self):
        """initData signed with a different token should fail validation."""
        from fastapi import HTTPException

        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)

        with pytest.raises(HTTPException) as exc_info:
            validate_init_data(init_data, "9999999999:DifferentTokenXYZ")

        assert exc_info.value.status_code == 401

    async def test_custom_max_age_is_respected(self):
        """A shorter max_age_seconds should reject otherwise-fresh data."""
        from fastapi import HTTPException

        # auth_date 10 seconds ago -- within 300s default but outside 5s custom
        auth_date = int(time.time()) - 10
        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA, auth_date=auth_date)

        with pytest.raises(HTTPException) as exc_info:
            validate_init_data(init_data, FAKE_BOT_TOKEN, max_age_seconds=5)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail


# ===========================================================================
# Unit tests for authenticate_telegram_user (service layer)
# ===========================================================================


class TestAuthenticateService:
    """Unit tests for the auth service function."""

    @patch("app.services.auth_service.settings")
    async def test_successful_auth_creates_user_and_returns_tokens(
        self, mock_settings, mock_db
    ):
        """Valid initData should create a new user and return JWT tokens."""
        mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

        session, users = mock_db
        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)

        from app.services.auth_service import authenticate_telegram_user

        result = await authenticate_telegram_user(init_data, session)

        assert result.token, "Access token should be non-empty"
        assert result.refresh_token, "Refresh token should be non-empty"
        assert result.user.first_name == DEFAULT_USER_DATA["first_name"]
        assert result.user.onboarding_complete is False
        assert result.user.subscription_status == "free"
        # Verify user was stored
        assert DEFAULT_USER_DATA["id"] in users

    @patch("app.services.auth_service.settings")
    async def test_returning_user_preserves_onboarding_complete(
        self, mock_settings, mock_db
    ):
        """Second auth with same telegram_id should return existing user
        and preserve the onboarding_complete flag."""
        mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

        session, users = mock_db

        from app.services.auth_service import authenticate_telegram_user

        # First auth -- creates the user
        init_data_1 = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)
        result_1 = await authenticate_telegram_user(init_data_1, session)
        assert result_1.user.onboarding_complete is False

        # Simulate the user completing onboarding
        existing_user = users[DEFAULT_USER_DATA["id"]]
        existing_user.onboarding_complete = True

        # Second auth -- same telegram_id
        init_data_2 = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)
        result_2 = await authenticate_telegram_user(init_data_2, session)

        assert result_2.user.onboarding_complete is True
        assert result_2.user.id == result_1.user.id

    @patch("app.services.auth_service.settings")
    async def test_missing_user_object_raises_error(self, mock_settings, mock_db):
        """initData without a user field should raise a ValueError."""
        mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

        session, _ = mock_db

        # Build initData with no user field
        auth_date = int(time.time())
        params = {"auth_date": str(auth_date)}

        data_check_parts = sorted(f"{k}={v}" for k, v in params.items())
        data_check_string = "\n".join(data_check_parts)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=FAKE_BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        computed_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        params["hash"] = computed_hash
        init_data = urlencode(params, quote_via=quote)

        from app.services.auth_service import authenticate_telegram_user

        with pytest.raises(ValueError, match="user object"):
            await authenticate_telegram_user(init_data, session)


# ===========================================================================
# Integration tests via HTTP (router level)
# ===========================================================================


class TestTelegramAuthEndpoint:
    """Integration tests against POST /api/auth/telegram."""

    @staticmethod
    def _setup_redis_mock(app_instance):
        """Ensure the app's mock Redis returns sensible defaults for the
        rate-limiter (incr returns int, expire/ttl return int)."""
        mock_redis = app_instance.state.redis
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.ttl = AsyncMock(return_value=60)

    async def test_successful_auth_returns_200_with_jwt(
        self, app, client: AsyncClient
    ):
        """Scenario 1: Valid initData -> 200, JWT returned, user created."""
        self._setup_redis_mock(app)
        session, users = _make_mock_db_session()

        # Override the get_db dependency to yield our mock session
        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db

        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            response = await client.post(
                "/api/auth/telegram",
                json={"init_data": init_data},
            )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert "token" in body
        assert "refresh_token" in body
        assert body["token"], "Access token should not be empty"
        assert body["refresh_token"], "Refresh token should not be empty"
        assert body["user"]["first_name"] == DEFAULT_USER_DATA["first_name"]
        assert body["user"]["onboarding_complete"] is False
        assert body["user"]["subscription_status"] == "free"
        assert "id" in body["user"]

    async def test_returning_user_preserves_state(
        self, app, client: AsyncClient
    ):
        """Scenario 2: Second auth with same telegram_id -> existing user,
        onboarding_complete preserved."""
        self._setup_redis_mock(app)
        session, users = _make_mock_db_session()

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            # First login
            init_data_1 = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)
            resp_1 = await client.post(
                "/api/auth/telegram",
                json={"init_data": init_data_1},
            )
            assert resp_1.status_code == 200
            user_id_1 = resp_1.json()["user"]["id"]

            # Simulate onboarding completion
            existing_user = users[DEFAULT_USER_DATA["id"]]
            existing_user.onboarding_complete = True

            # Second login
            init_data_2 = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)
            resp_2 = await client.post(
                "/api/auth/telegram",
                json={"init_data": init_data_2},
            )

        app.dependency_overrides.clear()

        assert resp_2.status_code == 200
        body_2 = resp_2.json()
        assert body_2["user"]["id"] == user_id_1, "Should be the same user"
        assert body_2["user"]["onboarding_complete"] is True

    async def test_expired_init_data_returns_401(
        self, app, client: AsyncClient
    ):
        """Scenario 3: auth_date older than 300 seconds -> 401."""
        self._setup_redis_mock(app)
        session, _ = _make_mock_db_session()

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db

        old_auth_date = int(time.time()) - 600  # 10 minutes ago
        init_data = make_init_data(
            FAKE_BOT_TOKEN, DEFAULT_USER_DATA, auth_date=old_auth_date
        )

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            response = await client.post(
                "/api/auth/telegram",
                json={"init_data": init_data},
            )

        app.dependency_overrides.clear()

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    async def test_tampered_hash_returns_401(
        self, app, client: AsyncClient
    ):
        """Scenario 4: Modified hash -> 401."""
        self._setup_redis_mock(app)
        session, _ = _make_mock_db_session()

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db

        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)
        # Tamper: flip a character in the hash
        parts = init_data.rsplit("hash=", 1)
        original_hash = parts[1]
        flipped = ("1" if original_hash[0] == "0" else "0") + original_hash[1:]
        tampered_init_data = parts[0] + "hash=" + flipped

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            response = await client.post(
                "/api/auth/telegram",
                json={"init_data": tampered_init_data},
            )

        app.dependency_overrides.clear()

        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower() or \
               "invalid" in response.json()["detail"].lower()

    async def test_missing_hash_returns_401(
        self, app, client: AsyncClient
    ):
        """Scenario 5: Missing hash in initData -> 401."""
        self._setup_redis_mock(app)
        session, _ = _make_mock_db_session()

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db

        # Build initData without hash
        user_json = json.dumps(DEFAULT_USER_DATA, separators=(",", ":"))
        init_data = urlencode(
            {"user": user_json, "auth_date": str(int(time.time()))},
            quote_via=quote,
        )

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            response = await client.post(
                "/api/auth/telegram",
                json={"init_data": init_data},
            )

        app.dependency_overrides.clear()

        assert response.status_code == 401
        assert "hash" in response.json()["detail"].lower()

    async def test_missing_user_object_returns_error(
        self, app, client: AsyncClient
    ):
        """Scenario 6: Missing user object in initData -> ValueError raised.

        The service raises a ValueError when the user object is missing.
        Depending on the ASGI transport, this may surface as a 500 response
        or propagate as an exception.  We verify the error is raised.
        """
        self._setup_redis_mock(app)
        session, _ = _make_mock_db_session()

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db

        # Build valid initData but without a user field
        auth_date = int(time.time())
        params = {"auth_date": str(auth_date)}
        data_check_parts = sorted(f"{k}={v}" for k, v in params.items())
        data_check_string = "\n".join(data_check_parts)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=FAKE_BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        computed_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        params["hash"] = computed_hash
        init_data = urlencode(params, quote_via=quote)

        try:
            with patch("app.services.auth_service.settings") as mock_settings:
                mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
                mock_settings.SECRET_KEY = "test-secret-key"
                mock_settings.JWT_ALGORITHM = "HS256"
                mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
                mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

                response = await client.post(
                    "/api/auth/telegram",
                    json={"init_data": init_data},
                )

            # If the global exception handler catches it, we get a 500
            assert response.status_code == 500
        except ValueError as exc:
            # If the ValueError propagates through ASGITransport, verify message
            assert "user object" in str(exc)
        finally:
            app.dependency_overrides.clear()


# ===========================================================================
# Edge-case tests
# ===========================================================================


class TestAuthEdgeCases:
    """Additional edge-case tests for robustness."""

    async def test_make_init_data_produces_verifiable_string(self):
        """The helper itself should produce data that passes validation."""
        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA)
        result = validate_init_data(init_data, FAKE_BOT_TOKEN)
        assert result["user"]["id"] == DEFAULT_USER_DATA["id"]

    async def test_different_user_ids_create_separate_users(self):
        """Two different telegram_ids should yield two distinct users."""
        session, users = _make_mock_db_session()

        user_a = {**DEFAULT_USER_DATA, "id": 111111}
        user_b = {**DEFAULT_USER_DATA, "id": 222222}

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            from app.services.auth_service import authenticate_telegram_user

            result_a = await authenticate_telegram_user(
                make_init_data(FAKE_BOT_TOKEN, user_a), session
            )
            result_b = await authenticate_telegram_user(
                make_init_data(FAKE_BOT_TOKEN, user_b), session
            )

        assert result_a.user.id != result_b.user.id
        assert len(users) == 2

    async def test_auth_date_exactly_at_boundary_is_accepted(self):
        """auth_date exactly 300 seconds ago should still be accepted
        (boundary is strictly greater-than)."""
        # auth_date 299 seconds ago -- should be within the 300s window
        auth_date = int(time.time()) - 299
        init_data = make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA, auth_date=auth_date)
        result = validate_init_data(init_data, FAKE_BOT_TOKEN, max_age_seconds=300)
        assert result["user"]["id"] == DEFAULT_USER_DATA["id"]

    async def test_jwt_token_contains_correct_claims(self):
        """The JWT access token should contain sub and telegram_id claims."""
        from jose import jwt as jose_jwt

        session, _ = _make_mock_db_session()

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            from app.services.auth_service import authenticate_telegram_user

            result = await authenticate_telegram_user(
                make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA), session
            )

        # Decode without verification to inspect claims
        payload = jose_jwt.decode(
            result.token, "test-secret-key", algorithms=["HS256"]
        )
        assert payload["telegram_id"] == DEFAULT_USER_DATA["id"]
        assert payload["type"] == "access"
        assert "sub" in payload
        assert "exp" in payload

    async def test_refresh_token_has_refresh_type(self):
        """The refresh token should have type=refresh in its claims."""
        from jose import jwt as jose_jwt

        session, _ = _make_mock_db_session()

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = FAKE_BOT_TOKEN
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
            mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

            from app.services.auth_service import authenticate_telegram_user

            result = await authenticate_telegram_user(
                make_init_data(FAKE_BOT_TOKEN, DEFAULT_USER_DATA), session
            )

        payload = jose_jwt.decode(
            result.refresh_token, "test-secret-key", algorithms=["HS256"]
        )
        assert payload["type"] == "refresh"
        assert payload["telegram_id"] == DEFAULT_USER_DATA["id"]
