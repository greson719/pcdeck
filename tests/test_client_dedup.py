"""
Unit tests for unique client deduplication and zombie connection pruning.
Verifies that multiple WebSocket connections or reconnects from the same physical device IP
are cleanly deduplicated to 1 client, and stale connections are superseded.
"""

import pytest
from unittest.mock import MagicMock
from starlette.websockets import WebSocketState
from server.main import (
    active_connections,
    screen_connections,
    get_connected_client_ips,
    get_unique_client_count,
    app,
)
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def clean_connections():
    """Ensure connection sets are pristine before and after each test."""
    active_connections.clear()
    screen_connections.clear()
    yield
    active_connections.clear()
    screen_connections.clear()


def make_mock_ws(ip="192.168.1.50", state=WebSocketState.CONNECTED):
    ws = MagicMock()
    ws.client.host = ip
    ws.client_state = state
    return ws


def test_single_device_multiple_reconnects_deduplicated():
    """A phone reconnecting 3 times (same IP) must count as exactly 1 client, not 3."""
    ws1 = make_mock_ws("192.168.1.105")
    ws2 = make_mock_ws("192.168.1.105")
    ws3 = make_mock_ws("192.168.1.105")

    active_connections.add(ws1)
    active_connections.add(ws2)
    active_connections.add(ws3)

    assert len(active_connections) == 3
    assert get_unique_client_count() == 1
    assert get_connected_client_ips() == {"192.168.1.105"}


def test_multiple_distinct_devices_counted_correctly():
    """Two different phones (different IPs) must count as 2 clients."""
    phone_a = make_mock_ws("192.168.1.105")
    phone_b = make_mock_ws("192.168.1.106")

    active_connections.add(phone_a)
    active_connections.add(phone_b)

    assert get_unique_client_count() == 2
    assert get_connected_client_ips() == {"192.168.1.105", "192.168.1.106"}


def test_control_and_screen_connections_from_same_device_deduplicated():
    """When 1 phone opens both control (/ws) and screen (/ws/screen), count remains 1."""
    ws_control = make_mock_ws("192.168.1.105")
    ws_screen = make_mock_ws("192.168.1.105")

    active_connections.add(ws_control)
    screen_connections.add(ws_screen)

    assert get_unique_client_count() == 1


def test_disconnected_zombie_sockets_auto_pruned():
    """Sockets marked DISCONNECTED are removed from active sets automatically."""
    live_ws = make_mock_ws("192.168.1.105", WebSocketState.CONNECTED)
    dead_ws = make_mock_ws("192.168.1.200", WebSocketState.DISCONNECTED)

    active_connections.add(live_ws)
    active_connections.add(dead_ws)

    assert get_unique_client_count() == 1
    assert dead_ws not in active_connections


def test_api_info_reports_unique_clients():
    """GET /api/info returns deduplicated clients_connected count."""
    client = TestClient(app)
    ws1 = make_mock_ws("192.168.1.105")
    ws2 = make_mock_ws("192.168.1.105")
    active_connections.add(ws1)
    active_connections.add(ws2)

    res = client.get("/api/info")
    assert res.status_code == 200
    data = res.json()
    assert data["clients_connected"] == 1


def test_api_desktop_status_reports_unique_clients():
    """GET /api/desktop/status returns deduplicated client_count and unique client list."""
    client = TestClient(app)
    ws1 = make_mock_ws("192.168.1.105")
    ws2 = make_mock_ws("192.168.1.105")
    active_connections.add(ws1)
    active_connections.add(ws2)

    res = client.get("/api/desktop/status")
    assert res.status_code == 200
    data = res.json()
    assert data["client_count"] == 1
    assert len(data["clients"]) == 1
    assert data["clients"][0]["ip"] == "192.168.1.105"
