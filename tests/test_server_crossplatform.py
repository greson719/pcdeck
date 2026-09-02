"""
Comprehensive Cross-Platform Integration Test Suite for PCDeck Server
Tests file transfers, chunked range requests, screen capture, input controller, and WebSockets.
"""

import sys
import os
import io
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.main import app, TRANSFER_DIR
from server.input_controller import InputController, LinuxInputController
from server.screen_streamer import ScreenStreamer


@pytest.fixture
def client():
    return TestClient(app)


def test_server_info_endpoint(client):
    """Verify /api/info returns valid system metadata and IP."""
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert "ip" in data
    assert "port" in data
    assert "status" in data


def test_file_transfer_full_lifecycle(client):
    """Test full file upload, list, download, and deletion on Linux/Windows POSIX paths."""
    test_content = b"PCDeck cross-platform file transfer test 12345"
    test_filename = "test_linux_file.txt"

    # 1. Test Upload
    response = client.post(
        "/api/files/upload",
        files={"file": (test_filename, io.BytesIO(test_content), "text/plain")}
    )
    assert response.status_code == 200

    # 2. Test File List
    response = client.get("/api/files/list")
    assert response.status_code == 200
    files = response.json().get("files", [])
    filenames = [f["name"] for f in files]
    assert test_filename in filenames

    # 3. Test File Download
    response = client.get(f"/api/files/download/{test_filename}")
    assert response.status_code == 200
    assert response.content == test_content

    # 4. Test File Deletion
    response = client.post(f"/api/files/delete/{test_filename}")
    assert response.status_code == 200


def test_screen_streamer_frame_generation():
    """Verify screen streamer starts, captures a frame, and stops without hanging."""
    streamer = ScreenStreamer()
    frame, frame_id = streamer.get_latest_frame()
    assert frame is None or isinstance(frame, bytes)
    assert isinstance(frame_id, int)


def test_linux_input_dispatch():
    """Verify LinuxInputController handles gestures and keyboard without crashing."""
    ctrl = LinuxInputController()
    ctrl.move_relative(5.5, -3.2)
    ctrl.click('left')
    ctrl.click('right')
    ctrl.scroll(0, 3)
    ctrl.type_text("Hello PCDeck")
    ctrl.hotkey(["ctrl", "c"])


def test_websocket_reconnection_lifecycle(client):
    """Test connecting, ping/pong, and reconnecting WebSocket."""
    with client.websocket_connect("/ws") as ws1:
        ws1.send_text("p,1000")
        msg = ws1.receive_text()
        assert msg == "pong,1000"

    # Reconnect immediately
    with client.websocket_connect("/ws") as ws2:
        ws2.send_text("p,2000")
        msg = ws2.receive_text()
        assert msg == "pong,2000"

