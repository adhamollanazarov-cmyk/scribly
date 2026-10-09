"""Golden lessons served in mock mode (MOCK_AI=1)."""

import json
from typing import Any

from app.settings import REPO_ROOT

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "lessons"


def load_fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return data
