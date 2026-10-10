import asyncio
import json
from typing import Any

import pytest

from app.lesson.claude import LLMRefused
from app.lesson.generate import FIX_SCHEMA, LESSON_SCHEMA, Header, Metrics, generate_lesson
from app.lesson.models import UNVERIFIED_NOTE, Source, Step
from app.lesson.pipeline import LessonError
from tests.drafts import (
    FLUX,
    SOURCE_TEXT,
    calc,
    choice,
    draft_json,
    good_steps,
    item,
    math,
    step,
    symbol,
)
from tests.fake_llm import FakeLLM

SOURCE = Source(type="problem", text=SOURCE_TEXT)


def run(llm: FakeLLM, metrics: Metrics | None = None) -> list[Header | Step]:
    async def collect() -> list[Header | Step]:
        return [event async for event in generate_lesson(SOURCE, llm, metrics)]

    return asyncio.run(collect())


def steps_of(events: list[Header | Step]) -> list[Step]:
    return [e for e in events if isinstance(e, Step)]


def fix_reply(*steps: dict[str, Any]) -> str:
    return json.dumps({"steps": list(steps)}, ensure_ascii=False)


def test_clean_draft_streams_header_then_checked_steps() -> None:
    metrics = Metrics()
    llm = FakeLLM([draft_json()])

    events = run(llm, metrics)

    assert isinstance(events[0], Header) and events[0].title == "Flux"
    assert [s.id for s in steps_of(events)] == ["s1", "s2", "s3", "s4", "s5"]
    assert len(llm.requests) == 1 and llm.requests[0][1] == LESSON_SCHEMA
    assert metrics.fixes == 0 and metrics.lesson is not None and metrics.final_error is None
    assert metrics.first_step_s is not None and metrics.usage.calls == 1


def test_ledger_fills_numbers_and_derives_used_in_steps() -> None:
    metrics = Metrics()
    events = run(FakeLLM([draft_json()]), metrics)

    s4 = steps_of(events)[3]
    assert s4.say == "So the flux is 339 newton meters squared per coulomb, whatever the radius."
    latex = next(p for p in s4.draw if p.id == "value").latex  # type: ignore[union-attr]
    assert latex == r"\Phi = 339\,\mathrm{N\cdot m^{2}/C}"
    assert metrics.lesson is not None
    assert metrics.lesson.calcs[0].used_in_steps == ["s4"]


def test_templates_are_expanded_before_streaming() -> None:
    s1 = steps_of(run(FakeLLM([draft_json()])))[0]

    assert all(p.type != "template" for p in s1.draw)
    assert {p.id for p in s1.draw} >= {"q1-charge", "sym-q"}


def test_step_with_a_violation_is_fixed_alone() -> None:
    steps = good_steps()
    steps[3] = step(
        "s4",
        "So the flux is 338.8 newton meters squared per coulomb.",
        [math("value", r"\Phi = {c1}", 360)],
        calcs=[FLUX],
    )
    fixed = good_steps()[3]
    llm = FakeLLM([draft_json(steps), fix_reply(fixed)])
    metrics = Metrics()

    events = run(llm, metrics)

    assert metrics.fixes == 1 and metrics.fixes_failed == 0
    assert metrics.fix_reasons == {"number": 1}
    assert llm.requests[1][1] == FIX_SCHEMA
    fix_request = llm.requests[1][0]
    assert "338.8 is not a given number" in fix_request
    assert '"id":"s3"' in fix_request  # the lesson so far is included
    assert steps_of(events)[3].say.startswith("So the flux is 339")
    assert steps_of(events)[3].warning is None


def test_missing_checkpoint_is_inserted_by_the_fix() -> None:
    steps = good_steps()
    steps[2] = step("s3", "A closed surface can have any shape at all.")
    extra = [step(f"s{i}", "Another idea about field lines.") for i in (6, 7)]
    steps = steps[:4] + extra + steps[4:]  # s1 s2 s3 s4 s6 s7 s5: five in a row at s6
    check = step("s5a", "Quick check before we go on.", kind="checkpoint", checkpoint=choice())
    llm = FakeLLM([draft_json(steps), fix_reply(check, extra[0])])

    events = run(llm)

    assert [s.id for s in steps_of(events)] == ["s1", "s2", "s3", "s4", "s5a", "s6", "s7", "s5"]
    assert "without a checkpoint" in llm.requests[1][0]


def test_hand_written_number_left_after_the_fix_is_flagged_unverified() -> None:
    steps = good_steps()
    steps[3] = step(
        "s4",
        "So the flux is 338.8 newton meters squared per coulomb.",
        [math("value", r"\Phi = {c1}", 360)],
        calcs=[FLUX],
    )
    llm = FakeLLM([draft_json(steps), fix_reply(steps[3])])
    metrics = Metrics()

    s4 = steps_of(run(llm, metrics))[3]

    assert s4.warning == "unverified" and s4.say.endswith(UNVERIFIED_NOTE)
    assert any(v.rule == "number" for _, v in metrics.leftovers)


def test_fatal_problem_left_after_the_fix_ends_with_a_safe_error() -> None:
    long_say = " ".join(["word"] * 35)
    steps = good_steps()
    steps[1] = step("s2", long_say, steps[1]["draw"])
    llm = FakeLLM([draft_json(steps), fix_reply(steps[1])])

    with pytest.raises(LessonError, match="could not be built"):
        run(llm)


def test_wrong_calc_is_fixed_then_marked_unverified_if_still_wrong() -> None:
    wrong = calc(
        "c1",
        "q/eps0",
        {"q": 3e-9, "eps0": 8.854e-12},
        1990.0,
        "N*m**2/C",
        "newton meters squared per coulomb",
    )
    steps = good_steps()
    steps[3] = {**steps[3], "calcs": [wrong]}
    llm = FakeLLM([draft_json(steps), fix_reply(steps[3])])

    s4 = steps_of(run(llm))[3]

    assert "computed 338.83, expected 1990" in llm.requests[1][0]
    assert s4.warning == "unverified"


def test_a_calc_can_use_an_earlier_result_at_full_precision() -> None:
    field = calc("c2", "c1/(4*pi*R^2)", {"R": 0.2}, 674.08, "N/C", "newtons per coulomb")
    steps = good_steps()
    steps.insert(4, step("s4b", "On the surface the field is {c2}.", calcs=[field]))
    metrics = Metrics()

    events = run(FakeLLM([draft_json(steps)]), metrics)

    s4b = next(s for s in steps_of(events) if s.id == "s4b")
    assert s4b.say == "On the surface the field is 674 newtons per coulomb."
    assert metrics.lesson is not None
    c2 = metrics.lesson.calcs[1]
    assert c2.values["c1"] == pytest.approx(3e-9 / 8.854e-12, rel=1e-12)


def test_example_inputs_declared_in_calcs_may_be_written_as_they_are() -> None:
    example = calc("c2", "q2/eps0", {"q2": 5e-9, "eps0": 8.854e-12}, 564.72, "N*m**2/C",
                   "newton meters squared per coulomb")  # fmt: skip
    steps = good_steps()
    steps.insert(4, step("s4b", "For example, 5 nanocoulombs gives {c2}.", calcs=[example]))
    metrics = Metrics()

    run(FakeLLM([draft_json(steps)]), metrics)

    assert metrics.fixes == 0


def test_unsupported_function_message_reaches_the_fix() -> None:
    bad = calc(
        "c1",
        "abs(q)/eps0",
        {"q": 3e-9, "eps0": 8.854e-12},
        338.83,
        "N*m**2/C",
        "newton meters squared per coulomb",
    )
    steps = good_steps()
    steps[3] = {**steps[3], "calcs": [bad]}
    llm = FakeLLM([draft_json(steps), fix_reply(good_steps()[3])])

    s4 = steps_of(run(llm))[3]

    assert "abs is not supported" in llm.requests[1][0]
    assert s4.warning is None


def test_symbol_used_before_its_legend_entry_is_sent_to_the_fix() -> None:
    steps = good_steps()
    steps[1] = step(
        "s2", "Flux counts the field lines.", [math("law", r"\Phi = \frac{Q}{\varepsilon_0}")]
    )
    llm = FakeLLM([draft_json(steps), fix_reply(good_steps()[1])])

    events = run(llm)

    assert r"uses \Phi, \epsilon_0 before a symbol legend entry" in llm.requests[1][0]
    assert len(steps_of(events)) == 5


def test_whole_lesson_is_retried_once_when_it_fails_before_the_first_step() -> None:
    llm = FakeLLM([LLMRefused("the AI declined to write this lesson"), draft_json()])
    metrics = Metrics()

    events = run(llm, metrics)

    assert metrics.retries == 1
    assert sum(isinstance(e, Header) for e in events) == 1
    assert "A previous attempt failed: the AI declined" in llm.requests[1][0]


def test_two_failures_before_the_first_step_raise_a_safe_error() -> None:
    llm = FakeLLM(["not json at all", '{"title": "x"'])

    with pytest.raises(LessonError, match="could not be generated"):
        run(llm)


def test_failure_after_steps_were_shown_is_not_retried() -> None:
    truncated = draft_json()[:-400]  # cut inside the last steps
    llm = FakeLLM([truncated])

    async def collect() -> list[Header | Step]:
        out: list[Header | Step] = []
        with pytest.raises(LessonError, match="stopped early"):
            async for event in generate_lesson(SOURCE, llm):
                out.append(event)
        return out

    shown = asyncio.run(collect())
    assert len(steps_of(shown)) >= 1 and len(llm.requests) == 1


def test_cost_is_accumulated_over_lesson_and_fix_calls() -> None:
    steps = good_steps()
    steps[3] = {**steps[3], "say": "So the flux is 338.8 newton meters squared per coulomb."}
    metrics = Metrics()
    run(FakeLLM([draft_json(steps), fix_reply(good_steps()[3])]), metrics)

    assert metrics.usage.calls == 2 and metrics.usage.cost_usd > 0


def test_number_checkpoint_answer_comes_from_the_ledger() -> None:
    steps = good_steps()
    number = {
        "question": "What is the flux?",
        "type": "number",
        "choices": [],
        "answer": "{c1:2sf}",
        "hint": "Use Q over epsilon zero.",
        "reexplain_hint": "Divide the charge by epsilon zero.",
    }
    steps.insert(
        4, step("s4b", "Your turn: compute the flux.", kind="checkpoint", checkpoint=number)
    )

    events = run(FakeLLM([draft_json(steps)]))

    cp = next(s for s in steps_of(events) if s.id == "s4b").checkpoint
    assert cp is not None and cp.answer == 340 and cp.unit == "N·m²/C"


def test_symbol_draft_item_is_kept_in_the_streamed_step() -> None:
    s1 = steps_of(run(FakeLLM([draft_json()])))[0]
    sym = next(p for p in s1.draw if p.id == "sym-q")
    assert sym.type == "symbol" and sym.unit == "C"  # type: ignore[union-attr]


def test_item_helpers_build_valid_drafts() -> None:
    assert symbol("a", "Q", "charge", "C", 10)["type"] == "symbol"
    assert item("b", "erase", txt={"target_id": "a"})["pts"] == []
