import copy
from typing import Any

import pytest
from pydantic import ValidationError

from app.lesson.fixtures import load_fixture
from app.lesson.models import Lesson, StreamedStep, VectorPrim, check_references


def step(step_id: str, kind: str = "explain", **extra: Any) -> dict[str, Any]:
    return {"id": step_id, "kind": kind, "say": "A short line.", **extra}


def lesson(*steps: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "id": "l1",
        "title": "Test",
        "level": "simple",
        "source": {"type": "topic", "text": "test"},
        "steps": list(steps) or [step("s1")],
        **extra,
    }


CHOICE = {"question": "Q?", "type": "choice", "choices": ["a", "b"], "answer": 1}


def test_gauss_fixture_is_valid() -> None:
    parsed = Lesson.model_validate(load_fixture("gauss_law"))

    assert [s.id for s in parsed.steps] == ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]
    assert sum(s.kind == "checkpoint" for s in parsed.steps) == 1
    assert all(s.subtitles.uz for s in parsed.steps)
    assert [c.id for c in parsed.calcs] == ["c1"]


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        Lesson.model_validate(lesson(step("s1", sayy="typo")))


def test_unknown_primitive_type_is_rejected() -> None:
    bad = step("s1", draw=[{"id": "p", "type": "hexagon"}])
    with pytest.raises(ValidationError):
        Lesson.model_validate(lesson(bad))


def test_unknown_color_token_is_rejected() -> None:
    bad = step("s1", draw=[{"id": "p", "type": "point", "x": 1, "y": 1, "color": "#ff0000"}])
    with pytest.raises(ValidationError):
        Lesson.model_validate(lesson(bad))


def test_say_over_30_words_is_rejected() -> None:
    with pytest.raises(ValidationError, match="31 words"):
        Lesson.model_validate(lesson(step("s1", say="word " * 31)))


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate step id"):
        Lesson.model_validate(lesson(step("s1"), step("s1")))
    point = {"id": "p", "type": "point", "x": 1, "y": 1}
    with pytest.raises(ValidationError, match="duplicate primitive id"):
        Lesson.model_validate(lesson(step("s1", draw=[point]), step("s2", draw=[point])))


def test_more_than_four_steps_without_checkpoint_is_rejected() -> None:
    steps = [step(f"s{i}") for i in range(1, 6)]
    with pytest.raises(ValidationError, match="without a checkpoint"):
        Lesson.model_validate(lesson(*steps))


def test_summary_may_follow_four_explain_steps() -> None:
    steps = [step(f"s{i}") for i in range(1, 5)] + [step("s5", "summary")]
    Lesson.model_validate(lesson(*steps))


def test_checkpoint_step_needs_checkpoint_and_vice_versa() -> None:
    with pytest.raises(ValidationError, match="checkpoint step needs"):
        Lesson.model_validate(lesson(step("s1", "checkpoint")))
    with pytest.raises(ValidationError, match="checkpoint step needs"):
        Lesson.model_validate(lesson(step("s1", checkpoint=CHOICE)))


@pytest.mark.parametrize(
    "checkpoint",
    [
        CHOICE | {"answer": 2},
        CHOICE | {"choices": ["only one"], "answer": 0},
        {"question": "How much?", "type": "number", "answer": 3.5},
    ],
)
def test_bad_checkpoints_are_rejected(checkpoint: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Lesson.model_validate(lesson(step("s1", "checkpoint", checkpoint=checkpoint)))


def test_number_checkpoint_with_unit_is_valid() -> None:
    number = {"question": "Flux?", "type": "number", "answer": 338.8, "unit": "N·m²/C"}
    Lesson.model_validate(lesson(step("s1", "checkpoint", checkpoint=number)))


def test_slider_value_must_be_in_range() -> None:
    slider = {"id": "r", "label": "R", "min": 0, "max": 1, "value": 2, "binds": ["c.r"]}
    with pytest.raises(ValidationError, match="min <= value <= max"):
        Lesson.model_validate(lesson(step("s1", sliders=[slider])))


def test_calc_must_use_known_steps() -> None:
    calc = {"id": "c", "expr": "1", "expected": 1, "unit": "m", "used_in_steps": ["s9"]}
    with pytest.raises(ValidationError, match="unknown steps"):
        Lesson.model_validate(lesson(calcs=[calc]))


def test_vector_uses_from_alias_both_ways() -> None:
    vector = VectorPrim.model_validate(
        {"id": "v", "type": "vector", "from": [0, 0], "to": [10, 0], "name": "E"}
    )

    assert vector.model_dump()["from"] == (0, 0)
    assert "from_" not in vector.model_dump()


def test_streamed_step_requires_audio_url_key() -> None:
    with pytest.raises(ValidationError):
        StreamedStep.model_validate(step("s1"))
    StreamedStep.model_validate(step("s1", audio_url=None))


def test_references_must_point_to_something_drawn_earlier() -> None:
    raw = lesson(
        step("s1", draw=[{"id": "hl", "type": "highlight", "target_id": "later"}]),
        step("s2", draw=[{"id": "later", "type": "point", "x": 1, "y": 1}]),
    )

    assert check_references(Lesson.model_validate(raw)) == ["step s1: hl targets unknown 'later'"]


def test_references_may_target_a_group() -> None:
    child = {"id": "g-1", "type": "point", "x": 1, "y": 1, "group": "g"}
    raw = lesson(step("s1", draw=[child, {"id": "e", "type": "erase", "target_id": "g"}]))

    assert check_references(Lesson.model_validate(raw)) == []


def test_slider_binds_must_name_a_real_field() -> None:
    circle = {"id": "c", "type": "circle", "cx": 1, "cy": 1, "r": 5}
    good = {"id": "r", "label": "R", "min": 1, "max": 9, "value": 5, "binds": ["c.r"]}
    bad = good | {"id": "w", "binds": ["c.width"]}
    raw = lesson(step("s1", draw=[circle], sliders=[good, bad]))

    assert check_references(Lesson.model_validate(raw)) == [
        "step s1: slider w binds unknown 'c.width'"
    ]


def test_fixture_is_not_mutated_by_validation() -> None:
    raw = load_fixture("gauss_law")
    before = copy.deepcopy(raw)
    Lesson.model_validate(raw)

    assert raw == before
