import copy
from typing import Any

import pytest

from app.lesson.fixtures import FIXTURE_DIR, load_fixture
from app.lesson.models import StreamedStep, check_references
from app.lesson.pipeline import LessonError, prepare_lesson
from app.lesson.verify import UNVERIFIED_NOTE


@pytest.mark.parametrize("name", [path.stem for path in FIXTURE_DIR.glob("*.json")])
def test_every_golden_fixture_survives_the_complete_pipeline(name: str) -> None:
    raw = load_fixture(name)
    before = copy.deepcopy(raw)
    lesson, results = prepare_lesson(raw)

    assert raw == before
    assert all(result.ok for result in results)
    assert check_references(lesson) == []
    assert all(p.type != "template" for step in lesson.steps for p in step.draw)
    for step in lesson.steps:
        StreamedStep.model_validate(step.model_dump() | {"audio_url": None})


@pytest.mark.parametrize(
    "overrides",
    [{"expected": float("inf")}, {"rel_tol": float("inf")}, {"expr": "9^9^9^9//1"}],
)
def test_invalid_calculation_is_flagged_before_narration(overrides: dict[str, Any]) -> None:
    raw = load_fixture("gauss_law")
    raw["calcs"][0].update(overrides)

    lesson, results = prepare_lesson(raw)

    assert not results[0].ok
    assert lesson.steps[5].warning == "unverified"
    assert lesson.steps[5].say.endswith(UNVERIFIED_NOTE)
    StreamedStep.model_validate(lesson.steps[5].model_dump() | {"audio_url": None})


def test_expansion_collision_is_rejected_before_streaming() -> None:
    raw = load_fixture("gauss_law")
    raw["steps"][0]["draw"].append({"id": "q1-charge", "type": "point", "x": 0, "y": 0})

    with pytest.raises(LessonError, match="could not be expanded"):
        prepare_lesson(raw)


def test_unknown_references_have_a_safe_public_error() -> None:
    raw = load_fixture("gauss_law")
    raw["steps"][-1]["draw"][0]["target_id"] = "SYNTHETIC_PRIVATE_INPUT"

    with pytest.raises(LessonError, match="broken reference") as caught:
        prepare_lesson(raw)
    assert "SYNTHETIC_PRIVATE_INPUT" not in str(caught.value)


@pytest.mark.xfail(
    strict=True, reason="R4: input warning suppresses the spoken verification warning"
)
def test_prefilled_warning_cannot_suppress_spoken_verification_warning() -> None:
    raw = load_fixture("gauss_law")
    raw["calcs"][0]["expected"] = 999
    raw["steps"][5]["warning"] = "unverified"

    lesson, _ = prepare_lesson(raw)

    assert lesson.steps[5].say.endswith(UNVERIFIED_NOTE)
