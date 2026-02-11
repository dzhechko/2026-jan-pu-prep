"""Onboarding service – cluster assignment logic."""

from app.schemas.onboarding import InterviewAnswer


def assign_cluster(answers: list[InterviewAnswer]) -> str:
    """Determine user cluster based on interview answers.

    Cluster assignment logic (simple mapping):
    - emotional_eating -> "emotional_eater"
    - overeating + irregular/restrictive -> "chaotic_eater"
    - lack_of_structure -> "unstructured_eater"
    - unhealthy_choices -> "mindless_eater"
    - default -> "general"
    """
    answers_map: dict[str, str] = {a.question_id: a.answer_id for a in answers}

    challenge = answers_map.get("biggest_challenge")
    eating_schedule = answers_map.get("eating_schedule")

    if challenge == "emotional_eating":
        return "emotional_eater"

    if challenge == "overeating" and eating_schedule in ("irregular", "restrictive"):
        return "chaotic_eater"

    if challenge == "lack_of_structure":
        return "unstructured_eater"

    if challenge == "unhealthy_choices":
        return "mindless_eater"

    return "general"
