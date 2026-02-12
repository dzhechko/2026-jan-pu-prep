"""Telegram notification sender – sends messages via Bot API using httpx."""

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
) -> bool:
    """Send a message to a Telegram user via Bot API.

    Returns True on success, False on failure.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("notification_skipped_no_token")
        return False

    url = TELEGRAM_API_BASE.format(token=settings.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("telegram_message_sent", chat_id=chat_id)
                return True
            else:
                logger.warning(
                    "telegram_message_failed",
                    chat_id=chat_id,
                    status=response.status_code,
                    body=response.text[:200],
                )
                return False
    except httpx.HTTPError as exc:
        logger.error(
            "telegram_message_error",
            chat_id=chat_id,
            error=str(exc),
        )
        return False
