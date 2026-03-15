import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zotero_server import server  # noqa: E402


def test_normalize_user_id_variants() -> None:
    assert server._normalize_user_id('"12345"') == "12345"
    assert server._normalize_user_id(" '67890' ") == "67890"
    assert server._normalize_user_id("abc123") == ""
    assert server._normalize_user_id(None) == ""


def test_resolve_user_id_from_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZOTERO_USER_ID", raising=False)
    monkeypatch.setenv("ZOTERO_USERID", " 24680 ")
    monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)

    assert server._resolve_user_id_from_env() == "24680"


@pytest.mark.asyncio
async def test_get_autodiscovers_user_id_and_avoids_blank_users_path() -> None:
    server.USER_ID = ""
    server.API_KEY = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/keys/current":
            return httpx.Response(200, json={"userID": "13579"})
        if request.url.path == "/users/13579/collections":
            return httpx.Response(200, json=[])
        if request.url.path == "/users//collections":
            return httpx.Response(500, json={"error": "blank user id path used"})
        return httpx.Response(404, json={"path": request.url.path})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://api.zotero.org") as client:
        data = await server._get(client, server._user_url("collections"))

    assert data == []
    assert server.USER_ID == "13579"


@pytest.mark.asyncio
async def test_ensure_user_id_raises_clear_error_without_config() -> None:
    server.USER_ID = ""
    server.API_KEY = ""

    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
    async with httpx.AsyncClient(transport=transport, base_url="https://api.zotero.org") as client:
        with pytest.raises(RuntimeError, match="unable to resolve ZOTERO_USER_ID"):
            await server._ensure_user_id(client)
