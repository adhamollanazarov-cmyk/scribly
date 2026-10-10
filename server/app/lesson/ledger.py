"""Result ledger: the model writes {c1} or {c1:3sf} instead of computed numbers, and the
server fills in the SymPy-verified value with its unit, so a result is identical
everywhere it appears (narration, board, checkpoint, summary)."""

import math
import re
from dataclasses import dataclass
from typing import Literal

CALC_ID = re.compile(r"^c\d+$")
# Calc ids are c1, c2, ... so LaTeX groups such as \frac{Q}{r} are never placeholders.
PLACEHOLDER = re.compile(r"\{(c\d+)(?::([0-9A-Za-z]*))?\}")
FORMAT_SPEC = re.compile(r"^(\d{1,2})(sf|dp)$")
DEFAULT_SIG_FIGS = 3
SCI_HIGH, SCI_LOW = 1e4, 1e-2
SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
NO_SPACE_UNITS = {"%", "°"}

Context = Literal["spoken", "text", "latex"]


@dataclass(frozen=True)
class Entry:
    value: float
    unit: str  # SymPy style, e.g. N*m**2/C; "1" or "" if dimensionless
    unit_spoken: str
    verified: bool


@dataclass(frozen=True)
class Spec:
    digits: int
    mode: Literal["sf", "dp"]


class LedgerError(ValueError):
    """A placeholder names an unknown calc or has a bad format."""


def parse_spec(spec: str | None) -> Spec:
    if not spec:
        return Spec(DEFAULT_SIG_FIGS, "sf")
    match = FORMAT_SPEC.match(spec)
    if not match or int(match.group(1)) == 0 and match.group(2) == "sf":
        raise LedgerError(f"bad format {spec!r}: use e.g. 3sf or 2dp")
    return Spec(int(match.group(1)), "sf" if match.group(2) == "sf" else "dp")


def rounded(value: float, spec: Spec) -> float:
    """The value as the student sees it."""
    if spec.mode == "dp" or value == 0:
        return round(value, spec.digits if spec.mode == "dp" else 0)
    return float(f"{value:.{spec.digits - 1}e}")


def format_number(value: float, spec: Spec, context: Context) -> str:
    if spec.mode == "dp":
        return _signed(f"{abs(value):.{spec.digits}f}", value, context)
    if value == 0:
        return "0"
    magnitude = abs(value)
    if SCI_LOW <= magnitude < SCI_HIGH:
        ndigits = spec.digits - 1 - math.floor(math.log10(magnitude))
        text = f"{round(magnitude, ndigits):.{max(0, ndigits)}f}"
        return _signed(text, value, context)
    mantissa, exponent = f"{magnitude:.{spec.digits - 1}e}".split("e")
    power = int(exponent)
    if context == "spoken":
        text = f"{mantissa} times ten to the {'minus ' if power < 0 else ''}{abs(power)}"
    elif context == "latex":
        text = f"{mantissa} \\times 10^{{{power}}}"
    else:
        text = f"{mantissa} × 10{str(power).translate(SUPERSCRIPT)}"
    return _signed(text, value, context)


def _signed(text: str, value: float, context: Context) -> str:
    if value >= 0:
        return text
    return f"minus {text}" if context == "spoken" else f"-{text}"


POWER = re.compile(r"\*\*(?:\((-?\d+)\)|(-?\d+))")


def _power(match: re.Match[str]) -> str:
    return match.group(1) or match.group(2)


def unit_text(unit: str) -> str:
    """N*m**2/C -> N·m²/C"""
    if unit in ("", "1"):
        return ""
    text = POWER.sub(lambda m: _power(m).translate(SUPERSCRIPT), unit)
    text = re.sub(r"\bohm\b", "Ω", text)
    text = re.sub(r"\bdeg\b", "°", text)
    return text.replace("*", "·")


def unit_latex(unit: str) -> str:
    if unit in ("", "1"):
        return ""
    text = POWER.sub(lambda m: f"^{{{_power(m)}}}", unit)
    text = re.sub(r"\bohm\b", r"\\Omega", text)
    text = re.sub(r"\bdeg\b", r"^{\\circ}", text).replace("%", r"\%")
    return text.replace("*", r"\cdot ")


def render(entry: Entry, spec: Spec, context: Context) -> str:
    number = format_number(entry.value, spec, context)
    if context == "spoken":
        unit = entry.unit_spoken.strip()
        return f"{number} {unit}" if unit else number
    unit = unit_latex(entry.unit) if context == "latex" else unit_text(entry.unit)
    if not unit:
        return number
    if context == "latex":
        return (
            f"{number}\\,\\mathrm{{{unit}}}" if unit not in (r"\%", r"^{\circ}") else number + unit
        )
    return f"{number}{unit}" if unit in NO_SPACE_UNITS else f"{number} {unit}"


def fill(text: str, ledger: dict[str, Entry], context: Context) -> tuple[str, set[str], list[str]]:
    """Replace placeholders. Returns (text, calc ids used, error messages)."""
    used: set[str] = set()
    errors: list[str] = []

    def replace(match: re.Match[str]) -> str:
        calc_id, spec_text = match.group(1), match.group(2)
        entry = ledger.get(calc_id)
        if entry is None:
            errors.append(
                f"placeholder {match.group(0)} names no calc defined in this or an "
                f"earlier step (known: {', '.join(sorted(ledger)) or 'none'})"
            )
            return match.group(0)
        try:
            spec = parse_spec(spec_text)
        except LedgerError as e:
            errors.append(f"placeholder {match.group(0)}: {e}")
            return match.group(0)
        used.add(calc_id)
        return render(entry, spec, context)

    return PLACEHOLDER.sub(replace, text), used, errors


def answer_value(text: str, ledger: dict[str, Entry]) -> tuple[float, str, set[str]]:
    """A number checkpoint answer: exactly one placeholder -> (value shown, unit text, ids)."""
    match = PLACEHOLDER.fullmatch(text.strip())
    if match is None:
        raise LedgerError(
            f"a number checkpoint answer must be one placeholder like {{c3:3sf}}, not {text!r}"
        )
    entry = ledger.get(match.group(1))
    if entry is None:
        raise LedgerError(f"answer {text!r} names no calc defined in this or an earlier step")
    spec = parse_spec(match.group(2))
    return rounded(entry.value, spec), unit_text(entry.unit) or "1", {match.group(1)}


def placeholders(text: str) -> list[str]:
    return [m.group(0) for m in PLACEHOLDER.finditer(text)]
