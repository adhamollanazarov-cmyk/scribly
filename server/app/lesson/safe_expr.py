"""Parse and evaluate math expressions from untrusted text (AI output, screenshots).

SymPy's parser calls eval(), so input is allow-listed before it reaches the parser.
"""

import math
import re
from collections.abc import Callable, Iterable, Mapping
from tokenize import TokenError
from typing import Any

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    parse_expr,
    standard_transformations,
)

MAX_LENGTH = 200
ALLOWED_CHARS = re.compile(r"^[A-Za-z0-9_+\-*/^().,\s]*$")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
ATTRIBUTE_ACCESS = re.compile(r"\.\s*[A-Za-z_]")
FUNCTIONS: dict[str, Any] = {
    "sqrt": sympy.sqrt,
    "sin": sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "asin": sympy.asin,
    "acos": sympy.acos,
    "atan": sympy.atan,
    "exp": sympy.exp,
    "log": sympy.log,
    "pi": sympy.pi,
    "E": sympy.E,
}
# Names the parser itself emits: auto_number/auto_symbol, and evaluate=False, which
# rewrites operators as Add/Mul/Pow calls. User text can never name these (allow-list).
PARSER_NAMES: dict[str, Any] = {
    "Integer": sympy.Integer,
    "Float": sympy.Float,
    "Rational": sympy.Rational,
    "Symbol": sympy.Symbol,
    "Add": sympy.Add,
    "Mul": sympy.Mul,
    "Pow": sympy.Pow,
}


class ExpressionError(ValueError):
    """The expression is malformed, unsafe, or does not evaluate to a finite number."""


def parse(text: str, variables: Iterable[str]) -> sympy.Expr:
    names = set(variables)
    _check_text(text, names)
    local_dict = {name: sympy.Symbol(name) for name in names}
    global_dict = {"__builtins__": {}, **PARSER_NAMES, **FUNCTIONS}
    try:
        expr = parse_expr(
            text,
            local_dict=local_dict,
            global_dict=global_dict,
            transformations=(*standard_transformations, convert_xor),
            evaluate=False,
        )
    except (SyntaxError, TokenError, TypeError, ValueError, AttributeError, NameError) as e:
        raise ExpressionError(f"cannot parse {text!r}") from e
    if not isinstance(expr, sympy.Expr):
        raise ExpressionError(f"{text!r} is not a math expression")
    return expr


def evaluate(expr: sympy.Expr, values: Mapping[str, float]) -> float:
    """Evaluate with plain floats. Never let SymPy simplify untrusted input: rebuilding
    `9^9^9^9` with evaluation on makes it compute a number with millions of digits."""
    missing = {str(s) for s in expr.free_symbols} - set(values)
    if missing:
        raise ExpressionError(f"no value for {sorted(missing)}")
    try:
        result = _to_float(expr, values)
    except (ValueError, OverflowError, ZeroDivisionError) as e:
        raise ExpressionError("expression does not evaluate to a finite real number") from e
    if not math.isfinite(result):
        raise ExpressionError("expression does not evaluate to a finite real number")
    return result


MATH_FUNCTIONS: dict[Any, Callable[[float], float]] = {
    sympy.sin: math.sin,
    sympy.cos: math.cos,
    sympy.tan: math.tan,
    sympy.asin: math.asin,
    sympy.acos: math.acos,
    sympy.atan: math.atan,
    sympy.exp: math.exp,
    sympy.log: math.log,
}


def _to_float(expr: sympy.Basic, values: Mapping[str, float]) -> float:
    if isinstance(expr, sympy.Symbol):
        return float(values[expr.name])
    if isinstance(expr, sympy.Number) or expr in (sympy.pi, sympy.E):
        return float(expr)
    args = [_to_float(arg, values) for arg in expr.args]
    if isinstance(expr, sympy.Add):
        return math.fsum(args)
    if isinstance(expr, sympy.Mul):
        return math.prod(args)
    if isinstance(expr, sympy.Pow):
        base, exponent = args
        if base == 0 and exponent < 0:
            raise ZeroDivisionError("division by zero")
        return math.pow(base, exponent)
    if expr.func in MATH_FUNCTIONS and len(args) == 1:
        return MATH_FUNCTIONS[expr.func](args[0])
    raise ValueError(f"unsupported operation {expr.func}")


def evaluate_text(text: str, values: Mapping[str, float]) -> float:
    return evaluate(parse(text, values.keys()), values)


def _check_text(text: str, names: set[str]) -> None:
    if len(text) > MAX_LENGTH:
        raise ExpressionError(f"expression is longer than {MAX_LENGTH} characters")
    if not ALLOWED_CHARS.match(text) or "__" in text or ATTRIBUTE_ACCESS.search(text):
        raise ExpressionError(f"{text!r} contains characters that are not allowed")
    for match in IDENTIFIER.finditer(text):
        name = match.group()
        if name not in names and name not in FUNCTIONS and not _is_exponent(text, match):
            raise ExpressionError(f"unknown name {name!r}")


def _is_exponent(text: str, match: re.Match[str]) -> bool:
    """The `e9` in `3e9` (or `e` in `3e-9`) is part of a number, not a name."""
    after_digit = match.start() > 0 and text[match.start() - 1] in "0123456789."
    return after_digit and re.fullmatch(r"[eE]\d*", match.group()) is not None
