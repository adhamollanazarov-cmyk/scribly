"""Claude adapter for lesson generation: one streamed structured-output request.

I/O lives here; generate.py only sees the `LessonLLM` protocol, so tests use a fake.
"""

from collections.abc import AsyncIterator
from typing import Any, Protocol

import anthropic

from app.lesson.pricing import Usage
from app.lesson.prompt import system_prompt
from app.settings import Settings


class LLMError(Exception):
    """The model call failed. `str()` is safe to log and to show."""


class LLMRefused(LLMError):
    pass


class LLMTruncated(LLMError):
    pass


class LessonLLM(Protocol):
    def stream(self, user: str, schema: dict[str, Any], usage: Usage) -> AsyncIterator[str]:
        """Stream the JSON text of one response that follows `schema`; add its usage."""
        ...


class ClaudeLessonLLM:
    def __init__(self, settings: Settings, client: anthropic.AsyncAnthropic | None = None):
        self.settings = settings
        self._client = client

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        """Created on first use, so mock mode never needs a key."""
        if self._client is None:
            key = self.settings.anthropic_api_key
            self._client = anthropic.AsyncAnthropic(api_key=key.get_secret_value() if key else None)
        return self._client

    def thinking(self) -> Any:
        return {"type": self.settings.lesson_thinking}

    async def stream(self, user: str, schema: dict[str, Any], usage: Usage) -> AsyncIterator[str]:
        model = self.settings.lesson_model
        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=self.settings.lesson_max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt(),
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user}],
                thinking=self.thinking(),
                output_config={
                    "effort": self.settings.lesson_effort,
                    "format": {"type": "json_schema", "schema": schema},
                },
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
        except anthropic.APIStatusError as e:
            raise LLMError(f"the AI service returned {e.status_code} ({type(e).__name__})") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("the AI service could not be reached") from e
        usage.add(final.usage, model)
        if final.stop_reason == "refusal":
            raise LLMRefused("the AI declined to write this lesson")
        if final.stop_reason == "max_tokens":
            raise LLMTruncated("the lesson was too long and was cut off")
