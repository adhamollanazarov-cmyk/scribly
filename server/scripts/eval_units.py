"""Small, fail-closed SI unit converter for evals. Never evaluates Python or SymPy."""

import ast
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    scale: float
    dimensions: tuple[int, ...]  # kg, m, s, A, K, mol, cd


UNITS = {
    name: Unit(scale, dimensions)
    for name, scale, dimensions in (
        ("1", 1, (0, 0, 0, 0, 0, 0, 0)),
        ("%", 0.01, (0, 0, 0, 0, 0, 0, 0)),
        ("kg", 1, (1, 0, 0, 0, 0, 0, 0)),
        ("g", 0.001, (1, 0, 0, 0, 0, 0, 0)),
        ("m", 1, (0, 1, 0, 0, 0, 0, 0)),
        ("s", 1, (0, 0, 1, 0, 0, 0, 0)),
        ("A", 1, (0, 0, 0, 1, 0, 0, 0)),
        ("K", 1, (0, 0, 0, 0, 1, 0, 0)),
        ("mol", 1, (0, 0, 0, 0, 0, 1, 0)),
        ("cd", 1, (0, 0, 0, 0, 0, 0, 1)),
        ("Hz", 1, (0, 0, -1, 0, 0, 0, 0)),
        ("N", 1, (1, 1, -2, 0, 0, 0, 0)),
        ("J", 1, (1, 2, -2, 0, 0, 0, 0)),
        ("W", 1, (1, 2, -3, 0, 0, 0, 0)),
        ("C", 1, (0, 0, 1, 1, 0, 0, 0)),
        ("V", 1, (1, 2, -3, -1, 0, 0, 0)),
        ("F", 1, (-1, -2, 4, 2, 0, 0, 0)),
        ("ohm", 1, (1, 2, -3, -2, 0, 0, 0)),
    )
}
PREFIXES = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "c": 1e-2,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}


def parse_unit(text: str) -> Unit:
    text = text.strip().replace("Ω", "ohm").replace("µ", "u").replace("μ", "u")
    text = text.replace("·", "*").replace("^", "**")
    if text in UNITS:
        return UNITS[text]
    if len(text) > 120:
        raise ValueError("unit too long")
    try:
        root = ast.parse(text, mode="eval")
    except (SyntaxError, RecursionError) as error:
        raise ValueError("invalid unit") from error
    if sum(1 for _ in ast.walk(root)) > 80:
        raise ValueError("unit too complex")
    return _unit(root.body, 0)


def _unit(node: ast.expr, depth: int) -> Unit:
    if depth > 12:
        raise ValueError("unit too deep")
    if isinstance(node, ast.Name):
        if node.id in UNITS:
            return UNITS[node.id]
        prefix, base = node.id[:1], node.id[1:]
        if prefix in PREFIXES and base in UNITS and base not in {"1", "%", "kg"}:
            unit = UNITS[base]
            return Unit(PREFIXES[prefix] * unit.scale, unit.dimensions)
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value == 1:
        return UNITS["1"]
    if isinstance(node, ast.BinOp):
        left = _unit(node.left, depth + 1)
        if isinstance(node.op, (ast.Mult, ast.Div)):
            right = _unit(node.right, depth + 1)
            sign = 1 if isinstance(node.op, ast.Mult) else -1
            return _bounded(
                left.scale * right.scale**sign,
                tuple(a + sign * b for a, b in zip(left.dimensions, right.dimensions, strict=True)),
            )
        if isinstance(node.op, ast.Pow):
            power = node.right
            sign = 1
            if isinstance(power, ast.UnaryOp) and isinstance(power.op, ast.USub):
                sign, power = -1, power.operand
            if (
                isinstance(power, ast.Constant)
                and type(power.value) is int
                and abs(power.value) <= 12
            ):
                exponent = sign * power.value
                try:
                    return _bounded(
                        left.scale**exponent, tuple(d * exponent for d in left.dimensions)
                    )
                except (OverflowError, ZeroDivisionError) as error:
                    raise ValueError("unit scale out of bounds") from error
    raise ValueError("unsupported unit")


def _bounded(scale: float, dimensions: tuple[int, ...]) -> Unit:
    if not math.isfinite(scale) or scale <= 0 or any(abs(d) > 64 for d in dimensions):
        raise ValueError("unit out of bounds")
    return Unit(scale, dimensions)


def convert(value: float, source: str, target: str) -> float:
    actual, expected = parse_unit(source), parse_unit(target)
    if actual.dimensions != expected.dimensions:
        raise ValueError("incompatible units")
    converted = value * (actual.scale / expected.scale)
    if not math.isfinite(converted):
        raise ValueError("non-finite result")
    return converted
