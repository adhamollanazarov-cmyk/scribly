"""Generate a lesson with the model and yield it step by step, each step checked,
verified and filled before the student sees it.

The model streams one lesson draft. As soon as a step is complete it is checked
(stepcheck.py). A step with problems is regenerated once, alone, with the exact list of
problems, while the main stream keeps going. Steps are yielded in order.
"""

import asyncio
import json
import logging
import time
import uuid
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.lesson.claude import LessonLLM, LLMError
from app.lesson.draft import LessonDraft, LessonHeader, StepFix, generation_schema
from app.lesson.lint import LintState, Violation, extract_givens
from app.lesson.models import Lesson, Source, Step
from app.lesson.pipeline import LessonError
from app.lesson.pricing import Usage
from app.lesson.stepcheck import Checked, LessonState, check_step, commit, error_lines
from app.lesson.stream_parse import StepStream

logger = logging.getLogger(__name__)

LESSON_SCHEMA = generation_schema(LessonDraft)
FIX_SCHEMA = generation_schema(StepFix)


@dataclass(frozen=True)
class Header:
    id: str
    title: str
    level: str


@dataclass
class Metrics:
    """What happened while generating one lesson (logs, eval report)."""

    usage: Usage = field(default_factory=Usage)
    started: float = field(default_factory=time.perf_counter)
    first_step_s: float | None = None
    total_s: float | None = None
    retries: int = 0
    fixes: int = 0
    fixes_failed: int = 0
    fix_reasons: Counter[str] = field(default_factory=Counter)  # rules that triggered a fix
    leftovers: list[tuple[str, Violation]] = field(default_factory=list)
    lesson: Lesson | None = None
    final_error: str | None = None
    state: LessonState | None = None


class _RetryLesson(Exception):
    """The attempt failed before any step was shown, so the whole lesson may be retried."""


async def generate_lesson(
    source: Source, llm: LessonLLM, metrics: Metrics | None = None
) -> AsyncIterator[Header | Step]:
    metrics = metrics or Metrics()
    note = ""
    for attempt in range(2):
        state = LessonState(source=source, lint=LintState(givens=extract_givens(source.text)))
        metrics.state = state
        try:
            header: Header | None = None
            async for event in _attempt(source, llm, state, metrics, note):
                if isinstance(event, Header):
                    header = event
                yield event
        except _RetryLesson as e:
            if attempt == 0:
                metrics.retries += 1
                note = str(e)
                logger.warning("Lesson attempt failed before the first step; retrying once")
                continue
            raise LessonError("The lesson could not be generated. Please try again.") from e
        metrics.total_s = time.perf_counter() - metrics.started
        metrics.leftovers = state.leftovers
        if header is not None:
            _finish(header, source, state, metrics)
        return


def _finish(header: Header, source: Source, state: LessonState, metrics: Metrics) -> None:
    try:
        metrics.lesson = Lesson.model_validate(
            {
                "id": header.id,
                "title": header.title,
                "level": header.level,
                "source": source.model_dump(),
                "steps": [s.model_dump() for s in state.steps],
                "calcs": [c.model_dump() for c in state.calcs],
            }
        )
    except ValidationError as e:
        metrics.final_error = "; ".join(error_lines(e))
        logger.error("Generated lesson failed final validation: %d problem(s)", e.error_count())


async def _attempt(
    source: Source, llm: LessonLLM, state: LessonState, metrics: Metrics, note: str
) -> AsyncIterator[Header | Step]:
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    producer = asyncio.create_task(_produce(llm, lesson_request(source, note), metrics, queue))
    shown = 0
    header: Header | None = None  # held back until a step is ready, so a retry is invisible
    try:
        while True:
            kind, payload = await queue.get()
            if kind == "header":
                header = _header(payload)
            elif kind == "step":
                try:
                    ready = [s async for s in _accept(payload, source, llm, state, metrics)]
                except LessonError as e:
                    if shown == 0:
                        raise _RetryLesson("the first step broke the rules twice") from e
                    raise
                for step in ready:
                    if shown == 0:
                        if header is None:
                            raise _RetryLesson("the lesson header was missing")
                        metrics.first_step_s = time.perf_counter() - metrics.started
                        yield header
                    shown += 1
                    yield step
            elif kind == "end":
                if shown == 0:
                    raise _RetryLesson("the lesson had no steps")
                return
            else:
                error: Exception = payload
                if shown == 0:
                    raise _RetryLesson(_describe(error)) from error
                raise LessonError("The lesson stopped early. Please try again.") from error
    finally:
        producer.cancel()


async def _produce(
    llm: LessonLLM, request: str, metrics: Metrics, queue: asyncio.Queue[tuple[str, Any]]
) -> None:
    parser = StepStream()
    try:
        async for chunk in llm.stream(request, LESSON_SCHEMA, metrics.usage):
            header, steps = parser.feed(chunk)
            if header is not None:
                await queue.put(("header", header))
            for raw in steps:
                await queue.put(("step", raw))
        header, steps, _ = parser.finish()
        if header is not None:
            await queue.put(("header", header))
        for raw in steps:
            await queue.put(("step", raw))
        await queue.put(("end", None))
    except Exception as e:  # handed to the consumer, which decides retry vs error
        await queue.put(("error", e))


def _header(payload: dict[str, Any]) -> Header:
    try:
        header = LessonHeader.model_validate(payload)
    except ValidationError as e:
        raise _RetryLesson("lesson header: " + "; ".join(error_lines(e))) from e
    return Header(id=str(uuid.uuid4()), title=header.title, level=header.level)


def _describe(error: Exception) -> str:
    if isinstance(error, LLMError):
        return str(error)
    if isinstance(error, ValueError):
        return "the reply was not complete JSON"
    return type(error).__name__


async def _accept(
    raw: Any, source: Source, llm: LessonLLM, state: LessonState, metrics: Metrics
) -> AsyncIterator[Step]:
    checked = check_step(raw, state)
    if not checked.violations:
        yield commit(state, checked)
        return
    metrics.fixes += 1
    metrics.fix_reasons.update({v.rule for v in checked.violations})
    fixed = await _fix(raw, checked.violations, source, llm, state, metrics)
    if fixed is not None:
        first = check_step(fixed[0], state)
        if not first.fatal:
            yield _commit_after_fix(state, first)
            for raw_next in fixed[1:]:
                nxt = check_step(raw_next, state)
                if nxt.fatal:
                    raise _step_error(nxt)
                yield _commit_after_fix(state, nxt)
            return
    metrics.fixes_failed += 1
    if checked.fatal:
        raise _step_error(checked)
    yield _commit_after_fix(state, checked)


def _commit_after_fix(state: LessonState, checked: Checked) -> Step:
    numbers_left = any(v.rule == "number" for v in checked.violations)
    return commit(state, checked, unverified=numbers_left)


def _step_error(checked: Checked) -> LessonError:
    rules = sorted({v.rule for v in checked.violations if v.fatal})
    logger.error("Step failed after its fix: rules=%s", ",".join(rules))
    return LessonError("A lesson step could not be built correctly. Please try again.")


async def _fix(
    raw: Any,
    problems: list[Violation],
    source: Source,
    llm: LessonLLM,
    state: LessonState,
    metrics: Metrics,
) -> list[Any] | None:
    """One regeneration of one step. None if the call or its JSON failed."""
    text = ""
    try:
        async for chunk in llm.stream(
            fix_request(raw, problems, source, state), FIX_SCHEMA, metrics.usage
        ):
            text += chunk
        data = json.loads(text)
    except (LLMError, ValueError) as e:
        logger.warning("Step fix failed: %s", type(e).__name__)
        return None
    steps = data.get("steps") if isinstance(data, dict) else None
    if not isinstance(steps, list) or not 1 <= len(steps) <= 2:
        return None
    return steps


# --- requests -------------------------------------------------------------------------


def _source_block(source: Source) -> str:
    kind = "topic" if source.type == "topic" else "problem"
    return f"The student's {kind}:\n<input>\n{source.text}\n</input>"


def lesson_request(source: Source, note: str = "") -> str:
    text = f"{_source_block(source)}\n\nWrite the lesson draft."
    if note:
        text += f"\n\nA previous attempt failed: {note}. Write the whole lesson again."
    return text


def fix_request(raw: Any, problems: list[Violation], source: Source, state: LessonState) -> str:
    so_far = [d.model_dump(mode="json") for d in state.drafts]
    defined = sorted(state.ledger)
    lines = "\n".join(f"- {p.message}" for p in problems)
    return (
        f"{_source_block(source)}\n\n"
        "The lesson so far, already shown to the student (do not repeat it):\n"
        f"{json.dumps(so_far, ensure_ascii=False, separators=(',', ':'))}\n\n"
        f"Calcs defined so far: {', '.join(defined) or 'none'}.\n\n"
        "This next step was rejected by the server:\n"
        f"{json.dumps(raw, ensure_ascii=False, separators=(',', ':'))}\n\n"
        f"Problems:\n{lines}\n\n"
        "Return the corrected step in `steps`, keeping its id. If a problem asks for a "
        "checkpoint, return a new checkpoint step first (id like s5a) and then the corrected "
        "step. Keep the ids of the calcs this step defines, because later steps may already "
        "use them. Change only what the problems require."
    )
