"""FastAPI entry point. Run with: uv run fastapi dev app/main.py"""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.settings import Settings, get_settings


class Health(BaseModel):
    status: str
    mock_ai: bool
    api_key_configured: bool


def create_app() -> FastAPI:
    app = FastAPI(title="Scribbly")

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
