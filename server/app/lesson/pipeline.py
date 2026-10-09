"""Turn raw lesson JSON into a checked, expanded, verified Lesson. No I/O."""

from typing import Any

from pydantic import ValidationError

from app.lesson.models import Lesson, check_references
from app.lesson.templates import TemplateError, expand_lesson
from app.lesson.verify import CalcResult, apply_verification, verify_lesson


class LessonError(ValueError):
    """The lesson cannot be shown. The message is safe to show to the student."""


def prepare_lesson(raw: dict[str, Any]) -> tuple[Lesson, list[CalcResult]]:
    try:
        lesson = Lesson.model_validate(raw)
    except ValidationError as e:
        raise LessonError(f"lesson JSON is invalid: {e.error_count()} problem(s)") from e
    try:
        lesson = expand_lesson(lesson)
    except TemplateError as e:
        raise LessonError("a drawing template could not be expanded") from e
    problems = check_references(lesson)
    if problems:
        raise LessonError(f"lesson has {len(problems)} broken reference(s)") from ValueError(
            "; ".join(problems)
        )
    results = verify_lesson(lesson)
    return apply_verification(lesson, results), results
