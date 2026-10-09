from typing import Any

import pytest

from app.lesson.fixtures import load_fixture
from app.lesson.models import Calc, Lesson
from app.lesson.verify import UNVERIFIED_NOTE, apply_verification, verify_calc, verify_lesson


def calc(**overrides: Any) -> Calc:
    base: dict[str, Any] = {
        "id": "c1",
        "expr": "q/epsilon_0",
        "values": {"q": 3e-9, "epsilon_0": 8.854e-12},
        "expected": 338.8,
        "unit": "N*m**2/C",
        "rel_tol": 0.01,
        "used_in_steps": ["s6"],
    }
    return Calc.model_validate(base | overrides)


def test_matching_value_passes() -> None:
    result = verify_calc(calc())

    assert result.ok
    assert result.value is not None and abs(result.value - 338.83) < 0.01


def test_wrong_expected_value_fails() -> None:
    result = verify_calc(calc(expected=-338.8))

    assert not result.ok
    assert result.error is not None and "expected -338.8" in result.error


def test_value_just_outside_tolerance_fails() -> None:
    assert not verify_calc(calc(expected=338.8 * 1.02)).ok


def test_bad_expression_fails_without_raising() -> None:
    result = verify_calc(calc(expr="q/(epsilon_0"))

    assert not result.ok
    assert result.value is None
    assert result.error is not None and "cannot parse" in result.error


def test_unknown_symbol_fails_without_raising() -> None:
    result = verify_calc(calc(expr="q/k"))

    assert not result.ok and result.error is not None and "unknown name 'k'" in result.error


def test_gauss_fixture_calc_passes() -> None:
    lesson = Lesson.model_validate(load_fixture("gauss_law"))

    assert all(r.ok for r in verify_lesson(lesson))


def test_failed_calc_marks_its_steps_unverified() -> None:
    raw = load_fixture("gauss_law")
    raw["calcs"][0]["expected"] = 999
    lesson = Lesson.model_validate(raw)

    marked = apply_verification(lesson, verify_lesson(lesson))
    by_id = {s.id: s for s in marked.steps}

    assert by_id["s6"].warning == "unverified"
    assert by_id["s6"].say.endswith(UNVERIFIED_NOTE)
    assert all(s.warning is None for s in marked.steps if s.id != "s6")


def test_passing_calcs_leave_lesson_unchanged() -> None:
    lesson = Lesson.model_validate(load_fixture("gauss_law"))

    assert apply_verification(lesson, verify_lesson(lesson)) == lesson


@pytest.mark.parametrize(
    "overrides",
    [
        {"expected": float("nan")},
        {"expected": float("inf")},
        {"expected": float("-inf")},
        {"rel_tol": float("inf")},
    ],
)
def test_non_finite_comparison_inputs_cannot_be_verified(overrides: dict[str, float]) -> None:
    result = verify_calc(calc(**overrides))

    assert not result.ok
    assert result.error is not None and "finite" in result.error


@pytest.mark.parametrize(("expr", "ok"), [("0", True), ("1e-12", False)])
def test_zero_expected_value_has_no_implicit_absolute_tolerance(expr: str, ok: bool) -> None:
    assert verify_calc(calc(expr=expr, expected=0)).ok is ok


def test_tolerance_boundary_is_inclusive() -> None:
    assert verify_calc(calc(expr="1.5", expected=1, rel_tol=0.5)).ok
