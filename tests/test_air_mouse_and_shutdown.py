"""
Test suite validating:
1. 60 FPS Pro Plan gating in desktop GUI.
2. Air Mouse toggle in Trackpad strip with correct reordering & BETA tag.
3. Landscape mode empty space elimination in Keys tab.
4. Safe 'Shut Down PC' button in Keys tab and backend execution.
5. High-precision Air Mouse sensor pipeline (devicemotion, rotationRate, zero drift, click freeze).
"""

import os
import json
import tkinter as tk
import pytest
from unittest.mock import patch, MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(ROOT, "static")
ANDROID_DIR = os.path.join(ROOT, "android_app", "assets")

from server.gui import PCDeckProGUI
from server.main import dispatch_command


def test_60_fps_locked_behind_pro():
    mock_app = MagicMock()
    mock_app.fps_var = MagicMock()
    mock_app.open_license_dialog = MagicMock()

    # Free user setting 60 FPS: must revert to 30 and open license dialog
    mock_app.is_pc_pro = False
    mock_app.fps_var.get.return_value = "60"
    PCDeckProGUI.update_fps(mock_app)
    mock_app.fps_var.set.assert_called_with("30")
    mock_app.open_license_dialog.assert_called_once()

    # Pro user setting 60 FPS: allowed
    mock_app.is_pc_pro = True
    mock_app.open_license_dialog.reset_mock()
    mock_app.fps_var.set.reset_mock()
    PCDeckProGUI.update_fps(mock_app)
    mock_app.open_license_dialog.assert_not_called()


def test_trackpad_toolbar_reordering_and_air_mouse():
    for base in [STATIC_DIR, ANDROID_DIR]:
        index_html = os.path.join(base, "index.html")
        with open(index_html, "r", encoding="utf-8") as f:
            html = f.read()

        # Check trackpad strip
        assert 'id="btn-speed-quick"' in html
        assert 'id="btn-air-mouse"' in html
        assert 'class="chip-beta-tag">BETA</span>' in html
        assert 'id="btn-gamepad-mode-toggle"' in html
        assert 'id="tool-drag-lock"' in html
        assert 'id="btn-esc-quick"' in html
        assert 'id="btn-desktop-quick"' in html
        assert 'id="btn-quick-mic-toggle"' in html
        assert 'id="btn-quick-cam-toggle"' in html
        assert 'id="btn-kbd-quick"' in html

        # Verify correct ordering: Speed -> Air Mouse -> Gamepad -> Drag -> Esc -> Desktop -> Mic -> Cam -> Keys
        # Verify correct ordering: Speed -> Gamepad -> Drag -> Esc -> Desktop -> Mic -> Cam -> Keys -> Air Mouse (deep right)
        pos_speed = html.find('id="btn-speed-quick"')
        pos_gp = html.find('id="btn-gamepad-mode-toggle"')
        pos_drag = html.find('id="tool-drag-lock"')
        pos_esc = html.find('id="btn-esc-quick"')
        pos_desktop = html.find('id="btn-desktop-quick"')
        pos_mic = html.find('id="btn-quick-mic-toggle"')
        pos_cam = html.find('id="btn-quick-cam-toggle"')
        pos_keys = html.find('id="btn-kbd-quick"')
        pos_air = html.find('id="btn-air-mouse"')

        assert pos_speed < pos_gp < pos_drag < pos_esc < pos_desktop < pos_mic < pos_cam < pos_keys < pos_air


def test_keys_landscape_css_rules():
    for base in [STATIC_DIR, ANDROID_DIR]:
        style_css = os.path.join(base, "style.css")
        with open(style_css, "r", encoding="utf-8") as f:
            css = f.read()

        assert "#tab-keyboard .scroll-container" in css
        assert "grid-column: 1 / -1 !important" in css
        assert "align-content: start !important" in css
        assert "align-items: start !important" in css
        assert "@media (orientation: landscape)" in css
        assert "#btn-air-mouse.active" in css
        assert ".chip-beta-tag" in css


def test_shutdown_pc_button_and_backend():
    # 1. Frontend markup exists
    for base in [STATIC_DIR, ANDROID_DIR]:
        index_html = os.path.join(base, "index.html")
        with open(index_html, "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="btn-shutdown-pc"' in html

    # 2. Backend handles comma-separated string
    with patch("server.main.subprocess.Popen") as mock_popen:
        dispatch_command("system,shutdown")
        assert mock_popen.called

    # 3. Backend handles JSON payload
    with patch("server.main.subprocess.Popen") as mock_popen:
        dispatch_command(json.dumps({"type": "system", "action": "shutdown"}))
        assert mock_popen.called


def test_air_mouse_sensor_pipeline_precision():
    """Verify angular velocity devicemotion pipeline, click dampening, and native gyro rate support."""
    for base in [STATIC_DIR, ANDROID_DIR]:
        app_js = os.path.join(base, "app.js")
        with open(app_js, "r", encoding="utf-8") as f:
            js = f.read()

        assert "processAirMouseRates" in js
        assert "rotationRate" in js
        assert "freezeAirMouseForClick" in js
        assert "onNativeGyroRate" in js
        assert "devicemotion" in js
        assert "deviceorientation" in js

        # Verify touchmove does not fight gyro in Air Mouse mode
        assert "if (window.isAirMouseActive)" in js
        # Verify click freeze on buttons
        assert "freezeAirMouseForClick(90)" in js

    # Verify native Android Java sensor tracking registers GYROSCOPE
    java_path = os.path.join(ROOT, "android_app", "src", "com", "pcdeck", "app", "MainActivity.java")
    with open(java_path, "r", encoding="utf-8") as f:
        java = f.read()
    assert "Sensor.TYPE_GYROSCOPE" in java
    assert "onNativeGyroRate" in java
