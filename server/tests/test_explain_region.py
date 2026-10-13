import base64
import zlib
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.lesson.claude import LLMError
from app.routes.explain import DEMO_HEADER, MAX_IMAGE_SIDE, NOT_YET, png_size
from app.routes.lessons import get_lesson_llm
from tests.test_lessons_api import FakeTTS, make_client, parse_sse


def png(width: int = 4, height: int = 3) -> bytes:
    """A real, tiny RGB PNG."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return len(data).to_bytes(4, "big") + body + zlib.crc32(body).to_bytes(4, "big")

    header = width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes([8, 2, 0, 0, 0])
    rows = b"".join(b"\x00" + b"\xff" * 3 * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def body(image: bytes | None = None, **extra: Any) -> dict[str, Any]:
    data = png() if image is None else image
    return {"image_png_base64": base64.b64encode(data).decode()} | extra


class ExplodingLLM:
    """Fails the test if the region endpoint ever reaches the model."""

    def __getattr__(self, name: str) -> Any:
        raise LLMError(f"unexpected model call: {name}")


@pytest.fixture
def tts() -> FakeTTS:
    return FakeTTS()


@pytest.fixture
def client(tmp_path: Path, tts: FakeTTS) -> Iterator[TestClient]:
    with closing(make_client(tmp_path, tts)) as c:
        yield c


def test_mock_mode_streams_the_demo_lesson_and_marks_it(client: TestClient) -> None:
    response = client.post("/explain-region", json=body())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers[DEMO_HEADER] == "1"
    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["meta"] + ["step"] * 7 + ["done"]
    assert events[0][1]["title"] == "Gauss's law"
    assert all(data["audio_url"].startswith("/audio/") for name, data in events if name == "step")


def test_voice_from_the_allow_list_reaches_tts(tmp_path: Path) -> None:
    voices: list[str] = []

    class RecordingTTS(FakeTTS):
        async def synthesize(self, text: str, voice: str, rate: str) -> bytes:
            voices.append(voice)
            return await super().synthesize(text, voice, rate)

    with closing(make_client(tmp_path, RecordingTTS())) as c:
        response = c.post("/explain-region", json=body(voice="en-GB-SoniaNeural"))

    assert response.status_code == 200
    assert voices and set(voices) == {"en-GB-SoniaNeural"}


def test_default_voice_comes_from_settings(tmp_path: Path) -> None:
    voices: list[str] = []

    class RecordingTTS(FakeTTS):
        async def synthesize(self, text: str, voice: str, rate: str) -> bytes:
            voices.append(voice)
            return await super().synthesize(text, voice, rate)

    with closing(make_client(tmp_path, RecordingTTS())) as c:
        c.post("/explain-region", json=body())

    assert set(voices) == {"en-US-AriaNeural"}


@pytest.mark.parametrize(
    "payload",
    [
        {"image_png_base64": "not base64!"},
        {"image_png_base64": base64.b64encode(b"GIF89a" + b"\x00" * 40).decode()},
        {"image_png_base64": ""},
        body(voice="en-US-SomeoneElse"),
        body(voice="'; rm -rf /"),
        body(extra_field=1),
        body(png(MAX_IMAGE_SIDE + 1, 2)),
        body(png(0, 2)),
        {},
    ],
)
def test_rejects_bad_requests(client: TestClient, payload: dict[str, Any]) -> None:
    assert client.post("/explain-region", json=payload).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"image_png_base64": base64.b64encode(b"GIF89a-secret-screen" * 40).decode()},
        body(png(MAX_IMAGE_SIDE + 1, 2)),
        body(extra_field=1),
        body(voice="en-US-SomeoneElse"),
        {"image_png_base64": "c2VjcmV0LXNjcmVlbg" * 200 + "!"},  # not valid base64
    ],
)
def test_errors_never_echo_the_screenshot(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post("/explain-region", json=payload)
    assert response.status_code == 422
    sent = payload["image_png_base64"]
    assert sent[:40] not in response.text
    assert all(set(e) == {"type", "loc", "msg"} for e in response.json()["detail"])
    assert response.json()["detail"][0]["loc"][0] == "body"


def test_malformed_json_does_not_echo_the_body(client: TestClient) -> None:
    raw = '{"image_png_base64": "' + "c2VjcmV0LXNjcmVlbg" * 200 + '"'  # missing brace
    response = client.post(
        "/explain-region", content=raw, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert "c2VjcmV0LXNjcmVlbg" not in response.text


def test_rejects_an_oversized_payload_before_decoding(client: TestClient) -> None:
    huge = "A" * (9 * 1024 * 1024 * 4 // 3)
    assert client.post("/explain-region", json={"image_png_base64": huge}).status_code == 422


def test_live_mode_says_not_yet_without_calling_the_model(tmp_path: Path) -> None:
    tts = FakeTTS()
    with closing(make_client(tmp_path, tts, mock_ai=False)) as c:
        c.app.dependency_overrides[get_lesson_llm] = ExplodingLLM  # type: ignore[attr-defined]
        response = c.post("/explain-region", json=body())

    assert response.status_code == 200
    assert DEMO_HEADER not in response.headers
    assert parse_sse(response.text) == [("error", {"message": NOT_YET})]
    assert tts.calls == 0


def test_the_screenshot_is_never_written(tmp_path: Path, tts: FakeTTS) -> None:
    marker = png(7, 5)
    with closing(make_client(tmp_path, tts)) as c:
        assert c.post("/explain-region", json=body(marker)).status_code == 200

    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert marker not in path.read_bytes(), path


def test_png_size_reads_the_header() -> None:
    assert png_size(png(13, 9)) == (13, 9)
    with pytest.raises(ValueError):
        png_size(b"\x89PNG\r\n\x1a\n")
