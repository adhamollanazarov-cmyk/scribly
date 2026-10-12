"""Bounded high-precision recheck of numerically ambiguous, already parsed calcs.

Walk the existing allow-listed AST; never substitute/simplify untrusted SymPy trees.
800 digits cover the entire finite binary64 exponent span, including cancellation
between large values and representable subnormal residuals. Contexts are per call.
"""

import math
import sys
from typing import Any

import mpmath
import sympy

from app.lesson.safe_expr import MATH_FUNCTIONS, ExpressionError, parse


def precise_value(text: str, values: dict[str, float]) -> float:
    tree = parse(text, values.keys())
    first = _recheck(tree, values, 800)
    second = _recheck(tree, values, 1000)
    if not math.isclose(first, second, rel_tol=1e-12, abs_tol=0):
        raise ExpressionError("ambiguous calculation is not stable at higher precision")
    return second


def _recheck(tree: sympy.Expr, values: dict[str, float], digits: int) -> float:
    context = mpmath.mp.clone()
    context.dps = digits
    limit = context.mpf(sys.float_info.max)
    minimum = context.mpf(math.ulp(0.0))
    functions = {function: getattr(context, str(function)) for function in MATH_FUNCTIONS}

    def walk(node: sympy.Basic) -> Any:
        if isinstance(node, sympy.Symbol):
            value = context.mpf(repr(values[node.name]))
        elif node == sympy.pi:
            value = context.pi
        elif node == sympy.E:
            value = context.e
        elif isinstance(node, sympy.Rational):
            value = context.mpf(int(node.p)) / int(node.q)
        elif isinstance(node, sympy.Number):
            value = context.mpf(str(node))
        else:
            args = [walk(arg) for arg in node.args]
            if isinstance(node, sympy.Add):
                value = context.fsum(args)
            elif isinstance(node, sympy.Mul):
                value = context.fprod(args)
            elif isinstance(node, sympy.Pow):
                base, exponent = args
                # Reject enormous exponential ranges before high-precision power.
                if base and abs(exponent * context.log(abs(base))) > 10000:
                    raise ValueError("power outside recheck bounds")
                value = context.power(base, exponent)
            elif node.func in functions and len(args) == 1:
                value = functions[node.func](args[0])
            else:
                raise ValueError("unsupported operation")
        if not context.isfinite(value) or context.im(value) or abs(value) > limit:
            raise ValueError("result outside finite real float range")
        # Trigonometric zeros of pi-based angles retain a precision-sized residual.
        # Their arguments have already passed the finite/underflow checks above.
        if node.func in (sympy.sin, sympy.cos, sympy.tan) and abs(value) < minimum:
            return context.mpf(0)
        if (
            value
            and abs(value) < minimum
            and (
                isinstance(node, (sympy.Number, sympy.Symbol, sympy.Mul, sympy.Pow))
                or node.func == sympy.exp
            )
        ):
            raise ValueError("nonzero intermediate underflows the float range")
        return value

    try:
        result = float(walk(tree))
    except (ValueError, TypeError, OverflowError, ZeroDivisionError) as error:
        raise ExpressionError("ambiguous calculation could not be rechecked safely") from error
    if not math.isfinite(result):
        raise ExpressionError("ambiguous calculation is not a finite real number")
    return result + 0.0
