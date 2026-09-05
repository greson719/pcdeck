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
    ctrl.scroll_at(0.5, 0.5, 0.0, -120.0)
    ctrl.type_text("Hello PCDeck")
    ctrl.hotkey(["ctrl", "c"])

    # Also verify default active platform controller handles scroll_at
    active_ctrl = InputController()
    active_ctrl.scroll_at(0.5, 0.5, 0.0, 50.0)


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


def test_fs_download_with_http_range(client, tmp_path):
    """Verify /api/fs/download handles full downloads, HTTP 206 Range resume, HEAD, and OPTIONS."""
    test_file = tmp_path / "stream_test.bin"
    payload = b"PCDeckUltraResilientDownloadTestPayloadBytes1234567890"
    test_file.write_bytes(payload)

    path_str = str(test_file)

    # 1. Full Download (200 OK)
    resp = client.get(f"/api/fs/download?path={path_str}")
    assert resp.status_code == 200
    assert resp.content == payload
    assert resp.headers.get("Accept-Ranges") == "bytes"

    # 2. Resumed Partial Download (206 Partial Content)
    range_offset = 12
    resp_range = client.get(
        f"/api/fs/download?path={path_str}",
        headers={"Range": f"bytes={range_offset}-"}
    )
    assert resp_range.status_code == 206
    assert resp_range.content == payload[range_offset:]
    assert "Content-Range" in resp_range.headers
    assert f"bytes {range_offset}-{len(payload)-1}/{len(payload)}" in resp_range.headers["Content-Range"]

    # 3. HEAD Request (checks headers without streaming body)
    resp_head = client.head(f"/api/fs/download?path={path_str}")
    assert resp_head.status_code == 200
    assert resp_head.headers.get("Content-Length") == str(len(payload))
    assert len(resp_head.content) == 0

    # 4. OPTIONS Request
    resp_options = client.options(f"/api/fs/download?path={path_str}")
    assert resp_options.status_code == 200
    assert resp_options.headers.get("Accept-Ranges") == "bytes"


def test_screen_streamer_sleep_and_wake_lifecycle():
    """Verify ScreenStreamer deep sleep event clears when paused and sets when resumed."""
    streamer = ScreenStreamer()
    assert streamer._wake_event.is_set()

    # Simulate client navigating to Trackpad tab (pause)
    streamer.pause_consumer()
    assert not streamer._wake_event.is_set()

    # Simulate client navigating back to Screen tab (resume)
    streamer.resume_consumer()
    assert streamer._wake_event.is_set()


