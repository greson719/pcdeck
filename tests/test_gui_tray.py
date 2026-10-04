"""
Unit test for PCDeckProGUI System Tray and Start Minimized Mode
"""

import sys
import os
import tkinter as tk
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.gui import PCDeckProGUI, SERVER_PORT
from server.main import get_pairing_token


def test_gui_start_minimized_and_tray():
    """Verify GUI initializes cleanly in minimized tray mode without showing main window."""
    root = tk.Tk()
    root.withdraw()

    app_gui = PCDeckProGUI(root, start_minimized=True)

    # 1. Verify window is withdrawn (hidden from desktop)
    assert root.wm_state() == "withdrawn"

    # 2. Verify pairing URL is clean and points to /connect gateway
    gateway_url = app_gui._get_gateway_qr_url()
    assert "/connect" in gateway_url
    assert str(SERVER_PORT) in gateway_url

    # 3. Verify tray icon exists
    assert app_gui.tray_icon is not None

    # 4. Verify quick flyout can be initialized
    app_gui.toggle_quick_flyout()
    assert app_gui.flyout is not None
    assert app_gui.flyout.winfo_exists()
    app_gui.flyout.withdraw()

    # 5. Clean shutdown
    import time
    time.sleep(0.5)
    try:
        app_gui.quit_application()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass


def test_msix_safeguards(monkeypatch, tmp_path):
    """Verify that when packaged as MSIX, startup shortcuts and prompts are completely disabled."""
    import server.gui as gui_module

    # Mock is_msix_packaged to True
    monkeypatch.setattr(gui_module, "is_msix_packaged", lambda: True)

    assert gui_module.is_msix_packaged() is True
    assert gui_module.is_first_run_startup_prompt_done() is True

    # Test rogue shortcut cleanup
    programs_dir = tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    startup_dir = tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    programs_dir.mkdir(parents=True)
    startup_dir.mkdir(parents=True, exist_ok=True)

    bad_lnk1 = programs_dir / "PCDeck.lnk"
    bad_lnk2 = startup_dir / "PCDeck.lnk"
    bad_lnk1.write_text("dummy")
    bad_lnk2.write_text("dummy")

    monkeypatch.setenv("APPDATA", str(tmp_path))

    class DummyApp:
        pass

    dummy = DummyApp()
    gui_module.PCDeckProGUI._cleanup_msix_rogue_shortcuts(dummy)

    # Both rogue shortcuts must be safely purged
    assert not bad_lnk1.exists()
    assert not bad_lnk2.exists()


def test_polite_review_prompt_logic(monkeypatch):
    """Verify polite review prompt 3-day (72h) and 3-session rule, snooze, and dismissal."""
    import server.gui as gui_module

    monkeypatch.setattr(gui_module.sys, "platform", "win32")

    now = 1000000.0

    # 1. New install: 0 days elapsed, 1 session -> False
    st1 = {
        "first_run_timestamp": now,
        "session_count": 1,
        "review_prompt_status": "pending",
        "review_next_prompt_time": 0.0,
    }
    assert gui_module.check_should_show_review_prompt(st1, current_time=now) is False

    # 2. 1 day elapsed (86400s), 5 sessions -> False (< 3 days)
    st2 = {
        "first_run_timestamp": now - 86400,
        "session_count": 5,
        "review_prompt_status": "pending",
        "review_next_prompt_time": 0.0,
    }
    assert gui_module.check_should_show_review_prompt(st2, current_time=now) is False

    # 3. 4 days elapsed (4 * 86400s), only 2 sessions -> False (< 3 sessions)
    st3 = {
        "first_run_timestamp": now - (4 * 86400),
        "session_count": 2,
        "review_prompt_status": "pending",
        "review_next_prompt_time": 0.0,
    }
    assert gui_module.check_should_show_review_prompt(st3, current_time=now) is False

    # 4. 4 days elapsed, 4 sessions, status pending -> True!
    st4 = {
        "first_run_timestamp": now - (4 * 86400),
        "session_count": 4,
        "review_prompt_status": "pending",
        "review_next_prompt_time": 0.0,
    }
    assert gui_module.check_should_show_review_prompt(st4, current_time=now) is True

    # 5. User snoozed ("Remind in 7 days") -> False while now < next_prompt_time
    st5 = dict(st4)
    st5["review_next_prompt_time"] = now + (7 * 86400)
    assert gui_module.check_should_show_review_prompt(st5, current_time=now) is False
    # But fires again after 7 days (now + 8 days)
    assert gui_module.check_should_show_review_prompt(st5, current_time=now + (8 * 86400)) is True

    # 6. User clicked "Don't show again" ("dismissed") -> Permanently False
    st6 = dict(st4)
    st6["review_prompt_status"] = "dismissed"
    assert gui_module.check_should_show_review_prompt(st6, current_time=now + (30 * 86400)) is False

    # 7. User clicked "Rate on Microsoft Store" ("reviewed") -> Permanently False
    st7 = dict(st4)
    st7["review_prompt_status"] = "reviewed"
    assert gui_module.check_should_show_review_prompt(st7, current_time=now + (30 * 86400)) is False

    # 8. Test record_review_action with custom days (e.g. 5-day notification cooldown)
    saved_state = {}
    monkeypatch.setattr(gui_module, "load_app_settings", lambda: dict(st4))
    monkeypatch.setattr(gui_module, "save_app_settings", lambda s: saved_state.update(s))
    monkeypatch.setattr(gui_module.time, "time", lambda: now)

    gui_module.record_review_action("snoozed", days=5)
    assert saved_state["review_next_prompt_time"] == now + (5 * 86400)
    assert gui_module.check_should_show_review_prompt(saved_state, current_time=now) is False
    assert gui_module.check_should_show_review_prompt(saved_state, current_time=now + (6 * 86400)) is True


