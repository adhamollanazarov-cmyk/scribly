"""Startup check: are the configured Claude models available to this API key?"""

import logging
from collections.abc import Iterable

import anthropic

from app.settings import Settings

logger = logging.getLogger(__name__)


def missing_models(configured: Iterable[str], available: Iterable[str]) -> list[str]:
    available_ids = set(available)
    return [model for model in configured if model not in available_ids]


async def list_model_ids(client: anthropic.AsyncAnthropic) -> list[str]:
    return [model.id async for model in client.models.list()]


async def check_models(
    settings: Settings, client: anthropic.AsyncAnthropic | None = None
) -> list[str]:
    """Log an error for each configured model the API does not list.

    Never raises: a failed check must not stop the server. Returns the missing ids.
    """
    if settings.mock_ai:
        return []
    if client is None:
        key = settings.anthropic_api_key
        if key is None or not key.get_secret_value():
            logger.error("ANTHROPIC_API_KEY is not set. Set it in .env or use MOCK_AI=1.")
            return []
        client = anthropic.AsyncAnthropic(api_key=key.get_secret_value())

    try:
        available = await list_model_ids(client)
    except anthropic.AuthenticationError:
        logger.error("Model check failed: ANTHROPIC_API_KEY was rejected (401).")
        return []
    except anthropic.APIStatusError as e:
        logger.error("Model check failed: Models API returned %s: %s", e.status_code, e.message)
        return []
    except anthropic.APIConnectionError:
        logger.error("Model check failed: could not reach the Anthropic API.")
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
