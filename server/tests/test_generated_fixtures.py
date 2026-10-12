"""Offline replay of recorded replies adapted to the current draft metadata.

See tests/fixtures/drafts/README.md for the authored migration. Expressions and
teaching text are original; these are not new API generations.
"""

import asyncio
import json
from pathlib import Path

import pytest

from app.lesson.generate import Metrics, generate_lesson
from app.lesson.models import Source
from app.settings import REPO_ROOT
from tests.fake_llm import FakeLLM

DRAFTS = sorted((REPO_ROOT / "tests" / "fixtures" / "drafts").glob("*.json"))


def replay(path: Path) -> Metrics:
    data = json.loads(path.read_text(encoding="utf-8"))
    replies: list[str | Exception] = [json.dumps(r, ensure_ascii=False) for r in data["replies"]]
    metrics = Metrics()

    async def go() -> None:
        async for _ in generate_lesson(Source(**data["source"]), FakeLLM(replies), metrics):
            pass

    asyncio.run(go())
    return metrics


def test_all_three_prompt_test_inputs_are_recorded() -> None:
    names = {p.stem for p in DRAFTS}
    assert {"gen_gauss_topic", "gen_point_charge", "gen_pasted_solution"} <= names


@pytest.mark.parametrize("path", DRAFTS, ids=lambda p: p.stem)
def test_recorded_lesson_still_builds(path: Path) -> None:
    metrics = replay(path)

    assert metrics.lesson is not None and metrics.final_error is None
    assert not [v for _, v in metrics.leftovers if v.fatal]
    assert all(s.warning is None for s in metrics.lesson.steps)
    assert metrics.lesson.calcs and all(c.used_in_steps for c in metrics.lesson.calcs)


def test_pasted_solution_lesson_marks_the_wrong_step() -> None:
    path = next(p for p in DRAFTS if p.stem == "gen_pasted_solution")
    lesson = replay(path).lesson
    assert lesson is not None
    assert any(p.type == "mark_wrong" for s in lesson.steps for p in s.draw)
