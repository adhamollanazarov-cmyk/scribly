"""Reject dangerous syntax before invoking SymPy's eval-based parser."""

from typing import Any

import pytest

from app.lesson import safe_expr


@pytest.mark.parametrize(
    "text",
    [
        "9^9^9^9//1",
        "sqrt(9^9^9^9)//1",
        "1//0",
        "q(1)",
        "1,2",
        "1 if q else 2",
        "q or 1",
        "sin(1,2)",
        "pi(1)",
        "1e999999999999999999999999",
        "-" * 70 + "1",
    ],
)
def test_unsupported_syntax_never_reaches_sympy(text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_parser(*args: Any, **kwargs: Any) -> None:
        pytest.fail("untrusted non-arithmetic syntax reached SymPy")

    monkeypatch.setattr(safe_expr, "parse_expr", forbidden_parser)
    with pytest.raises(safe_expr.ExpressionError):
        safe_expr.evaluate_text(text, {"q": 1.0, "if": 1.0, "else": 1.0, "or": 1.0})


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("cos(0)+tan(0)", 1),
        ("asin(1)+acos(0)", 3.141592653589793),
        ("atan(1)", 0.7853981633974483),
        ("exp(log(2))", 2),
        ("-2^2 + 2^-2", -3.75),
        ("2**3**2", 512),
        (".5 + 1.25E+2", 125.5),
    ],
)
def test_documented_arithmetic_still_works(text: str, expected: float) -> None:
    assert safe_expr.evaluate_text(text, {}) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["sqrt(-1)", "log(0)", "asin(2)", "exp(1000)", "1/0"])
def test_domain_and_overflow_errors_are_expression_errors(text: str) -> None:
    with pytest.raises(safe_expr.ExpressionError):
        safe_expr.evaluate_text(text, {})
