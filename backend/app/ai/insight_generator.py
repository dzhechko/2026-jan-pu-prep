"""AI insight generator – produce personalized, actionable insights."""

import json
from typing import Any

import structlog

from app.ai.llm_client import llm_client
from app.ai.prompts import INSIGHT_GENERATE_SYSTEM, INSIGHT_GENERATE_USER_TEMPLATE

logger = structlog.get_logger()


class GeneratedInsight:
    """Intermediate representation of an insight before persistence."""

    def __init__(
        self,
        title: str,
        body: str,
        action: str | None = None,
        insight_type: str = "general",
    ) -> None:
        self.title = title
        self.body = body
        self.action = action
        self.insight_type = insight_type


async def generate_insight(
    patterns_summary: str,
    recent_entries_summary: str,
    user_context: str = "",
) -> GeneratedInsight | None:
    """Generate a single personalized insight based on patterns and data.

    Parameters
    ----------
    patterns_summary:
        Text description of the user's active patterns.
    recent_entries_summary:
        Summary of recent food entries.
    user_context:
        Additional context (language, cluster, preferences).

    Returns
    -------
    GeneratedInsight or None
        The generated insight, or None on failure.

    TODO:
        - Implement insight diversity tracking (avoid repetition)
        - Add CBT technique integration
        - Support different insight types (pattern, milestone, tip)
        - Localize fully for Russian audience
        - Add A/B testing support for insight variants
    """
    messages = [
        {"role": "system", "content": INSIGHT_GENERATE_SYSTEM},
        {
            "role": "user",
            "content": INSIGHT_GENERATE_USER_TEMPLATE.format(
                patterns=patterns_summary,
                entries=recent_entries_summary,
                context=user_context,
            ),
        },
    ]

    try:
        response_text = await llm_client.chat_completion_json(
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        data: dict[str, Any] = json.loads(response_text)

        insight = GeneratedInsight(
            title=data.get("title", ""),
            body=data.get("body", ""),
            action=data.get("action"),
            insight_type=data.get("type", "general"),
        )

        if not insight.title or not insight.body:
            logger.warning("insight_generation_empty", data=data)
            return None

        logger.info("insight_generated", type=insight.insight_type, title=insight.title[:50])
        return insight

    except Exception as exc:
        logger.error("insight_generation_error", error=str(exc))
        return None
