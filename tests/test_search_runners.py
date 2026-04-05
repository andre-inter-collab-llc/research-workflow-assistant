from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

# Ensure local shared package is importable without editable install
_SHARED_SRC = Path(__file__).resolve().parents[1] / "mcp-servers" / "_shared" / "src"
if str(_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(_SHARED_SRC))

from rwa_result_store import search_runners  # noqa: E402


def test_request_with_retries_retries_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_runners.time, "sleep", lambda _seconds: None)

    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        response = search_runners._request_with_retries(
            client,
            "GET",
            "https://example.org/test",
        )

    assert response.status_code == 200
    assert attempts["count"] == 2


def test_request_with_retries_retries_on_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(search_runners.time, "sleep", lambda _seconds: None)

    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ConnectError("temporary network issue", request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        response = search_runners._request_with_retries(
            client,
            "GET",
            "https://example.org/test",
        )

    assert response.status_code == 200
    assert attempts["count"] == 2


def test_run_europe_pmc_raises_on_version_only_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(search_runners.time, "sleep", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        assert "query" in request.url.params
        return httpx.Response(200, json={"version": "6.9"}, request=request)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(search_runners.httpx, "Client", client_factory)

    with pytest.raises(RuntimeError, match="version-only response"):
        search_runners.run_europe_pmc(
            project_path=str(tmp_path),
            query="latent syphilis",
        )
