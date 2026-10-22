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
        if msg.startswith("pro_unlocked,"):
            msg = ws1.receive_text()
        assert msg == "pong,1000"

    # Reconnect immediately
    with client.websocket_connect("/ws") as ws2:
        ws2.send_text("p,2000")
        msg = ws2.receive_text()
        if msg.startswith("pro_unlocked,"):
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


def test_server_ping_and_pro_sync(client, monkeypatch):
    """Verify /api/ping returns pro_active and responds to PC host Pro state."""
    from server.main import set_pro_client, is_pro_client
    import server.license_manager as lm

    monkeypatch.setattr(lm, "verify_license", lambda: {"pro_active": False})

    try:
        set_pro_client(True)
        assert is_pro_client() is True
        resp = client.get("/api/ping")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"
        assert data.get("pro_active") is True

        info_resp = client.get("/api/info")
        assert info_resp.status_code == 200
        assert info_resp.json().get("pro_active") is True

        set_pro_client(False)
        assert is_pro_client() is False
        resp_free = client.get("/api/ping")
        assert resp_free.status_code == 200
        assert resp_free.json().get("pro_active") is False
    finally:
        set_pro_client(False)


def test_websocket_pro_sync_lifecycle(client):
    """Verify mobile client receives pro_unlocked,1 automatically when PC is Pro."""
    from server.main import set_pro_client, get_pairing_token

    try:
        set_pro_client(True)
        tok = get_pairing_token()
        with client.websocket_connect(f"/ws?token={tok}") as ws:
            # Client should automatically receive pro_unlocked,1 on connect
            msg = ws.receive_text()
            assert msg == "pro_unlocked,1"

            # Client sends pro_check, should receive pro_unlocked,1
            ws.send_text("pro_check")
            msg2 = ws.receive_text()
            assert msg2 == "pro_unlocked,1"
    finally:
        set_pro_client(False)


def test_anti_tamper_hwid_and_spoof_protection(client, monkeypatch):
    """Verify spoofed client messages cannot unlock Pro, and HWID mismatch rejects copied licenses."""
    from server.main import set_pro_client, is_pro_client, get_pairing_token
    import server.license_manager as lm

    # 1. PC host has no license
    monkeypatch.setattr(lm, "verify_license", lambda: {"pro_active": False})
    set_pro_client(False)

    tok = get_pairing_token()
    with client.websocket_connect(f"/ws?token={tok}") as ws:
        # Spoofed pro_status,1 should be REJECTED with pro_unlocked,0
        ws.send_text("pro_status,1")
        msg = ws.receive_text()
        assert msg == "pro_unlocked,0"
        assert is_pro_client() is False

        # Spoofed fake key in pro_auth should be REJECTED
        ws.send_text("pro_auth,FAKE-CRACK-KEY-12345")
        msg2 = ws.receive_text()
        assert msg2 == "pro_unlocked,0"
        assert is_pro_client() is False

    # 2. Cryptographic HWID validation: copying license to different HWID must fail
    fake_hwid = "different_machine_hwid_99999"
    # When HWID differs from stored HWID, verify_license returns pro_active False
    monkeypatch.setattr(lm, "get_machine_hwid", lambda: fake_hwid)
    verified = lm.verify_license()
    assert verified.get("pro_active") is False


def test_screen_multi_monitor_bounds_and_switching(client):
    """Verify monitor summary and coordinate bounding box calculation for multi-monitor setups."""
    from server.screen_streamer import ScreenStreamer
    from server.input_controller import InputController

    streamer = ScreenStreamer()
    summary = streamer.get_monitors_summary()
    assert "count" in summary
    assert "active_idx" in summary
    assert "monitors" in summary
    assert summary["count"] >= 1
    assert len(summary["monitors"]) >= 1

    ctrl = InputController()
    if hasattr(ctrl, "set_active_monitor_bounds") and hasattr(ctrl, "get_active_monitor_bounds"):
        # Test custom bounds for a secondary 1080p monitor placed to the right
        ctrl.set_active_monitor_bounds(left=1920, top=0, width=1920, height=1080)
        bounds = ctrl.get_active_monitor_bounds()
        assert bounds["left"] == 1920
        assert bounds["top"] == 0
        assert bounds["width"] == 1920
        assert bounds["height"] == 1080

        # Reset bounds back to primary
        ctrl.set_active_monitor_bounds(left=0, top=0, width=1920, height=1080)
        bounds = ctrl.get_active_monitor_bounds()
        assert bounds["left"] == 0


def test_license_legacy_hwid_migration(tmp_path, monkeypatch):
    """Verify that a license saved under legacy volatile HWID seamlessly migrates to stable HWID."""
    import server.license_manager as lm
    import json
    import base64

    test_license_file = str(tmp_path / "license.dat")
    monkeypatch.setattr(lm, "SECURE_LICENSE_FILE", test_license_file)
    monkeypatch.setattr(lm, "LICENSE_DIR", str(tmp_path))

    legacy_hwid = "legacy_volatile_hwid_12345678"
    stable_hwid = "stable_machine_guid_87654321"

    monkeypatch.setattr(lm, "_get_all_legacy_hwids", lambda: [legacy_hwid])
    monkeypatch.setattr(lm, "get_machine_hwid", lambda: stable_hwid)

    # Save a record using legacy HWID
    key = "74a5e381-test-key-1234"
    instance_id = "inst_legacy_999"
    sig = lm._compute_hmac(legacy_hwid, key, instance_id)
    record = {
        "key": key,
        "instance_id": instance_id,
        "hwid": legacy_hwid,
        "sig": sig,
        "activated_at": "2026-10-17T09:00:00",
        "meta": {"legacy": True}
    }
    with open(test_license_file, "wb") as f:
        f.write(base64.b64encode(json.dumps(record).encode("utf-8")))

    # verify_license should recognize legacy HWID and return pro_active=True
    res = lm.verify_license()
    assert res["pro_active"] is True
    assert res["key"] == key.upper()

    # It should also have seamlessly upgraded the file to the new stable HWID
    with open(test_license_file, "rb") as f:
        upgraded_data = json.loads(base64.b64decode(f.read()).decode("utf-8"))
    assert upgraded_data["hwid"] == stable_hwid
    expected_new_sig = lm._compute_hmac(stable_hwid, key, instance_id)
    assert upgraded_data["sig"] == expected_new_sig


def test_license_hybrid_recovery_on_activation_limit(tmp_path, monkeypatch):
    """Verify HTTP 422 triggers hybrid recovery on same machine, but rejects fresh machines."""
    import server.license_manager as lm
    import urllib.error
    import io
    import json
    import base64

    test_license_file = str(tmp_path / "license.dat")
    monkeypatch.setattr(lm, "SECURE_LICENSE_FILE", test_license_file)
    monkeypatch.setattr(lm, "LICENSE_DIR", str(tmp_path))

    # Mock urllib.request.urlopen to raise HTTP 422 for activate, and 200 valid for validate
    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/licenses/activate" in url:
            fp = io.BytesIO(b'{"message":"License key activation limit reached for this key."}')
            raise urllib.error.HTTPError(url, 422, "Unprocessable Entity", {}, fp)
        elif "/licenses/validate" in url:
            class MockResponse:
                def read(self):
                    return b'{"valid": true}'
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return MockResponse()
        raise ValueError(f"Unexpected URL {url}")

    monkeypatch.setattr(lm.urllib.request, "urlopen", mock_urlopen)

    key = "74a5e381-valid-key"

    # Case 1: Fresh machine with no prior record -> 422 rejects to protect seat limits
    ok, msg, data = lm.activate_license_online(key)
    assert ok is False
    assert "activation limit reached" in msg.lower()

    # Case 2: Machine already possessed this key locally (re-activation after HWID drift)
    # Simulate authentic prior local record
    hwid = lm.get_machine_hwid()
    sig = lm._compute_hmac(hwid, key, "inst_prior_001")
    prior_record = {
        "key": key,
        "instance_id": "inst_prior_001",
        "hwid": hwid,
        "sig": sig,
        "activated_at": "2026-10-10T00:00:00"
    }
    with open(test_license_file, "wb") as f:
        f.write(base64.b64encode(json.dumps(prior_record).encode("utf-8")))

    # Now activating the same key recovers successfully via hybrid entitlement
    ok, msg, data = lm.activate_license_online(key)
    assert ok is True
    assert "activated successfully" in msg.lower()
    assert data.get("recovered") is True

    # Check that verify_license now sees the license as active
    verified = lm.verify_license()
    assert verified["pro_active"] is True
    assert verified["key"] == key.upper()


def test_first_time_download_stream_not_corrupted(client, tmp_path, monkeypatch):
    """Verify first-time APK download without cookies is not truncated or corrupted by middleware."""
    from server.main import STATIC_DIR
    apk_mock = tmp_path / "PCDeck.apk"
    # Create a dummy APK > 200 KB
    content = b"PK\x03\x04" + b"X" * 250000
    apk_mock.write_bytes(content)

    import server.main as main_mod
    monkeypatch.setattr(main_mod, "STATIC_DIR", str(tmp_path))

    # Request without any cookies or prior visits
    resp = client.get("/PCDeck.apk")
    assert resp.status_code == 200
    assert len(resp.content) == len(content)
    assert resp.content == content
    assert "set-cookie" not in resp.headers


def test_websocket_pair_response_on_authenticated_client(client):
    """Verify that websocket pair command always receives pair_ok response even if client IP was already authorized."""
    from server.main import get_pairing_token
    token = get_pairing_token()
    with client.websocket_connect("/ws") as ws:
        # Client sends pair command
        ws.send_text(f"pair,{token}")
        reply = ws.receive_text()
        assert reply == "pair_ok,1"


def test_media_stream_range_requests(client, tmp_path):
    """Verify /api/fs/stream serves HTTP 206 Partial Content with byte ranges for video/audio seeking."""
    dummy_video = tmp_path / "sample_video.mp4"
    dummy_content = b"X" * 10240  # 10 KB dummy content
    dummy_video.write_bytes(dummy_content)

    # 1. Full file request
    resp = client.get(f"/api/fs/stream?path={dummy_video}")
    assert resp.status_code == 200
    assert resp.headers.get("accept-ranges") == "bytes"
    assert resp.headers.get("content-type") == "video/mp4"

    # 2. HTTP 206 Byte Range Request (first 100 bytes)
    resp_range = client.get(
        f"/api/fs/stream?path={dummy_video}",
        headers={"Range": "bytes=0-99"}
    )
    assert resp_range.status_code == 206
    assert resp_range.headers.get("content-range") == "bytes 0-99/10240"
    assert len(resp_range.content) == 100
    assert resp_range.content == dummy_content[:100]


def test_media_subtitles_endpoint(client, tmp_path):
    """Verify /api/fs/subtitles locates and auto-converts sidecar .srt files to WebVTT."""
    dummy_video = tmp_path / "movie.mp4"
    dummy_video.write_bytes(b"dummy")

    dummy_srt = tmp_path / "movie.srt"
    dummy_srt.write_text("1\n00:00:01,000 --> 00:00:04,000\nHello world\n", encoding="utf-8")

    resp = client.get(f"/api/fs/subtitles?path={dummy_video}")
    assert resp.status_code == 200
    assert "text/vtt" in resp.headers.get("content-type", "")
    assert "WEBVTT" in resp.text
    assert "00:00:01.000 --> 00:00:04.000" in resp.text
    assert "Hello world" in resp.text








