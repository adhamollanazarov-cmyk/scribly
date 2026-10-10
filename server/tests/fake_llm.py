"""A stand-in for Claude: replays canned JSON replies in small chunks."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from app.lesson.pricing import Usage


@dataclass
class FakeLLM:
    replies: list[str | Exception]
    chunk: int = 37
    model: str = "claude-sonnet-5-5"
    requests: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def stream(self, user: str, schema: dict[str, Any], usage: Usage) -> AsyncIterator[str]:
        self.requests.append((user, schema))
        if not self.replies:
            raise AssertionError("FakeLLM: no reply left for this request")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        for start in range(0, len(reply), self.chunk):
            yield reply[start : start + self.chunk]
        usage.add(
            SimpleNamespace(
                input_tokens=100,
                output_tokens=len(reply) // 4,
                cache_read_input_tokens=5000,
                cache_creation_input_tokens=0,
            ),
            self.model,
        )
