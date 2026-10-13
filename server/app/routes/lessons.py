"""POST /lessons (SSE stream of meta, step, done, error) and GET /audio/{key}.mp3."""

import logging
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field

from app.lesson.claude import ClaudeLessonLLM, LessonLLM
from app.lesson.fixtures import DEFAULT_FIXTURE, fixture_for_text, load_fixture
from app.lesson.generate import Header, generate_lesson
from app.lesson.models import Lesson, Source, StreamedStep
from app.lesson.pipeline import LessonError, prepare_lesson
from app.lesson.stream_export import lesson_meta
from app.library import find_library_lesson
from app.settings import Settings, get_settings
from app.tts import AudioCache, EdgeTTSProvider, TTSError, TTSProvider

logger = logging.getLogger(__name__)
router = APIRouter()

NO_KEY = "ANTHROPIC_API_KEY is not set on the server. Add it to .env, or set MOCK_AI=1."
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


def get_lesson_llm(settings: SettingsDep) -> LessonLLM:
    return ClaudeLessonLLM(settings)


LLMDep = Annotated[LessonLLM, Depends(get_lesson_llm)]


def mock_lesson(text: str) -> Lesson:
    """Mock mode: the fixture with this source text, else a library topic, else Gauss."""
    name = fixture_for_text(text)
    found = find_library_lesson(text) if name == DEFAULT_FIXTURE else None
    return found or prepare_lesson(load_fixture(name))[0]


@router.post("/lessons", response_class=EventSourceResponse)
async def create_lesson(
    request: LessonRequest, settings: SettingsDep, tts: TTSDep, cache: CacheDep, llm: LLMDep
) -> AsyncIterator[ServerSentEvent]:
    if not settings.mock_ai:
        async for event in live_lesson_events(request, settings, tts, cache, llm):
            yield event
        return
    try:
        lesson = mock_lesson(request.text)
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
    lesson: Lesson,
    settings: Settings,
    tts: TTSProvider,
    cache: AudioCache,
    voice: str | None = None,
) -> AsyncIterator[ServerSentEvent]:
    yield ServerSentEvent(event="meta", data=lesson_meta(lesson, len(lesson.steps)))
    for step in lesson.steps:
        audio_url = await narrate(step.say, settings, tts, cache, voice)
        streamed = StreamedStep.model_validate(step.model_dump() | {"audio_url": audio_url})
        yield ServerSentEvent(event="step", data=streamed.model_dump(mode="json"))
    yield ServerSentEvent(event="done", data={"id": lesson.id})


async def live_lesson_events(
    request: LessonRequest, settings: Settings, tts: TTSProvider, cache: AudioCache, llm: LessonLLM
) -> AsyncIterator[ServerSentEvent]:
    """Steps from the model, each narrated as soon as it is checked."""
    if settings.anthropic_api_key is None or not settings.anthropic_api_key.get_secret_value():
        yield error_event(NO_KEY)
        return
    source = Source(type=request.type, text=request.text)
    lesson_id = None
    try:
        async for event in generate_lesson(source, llm):
            if isinstance(event, Header):
                lesson_id = event.id
                meta = {"id": event.id, "title": event.title, "level": event.level}
                yield ServerSentEvent(event="meta", data=meta | {"step_count": None})
                continue
            audio_url = await narrate(event.say, settings, tts, cache)
            streamed = StreamedStep.model_validate(event.model_dump() | {"audio_url": audio_url})
            yield ServerSentEvent(event="step", data=streamed.model_dump(mode="json"))
    except LessonError as e:
        logger.error("Live lesson failed: error_type=LessonError")
        yield error_event(str(e))
        return
    except Exception as e:
        logger.error("Live lesson failed: error_type=%s", type(e).__name__)
        yield error_event(GENERIC_ERROR)
        return
    yield ServerSentEvent(event="done", data={"id": lesson_id})


async def narrate(
    text: str, settings: Settings, tts: TTSProvider, cache: AudioCache, voice: str | None = None
) -> str | None:
    """Audio URL for the narration, or None so the lesson continues without sound."""
    try:
        key = await cache.get_or_create(tts, text, voice or settings.tts_voice, settings.tts_rate)
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
