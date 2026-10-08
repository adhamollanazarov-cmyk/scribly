"""Startup check: are the configured Claude models available to this API key?"""

import asyncio
import logging
from collections.abc import Iterable
from contextlib import AsyncExitStack

import anthropic

from app.settings import Settings

logger = logging.getLogger(__name__)
MODEL_CHECK_TIMEOUT_SECONDS = 10.0


def missing_models(configured: Iterable[str], available: Iterable[str]) -> list[str]:
    available_ids = set(available)
    return [model for model in configured if model not in available_ids]


async def list_model_ids(client: anthropic.AsyncAnthropic) -> list[str]:
    return [model.id async for model in client.models.list()]


async def check_models(
    settings: Settings, client: anthropic.AsyncAnthropic | None = None
) -> list[str]:
    """Log an error for each configured model the API does not list.

    Provider errors and timeouts do not stop startup. Returns the missing ids.
    Injected clients remain caller-owned; internally created clients are closed.
    """
    if settings.mock_ai:
        return []
    try:
        # One deadline covers all pages, rather than resetting per HTTP request.
        async with asyncio.timeout(MODEL_CHECK_TIMEOUT_SECONDS), AsyncExitStack() as stack:
            if client is None:
                key = settings.anthropic_api_key
                if key is None or not key.get_secret_value():
                    logger.error("ANTHROPIC_API_KEY is not set. Set it in .env or use MOCK_AI=1.")
                    return []
                client = await stack.enter_async_context(
                    anthropic.AsyncAnthropic(
                        api_key=key.get_secret_value(),
                        timeout=MODEL_CHECK_TIMEOUT_SECONDS,
                        max_retries=0,
                    )
                )
            available = await list_model_ids(client)
    except anthropic.APIError as error:
        # Exception class names are SDK-controlled; messages and bodies are not.
        logger.error(
            "Model check failed: status=%s error_type=%s",
            getattr(error, "status_code", "unavailable"),
            type(error).__name__,
        )
        return []
    except TimeoutError:
        logger.error("Model check failed: status=unavailable error_type=TimeoutError")
        return []

    configured = {"LESSON_MODEL": settings.lesson_model, "FAST_MODEL": settings.fast_model}
    missing = missing_models(configured.values(), available)
    for name, model in configured.items():
        if model in missing:
            logger.error(
                "%s=%s is not in the Models API list for this key. Available: %s",
                name,
                model,
                ", ".join(sorted(available)),
            )
    return missing
