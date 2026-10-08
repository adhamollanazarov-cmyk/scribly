import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from app import main, model_check
from tests.test_model_check import fake_client, model, models_page, run_check, settings

Handler = Callable[[httpx2.Request], httpx2.Response | Awaitable[httpx2.Response]]


def install_client_factory(
    monkeypatch: pytest.MonkeyPatch, handler: Handler
) -> list[anthropic.AsyncAnthropic]:
    """Exercise production client options with an in-memory HTTP transport."""
    real_client = anthropic.AsyncAnthropic
    clients: list[anthropic.AsyncAnthropic] = []

    def construct(**kwargs: Any) -> anthropic.AsyncAnthropic:
        http_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
        client = real_client(http_client=http_client, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(anthropic, "AsyncAnthropic", construct)
    return clients


@pytest.mark.parametrize("status_code", [200, 429, 500])
def test_owned_client_is_closed_and_requests_are_not_retried(
    status_code: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if status_code == 200:
            return models_page("claude-sonnet-5-5", "claude-haiku-5-5")(request)
        return httpx2.Response(status_code, json={"error": {"message": "unavailable"}})

    clients = install_client_factory(monkeypatch, handler)

    assert run_check(settings(anthropic_api_key="test-key")) == []
    assert len(requests) == 1
    assert len(clients) == 1
    assert clients[0].max_retries == 0
    assert clients[0].timeout == 10.0
    assert clients[0].is_closed()


def test_injected_client_remains_caller_owned() -> None:
    async def run() -> None:
        async with fake_client(models_page("claude-sonnet-5-5", "claude-haiku-5-5")) as client:
            assert await model_check.check_models(settings(), client) == []
            assert not client.is_closed()
        assert client.is_closed()

    asyncio.run(run())


def test_one_total_deadline_covers_pagination_and_closes_client(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    real_timeout = asyncio.timeout
    deadlines: list[asyncio.Timeout] = []
    budgets: list[float] = []
    requests: list[httpx2.Request] = []

    def record_timeout(delay: float) -> asyncio.Timeout:
        budgets.append(delay)
        deadline = real_timeout(delay)
        deadlines.append(deadline)
        return deadline

    async def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if len(requests) == 1:
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
        assert len(deadlines) == 1
        # Expire the real outer deadline without spending ten seconds in a test.
        deadlines[0].reschedule(asyncio.get_running_loop().time() - 1)
        await asyncio.Event().wait()
        raise AssertionError("The total deadline must cancel the stalled second page")

    monkeypatch.setattr(model_check.asyncio, "timeout", record_timeout)
    clients = install_client_factory(monkeypatch, handler)

    assert run_check(settings(anthropic_api_key="test-key")) == []
    assert budgets == [10.0]
    assert len(requests) == 2
    assert deadlines[0].expired()
    assert clients[0].is_closed()
    assert "status=unavailable error_type=TimeoutError" in caplog.text


def test_total_timeout_allows_app_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    real_timeout = asyncio.timeout
    budgets: list[float] = []

    def expire_immediately(delay: float) -> asyncio.Timeout:
        budgets.append(delay)
        return real_timeout(0)

    async def stalled(request: httpx2.Request) -> httpx2.Response:
        await asyncio.Event().wait()
        raise AssertionError("The startup timeout must cancel this request")

    clients = install_client_factory(monkeypatch, stalled)
    app_settings = settings(anthropic_api_key="test-key")
    monkeypatch.setattr(main, "get_settings", lambda: app_settings)
    monkeypatch.setattr(model_check.asyncio, "timeout", expire_immediately)

    with TestClient(main.create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    assert budgets == [10.0]
    assert clients[0].is_closed()


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, "AuthenticationError"),
        (403, "PermissionDeniedError"),
        (429, "RateLimitError"),
        (500, "InternalServerError"),
    ],
)
def test_provider_error_logs_only_status_and_sdk_type(
    status_code: int, error_type: str, caplog: pytest.LogCaptureFixture
) -> None:
    sensitive = "synthetic-private-key-and-screenshot-content"

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            status_code,
            json={"error": {"type": sensitive, "message": f"{sensitive}\nforged log entry"}},
            headers={"request-id": sensitive},
        )

    assert run_check(settings(), handler) == []
    messages = [r.getMessage() for r in caplog.records if r.name == model_check.__name__]
    assert messages == [f"Model check failed: status={status_code} error_type={error_type}"]
    assert sensitive not in caplog.text
    assert "forged log entry" not in caplog.text


@pytest.mark.parametrize(
    ("transport_error", "error_type"),
    [(httpx2.ConnectError, "APIConnectionError"), (httpx2.ReadTimeout, "APITimeoutError")],
)
def test_transport_error_messages_are_not_logged(
    transport_error: type[httpx2.RequestError],
    error_type: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive = "synthetic-private-transport-content"

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise transport_error(sensitive, request=request)

    assert run_check(settings(), handler) == []
    assert f"status=unavailable error_type={error_type}" in caplog.text
    assert sensitive not in caplog.text
