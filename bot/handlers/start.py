"""/start command handler for НутриМайнд bot.

Handles plain /start as well as deep-link payloads such as:
  /start invite_ABC123
"""

from __future__ import annotations

import os
import re

import httpx
import structlog
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ContextTypes

log = structlog.get_logger()

# Regex for invite deep-link codes: /start invite_<CODE>
_INVITE_RE = re.compile(r"^invite_([A-Za-z0-9_-]{4,32})$")

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
MINI_APP_URL = os.getenv("TELEGRAM_MINI_APP_URL", "https://app.nutrimind.ru")


async def _register_invite(telegram_id: int, invite_code: str) -> None:
    """Notify the backend that *telegram_id* arrived via *invite_code*."""
    url = f"{API_BASE_URL}/api/v1/invites/accept"
    payload = {"telegram_id": telegram_id, "invite_code": invite_code}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            log.info("invite_registered", telegram_id=telegram_id, code=invite_code)
    except httpx.HTTPError as exc:
        # Non-critical — the user can still use the app without the invite
        log.warning(
            "invite_registration_failed",
            telegram_id=telegram_id,
            code=invite_code,
            error=str(exc),
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start [deep_link_payload]."""
    if update.effective_chat is None or update.effective_user is None:
        return

    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # --- deep-link handling ------------------------------------------------
    deep_link_payload: str | None = None
    if context.args:
        deep_link_payload = context.args[0]

    if deep_link_payload:
        match = _INVITE_RE.match(deep_link_payload)
        if match:
            invite_code = match.group(1)
            log.info("deep_link_invite", chat_id=chat_id, code=invite_code)
            # Fire-and-forget: register invite in background
            await _register_invite(telegram_id, invite_code)

    # --- welcome message ---------------------------------------------------
    welcome_text = (
        "Привет! Я — <b>НутриМайнд</b>, твой AI-помощник для осознанного "
        "управления весом.\n\n"
        "Я помогу тебе:\n"
        "- Вести дневник питания простым текстом\n"
        "- Находить паттерны пищевого поведения\n"
        "- Получать персональные инсайты на основе КПТ\n"
        "- Предсказывать риски срывов заранее\n\n"
        "Нажми кнопку ниже, чтобы начать \u2193"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Открыть НутриМайнд",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        ]
    )

    await update.effective_chat.send_message(
        text=welcome_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    log.info("start_handled", chat_id=chat_id, deep_link=deep_link_payload)
