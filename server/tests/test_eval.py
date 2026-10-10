import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.lesson.claude import LLMRefused
from app.lesson.generate import Metrics, generate_lesson
from app.lesson.ledger import Entry
from app.lesson.models import Source
from scripts.eval import (
    GRADING_VERSION,
    Expected,
    Problem,
    Result,
    compare_section,
    grade,
    load_problems,
    missing_draws,
    render_report,
    run_eval,
    value_matches,
)
from scripts.eval_units import convert, parse_unit
from tests.drafts import SOURCE_TEXT, calc, draft_json, good_steps
from tests.fake_llm import FakeLLM

FLUX = Problem(
    id="es-flux",
    topic="electrostatics/gauss",
    level="simple",
    source="own",
    input=SOURCE_TEXT,
    expected=[Expected("flux", 338.8299, "N*m**2/C")],
    must_draw=["point_charge", "math|text"],
)
FIELD = Problem(
    id="es-field",
    topic="electrostatics/gauss",
    level="simple",
    source="own",
    input=SOURCE_TEXT,
    expected=[Expected("E", 674.08, "N/C")],
    must_draw=["gaussian_sphere"],
)
META = {
    "grading_version": GRADING_VERSION,
    "date": "2026-10-10",
    "model": "claude-sonnet-5-5",
    "thinking": "between_tools",
    "effort": "high",
    "prompt_sha": "abc123",
    "wall_s": 12.0,
}


def run(
    problems: list[Problem], replies: list[list[str | Exception]], **kw: object
) -> list[Result]:
    queue = list(replies)
    return asyncio.run(run_eval(problems, lambda: FakeLLM(queue.pop(0)), log=lambda _: None, **kw))  # type: ignore[arg-type]


def test_two_mocked_problems_are_graded_and_reported(tmp_path: Path) -> None:
    results = run([FLUX, FIELD], [[draft_json()], [draft_json()]], save_dir=tmp_path)

    by_id = {r.id: r for r in results}
    assert by_id["es-flux"].passed
    assert by_id["es-field"].numbers == {"E": False}
    assert by_id["es-field"].missing_draws == ["gaussian_sphere"]
    assert all(r.cost_usd > 0 and r.first_step_s is not None for r in results)
    saved = json.loads((tmp_path / "es-flux.json").read_text(encoding="utf-8"))
    assert saved["lesson"]["calcs"][0]["used_in_steps"] == ["s4"]

    report = render_report(results, META)
    assert "| electrostatics | 2 | 50% | 100% | 50% | 50% |" in report
    assert "**es-field**: numbers not found among verified calcs: E; missing drawings" in report
    assert "## 3 worst lessons" in report and report.index("**es-field** (pass") > 0


def test_generation_error_is_recorded_not_raised() -> None:
    [result] = run([FLUX], [[LLMRefused("declined"), LLMRefused("declined")]])

    assert not result.valid and not result.passed
    assert result.error is not None and "could not be generated" in result.error


def test_cost_limit_skips_the_remaining_problems() -> None:
    results = run([FLUX, FIELD], [[draft_json()], [draft_json()]], concurrency=1, max_cost=0.0)

    assert all(r.skipped for r in results)
    assert "(2 skipped)" in render_report(results, META)


def test_value_matching_allows_si_prefixes_and_percent_not_other_factors() -> None:
    cap = Expected("C", 1.7708e-10, "F")
    assert value_matches(cap, [Entry(177.08, "pF", "picofarads", True)])
    assert not value_matches(cap, [Entry(17.708, "pF", "picofarads", True)])
    assert value_matches(Expected("err", 1.99, "%"), [Entry(0.0199, "1", "", True)])
    assert not value_matches(Expected("E", 733.618, "N/C"), [Entry(-733.6, "N/C", "", True)])


@pytest.mark.parametrize(
    "value,unit,verified",
    [
        (12000, "V", True),
        (12, "A", True),
        (-12, "V", True),
        (12, "V", False),
        (12, "unknown", True),
        (float("nan"), "V", True),
        (float("inf"), "V", True),
    ],
)
def test_eval_rejects_wrong_scales_units_signs_and_unverified_values(
    value: float,
    unit: str,
    verified: bool,
) -> None:
    assert not value_matches(Expected("voltage", 12, "V"), [Entry(value, unit, "", verified)])


def test_eval_tiny_and_zero_targets_have_no_absolute_tolerance_loophole() -> None:
    assert not value_matches(Expected("zero", 0, "C"), [Entry(1e-20, "C", "", True)])
    assert not value_matches(Expected("q", 1e-20, "C"), [Entry(2e-20, "C", "", True)])
    assert value_matches(Expected("zero", 0, "C"), [Entry(0, "C", "", True)])


@pytest.mark.parametrize(
    "source,target,value,expected",
    [
        ("kN", "N", -2, -2000),
        ("cm/s^2", "m/s**2", 2, 0.02),
        ("kg*m/s**2", "N", 3, 3),
        ("Ω", "ohm", 100, 100),
        ("µC", "C", 2, 2e-6),
        ("N*m^2/C", "V*m", 2, 2),
    ],
)
def test_eval_converts_only_dimensionally_compatible_units(
    source: str,
    target: str,
    value: float,
    expected: float,
) -> None:
    assert convert(value, source, target) == pytest.approx(expected)


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os').getcwd()",
        "N.__class__",
        "N+N",
        "N**999999",
        "N**0.5",
        "N//C",
        "True",
        "2*N",
        "N**(2**10)",
        "(" * 200 + "N" + ")" * 200,
    ],
)
def test_eval_unit_parser_rejects_executable_or_unbounded_expressions(text: str) -> None:
    with pytest.raises(ValueError):
        parse_unit(text)


def generated_metrics(steps: list[dict[str, Any]]) -> Metrics:
    metrics = Metrics()

    async def collect() -> None:
        async for _ in generate_lesson(
            Source(type="problem", text=SOURCE_TEXT),
            FakeLLM([draft_json(steps)]),
            metrics,
        ):
            pass

    asyncio.run(collect())
    return metrics


def test_eval_does_not_credit_an_unused_correct_calc() -> None:
    steps = good_steps()
    steps[3]["calcs"].append(calc("c2", "x", {"x": 674.08}, 674.08, "N/C", ""))
    metrics = generated_metrics(steps)
    assert metrics.state is not None and metrics.state.ledger["c2"].verified
    assert grade(FIELD, metrics, None).numbers == {"E": False}


def test_eval_grades_displayed_rounding_not_only_full_precision_calcs() -> None:
    steps = good_steps()
    steps[3]["calcs"].append(calc("c2", "q", {"q": 1e-9}, 1e-9, "C", "coulombs"))
    steps[3]["say"] = "The charge is {c2:0dp}."
    metrics = generated_metrics(steps)
    problem = replace(FLUX, expected=[Expected("charge", 1e-9, "C")])
    assert metrics.lesson is not None and metrics.lesson.steps[3].say == "The charge is 0 coulombs."
    assert grade(problem, metrics, None).numbers == {"charge": False}


def test_eval_does_not_pass_a_lesson_with_an_unverified_step() -> None:
    metrics = generated_metrics(good_steps())
    assert metrics.lesson is not None
    steps = metrics.lesson.steps
    metrics.lesson = metrics.lesson.model_copy(
        update={
            "steps": [*steps[:-1], steps[-1].model_copy(update={"warning": "unverified"})],
        }
    )
    result = grade(FLUX, metrics, None)
    assert result.valid and result.numbers_ok and not result.missing_draws
    assert result.unverified_steps == 1 and not result.passed
    assert "unverified steps: 1" in render_report([result], META)


def test_unchecked_direction_claims_cannot_be_reported_as_an_automatic_pass() -> None:
    metrics = generated_metrics(good_steps())
    problem = replace(FLUX, manual_checks=["Check current directions in the summary."])
    result = grade(problem, metrics, None)
    assert result.valid and result.numbers_ok and result.unverified_steps == 0
    assert not result.passed
    assert "manual review required: Check current directions" in render_report([result], META)


def test_old_report_scores_are_not_presented_as_a_new_evaluation() -> None:
    old_meta = {k: v for k, v in META.items() if k != "grading_version"}
    assert "does not recheck signs, units" in render_report([], old_meta)


def test_comparisons_warn_when_grading_criteria_differ() -> None:
    assert "Scoring versions differ" in "\n".join(compare_section([], [], ("old", "new")))
    assert "Scoring versions differ" not in "\n".join(
        compare_section([], [], ("old", "new"), GRADING_VERSION)
    )


def test_missing_draws_accepts_alternatives() -> None:
    assert missing_draws(["incline_block", "free_body|vector"], {"incline_block", "vector"}) == []
    assert missing_draws(["axes_plot|axes"], {"text"}) == ["axes_plot|axes"]


def test_eval_bank_is_well_formed() -> None:
    problems = load_problems()
    assert len(problems) == 30
    assert len({p.id for p in problems}) == 30
    assert sum(p.source == "audit" for p in problems) == 10
    assert all(p.expected for p in problems)
    for problem in problems:
        for expected in problem.expected:
            parse_unit(expected.unit)
    groups = {p.group for p in problems}
    assert {"mechanics", "kinematics", "circuits", "electrostatics"} <= groups
    kirchhoff = next(p for p in problems if p.id == "circ-kirchhoff")
    assert kirchhoff.manual_checks and "directions" in kirchhoff.manual_checks[0]
