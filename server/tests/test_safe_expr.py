import contextlib
import time

import pytest

from app.lesson.safe_expr import ExpressionError, evaluate, evaluate_text, parse


@pytest.mark.parametrize(
    ("text", "values", "expected"),
    [
        ("q/epsilon_0", {"q": 3e-9, "epsilon_0": 8.854e-12}, 338.83),
        ("2^3 + sqrt(16)", {}, 12.0),
        ("3e-9 * 2", {}, 6e-9),
        ("1.5e3", {}, 1500.0),
        ("sin(pi/2)", {}, 1.0),
        ("E", {"E": 4.0}, 4.0),  # a variable named E wins over Euler's number
    ],
)
def test_evaluates_allowed_expressions(
    text: str, values: dict[str, float], expected: float
) -> None:
    assert evaluate_text(text, values) == pytest.approx(expected, rel=1e-4)


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os').system('echo hi')",
        "q.__class__",
        "(1).real",
        "open('x')",
        "lambda: 1",
        "0if 1else 2",
        "[1, 2]",
        "q; 1",
        "1 +",
        "(1 + 2",
        "x" * 201,
        "nonexistent * 2",
    ],
)
def test_rejects_unsafe_or_malformed_text(text: str) -> None:
    with pytest.raises(ExpressionError):
        evaluate_text(text, {"q": 1.0})


def test_missing_value_is_an_error() -> None:
    expr = parse("q * r", ["q", "r"])

    with pytest.raises(ExpressionError, match="no value for \\['r'\\]"):
        evaluate(expr, {"q": 1.0})


def test_non_finite_result_is_an_error() -> None:
    with pytest.raises(ExpressionError, match="finite"):
        evaluate_text("1/0", {})


def test_huge_power_does_not_hang() -> None:
    start = time.perf_counter()
    with contextlib.suppress(ExpressionError):
        evaluate_text("9^9^9^9", {})

    assert time.perf_counter() - start < 2
