"""Token usage and its cost in USD (for logs and the eval report)."""

from dataclasses import dataclass
from typing import Any

# USD per million tokens: input, output, cache read, cache write (5-minute TTL).
# Checked 2026-10-10 on platform.claude.com (Sonnet 5.5 cache reads are $0.10).
PRICES: dict[str, tuple[float, float, float, float]] = {
    "claude-sonnet-5-5": (2.00, 10.00, 0.10, 2.50),
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0
    unpriced_models: int = 0

    def add(self, usage: Any, model: str) -> None:
        """Add an Anthropic `Usage` object (or anything with the same attributes)."""
        counts = (
            int(getattr(usage, "input_tokens", 0) or 0),
            int(getattr(usage, "output_tokens", 0) or 0),
            int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        )
        self.input_tokens += counts[0]
        self.output_tokens += counts[1]
        self.cache_read_tokens += counts[2]
        self.cache_write_tokens += counts[3]
        self.calls += 1
        prices = PRICES.get(model)
        if prices is None:
            self.unpriced_models += 1
            return
        self.cost_usd += sum(n * p for n, p in zip(counts, prices, strict=True)) / 1e6

    def merge(self, other: "Usage") -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))
