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
    async def run() -> list[str]:
        if handler is None:
            return await check_models(s)
        async with fake_client(handler) as client:
            return await check_models(s, client)

    return asyncio.run(run())


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
    assert "status=401 error_type=AuthenticationError" in caplog.text


def test_network_failure_logs_error_without_raising(caplog: pytest.LogCaptureFixture) -> None:
    def offline(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("offline", request=request)

    assert run_check(settings(), offline) == []
    assert "status=unavailable error_type=APIConnectionError" in caplog.text


@pytest.mark.parametrize("status_code", [403, 429, 500, 503])
def test_status_errors_do_not_stop_startup(
    status_code: int, caplog: pytest.LogCaptureFixture
) -> None:
    def unavailable(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            status_code,
            json={"type": "error", "error": {"type": "api_error", "message": "unavailable"}},
        )

    assert run_check(settings(), unavailable) == []
    assert f"status={status_code} error_type=" in caplog.text


def test_timeout_is_nonfatal(caplog: pytest.LogCaptureFixture) -> None:
    def timeout(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=request)

    assert run_check(settings(), timeout) == []
    assert "status=unavailable error_type=APITimeoutError" in caplog.text


def test_models_on_later_pages_are_not_reported_missing(caplog: pytest.LogCaptureFixture) -> None:
    requests: list[httpx2.Request] = []

    def paginated(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        assert request.url.path == "/v1/models"
        if len(requests) == 1:
            assert "after_id" not in request.url.params
            return httpx2.Response(
                200,
                json={
                    "data": [model("claude-sonnet-5-5")],
                    "has_more": True,
                    "first_id": "claude-sonnet-5-5",
                    "last_id": "claude-sonnet-5-5",
                },
            )
        assert len(requests) == 2
        assert request.url.params["after_id"] == "claude-sonnet-5-5"
        return httpx2.Response(
            200,
            json={
                "data": [model("claude-haiku-5-5")],
                "has_more": False,
                "first_id": "claude-haiku-5-5",
                "last_id": "claude-haiku-5-5",
            },
        )

    assert run_check(settings(), paginated) == []
    assert len(requests) == 2
    assert caplog.records == []


def test_mock_mode_does_not_construct_a_client(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_client(**kwargs: Any) -> None:
        raise AssertionError("Mock mode must not create an API client")

    monkeypatch.setattr(anthropic, "AsyncAnthropic", forbidden_client)

    assert run_check(settings(mock_ai=True, anthropic_api_key="test-key")) == []


def test_empty_api_key_logs_error(caplog: pytest.LogCaptureFixture) -> None:
    assert run_check(settings(anthropic_api_key="")) == []
    assert "ANTHROPIC_API_KEY is not set" in caplog.text
