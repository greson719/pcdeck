"""
Test suite validating Light Mode text visibility, high-contrast colors,
and click event handling across all tabs in PCDeck GUI.
"""

import os
import sys
import tkinter as tk
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows GUI environment")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.gui import (
    PCDeckProGUI,
    THEME_LIGHT,
    THEME_DARK,
    CTkModernButton,
    CTkModernLabel,
    HAS_CUSTOMTKINTER,
)


@pytest.fixture(scope="module")
def light_gui(shared_tk_root):
    root = tk.Toplevel(shared_tk_root)
    root.withdraw()
    app = PCDeckProGUI(root, start_minimized=True)
    app.theme_pref = "light"
    app._apply_theme_tokens()
    app.root.configure(bg=app.c_bg)
    root.update()
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


def test_light_mode_color_tokens(light_gui):
    app, root = light_gui

    # 1. Verify Light Mode token assignment
    assert app.c_bg == THEME_LIGHT["C_BG"]
    assert app.c_surface == THEME_LIGHT["C_SURFACE"]
    assert app.c_text == THEME_LIGHT["C_TEXT"]
    assert app.c_text == "#1f2328"

    # 2. Check tab buttons text colors in Light Mode
    for tab_key in ["connect", "tools", "settings"]:
        app._switch_tab(tab_key)
        root.update()
        active_btn = app.tab_buttons[tab_key]
        # Active tab must have dark text (#1f2328) on white (#ffffff)
        assert active_btn.cget("text_color") == "#1f2328"
        assert active_btn.cget("fg_color") == "#ffffff"


def test_button_click_reliability(light_gui):
    app, root = light_gui

    # 1. Test clicking tabs
    clicked_tabs = []
    app._switch_tab("connect")
    root.update()
    assert app.current_tab == "connect"

    # Simulate click on tools tab button
    tools_btn = app.tab_buttons["tools"]
    tools_btn._on_release()
    root.update()
    assert app.current_tab == "tools"

    # Simulate click on settings tab button
    settings_btn = app.tab_buttons["settings"]
    settings_btn._on_release()
    root.update()
    assert app.current_tab == "settings"


def test_button_text_contrast_never_white_on_light(light_gui):
    app, root = light_gui

    # Test CTkModernButton auto-resolves text_color based on background
    neutral_btn = CTkModernButton(root, text="Neutral Test", bg="#e9ecef")
    assert neutral_btn.cget("text_color") == "#1f2328"
    assert neutral_btn.cget("text_color") != "#DCE4EE"  # Must not be invisible silver

    accent_btn = CTkModernButton(root, text="Accent Test", bg="#2563eb")
    assert accent_btn.cget("text_color") == "#ffffff"  # White on blue

    danger_btn = CTkModernButton(root, text="Danger Test", bg="#dc2626")
    assert danger_btn.cget("text_color") == "#ffffff"  # White on red


def test_dynamic_theme_change_rebuild(light_gui):
    app, root = light_gui

    # Switch to settings tab
    app._switch_tab("settings")
    root.update()

    # Trigger theme change to Light Mode
    app.theme_combo_var.set("Light Mode")
    app.on_theme_change()
    root.update()

    # Allow deferred rebuild tick
    root.after(30, lambda: None)
    import time
    time.sleep(0.05)
    root.update()

    assert app.theme_pref == "light"
    assert app.c_text == "#1f2328"
