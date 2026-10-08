import pytest

SETTING_VARS = ("ANTHROPIC_API_KEY", "LESSON_MODEL", "FAST_MODEL", "MOCK_AI", "TTS_VOICE")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's shell variables out of the tests."""
    for name in SETTING_VARS:
        monkeypatch.delenv(name, raising=False)
