import pytest

from app.lesson.lint import (
    extract_givens,
    find_numbers,
    is_unit_token,
    lint_checkpoint_spacing,
    lint_numbers,
    lint_words,
)

PROJECTILE = (
    "A projectile launches from ground level with initial speed u = 20 m/s at theta = 35 "
    "degrees above the horizontal. Take g = 9.81 m/s^2."
)
CAPACITOR = "Plate area A = 0.020 m^2, kappa = 4.0, charge 3.0 nC, mu_k = 0.20 (dimensionless)."


def rules(violations: list) -> list[str]:  # type: ignore[type-arg]
    return [v.rule for v in violations]


def test_word_limit_counts_the_filled_narration() -> None:
    assert lint_words(" ".join(["w"] * 30)) == []
    [v] = lint_words(" ".join(["w"] * 31))
    assert v.rule == "words" and v.fatal and "31 words" in v.message


@pytest.mark.parametrize(
    ("kind", "run", "bad"),
    [
        ("explain", 3, False),
        ("explain", 4, True),
        ("checkpoint", 9, False),
        ("summary", 6, False),
    ],
)
def test_checkpoint_spacing(kind: str, run: int, bad: bool) -> None:
    assert bool(lint_checkpoint_spacing(kind, run)) is bad


def test_givens_record_whether_they_had_a_unit() -> None:
    givens = {g.value: g.has_unit for g in extract_givens(CAPACITOR)}
    assert givens == {0.020: True, 4.0: False, 3.0: True, 0.20: False}


def test_computed_number_in_narration_is_flagged() -> None:
    givens = extract_givens(PROJECTILE)
    [v] = lint_numbers("The range is 38.4 metres.", "say", givens)
    assert v.rule == "number" and not v.fatal and "38.4" in v.message


def test_given_numbers_counts_constants_and_placeholders_are_fine() -> None:
    givens = extract_givens(PROJECTILE)
    text = "At 20 metres per second and 35 degrees, with g = 9.81 m/s², the range is {c5}."
    assert lint_numbers(text, "say", givens) == []
    assert lint_numbers("Two forces act; half of 4 is 2.", "say", givens) == []


def test_rescaled_given_counts_as_given() -> None:
    givens = extract_givens(CAPACITOR)
    assert lint_numbers("Q = 3.0 × 10⁻⁹ C", "label", givens) == []
    assert lint_numbers(r"Q = 3 \times 10^{-9}\,\text{C}", "math", givens, latex=True) == []


def test_given_with_a_unit_needs_its_unit() -> None:
    givens = extract_givens(PROJECTILE)
    [v] = lint_numbers("It starts at 20 and climbs.", "say", givens)
    assert v.rule == "unit"


def test_dimensionless_given_needs_no_unit() -> None:
    givens = extract_givens(CAPACITOR)
    assert lint_numbers("Here mu k is 0.20 and kappa is 4.0.", "say", givens) == []


def test_latex_exponents_and_subscripts_are_not_numbers() -> None:
    found = [f.value for f in find_numbers(r"E = \frac{q}{4\pi\varepsilon_0 r^2} + x_{12}", True)]
    assert found == [4.0]


def test_numbers_in_latex_need_units_too() -> None:
    givens = extract_givens(PROJECTILE)
    assert rules(lint_numbers(r"u = 20", "math", givens, latex=True)) == ["unit"]
    assert lint_numbers(r"u = 20\,\text{m/s}", "math", givens, latex=True) == []
    assert lint_numbers(r"\theta = 35^{\circ}", "math", givens, latex=True) == []


@pytest.mark.parametrize(
    "token",
    [
        "m",
        "m/s²",
        "N·m²/C",
        "nC",
        "μC",
        "microC",
        "kg",
        "Ω",
        "ohms",
        "metres",
        "nanocoulombs",
        "degrees",
        "%",
        "newton",
        "F/m",
        "m/s^2",
        "pF",
        "J",
    ],
)
def test_unit_tokens(token: str) -> None:
    assert is_unit_token(token)


@pytest.mark.parametrize("token", ["and", "lines", "charges", "times", "x", "the"])
def test_not_unit_tokens(token: str) -> None:
    assert not is_unit_token(token)
