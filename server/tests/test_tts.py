import asyncio
from pathlib import Path

import pytest

from app.tts import AudioCache, EdgeTTSProvider, TTSError, audio_key


class CountingTTS:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def synthesize(self, text: str, voice: str, rate: str) -> bytes:
        self.calls.append((text, voice, rate))
        return b"ID3fake-mp3:" + text.encode()


class BrokenTTS:
    async def synthesize(self, text: str, voice: str, rate: str) -> bytes:
        raise TTSError("offline")


def test_key_is_stable_hex_and_depends_on_every_input() -> None:
    key = audio_key("Hello", "en-US-AriaNeural", "+0%")

    assert key == audio_key("Hello", "en-US-AriaNeural", "+0%")
    assert len(key) == 64 and all(c in "0123456789abcdef" for c in key)
    assert len({key, audio_key("Hello!", "en-US-AriaNeural", "+0%"),
                audio_key("Hello", "en-US-GuyNeural", "+0%"),
                audio_key("Hello", "en-US-AriaNeural", "+10%")}) == 4  # fmt: skip


def test_cache_miss_writes_file_and_hit_skips_provider(tmp_path: Path) -> None:
    cache, tts = AudioCache(tmp_path / "audio"), CountingTTS()

    first = asyncio.run(cache.get_or_create(tts, "Hi", "v", "+0%"))
    second = asyncio.run(cache.get_or_create(tts, "Hi", "v", "+0%"))

    assert first == second
    assert len(tts.calls) == 1
    path = cache.path_for(first)
    assert path is not None and path.read_bytes() == b"ID3fake-mp3:Hi"
    assert [p.name for p in (tmp_path / "audio").iterdir()] == [f"{first}.mp3"]  # no temp left


def test_provider_failure_writes_nothing(tmp_path: Path) -> None:
    cache = AudioCache(tmp_path)

    with pytest.raises(TTSError):
        asyncio.run(cache.get_or_create(BrokenTTS(), "Hi", "v", "+0%"))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "key", ["", "abc", "../../etc/passwd", "A" * 64, "g" * 64, "a" * 63, "a" * 65, "a" * 64 + "\n"]
)
def test_path_for_rejects_anything_but_64_hex_chars(tmp_path: Path, key: str) -> None:
    assert AudioCache(tmp_path).path_for(key) is None


@pytest.mark.parametrize("failure", [PermissionError("locked"), asyncio.CancelledError()])
def test_failed_atomic_replace_preserves_old_file_and_removes_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: BaseException
) -> None:
    cache = AudioCache(tmp_path)
    path = tmp_path / ("0" * 64 + ".mp3")
    path.write_bytes(b"old audio")

    def fail_replace(source: str, target: Path) -> None:
        # Reading the temp file here also exercises closed file handles on Windows.
        assert Path(source).read_bytes() == b"new audio"
        raise failure

    monkeypatch.setattr("app.tts.os.replace", fail_replace)
    with pytest.raises(type(failure)):
        cache._write_atomic(path, b"new audio")

    assert path.read_bytes() == b"old audio"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("has_audio", [True, False])
def test_edge_provider_collects_only_audio_chunks(
    monkeypatch: pytest.MonkeyPatch, has_audio: bool
) -> None:
    from collections.abc import AsyncIterator
    from typing import Any

    class Communicate:
        def __init__(self, text: str, voice: str, *, rate: str) -> None:
            assert (text, voice, rate) == ("Hi", "v", "+0%")

        async def stream(self) -> AsyncIterator[dict[str, Any]]:
            yield {"type": "WordBoundary", "text": "private text"}
            if has_audio:
                yield {"type": "audio", "data": b"ID3"}
                yield {"type": "audio", "data": b"audio"}

    monkeypatch.setattr("app.tts.edge_tts.Communicate", Communicate)
    if has_audio:
        assert asyncio.run(EdgeTTSProvider().synthesize("Hi", "v", "+0%")) == b"ID3audio"
    else:
        with pytest.raises(TTSError, match="after two attempts"):
            asyncio.run(EdgeTTSProvider().synthesize("Hi", "v", "+0%"))
