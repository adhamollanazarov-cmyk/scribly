from pathlib import Path

import pytest
from pydantic import ValidationError

from app.settings import REPO_ROOT, Settings


def test_env_file_is_anchored_to_repo_root() -> None:
    assert Settings.model_config["env_file"] == REPO_ROOT / ".env"
    assert Path(__file__).resolve().parents[2] == REPO_ROOT


def test_dotenv_loads_settings_from_another_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-dotenv-key\n"
        "LESSON_MODEL=lesson-from-file\n"
        "FAST_MODEL=fast-from-file\n"
        "MOCK_AI=1\n"
        "TTS_VOICE=voice-from-file\n"
        "UNRELATED_SETTING=ignored\n",
        encoding="utf-8",
    )
    other_dir = tmp_path / "server"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)

    settings = Settings()

    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "test-dotenv-key"
    assert settings.lesson_model == "lesson-from-file"
    assert settings.fast_model == "fast-from-file"
    assert settings.mock_ai is True
    assert settings.tts_voice == "voice-from-file"
    assert "test-dotenv-key" not in repr(settings)
    assert "test-dotenv-key" not in settings.model_dump_json()


def test_environment_overrides_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=file-key\nLESSON_MODEL=file-model\nMOCK_AI=0\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "shell-key")
    monkeypatch.setenv("LESSON_MODEL", "shell-model")
    monkeypatch.setenv("MOCK_AI", "1")

    settings = Settings(_env_file=env_file)

    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "shell-key"
    assert settings.lesson_model == "shell-model"
    assert settings.mock_ai is True


def test_invalid_mock_mode_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_AI", "not-a-boolean")

    with pytest.raises(ValidationError, match="mock_ai"):
        Settings(_env_file=None)
