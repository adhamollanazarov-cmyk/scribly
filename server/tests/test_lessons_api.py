import asyncio
import json
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.lesson.fixtures import load_fixture
from app.lesson.models import StreamedStep
from app.lesson.pipeline import prepare_lesson
from app.main import create_app
from app.routes.lessons import NOT_AVAILABLE, get_tts_provider, lesson_events
from app.settings import Settings, get_settings
from app.tts import AudioCache, TTSError

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


def test_without_mock_mode_streams_a_clear_error(tmp_path: Path) -> None:
    with closing(make_client(tmp_path, FakeTTS(), mock_ai=False)) as client:
        assert stream(client) == [("error", {"message": NOT_AVAILABLE})]


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
