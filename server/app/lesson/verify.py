"""Check every `calc` with SymPy before any number is spoken (AGENTS.md §3, rule 4)."""

import math
from dataclasses import dataclass

from app.lesson.models import UNVERIFIED_NOTE, Calc, Lesson
from app.lesson.precise import precise_value
from app.lesson.safe_expr import ExpressionError, evaluate_text_with_error

# This bound triggers a precise recheck; uncertainty never authorizes a match or zero.
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
        candidate_bound = ZERO_TOLERANCE * rounding
        relative_match = abs(value - calc.expected) <= calc.rel_tol * abs(calc.expected)
        if (
            not math.isfinite(candidate_bound)
            or abs(value) <= candidate_bound
            or (not relative_match and abs(value - calc.expected) <= candidate_bound)
        ):
            value = precise_value(calc.expr, calc.values)
    except ExpressionError as e:
        return CalcResult(calc.id, ok=False, value=None, error=str(e))
    if abs(value - calc.expected) > calc.rel_tol * abs(calc.expected):
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
