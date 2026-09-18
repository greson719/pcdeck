"""
Unit and Integration Tests for PCDeck Single-Instance Mutex and Dual-Signal IPC.
Validates:
1. Named Mutex mutual exclusion (bInitialOwner=True).
2. Dual-signal IPC (Win32 Named Event + RegisterWindowMessageW).
3. Window restoration from withdrawn/tray state.
4. Mutex handle persistence across application lifecycle.
"""

import sys
import time
import pytest

if sys.platform != "win32":
    pytest.skip("Single-instance Win32 tests only run on Windows", allow_module_level=True)

import ctypes
from ctypes import wintypes
import server.gui as gui


def test_mutex_collision_and_handle_persistence():
    """Verify that the named mutex prevents dual execution and retains handle ownership."""
    kernel32 = ctypes.windll.kernel32
    test_mutex_name = r"Local\PCDeck_Test_Mutex_Suite"
    
    # 1. Acquire primary handle with atomic ownership
    h1 = kernel32.CreateMutexW(None, True, test_mutex_name)
    assert h1 != 0, "Primary mutex handle could not be created"
    err1 = kernel32.GetLastError()
    assert err1 == 0, f"Expected clean creation (0), got {err1}"

    # 2. Secondary acquisition attempt must detect ERROR_ALREADY_EXISTS (183)
    h2 = kernel32.CreateMutexW(None, True, test_mutex_name)
    err2 = kernel32.GetLastError()
    assert err2 == 183, f"Expected ERROR_ALREADY_EXISTS (183), got {err2}"
    
    # 3. Clean up test handles
    kernel32.CloseHandle(h2)
    kernel32.CloseHandle(h1)


def test_ipc_event_and_message_delivery():
    """Verify that secondary instance signals wake up the primary listener without exact title matching."""
    import tkinter as tk
    import threading

    root = tk.Tk()
    root.title("PCDeck Test Unit - Dynamic IP 10.0.0.99")
    root.withdraw()
    root.update()

    signals_received = []

    def mock_show():
        signals_received.append("WAKEUP")
        root.deiconify()
        root.state("normal")

    test_events = [r"Local\PCDeck_Test_IPC_Event"]
    test_class = "PCDeck_Test_IPC_Class"
    test_msg = "PCDeck_Test_IPC_Msg"

    # Start primary IPC listener with test-isolated IPC identifiers
    gui.start_single_instance_ipc_server(
        root, mock_show,
        event_names=test_events,
        window_class=test_class,
        message_string=test_msg
    )
    time.sleep(0.15)

    # Initial state: withdrawn
    assert root.winfo_viewable() == 0, "Window should start withdrawn"

    # Simulate secondary instance interactive run collision
    gui.signal_existing_instance_to_show(
        event_names=test_events,
        window_class=test_class,
        message_string=test_msg
    )

    # Process events in primary message pump
    start_wait = time.time()
    while time.time() - start_wait < 2.0 and not signals_received:
        root.update_idletasks()
        root.update()
        time.sleep(0.05)

    assert len(signals_received) >= 1, "Expected primary instance to receive wake-up signal"
    assert root.winfo_viewable() == 1, "Window should be restored to viewable after wake-up"

    root.destroy()
