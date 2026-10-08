import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings, get_settings

SETTING_VARS = ("ANTHROPIC_API_KEY", "LESSON_MODEL", "FAST_MODEL", "MOCK_AI", "TTS_VOICE")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's shell variables out of the tests."""
    for name in SETTING_VARS:
        monkeypatch.delenv(name, raising=False)


def client_with(settings: Settings) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_health_ok() -> None:
    response = client_with(Settings(_env_file=None)).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_mock_mode() -> None:
    response = client_with(Settings(_env_file=None, mock_ai=True)).get("/health")

    assert response.json()["mock_ai"] is True


def test_health_never_leaks_api_key() -> None:
    settings = Settings(_env_file=None, anthropic_api_key="sk-ant-secret-123")
    response = client_with(settings).get("/health")

    assert response.json()["api_key_configured"] is True
    assert "sk-ant-secret-123" not in response.text


def test_settings_read_mock_ai_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_AI", "1")

    assert Settings(_env_file=None).mock_ai is True


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.lesson_model == "claude-sonnet-5-5"
    assert settings.fast_model == "claude-haiku-4-5"
    assert settings.tts_voice == "en-US-AriaNeural"
