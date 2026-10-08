"""FastAPI entry point. Run with: uv run fastapi dev app/main.py"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.model_check import check_models
from app.settings import Settings, get_settings

# "LEVEL: message", like uvicorn, so app errors stand out in the dev console.
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


class Health(BaseModel):
    status: str
    mock_ai: bool
    api_key_configured: bool


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await check_models(get_settings())
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Scribbly", lifespan=lifespan)

    @app.get("/health")
    def health(settings: Annotated[Settings, Depends(get_settings)]) -> Health:
        key = settings.anthropic_api_key
        return Health(
            status="ok",
            mock_ai=settings.mock_ai,
            api_key_configured=bool(key and key.get_secret_value()),
        )

    return app


app = create_app()
