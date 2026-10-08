import asyncio
import logging
from collections.abc import Callable
from typing import Any

import anthropic
import httpx2
import pytest

from app.model_check import check_models, missing_models
from app.settings import Settings

Handler = Callable[[httpx2.Request], httpx2.Response]


def model(model_id: str) -> dict[str, Any]:
    return {
        "type": "model",
        "id": model_id,
        "display_name": model_id,
        "created_at": "2026-01-01T00:00:00Z",
    }


def models_page(*ids: str) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/models"
        body = {"data": [model(i) for i in ids], "has_more": False, "first_id": None}
        return httpx2.Response(200, json=body)

    return handler


def fake_client(handler: Handler) -> anthropic.AsyncAnthropic:
    http_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return anthropic.AsyncAnthropic(api_key="test-key", http_client=http_client, max_retries=0)


def settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "_env_file": None,
        "lesson_model": "claude-sonnet-5-5",
        "fast_model": "claude-haiku-5-5",
        "mock_ai": False,
    }
    return Settings(**(defaults | overrides))


def run_check(s: Settings, handler: Handler | None = None) -> list[str]:
    client = fake_client(handler) if handler else None
    return asyncio.run(check_models(s, client))


def test_missing_models_keeps_order() -> None:
    assert missing_models(["a", "b", "c"], ["b"]) == ["a", "c"]


def test_all_models_available_logs_nothing(caplog: pytest.LogCaptureFixture) -> None:
    handler = models_page("claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5")

    assert run_check(settings(), handler) == []
    assert caplog.records == []


def test_missing_model_logs_clear_error(caplog: pytest.LogCaptureFixture) -> None:
    handler = models_page("claude-sonnet-5-5")

    assert run_check(settings(), handler) == ["claude-haiku-5-5"]
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.ERROR
    assert "FAST_MODEL=claude-haiku-5-5" in record.getMessage()
    assert "claude-sonnet-5-5" in record.getMessage()  # lists what is available


def test_mock_mode_skips_api_call() -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("Models API must not be called in mock mode")

    assert run_check(settings(mock_ai=True), fail) == []


def test_missing_api_key_logs_error(caplog: pytest.LogCaptureFixture) -> None:
    assert run_check(settings(anthropic_api_key=None)) == []
    assert "ANTHROPIC_API_KEY is not set" in caplog.text


def test_rejected_key_logs_error_without_raising(caplog: pytest.LogCaptureFixture) -> None:
    def unauthorized(request: httpx2.Request) -> httpx2.Response:
        body = {"type": "error", "error": {"type": "authentication_error", "message": "bad"}}
        return httpx2.Response(401, json=body)

    assert run_check(settings(), unauthorized) == []
    assert "rejected (401)" in caplog.text


def test_network_failure_logs_error_without_raising(caplog: pytest.LogCaptureFixture) -> None:
    def offline(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("offline", request=request)

    assert run_check(settings(), offline) == []
    assert "could not reach the Anthropic API" in caplog.text
