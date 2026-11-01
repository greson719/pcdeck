"""
Unit tests for Cross-Site WebSocket Hijacking (CSWSH) and Origin Validation.
Verifies protections against cross-site browser requests, sandboxed desktop iframes,
and validates legitimate Android WebView and local client connections.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.main import app, get_pairing_token


@pytest.fixture
def client():
    return TestClient(app)


def test_api_ping_foreign_origin_redacts_token(client):
    """Foreign origins (e.g. evil.com) must NOT receive the pairing token."""
    res = client.get("/api/ping", headers={"origin": "http://evil.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["token"] == ""


def test_api_ping_sandboxed_desktop_iframe_redacts_token(client):
    """Desktop browsers sending Origin: null (<iframe sandbox="allow-scripts">) must NOT receive token."""
    res = client.get(
        "/api/ping",
        headers={
            "origin": "null",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["token"] == ""


def test_api_ping_android_webview_receives_token(client):
    """Android WebView sending Origin: null (file:///android_asset/) must receive the pairing token."""
    res = client.get(
        "/api/ping",
        headers={
            "origin": "null",
            "user-agent": "Mozilla/5.0 (Linux; U; Android 14; en-us; Pixel 7 Build/UQ1A.240205.002) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Mobile Safari/537.36",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["token"] == get_pairing_token()
    assert len(data["token"]) == 32


def test_websocket_foreign_origin_rejected(client):
    """WebSocket connection with foreign origin (e.g. http://evil.com) must be rejected with 4003."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws", headers={"origin": "http://evil.com"}):
            pass
    assert exc_info.value.code == 4003


def test_websocket_sandboxed_desktop_iframe_rejected(client):
    """WebSocket connection from desktop with Origin: null must be rejected with 4003."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws",
            headers={
                "origin": "null",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
        ):
            pass
    assert exc_info.value.code == 4003


def test_websocket_android_webview_allowed(client):
    """WebSocket connection from Android WebView with Origin: null must be allowed."""
    with client.websocket_connect(
        "/ws",
        headers={
            "origin": "null",
            "user-agent": "Mozilla/5.0 (Linux; U; Android 14; en-us; Pixel 7 Build/UQ1A.240205.002) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Mobile Safari/537.36",
        },
    ) as ws:
        ws.send_text("p,123")
        resp = ws.receive_text()
        if resp.startswith("pro_unlocked,"):
            resp = ws.receive_text()
        assert resp == "pong,123"
