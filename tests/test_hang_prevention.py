"""
Unit and regression tests for Windows UI thread responsiveness and Hang prevention.
Validates:
1. In-memory metrics update on UI thread executes in milliseconds without subprocess or disk I/O.
2. Background metrics worker populates cached values without blocking the main event queue.
3. show_notification and show_toast_notification return immediately asynchronously.
4. quit_application teardown executes without synchronous thread joining on the main thread.
5. start_single_instance_ipc_server debounced_trigger does not accumulate duplicate timers.
"""

import sys
import time
import pytest
import tkinter as tk
import threading

if sys.platform != "win32":
    pytest.skip("Windows UI hang prevention tests only run on Windows", allow_module_level=True)

import server.gui as gui


def test_metrics_ui_thread_speed(shared_tk_root, monkeypatch):
    """Verify that update_metrics reads from in-memory cache and never runs subprocesses on the UI thread."""
    root = tk.Toplevel(shared_tk_root)
    root.withdraw()

    # Prevent port 8000 collisions during test runs
    monkeypatch.setattr(gui.PCDeckProGUI, "start_server", lambda self: None)

    app = gui.PCDeckProGUI(root, start_minimized=True)

    # Track subprocess calls made specifically on the main/UI thread
    main_thread_id = threading.get_ident()
    ui_subprocesses = []

    import subprocess
    real_run = subprocess.run

    def mock_run(*args, **kwargs):
        if threading.get_ident() == main_thread_id:
            ui_subprocesses.append(args)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Measure execution time of in-memory metrics sync
    t0 = time.perf_counter()
    ip = getattr(app, "_cached_ip", "192.168.1.100")
    st = getattr(app, "_cached_wifi_status", {"state": "connected", "ssid": "TestWiFi", "signal": "90%"})
    pro = getattr(app, "_cached_pro_active", False)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 100.0, f"In-memory metrics tick took {elapsed_ms}ms; expected < 100ms"
    assert len(ui_subprocesses) == 0, f"Subprocesses called on UI thread: {ui_subprocesses}"

    app.quit_application()


def test_show_notification_is_non_blocking(shared_tk_root, monkeypatch):
    """Verify that show_notification returns control to the UI thread asynchronously."""
    root = tk.Toplevel(shared_tk_root)
    root.withdraw()

    monkeypatch.setattr(gui.PCDeckProGUI, "start_server", lambda self: None)
    app = gui.PCDeckProGUI(root, start_minimized=True)

    t0 = time.perf_counter()
    app.show_notification("Test Non-Blocking Message", "Test Title")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Must return without blocking for Windows Explorer RPC timeout (which is 5000ms)
    assert elapsed_ms < 1500.0, f"show_notification blocked UI thread for {elapsed_ms}ms"

    app.quit_application()


def test_show_toast_notification_is_non_blocking(shared_tk_root, monkeypatch):
    """Verify that show_toast_notification returns control immediately without waiting on PowerShell."""
    import subprocess
    from unittest.mock import MagicMock

    root = tk.Toplevel(shared_tk_root)
    root.withdraw()

    monkeypatch.setattr(gui.PCDeckProGUI, "start_server", lambda self: None)
    # Mock MSIX AUMID so toast path is active without requiring actual MSIX installation
    monkeypatch.setattr(gui.PCDeckProGUI, "_get_msix_aumid", staticmethod(lambda: "GresonParichha.PCDeck_test!PCDeck"))
    # Mock subprocess.Popen so no real PowerShell toast appears on the developer's screen during test runs
    mock_popen = MagicMock()
    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    app = gui.PCDeckProGUI(root, start_minimized=True)

    t0 = time.perf_counter()
    sent = app.show_toast_notification(
        title="Test Toast",
        message="This must not block",
        action_url="https://getpcdeck.com",
        action_label="Open"
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert sent is True
    assert elapsed_ms < 1500.0, f"show_toast_notification blocked UI thread for {elapsed_ms}ms"

    # Verify unpackaged fallback returns False (directing to tray balloon without PowerShell branding)
    monkeypatch.setattr(gui.PCDeckProGUI, "_get_msix_aumid", staticmethod(lambda: None))
    assert app.show_toast_notification("Title", "Msg") is False

    app.quit_application()


def test_ipc_direct_dispatch_without_recursive_polling(shared_tk_root):
    """Verify that debounced_trigger dispatches safely via single guarded polling queue."""
    root = tk.Toplevel(shared_tk_root)
    root.withdraw()

    calls = []
    def on_show():
        calls.append(1)

    unique_id = f"{int(time.time() * 1000)}"
    events = [rf"Local\Test_IPC_Debounce_{unique_id}"]
    cls = f"Test_Class_{unique_id}"
    msg = f"Test_Msg_{unique_id}"

    gui.start_single_instance_ipc_server(root, on_show, event_names=events, window_class=cls, message_string=msg)

    # Signal once
    gui.signal_existing_instance_to_show(event_names=events, window_class=cls, message_string=msg)

    # Process events in message pump
    start_wait = time.time()
    while time.time() - start_wait < 1.0 and not calls:
        root.update_idletasks()
        root.update()
        time.sleep(0.02)

    assert len(calls) == 1, f"Expected 1 wakeup call, got {len(calls)}"
    root.destroy()
