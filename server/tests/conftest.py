import pytest

SETTING_VARS = (
    "ANTHROPIC_API_KEY",
    "LESSON_MODEL",
    "FAST_MODEL",
    "LESSON_THINKING",
    "LESSON_EFFORT",
    "LESSON_MAX_TOKENS",
    "MOCK_AI",
    "TTS_VOICE",
    "TTS_RATE",
    "AUDIO_CACHE_DIR",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's shell variables out of the tests."""
    for name in SETTING_VARS:
        monkeypatch.delenv(name, raising=False)
