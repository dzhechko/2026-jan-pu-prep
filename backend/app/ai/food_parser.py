"""AI food parser – convert Russian natural-language food text into structured items."""

import json
from typing import Any

import structlog

from app.ai.llm_client import llm_client
from app.ai.prompts import FOOD_PARSE_SYSTEM, FOOD_PARSE_USER_TEMPLATE
from app.schemas.food import FoodItem

logger = structlog.get_logger()


async def parse_food_text(raw_text: str) -> list[FoodItem]:
    """Parse a Russian-language food description into structured food items.

    Example input:  "Утром съела овсянку с бананом и кофе с молоком"
    Expected output: [
        FoodItem(name="Овсянка", calories=150, category="grain"),
        FoodItem(name="Банан", calories=105, category="fruit"),
        FoodItem(name="Кофе с молоком", calories=50, category="beverage"),
    ]

    TODO:
        - Fine-tune prompt for Russian food vocabulary
        - Add portion size estimation
        - Add confidence scores per item
        - Cache common food items for faster responses
        - Handle ambiguous descriptions gracefully
    """
    messages = [
        {"role": "system", "content": FOOD_PARSE_SYSTEM},
        {"role": "user", "content": FOOD_PARSE_USER_TEMPLATE.format(text=raw_text)},
    ]

    try:
        response_text = await llm_client.chat_completion_json(
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        data: dict[str, Any] = json.loads(response_text)
        items_raw: list[dict[str, Any]] = data.get("items", [])

        items = [
            FoodItem(
                name=item.get("name", "Unknown"),
                calories=int(item.get("calories", 0)),
                category=item.get("category", "other"),
            )
            for item in items_raw
        ]

        logger.info(
            "food_parsed",
            raw_text=raw_text[:80],
            item_count=len(items),
            total_calories=sum(i.calories for i in items),
        )
        return items

    except Exception as exc:
        logger.error("food_parse_error", error=str(exc), raw_text=raw_text[:80])
        # Return empty list on failure – caller should handle gracefully
        return []
