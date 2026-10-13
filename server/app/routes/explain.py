"""POST /explain-region: the desktop overlay sends a captured screen region (PNG).

Until Phase 4 (vision) this only serves a demo lesson in mock mode: the library lesson for
the optional `topic` (the overlay's "Demo topics"), else the Gauss fixture. The image is
validated and then dropped: it is never written to disk or logged.
"""

import base64
import binascii
import logging
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Depends, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.lesson.fixtures import DEFAULT_FIXTURE, load_fixture
from app.lesson.models import Lesson
from app.lesson.pipeline import LessonError, prepare_lesson
from app.library import find_library_lesson
from app.routes.lessons import (
    GENERIC_ERROR,
    CacheDep,
    SettingsDep,
    TTSDep,
    error_event,
    lesson_events,
)

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_SIDE = 4096
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
NOT_YET = "Explaining a screen region arrives in Phase 4. Set MOCK_AI=1 for the demo lesson."
DEMO_HEADER = "X-Scribbly-Demo"

# edge-tts voices offered in the overlay settings.
Voice = Literal["en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"]


def png_size(data: bytes) -> tuple[int, int]:
    """Width and height from the PNG header; ValueError if `data` is not a PNG."""
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise ValueError("image must be a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


class RegionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Base64 of a PNG: 4 characters per 3 bytes.
    image_png_base64: str = Field(min_length=1, max_length=(MAX_IMAGE_BYTES + 2) // 3 * 4)
    voice: Voice | None = None
    # A library topic title, until Phase 4 reads the topic from the image.
    topic: str | None = Field(default=None, max_length=200)

    @field_validator("image_png_base64")
    @classmethod
    def check_png(cls, value: str) -> str:
        try:
            data = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("image must be base64") from None
        width, height = png_size(data)
        if not (0 < width <= MAX_IMAGE_SIDE and 0 < height <= MAX_IMAGE_SIDE):
            raise ValueError(f"image sides must be 1–{MAX_IMAGE_SIDE} px")
        return value


def demo_lesson(topic: str | None) -> Lesson:
    """The library lesson for `topic`, or the Gauss fixture when there is none or no match."""
    found = find_library_lesson(topic) if topic else None
    return found or prepare_lesson(load_fixture(DEFAULT_FIXTURE))[0]


def mark_demo(response: Response, settings: SettingsDep) -> None:
    """Runs before streaming starts, so the header reaches the SSE response."""
    if settings.mock_ai:
        response.headers[DEMO_HEADER] = "1"


@router.post(
    "/explain-region", response_class=EventSourceResponse, dependencies=[Depends(mark_demo)]
)
async def explain_region(
    request: RegionRequest,
    settings: SettingsDep,
    tts: TTSDep,
    cache: CacheDep,
) -> AsyncIterator[ServerSentEvent]:
    voice, topic = request.voice, request.topic
    del request  # the screenshot is not kept beyond validation
    if not settings.mock_ai:
        yield error_event(NOT_YET)
        return
    try:
        lesson = demo_lesson(topic)
    except LessonError as e:
        logger.error("Demo region lesson failed: error_type=LessonError")
        yield error_event(str(e))
        return
    except Exception as e:
        logger.error("Demo region lesson failed: error_type=%s", type(e).__name__)
        yield error_event(GENERIC_ERROR)
        return
    async for event in lesson_events(lesson, settings, tts, cache, voice):
        yield event
