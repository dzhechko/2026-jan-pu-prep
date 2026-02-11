"""Tests for the CBT lessons feature (US-4.1).

BDD scenarios covered:

Unit tests (11 tests):
1.  test_get_all_lessons_empty -- no lessons in DB -> empty list
2.  test_get_all_lessons_with_data -- returns lessons with completion status
3.  test_get_lesson_found -- returns lesson + progress
4.  test_get_lesson_not_found -- returns None
5.  test_complete_lesson_success -- marks as completed, returns True
6.  test_complete_lesson_already_done -- returns False
7.  test_get_recommended_with_patterns -- recommends lesson matching user's pattern
8.  test_get_recommended_no_patterns -- falls back to first uncompleted
9.  test_get_recommended_all_completed -- returns None
10. test_seed_lessons -- inserts 20 lessons when empty
11. test_seed_lessons_already_seeded -- does not duplicate

Endpoint tests (5 tests):
12. test_list_lessons_endpoint -- GET /api/lessons -> 200
13. test_get_lesson_endpoint -- GET /api/lessons/{id} -> 200
14. test_get_lesson_not_found_endpoint -- GET /api/lessons/{bad_id} -> 404
15. test_complete_lesson_endpoint -- POST /api/lessons/{id}/complete -> 200
16. test_recommended_endpoint -- GET /api/lessons/recommended -> 200
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from httpx import AsyncClient

from app.models.lesson import CBTLesson, UserLessonProgress
from app.models.pattern import Pattern


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_TELEGRAM_ID = 123456789


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lesson(
    lesson_order: int = 1,
    title: str = "Тестовый урок",
    content_md: str = "## Содержание урока\n\nТекст урока.",
    pattern_tags: list[str] | None = None,
    duration_min: int = 5,
    lesson_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock CBTLesson object."""
    lesson = MagicMock(spec=CBTLesson)
    lesson.id = lesson_id or uuid.uuid4()
    lesson.lesson_order = lesson_order
    lesson.title = title
    lesson.content_md = content_md
    lesson.pattern_tags = pattern_tags or ["time", "mood"]
    lesson.duration_min = duration_min
    return lesson


def _make_progress_record(
    user_id: uuid.UUID,
    lesson_id: uuid.UUID,
) -> MagicMock:
    """Create a mock UserLessonProgress object."""
    record = MagicMock(spec=UserLessonProgress)
    record.user_id = user_id
    record.lesson_id = lesson_id
    record.completed_at = datetime.now(timezone.utc)
    return record


def _make_pattern(
    pattern_type: str = "mood",
    user_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock Pattern object."""
    pattern = MagicMock(spec=Pattern)
    pattern.id = uuid.uuid4()
    pattern.user_id = user_id or FAKE_USER_ID
    pattern.type = pattern_type
    pattern.active = True
    return pattern


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
# Unit tests for lesson service
# ===========================================================================


class TestGetAllLessons:
    """Unit tests for get_all_lessons."""

    async def test_get_all_lessons_empty(self):
        """No lessons in DB -> empty list, progress 0/0."""
        from app.services.lesson_service import get_all_lessons

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # Fetch all lessons -> empty
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result_mock.scalars.return_value = scalars_mock
            else:
                # Fetch completed lesson IDs -> empty
                result_mock.all.return_value = []
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_all_lessons(session, FAKE_USER_ID)

        assert result.lessons == []
        assert result.progress.current == 0
        assert result.progress.total == 0

    async def test_get_all_lessons_with_data(self):
        """Returns lessons with completion status."""
        from app.services.lesson_service import get_all_lessons

        lesson1 = _make_lesson(lesson_order=1, title="Урок 1")
        lesson2 = _make_lesson(lesson_order=2, title="Урок 2")
        completed_id = lesson1.id

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # Fetch all lessons
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [lesson1, lesson2]
                result_mock.scalars.return_value = scalars_mock
            else:
                # Fetch completed lesson IDs
                result_mock.all.return_value = [(completed_id,)]
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_all_lessons(session, FAKE_USER_ID)

        assert len(result.lessons) == 2
        assert result.lessons[0].title == "Урок 1"
        assert result.lessons[0].completed is True
        assert result.lessons[1].title == "Урок 2"
        assert result.lessons[1].completed is False
        assert result.progress.current == 1
        assert result.progress.total == 2


class TestGetLesson:
    """Unit tests for get_lesson."""

    async def test_get_lesson_found(self):
        """Returns lesson + progress when found."""
        from app.services.lesson_service import get_lesson

        lesson = _make_lesson(lesson_order=3, title="Найденный урок")

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # get_lesson: select lesson by id
                result_mock.scalar_one_or_none.return_value = lesson
            elif call_count["n"] == 2:
                # get_progress: total count
                result_mock.scalar_one.return_value = 20
            else:
                # get_progress: completed count
                result_mock.scalar_one.return_value = 5
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_lesson(session, lesson.id, FAKE_USER_ID)

        assert result is not None
        assert result.lesson.title == "Найденный урок"
        assert result.progress.total == 20
        assert result.progress.current == 5

    async def test_get_lesson_not_found(self):
        """Returns None when lesson not found."""
        from app.services.lesson_service import get_lesson

        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        result = await get_lesson(session, uuid.uuid4(), FAKE_USER_ID)

        assert result is None


class TestCompleteLesson:
    """Unit tests for complete_lesson."""

    async def test_complete_lesson_success(self):
        """Marks as completed and returns True."""
        from app.services.lesson_service import complete_lesson

        lesson_id = uuid.uuid4()

        session = AsyncMock()

        # Check existing: not found
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await complete_lesson(session, lesson_id, FAKE_USER_ID)

        assert result is True
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_complete_lesson_already_done(self):
        """Returns False when already completed."""
        from app.services.lesson_service import complete_lesson

        lesson_id = uuid.uuid4()
        existing_progress = _make_progress_record(FAKE_USER_ID, lesson_id)

        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_progress
        session.execute = AsyncMock(return_value=result_mock)

        result = await complete_lesson(session, lesson_id, FAKE_USER_ID)

        assert result is False
        session.add.assert_not_called()


class TestGetRecommendedLesson:
    """Unit tests for get_recommended_lesson."""

    async def test_get_recommended_with_patterns(self):
        """Recommends lesson matching user's active pattern type."""
        from app.services.lesson_service import get_recommended_lesson

        # Lesson 1: tags ["time", "skip"] -- should NOT match mood
        lesson1 = _make_lesson(
            lesson_order=1, title="Урок 1", pattern_tags=["time", "skip"]
        )
        # Lesson 2: tags ["mood"] -- should match mood pattern
        lesson2 = _make_lesson(
            lesson_order=2, title="Урок 2", pattern_tags=["mood"]
        )

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # Load user's active pattern types
                result_mock.all.return_value = [("mood",)]
            elif call_count["n"] == 2:
                # Fetch all lessons
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [lesson1, lesson2]
                result_mock.scalars.return_value = scalars_mock
            elif call_count["n"] == 3:
                # Fetch completed lesson IDs -> none completed
                result_mock.all.return_value = []
            elif call_count["n"] == 4:
                # get_progress: total count
                result_mock.scalar_one.return_value = 2
            else:
                # get_progress: completed count
                result_mock.scalar_one.return_value = 0
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_recommended_lesson(session, FAKE_USER_ID)

        assert result is not None
        assert result.lesson.title == "Урок 2"

    async def test_get_recommended_no_patterns(self):
        """Falls back to first uncompleted lesson when no patterns match."""
        from app.services.lesson_service import get_recommended_lesson

        lesson1 = _make_lesson(lesson_order=1, title="Первый урок")
        lesson2 = _make_lesson(lesson_order=2, title="Второй урок")

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # Load user's active pattern types -> empty
                result_mock.all.return_value = []
            elif call_count["n"] == 2:
                # Fetch all lessons
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [lesson1, lesson2]
                result_mock.scalars.return_value = scalars_mock
            elif call_count["n"] == 3:
                # Fetch completed lesson IDs -> none
                result_mock.all.return_value = []
            elif call_count["n"] == 4:
                # get_progress: total count
                result_mock.scalar_one.return_value = 2
            else:
                # get_progress: completed count
                result_mock.scalar_one.return_value = 0
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_recommended_lesson(session, FAKE_USER_ID)

        assert result is not None
        # Falls back to first uncompleted lesson
        assert result.lesson.title == "Первый урок"

    async def test_get_recommended_all_completed(self):
        """Returns None when all lessons are completed."""
        from app.services.lesson_service import get_recommended_lesson

        lesson1 = _make_lesson(lesson_order=1, title="Урок 1")

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # Load user's active pattern types -> empty
                result_mock.all.return_value = []
            elif call_count["n"] == 2:
                # Fetch all lessons
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [lesson1]
                result_mock.scalars.return_value = scalars_mock
            else:
                # Fetch completed lesson IDs -> all completed
                result_mock.all.return_value = [(lesson1.id,)]
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)

        result = await get_recommended_lesson(session, FAKE_USER_ID)

        assert result is None


class TestSeedLessons:
    """Unit tests for seed_lessons."""

    async def test_seed_lessons(self):
        """Inserts 20 lessons when table is empty."""
        from app.services.lesson_service import seed_lessons

        session = AsyncMock()

        # Count query -> 0 (empty table)
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 0
        session.execute = AsyncMock(return_value=result_mock)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seed_lessons(session)

        # Should have called db.add 20 times
        assert session.add.call_count == 20
        session.flush.assert_awaited_once()

        # Verify all added objects are CBTLesson instances
        for c in session.add.call_args_list:
            added_obj = c[0][0]
            assert isinstance(added_obj, CBTLesson)

    async def test_seed_lessons_already_seeded(self):
        """Does not duplicate when lessons already exist."""
        from app.services.lesson_service import seed_lessons

        session = AsyncMock()

        # Count query -> 20 (already seeded)
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 20
        session.execute = AsyncMock(return_value=result_mock)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seed_lessons(session)

        # Should NOT have called db.add
        session.add.assert_not_called()
        session.flush.assert_not_awaited()


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestListLessonsEndpoint:
    """Endpoint tests for GET /api/lessons."""

    async def test_list_lessons_endpoint(self, app, client: AsyncClient):
        """GET /api/lessons -> 200 with lessons list."""
        lesson1 = _make_lesson(lesson_order=1, title="Урок 1")
        lesson2 = _make_lesson(lesson_order=2, title="Урок 2")

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # Fetch all lessons
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [lesson1, lesson2]
                result_mock.scalars.return_value = scalars_mock
            else:
                # Fetch completed lesson IDs -> none
                result_mock.all.return_value = []
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/lessons")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert len(body["lessons"]) == 2
        assert body["lessons"][0]["title"] == "Урок 1"
        assert body["lessons"][1]["title"] == "Урок 2"
        assert body["progress"]["current"] == 0
        assert body["progress"]["total"] == 2


class TestGetLessonEndpoint:
    """Endpoint tests for GET /api/lessons/{lesson_id}."""

    async def test_get_lesson_endpoint(self, app, client: AsyncClient):
        """GET /api/lessons/{id} -> 200 with lesson detail."""
        lesson = _make_lesson(lesson_order=1, title="Детали урока")

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # get_lesson: select lesson by id
                result_mock.scalar_one_or_none.return_value = lesson
            elif call_count["n"] == 2:
                # get_progress: total count
                result_mock.scalar_one.return_value = 20
            else:
                # get_progress: completed count
                result_mock.scalar_one.return_value = 3
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        _override_dependencies(app, session)

        try:
            response = await client.get(f"/api/lessons/{lesson.id}")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["lesson"]["title"] == "Детали урока"
        assert body["progress"]["total"] == 20
        assert body["progress"]["current"] == 3

    async def test_get_lesson_not_found_endpoint(self, app, client: AsyncClient):
        """GET /api/lessons/{bad_id} -> 404."""
        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)
        _override_dependencies(app, session)

        try:
            response = await client.get(f"/api/lessons/{uuid.uuid4()}")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404


class TestCompleteLessonEndpoint:
    """Endpoint tests for POST /api/lessons/{lesson_id}/complete."""

    async def test_complete_lesson_endpoint(self, app, client: AsyncClient):
        """POST /api/lessons/{id}/complete -> 200."""
        lesson_id = uuid.uuid4()

        session = AsyncMock()

        # Check existing: not found -> newly completed
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)
        session.add = MagicMock()
        session.flush = AsyncMock()
        _override_dependencies(app, session)

        try:
            response = await client.post(f"/api/lessons/{lesson_id}/complete")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["lesson_id"] == str(lesson_id)
        assert body["newly_completed"] is True


class TestRecommendedEndpoint:
    """Endpoint tests for GET /api/lessons/recommended."""

    async def test_recommended_endpoint(self, app, client: AsyncClient):
        """GET /api/lessons/recommended -> 200 with recommended lesson."""
        lesson = _make_lesson(
            lesson_order=1, title="Рекомендованный урок", pattern_tags=["mood"]
        )

        session = AsyncMock()

        call_count = {"n": 0}

        def _execute_side_effect(stmt):
            call_count["n"] += 1
            result_mock = MagicMock()
            if call_count["n"] == 1:
                # Load user's active pattern types
                result_mock.all.return_value = [("mood",)]
            elif call_count["n"] == 2:
                # Fetch all lessons
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [lesson]
                result_mock.scalars.return_value = scalars_mock
            elif call_count["n"] == 3:
                # Fetch completed lesson IDs -> none
                result_mock.all.return_value = []
            elif call_count["n"] == 4:
                # get_progress: total count
                result_mock.scalar_one.return_value = 1
            else:
                # get_progress: completed count
                result_mock.scalar_one.return_value = 0
            return result_mock

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        _override_dependencies(app, session)

        try:
            response = await client.get("/api/lessons/recommended")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["lesson"]["title"] == "Рекомендованный урок"
        assert body["progress"]["total"] == 1
        assert body["progress"]["current"] == 0
