"""Golden lessons served in mock mode (MOCK_AI=1)."""

import json
from typing import Any

from app.settings import REPO_ROOT

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "lessons"
DEFAULT_FIXTURE = "gauss_law"


def load_fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return data


def fixture_names() -> list[str]:
    return sorted(path.stem for path in FIXTURE_DIR.glob("*.json"))


def fixture_for_text(text: str) -> str:
    """The fixture whose source text matches the request (case and spacing ignored)."""
    wanted = _normalize(text)
    for name in fixture_names():
        if _normalize(load_fixture(name)["source"]["text"]) == wanted:
            return name
    return DEFAULT_FIXTURE


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()
