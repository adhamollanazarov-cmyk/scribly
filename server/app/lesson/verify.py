"""Check every `calc` with SymPy before any number is spoken (AGENTS.md §3, rule 4)."""

import math
from dataclasses import dataclass

from app.lesson.models import UNVERIFIED_NOTE, Calc, Lesson
from app.lesson.safe_expr import ExpressionError, evaluate_text_with_error

# A result within this many rounding-error bounds of zero is zero: cancelling terms
# (q - q, cos 90°) leave float noise such as 6e-17 that must not reach the board.
ZERO_TOLERANCE = 1e3


@dataclass(frozen=True)
class CalcResult:
    calc_id: str
    ok: bool
    value: float | None
    error: str | None = None


def verify_calc(calc: Calc) -> CalcResult:
    if not math.isfinite(calc.expected) or not math.isfinite(calc.rel_tol):
        return CalcResult(
            calc.id, ok=False, value=None, error="expected value and tolerance must be finite"
        )
    try:
        value, rounding = evaluate_text_with_error(calc.expr, calc.values)
    except ExpressionError as e:
        return CalcResult(calc.id, ok=False, value=None, error=str(e))
    abs_tol = ZERO_TOLERANCE * rounding if math.isfinite(rounding) else 0.0
    if abs(value) <= abs_tol:
        value = 0.0
    if abs(value - calc.expected) > max(calc.rel_tol * abs(calc.expected), abs_tol):
        error = f"computed {value:.6g}, expected {calc.expected:.6g} {calc.unit}"
        return CalcResult(calc.id, ok=False, value=value, error=error)
    return CalcResult(calc.id, ok=True, value=value)


def verify_lesson(lesson: Lesson) -> list[CalcResult]:
    return [verify_calc(calc) for calc in lesson.calcs]


def apply_verification(lesson: Lesson, results: list[CalcResult]) -> Lesson:
    """Mark every step that uses a failed calc as unverified and say so out loud."""
    failed = {r.calc_id for r in results if not r.ok}
    unverified = {s for c in lesson.calcs if c.id in failed for s in c.used_in_steps}
    steps = [
        step.model_copy(
            update={
                "warning": "unverified",
                "say": step.say
                if step.say.endswith(UNVERIFIED_NOTE)
                else f"{step.say} {UNVERIFIED_NOTE}",
            }
        )
        if step.id in unverified
        else step
        for step in lesson.steps
    ]
    return lesson.model_copy(update={"steps": steps})
