"""
Unit and Integration Tests for PCDeck Silent Cryptographic Pairing Token Engine
Validates token generation, persistence, remote authorization, and WebSocket verification.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.main import app, get_pairing_token, is_trusted_client


@pytest.fixture
def client():
    return TestClient(app)


def test_pairing_token_format_and_persistence():
    """Verify pairing token is a 32-character hex string and persists across calls."""
    tok1 = get_pairing_token()
    assert isinstance(tok1, str)
    assert len(tok1) == 32
    assert all(c in "0123456789abcdefABCDEF" for c in tok1)

    tok2 = get_pairing_token()
    assert tok1 == tok2


def test_is_trusted_client_loopback():
    """Verify local loopback connections are trusted unconditionally."""
    assert is_trusted_client("127.0.0.1", None) is True
    assert is_trusted_client("::1", None) is True
    assert is_trusted_client("localhost", None) is True
    assert is_trusted_client("testclient", None) is True


def test_is_trusted_client_remote():
    """Verify remote LAN connections require valid cryptographic token."""
    valid_token = get_pairing_token()
    remote_ip = "192.168.1.55"

    # Authorized with valid token
    assert is_trusted_client(remote_ip, valid_token) is True
    assert is_trusted_client(remote_ip, f" {valid_token} ") is True

    # Rejected without token or with bad token
    assert is_trusted_client(remote_ip, None) is False
    assert is_trusted_client(remote_ip, "") is False
    assert is_trusted_client(remote_ip, "hacker_token_123") is False


def test_websocket_pairing_with_token(client):
    """Test connecting to /ws with valid pairing token query parameter."""
    token = get_pairing_token()
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_text("p,100")
        resp = ws.receive_text()
        assert resp == "pong,100"
