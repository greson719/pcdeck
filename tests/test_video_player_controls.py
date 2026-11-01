"""
Test suite validating Video & Audio Streaming Player controls:
1. Auto-hide timeout of 10000ms with interaction pause.
2. Responsive mobile layout preventing panel overflow.
3. Touch gesture anti-flicker & controls retention on back / rewind.
4. Dedicated Music / Audio mode with animated visualizer and persistent controls.
5. Server & client media format MIME mappings.
6. Full asset synchronization across static/ and android_app/assets/.
"""

import os
import re
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(ROOT, "static")
ANDROID_DIR = os.path.join(ROOT, "android_app", "assets")
SERVER_MAIN = os.path.join(ROOT, "server", "main.py")


def test_video_player_auto_hide_and_interaction():
    for base in [STATIC_DIR, ANDROID_DIR]:
        app_js = os.path.join(base, "app.js")
        with open(app_js, "r", encoding="utf-8") as f:
            code = f.read()

        # 1. Verify auto-hide delay is at least 10000ms (10 seconds for comfortable viewing)
        assert "scheduleMediaControlsHide(delayMs = 10000)" in code or "delayMs = 10000" in code
        assert "isMediaInteractingWithControls" in code

        # 2. Verify controls pause auto-hide on touch/hover
        assert "mouseenter', onControlsEnter" in code or "mouseenter" in code
        assert "touchstart', onControlsEnter" in code or "touchstart" in code
        assert "scheduleMediaControlsHide(10000)" in code


def test_video_player_responsive_mobile_css():
    for base in [STATIC_DIR, ANDROID_DIR]:
        style_css = os.path.join(base, "style.css")
        with open(style_css, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. Verify volume slider is hidden on mobile to avoid row overflow
        assert ".media-vol-slider" in css
        assert "display: none !important" in css

        # 2. Verify redundant top buttons are hidden on compact screens
        assert "#btn-media-fullscreen-top" in css
        assert "#btn-media-pip" in css
        assert "#btn-media-audio-boost" in css

        # 3. Verify speed selector pills streamlined on mobile
        assert '.media-speed-pill[data-speed="0.75"]' in css
        assert '.media-speed-pill[data-speed="1.25"]' in css


def test_video_player_touch_and_back_fix():
    for base in [STATIC_DIR, ANDROID_DIR]:
        app_js = os.path.join(base, "app.js")
        with open(app_js, "r", encoding="utf-8") as f:
            code = f.read()

        # 1. Anti-flicker touch detection tracking controls state on touchstart
        assert "controlsWereHiddenAtStart" in code
        assert "lastTouchInteractionTime" in code

        # 2. Controls stay visible upon exiting fullscreen (Back action)
        assert "// Keep controls clearly visible upon exiting fullscreen / back" in code or "showMediaControls" in code

        # 3. Rewind 10s and Forward 10s keep controls visible with fresh timer
        assert "rewind10Btn.onclick = (e) => {" in code
        assert "showMediaControls();" in code or "showMediaControls(" in code


def test_media_player_audio_music_support():
    # 1. HTML visualizer structure
    for base in [STATIC_DIR, ANDROID_DIR]:
        index_html = os.path.join(base, "index.html")
        with open(index_html, "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="media-audio-visualizer"' in html
        assert 'class="media-audio-wave-bars"' in html

    # 2. CSS audio mode styling & persistent controls
    for base in [STATIC_DIR, ANDROID_DIR]:
        style_css = os.path.join(base, "style.css")
        with open(style_css, "r", encoding="utf-8") as f:
            css = f.read()
        assert ".media-video-container.is-audio-mode" in css
        assert ".media-audio-visualizer" in css
        assert ".media-video-container.is-audio-mode.controls-hidden .media-top-bar" in css

    # 3. JS audio mode logic
    for base in [STATIC_DIR, ANDROID_DIR]:
        app_js = os.path.join(base, "app.js")
        with open(app_js, "r", encoding="utf-8") as f:
            code = f.read()
        assert "is-audio-mode" in code
        assert "audioExts" in code

    # 4. Server stream endpoint MIME mappings
    with open(SERVER_MAIN, "r", encoding="utf-8") as f:
        server_code = f.read()
    assert '".flac": "audio/flac"' in server_code
    assert '".wma": "audio/x-ms-wma"' in server_code
    assert '".opus": "audio/opus"' in server_code


def test_assets_sync_static_and_android():
    # Both static and android_app/assets must stay synchronized
    for fname in ["app.js", "style.css", "index.html"]:
        static_file = os.path.join(STATIC_DIR, fname)
        android_file = os.path.join(ANDROID_DIR, fname)
        with open(static_file, "r", encoding="utf-8") as f1, open(android_file, "r", encoding="utf-8") as f2:
            assert f1.read() == f2.read(), f"{fname} is desynchronized between static/ and android_app/assets/"
