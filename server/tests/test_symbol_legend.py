import pytest

from app.lesson.fixtures import load_fixture
from app.lesson.lint import formula_symbols, legend_symbols, lint_symbols
from app.lesson.models import MathPrim, SymbolPrim
from app.lesson.pipeline import prepare_lesson


@pytest.mark.parametrize(
    ("latex", "symbols"),
    [
        (r"\Phi = \frac{Q}{\varepsilon_0}", [r"\Phi", "Q", r"\epsilon_0"]),
        (r"\Phi = \frac{Q_{\text{enc}}}{\epsilon_{0}}", [r"\Phi", "Q_enc", r"\epsilon_0"]),
        (r"\oint \vec{E} \cdot d\vec{A}", ["E", "A"]),
        (r"\Phi = \oint E\, dA", [r"\Phi", "E", "A"]),
        (r"x(t) = v_0 t \sin\theta", ["x", "t", "v_0", "t", r"\theta"]),
        (r"T \approx 2\pi\sqrt{L/g}", ["T", "L", "g"]),
        (r"\Phi \propto 12\ \text{lines}", [r"\Phi"]),
        (r"q = 3\,nC", ["q"]),
        (r"N(t) = N_0 e^{-t/\tau}", ["N", "t", "N_0", "t", r"\tau"]),
        (r"\Delta v = a \Delta t", ["v", "a", "t"]),
        (r"v' = v_{\max}", ["v'", "v_max"]),
        (r"E = 339\,\mathrm{N\cdot m^{2}/C}", ["E"]),
    ],
)
def test_formula_symbols(latex: str, symbols: list[str]) -> None:
    assert formula_symbols(latex) == symbols


def test_legend_spelling_variants_match() -> None:
    defined = legend_symbols(r"\varepsilon_0") | legend_symbols(r"Q_{\text{enc}}")
    assert lint_symbols(r"\frac{Q_{enc}}{\epsilon_{0}}", "f", defined) == []


def test_missing_symbols_are_listed_for_the_fix() -> None:
    [v] = lint_symbols(r"F = k\frac{q_1 q_2}{r^2}", "coulomb", {"F", "k"})
    assert v.rule == "symbol" and not v.fatal
    assert r"uses q_1, q_2, r before a symbol legend entry" in v.message


def test_golden_fixture_introduces_every_symbol_before_its_formula() -> None:
    lesson, _ = prepare_lesson(load_fixture("gauss_law"))
    defined: set[str] = set()
    problems = []
    for step in lesson.steps:
        for prim in step.draw:
            if isinstance(prim, SymbolPrim):
                defined |= legend_symbols(prim.symbol)
            elif isinstance(prim, MathPrim):
                problems += lint_symbols(prim.latex, prim.id, defined)
    assert problems == []
