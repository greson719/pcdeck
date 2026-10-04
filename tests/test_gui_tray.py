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

