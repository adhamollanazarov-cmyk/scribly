"""Check every `calc` with SymPy before any number is spoken (AGENTS.md §3, rule 4)."""

import math
from dataclasses import dataclass

from app.lesson.models import Calc, Lesson
from app.lesson.safe_expr import ExpressionError, evaluate_text

UNVERIFIED_NOTE = "I could not verify this number."


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
        value = evaluate_text(calc.expr, calc.values)
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
        step.model_copy(update={"warning": "unverified", "say": f"{step.say} {UNVERIFIED_NOTE}"})
        if step.id in unverified and step.warning is None
        else step
        for step in lesson.steps
    ]
    return lesson.model_copy(update={"steps": steps})
