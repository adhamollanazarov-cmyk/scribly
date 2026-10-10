"""Find complete steps in a lesson draft that is still streaming in.

The draft is one JSON object `{"title", "level", "steps": [...]}` whose keys arrive in
that order (structured outputs emit required keys in schema order). A step is complete
once the next one has started or the whole object has been parsed.
"""

from dataclasses import dataclass
from typing import Any

import jiter


@dataclass
class StepStream:
    buffer: str = ""
    header: dict[str, Any] | None = None
    emitted: int = 0

    def feed(self, chunk: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Add text. Returns (header if it just became complete, steps newly complete)."""
        self.buffer += chunk
        data = self._parse(partial=True)
        return self._take(data, finished=False)

    def finish(self) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[str, Any]]:
        """End of stream: everything left. Raises ValueError if the JSON is incomplete."""
        data = self._parse(partial=False)
        header, steps = self._take(data, finished=True)
        return header, steps, data

    def _parse(self, partial: bool) -> dict[str, Any]:
        try:
            data = jiter.from_json(
                self.buffer.encode(), partial_mode="trailing-strings" if partial else "off"
            )
        except ValueError:
            if partial:
                return {}
            raise
        if not isinstance(data, dict):
            raise ValueError("the lesson draft is not a JSON object")
        return data

    def _take(
        self, data: dict[str, Any], finished: bool
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        header = None
        if self.header is None and ("steps" in data or finished):
            self.header = {k: v for k, v in data.items() if k != "steps"}
            header = self.header
        steps = data.get("steps")
        if not isinstance(steps, list):
            return header, []
        complete = len(steps) if finished else len(steps) - 1
        new = steps[self.emitted : max(complete, self.emitted)]
        self.emitted += len(new)
        return header, new
