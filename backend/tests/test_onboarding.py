"""Tests for the onboarding interview endpoint.

BDD scenarios covered:
1. Happy path: submit 2 valid answers -> 200, profile_initialized=true, cluster_id assigned
2. Incomplete: submit 1 answer -> 422 validation error
3. Already onboarded: submit again -> still works (updates profile)
4. Invalid question_id -> 422 validation error
5. Cluster assignment logic tests (unit tests for the service)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.models.ai_profile import AIProfile
from app.models.user import User
from app.schemas.onboarding import InterviewAnswer
from app.services.onboarding_service import assign_cluster


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789

VALID_ANSWERS = [
    {"question_id": "eating_schedule", "answer_id": "irregular"},
    {"question_id": "biggest_challenge", "answer_id": "emotional_eating"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_user(
    user_id: uuid.UUID = FAKE_USER_ID,
    onboarding_complete: bool = False,
) -> MagicMock:
    """Create a fake User-like object for testing."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.telegram_id = FAKE_TELEGRAM_ID
    user.first_name = "TestUser"
    user.onboarding_complete = onboarding_complete
    user.subscription_status = "free"
    return user


def _make_mock_db_session(user: User | None = None, ai_profile: AIProfile | None = None):
    """Return an AsyncMock session that simulates DB queries.

    The session can handle two types of queries:
    - SELECT User WHERE id = ...
    - SELECT AIProfile WHERE user_id = ...
    """
    session = AsyncMock()

    call_count = 0

    def _execute_side_effect(stmt):
        nonlocal call_count
        result_mock = MagicMock()
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        if "ai_profiles" in compiled:
            result_mock.scalar_one_or_none.return_value = ai_profile
        elif "users" in compiled:
            result_mock.scalar_one_or_none.return_value = user
        else:
            result_mock.scalar_one_or_none.return_value = None

        call_count += 1
        return result_mock

    session.execute = AsyncMock(side_effect=_execute_side_effect)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    # Make it usable as an async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    return session


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
# Unit tests for cluster assignment service
# ===========================================================================


class TestAssignCluster:
    """Unit tests for the assign_cluster function."""

    def test_emotional_eating_returns_emotional_eater(self):
        answers = [
            InterviewAnswer(question_id="eating_schedule", answer_id="regular"),
            InterviewAnswer(question_id="biggest_challenge", answer_id="emotional_eating"),
        ]
        assert assign_cluster(answers) == "emotional_eater"

    def test_overeating_with_irregular_returns_chaotic_eater(self):
        answers = [
            InterviewAnswer(question_id="eating_schedule", answer_id="irregular"),
            InterviewAnswer(question_id="biggest_challenge", answer_id="overeating"),
        ]
        assert assign_cluster(answers) == "chaotic_eater"

    def test_overeating_with_restrictive_returns_chaotic_eater(self):
        answers = [
            InterviewAnswer(question_id="eating_schedule", answer_id="restrictive"),
            InterviewAnswer(question_id="biggest_challenge", answer_id="overeating"),
        ]
        assert assign_cluster(answers) == "chaotic_eater"

    def test_overeating_with_regular_returns_general(self):
        """overeating without irregular/restrictive eating schedule -> general."""
        answers = [
            InterviewAnswer(question_id="eating_schedule", answer_id="regular"),
            InterviewAnswer(question_id="biggest_challenge", answer_id="overeating"),
        ]
        assert assign_cluster(answers) == "general"

    def test_lack_of_structure_returns_unstructured_eater(self):
        answers = [
            InterviewAnswer(question_id="eating_schedule", answer_id="frequent"),
            InterviewAnswer(question_id="biggest_challenge", answer_id="lack_of_structure"),
        ]
        assert assign_cluster(answers) == "unstructured_eater"

    def test_unhealthy_choices_returns_mindless_eater(self):
        answers = [
            InterviewAnswer(question_id="eating_schedule", answer_id="regular"),
            InterviewAnswer(question_id="biggest_challenge", answer_id="unhealthy_choices"),
        ]
        assert assign_cluster(answers) == "mindless_eater"

    def test_portion_control_returns_general(self):
        """portion_control is not explicitly mapped -> falls through to general."""
        answers = [
            InterviewAnswer(question_id="eating_schedule", answer_id="regular"),
            InterviewAnswer(question_id="biggest_challenge", answer_id="portion_control"),
        ]
        assert assign_cluster(answers) == "general"


# ===========================================================================
# Integration tests via HTTP (router level)
# ===========================================================================


class TestSubmitInterviewEndpoint:
    """Integration tests against POST /api/onboarding/interview."""

    async def test_happy_path_returns_200_with_cluster(
        self, app, client: AsyncClient
    ):
        """Scenario 1: Submit 2 valid answers -> 200, profile_initialized, cluster_id."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user, ai_profile=None)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={"answers": VALID_ANSWERS},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["profile_initialized"] is True
        assert body["cluster_id"] == "emotional_eater"

        # Verify session.add was called (new AIProfile created)
        session.add.assert_called_once()
        # Verify flush was called
        session.flush.assert_awaited_once()
        # Verify onboarding_complete was set
        assert user.onboarding_complete is True

    async def test_incomplete_answers_returns_422(
        self, app, client: AsyncClient
    ):
        """Scenario 2: Submit only 1 answer -> 422 validation error."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={
                    "answers": [
                        {"question_id": "eating_schedule", "answer_id": "regular"},
                    ]
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422
        body = response.json()
        assert "2 answers" in str(body).lower() or "exactly" in str(body).lower()

    async def test_too_many_answers_returns_422(
        self, app, client: AsyncClient
    ):
        """Submit 3 answers -> 422 validation error."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={
                    "answers": [
                        {"question_id": "eating_schedule", "answer_id": "regular"},
                        {"question_id": "biggest_challenge", "answer_id": "overeating"},
                        {"question_id": "eating_schedule", "answer_id": "irregular"},
                    ]
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    async def test_already_onboarded_updates_profile(
        self, app, client: AsyncClient
    ):
        """Scenario 3: Submit again when already onboarded -> still works, updates profile."""
        user = _make_fake_user(onboarding_complete=True)
        existing_profile = MagicMock(spec=AIProfile)
        existing_profile.user_id = FAKE_USER_ID
        existing_profile.interview_answers = [
            {"question_id": "eating_schedule", "answer_id": "regular"},
            {"question_id": "biggest_challenge", "answer_id": "overeating"},
        ]
        existing_profile.cluster_id = "general"

        session = _make_mock_db_session(user=user, ai_profile=existing_profile)
        _override_dependencies(app, session)

        new_answers = [
            {"question_id": "eating_schedule", "answer_id": "irregular"},
            {"question_id": "biggest_challenge", "answer_id": "lack_of_structure"},
        ]

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={"answers": new_answers},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["profile_initialized"] is True
        assert body["cluster_id"] == "unstructured_eater"

        # Verify profile was updated (not created anew)
        session.add.assert_not_called()
        assert existing_profile.cluster_id == "unstructured_eater"
        assert existing_profile.interview_answers == new_answers

    async def test_invalid_question_id_returns_422(
        self, app, client: AsyncClient
    ):
        """Scenario 4: Invalid question_id -> 422 validation error."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={
                    "answers": [
                        {"question_id": "invalid_question", "answer_id": "regular"},
                        {"question_id": "biggest_challenge", "answer_id": "overeating"},
                    ]
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422
        body = response.json()
        assert "invalid_question" in str(body).lower() or "question_id" in str(body).lower()

    async def test_invalid_answer_id_returns_422(
        self, app, client: AsyncClient
    ):
        """Invalid answer_id for a valid question -> 422 validation error."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={
                    "answers": [
                        {"question_id": "eating_schedule", "answer_id": "nonexistent"},
                        {"question_id": "biggest_challenge", "answer_id": "overeating"},
                    ]
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    async def test_user_not_found_returns_404(
        self, app, client: AsyncClient
    ):
        """If the user_id from the token doesn't exist in DB -> 404."""
        session = _make_mock_db_session(user=None)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={"answers": VALID_ANSWERS},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
        body = response.json()
        assert "not found" in body["detail"].lower()

    async def test_empty_answers_returns_422(
        self, app, client: AsyncClient
    ):
        """Empty answers list -> 422 validation error."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={"answers": []},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    async def test_chaotic_eater_cluster_assignment(
        self, app, client: AsyncClient
    ):
        """Verify chaotic_eater cluster: overeating + irregular schedule."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user, ai_profile=None)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={
                    "answers": [
                        {"question_id": "eating_schedule", "answer_id": "irregular"},
                        {"question_id": "biggest_challenge", "answer_id": "overeating"},
                    ]
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["cluster_id"] == "chaotic_eater"

    async def test_mindless_eater_cluster_assignment(
        self, app, client: AsyncClient
    ):
        """Verify mindless_eater cluster: unhealthy_choices."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user, ai_profile=None)
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={
                    "answers": [
                        {"question_id": "eating_schedule", "answer_id": "regular"},
                        {"question_id": "biggest_challenge", "answer_id": "unhealthy_choices"},
                    ]
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["cluster_id"] == "mindless_eater"

    async def test_missing_authorization_returns_401(
        self, app, client: AsyncClient
    ):
        """Request without overriding get_current_user (no auth header) -> 401."""
        user = _make_fake_user()
        session = _make_mock_db_session(user=user)

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db
        # Deliberately NOT overriding get_current_user

        try:
            response = await client.post(
                "/api/onboarding/interview",
                json={"answers": VALID_ANSWERS},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401
