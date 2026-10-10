"""Calc grammar errors must tell the model exactly what to write instead."""

import pytest

from app.lesson.models import Calc
from app.lesson.safe_expr import ExpressionError, evaluate_text
from app.lesson.verify import verify_calc


@pytest.mark.parametrize(
    ("expr", "values", "hint"),
    [
        ("abs(Ea - Ee)/Ee", {"Ea": 1.0, "Ee": 2.0}, "abs is not supported"),
        ("Min(x, 1/x**2)", {"x": 0.5}, "Min is not supported"),
        ("Max(a, b)", {"a": 1.0, "b": 2.0}, "Max is not supported"),
        ("Piecewise(a)", {"a": 1.0}, "Piecewise is not supported"),
        ("ln(a)", {"a": 2.0}, "use log(x)"),
        ("floor(a)", {"a": 2.5}, "neither a value name nor an allowed function"),
    ],
)
def test_unsupported_names_get_an_actionable_message(
    expr: str, values: dict[str, float], hint: str
) -> None:
    with pytest.raises(ExpressionError) as err:
        evaluate_text(expr, values)
    assert hint in str(err.value)
    assert "allowed: + - * / ^ ( )" in str(err.value) and "sqrt" in str(err.value)


def test_lambda_as_a_name_is_explained() -> None:
    with pytest.raises(ExpressionError, match="lambda is a reserved word: name the value lam"):
        evaluate_text("lambda/(2*pi*eps0*r)", {"lam": 2e-9, "eps0": 8.854e-12, "r": 0.1})


def test_lam_is_the_supported_spelling() -> None:
    value = evaluate_text("lam/(2*pi*eps0*r)", {"lam": 2e-9, "eps0": 8.854e-12, "r": 0.1})
    assert value == pytest.approx(359.5097, rel=1e-6)


def test_positive_form_replaces_abs_for_the_dipole_error() -> None:
    calc = Calc(
        id="c3", expr="100*(1-(1-a^2/x^2)^2)", values={"a": 0.01, "x": 0.1}, expected=1.99, unit="%"
    )
    assert verify_calc(calc).ok


def test_unsupported_syntax_lists_what_is_allowed() -> None:
    with pytest.raises(ExpressionError, match="unsupported expression syntax .allowed"):
        evaluate_text("a // b", {"a": 1.0, "b": 2.0})
