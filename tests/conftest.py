import os
import sys
import pytest
import tkinter as tk

# Ensure Tkinter / Tcl always finds init.tcl across sequential test modules in Python 3.12
tcl_dir = os.path.join(sys.prefix, "tcl", "tcl8.6")
tk_dir = os.path.join(sys.prefix, "tcl", "tk8.6")
if os.path.exists(tcl_dir):
    os.environ["TCL_LIBRARY"] = tcl_dir
if os.path.exists(tk_dir):
    os.environ["TK_LIBRARY"] = tk_dir

# Suppress real pystray background message loops and blocking joins in headless / test environments
try:
    import pystray
    pystray.Icon.run_detached = lambda self: None
    pystray.Icon.stop = lambda self: None
except Exception:
    pass

# Prevent GUI tests from spawning live uvicorn servers on port 8000
try:
    from server.gui import PCDeckProGUI
    PCDeckProGUI.start_server = lambda self: None
except Exception:
    pass

# Mock outbound live license server requests in tests to avoid network timeouts / hangs
import urllib.request
_orig_urlopen = urllib.request.urlopen
def _safe_test_urlopen(req, *args, **kwargs):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if "dodopayments.com" in url:
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
    return _orig_urlopen(req, *args, **kwargs)
urllib.request.urlopen = _safe_test_urlopen

_shared_root = None

@pytest.fixture(scope="session")
def shared_tk_root():
    global _shared_root
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        pytest.skip("Tkinter GUI tests require Windows or X11 DISPLAY")
    if _shared_root is None:
        try:
            _shared_root = tk.Tk()
            _shared_root.withdraw()
        except Exception as e:
            pytest.skip(f"Tkinter unavailable: {e}")
    yield _shared_root
