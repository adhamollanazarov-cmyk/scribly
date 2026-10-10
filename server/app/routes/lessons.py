"""POST /lessons (SSE stream of meta, step, done, error) and GET /audio/{key}.mp3."""

import logging
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field

from app.lesson.fixtures import load_fixture
from app.lesson.models import Lesson, StreamedStep
from app.lesson.pipeline import LessonError, prepare_lesson
from app.settings import Settings, get_settings
from app.tts import AudioCache, EdgeTTSProvider, TTSError, TTSProvider

logger = logging.getLogger(__name__)
router = APIRouter()

NOT_AVAILABLE = "Lesson generation from the AI arrives in Phase 1b. Set MOCK_AI=1 for now."
GENERIC_ERROR = "Something went wrong while preparing the lesson. Please try again."


class LessonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["topic", "problem"]
    text: str = Field(min_length=1, max_length=5000)


def get_tts_provider() -> TTSProvider:
    return EdgeTTSProvider()


def get_audio_cache(settings: Annotated[Settings, Depends(get_settings)]) -> AudioCache:
    return AudioCache(settings.audio_cache_dir)


SettingsDep = Annotated[Settings, Depends(get_settings)]
TTSDep = Annotated[TTSProvider, Depends(get_tts_provider)]
CacheDep = Annotated[AudioCache, Depends(get_audio_cache)]


@router.post("/lessons", response_class=EventSourceResponse)
async def create_lesson(
    request: LessonRequest, settings: SettingsDep, tts: TTSDep, cache: CacheDep
) -> AsyncIterator[ServerSentEvent]:
    if not settings.mock_ai:
        yield error_event(NOT_AVAILABLE)
        return
    try:
        lesson, _ = prepare_lesson(load_fixture("gauss_law"))
    except LessonError as e:
        logger.error("Mock lesson failed: error_type=LessonError")
        yield error_event(str(e))
        return
    except Exception as e:
        logger.error("Mock lesson failed: error_type=%s", type(e).__name__)
        yield error_event(GENERIC_ERROR)
        return
    async for event in lesson_events(lesson, settings, tts, cache):
        yield event


async def lesson_events(
    lesson: Lesson, settings: Settings, tts: TTSProvider, cache: AudioCache
) -> AsyncIterator[ServerSentEvent]:
    meta = {"id": lesson.id, "title": lesson.title, "level": lesson.level}
    yield ServerSentEvent(event="meta", data=meta | {"step_count": len(lesson.steps)})
    for step in lesson.steps:
        audio_url = await narrate(step.say, settings, tts, cache)
        streamed = StreamedStep.model_validate(step.model_dump() | {"audio_url": audio_url})
        yield ServerSentEvent(event="step", data=streamed.model_dump(mode="json"))
    yield ServerSentEvent(event="done", data={"id": lesson.id})


async def narrate(text: str, settings: Settings, tts: TTSProvider, cache: AudioCache) -> str | None:
    """Audio URL for the narration, or None so the lesson continues without sound."""
    try:
        key = await cache.get_or_create(tts, text, settings.tts_voice, settings.tts_rate)
    except (TTSError, OSError) as e:
        logger.error("TTS failed, step will stream without audio: %s", type(e).__name__)
        return None
    return f"/audio/{key}.mp3"


def error_event(message: str) -> ServerSentEvent:
    return ServerSentEvent(event="error", data={"message": message})


@router.get("/audio/{key}.mp3")
def get_audio(key: str, cache: CacheDep) -> FileResponse:
    path = cache.path_for(key)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(
        path,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
