import asyncio
import json
from typing import Any

import pytest

from app.lesson.generate import Metrics, generate_lesson
from app.lesson.ledger import Entry
from app.lesson.lint import LintState
from app.lesson.models import Source
from app.lesson.pipeline import LessonError
from app.lesson.stepcheck import LessonState, check_step, commit
from tests.drafts import SOURCE_TEXT, calc, draft_json, good_steps, item, step
from tests.fake_llm import FakeLLM

SOURCE = Source(type="problem", text=SOURCE_TEXT)


def state() -> LessonState:
    return LessonState(SOURCE, LintState([]))


def test_calc_inputs_cannot_shadow_an_earlier_ledger_result() -> None:
    context = state()
    context.ledger["c1"] = Entry(2, "N", "newtons", True)
    raw = step(
        "s1", "The force is {c2}.", calcs=[calc("c2", "c1*2", {"c1": 999}, 1998, "N", "newtons")]
    )

    checked = check_step(raw, context)

    assert checked.fatal
    assert "c2" not in checked.entries
    assert any("ledger" in v.message for v in checked.violations)
    assert context.ledger["c1"].value == 2


def test_calc_inputs_cannot_shadow_a_result_in_the_same_step() -> None:
    raw = step(
        "s1",
        "The force is {c2}.",
        calcs=[
            calc("c1", "x", {"x": 2}, 2, "N", "newtons"),
            calc("c2", "c1*2", {"c1": 999}, 1998, "N", "newtons"),
        ],
    )
    checked = check_step(raw, state())
    assert checked.fatal and "c2" not in checked.entries
    assert checked.entries["c1"].value == 2


def test_template_child_collision_is_rejected_before_streaming() -> None:
    raw = step(
        "s1",
        "Here is a charge.",
        [
            item("q", "point_charge", {"x": 0, "y": 0}),
            item("q-charge", "point", {"x": 1, "y": 1}),
        ],
    )

    checked = check_step(raw, state())

    assert checked.fatal
    assert any("already used" in v.message for v in checked.violations)


def test_template_group_id_cannot_be_reused_as_a_later_primitive_id() -> None:
    context = state()
    first = step("s1", "Here is a charge.", [item("q", "point_charge", {"x": 0, "y": 0})])
    checked = check_step(first, context)
    assert not checked.fatal
    commit(context, checked)
    second = step("s2", "Here is a point.", [item("q", "point", {"x": 1, "y": 1})])
    assert check_step(second, context).fatal


def test_template_children_cannot_collide_with_another_template_group() -> None:
    raw = step(
        "s1",
        "Here are the charges.",
        [
            item("q", "point_charge", {"x": 0, "y": 0}),
            item("q-charge", "point_charge", {"x": 1, "y": 1}),
        ],
    )
    assert check_step(raw, state()).fatal


@pytest.mark.parametrize("key", ["id", "type", "group", "color", "label", "at"])
def test_generic_arguments_cannot_override_primitive_metadata(key: str) -> None:
    raw = step("s1", "Here is a point.", [item("p", "point", {"x": 0, "y": 0}, {key: "replaced"})])
    assert check_step(raw, state()).fatal


def test_final_validation_failure_raises_instead_of_completing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.lesson.models import Lesson

    def invalid_lesson(*args: Any, **kwargs: Any) -> Any:
        return Lesson.model_validate({})

    # Inject an otherwise invisible final error, after individually valid steps.
    class BrokenFinalLesson:
        model_validate = staticmethod(invalid_lesson)

    monkeypatch.setattr("app.lesson.generate.Lesson", BrokenFinalLesson)
    metrics = Metrics()

    async def collect() -> None:
        async for _ in generate_lesson(SOURCE, FakeLLM([draft_json()]), metrics):
            pass

    with pytest.raises(LessonError, match="validation"):
        asyncio.run(collect())
    assert metrics.lesson is None and metrics.final_error is not None


def test_collision_repair_is_one_step_and_only_valid_ids_are_emitted() -> None:
    steps = good_steps()
    steps[1]["draw"].append(item("extra", "point", {"x": 0, "y": 0}, {"id": "q1-charge"}))
    llm = FakeLLM([draft_json(steps), json.dumps({"steps": [good_steps()[1]]})])
    metrics = Metrics()

    async def collect() -> None:
        async for _ in generate_lesson(SOURCE, llm, metrics):
            pass

    asyncio.run(collect())

    assert metrics.fixes == 1 and metrics.lesson is not None
    assert len(llm.requests) == 2
    ids = [p.id for s in metrics.lesson.steps for p in s.draw]
    assert len(ids) == len(set(ids))
