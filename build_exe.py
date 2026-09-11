"""
Build Script for PCDeck Windows Executable (PCDeck.exe)
Uses PyInstaller in the local .venv with full hidden-import resolution for simplejpeg, vgamepad, and WASAPI audio.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"

def build():
    print("=======================================================")
    print("       [+] BUILDING PCDECK WINDOWS STANDALONE (.EXE)   ")
    print("=======================================================")

    # Remove nested APK inside static/ to prevent double-bundling inside the single executable
    static_apk = ROOT / "static" / "PCDeck.apk"
    if static_apk.exists():
        try:
            static_apk.unlink()
            print("    [+] Purged duplicate static/PCDeck.apk before packaging EXE")
        except Exception:
            pass

    cmd = [
        str(PYTHON_EXE), "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "PCDeck",
        "--icon", "app_icon.ico",
        "--version-file", "version_info.txt",
        "--add-data", "static;static",
        "--add-data", "drivers;drivers",
        "--add-data", "PCDeck.apk;.",
        "--add-data", "app_icon.ico;.",
        "--add-data", "PCDeck.ico;.",
        "--exclude-module", "PIL._avif",
        "--hidden-import", "server.gui",
        "--hidden-import", "server.main",
        "--hidden-import", "server.binary_protocol",
        "--hidden-import", "server.license_manager",
        "--hidden-import", "server.screen_streamer",
        "--hidden-import", "server.wifi_manager",
        "--hidden-import", "server.wifi_latency_manager",
        "--hidden-import", "server.gamepad_manager",
        "--hidden-import", "server.audio_streamer",
        "--hidden-import", "server.camera_streamer",
        "--hidden-import", "cv2",
        "--hidden-import", "simplejpeg",
        "--hidden-import", "numpy",
        "--hidden-import", "vgamepad",
        "--collect-all", "vgamepad",
        "--hidden-import", "pystray",
        "--collect-all", "pystray",
        "--hidden-import", "sounddevice",
        "--hidden-import", "pyaudiowpatch",
        "--hidden-import", "pyvirtualcam",
        "--hidden-import", "qrcode",
        "--hidden-import", "tkinter",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "pynput",
        "--hidden-import", "mss",
        "--hidden-import", "PIL",
        "server/gui.py"
    ]

    print("\n[+] Running PyInstaller build...")
    res = subprocess.run(cmd, cwd=str(ROOT))
    if res.returncode != 0:
        print("[-] Build failed.")
        sys.exit(1)

    dist_exe = ROOT / "dist" / "PCDeck.exe"
    target_exe = ROOT / "PCDeck.exe"
    if dist_exe.exists():
        for target in [target_exe, ROOT / "website" / "PCDeck.exe"]:
            if target == target_exe or target.parent.exists():
                try:
                    shutil.copy2(dist_exe, target)
                    print(f"\n[OK] SUCCESS: Copied PCDeck.exe to {target.relative_to(ROOT)} ({target.stat().st_size / (1024*1024):.1f} MB)")
                except PermissionError:
                    # Windows allows renaming a locked/running executable so the new binary can take its place
                    backup = target.with_name(f"{target.name}.old")
                    try:
                        if backup.exists():
                            try:
                                backup.unlink()
                            except Exception:
                                pass
                        target.rename(backup)
                        shutil.copy2(dist_exe, target)
                        print(f"\n[OK] SUCCESS: Replaced running {target.relative_to(ROOT)} (old binary moved to {backup.name})")
                    except Exception as e:
                        print(f"[-] Could not overwrite {target.name}: {e}. Standalone is available at dist/PCDeck.exe")

    # Restore static/PCDeck.apk for local server development
    if (ROOT / "PCDeck.apk").exists():
        try:
            shutil.copy2(ROOT / "PCDeck.apk", ROOT / "static" / "PCDeck.apk")
        except Exception:
            pass

    # Build Setup Installer (PCDeck-Setup.exe)
    iss_file = ROOT / "PCDeck_Setup.iss"
    if iss_file.exists():
        print("\n=======================================================")
        print("       [+] BUILDING PCDECK SETUP INSTALLER             ")
        print("=======================================================")
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            import build_installer
            build_installer.build_installer()
        except Exception as e:
            print(f"[-] Note: Setup installer build skipped: {e}")

if __name__ == "__main__":
    build()
