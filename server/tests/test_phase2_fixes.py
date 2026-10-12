import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from app.lesson.fixtures import load_fixture
from app.lesson.lint import LintState
from app.lesson.models import CurvePrim, Source
from app.lesson.pipeline import LessonError, prepare_lesson
from app.lesson.stepcheck import LessonState, check_step, commit
from app.tts import AudioCache, EdgeTTSProvider, TTSError
from tests.drafts import item, step


@pytest.mark.parametrize("first", ["error", "empty", "timeout"])
def test_edge_retry_recovers_without_caching_partial_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, first: str
) -> None:
    calls = []

    class Communicate:
        def __init__(self, text: str, voice: str, *, rate: str) -> None:
            calls.append((text, voice, rate))
            self.attempt = len(calls)

        async def stream(self) -> AsyncIterator[dict[str, Any]]:
            if self.attempt == 1:
                if first == "error":
                    yield {"type": "audio", "data": b"partial"}
                    raise RuntimeError("PRIVATE_PROVIDER_CONTENT")
                if first == "timeout":
                    await asyncio.sleep(10)
                return
            yield {"type": "audio", "data": b"ID3complete"}

    monkeypatch.setattr("app.tts.edge_tts.Communicate", Communicate)
    cache = AudioCache(tmp_path)
    provider = EdgeTTSProvider(attempt_timeout=0.01, retry_delay=0)
    key = asyncio.run(cache.get_or_create(provider, "Hi", "v", "+0%"))
    assert calls == [("Hi", "v", "+0%")] * 2
    assert (tmp_path / f"{key}.mp3").read_bytes() == b"ID3complete"
    assert len(list(tmp_path.iterdir())) == 1
    asyncio.run(cache.get_or_create(provider, "Hi", "v", "+0%"))
    assert len(calls) == 2


def test_edge_persistent_failure_is_bounded_and_private(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = 0

    class Communicate:
        def __init__(self, *args: Any, **kw: Any) -> None:
            nonlocal calls
            calls += 1

        async def stream(self) -> AsyncIterator[dict[str, Any]]:
            raise RuntimeError("PRIVATE_PROVIDER_CONTENT")
            yield {}

    monkeypatch.setattr("app.tts.edge_tts.Communicate", Communicate)
    with pytest.raises(TTSError) as caught:
        asyncio.run(
            AudioCache(tmp_path).get_or_create(EdgeTTSProvider(retry_delay=0), "Hi", "v", "+0%")
        )
    assert calls == 2 and "PRIVATE" not in str(caught.value)
    assert not list(tmp_path.iterdir())


def test_edge_cancellation_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    class Communicate:
        def __init__(self, *args: Any, **kw: Any) -> None:
            nonlocal calls
            calls += 1

        async def stream(self) -> AsyncIterator[dict[str, Any]]:
            raise asyncio.CancelledError
            yield {}

    monkeypatch.setattr("app.tts.edge_tts.Communicate", Communicate)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(EdgeTTSProvider().synthesize("Hi", "v", "+0%"))
    assert calls == 1


def test_bare_plot_is_sampled_with_explicit_scales_and_preserves_references() -> None:
    raw = load_fixture("plot_square")
    lesson, _ = prepare_lesson(raw)
    curve = lesson.steps[1].draw[0]
    assert isinstance(curve, CurvePrim) and curve.id == "square" and curve.at == 0.1
    assert curve.points[0] == (120, 760)
    assert curve.points[20] == (520, 635)
    assert curve.points[-1] == (920, 260)
    assert lesson.steps[2].draw[0].target_id == curve.id


@pytest.mark.parametrize(
    "change",
    [
        {"expr": "__import__('os').getcwd()"},
        {"expr": "x.__class__"},
        {"expr": "9^9^9^9"},
        {"expr": "1/x"},
        {"axes_id": "later"},
        {"axes_id": "rule"},
        {"x_max": 0},
        {"y_max": 0},
        {"samples": 201},
        {"x_max": float("inf")},
    ],
)
def test_invalid_or_unsafe_plots_fail_before_streaming(change: dict[str, Any]) -> None:
    raw = load_fixture("plot_square")
    raw["steps"][1]["draw"][0].update(change)
    with pytest.raises(LessonError):
        prepare_lesson(raw)


def test_generated_plot_resolves_axes_from_an_earlier_step() -> None:
    state = LessonState(Source(type="topic", text="Plot a square."), LintState([]))
    axes = item(
        "axes", "axes", {"x": 100, "y": 100, "w": 200, "h": 100}, {"xlabel": "x", "ylabel": "y"}
    )
    first = check_step(step("s1", "Here are the axes.", [axes]), state)
    assert not first.fatal
    commit(state, first)
    plot = item(
        "p",
        "plot",
        {"x_min": 0, "x_max": 2, "y_min": 0, "y_max": 4, "samples": 3},
        {"axes_id": "axes", "expr": "x^2"},
    )
    checked = check_step(step("s2", "Here is the curve.", [plot]), state)
    assert not checked.fatal and checked.step is not None
    assert checked.step.draw[0].points == [(100, 200), (200, 175), (300, 100)]
