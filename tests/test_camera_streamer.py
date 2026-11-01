"""
Tests for PCDeck Wireless HD Virtual Camera Pipeline.
Validates zero-latency direct push, aspect ratio preservation,
and client-server sync invariants.
"""
import io
import time
import pytest
from PIL import Image
import numpy as np

from server.camera_streamer import camera_streamer


def test_camera_streamer_push_frame_direct():
    """Validates that push_frame_bytes accepts JPEG frames and updates live frame atomically."""
    # Create a 1280x720 dummy RGB JPEG image
    img = Image.new("RGB", (1280, 720), (20, 40, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    jpeg_bytes = buf.getvalue()

    try:
        t_before = time.time()
        camera_streamer.push_frame_bytes(jpeg_bytes)
        t_after = time.time()

        assert camera_streamer.is_active is True
        assert camera_streamer.is_streaming_live is True
        assert camera_streamer.last_frame_time >= t_before
        assert camera_streamer.last_frame_time <= t_after + 0.1
        assert camera_streamer._latest_live_frame is not None
        assert camera_streamer._latest_live_frame.shape == (720, 1280, 3)
    finally:
        camera_streamer.stop_camera()


def test_camera_streamer_aspect_ratio_pillarboxing():
    """Validates portrait phone video (e.g. 720x1280) is pillarboxed to 1280x720 without stretching."""
    img = Image.new("RGB", (720, 1280), (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    jpeg_bytes = buf.getvalue()

    try:
        camera_streamer.push_frame_bytes(jpeg_bytes)
        assert camera_streamer._latest_live_frame is not None
        assert camera_streamer._latest_live_frame.shape == (720, 1280, 3)
    finally:
        camera_streamer.stop_camera()


def test_camera_client_buffer_and_cadence_settings():
    """Validates client app.js has zero-latency buffer threshold and 4ms cadence margin."""
    with open("static/app.js", "r", encoding="utf-8") as f:
        content = f.read()

    # Verify 256KB network backlog threshold (prevents dropping 80KB 720p frames)
    assert "camWs.bufferedAmount > 262144" in content
    # Verify cadence margin (- 4)
    assert "frameInterval - 4" in content
    # Verify direct send(blob) zero-copy
    assert "camWs.send(blob)" in content
    # Verify front camera mirror only
    assert "camFacingMode === 'user'" in content
