"""Onboarding schemas – interview request/response models."""

from pydantic import BaseModel, field_validator


VALID_QUESTIONS = {
    "eating_schedule": {"regular", "irregular", "frequent", "restrictive"},
    "biggest_challenge": {
        "overeating",
        "emotional_eating",
        "lack_of_structure",
        "unhealthy_choices",
        "portion_control",
    },
}


class InterviewAnswer(BaseModel):
    question_id: str
    answer_id: str


class InterviewRequest(BaseModel):
    answers: list[InterviewAnswer]

    @field_validator("answers")
    @classmethod
    def exactly_two_answers(cls, v: list[InterviewAnswer]) -> list[InterviewAnswer]:
        if len(v) != 2:
            raise ValueError("Exactly 2 answers are required")
        return v

    @field_validator("answers")
    @classmethod
    def valid_question_and_answer_ids(
        cls, v: list[InterviewAnswer]
    ) -> list[InterviewAnswer]:
        for answer in v:
            if answer.question_id not in VALID_QUESTIONS:
                raise ValueError(
                    f"Invalid question_id: {answer.question_id}. "
                    f"Valid question_ids: {sorted(VALID_QUESTIONS.keys())}"
                )
            valid_answers = VALID_QUESTIONS[answer.question_id]
            if answer.answer_id not in valid_answers:
                raise ValueError(
                    f"Invalid answer_id '{answer.answer_id}' for question "
                    f"'{answer.question_id}'. Valid answers: {sorted(valid_answers)}"
                )
        return v


class InterviewResponse(BaseModel):
    profile_initialized: bool
    cluster_id: str
