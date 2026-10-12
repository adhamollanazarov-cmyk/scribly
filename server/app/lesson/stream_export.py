"""Render shared/streams/<fixture>.json: the SSE events mock mode sends for each fixture.

The web tests replay these files, so the renderer is tested on exactly what the server
streams (templates expanded, calcs verified). Audio URLs use the default voice and rate.
"""

import json
from typing import Any

from app.lesson.fixtures import fixture_names, load_fixture
from app.lesson.models import Lesson, StreamedStep
from app.lesson.pipeline import prepare_lesson
from app.settings import REPO_ROOT, Settings
from app.tts import audio_key

STREAMS_DIR = REPO_ROOT / "shared" / "streams"


def lesson_meta(lesson: Lesson, step_count: int | None) -> dict[str, Any]:
    return {"id": lesson.id, "title": lesson.title, "level": lesson.level, "step_count": step_count}


def render_stream(name: str) -> str:
    lesson, _ = prepare_lesson(load_fixture(name))
    voice = Settings.model_fields["tts_voice"].default
    rate = Settings.model_fields["tts_rate"].default
    events: list[dict[str, Any]] = [
        {"event": "meta", "data": lesson_meta(lesson, len(lesson.steps))}
    ]
    for step in lesson.steps:
        audio_url = f"/audio/{audio_key(step.say, voice, rate)}.mp3"
        streamed = StreamedStep.model_validate(step.model_dump() | {"audio_url": audio_url})
        events.append({"event": "step", "data": streamed.model_dump(mode="json")})
    events.append({"event": "done", "data": {"id": lesson.id}})
    return json.dumps(events, indent=2, ensure_ascii=False) + "\n"


def write_streams() -> list[str]:
    STREAMS_DIR.mkdir(parents=True, exist_ok=True)
    names = fixture_names()
    for stale in STREAMS_DIR.glob("*.json"):
        if stale.stem not in names:
            stale.unlink()
    for name in names:
        (STREAMS_DIR / f"{name}.json").write_text(
            render_stream(name), encoding="utf-8", newline="\n"
        )
    return names
