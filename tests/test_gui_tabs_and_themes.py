"""
Unit tests for PCDeck GUI:
- Segmented 3-Tab Interface (Connect, Tools & Audio, Settings)
- Windows System Theme Detection (Auto / Dark / Light) & Dynamic Theming
- Thomas's Visible Version Badge (Header & Footer)
- Audio Stream Toggle & Hardware Integrity
- Polite 3-Day Review System Integration
"""

import sys
import os
import tkinter as tk
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows GUI environment")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.gui import (
    PCDeckProGUI,
    get_windows_system_theme,
    THEME_DARK,
    THEME_LIGHT,
    CURRENT_DESKTOP_VERSION_NAME,
    check_should_show_review_prompt,
    record_review_action,
)


@pytest.fixture(scope="module")
def gui_instance(shared_tk_root):
    """Initializes PCDeckProGUI in minimized mode for fast head-less testing."""
    root = tk.Toplevel(shared_tk_root)
    root.withdraw()
    app = PCDeckProGUI(root, start_minimized=True)
    yield app, root
    try:
        if app.tray_icon:
            app.tray_icon.stop()
    except Exception:
        pass
    try:
        if app.server:
            app.server.should_exit = True
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass


def test_segmented_tabs_switching(gui_instance):
    app, root = gui_instance

    # 1. Verify all 3 tab frames exist
    assert hasattr(app, "tab_connect") and app.tab_connect is not None
    assert hasattr(app, "tab_tools") and app.tab_tools is not None
    assert hasattr(app, "tab_settings") and app.tab_settings is not None

    # 2. Verify initial tab is 'connect' and is packed
    assert app.current_tab == "connect"
    assert app.tab_connect.winfo_manager() == "pack"
    assert app.tab_tools.winfo_manager() != "pack"
    assert app.tab_settings.winfo_manager() != "pack"

    # 3. Switch to 'tools' tab
    app._switch_tab("tools")
    root.update()
    assert app.current_tab == "tools"
    assert app.tab_connect.winfo_manager() != "pack"
    assert app.tab_tools.winfo_manager() == "pack"
    assert app.tab_settings.winfo_manager() != "pack"

    # 4. Switch to 'settings' tab
    app._switch_tab("settings")
    root.update()
    assert app.current_tab == "settings"
    assert app.tab_connect.winfo_manager() != "pack"
    assert app.tab_tools.winfo_manager() != "pack"
    assert app.tab_settings.winfo_manager() == "pack"

    # 5. Switch back to 'connect' tab
    app._switch_tab("connect")
    root.update()
    assert app.current_tab == "connect"
    assert app.tab_connect.winfo_manager() == "pack"


def test_thomas_version_badge(gui_instance):
    app, root = gui_instance

    # 1. Verify Thomas's version badge in top title row
    assert hasattr(app, "header_version_badge") and app.header_version_badge.winfo_exists()
    assert f"v{CURRENT_DESKTOP_VERSION_NAME}" in app.header_version_badge.cget("text")

    # 2. Verify bottom version label is removed per user directive (header-only clean layout)
    assert getattr(app, "version_lbl", None) is None or not app.version_lbl.winfo_exists()


def test_windows_theme_system(gui_instance, monkeypatch):
    app, root = gui_instance

    # 1. Verify get_windows_system_theme returns valid string
    sys_theme = get_windows_system_theme()
    assert sys_theme in ("dark", "light")

    # 2. Test dynamic switch to Dark mode
    app.theme_pref = "dark"
    app._apply_theme_tokens()
    assert app.c_bg == THEME_DARK["C_BG"]
    assert app.c_surface == THEME_DARK["C_SURFACE"]
    assert app.c_text == THEME_DARK["C_TEXT"]

    # 3. Test dynamic switch to Light mode
    app.theme_pref = "light"
    app._apply_theme_tokens()
    assert app.c_bg == THEME_LIGHT["C_BG"]
    assert app.c_surface == THEME_LIGHT["C_SURFACE"]
    assert app.c_text == THEME_LIGHT["C_TEXT"]


def test_audio_streaming_toggle(gui_instance):
    app, root = gui_instance

    # 1. Verify audio controls exist
    assert hasattr(app, "audio_status_lbl") and app.audio_status_lbl.winfo_exists()
    assert hasattr(app, "btn_toggle_audio") and app.btn_toggle_audio.winfo_exists()

    # 2. Toggle audio stream (should handle safely even without active audio client)
    app.toggle_audio_stream()
    # Call again to toggle back
    app.toggle_audio_stream()


def test_review_card_system(gui_instance):
    app, root = gui_instance

    # 1. Verify review evaluation logic
    settings = {
        "review_prompt_status": "pending",
        "review_next_prompt_time": 0.0,
        "first_run_timestamp": 0.0,
        "session_count": 5,
    }
    # On Windows with >3 days and >3 sessions, should be eligible
    if sys.platform == "win32":
        assert check_should_show_review_prompt(settings, current_time=400000.0) is True

    # 2. Verify manual review card build in right column
    app._build_review_card(app.right_col)
    root.update()
    assert app.review_card is not None
    assert app.review_card.winfo_exists()

    # 3. Test snooze dismisses review card
    app._on_review_snooze()
    assert app.review_card is None


def test_all_mobile_themes_respect_updates():
    """Verify that all mobile themes (aero, y2k, crt, purple, oled, analog, lime)
    include specialized styles for the version badge, air mouse beta tag, and active chips."""
    themes = ["aero", "y2k", "crt", "purple", "oled", "analog", "lime"]
    
    for path in ["static/style.css", "android_app/assets/style.css"]:
        assert os.path.exists(path), f"Missing {path}"
        with open(path, "r", encoding="utf-8") as f:
            css = f.read()
        
        for theme in themes:
            # 1. Version label must have theme adaptation
            assert f'body[data-theme="{theme}"] #app-current-version-label' in css, (
                f"Missing version label style for theme '{theme}' in {path}"
            )
            # 2. Beta tag must have theme adaptation
            assert f'body[data-theme="{theme}"] .chip-beta-tag' in css, (
                f"Missing beta tag style for theme '{theme}' in {path}"
            )
            # 3. Active air mouse button must have theme adaptation
            assert f'body[data-theme="{theme}"] #btn-air-mouse.active' in css, (
                f"Missing air mouse active style for theme '{theme}' in {path}"
            )

