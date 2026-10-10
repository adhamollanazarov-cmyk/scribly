import asyncio
import json
from pathlib import Path

from app.lesson.claude import LLMRefused
from scripts.eval import (
    Expected,
    Problem,
    Result,
    load_problems,
    missing_draws,
    render_report,
    run_eval,
    value_matches,
)
from tests.drafts import SOURCE_TEXT, draft_json
from tests.fake_llm import FakeLLM

FLUX = Problem(
    id="es-flux",
    topic="electrostatics/gauss",
    level="simple",
    source="own",
    input=SOURCE_TEXT,
    expected=[Expected("flux", 338.8299, "N*m**2/C")],
    must_draw=["point_charge", "math|text"],
)
FIELD = Problem(
    id="es-field",
    topic="electrostatics/gauss",
    level="simple",
    source="own",
    input=SOURCE_TEXT,
    expected=[Expected("E", 674.08, "N/C")],
    must_draw=["gaussian_sphere"],
)
META = {
    "date": "2026-10-10",
    "model": "claude-sonnet-5-5",
    "thinking": "between_tools",
    "effort": "high",
    "prompt_sha": "abc123",
    "wall_s": 12.0,
}


def run(
    problems: list[Problem], replies: list[list[str | Exception]], **kw: object
) -> list[Result]:
    queue = list(replies)
    return asyncio.run(run_eval(problems, lambda: FakeLLM(queue.pop(0)), log=lambda _: None, **kw))  # type: ignore[arg-type]


def test_two_mocked_problems_are_graded_and_reported(tmp_path: Path) -> None:
    results = run([FLUX, FIELD], [[draft_json()], [draft_json()]], save_dir=tmp_path)

    by_id = {r.id: r for r in results}
    assert by_id["es-flux"].passed
    assert by_id["es-field"].numbers == {"E": False}
    assert by_id["es-field"].missing_draws == ["gaussian_sphere"]
    assert all(r.cost_usd > 0 and r.first_step_s is not None for r in results)
    saved = json.loads((tmp_path / "es-flux.json").read_text(encoding="utf-8"))
    assert saved["lesson"]["calcs"][0]["used_in_steps"] == ["s4"]

    report = render_report(results, META)
    assert "| electrostatics | 2 | 50% | 100% | 50% | 50% |" in report
    assert "**es-field**: numbers not found among verified calcs: E; missing drawings" in report
    assert "## 3 worst lessons" in report and report.index("**es-field** (pass") > 0


def test_generation_error_is_recorded_not_raised() -> None:
    [result] = run([FLUX], [[LLMRefused("declined"), LLMRefused("declined")]])

    assert not result.valid and not result.passed
    assert result.error is not None and "could not be generated" in result.error


def test_cost_limit_skips_the_remaining_problems() -> None:
    results = run([FLUX, FIELD], [[draft_json()], [draft_json()]], concurrency=1, max_cost=0.0)

    assert all(r.skipped for r in results)
    assert "(2 skipped)" in render_report(results, META)


def test_value_matching_allows_si_prefixes_and_percent_not_other_factors() -> None:
    cap = Expected("C", 1.7708e-10, "F")
    assert value_matches(cap, [177.08])  # shown in pF
    assert not value_matches(cap, [17.708])
    assert value_matches(Expected("err", 1.99, "%"), [0.0199])
    assert value_matches(Expected("E", 733.618, "N/C"), [-733.6])


def test_missing_draws_accepts_alternatives() -> None:
    assert missing_draws(["incline_block", "free_body|vector"], {"incline_block", "vector"}) == []
    assert missing_draws(["axes_plot|axes"], {"text"}) == ["axes_plot|axes"]


def test_eval_bank_is_well_formed() -> None:
    problems = load_problems()
    assert len(problems) == 30
    assert len({p.id for p in problems}) == 30
    assert sum(p.source == "audit" for p in problems) == 10
    assert all(p.expected for p in problems)
    groups = {p.group for p in problems}
    assert {"mechanics", "kinematics", "circuits", "electrostatics"} <= groups
