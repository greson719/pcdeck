#!/usr/bin/env python3
"""
PCDeck MSIX Builder for Microsoft Store
Automates packaging dist/msix_layout into dist/PCDeck.msix using makeappx.exe
Supports setting Partner Center Package Identity parameters.
"""

import sys
import os
import shutil
import hashlib
import argparse
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
LAYOUT_DIR = DIST_DIR / "msix_layout"
MANIFEST_PATH = LAYOUT_DIR / "AppxManifest.xml"
OUTPUT_MSIX = DIST_DIR / "PCDeck.msix"

SDK_MAKEAPPX = ROOT_DIR / "build_tools" / "msix_sdk" / "makeappx.exe"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def sync_exe():
    src_exe = DIST_DIR / "PCDeck.exe"
    dst_exe = LAYOUT_DIR / "PCDeck.exe"
    if not src_exe.exists():
        print(f"[ERROR] Source executable not found: {src_exe}")
        sys.exit(1)
    if not dst_exe.exists() or src_exe.stat().st_mtime > dst_exe.stat().st_mtime:
        print(f"[*] Syncing updated PCDeck.exe to msix_layout...")
        shutil.copy2(src_exe, dst_exe)
    print(f"[+] Payload EXE verified: {dst_exe.name} ({dst_exe.stat().st_size:,} bytes)")

def update_manifest(identity_name: str = None, publisher: str = None, publisher_display: str = None, version: str = None):
    if not MANIFEST_PATH.exists():
        print(f"[ERROR] AppxManifest.xml not found at {MANIFEST_PATH}")
        sys.exit(1)

    # Register XML namespaces to avoid ns0 prefixes
    namespaces = {
        "": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
        "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
        "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
    }
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)

    tree = ET.parse(MANIFEST_PATH)
    root = tree.getroot()

    ns = {"appx": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
    identity = root.find("appx:Identity", ns)
    properties = root.find("appx:Properties", ns)

    modified = False
    if identity is not None:
        if identity_name and identity.get("Name") != identity_name:
            print(f"[*] Updating Identity Name: {identity.get('Name')} -> {identity_name}")
            identity.set("Name", identity_name)
            modified = True
        if publisher and identity.get("Publisher") != publisher:
            print(f"[*] Updating Identity Publisher: {identity.get('Publisher')} -> {publisher}")
            identity.set("Publisher", publisher)
            modified = True
        if version and identity.get("Version") != version:
            print(f"[*] Updating Identity Version: {identity.get('Version')} -> {version}")
            identity.set("Version", version)
            modified = True

    if properties is not None and publisher_display:
        pub_disp = properties.find("appx:PublisherDisplayName", ns)
        if pub_disp is not None and pub_disp.text != publisher_display:
            print(f"[*] Updating PublisherDisplayName: {pub_disp.text} -> {publisher_display}")
            pub_disp.text = publisher_display
            modified = True

    if modified:
        tree.write(MANIFEST_PATH, encoding="utf-8", xml_declaration=True)
        print("[+] AppxManifest.xml updated successfully.")
    else:
        print("[+] AppxManifest.xml is up to date.")

def run_makeappx():
    if not SDK_MAKEAPPX.exists():
        print(f"[ERROR] makeappx.exe not found at {SDK_MAKEAPPX}")
        sys.exit(1)

    print(f"[*] Packaging MSIX from {LAYOUT_DIR} -> {OUTPUT_MSIX}...")
    cmd = [
        str(SDK_MAKEAPPX),
        "pack",
        "/d", str(LAYOUT_DIR),
        "/p", str(OUTPUT_MSIX),
        "/o"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] makeappx failed (code {res.returncode}):")
        print(res.stdout)
        print(res.stderr)
        sys.exit(res.returncode)
    
    size_mb = OUTPUT_MSIX.stat().st_size / (1024 * 1024)
    sha256 = compute_sha256(OUTPUT_MSIX)
    print(f"\n==================================================")
    print(f" SUCCESS: MSIX Package Generated")
    print(f" Path:   {OUTPUT_MSIX}")
    print(f" Size:   {size_mb:.2f} MB ({OUTPUT_MSIX.stat().st_size:,} bytes)")
    print(f" SHA256: {sha256}")
    print(f"==================================================\n")

SDK_SIGNTOOL = ROOT_DIR / "build_tools" / "msix_sdk" / "signtool.exe"
PFX_PATH = ROOT_DIR / "build_tools" / "PCDeckTest.pfx"
PFX_PASS = "PCDeck123"

def sign_msix():
    if not SDK_SIGNTOOL.exists() or not PFX_PATH.exists():
        print(f"[*] Skipping signing (signtool or PFX not present). Store will sign automatically upon upload.")
        return
    print(f"[*] Signing {OUTPUT_MSIX} with local test certificate for immediate local install/testing...")
    cmd = [
        str(SDK_SIGNTOOL),
        "sign",
        "/fd", "SHA256",
        "/a",
        "/f", str(PFX_PATH),
        "/p", PFX_PASS,
        str(OUTPUT_MSIX)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print("[+] Package successfully signed! Can be double-clicked and installed locally.")
    else:
        print(f"[!] Warning: Signing failed (code {res.returncode}): {res.stderr.strip()}")

def main():
    parser = argparse.ArgumentParser(description="Build PCDeck.msix package for Microsoft Store")
    parser.add_argument("--identity-name", default="GresonParichha.PCDeck", help="Package Identity Name from Partner Center")
    parser.add_argument("--publisher", default="CN=EE1A7F1B-8959-4B69-B895-5E5FF21E385E", help="Publisher string from Partner Center")
    parser.add_argument("--publisher-display-name", default="Greson Parichha", help="Publisher Display Name (default: Greson Parichha)")
    parser.add_argument("--version", default="2.7.2.0", help="App version string (e.g. 2.7.2.0)")
    args = parser.parse_args()

    sync_exe()
    update_manifest(
        identity_name=args.identity_name,
        publisher=args.publisher,
        publisher_display=args.publisher_display_name,
        version=args.version
    )
    run_makeappx()
    sign_msix()

if __name__ == "__main__":
    main()

