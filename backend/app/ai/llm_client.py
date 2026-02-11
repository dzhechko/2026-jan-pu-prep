"""OpenAI LLM client with retry logic and structured output."""

import asyncio
from typing import Any

import structlog
from openai import AsyncOpenAI, APIError, RateLimitError

from app.config import settings

logger = structlog.get_logger()

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0


class LLMClient:
    """Async wrapper around the OpenAI API with exponential backoff retries."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> str:
        """Send a chat completion request with automatic retries.

        Parameters
        ----------
        messages:
            OpenAI-style message list (role + content).
        temperature:
            Sampling temperature (0.0 - 2.0).
        max_tokens:
            Maximum response length.
        response_format:
            Optional response format (e.g., ``{"type": "json_object"}``).

        Returns
        -------
        str
            The assistant's response text.
        """
        delay = BASE_DELAY_SECONDS

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""

                logger.debug(
                    "llm_completion_success",
                    model=self._model,
                    attempt=attempt,
                    tokens_used=response.usage.total_tokens if response.usage else None,
                )
                return content

            except RateLimitError as exc:
                logger.warning(
                    "llm_rate_limited",
                    attempt=attempt,
                    delay=delay,
                    error=str(exc),
                )
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(delay)
                delay *= BACKOFF_MULTIPLIER

            except APIError as exc:
                logger.error(
                    "llm_api_error",
                    attempt=attempt,
                    status=exc.status_code,
                    error=str(exc),
                )
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(delay)
                delay *= BACKOFF_MULTIPLIER

    async def chat_completion_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Convenience method requesting JSON-formatted output."""
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )


# Module-level singleton
llm_client = LLMClient()
