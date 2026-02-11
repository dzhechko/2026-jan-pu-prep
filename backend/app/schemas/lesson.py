"""CBT lesson schemas."""

from uuid import UUID

from pydantic import BaseModel


class LessonData(BaseModel):
    id: UUID
    title: str
    content_md: str
    duration_min: int

    model_config = {"from_attributes": True}


class ProgressData(BaseModel):
    current: int
    total: int


class LessonResponse(BaseModel):
    lesson: LessonData
    progress: ProgressData


class LessonListItem(BaseModel):
    id: UUID
    title: str
    lesson_order: int
    duration_min: int
    completed: bool

    model_config = {"from_attributes": True}


class LessonsListResponse(BaseModel):
    lessons: list[LessonListItem]
    progress: ProgressData
