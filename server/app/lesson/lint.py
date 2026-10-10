"""Teaching-rule lint (AGENTS.md §4) for one generated step. Pure functions.

Rules: narration length, checkpoint spacing, symbols introduced by a legend entry before
any formula uses them, no computed numbers written by hand (they must come from the
result ledger), and units on given numbers. Messages are written for the model: the
step fix receives them verbatim.
"""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.lesson.ledger import PLACEHOLDER
from app.lesson.models import MAX_SAY_WORDS, MAX_STEPS_WITHOUT_CHECKPOINT

# --- violations ---------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    rule: str  # words | checkpoint | placeholder | calc | contract | symbol | number | unit
    message: str
    fatal: bool  # True: the lesson cannot be shown with it; False: keep the step, log it


FATAL_RULES = {"words", "checkpoint", "placeholder", "contract"}


def violation(rule: str, message: str) -> Violation:
    return Violation(rule, message, fatal=rule in FATAL_RULES)


# --- narration and pacing -------------------------------------------------------------


def word_count(text: str) -> int:
    return len(text.split())


def lint_words(say_filled: str) -> list[Violation]:
    words = word_count(say_filled)
    if words <= MAX_SAY_WORDS:
        return []
    return [
        violation(
            "words",
            f"say has {words} words after the placeholders are filled in "
            f"(units are spoken); the limit is {MAX_SAY_WORDS}. Aim for 26 or fewer: "
            "shorten it or split the idea into two steps.",
        )
    ]


def lint_checkpoint_spacing(kind: str, run_before: int) -> list[Violation]:
    """`run_before`: steps in a row without a checkpoint just before this one."""
    if kind in ("checkpoint", "summary") or run_before < MAX_STEPS_WITHOUT_CHECKPOINT:
        return []
    return [
        violation(
            "checkpoint",
            f"this would be step {run_before + 1} in a row without a "
            f"checkpoint (at most {MAX_STEPS_WITHOUT_CHECKPOINT}). Return a new "
            "checkpoint step that checks the last ideas, followed by this step.",
        )
    ]


# --- symbols in formulas --------------------------------------------------------------

GREEK = {
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
    "iota",
    "kappa",
    "lambda",
    "mu",
    "nu",
    "xi",
    "rho",
    "sigma",
    "tau",
    "upsilon",
    "phi",
    "chi",
    "psi",
    "omega",
    "Gamma",
    "Delta",
    "Theta",
    "Lambda",
    "Xi",
    "Sigma",
    "Upsilon",
    "Phi",
    "Psi",
    "Omega",
}
GREEK_VARIANTS = {
    "varepsilon": "epsilon",
    "vartheta": "theta",
    "varphi": "phi",
    "varrho": "rho",
    "varsigma": "sigma",
}
SKIP_CONTENT = {"text", "mathrm", "textrm", "mbox", "operatorname", "textbf", "textit", "unit"}
OPERATOR_PREFIX = {"Delta", "delta", "partial", "nabla"}
DECORATORS = {"vec", "mathbf", "boldsymbol", "hat", "bar", "overline", "overrightarrow", "tilde"}
SPACING = re.compile(r"^(?:\s|\\[,;:! ]|~)+")


def formula_symbols(latex: str) -> list[str]:
    """Symbols a LaTeX formula uses, normalized: `\\Phi`, `Q_enc`, `\\epsilon_0`, `v'`.

    Not symbols: numbers, function names (\\sin, \\ln), \\pi, words in \\text{} or
    \\mathrm{}, a differential d (dA, dt), e as a base of ^ (Euler's number), and a unit
    such as `3\\,nC` written right after a number."""
    out: list[str] = []
    i = 0
    while i < len(latex):
        c = latex[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+)", latex[i:])
            if m is None:
                i += 2
                continue
            name = m.group(1)
            i += len(m.group(0))
            if name in SKIP_CONTENT:
                i = _skip_group(latex, i)
            elif name in OPERATOR_PREFIX and _next_is_symbol(latex, i):
                continue
            elif name in GREEK or name in GREEK_VARIANTS:
                i, sym = _with_suffix(latex, i, "\\" + GREEK_VARIANTS.get(name, name))
                out.append(sym)
            continue
        if c.isalpha():
            if _unit_after_number(latex, i):
                i = _letters_end(latex, i)
                continue
            if c == "d" and _next_is_symbol(latex, i + 1):
                i += 1
                continue
            if c == "e" and latex[i + 1 : i + 2] == "^":
                i += 1
                continue
            i, sym = _with_suffix(latex, i + 1, c)
            out.append(sym)
            continue
        i += 1
    return out


def _skip_group(s: str, i: int) -> int:
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s) or s[i] != "{":
        return i
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return j + 1
    return len(s)


def _group_text(s: str, i: int) -> tuple[int, str]:
    end = _skip_group(s, i)
    return end, s[i:end]


def _with_suffix(s: str, i: int, base: str) -> tuple[int, str]:
    primes = ""
    while i < len(s) and s[i] == "'":
        primes += "'"
        i += 1
    sub = ""
    if s[i : i + 1] == "_":
        i += 1
        if s[i : i + 1] == "{":
            i, raw = _group_text(s, i)
        elif s[i : i + 1] == "\\":
            m = re.match(r"\\[A-Za-z]+", s[i:])
            raw = m.group(0) if m else s[i : i + 2]
            i += len(raw)
        else:
            raw = s[i : i + 1]
            i += 1
        sub = _normalize_sub(raw)
    while i < len(s) and s[i] == "'":
        primes += "'"
        i += 1
    return i, base + (f"_{sub}" if sub else "") + primes


def _normalize_sub(raw: str) -> str:
    raw = re.sub(r"\\(?:text|mathrm|textrm|rm|mathit)\s*", "", raw)
    raw = re.sub(r"\\([A-Za-z]+)", lambda m: GREEK_VARIANTS.get(m.group(1), m.group(1)), raw)
    return re.sub(r"[{}\s]", "", raw)


def _next_is_symbol(s: str, i: int) -> bool:
    rest = SPACING.sub("", s[i:])
    if rest[:1].isalpha():
        return True
    m = re.match(r"\\([A-Za-z]+)", rest)
    name = m.group(1) if m else ""
    return name in GREEK or name in GREEK_VARIANTS or name in DECORATORS


def _letters_end(s: str, i: int) -> int:
    while i < len(s) and s[i].isalpha():
        i += 1
    return i


def _unit_after_number(s: str, i: int) -> bool:
    """`3\\,nC` or `9.81~m`: letters after a number and explicit spacing are a unit."""
    before = s[:i]
    m = re.search(r"\d(?:\s|\\[,;: ]|~)+$", before)
    return bool(m) and is_unit_token(s[i : _letters_end(s, i)])


def legend_symbols(symbol_latex: str) -> set[str]:
    return set(formula_symbols(symbol_latex))


def lint_symbols(math_latex: str, prim_id: str, defined: set[str]) -> list[Violation]:
    missing = sorted({s for s in formula_symbols(math_latex) if s not in defined})
    if not missing:
        return []
    names = ", ".join(missing)
    return [
        violation(
            "symbol",
            f"math {prim_id} uses {names} before a symbol legend entry "
            "defines it. Add a symbol item (symbol, meaning, SI unit) earlier: in an "
            "earlier step, or before this item in the same draw list.",
        )
    ]


# --- numbers and units ----------------------------------------------------------------

SI_PREFIXES = ("p", "n", "μ", "µ", "u", "m", "c", "k", "M", "G")
SPELLED_PREFIXES = ("pico", "nano", "micro", "milli", "centi", "kilo", "mega", "giga")
UNIT_SYMBOLS = {
    "m",
    "s",
    "g",
    "N",
    "C",
    "V",
    "Ω",
    "A",
    "J",
    "W",
    "F",
    "Hz",
    "K",
    "Pa",
    "T",
    "H",
    "Wb",
    "rad",
    "eV",
    "L",
    "min",
    "h",
    "mol",
    "ohm",
    "ohms",
    "%",
    "°",
    "deg",
}
SPOKEN_UNITS = {
    "meter",
    "metre",
    "second",
    "gram",
    "newton",
    "coulomb",
    "volt",
    "ohm",
    "amp",
    "ampere",
    "joule",
    "watt",
    "farad",
    "hertz",
    "kelvin",
    "pascal",
    "tesla",
    "henry",
    "weber",
    "radian",
    "degree",
    "percent",
    "electronvolt",
    "liter",
    "litre",
    "minute",
    "hour",
    "mole",
}
SUPERSCRIPTS = "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"


def is_unit_token(token: str) -> bool:
    token = token.strip().strip(".,;:!?)(")
    if not token:
        return False
    word = token.lower()
    for prefix in SPELLED_PREFIXES:
        if word.startswith(prefix) and len(word) > len(prefix):
            word = word[len(prefix) :]
            break
    if word.rstrip("s") in SPOKEN_UNITS or word in SPOKEN_UNITS:
        return True
    parts = [p for p in re.split(rf"[/·*^()\-\d{SUPERSCRIPTS}²³]+", token) if p]
    return bool(parts) and all(_unit_part(p) for p in parts)


def _unit_part(part: str) -> bool:
    if part in UNIT_SYMBOLS or part == "°C":
        return True
    for prefix in (*SPELLED_PREFIXES, *SI_PREFIXES):
        if part.startswith(prefix) and part[len(prefix) :] in UNIT_SYMBOLS:
            return True
    return False


@dataclass(frozen=True)
class Given:
    value: float
    has_unit: bool


@dataclass(frozen=True)
class Found:
    value: float
    after: str  # the text right after the number, for the unit check


NUMBER = r"(?<![A-Za-z_\d.\\])(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
TEXT_SCI = re.compile(
    rf"({NUMBER})\s*[×x*]\s*10\s*(?:\^\s*\(?\s*([-−]?\d+)\s*\)?|([⁻{SUPERSCRIPTS[:-1]}]+))"
)
LATEX_SCI = re.compile(rf"({NUMBER})\s*\\(?:times|cdot)\s*10\s*\^\s*\{{?\s*([-−]?\d+)\s*\}}?")
PLAIN_NUMBER = re.compile(NUMBER)


def _superscript_int(text: str) -> int:
    return int(text.translate(str.maketrans(SUPERSCRIPTS, "0123456789-")))


def find_numbers(text: str, latex: bool = False) -> list[Found]:
    """Numbers written in text or LaTeX, with what follows each one. Scientific forms
    (3.0 × 10⁻⁹, 3\\times10^{-9}, 3e-9) are one number; subscripts and exponents are not
    numbers of their own."""
    # Every blanking below keeps the length, so `after` is read from `original`.
    original = PLACEHOLDER.sub(_blank, text)
    found: list[Found] = []

    def sci(m: re.Match[str]) -> str:
        if latex:
            power = int(m.group(2).replace("−", "-"))
        else:
            power = (
                int(m.group(2).replace("−", "-")) if m.group(2) else _superscript_int(m.group(3))
            )
        found.append(Found(float(m.group(1)) * 10.0**power, original[m.end() : m.end() + 40]))
        return _blank(m)

    text = (LATEX_SCI if latex else TEXT_SCI).sub(sci, original)
    if latex:
        text = re.sub(r"[_^]\s*(\{[^{}]*\}|\\[A-Za-z]+|.)", _blank, text)
        text = re.sub(r"\\[A-Za-z]+", _blank, text)
    else:
        text = re.sub(r"\^\s*\(?-?\d+\)?", _blank, text)  # m^2
    for m in PLAIN_NUMBER.finditer(text):
        found.append(Found(float(m.group(0)), original[m.end() : m.end() + 40]))
    return found


def _blank(match: re.Match[str]) -> str:
    return " " * len(match.group(0))


def unit_follows(after: str, latex: bool) -> bool:
    if latex:
        after = SPACING.sub("", after)
        m = re.match(r"\\(?:text|mathrm|unit)\s*\{([^{}]*)\}", after)
        if m:
            return True
        if re.match(r"(\^\s*\{?\\circ|\\%|°)", after):
            return True
        letters = re.match(r"[A-Za-zΩμ°%]+", after)
        return letters is not None and is_unit_token(letters.group(0))
    if after[:1] in ("%", "°"):
        return True
    word = re.match(r"\s*([^\s,;:!?]+)", after)
    return word is not None and is_unit_token(word.group(1))


def extract_givens(source: str) -> list[Given]:
    return [Given(f.value, unit_follows(f.after, latex=False)) for f in find_numbers(source)]


CONSTANTS = (
    9.8,
    9.81,
    8.85e-12,
    8.854e-12,
    8.99e9,
    9.0e9,
    1.6e-19,
    1.602e-19,
    3.0e8,
    6.63e-34,
    9.11e-31,
    6.67e-11,
    1.26e-6,
    3.14,
    3.1416,
    2.718,
)


def _same(a: float, b: float, rel: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=0.0)


def matching_given(value: float, givens: Iterable[Given]) -> Given | None:
    """A given equal to the value, allowing SI-prefix rescaling (3 nC -> 3e-9 C)."""
    value = abs(value)
    givens = list(givens)
    for given in givens:
        if _same(abs(given.value), value):
            return given
    for given in givens:
        g = abs(given.value)
        if g and value and any(_same(value, g * 10.0**k) for k in range(-15, 16)):
            return given
    return None


def is_allowed_constant(value: float) -> bool:
    value = abs(value)
    if value <= 12 and (value * 4).is_integer():
        return True  # small counts, halves and quarters
    if value >= 10 and math.log10(value).is_integer():
        return True  # 10, 100, 1000: conversions
    return any(_same(value, c, rel=0.01) for c in CONSTANTS)


def is_angle(found: Found) -> bool:
    multiple = found.value <= 360 and (found.value / 15).is_integer()
    return multiple and bool(re.match(r"\s*(°|\^\s*\{?\\circ|degree)", found.after))


def lint_numbers(
    text: str, where: str, givens: list[Given], latex: bool = False, check_units: bool = True
) -> list[Violation]:
    out: list[Violation] = []
    for found in find_numbers(text, latex):
        given = matching_given(found.value, givens)
        if given is not None:
            small = abs(found.value) <= 12 and float(found.value).is_integer()
            if (
                check_units
                and given.has_unit
                and not small
                and not unit_follows(found.after, latex)
            ):
                out.append(
                    violation(
                        "unit", f"{where}: the given {found.value:g} needs its unit right after it"
                    )
                )
            continue
        if is_allowed_constant(found.value) or is_angle(found):
            continue
        out.append(
            violation(
                "number",
                f"{where}: {found.value:g} is not a given number. Every "
                "computed number must come from a calc placeholder such as {c3} or "
                "{c3:2sf}, so it is verified.",
            )
        )
    return out


# --- per-step state -------------------------------------------------------------------


@dataclass
class LintState:
    givens: list[Given]
    defined_symbols: set[str] = field(default_factory=set)
    run_without_checkpoint: int = 0
