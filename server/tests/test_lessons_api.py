import asyncio
import json
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.lesson.claude import LLMError
from app.lesson.fixtures import load_fixture
from app.lesson.models import StreamedStep
from app.lesson.pipeline import prepare_lesson
from app.main import create_app
from app.routes.lessons import (
    GENERIC_ERROR,
    NO_KEY,
    get_lesson_llm,
    get_tts_provider,
    lesson_events,
)
from app.settings import Settings, get_settings
from app.tts import AudioCache, TTSError
from tests.drafts import draft_json, good_steps, step
from tests.fake_llm import FakeLLM

REQUEST = {"type": "topic", "text": "Explain Gauss's law"}


class FakeTTS:
    def __init__(self, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.calls = 0

    async def synthesize(self, text: str, voice: str, rate: str) -> bytes:
        self.calls += 1
        if self.fail_on and self.fail_on in text:
            raise TTSError("offline")
        return b"ID3" + text.encode()


def make_client(tmp_path: Path, tts: FakeTTS, mock_ai: bool = True) -> TestClient:
    """No `with TestClient(...)`: that runs the startup model check, which may use .env."""
    app = create_app()
    settings = Settings(_env_file=None, mock_ai=mock_ai, audio_cache_dir=tmp_path / "audio")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_tts_provider] = lambda: tts
    return TestClient(app)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with closing(make_client(tmp_path, FakeTTS())) as c:
        yield c


def parse_sse(body: str) -> list[tuple[str, Any]]:
    events = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1) for line in block.splitlines() if not line.startswith(":")
        )
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def stream(client: TestClient) -> list[tuple[str, Any]]:
    response = client.post("/lessons", json=REQUEST)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


def test_mock_lesson_streams_meta_steps_done_in_order(client: TestClient) -> None:
    events = stream(client)

    assert [name for name, _ in events] == ["meta"] + ["step"] * 7 + ["done"]
    meta = events[0][1]
    assert meta == {
        "id": "6f1c2b9e-0d3a-4c7e-9b1a-3e5f7a9c2d41",
        "title": "Gauss's law",
        "level": "simple",
        "step_count": 7,
    }
    assert events[-1][1] == {"id": meta["id"]}


def test_streamed_steps_are_expanded_valid_and_have_audio(client: TestClient) -> None:
    steps = [data for name, data in stream(client) if name == "step"]

    assert [s["id"] for s in steps] == ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]
    for data in steps:
        step = StreamedStep.model_validate(data)
        assert all(p.type != "template" for p in step.draw)
        assert step.audio_url is not None
        audio = client.get(step.audio_url)
        assert audio.status_code == 200
        assert audio.headers["content-type"] == "audio/mpeg"
        assert audio.content == b"ID3" + step.say.encode()


def test_second_request_uses_the_audio_cache(tmp_path: Path) -> None:
    tts = FakeTTS()
    with closing(make_client(tmp_path, tts)) as client:
        stream(client)
        stream(client)

    assert tts.calls == 7


def test_tts_failure_streams_step_without_audio(tmp_path: Path) -> None:
    with closing(make_client(tmp_path, FakeTTS(fail_on="Gaussian surface"))) as client:
        steps = {d["id"]: d for name, d in stream(client) if name == "step"}

    assert steps["s3"]["audio_url"] is None
    assert all(steps[s]["audio_url"] for s in steps if s != "s3")


def live_client(tmp_path: Path, llm: FakeLLM, key: str | None = "test-key") -> TestClient:
    app = create_app()
    settings = Settings(
        _env_file=None, mock_ai=False, audio_cache_dir=tmp_path / "audio", anthropic_api_key=key
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_tts_provider] = lambda: FakeTTS()
    app.dependency_overrides[get_lesson_llm] = lambda: llm
    return TestClient(app)


def test_live_mode_streams_generated_steps_with_audio(tmp_path: Path) -> None:
    with closing(live_client(tmp_path, FakeLLM([draft_json()]))) as client:
        events = stream(client)

    assert [name for name, _ in events] == ["meta"] + ["step"] * 5 + ["done"]
    meta = events[0][1]
    assert meta["title"] == "Flux" and meta["step_count"] is None
    assert events[-1][1] == {"id": meta["id"]}
    for _, data in events[1:-1]:
        assert StreamedStep.model_validate(data).audio_url is not None


def test_live_mode_without_a_key_streams_a_clear_error(tmp_path: Path) -> None:
    with closing(live_client(tmp_path, FakeLLM([]), key=None)) as client:
        assert stream(client) == [("error", {"message": NO_KEY})]


def test_live_mode_failure_is_a_safe_error_event(tmp_path: Path) -> None:
    llm = FakeLLM([LLMError("SYNTHETIC_PRIVATE_INPUT"), LLMError("SYNTHETIC_PRIVATE_INPUT")])
    with closing(live_client(tmp_path, llm)) as client:
        events = stream(client)

    assert events == [
        ("error", {"message": "The lesson could not be generated. Please try again."})
    ]
    assert "SYNTHETIC_PRIVATE_INPUT" not in json.dumps(events)


def test_final_lesson_validation_failure_sends_error_without_done(tmp_path: Path) -> None:
    # The incremental pacing lint exempts every summary; the Lesson contract exempts
    # only the final one. Exercise a real final validation failure through SSE.
    checkpoint = good_steps()[2]
    checkpoint["id"] = "s6"
    steps = [step(f"s{i}", "Here is the next idea.") for i in range(1, 5)]
    steps += [
        step("s5", "Consider the main idea.", kind="summary"),
        checkpoint,
        step("s7", "That completes the lesson.", kind="summary"),
    ]
    llm = FakeLLM([draft_json(steps)])
    with closing(live_client(tmp_path, llm)) as client:
        events = stream(client)

    assert [name for name, _ in events] == ["meta"] + ["step"] * 7 + ["error"]
    assert events[-1][1] == {"message": "The lesson failed final validation. Please try again."}
    assert len(llm.requests) == 1


def test_broken_fixture_streams_error_not_a_crash(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.routes.lessons.load_fixture", lambda name: {"steps": []})

    events = stream(client)

    assert len(events) == 1 and events[0][0] == "error"
    assert "invalid" in events[0][1]["message"]


@pytest.mark.parametrize(
    "body", [{}, {"type": "video", "text": "x"}, {"type": "topic", "text": ""}]
)
def test_bad_request_body_is_422(client: TestClient, body: dict[str, Any]) -> None:
    assert client.post("/lessons", json=body).status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/audio/abc.mp3",
        "/audio/" + "0" * 64 + ".mp3",  # well-formed but not cached
        "/audio/..%2F..%2F.env.mp3",
        "/audio/%2e%2e%2f%2e%2e%2fsettings.py.mp3",
        "/audio/" + "A" * 64 + ".mp3",
        "/audio/" + "0" * 64 + ".wav",
    ],
)
def test_audio_route_rejects_unknown_or_unsafe_paths(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404


def test_each_step_is_sent_before_the_next_step_is_narrated(tmp_path: Path) -> None:
    async def collect() -> list[tuple[str, int]]:
        tts = FakeTTS()
        lesson, _ = prepare_lesson(load_fixture("gauss_law"))
        settings = Settings(_env_file=None, mock_ai=True)
        seen = []
        async for event in lesson_events(lesson, settings, tts, AudioCache(tmp_path)):
            seen.append((event.event or "", tts.calls))
        return seen

    seen = asyncio.run(collect())

    steps = [calls for name, calls in seen if name == "step"]
    assert steps == [1, 2, 3, 4, 5, 6, 7]  # one TTS call per step, then that step is sent


@pytest.mark.parametrize(
    "key",
    [
        "..\\..\\.env",
        "C:\\Windows\\win.ini",
        "\\\\localhost\\share\\file",
        "0" * 64 + ":private",
        "0" * 64 + "%00",
        "0" * 64 + "%0a",
        "0" * 64 + "%5c..%5c.env",
        "0" * 64 + "%252f..%252f.env",
    ],
)
def test_audio_rejects_windows_paths_and_encoded_suffixes(client: TestClient, key: str) -> None:
    assert client.get(f"/audio/{key}.mp3").status_code == 404


def test_audio_response_has_expected_cache_headers(client: TestClient) -> None:
    audio_url = next(data["audio_url"] for name, data in stream(client) if name == "step")
    response = client.get(audio_url)

    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.headers["content-type"] == "audio/mpeg"


def test_cache_write_error_is_safe_and_does_not_end_the_lesson(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    marker = "SYNTHETIC_PRIVATE_INPUT"

    def fail_write(self: AudioCache, path: Path, data: bytes) -> None:
        raise PermissionError(marker)

    monkeypatch.setattr(AudioCache, "_write_atomic", fail_write)
    events = stream(client)

    assert events[-1][0] == "done"
    assert all(data["audio_url"] is None for name, data in events if name == "step")
    assert "PermissionError" in caplog.text
    assert marker not in caplog.text
    assert marker not in json.dumps(events)


def test_unexpected_fixture_failure_has_generic_public_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken_fixture(name: str) -> dict[str, Any]:
        raise OSError("SYNTHETIC_PRIVATE_INPUT")

    monkeypatch.setattr("app.routes.lessons.load_fixture", broken_fixture)
    assert stream(client) == [("error", {"message": GENERIC_ERROR})]
    assert "OSError" in caplog.text
    assert "SYNTHETIC_PRIVATE_INPUT" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_template_error_does_not_log_raw_input(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    raw = load_fixture("gauss_law")
    raw["steps"][0]["draw"][0]["params"]["unexpected"] = "SYNTHETIC_PRIVATE_INPUT"
    monkeypatch.setattr("app.routes.lessons.load_fixture", lambda name: raw)

    events = stream(client)

    assert events[0][0] == "error"
    assert "SYNTHETIC_PRIVATE_INPUT" not in json.dumps(events)
    assert "SYNTHETIC_PRIVATE_INPUT" not in caplog.text
