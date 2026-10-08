import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings, get_settings


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
    assert settings.fast_model == "claude-haiku-5-5"
    assert settings.tts_voice == "en-US-AriaNeural"


def test_app_starts_in_mock_mode_without_api_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_AI", "1")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:  # runs the startup model check
        assert client.get("/health").json()["mock_ai"] is True

    get_settings.cache_clear()
