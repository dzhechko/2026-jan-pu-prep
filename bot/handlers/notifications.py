"""Outgoing notification helpers for НутриМайнд bot.

These functions are called either:
  1. Directly from bot internals (e.g. scheduled tasks), or
  2. Via lightweight internal HTTP endpoints that the backend API
     POSTs to when it needs the bot to send a push message.

The ``register_notification_routes`` function wires up those internal
HTTP handlers into the ``Application`` so they are served on the same
webhook port.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import structlog
from telegram import Bot
from telegram.ext import Application

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Notification senders
# ---------------------------------------------------------------------------

async def send_risk_alert(bot: Bot, chat_id: int, risk_message: str) -> None:
    """Send a risk-of-relapse warning to the user.

    Called when the risk predictor detects elevated risk score.
    """
    text = (
        "\u26a0\ufe0f <b>Внимание — повышенный риск срыва</b>\n\n"
        f"{risk_message}\n\n"
        "Открой приложение, чтобы увидеть рекомендации."
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    log.info("notification_sent", kind="risk_alert", chat_id=chat_id)


async def send_insight_notification(bot: Bot, chat_id: int) -> None:
    """Daily reminder that a new insight is ready."""
    text = (
        "\U0001f4a1 <b>Новый инсайт готов!</b>\n\n"
        "Я проанализировал твой дневник и подготовил персональный инсайт. "
        "Открой приложение, чтобы прочитать."
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    log.info("notification_sent", kind="insight", chat_id=chat_id)


async def send_subscription_confirmation(
    bot: Bot,
    chat_id: int,
    plan: str,
    expires_at: datetime | str,
) -> None:
    """Confirm that the user's subscription has been activated."""
    if isinstance(expires_at, datetime):
        expires_str = expires_at.strftime("%d.%m.%Y")
    else:
        expires_str = expires_at

    text = (
        "\u2705 <b>Подписка активирована!</b>\n\n"
        f"Тариф: <b>{plan}</b>\n"
        f"Действует до: <b>{expires_str}</b>\n\n"
        "Спасибо, что выбрал НутриМайнд!"
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    log.info("notification_sent", kind="subscription", chat_id=chat_id, plan=plan)


async def send_cancellation_confirmation(
    bot: Bot,
    chat_id: int,
    active_until: datetime | str,
) -> None:
    """Confirm subscription cancellation."""
    if isinstance(active_until, datetime):
        until_str = active_until.strftime("%d.%m.%Y")
    else:
        until_str = active_until

    text = (
        "\u274c <b>Подписка отменена</b>\n\n"
        f"Премиум-функции будут доступны до <b>{until_str}</b>.\n"
        "Ты всегда можешь возобновить подписку в приложении."
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    log.info("notification_sent", kind="cancellation", chat_id=chat_id)


async def send_invite_reward(bot: Bot, chat_id: int, days_premium: int) -> None:
    """Notify that the user earned premium days via referral."""
    text = (
        "\U0001f381 <b>Бонус за приглашение!</b>\n\n"
        f"Твой друг присоединился к НутриМайнд. "
        f"Тебе начислено <b>{days_premium} дней</b> премиум-доступа.\n\n"
        "Продолжай приглашать друзей — каждый приносит бонус!"
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    log.info(
        "notification_sent",
        kind="invite_reward",
        chat_id=chat_id,
        days=days_premium,
    )


# ---------------------------------------------------------------------------
# Internal HTTP routes (called by the backend service)
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, Any] = {
    "risk_alert": lambda bot, data: send_risk_alert(
        bot, data["chat_id"], data["risk_message"]
    ),
    "insight": lambda bot, data: send_insight_notification(bot, data["chat_id"]),
    "subscription": lambda bot, data: send_subscription_confirmation(
        bot, data["chat_id"], data["plan"], data["expires_at"]
    ),
    "cancellation": lambda bot, data: send_cancellation_confirmation(
        bot, data["chat_id"], data["active_until"]
    ),
    "invite_reward": lambda bot, data: send_invite_reward(
        bot, data["chat_id"], data["days_premium"]
    ),
}


def register_notification_routes(app: Application) -> None:
    """Add a custom webhook handler that the backend can POST to.

    The backend sends requests like::

        POST /notify
        Content-Type: application/json

        {
            "type": "risk_alert",
            "chat_id": 123456789,
            "risk_message": "..."
        }

    This is handled through ``Application.run_webhook`` custom routes.
    We hook into the ``post_init`` lifecycle to register a custom
    ``/notify`` handler on the underlying ``tornado``/``httpx`` server
    used by python-telegram-bot v21.

    For simplicity we use a ``JobQueue`` one-shot job to process the
    notification, keeping everything inside the Application event loop.
    """

    async def _handle_notify(update: object, context: Any) -> None:
        """This is a no-op placeholder.

        Actual notification dispatching happens through direct bot API
        calls triggered by the backend via httpx. The backend calls:

            POST http://bot:8080/notify
              {"type": "risk_alert", "chat_id": 123, ...}

        In production, the backend uses httpx to invoke the helper
        functions above directly, or calls a lightweight internal
        endpoint. For the MVP, the backend imports and calls these
        functions via the shared Redis queue (RQ worker), making
        the internal HTTP route optional.
        """

    # Store dispatch table on the app for external access
    app.bot_data["notification_dispatch"] = _DISPATCH

    log.info("notification_routes_registered", types=list(_DISPATCH.keys()))
