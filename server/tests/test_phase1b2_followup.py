"""Offline regressions for the accepted Phase 1b.2 medium/low fixes."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.lesson.direction import physical
from app.lesson.draft import CalcDraft, StepDraft
from app.lesson.generate import LessonError, Metrics, generate_lesson
from app.lesson.ledger import Entry
from app.lesson.lint import LintState, extract_givens, formula_symbols
from app.lesson.models import Source
from app.lesson.prompt import system_prompt
from app.lesson.stepcheck import LessonState, check_step, commit
from scripts.eval import (
    GRADING_VERSION,
    Expected,
    Result,
    compare_section,
    load_problems,
    render_report,
    value_matches,
)
from tests.drafts import calc, draft_json, item, math, step
from tests.fake_llm import FakeLLM


def state(text: str = "Find the force.", source_type: str = "problem") -> LessonState:
    source = Source(type=source_type, text=text)
    return LessonState(source, LintState(extract_givens(text)))


def directed(value: float = 0, **kw: Any) -> dict[str, Any]:
    return calc("c1", "F", {"F": value}, value, "N", "newtons", "+x", **kw)


def convention(**kw: Any) -> dict[str, Any]:
    return item(
        "conv", "arrow", {"x1": 100, "y1": 500, "x2": 300, "y2": 500}, label="+x", at=0, **kw
    )


@pytest.mark.parametrize("kind", ["component", "oriented"])
@pytest.mark.parametrize("value", [-2, 0, 2])
@pytest.mark.parametrize("missing", ["positive", "frame", "quantity_kind"])
def test_directed_quantities_require_explicit_metadata(
    kind: str, value: float, missing: str
) -> None:
    raw = directed(value, quantity_kind=kind)
    del raw[missing]
    checked = check_step(step("s1", "{c1}.", [convention()], calcs=[raw]), state())
    assert checked.fatal and not checked.entries


@pytest.mark.parametrize("kind", ["component", "oriented"])
@pytest.mark.parametrize(
    "field,value", [("positive", ""), ("positive", "sideways"), ("frame", ""), ("frame", " lab ")]
)
def test_empty_or_unreadable_directed_metadata_is_rejected(
    kind: str, field: str, value: str
) -> None:
    raw = directed(quantity_kind=kind)
    raw[field] = value
    checked = check_step(step("s1", "{c1}.", calcs=[raw]), state())
    assert checked.fatal and not checked.entries


@pytest.mark.parametrize("kind", ["scalar", "magnitude"])
@pytest.mark.parametrize("field,value", [("positive", "+x"), ("positive", " "), ("frame", "lab")])
def test_scalars_and_magnitudes_require_empty_metadata(kind: str, field: str, value: str) -> None:
    raw = calc("c1", "v", {"v": 2}, 2, "J", "joules", quantity_kind=kind)
    raw[field] = value
    checked = check_step(step("s1", "{c1}.", calcs=[raw]), state())
    assert checked.fatal and not checked.entries


def test_negative_scalar_and_nonnegative_magnitude_need_no_direction() -> None:
    for kind, value in (("scalar", -2), ("magnitude", 0), ("magnitude", 2)):
        raw = calc("c1", "v", {"v": value}, value, "J", "joules", quantity_kind=kind)
        checked = check_step(step("s1", "{c1}.", calcs=[raw]), state())
        assert not checked.violations and checked.entries["c1"].verified
    with pytest.raises(ValueError, match="magnitude cannot be negative"):
        CalcDraft.model_validate(
            calc("c1", "-2", {}, -2, "N", "newtons", quantity_kind="magnitude")
        )


def test_zero_component_retains_frame_without_inventing_a_physical_direction() -> None:
    checked = check_step(step("s1", "{c1}.", [convention()], calcs=[directed()]), state())
    assert not checked.violations
    entry = checked.entries["c1"]
    assert (entry.quantity_kind, entry.frame, entry.positive) == ("component", "lab", "+x")
    assert physical(entry.value, entry.positive) is None
    assert value_matches(Expected("zero component", 0, "N"), [entry])
    assert not value_matches(Expected("force", 1, "N", direction="+x"), [entry])


@pytest.mark.parametrize(
    "variant", ["unrelated", "coffee", "reversed", "late", "frame", "zero", "axes", "after_result"]
)
def test_irrelevant_or_late_convention_cannot_authorize_a_component(variant: str) -> None:
    arrow = convention()
    draws = [arrow]
    if variant == "unrelated":
        arrow["label"] = "+ (A->B)"
    elif variant == "coffee":
        arrow["label"] = "+ coffee"
    elif variant == "reversed":
        arrow["num"][2]["v"] = 50
    elif variant == "late":
        arrow["at"] = 0.5
    elif variant == "frame":
        arrow["frame"] = "other"
    elif variant == "zero":
        arrow["num"][2]["v"] = 100
    elif variant == "axes":
        draws = [
            item(
                "axes",
                "axes",
                {"x": 100, "y": 100, "w": 300, "h": 200},
                {"xlabel": "t", "ylabel": "v"},
                at=0,
            )
        ]
    elif variant == "after_result":
        draws = [math("result", "{c1}"), arrow]
    checked = check_step(step("s1", "{c1}.", draws, calcs=[directed()]), state())
    assert checked.fatal and any(v.rule == "sign" for v in checked.violations)


def test_only_displayed_axes_are_available_in_later_steps() -> None:
    context = state()
    earlier = check_step(step("s1", "Right is our positive direction.", [convention()]), context)
    assert not earlier.violations
    commit(context, earlier)
    assert not check_step(step("s2", "{c1}.", calcs=[directed()]), context).violations
    y = directed()
    y["positive"] = "+y"
    assert check_step(step("s2", "{c1}.", calcs=[y]), context).fatal


def test_opposite_conventions_are_independent_between_explicit_frames() -> None:
    context = state()
    first = check_step(step("s1", "{c1}.", [convention()], calcs=[directed(2)]), context)
    commit(context, first)
    other = calc("c2", "F", {"F": -2}, -2, "N", "newtons", "-x", frame="other")
    arrow = item(
        "other-conv",
        "arrow",
        {"x1": 300, "y1": 500, "x2": 100, "y2": 500},
        label="positive -x",
        frame="other",
        at=0,
    )
    checked = check_step(step("s2", "{c2}.", [arrow], calcs=[other]), context)
    assert not checked.violations


def test_persistent_invalid_sign_cannot_finish_as_a_verified_lesson() -> None:
    raw = step("s1", "{c1}.", calcs=[directed()])
    fake = FakeLLM([draft_json([raw]), json.dumps({"steps": [raw]})])
    metrics = Metrics()

    async def go() -> None:
        async for _ in generate_lesson(Source(type="problem", text="Find force."), fake, metrics):
            pass

    with pytest.raises(LessonError):
        asyncio.run(go())
    assert metrics.lesson is None and metrics.fixes == 1 and metrics.fixes_failed == 1
    assert metrics.state is not None and not metrics.state.ledger


@pytest.mark.parametrize(
    "expr,values", [("0.5*m*v^2", {"m": 2, "v": 3}), ("F", {"F": 500}), ("500", {})]
)
def test_literals_and_ungrounded_inputs_do_not_authorize_raw_physical_numbers(
    expr: str, values: dict[str, float]
) -> None:
    raw = step(
        "s1",
        "The force is 500 newtons.",
        calcs=[calc("c1", expr, values, 9 if "0.5" in expr else 500, "N", "newtons")],
    )
    assert any(v.rule == "number" for v in check_step(raw, state()).violations)


def test_previous_calcs_cannot_authorize_later_raw_results() -> None:
    context = state()
    earlier = check_step(
        step("s1", "{c1}.", calcs=[calc("c1", "0.5", {}, 0.5, "J", "joules")]), context
    )
    commit(context, earlier)
    assert any(
        v.rule == "number"
        for v in check_step(step("s2", "The force is 500 newtons."), context).violations
    )


def test_only_problem_data_or_explicit_examples_authorize_raw_numbers() -> None:
    given = step("s1", "The mass is 123.4 kilograms.")
    assert not check_step(given, state("A mass of 123.4 kg rests here.")).violations
    context = state("Explain force.", "topic")
    example = step("s1", "For a hypothetical example, take 123.4 newtons.")
    checked = check_step(example, context)
    assert not checked.violations
    commit(context, checked)
    assert not check_step(step("s2", "Use 123.4 newtons."), context).violations
    assert any(v.rule == "number" for v in check_step(given, state()).violations)
    coefficient = step("s1", "Use half the mass times speed squared.", [math("k", "0.5")])
    assert not check_step(coefficient, state()).violations


@pytest.mark.parametrize(
    "latex,symbols",
    [
        (r"2\Omega", [r"\Omega"]),
        (r"2\mu", [r"\mu"]),
        (r"100\,\Omega", []),
        (r"100\mathrm{\Omega}", []),
        (r"2\,\mu\text{C}", []),
    ],
)
def test_unit_spacing_preserves_coefficient_times_symbol(latex: str, symbols: list[str]) -> None:
    assert formula_symbols(latex) == symbols


@pytest.mark.parametrize("direction,value", [("sideways", 1), (" ", 1), ("+x", 0), ("+x", -1)])
def test_eval_loader_rejects_invalid_or_zero_physical_directions(
    tmp_path: Path, direction: str, value: float
) -> None:
    path = tmp_path / "bank.yaml"
    path.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "p",
                    "topic": "force",
                    "level": "simple",
                    "source": "own",
                    "input": "Find force.",
                    "expected": [
                        {"name": "F", "value": value, "unit": "N", "direction": direction}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="expected direction"):
        load_problems(path)


def test_matcher_fails_closed_even_for_unvalidated_expected_direction() -> None:
    expected = Expected("F", 1, "N")
    object.__setattr__(expected, "direction", "sideways")
    assert not value_matches(expected, [Entry(1, "N", "newtons", True)])
    assert not value_matches(expected, [Entry(1, "N", "newtons", True)], magnitude_only=True)


@pytest.mark.parametrize("direction", [None, [], 2])
def test_expected_direction_must_be_a_string(direction: Any) -> None:
    with pytest.raises(ValueError, match="direction must be a string"):
        Expected("F", 1, "N", direction=direction)


def test_prompt_example_validates_with_required_quantity_metadata() -> None:
    example = system_prompt().split("```json\n")[1].split("```", 1)[0]
    draft = StepDraft.model_validate_json(example)
    assert draft.calcs[0].quantity_kind == "scalar"
    assert draft.calcs[0].positive == draft.calcs[0].frame == ""


@pytest.mark.parametrize(
    "ylabel,positive,ok", [("y", "+y", True), ("x", "+y", False), ("-y", "-y", False)]
)
def test_axes_authorize_only_their_actual_axis_labels(ylabel: str, positive: str, ok: bool) -> None:
    drawing = item(
        "axes",
        "axes",
        {"x": 100, "y": 100, "w": 300, "h": 200},
        {"xlabel": "x", "ylabel": ylabel},
        at=0,
    )
    raw = directed()
    raw["positive"] = positive
    checked = check_step(step("s1", "{c1}.", [drawing], calcs=[raw]), state())
    assert (not checked.fatal) is ok


@pytest.mark.parametrize("tip_y,ok", [(300, True), (700, False)])
def test_physics_y_convention_is_up_in_svg_coordinates(tip_y: float, ok: bool) -> None:
    drawing = item(
        "conv", "arrow", {"x1": 100, "y1": 500, "x2": 100, "y2": tip_y}, label="+y", at=0
    )
    raw = directed()
    raw["positive"] = "+y"
    checked = check_step(step("s1", "{c1}.", [drawing], calcs=[raw]), state())
    assert (not checked.fatal) is ok


def test_eval_cannot_infer_direction_from_a_scalar_or_missing_frame() -> None:
    expected = Expected("F", 2, "N", direction="+x")
    for kind, frame in (("scalar", "lab"), ("magnitude", "lab"), ("component", "")):
        assert not value_matches(expected, [Entry(2, "N", "newtons", True, "+x", kind, frame)])


def test_battery_power_question_and_answer_are_for_ideal_emf() -> None:
    problem = next(p for p in load_problems() if p.id == "hard-kirchhoff-charging")
    assert "power delivered by the ideal emf" in problem.input
    assert "excluding its internal resistor" in problem.input
    answers = {e.name: e.value for e in problem.expected}
    assert answers["P2"] == pytest.approx(-11.5 * answers["I2"], rel=1e-12)
    assert answers["P2"] != pytest.approx(-answers["V_AB"] * answers["I2"])


def test_report_keeps_problem_reasons_and_aggregate_fix_counts_separate() -> None:
    result = Result(
        "p",
        "mechanics",
        "own",
        True,
        None,
        numbers={"F": False},
        fix_reasons={"sign": 2, "symbol": 1},
    )
    report = render_report(
        [result],
        {
            "grading_version": GRADING_VERSION,
            "date": "2026-10-12",
            "model": "fake",
            "thinking": "none",
            "effort": "none",
            "prompt_sha": "test",
        },
    )
    assert "numbers not found among verified calcs: F" in report
    assert "- sign: 2" in report and "- symbol: 1" in report


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_values_have_no_physical_direction(value: float) -> None:
    assert physical(value, "+x") is None


def test_old_direction_scores_are_not_compared_as_the_same_grader() -> None:
    assert "Scoring versions differ" in "\n".join(compare_section([], [], ("v3", "v4"), 3))
