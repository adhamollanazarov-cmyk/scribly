"""Check one generated step against everything before it, and turn it into a contract
Step. Pure: `check_step` never mutates the lesson state; `commit` applies the result.

Order: draft shape -> ids -> calcs (SymPy) -> ledger fill -> teaching lint -> contract
(Pydantic, template expansion, references). Every problem becomes a Violation the
step fix can act on.
"""

import keyword
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.lesson.direction import normalize
from app.lesson.draft import CheckpointDraft, StepDraft, TextArg, contract_primitive
from app.lesson.ledger import CALC_ID, PLACEHOLDER, Context, Entry, LedgerError, answer_value, fill
from app.lesson.lint import (
    LintState,
    Violation,
    displayed_conventions,
    extract_givens,
    legend_symbols,
    lint_checkpoint_spacing,
    lint_numbers,
    lint_sign,
    lint_symbols,
    lint_words,
    violation,
)
from app.lesson.models import (
    UNVERIFIED_NOTE,
    Calc,
    PrimitiveBase,
    Source,
    Step,
    check_step_references,
)
from app.lesson.safe_expr import FUNCTIONS
from app.lesson.templates import TemplateError, expand_step
from app.lesson.verify import CalcResult, verify_calc

LATEX_KEYS = {"latex"}
RAW_KEYS = {"symbol", "expr", "sign", "direction", "orientation"}  # not prose, not filled
DEFAULT_REL_TOL = 0.01
CALC_NAME = re.compile(r"\b(c\d+)\b")
CHECKPOINT_TOLERANCE = 0.02


@dataclass
class LessonState:
    source: Source
    lint: LintState
    ledger: dict[str, Entry] = field(default_factory=dict)
    calcs: list[Calc] = field(default_factory=list)
    calc_results: list[CalcResult] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    drafts: list[StepDraft] = field(default_factory=list)
    drawn: dict[str, PrimitiveBase] = field(default_factory=dict)
    groups: set[str] = field(default_factory=set)
    leftovers: list[tuple[str, Violation]] = field(default_factory=list)


@dataclass
class Checked:
    violations: list[Violation]
    draft: StepDraft | None = None
    step: Step | None = None
    calcs: list[Calc] = field(default_factory=list)
    results: list[CalcResult] = field(default_factory=list)
    entries: dict[str, Entry] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)
    symbols: set[str] = field(default_factory=set)
    conventions: set[tuple[str, str]] = field(default_factory=set)
    drawn_conventions: set[tuple[str, str]] = field(default_factory=set)

    @property
    def fatal(self) -> bool:
        return self.step is None or any(v.fatal for v in self.violations)


def check_step(raw: Any, state: LessonState) -> Checked:
    try:
        draft = StepDraft.model_validate(raw)
    except ValidationError as e:
        return Checked([violation("contract", m) for m in error_lines(e)])
    out = Checked([], draft=draft)
    out.violations += _check_ids(draft, state)
    _check_calcs(draft, state, out)
    out.violations += _lint_signs(draft, state, out)
    ledger = {**state.ledger, **out.entries}
    filled, used, problems = fill_step(draft, ledger)
    out.used = used
    out.violations += [violation("placeholder", p) for p in problems]
    out.violations += lint_words(filled.say)
    out.violations += lint_checkpoint_spacing(draft.kind, state.lint.run_without_checkpoint)
    out.violations += _lint_numbers(draft, state)
    out.violations += _lint_symbols(filled, state, out)
    step, contract_problems, answer_ids = _contract_step(filled, draft, ledger, state)
    out.used |= answer_ids
    out.violations += [violation("contract", p) for p in contract_problems]
    if step is not None and any(not ledger[i].verified for i in out.used if i in ledger):
        step = mark_unverified(step)
    out.step = step
    return out


def commit(state: LessonState, checked: Checked, unverified: bool = False) -> Step:
    """Add a checked step to the lesson. `unverified`: a hand-written number survived the
    fix, so the student is told it is not verified."""
    assert checked.step is not None and checked.draft is not None
    step = mark_unverified(checked.step) if unverified else checked.step
    state.ledger.update(checked.entries)
    state.calcs += checked.calcs
    state.calc_results += checked.results
    state.calcs = [
        c.model_copy(update={"used_in_steps": [*c.used_in_steps, step.id]})
        if c.id in checked.used
        else c
        for c in state.calcs
    ]
    check_step_references(step, state.drawn, state.groups)
    state.lint.defined_symbols |= checked.symbols
    state.lint.conventions |= checked.conventions
    state.lint.drawn_conventions |= checked.drawn_conventions
    state.lint.run_without_checkpoint = (
        0 if step.kind == "checkpoint" else state.lint.run_without_checkpoint + 1
    )
    state.steps.append(step)
    state.drafts.append(checked.draft)
    state.leftovers += [(step.id, v) for v in checked.violations]
    return step


def mark_unverified(step: Step) -> Step:
    if step.warning == "unverified":
        return step
    return step.model_copy(update={"warning": "unverified", "say": f"{step.say} {UNVERIFIED_NOTE}"})


def error_lines(error: ValidationError) -> list[str]:
    lines = []
    for item in error.errors():
        where = ".".join(str(p) for p in item["loc"]) or "step"
        lines.append(f"{where}: {item['msg']}")
    return lines


# --- ids and calcs ----------------------------------------------------------------------


def _check_ids(draft: StepDraft, state: LessonState) -> list[Violation]:
    out = []
    if draft.id in {s.id for s in state.steps}:
        out.append(violation("contract", f"step id {draft.id} is already used"))
    seen = {p.id for s in state.steps for p in s.draw} | state.groups
    for item in draft.draw:
        if item.id in seen:
            out.append(
                violation(
                    "contract",
                    f"draw id {item.id} is already used; ids are unique across the lesson",
                )
            )
        seen.add(item.id)
    return out


def _check_calcs(draft: StepDraft, state: LessonState, out: Checked) -> None:
    for calc in draft.calcs:
        if not CALC_ID.match(calc.id) or calc.id in state.ledger or calc.id in out.entries:
            out.violations.append(
                violation(
                    "contract", f"calc id {calc.id!r} must be c1, c2, ... and unique in the lesson"
                )
            )
            continue
        bad = [v.name for v in calc.values if not _valid_name(v.name)]
        if bad:
            out.violations.append(
                violation(
                    "calc",
                    f"calc {calc.id}: {bad} cannot be value "
                    "names; use plain identifiers that are not Python "
                    "keywords or function names (lam, not lambda)",
                )
            )
            continue
        known = {**state.ledger, **out.entries}
        reserved = [v.name for v in calc.values if CALC_ID.fullmatch(v.name)]
        if reserved:
            out.violations.append(
                violation(
                    "calc",
                    f"calc {calc.id}: {reserved} are reserved ledger names; "
                    "use earlier calc ids only in expr, never in values",
                )
            )
            continue
        values = {v.name: v.value for v in calc.values}
        # Earlier results used by name (c1) come in at full precision, never retyped.
        for name in set(CALC_NAME.findall(calc.expr)) - values.keys():
            if name in known:
                values[name] = known[name].value
        model = Calc(
            id=calc.id,
            expr=calc.expr,
            values=values,
            expected=calc.expected,
            unit=calc.unit or "1",
            rel_tol=DEFAULT_REL_TOL,
        )
        result = verify_calc(model)
        out.calcs.append(model)
        out.results.append(result)
        if not result.ok:
            out.violations.append(violation("calc", f"calc {calc.id}: {result.error}"))
        inputs_ok = all(known[n].verified for n in CALC_NAME.findall(calc.expr) if n in known)
        if result.value is not None:
            verified = result.ok and inputs_ok
            out.entries[calc.id] = Entry(
                result.value,
                model.unit,
                calc.unit_spoken,
                verified,
                calc.positive,
                calc.quantity_kind,
                calc.frame,
            )


def _valid_name(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name) and name not in FUNCTIONS


# --- ledger fill ------------------------------------------------------------------------


def fill_step(draft: StepDraft, ledger: dict[str, Entry]) -> tuple[StepDraft, set[str], list[str]]:
    used: set[str] = set()
    problems: list[str] = []

    def f(text: str, context: Context) -> str:
        filled, ids, errors = fill(text, ledger, context)
        used.update(ids)
        problems.extend(errors)
        return filled

    draw = [
        item.model_copy(
            update={
                "label": f(item.label, "text"),
                "txt": [
                    TextArg(
                        k=a.k,
                        v=a.v
                        if a.k in RAW_KEYS
                        else f(a.v, "latex" if a.k in LATEX_KEYS else "text"),
                    )
                    for a in item.txt
                ],
            }
        )
        for item in draft.draw
    ]
    checkpoints = [
        cp.model_copy(
            update={
                "question": f(cp.question, "text"),
                "choices": [f(c, "text") for c in cp.choices],
                "hint": f(cp.hint, "text"),
                "reexplain_hint": f(cp.reexplain_hint, "text"),
            }
        )
        for cp in draft.checkpoints
    ]
    subtitles = draft.subtitles.model_copy(
        update={"uz": f(draft.subtitles.uz, "text"), "ru": f(draft.subtitles.ru, "text")}
    )
    filled = draft.model_copy(
        update={
            "say": f(draft.say, "spoken"),
            "subtitles": subtitles,
            "draw": draw,
            "checkpoints": checkpoints,
        }
    )
    return filled, used, problems


# --- lint helpers -----------------------------------------------------------------------


def _lint_numbers(draft: StepDraft, state: LessonState) -> list[Violation]:
    # Calc values/literals cannot grant themselves provenance. Only problem data
    # and explicitly labelled hypothetical examples authorize raw physical numbers.
    givens = list(state.lint.givens)
    for previous in [*state.drafts, draft]:
        texts = [previous.say, *(item.label for item in previous.draw)]
        texts += [a.v for item in previous.draw for a in item.txt if a.k == "text"]
        for text in texts:
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                if re.search(r"\b(example|hypothetical|suppose)\b", sentence, re.IGNORECASE):
                    givens += [g for g in extract_givens(sentence) if g.has_unit]
    out = lint_numbers(draft.say, f"step {draft.id} say", givens)
    for lang in ("uz", "ru"):
        text = getattr(draft.subtitles, lang)
        out += lint_numbers(text, f"step {draft.id} subtitles.{lang}", givens, check_units=False)
    for item in draft.draw:
        out += lint_numbers(item.label, f"{item.id} label", givens)
        for arg in item.txt:
            if arg.k not in RAW_KEYS:
                out += lint_numbers(arg.v, f"{item.id} {arg.k}", givens, latex=arg.k in LATEX_KEYS)
    for cp in draft.checkpoints:
        for name, text in (
            ("question", cp.question),
            ("hint", cp.hint),
            ("reexplain_hint", cp.reexplain_hint),
        ):
            out += lint_numbers(text, f"step {draft.id} checkpoint {name}", givens)
        for choice in cp.choices:
            out += lint_numbers(choice, f"step {draft.id} checkpoint choice", givens)
    return out


def _lint_signs(draft: StepDraft, state: LessonState, out: Checked) -> list[Violation]:
    """Match a displayed convention by frame and direction, before first use."""
    annotations: list[tuple[int, float, str, str]] = []
    for index, item in enumerate(draft.draw):
        if not item.frame:
            continue
        directions = displayed_conventions(
            item.type, item.label, {a.k: a.v for a in item.txt}, {a.k: a.v for a in item.num}
        )
        for direction in directions:
            annotations.append((index, item.at, item.frame, direction))
            out.drawn_conventions.add((item.frame, direction))
    problems: list[Violation] = []
    for calc in draft.calcs:
        if calc.quantity_kind in ("scalar", "magnitude"):
            continue
        # Narration can use a result immediately. In this step the convention must
        # start at zero and precede any result annotation in draw-list order.
        first_use = next(
            (
                i
                for i, item in enumerate(draft.draw)
                if any(
                    m.group(1) == calc.id
                    for text in [item.label, *(a.v for a in item.txt)]
                    for m in PLACEHOLDER.finditer(text)
                )
            ),
            len(draft.draw),
        )
        visible = state.lint.drawn_conventions | {
            (frame, direction)
            for index, at, frame, direction in annotations
            if at == 0 and index < first_use
        }
        known = {
            direction
            for frame, direction in state.lint.conventions | out.conventions
            if frame == calc.frame
        }
        canonical = normalize(calc.positive)
        drawn = (calc.frame, canonical) in visible
        problems += lint_sign(calc.id, calc.positive, known, drawn)
        if canonical:
            out.conventions.add((calc.frame, canonical))
    return problems


def _lint_symbols(filled: StepDraft, state: LessonState, out: Checked) -> list[Violation]:
    defined = set(state.lint.defined_symbols)
    problems: list[Violation] = []
    for item in filled.draw:
        args = {a.k: a.v for a in item.txt}
        if item.type == "symbol" and "symbol" in args:
            new = legend_symbols(args["symbol"])
            defined |= new
            out.symbols |= new
        elif item.type == "math" and "latex" in args:
            problems += lint_symbols(args["latex"], item.id, defined)
    return problems


# --- contract ---------------------------------------------------------------------------


def _contract_step(
    filled: StepDraft, draft: StepDraft, ledger: dict[str, Entry], state: LessonState
) -> tuple[Step | None, list[str], set[str]]:
    problems: list[str] = []
    draw: list[dict[str, Any]] = []
    for item in filled.draw:
        try:
            draw.append(contract_primitive(item))
        except ValueError as e:
            problems.append(str(e))
    checkpoint: dict[str, Any] | None = None
    answer_ids: set[str] = set()
    if draft.checkpoints:
        try:
            checkpoint, answer_ids = _contract_checkpoint(
                filled.checkpoints[0], draft.checkpoints[0], ledger
            )
        except LedgerError as e:
            problems.append(str(e))
    raw = {
        "id": filled.id,
        "kind": filled.kind,
        "say": filled.say,
        "draw": draw,
        "subtitles": {"uz": filled.subtitles.uz, "ru": filled.subtitles.ru},
    }
    if checkpoint is not None:
        raw["checkpoint"] = checkpoint
    elif filled.kind == "checkpoint":
        return None, problems, answer_ids
    try:
        step = Step.model_validate(raw, context={"raw_input": True})
        step = expand_step(step)
        step = Step.model_validate(step.model_dump())
    except ValidationError as e:
        problems += [line for line in error_lines(e) if "the limit is" not in line]
        return None, problems, answer_ids
    except TemplateError as e:
        return None, [*problems, str(e)], answer_ids
    problems += check_step_references(step, dict(state.drawn), set(state.groups))
    taken = {p.id for s in state.steps for p in s.draw} | state.groups
    taken |= {p.group for p in step.draw if p.group is not None}
    for primitive in step.draw:
        if primitive.id in taken:
            problems.append(f"draw id {primitive.id} is already used after template expansion")
        taken.add(primitive.id)
    return (None if problems else step), problems, answer_ids


def _contract_checkpoint(
    filled: CheckpointDraft, draft: CheckpointDraft, ledger: dict[str, Entry]
) -> tuple[dict[str, Any], set[str]]:
    out: dict[str, Any] = {
        "question": filled.question,
        "type": filled.type,
        "hint": filled.hint,
        "reexplain_hint": filled.reexplain_hint,
    }
    if filled.type == "choice":
        return {**out, "choices": filled.choices, "answer": int(filled.answer)}, set()
    value, unit, ids = answer_value(draft.answer, ledger)
    return {**out, "answer": value, "unit": unit, "tolerance": CHECKPOINT_TOLERANCE}, ids
