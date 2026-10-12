"""Sign conventions. A calc says what a positive result means (`+x`, `A->B`, `down the
slope`); the sign of its value then gives the physical direction. One small vocabulary,
shared by the step lint and the eval grader. Pure functions.
"""

import re

AXIS = re.compile(r"^(?:([+-])\s*|(positive|negative)\s+)?([xyz])(?:\s*(?:axis|direction))?$")
PATH = re.compile(
    r"^(?:from\s+)?([a-z][a-z0-9_]{0,5})(?:\s*(?:->|→)\s*|\s+to\s+)([a-z][a-z0-9_]{0,5})$"
)
TOWARD = re.compile(r"^(toward|towards|away from)\s+([a-z0-9_ ]{1,20})$")
ALIASES = {
    "up": "+y",
    "upward": "+y",
    "upwards": "+y",
    "down": "-y",
    "downward": "-y",
    "downwards": "-y",
    "right": "+x",
    "to the right": "+x",
    "left": "-x",
    "to the left": "-x",
    "clockwise": "cw",
    "counterclockwise": "ccw",
    "counter-clockwise": "ccw",
    "anticlockwise": "ccw",
    "anti-clockwise": "ccw",
    "up the incline": "up the slope",
    "down the incline": "down the slope",
    "into page": "into the page",
    "out of page": "out of the page",
}
PAIRS = (("cw", "ccw"), ("up the slope", "down the slope"), ("into the page", "out of the page"))
OPPOSITE = {a: b for a, b in PAIRS} | {b: a for a, b in PAIRS}
VOCABULARY = (
    "+x, -x, +y (up), -y, +z, -z, A->B (two point or node names), cw, ccw, "
    "down the slope, up the slope, toward P, away from P, into the page, out of the page"
)


def normalize(text: str) -> str | None:
    """The canonical form of a direction, "" for none, None if it cannot be read."""
    text = " ".join(text.strip().lower().replace("−", "-").split())
    if not text:
        return ""
    text = ALIASES.get(text, text)
    if m := AXIS.match(text):
        sign = "-" if m.group(1) == "-" or m.group(2) == "negative" else "+"
        return sign + m.group(3)
    if m := TOWARD.match(text):
        return f"{'toward' if m.group(1) != 'away from' else 'away from'} {m.group(2)}"
    if m := PATH.match(text):
        return f"{m.group(1)}->{m.group(2)}" if m.group(1) != m.group(2) else None
    return text if text in OPPOSITE else None


def opposite(direction: str) -> str:
    """The opposite of a canonical, non-empty direction."""
    if direction[0] in "+-" and len(direction) == 2:
        return ("-" if direction[0] == "+" else "+") + direction[1]
    if "->" in direction:
        start, end = direction.split("->")
        return f"{end}->{start}"
    if direction.startswith("toward "):
        return "away from " + direction.removeprefix("toward ")
    if direction.startswith("away from "):
        return "toward " + direction.removeprefix("away from ")
    return OPPOSITE[direction]


def physical(value: float, positive: str) -> str | None:
    """Where a signed result points, or None for a scalar, zero or an unreadable sign."""
    canonical = normalize(positive)
    if not canonical or value == 0:
        return None
    return canonical if value > 0 else opposite(canonical)
