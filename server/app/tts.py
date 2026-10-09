"""Text-to-speech behind a small interface, with a file cache keyed by text+voice+rate."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Protocol

import edge_tts

AUDIO_KEY = re.compile(r"^[0-9a-f]{64}$")


class TTSError(RuntimeError):
    """Speech could not be produced."""


class TTSProvider(Protocol):
    async def synthesize(self, text: str, voice: str, rate: str) -> bytes:
        """Return MP3 bytes for `text`."""
        ...


class EdgeTTSProvider:
    async def synthesize(self, text: str, voice: str, rate: str) -> bytes:
        audio = bytearray()
        try:
            async for chunk in edge_tts.Communicate(text, voice, rate=rate).stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
        except Exception as e:  # edge-tts raises several unrelated network/protocol errors
            raise TTSError(f"edge-tts failed: {type(e).__name__}") from e
        if not audio:
            raise TTSError("edge-tts returned no audio")
        return bytes(audio)


def audio_key(text: str, voice: str, rate: str) -> str:
    payload = json.dumps([text, voice, rate], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AudioCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path_for(self, key: str) -> Path | None:
        """The file for a valid key, or None. Only hex keys can become paths."""
        if not AUDIO_KEY.fullmatch(key):
            return None
        return self.directory / f"{key}.mp3"

    async def get_or_create(self, provider: TTSProvider, text: str, voice: str, rate: str) -> str:
        key = audio_key(text, voice, rate)
        path = self.directory / f"{key}.mp3"
        if not path.is_file():
            audio = await provider.synthesize(text, voice, rate)
            self._write_atomic(path, audio)
        return key

    def _write_atomic(self, path: Path, data: bytes) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
