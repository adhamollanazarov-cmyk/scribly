"""Parse and evaluate math expressions from untrusted text (AI output, screenshots).

SymPy's parser calls eval(), so input is allow-listed before it reaches the parser.
"""

import ast
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
MAX_DEPTH = 32
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
    _check_syntax(text)
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
    return evaluate_with_error(expr, values)[0]


def evaluate_with_error(expr: sympy.Expr, values: Mapping[str, float]) -> tuple[float, float]:
    """The value and a first-order bound on its floating-point rounding error. The bound
    tells a true zero (q - q, cos 90°) from a small result: cancelling terms leave noise
    of about the bound, a real result is far larger than it."""
    missing = {str(s) for s in expr.free_symbols} - set(values)
    if missing:
        raise ExpressionError(f"no value for {sorted(missing)}")
    try:
        result, error = _to_float(expr, values)
    except (ValueError, OverflowError, ZeroDivisionError) as e:
        raise ExpressionError("expression does not evaluate to a finite real number") from e
    if not math.isfinite(result):
        raise ExpressionError("expression does not evaluate to a finite real number")
    return result, error


UNIT_ROUNDOFF = 2.0**-53
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
# |f'(x)|, for propagating the error of the argument; asin/acos are capped at |x| = 1.
SLOPES: dict[Any, Callable[[float], float]] = {
    sympy.sin: lambda x: abs(math.cos(x)),
    sympy.cos: lambda x: abs(math.sin(x)),
    sympy.tan: lambda x: 1 + math.tan(x) ** 2,
    sympy.asin: lambda x: 1 / math.sqrt(max(1 - x * x, UNIT_ROUNDOFF)),
    sympy.acos: lambda x: 1 / math.sqrt(max(1 - x * x, UNIT_ROUNDOFF)),
    sympy.atan: lambda x: 1 / (1 + x * x),
    sympy.exp: math.exp,
    sympy.log: lambda x: 1 / abs(x),
}


def _to_float(expr: sympy.Basic, values: Mapping[str, float]) -> tuple[float, float]:
    """(value, rounding error bound)"""
    if isinstance(expr, sympy.Symbol):
        value = float(values[expr.name])
        return value, abs(value) * UNIT_ROUNDOFF
    if isinstance(expr, sympy.Number) or expr in (sympy.pi, sympy.E):
        value = float(expr)
        return value, abs(value) * UNIT_ROUNDOFF
    pairs = [_to_float(arg, values) for arg in expr.args]
    args = [v for v, _ in pairs]
    if isinstance(expr, sympy.Add):
        value = math.fsum(args)
        error = math.fsum(e for _, e in pairs)
    elif isinstance(expr, sympy.Mul):
        value = math.prod(args)
        error = math.fsum(
            e * math.prod(abs(a) for j, a in enumerate(args) if j != i)
            for i, (_, e) in enumerate(pairs)
        )
    elif isinstance(expr, sympy.Pow):
        (base, base_error), (exponent, exponent_error) = pairs
        if base == 0 and exponent < 0:
            raise ZeroDivisionError("division by zero")
        value = math.pow(base, exponent)
        if base == 0:
            error = base_error**exponent if exponent > 0 else 0.0
        else:
            error = abs(exponent * value / base) * base_error
            error += abs(value * math.log(abs(base))) * exponent_error
    elif expr.func in MATH_FUNCTIONS and len(args) == 1:
        value = MATH_FUNCTIONS[expr.func](args[0])
        error = SLOPES[expr.func](args[0]) * pairs[0][1]
    else:
        raise ValueError(f"unsupported operation {expr.func}")
    return value, error + abs(value) * UNIT_ROUNDOFF


def evaluate_text(text: str, values: Mapping[str, float]) -> float:
    return evaluate(parse(text, values.keys()), values)


def evaluate_text_with_error(text: str, values: Mapping[str, float]) -> tuple[float, float]:
    return evaluate_with_error(parse(text, values.keys()), values)


def _check_syntax(text: str) -> None:
    """Only operators SymPy rewrites unevaluated may reach its eval-based parser.

    In particular, FloorDiv leaves its subtree untouched by evaluate=False, allowing
    an input such as `9^9^9^9//1` to perform eager, unbounded integer arithmetic.
    """
    try:
        tree = ast.parse(text.replace("^", "**").strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError) as e:
        raise ExpressionError(f"cannot parse {text!r}") from e

    def check(node: ast.AST, depth: int = 0) -> None:
        if depth > MAX_DEPTH:
            raise ExpressionError("expression is too deeply nested")
        match node:
            case ast.Constant(value=value) if isinstance(value, int | float) and not isinstance(
                value, bool
            ):
                if not math.isfinite(value):
                    raise ExpressionError("numeric literals must be finite")
            case ast.Name():
                pass  # Names have already passed the lexical allow-list.
            case ast.BinOp(left=left, op=op, right=right) if isinstance(
                op, ast.Add | ast.Sub | ast.Mult | ast.Div | ast.Pow
            ):
                check(left, depth + 1)
                check(right, depth + 1)
            case ast.UnaryOp(op=op, operand=operand) if isinstance(op, ast.UAdd | ast.USub):
                check(operand, depth + 1)
            case ast.Call(func=ast.Name(id=name), args=[arg], keywords=[]) if (
                name in FUNCTIONS and name not in ("pi", "E")
            ):
                check(arg, depth + 1)
            case _:
                raise ExpressionError(f"unsupported expression syntax ({ALLOWED_TEXT})")

    check(tree.body)


def _check_text(text: str, names: set[str]) -> None:
    if len(text) > MAX_LENGTH:
        raise ExpressionError(f"expression is longer than {MAX_LENGTH} characters")
    if not ALLOWED_CHARS.match(text) or "__" in text or ATTRIBUTE_ACCESS.search(text):
        raise ExpressionError(f"{text!r} contains characters that are not allowed")
    for match in IDENTIFIER.finditer(text):
        name = match.group()
        if name not in names and name not in FUNCTIONS and not _is_exponent(text, match):
            raise ExpressionError(unknown_name_message(name))


NAME_HINTS = {
    "abs": "abs is not supported: write the expression so its value is already positive, "
    "e.g. 100*(E2 - E1)/E1 with the larger value first",
    "Min": "Min is not supported: split the cases into separate calcs",
    "Max": "Max is not supported: split the cases into separate calcs",
    "Piecewise": "Piecewise is not supported: split the cases into separate calcs",
    "lambda": "lambda is a reserved word: name the value lam",
    "ln": "use log(x) for the natural logarithm",
    "e": "use E for Euler's number, or exp(x)",
}
ALLOWED_TEXT = (
    "allowed: + - * / ^ ( ), numbers, the names in values, and "
    + ", ".join(name for name in FUNCTIONS if name not in ("pi", "E"))
    + ", pi, E"
)


def unknown_name_message(name: str) -> str:
    hint = NAME_HINTS.get(name, f"{name!r} is neither a value name nor an allowed function")
    return f"unknown name {name!r}: {hint} ({ALLOWED_TEXT})"


def _is_exponent(text: str, match: re.Match[str]) -> bool:
    """The `e9` in `3e9` (or `e` in `3e-9`) is part of a number, not a name."""
    after_digit = match.start() > 0 and text[match.start() - 1] in "0123456789."
    return after_digit and re.fullmatch(r"[eE]\d*", match.group()) is not None
