"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings.

    All values are loaded from environment variables (or a .env file
    when running locally).  Pydantic-settings validates types and
    provides sensible defaults for development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = "change-me-in-production"

    # ── Telegram ─────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_MINI_APP_URL: str = ""

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutrimind"

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── OpenAI ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── Scheduler ─────────────────────────────────────────
    SCHEDULER_ENABLED: bool = True

    # ── JWT ──────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    @property
    def database_url_sync(self) -> str:
        """Return a synchronous version of the database URL (for Alembic)."""
        return self.DATABASE_URL.replace("+asyncpg", "")


settings = Settings()
