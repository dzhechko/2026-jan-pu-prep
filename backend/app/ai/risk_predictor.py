"""AI risk predictor – estimate likelihood of unhealthy eating episodes."""

import json
from typing import Any

import structlog

from app.ai.llm_client import llm_client
from app.ai.prompts import RISK_PREDICT_SYSTEM, RISK_PREDICT_USER_TEMPLATE
from app.schemas.pattern import RiskScore

logger = structlog.get_logger()


async def predict_risk(
    patterns_summary: str,
    recent_entries_summary: str,
    current_hour: int,
    day_of_week: int,
) -> RiskScore | None:
    """Predict the current risk level for a user.

    Parameters
    ----------
    patterns_summary:
        Description of active patterns.
    recent_entries_summary:
        Summary of today's and recent food entries.
    current_hour:
        Hour of day (0-23) in user's timezone.
    day_of_week:
        Day of week (0=Monday, 6=Sunday).

    Returns
    -------
    RiskScore or None
        Risk assessment, or None if insufficient data.

    TODO:
        - Integrate with user's historical risk_model from AI profile
        - Add time-series analysis for risk windows
        - Implement proactive notification triggers
        - Calibrate confidence thresholds
        - Add contextual factors (weather, holidays, etc.)
    """
    messages = [
        {"role": "system", "content": RISK_PREDICT_SYSTEM},
        {
            "role": "user",
            "content": RISK_PREDICT_USER_TEMPLATE.format(
                patterns=patterns_summary,
                entries=recent_entries_summary,
                hour=current_hour,
                day=day_of_week,
            ),
        },
    ]

    try:
        response_text = await llm_client.chat_completion_json(
            messages=messages,
            temperature=0.2,
            max_tokens=512,
        )
        data: dict[str, Any] = json.loads(response_text)

        level = data.get("level", "unknown")
        if level not in ("low", "medium", "high", "critical"):
            logger.warning("risk_unknown_level", level=level)
            return None

        risk = RiskScore(
            level=level,
            time_window=data.get("time_window"),
            recommendation=data.get("recommendation"),
        )

        logger.info("risk_predicted", level=risk.level, window=risk.time_window)
        return risk

    except Exception as exc:
        logger.error("risk_prediction_error", error=str(exc))
        return None
