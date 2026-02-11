"""AI pattern detector – identify behavioral eating patterns from food logs."""

import json
from typing import Any

import structlog

from app.ai.llm_client import llm_client
from app.ai.prompts import PATTERN_DETECT_SYSTEM, PATTERN_DETECT_USER_TEMPLATE

logger = structlog.get_logger()


class DetectedPattern:
    """Intermediate representation of a detected pattern before persistence."""

    def __init__(
        self,
        pattern_type: str,
        description_ru: str,
        confidence: float,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.pattern_type = pattern_type
        self.description_ru = description_ru
        self.confidence = confidence
        self.evidence = evidence or {}


async def detect_patterns(
    food_entries_summary: str,
    existing_patterns: list[str] | None = None,
) -> list[DetectedPattern]:
    """Analyze food log data to detect behavioral eating patterns.

    Parameters
    ----------
    food_entries_summary:
        A textual summary of the user's recent food entries including
        timestamps, moods, and calorie data.
    existing_patterns:
        List of already-known pattern types to avoid duplication.

    Returns
    -------
    list[DetectedPattern]
        Newly detected patterns not already present.

    TODO:
        - Implement statistical pre-filters (time clustering, calorie spikes)
        - Add pattern type taxonomy (emotional, timing, social, restriction)
        - Implement pattern confidence decay over time
        - Add support for pattern evolution tracking
    """
    existing = existing_patterns or []

    messages = [
        {"role": "system", "content": PATTERN_DETECT_SYSTEM},
        {
            "role": "user",
            "content": PATTERN_DETECT_USER_TEMPLATE.format(
                entries=food_entries_summary,
                existing_patterns=", ".join(existing) if existing else "none",
            ),
        },
    ]

    try:
        response_text = await llm_client.chat_completion_json(
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        data: dict[str, Any] = json.loads(response_text)
        patterns_raw: list[dict[str, Any]] = data.get("patterns", [])

        patterns = [
            DetectedPattern(
                pattern_type=p.get("type", "unknown"),
                description_ru=p.get("description_ru", ""),
                confidence=float(p.get("confidence", 0.0)),
                evidence=p.get("evidence"),
            )
            for p in patterns_raw
            if p.get("type") not in existing
        ]

        logger.info("patterns_detected", count=len(patterns))
        return patterns

    except Exception as exc:
        logger.error("pattern_detection_error", error=str(exc))
        return []
