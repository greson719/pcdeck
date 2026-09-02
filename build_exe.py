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

    cmd = [
        str(PYTHON_EXE), "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "PCDeck",
        "--icon", "app_icon.ico",
        "--add-data", "static;static",
        "--add-data", "app_icon.ico;.",
        "--add-data", "PCDeck.ico;.",
        "--add-data", "icon.ico;.",
        "--add-data", "PCDeck_Mouse_Logo.png;.",
        "--add-data", "PCDeck_Master_Logo.png;.",
        "--add-data", "PCDeck_Logo.png;.",
        "--add-data", "icon.png;.",
        "--add-data", "icon-512.png;.",
        "--hidden-import", "server.gui",
        "--hidden-import", "server.main",
        "--hidden-import", "server.screen_streamer",
        "--hidden-import", "server.gamepad_manager",
        "--hidden-import", "server.audio_streamer",
        "--hidden-import", "server.camera_streamer",
        "--hidden-import", "cv2",
        "--hidden-import", "simplejpeg",
        "--hidden-import", "numpy",
        "--hidden-import", "vgamepad",
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
        try:
            shutil.copy2(dist_exe, target_exe)
            print(f"\n[OK] SUCCESS: Built and updated PCDeck.exe at root ({target_exe.stat().st_size / (1024*1024):.1f} MB)")
        except PermissionError:
            print(f"\n[OK] SUCCESS: Built PCDeck.exe in dist/ ({dist_exe.stat().st_size / (1024*1024):.1f} MB). (Root PCDeck.exe is currently running - close it to overwrite).")

if __name__ == "__main__":
    build()
