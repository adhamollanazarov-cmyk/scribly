import pytest

from app.lesson.ledger import (
    Entry,
    LedgerError,
    Spec,
    answer_value,
    fill,
    format_number,
    parse_spec,
    render,
    unit_latex,
    unit_text,
)

FLUX = Entry(338.8299, "N*m**2/C", "newton meters squared per coulomb", verified=True)
CAP = Entry(1.7708e-10, "F", "farads", verified=True)
LEDGER = {"c1": FLUX, "c2": CAP, "c3": Entry(1.99, "%", "percent", True)}


@pytest.mark.parametrize(
    ("value", "spec", "expected"),
    [
        (338.8299, "3sf", "339"),
        (338.8299, "4sf", "338.8"),
        (3.205858, "3sf", "3.21"),
        (38.315703, "3sf", "38.3"),
        (0.5991828, "3sf", "0.599"),
        (1348.16, "3sf", "1350"),
        (2.0, "3sf", "2.00"),
        (0.0, "3sf", "0"),
        (-9.56232e-9, "3sf", "-9.56 × 10⁻⁹"),
        (1.7708e-10, "2sf", "1.8 × 10⁻¹⁰"),
        (12345.0, "3sf", "1.23 × 10⁴"),
        (3.14159, "2dp", "3.14"),
        (2.0 / 3.0, "2dp", "0.67"),
    ],
)
def test_format_number_text(value: float, spec: str, expected: str) -> None:
    assert format_number(value, parse_spec(spec), "text") == expected


def test_format_number_spoken_and_latex_scientific() -> None:
    spec = Spec(3, "sf")
    assert format_number(1.7708e-10, spec, "spoken") == "1.77 times ten to the minus 10"
    assert format_number(1.7708e-10, spec, "latex") == r"1.77 \times 10^{-10}"
    assert format_number(-3.2, spec, "spoken") == "minus 3.20"


def test_units_for_board_and_latex() -> None:
    assert unit_text("N*m**2/C") == "N·m²/C"
    assert unit_text("m/s**2") == "m/s²"
    assert unit_text("ohm") == "Ω"
    assert unit_text("1") == ""
    assert unit_latex("N*m**2/C") == r"N\cdot m^{2}/C"
    assert unit_latex("C**2/(N*m**2)") == r"C^{2}/(N\cdot m^{2})"


def test_render_attaches_the_unit_for_each_context() -> None:
    spec = Spec(3, "sf")
    assert render(FLUX, spec, "spoken") == "339 newton meters squared per coulomb"
    assert render(FLUX, spec, "text") == "339 N·m²/C"
    assert render(FLUX, spec, "latex") == r"339\,\mathrm{N\cdot m^{2}/C}"
    assert render(LEDGER["c3"], spec, "text") == "1.99%"
    assert render(LEDGER["c3"], spec, "latex") == r"1.99\%"


def test_fill_replaces_every_placeholder_and_reports_ids() -> None:
    text, used, errors = fill("Flux {c1} and C = {c2:2sf}.", LEDGER, "text")

    assert text == "Flux 339 N·m²/C and C = 1.8 × 10⁻¹⁰ F."
    assert used == {"c1", "c2"} and errors == []


def test_same_result_is_identical_everywhere() -> None:
    spoken = fill("{c1}", LEDGER, "spoken")[0]
    board = fill("{c1}", LEDGER, "text")[0]
    assert spoken.split()[0] == board.split()[0] == "339"


def test_latex_groups_are_not_placeholders() -> None:
    text, used, errors = fill(r"\frac{Q}{\varepsilon_0} = {c1}", LEDGER, "latex")

    assert text.startswith(r"\frac{Q}{\varepsilon_0} = 339")
    assert used == {"c1"} and errors == []


def test_unknown_calc_and_bad_format_are_errors() -> None:
    _, used, errors = fill("{c9} and {c1:3xx}", LEDGER, "text")

    assert used == set()
    assert "{c9} names no calc" in errors[0]
    assert "bad format '3xx'" in errors[1]


def test_answer_value_is_the_value_as_shown() -> None:
    assert answer_value("{c1:2sf}", LEDGER) == (340.0, "N·m²/C", {"c1"})
    assert answer_value("{c3}", LEDGER)[1] == "%"
    with pytest.raises(LedgerError, match="exactly one placeholder|must be one placeholder"):
        answer_value("339", LEDGER)
    with pytest.raises(LedgerError, match="names no calc"):
        answer_value("{c7}", LEDGER)
