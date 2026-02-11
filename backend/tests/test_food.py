"""Tests for the food logging feature.

BDD scenarios covered:
1. Log simple food ("борщ") -> 201, parsed_items has 1 item with correct calories
2. Log compound food ("борщ с хлебом") -> 201, 2 items parsed
3. Log with mood and context -> saved correctly
4. Log with invalid mood -> 422
5. Log with empty text -> 422
6. Get history -> returns entries in reverse chronological order
7. Get history with pagination (limit/offset) -> correct subset
8. Get history empty -> returns [] with total=0
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.models.food_entry import FoodEntry
from app.schemas.food import FoodItem


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_db_session(food_entries: list[FoodEntry] | None = None):
    """Return an AsyncMock session that simulates DB operations for food logging.

    The session tracks added food entries and can return pre-loaded entries
    for history queries.
    """
    session = AsyncMock()
    added_entries: list[FoodEntry] = []
    stored_entries = list(food_entries) if food_entries else []

    def _add_side_effect(obj):
        """Simulate session.add -- store the entry and assign an id."""
        if isinstance(obj, FoodEntry):
            if obj.id is None:
                obj.id = uuid.uuid4()
            added_entries.append(obj)
            stored_entries.append(obj)

    session.add = MagicMock(side_effect=_add_side_effect)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    def _execute_side_effect(stmt):
        """Simulate SELECT queries for food_entries."""
        result_mock = MagicMock()
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        if "count" in compiled.lower():
            # Count query – return total number of entries for the user
            user_entries = [
                e for e in stored_entries
                if str(e.user_id) == str(FAKE_USER_ID)
            ]
            result_mock.scalar_one.return_value = len(user_entries)
        elif "food_entries" in compiled:
            # Select query – return entries in reverse chronological order
            user_entries = [
                e for e in stored_entries
                if str(e.user_id) == str(FAKE_USER_ID)
            ]
            user_entries.sort(key=lambda e: e.logged_at, reverse=True)

            # Extract limit and offset from compiled statement
            limit = None
            offset = 0
            compiled_lower = compiled.lower()
            if "limit" in compiled_lower:
                import re
                limit_match = re.search(r"limit\s+(\d+)", compiled_lower)
                if limit_match:
                    limit = int(limit_match.group(1))
            if "offset" in compiled_lower:
                import re
                offset_match = re.search(r"offset\s+(\d+)", compiled_lower)
                if offset_match:
                    offset = int(offset_match.group(1))

            sliced = user_entries[offset:]
            if limit is not None:
                sliced = sliced[:limit]

            scalars_mock = MagicMock()
            scalars_mock.all.return_value = sliced
            result_mock.scalars.return_value = scalars_mock
        else:
            result_mock.scalar_one.return_value = 0
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            result_mock.scalars.return_value = scalars_mock

        return result_mock

    session.execute = AsyncMock(side_effect=_execute_side_effect)

    # Make it usable as an async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    return session, added_entries


def _override_dependencies(app, session, user_id=FAKE_USER_ID):
    """Override get_db and get_current_user dependencies on the app."""
    from app.dependencies import get_db, get_current_user

    async def _override_get_db():
        yield session

    async def _override_get_current_user():
        return {"user_id": user_id, "telegram_id": FAKE_TELEGRAM_ID}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user


def _make_food_entry(
    raw_text: str,
    parsed_items: list[dict],
    total_calories: int,
    logged_at: datetime,
    mood: str | None = None,
    context: str | None = None,
    user_id: uuid.UUID = FAKE_USER_ID,
) -> FoodEntry:
    """Create a FoodEntry object for testing (simulating a DB row)."""
    entry = FoodEntry(
        id=uuid.uuid4(),
        user_id=user_id,
        raw_text=raw_text,
        parsed_items=parsed_items,
        total_calories=total_calories,
        mood=mood,
        context=context,
        logged_at=logged_at,
        day_of_week=logged_at.weekday(),
        hour=logged_at.hour,
    )
    return entry


# ===========================================================================
# Unit tests for parse_food_text
# ===========================================================================


class TestParseFoodText:
    """Unit tests for the food text parsing logic."""

    async def test_single_known_food(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("борщ")
        assert len(items) == 1
        assert items[0].name == "борщ"
        assert items[0].calories == 150
        assert items[0].category == "green"

    async def test_compound_food_with_с(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("борщ с хлебом")
        assert len(items) == 2
        names = [item.name.lower() for item in items]
        assert "борщ" in names
        # "хлебом" is not in the DB, so it falls back (AI or unknown)
        # but "хлеб" is. Let's test with exact match
        # The split produces "борщ" and "хлебом" — "хлебом" is not in DB

    async def test_compound_food_with_и(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("чай и яблоко")
        assert len(items) == 2
        names = [item.name.lower() for item in items]
        assert "чай" in names
        assert "яблоко" in names

    async def test_compound_food_with_comma(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("суп, хлеб, чай")
        assert len(items) == 3
        names = [item.name.lower() for item in items]
        assert "суп" in names
        assert "хлеб" in names
        assert "чай" in names

    async def test_compound_food_with_plus(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("кофе+молоко")
        assert len(items) == 2
        names = [item.name.lower() for item in items]
        assert "кофе" in names
        assert "молоко" in names

    async def test_unknown_food_falls_back(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("фуагра")
        assert len(items) == 1
        assert items[0].name == "фуагра"
        assert items[0].calories == 0
        assert items[0].category == "yellow"

    async def test_case_insensitive_lookup(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("Борщ")
        assert len(items) == 1
        assert items[0].calories == 150

    async def test_empty_after_strip_returns_empty(self):
        from app.services.food_service import parse_food_text

        items = await parse_food_text("   ")
        assert len(items) == 0


# ===========================================================================
# Integration tests via HTTP (router level)
# ===========================================================================


class TestLogFoodEndpoint:
    """Integration tests against POST /api/food/log."""

    async def test_log_simple_food_returns_201(self, app, client: AsyncClient):
        """Log a single known food -> 201, correct parsed item."""
        session, added = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": "борщ"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        body = response.json()
        assert len(body["parsed_items"]) == 1
        assert body["parsed_items"][0]["name"] == "борщ"
        assert body["parsed_items"][0]["calories"] == 150
        assert body["parsed_items"][0]["category"] == "green"
        assert body["total_calories"] == 150
        assert "entry_id" in body

    async def test_log_compound_food_returns_201_with_multiple_items(
        self, app, client: AsyncClient
    ):
        """Log compound food ("чай и яблоко") -> 201, 2 items parsed."""
        session, added = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": "чай и яблоко"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        body = response.json()
        assert len(body["parsed_items"]) == 2
        names = [item["name"].lower() for item in body["parsed_items"]]
        assert "чай" in names
        assert "яблоко" in names
        assert body["total_calories"] == 5 + 52  # чай=5, яблоко=52

    async def test_log_with_mood_and_context(self, app, client: AsyncClient):
        """Log with optional mood and context -> saved correctly."""
        session, added = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={
                    "raw_text": "салат",
                    "mood": "great",
                    "context": "home",
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        body = response.json()
        assert len(body["parsed_items"]) == 1
        assert body["parsed_items"][0]["name"] == "салат"

        # Verify that mood and context were passed to the DB entry
        assert len(added) == 1
        assert added[0].mood == "great"
        assert added[0].context == "home"

    async def test_log_with_invalid_mood_returns_422(
        self, app, client: AsyncClient
    ):
        """Invalid mood value -> 422 validation error."""
        session, _ = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": "борщ", "mood": "fantastic"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    async def test_log_with_invalid_context_returns_422(
        self, app, client: AsyncClient
    ):
        """Invalid context value -> 422 validation error."""
        session, _ = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": "борщ", "context": "beach"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    async def test_log_with_empty_text_returns_422(
        self, app, client: AsyncClient
    ):
        """Empty raw_text -> 422 validation error."""
        session, _ = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": ""},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    async def test_log_with_too_long_text_returns_422(
        self, app, client: AsyncClient
    ):
        """raw_text exceeding 500 chars -> 422 validation error."""
        session, _ = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": "а" * 501},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    async def test_log_without_auth_returns_401(
        self, app, client: AsyncClient
    ):
        """Request without auth -> 401."""
        session, _ = _make_mock_db_session()

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db
        # Deliberately NOT overriding get_current_user

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": "борщ"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401

    async def test_log_persists_entry_to_db(self, app, client: AsyncClient):
        """Verify that the food entry is actually added to the DB session."""
        session, added = _make_mock_db_session()
        _override_dependencies(app, session)

        try:
            response = await client.post(
                "/api/food/log",
                json={"raw_text": "гречка"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        assert len(added) == 1
        assert added[0].raw_text == "гречка"
        assert added[0].total_calories == 180
        assert added[0].user_id == FAKE_USER_ID
        session.flush.assert_awaited_once()


class TestGetFoodHistoryEndpoint:
    """Integration tests against GET /api/food/history."""

    async def test_get_history_empty_returns_empty_list(
        self, app, client: AsyncClient
    ):
        """No entries -> returns [] with total=0."""
        session, _ = _make_mock_db_session(food_entries=[])
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/food/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["entries"] == []
        assert body["total"] == 0

    async def test_get_history_returns_entries_reverse_chronological(
        self, app, client: AsyncClient
    ):
        """Entries are returned in reverse chronological order."""
        now = datetime.now(timezone.utc)
        entries = [
            _make_food_entry(
                raw_text="завтрак",
                parsed_items=[{"name": "каша", "calories": 200, "category": "yellow"}],
                total_calories=200,
                logged_at=now - timedelta(hours=3),
            ),
            _make_food_entry(
                raw_text="обед",
                parsed_items=[{"name": "суп", "calories": 100, "category": "green"}],
                total_calories=100,
                logged_at=now - timedelta(hours=1),
            ),
            _make_food_entry(
                raw_text="ужин",
                parsed_items=[{"name": "курица", "calories": 250, "category": "yellow"}],
                total_calories=250,
                logged_at=now,
            ),
        ]

        session, _ = _make_mock_db_session(food_entries=entries)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/food/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert len(body["entries"]) == 3
        # Verify reverse chronological order
        assert body["entries"][0]["raw_text"] == "ужин"
        assert body["entries"][1]["raw_text"] == "обед"
        assert body["entries"][2]["raw_text"] == "завтрак"

    async def test_get_history_with_pagination(
        self, app, client: AsyncClient
    ):
        """Pagination with limit and offset -> correct subset."""
        now = datetime.now(timezone.utc)
        entries = [
            _make_food_entry(
                raw_text=f"еда {i}",
                parsed_items=[{"name": f"блюдо {i}", "calories": 100, "category": "yellow"}],
                total_calories=100,
                logged_at=now - timedelta(hours=5 - i),
            )
            for i in range(5)
        ]

        session, _ = _make_mock_db_session(food_entries=entries)
        _override_dependencies(app, session)

        try:
            # Request page 2: offset=2, limit=2
            response = await client.get(
                "/api/food/history",
                params={"limit": 2, "offset": 2},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        assert len(body["entries"]) == 2
        # After sorting desc and skipping 2, we should get entries at index 2 and 3
        # (0=newest, 1, 2, 3, 4=oldest)
        assert body["entries"][0]["raw_text"] == "еда 2"
        assert body["entries"][1]["raw_text"] == "еда 1"

    async def test_get_history_without_auth_returns_401(
        self, app, client: AsyncClient
    ):
        """Request without auth -> 401."""
        session, _ = _make_mock_db_session()

        from app.dependencies import get_db

        async def _override_get_db():
            yield session

        app.dependency_overrides[get_db] = _override_get_db
        # Deliberately NOT overriding get_current_user

        try:
            response = await client.get("/api/food/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401

    async def test_get_history_entries_have_correct_structure(
        self, app, client: AsyncClient
    ):
        """Each history entry has the expected fields."""
        now = datetime.now(timezone.utc)
        entries = [
            _make_food_entry(
                raw_text="борщ с хлебом",
                parsed_items=[
                    {"name": "борщ", "calories": 150, "category": "green"},
                    {"name": "хлеб", "calories": 80, "category": "yellow"},
                ],
                total_calories=230,
                mood="ok",
                context="home",
                logged_at=now,
            ),
        ]

        session, _ = _make_mock_db_session(food_entries=entries)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/food/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        entry = body["entries"][0]
        assert entry["raw_text"] == "борщ с хлебом"
        assert entry["total_calories"] == 230
        assert entry["mood"] == "ok"
        assert entry["context"] == "home"
        assert len(entry["parsed_items"]) == 2
        assert entry["parsed_items"][0]["name"] == "борщ"
        assert entry["parsed_items"][1]["name"] == "хлеб"
        assert "id" in entry
        assert "logged_at" in entry
