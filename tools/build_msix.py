#!/usr/bin/env python3
"""
Automated MSIX Packager for PCDeck.
Generates all high-DPI Store logo assets, AppxManifest.xml, packages PCDeck.msix,
and prepares the release bundle in msstore_assets/.
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist" / "msix_layout"
OUTPUT_MSIX = ROOT / "PCDeck.msix"
MSSTORE_DIR = ROOT / "msstore_assets"
MANIFEST_ASSETS_DIR = MSSTORE_DIR / "Manifest_Assets"

APPX_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap rescap">

  <Identity Name="PCDeck"
            Publisher="CN=PCDeck, O=PCDeck, C=US"
            Version="1.0.0.0"
            ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>PCDeck: Wireless Trackpad, Screen Mirror &amp; Remote</DisplayName>
    <PublisherDisplayName>Greshon Parichha</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
    <Description>Turn your smartphone into a wireless multi-touch trackpad, 60 FPS desktop screen mirror, live mechanical keyboard, audio loopback streamer, and cable-free file manager for Windows 10/11 over local Wi-Fi.</Description>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22621.0" />
  </Dependencies>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>

  <Applications>
    <Application Id="PCDeck"
                 Executable="PCDeck.exe"
                 EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="PCDeck"
                          Description="PCDeck Windows Server"
                          BackgroundColor="#0A0E17"
                          Square150x150Logo="Assets\\Square150x150Logo.png"
                          Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png"
                         Square310x310Logo="Assets\\Square310x310Logo.png"
                         ShortName="PCDeck" />
        <uap:SplashScreen Image="Assets\\SplashScreen.png" BackgroundColor="#0A0E17" />
      </uap:VisualElements>
    </Application>
  </Applications>
</Package>
"""

CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/vnd.ms-appx.manifest+xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="exe" ContentType="application/x-msdownload"/>
  <Default Extension="ico" ContentType="image/x-icon"/>
  <Default Extension="pfx" ContentType="application/x-pkcs12"/>
</Types>
"""


def ensure_manifest_assets():
    if not MANIFEST_ASSETS_DIR.exists() or len(list(MANIFEST_ASSETS_DIR.glob("*.png"))) < 10:
        print("[*] Generating High-DPI manifest assets first...")
        import generate_msstore_assets
        generate_msstore_assets.main()


def build_msix():
    print("[*] Starting automated MSIX layout generation...")
    ensure_manifest_assets()

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    exe_src = ROOT / "PCDeck.exe"
    if not exe_src.exists():
        print(f"[!] Error: {exe_src} not found. Please build or place PCDeck.exe in root first.")
        sys.exit(1)
    
    shutil.copy2(exe_src, DIST_DIR / "PCDeck.exe")
    print(f"  [+] Copied PCDeck.exe ({exe_src.stat().st_size / (1024*1024):.1f} MB)")

    # Copy all High-DPI Assets
    assets_dist = DIST_DIR / "Assets"
    assets_dist.mkdir(parents=True, exist_ok=True)
    for asset_file in MANIFEST_ASSETS_DIR.glob("*.png"):
        shutil.copy2(asset_file, assets_dist / asset_file.name)
    print(f"  [+] Copied {len(list(assets_dist.glob('*.png')))} High-DPI manifest assets into Assets/")

    (DIST_DIR / "AppxManifest.xml").write_text(APPX_MANIFEST, encoding="utf-8")
    (DIST_DIR / "[Content_Types].xml").write_text(CONTENT_TYPES_XML, encoding="utf-8")
    print("  [+] Generated AppxManifest.xml & [Content_Types].xml")

    makeappx_candidates = list(Path("C:/Program Files (x86)/Windows Kits/10/bin").glob("**/x64/makeappx.exe"))
    
    if makeappx_candidates:
        makeappx_exe = makeappx_candidates[-1]
        print(f"[*] Found Windows SDK makeappx: {makeappx_exe}")
        cmd = [str(makeappx_exe), "pack", "/d", str(DIST_DIR), "/p", str(OUTPUT_MSIX), "/o"]
        subprocess.run(cmd, check=True)
        print(f"[OK] Successfully built MSIX via makeappx: {OUTPUT_MSIX}")
    else:
        print("[*] Creating standard MSIX package container...")
        if OUTPUT_MSIX.exists():
            OUTPUT_MSIX.unlink()
        
        with zipfile.ZipFile(OUTPUT_MSIX, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(DIST_DIR):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(DIST_DIR)
                    zf.write(file_path, arcname)
        print(f"[OK] Created MSIX package container at: {OUTPUT_MSIX} ({OUTPUT_MSIX.stat().st_size / (1024*1024):.1f} MB)")

    # Copy to msstore_assets directory
    shutil.copy2(OUTPUT_MSIX, MSSTORE_DIR / "PCDeck.msix")
    print(f"  [+] Copied PCDeck.msix to msstore_assets/PCDeck.msix")


if __name__ == "__main__":
    build_msix()
