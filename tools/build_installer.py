#!/usr/bin/env python3
"""
Automated Win32 Installer Builder for PCDeck.
Locates Inno Setup Compiler (ISCC), compiles PCDeck_Setup.iss into PCDeck-Setup.exe,
and distributes the release binary into msstore_assets/ and website/.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISS_FILE = ROOT / "PCDeck_Setup.iss"
OUTPUT_SETUP = ROOT / "PCDeck-Setup.exe"
WEBSITE_DIR = ROOT / "website"
MSSTORE_DIR = ROOT / "msstore_assets"


def find_iscc() -> Path:
    """Finds the Inno Setup Compiler (ISCC.exe)."""
    # 1. Check PATH
    iscc_in_path = shutil.which("iscc") or shutil.which("iscc.exe")
    if iscc_in_path:
        return Path(iscc_in_path)

    # 2. Check standard installation directories
    candidate_dirs = [
        Path("C:/Program Files (x86)/Inno Setup 6"),
        Path("C:/Program Files/Inno Setup 6"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6",
        Path("C:/Program Files (x86)/Inno Setup 5"),
    ]

    for candidate in candidate_dirs:
        iscc = candidate / "ISCC.exe"
        if iscc.exists():
            return iscc

    return None


def build_installer():
    print("=======================================================")
    print("       [+] BUILDING PCDECK WIN32 INSTALLER (.EXE)      ")
    print("=======================================================")

    exe_path = ROOT / "PCDeck.exe"
    if not exe_path.exists():
        print(f"[!] Error: {exe_path} not found.")
        print("    Running build_exe.py first...")
        import build_exe
        build_exe.build()

    iscc_path = find_iscc()
    if not iscc_path or not iscc_path.exists():
        print("[!] Error: Inno Setup Compiler (ISCC.exe) not found on system.")
        print("    Please install Inno Setup 6 (e.g. winget install JRSoftware.InnoSetup).")
        sys.exit(1)

    print(f"[*] Using Inno Setup Compiler: {iscc_path}")
    print(f"[*] Compiling script: {ISS_FILE}")

    cmd = [str(iscc_path), f"/O{ROOT}", f"/FPCDeck-Setup", str(ISS_FILE)]
    res = subprocess.run(cmd, cwd=str(ROOT))

    if res.returncode != 0 or not OUTPUT_SETUP.exists():
        print("[-] Installer compilation failed.")
        sys.exit(1)

    size_mb = OUTPUT_SETUP.stat().st_size / (1024 * 1024)
    print(f"\n[OK] Successfully generated: {OUTPUT_SETUP.name} ({size_mb:.2f} MB)")

    # Copy to website/
    if WEBSITE_DIR.exists():
        dest_web = WEBSITE_DIR / "PCDeck-Setup.exe"
        shutil.copy2(OUTPUT_SETUP, dest_web)
        print(f"  [+] Copied to {dest_web.relative_to(ROOT)}")

    # Copy to msstore_assets/
    if MSSTORE_DIR.exists():
        dest_msstore = MSSTORE_DIR / "PCDeck-Setup.exe"
        shutil.copy2(OUTPUT_SETUP, dest_msstore)
        print(f"  [+] Copied to {dest_msstore.relative_to(ROOT)}")

    # Update checksums
    print("\n[*] Updating download page SHA-256 checksums...")
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import update_checksums
        update_checksums.main()
    except Exception as e:
        print(f"[-] Note: update_checksums encountered: {e}")

    print("\n=======================================================")
    print(" [SUCCESS] PCDeck-Setup.exe is ready for Store & Web!  ")
    print("=======================================================")


if __name__ == "__main__":
    build_installer()
