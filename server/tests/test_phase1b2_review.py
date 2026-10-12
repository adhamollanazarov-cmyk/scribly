import math

import pytest

from app.lesson.models import Calc
from app.lesson.verify import verify_calc
from scripts.eval import Problem, load_problems
from tests.hard_reference import reference_answers


@pytest.mark.parametrize("expected", [0, 1000])
def test_cancellation_bound_cannot_verify_an_incorrect_expected_result(expected: float) -> None:
    result = verify_calc(
        Calc(id="c1", expr="a-b+1", values={"a": 1e16, "b": 1e16}, expected=expected, unit="N")
    )
    assert not result.ok
    assert result.value == 1


@pytest.mark.parametrize("expected,ok", [(0, False), (1e-13, True)])
def test_small_but_real_difference_keeps_its_value_and_sign(expected: float, ok: bool) -> None:
    result = verify_calc(
        Calc(
            id="c1", expr="a-b", values={"a": 1, "b": 0.9999999999999}, expected=expected, unit="N"
        )
    )
    assert result.ok is ok
    assert result.value is not None and math.isclose(result.value, 1e-13, rel_tol=1e-12)


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("a-b+1", 1),
        ("cos(pi/2)+q", 1e-200),
        ("a+q-a", 1e-300),
    ],
)
def test_precise_recheck_preserves_representable_residuals(expr: str, expected: float) -> None:
    values = {"a": 1e16, "b": 1e16, "q": 1e-200 if "cos" in expr else 1e-300}
    result = verify_calc(Calc(id="c1", expr=expr, values=values, expected=expected, unit="N"))
    assert result.ok
    assert result.value is not None and math.isclose(result.value, expected, rel_tol=1e-12)


HARD = [p for p in load_problems() if p.source == "hard"]


@pytest.mark.parametrize(
    "expr",
    [
        "(exp(-10000)+1-1)^0.01",
        "(0.1+0.2-0.3)^0.001",
        "(cos(pi/2))^0.001",
    ],
)
def test_unsafe_underflow_or_unstable_recheck_is_not_a_verified_zero(expr: str) -> None:
    result = verify_calc(Calc(id="c1", expr=expr, values={}, expected=0, unit="N"))
    # Exact decimal cancellation may give zero; amplified numerical noise may not
    # be accepted as an arbitrary nonzero result or silently authorize an expected zero.
    if "exp" in expr:
        assert not result.ok and result.value is None
    else:
        assert result.value is None or result.value == 0


@pytest.mark.parametrize("problem", HARD, ids=[p.id for p in HARD])
def test_hard_answers_against_independent_exact_input_solutions(problem: Problem) -> None:
    references = reference_answers()[problem.id]
    assert set(references) == {e.name for e in problem.expected}
    for expected in problem.expected:
        expression, unit, positive = references[expected.name]
        value = float(expression.evalf(50))
        direction = positive
        if positive and value < 0:
            direction = {"A->B": "B->A", "+x": "-x", "+y": "-y", "up the slope": "down the slope"}[
                positive
            ]
        actual = abs(value) if expected.direction else value
        assert math.isclose(actual, expected.value, rel_tol=1e-12, abs_tol=0), expected.name
        assert unit == expected.unit
        if expected.direction:
            assert direction == expected.direction, expected.name
