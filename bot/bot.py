"""НутриМайнд Telegram Bot — entry point.

Supports two modes:
  - Polling (dev):   python bot.py --polling
  - Webhook (prod):  python bot.py          (default)

Environment variables:
  TELEGRAM_BOT_TOKEN       — BotFather token (required)
  TELEGRAM_MINI_APP_URL    — Mini App URL shown in /start (required)
  WEBHOOK_URL              — Public URL for webhook, e.g. https://app.nutrimind.ru/bot/webhook
  WEBHOOK_SECRET           — Random string to verify Telegram webhook requests
  WEBHOOK_PORT             — Port the built-in webhook server listens on (default 8080)
  API_BASE_URL             — Backend API base, e.g. http://api:8000 (default http://api:8000)
"""

from __future__ import annotations

import argparse
import os
import sys

import structlog
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

from handlers.start import start_command
from handlers.notifications import register_notification_routes

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
        if os.getenv("APP_ENV", "development") == "development"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_config()["wrapper_class"].level
        if hasattr(structlog.get_config().get("wrapper_class", object), "level")
        else 0
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        log.critical("missing_env_var", var=name)
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="НутриМайнд Telegram Bot")
    parser.add_argument(
        "--polling",
        action="store_true",
        help="Run in polling mode (development). Default is webhook mode.",
    )
    args = parser.parse_args()

    token = _require_env("TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token(token).build()

    # -- handlers ----------------------------------------------------------
    app.add_handler(CommandHandler("start", start_command))

    # Register the /notify internal HTTP routes (used by the backend API
    # to trigger push messages through the bot).
    register_notification_routes(app)

    # -- run ---------------------------------------------------------------
    if args.polling:
        log.info("bot_starting", mode="polling")
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    else:
        webhook_url = _require_env("WEBHOOK_URL")
        webhook_secret = os.getenv("WEBHOOK_SECRET", "")
        port = int(os.getenv("WEBHOOK_PORT", "8080"))

        log.info(
            "bot_starting",
            mode="webhook",
            port=port,
            webhook_url=webhook_url,
        )

        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="/bot/webhook",
            webhook_url=f"{webhook_url}/bot/webhook",
            secret_token=webhook_secret,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
