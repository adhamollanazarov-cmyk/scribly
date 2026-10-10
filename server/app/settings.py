"""Typed settings read from the repo-root .env file and the environment."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: SecretStr | None = None
    lesson_model: str = "claude-sonnet-5-5"
    fast_model: str = "claude-haiku-5-5"
    # Sonnet 5.5 rejects thinking "disabled"; "between_tools" is its no-thinking mode and
    # needs effort high or lower. "adaptive" thinks first (slower first step).
    lesson_thinking: Literal["between_tools", "adaptive"] = "between_tools"
    lesson_effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    lesson_max_tokens: int = 32000
    mock_ai: bool = False
    tts_voice: str = "en-US-AriaNeural"
    tts_rate: str = "+0%"
    audio_cache_dir: Path = REPO_ROOT / "server" / ".cache" / "audio"


@lru_cache
def get_settings() -> Settings:
    return Settings()
