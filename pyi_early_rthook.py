import sys

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PCDeckPro.NeonMouse.v2026")
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    except Exception:
        pass

try:
    import pyimod02_importers
    if hasattr(pyimod02_importers, "PyiFrozenLoader") and not hasattr(pyimod02_importers, "PyiFrozenImporter"):
        pyimod02_importers.PyiFrozenImporter = pyimod02_importers.PyiFrozenLoader
    elif hasattr(pyimod02_importers, "PyiFrozenImporter") and not hasattr(pyimod02_importers, "PyiFrozenLoader"):
        pyimod02_importers.PyiFrozenLoader = pyimod02_importers.PyiFrozenImporter
    if not hasattr(pyimod02_importers, "PyiFrozenImporter"):
        class _FallbackImporter:
            pass
        pyimod02_importers.PyiFrozenImporter = _FallbackImporter
except Exception:
    pass

