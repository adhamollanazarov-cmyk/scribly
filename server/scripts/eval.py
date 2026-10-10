"""Eval bank runner (docs/COVERAGE.md §4). Real API calls: costs money.

Run from server/:
    uv run python -m scripts.eval                      # all problems
    uv run python -m scripts.eval --topic circuits --limit 3
    uv run python -m scripts.eval --thinking adaptive --source audit --label adaptive \
        --compare ../docs/eval/2026-10-10.json

Writes docs/eval/<date>[-<label>].md and .json, keeps every lesson in
server/.cache/eval/<date>[-<label>]/, and copies the 3 worst lessons to docs/eval/<date>[-<label>]/.
"""

import argparse
import asyncio
import hashlib
import json
import math
import shutil
import statistics
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.lesson.claude import ClaudeLessonLLM, LessonLLM
from app.lesson.generate import Metrics, generate_lesson
from app.lesson.ledger import PLACEHOLDER, Entry, parse_spec, rounded
from app.lesson.models import Source
from app.lesson.prompt import system_prompt
from app.lesson.stepcheck import RAW_KEYS, LessonState
from app.settings import REPO_ROOT, Settings, get_settings
from scripts.eval_units import convert

PROBLEMS = REPO_ROOT / "tests" / "eval" / "problems.yaml"
REPORT_DIR = REPO_ROOT / "docs" / "eval"
CACHE_DIR = REPO_ROOT / "server" / ".cache" / "eval"
GRADING_VERSION = 2


@dataclass(frozen=True)
class Expected:
    name: str
    value: float
    unit: str
    rel_tol: float = 0.01


@dataclass(frozen=True)
class Problem:
    id: str
    topic: str
    level: str
    source: str
    input: str
    expected: list[Expected]
    must_draw: list[str]
    manual_checks: list[str] = field(default_factory=list)

    @property
    def group(self) -> str:
        return self.topic.split("/")[0]


@dataclass
class Result:
    id: str
    topic: str
    source: str
    valid: bool
    error: str | None
    numbers: dict[str, bool] = field(default_factory=dict)
    missing_draws: list[str] = field(default_factory=list)
    leftovers: dict[str, int] = field(default_factory=dict)
    steps: int = 0
    unverified_steps: int = 0
    fixes: int = 0
    fixes_failed: int = 0
    fix_reasons: dict[str, int] = field(default_factory=dict)
    retries: int = 0
    first_step_s: float | None = None
    total_s: float | None = None
    cost_usd: float = 0.0
    skipped: bool = False
    manual_checks: list[str] = field(default_factory=list)

    @property
    def numbers_ok(self) -> bool:
        return all(self.numbers.values())

    @property
    def passed(self) -> bool:
        return (
            self.valid
            and self.numbers_ok
            and not self.missing_draws
            and self.unverified_steps == 0
            and not self.manual_checks
            and not self.skipped
        )


def load_problems(path: Path = PROBLEMS) -> list[Problem]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        Problem(
            id=p["id"],
            topic=p["topic"],
            level=p["level"],
            source=p["source"],
            input=" ".join(p["input"].split()),
            expected=[Expected(**e) for e in p.get("expected", [])],
            must_draw=list(p.get("must_draw", [])),
            manual_checks=list(p.get("manual_checks", [])),
        )
        for p in raw
    ]


# --- grading --------------------------------------------------------------------------


def value_matches(expected: Expected, values: list[Entry]) -> bool:
    for entry in values:
        if not entry.verified:
            continue
        try:
            value = convert(entry.value, entry.unit, expected.unit)
        except (ValueError, OverflowError, ZeroDivisionError):
            continue
        if math.isclose(value, expected.value, rel_tol=expected.rel_tol, abs_tol=0):
            return True
    return False


def missing_draws(must_draw: list[str], drawn: set[str]) -> list[str]:
    return [need for need in must_draw if not set(need.split("|")) & drawn]


def displayed_values(state: LessonState | None) -> list[Entry]:
    """Grade the rounded values actually filled into student-facing fields."""
    if state is None:
        return []
    used = {c.id for c in state.calcs if c.used_in_steps}
    values = []
    for draft in state.drafts:
        texts = [draft.say, draft.subtitles.uz, draft.subtitles.ru]
        for item in draft.draw:
            texts += [item.label, *(a.v for a in item.txt if a.k not in RAW_KEYS)]
        for cp in draft.checkpoints:
            texts += [cp.question, *cp.choices, cp.hint, cp.reexplain_hint]
            if cp.type == "number":
                texts.append(cp.answer)
        for text in texts:
            for match in PLACEHOLDER.finditer(text):
                entry = state.ledger.get(match.group(1))
                if entry is not None and entry.verified and match.group(1) in used:
                    values.append(
                        replace(entry, value=rounded(entry.value, parse_spec(match.group(2))))
                    )
    return values


def grade(problem: Problem, metrics: Metrics, error: str | None) -> Result:
    state = metrics.state
    verified = displayed_values(state)
    drawn = {item.type for d in state.drafts for item in d.draw} if state else set()
    lesson = metrics.lesson
    leftovers = Counter(v.rule for _, v in metrics.leftovers)
    return Result(
        id=problem.id,
        topic=problem.topic,
        source=problem.source,
        valid=error is None and lesson is not None and metrics.final_error is None,
        error=error or metrics.final_error,
        numbers={e.name: value_matches(e, verified) for e in problem.expected},
        missing_draws=missing_draws(problem.must_draw, drawn),
        leftovers=dict(leftovers),
        steps=len(lesson.steps) if lesson else len(state.steps) if state else 0,
        unverified_steps=sum(s.warning == "unverified" for s in lesson.steps) if lesson else 0,
        fixes=metrics.fixes,
        fixes_failed=metrics.fixes_failed,
        fix_reasons=dict(metrics.fix_reasons),
        retries=metrics.retries,
        first_step_s=metrics.first_step_s,
        total_s=metrics.total_s,
        cost_usd=metrics.usage.cost_usd,
        manual_checks=list(problem.manual_checks),
    )


def badness(result: Result) -> tuple[Any, ...]:
    """Sort key: worst first."""
    wrong = sum(not ok for ok in result.numbers.values())
    return (
        result.passed,
        result.valid,
        -wrong,
        -len(result.missing_draws),
        -result.unverified_steps,  # the student hears "I could not verify this number"
        -sum(result.leftovers.values()),
        -result.fixes,
    )


# --- running --------------------------------------------------------------------------


async def run_one(problem: Problem, llm: LessonLLM, save_dir: Path | None) -> Result:
    metrics = Metrics()
    error = None
    source = Source(type="problem", text=problem.input)
    try:
        async for _ in generate_lesson(source, llm, metrics):
            pass
    except Exception as e:  # recorded in the report, the run goes on
        causes = []
        cause = e.__cause__
        while cause is not None:
            causes.append(str(cause))
            cause = cause.__cause__
        error = f"{type(e).__name__}: {e}" + "".join(f" <- {c}" for c in causes)
    if metrics.total_s is None:
        metrics.total_s = time.perf_counter() - metrics.started
    result = grade(problem, metrics, error)
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        lesson = metrics.lesson.model_dump(mode="json") if metrics.lesson else None
        drafts = [d.model_dump(mode="json") for d in metrics.state.drafts] if metrics.state else []
        leftovers = [
            {"step": s, "rule": v.rule, "message": v.message} for s, v in metrics.leftovers
        ]
        payload = {
            "problem": asdict(problem),
            "result": asdict(result),
            "lesson": lesson,
            "drafts": drafts,
            "leftovers": leftovers,
        }
        (save_dir / f"{problem.id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
        )
    return result


async def run_eval(
    problems: list[Problem],
    make_llm: Callable[[], LessonLLM],
    concurrency: int = 4,
    max_cost: float = 10.0,
    save_dir: Path | None = None,
    log: Callable[[str], None] = print,
) -> list[Result]:
    gate = asyncio.Semaphore(concurrency)
    spent = 0.0

    async def one(problem: Problem) -> Result:
        nonlocal spent
        async with gate:
            if spent >= max_cost:
                log(f"skip {problem.id}: cost limit ${max_cost:.2f} reached")
                return Result(
                    problem.id,
                    problem.topic,
                    problem.source,
                    valid=False,
                    error="skipped: cost limit",
                    skipped=True,
                )
            result = await run_one(problem, make_llm(), save_dir)
            spent += result.cost_usd
            mark = "PASS" if result.passed else "FAIL"
            log(
                f"{mark} {problem.id} ${result.cost_usd:.3f} {result.total_s or 0:.0f}s "
                f"(total ${spent:.2f})"
            )
            return result

    return list(await asyncio.gather(*(one(p) for p in problems)))


# --- report ---------------------------------------------------------------------------


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def _avg(values: list[float]) -> str:
    return f"{statistics.mean(values):.1f}" if values else "-"


def _median(values: list[float]) -> str:
    return f"{statistics.median(values):.1f}" if values else "-"


def summary_row(name: str, results: list[Result]) -> str:
    ran = [r for r in results if not r.skipped]
    n = len(ran)
    first = [r.first_step_s for r in ran if r.first_step_s is not None]
    total = [r.total_s for r in ran if r.total_s is not None]
    cost = [r.cost_usd for r in ran]
    return (
        f"| {name} | {n} | {_pct(sum(r.passed for r in ran), n)} | "
        f"{_pct(sum(r.valid for r in ran), n)} | {_pct(sum(r.numbers_ok for r in ran), n)} | "
        f"{_pct(sum(not r.missing_draws for r in ran), n)} | ${sum(cost) / n if n else 0:.3f} | "
        f"{_median(first)} | {_avg(total)} |"
    )


def render_report(results: list[Result], meta: dict[str, Any], top: int = 3) -> str:
    groups = sorted({r.topic.split("/")[0] for r in results})
    ran = [r for r in results if not r.skipped]
    lines = [
        f"# Eval report — {meta['date']}{' — ' + meta['label'] if meta.get('label') else ''}",
        "",
        *(
            [
                "Stored scores use an older or unspecified grader. Re-rendering changes "
                "formatting only; it does not recheck signs, units, displayed rounding or "
                "manual-review requirements. Do not treat these scores as a new evaluation.",
                "",
            ]
            if meta.get("grading_version") != GRADING_VERSION
            else []
        ),
        f"Model `{meta['model']}`, thinking `{meta['thinking']}`, effort `{meta['effort']}`, "
        f"prompt sha256 `{meta['prompt_sha']}`, problems: {len(results)} "
        f"({len(results) - len(ran)} skipped). Total cost **${sum(r.cost_usd for r in ran):.2f}**,"
        f" wall time {meta.get('wall_s', 0):.0f} s.",
        "",
        "Pass = valid lesson AND every expected number matched, with its sign and compatible "
        "units, by a displayed verified calc AND every required drawing present AND no "
        "unverified steps or pending manual checks. Signed numeric matching does not "
        "check semantic directions or associate quantities with their names; bank cases "
        "flagged with manual checks cannot automatically pass. First step = time until "
        "step 1 is checked and ready "
        "(no TTS).",
        "",
        "| topic | n | pass | valid | numbers | drawings | avg cost | median first step (s) "
        "| avg total (s) |",
        "|---|---|---|---|---|---|---|---|---|",
        *[summary_row(g, [r for r in results if r.topic.startswith(g)]) for g in groups],
        summary_row("**all**", results),
        "",
        "## Problems",
        "",
        "| id | pass | valid | numbers | missing drawings | fixes | lint left | unverified steps "
        "| first step (s) | total (s) | cost |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: r.id):
        ok = sum(r.numbers.values())
        left = ", ".join(f"{k} {v}" for k, v in sorted(r.leftovers.items())) or "-"
        lines.append(
            f"| {r.id} | {'✅' if r.passed else '❌'} | {'yes' if r.valid else 'no'} | "
            f"{ok}/{len(r.numbers)} | {', '.join(r.missing_draws) or '-'} | {r.fixes} | {left} | "
            f"{r.unverified_steps} | {r.first_step_s or 0:.1f} | {r.total_s or 0:.0f} | "
            f"${r.cost_usd:.3f} |"
        )
    failures = [r for r in results if not r.passed]
    lines += ["", "## Failures", ""]
    for r in failures:
        reasons = []
        if r.error:
            reasons.append(f"error: {r.error}")
        wrong = [n for n, ok in r.numbers.items() if not ok]
        if wrong:
            reasons.append(f"numbers not found among verified calcs: {', '.join(wrong)}")
        if r.missing_draws:
            reasons.append(f"missing drawings: {', '.join(r.missing_draws)}")
        if r.unverified_steps:
            reasons.append(f"unverified steps: {r.unverified_steps}")
        if r.manual_checks:
            reasons.append(f"manual review required: {'; '.join(r.manual_checks)}")
        lines.append(f"- **{r.id}**: {'; '.join(reasons)}")
    if not failures:
        lines.append("None.")
    reasons: Counter[str] = Counter()
    rules: Counter[str] = Counter()
    for r in ran:
        reasons.update(r.fix_reasons)
        rules.update(r.leftovers)
    lines += ["", "## Why steps were sent back for a fix (steps per rule)", ""]
    lines += [f"- {rule}: {count}" for rule, count in reasons.most_common()] or ["None."]
    lines += ["", "## Lint problems left after the one fix", ""]
    lines += [f"- {rule}: {count}" for rule, count in rules.most_common()] or ["None."]
    worst = sorted(ran, key=badness)[:top]
    lines += ["", f"## {top} worst lessons", ""]
    for r in worst:
        lines.append(
            f"- **{r.id}** (pass: {r.passed}, numbers {sum(r.numbers.values())}/"
            f"{len(r.numbers)}, fixes {r.fixes}, lint left {sum(r.leftovers.values())}, "
            f"unverified steps {r.unverified_steps})"
        )
    if meta.get("compare"):
        lines += ["", "## Comparison", "", *meta["compare"]]
    return "\n".join(lines) + "\n"


def compare_section(
    results: list[Result],
    other: list[dict[str, Any]],
    names: tuple[str, str],
    before_version: int | None = None,
) -> list[str]:
    before = {r["id"]: r for r in other}
    lines = [
        *(
            ["Scoring versions differ: pass/number changes are not a model comparison.", ""]
            if before_version != GRADING_VERSION
            else []
        ),
        f"| id | pass ({names[0]}) | pass ({names[1]}) | numbers | first step (s) | total (s) "
        "| cost |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: r.id):
        b = before.get(r.id)
        if b is None:
            continue
        bn = sum(b["numbers"].values())
        lines.append(
            f"| {r.id} | {'✅' if b['passed'] else '❌'} | {'✅' if r.passed else '❌'} | "
            f"{bn} → {sum(r.numbers.values())} of {len(r.numbers)} | "
            f"{b['first_step_s'] or 0:.1f} → {r.first_step_s or 0:.1f} | "
            f"{b['total_s'] or 0:.0f} → {r.total_s or 0:.0f} | "
            f"${b['cost_usd']:.3f} → ${r.cost_usd:.3f} |"
        )
    return lines


def result_dicts(results: list[Result]) -> list[dict[str, Any]]:
    return [asdict(r) | {"passed": r.passed} for r in results]


# --- command line ---------------------------------------------------------------------


def select(problems: list[Problem], args: argparse.Namespace) -> list[Problem]:
    if args.ids:
        wanted = set(args.ids.split(","))
        problems = [p for p in problems if p.id in wanted]
    if args.topic:
        problems = [p for p in problems if p.topic.startswith(args.topic)]
    if args.source:
        problems = [p for p in problems if p.source == args.source]
    return problems[: args.limit] if args.limit else problems


def write_outputs(results: list[Result], meta: dict[str, Any], stem: str, save_dir: Path) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"{stem}.md").write_text(
        render_report(results, meta), encoding="utf-8", newline="\n"
    )
    (REPORT_DIR / f"{stem}.json").write_text(
        json.dumps({"meta": meta | {"compare": None}, "results": result_dicts(results)}, indent=1),
        encoding="utf-8",
        newline="\n",
    )
    worst_dir = REPORT_DIR / stem
    if worst_dir.exists():
        shutil.rmtree(worst_dir)
    worst_dir.mkdir()
    for r in sorted([r for r in results if not r.skipped], key=badness)[:3]:
        if (save_dir / f"{r.id}.json").exists():
            shutil.copy(save_dir / f"{r.id}.json", worst_dir / f"{r.id}.json")


def rerender(path: Path) -> None:
    """Rewrite a report from its saved .json (e.g. after changing the report format)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    names = set(Result.__dataclass_fields__)
    results = [Result(**{k: v for k, v in r.items() if k in names}) for r in data["results"]]
    write_outputs(results, data["meta"], path.stem, CACHE_DIR / path.stem)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rerender", type=Path, help="rewrite the report of this .json, no API")
    parser.add_argument("--topic")
    parser.add_argument("--source", choices=["audit", "own"])
    parser.add_argument("--ids", help="comma-separated problem ids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--thinking", choices=["between_tools", "adaptive"])
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-cost", type=float, default=10.0)
    parser.add_argument("--label", default="")
    parser.add_argument("--compare", type=Path, help="results .json of an earlier run")
    args = parser.parse_args()
    if args.rerender:
        rerender(args.rerender)
        return

    overrides = {
        k: v for k, v in (("lesson_thinking", args.thinking), ("lesson_effort", args.effort)) if v
    }
    settings: Settings = get_settings().model_copy(update=overrides)
    problems = select(load_problems(), args)
    stem = date.today().isoformat() + (f"-{args.label}" if args.label else "")
    save_dir = CACHE_DIR / stem
    print(
        f"{len(problems)} problems, {settings.lesson_model}, thinking {settings.lesson_thinking}, "
        f"effort {settings.lesson_effort}, cost limit ${args.max_cost:.2f}"
    )

    started = time.perf_counter()
    results = asyncio.run(
        run_eval(
            problems, lambda: ClaudeLessonLLM(settings), args.concurrency, args.max_cost, save_dir
        )
    )
    meta: dict[str, Any] = {
        "grading_version": GRADING_VERSION,
        "date": date.today().isoformat(),
        "label": args.label,
        "model": settings.lesson_model,
        "thinking": settings.lesson_thinking,
        "effort": settings.lesson_effort,
        "prompt_sha": hashlib.sha256(system_prompt().encode()).hexdigest()[:12],
        "wall_s": time.perf_counter() - started,
    }
    if args.compare:
        previous = json.loads(args.compare.read_text(encoding="utf-8"))
        meta["compare"] = compare_section(
            results,
            previous["results"],
            ("before", args.label or "this run"),
            previous.get("meta", {}).get("grading_version"),
        )
    write_outputs(results, meta, stem, save_dir)
    total = sum(r.cost_usd for r in results)
    print(
        f"report: {REPORT_DIR / f'{stem}.md'}  pass {sum(r.passed for r in results)}/"
        f"{len(results)}  cost ${total:.2f}"
    )


if __name__ == "__main__":
    main()
