#!/usr/bin/env python3
"""
Sync canonical website files from website/ to project root (./) for Vercel deployment.
Root serves as Vercel's deployment root, so keeping root and website/ in 100% sync
ensures all pages, scripts, guides, and international landing pages resolve correctly.
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEBSITE = ROOT / "website"

EXCLUDED_NAMES = {
    ".git",
    ".github",
    ".gitignore",
    ".vercelignore",
    "PROJECT_CONTEXT.md",
    "PCDeck-Setup.exe",
    "PCDeck.exe",
    "PCDeck.apk",
    "PCDeck.aab",
    "PCDeck_Master_Logo.png",
    "icon.png",  # Preserve high-res master icon at root
}

def sync_website():
    if not WEBSITE.exists():
        print("[-] website/ directory not found.")
        return

    synced_count = 0
    for item in WEBSITE.iterdir():
        if item.name in EXCLUDED_NAMES:
            continue

        dest = ROOT / item.name

        if item.is_dir():
            # Copy directory tree
            shutil.copytree(item, dest, dirs_exist_ok=True)
            synced_count += 1
            print(f"  [+] Synced directory: {item.name}/")
        elif item.is_file():
            # Copy file
            shutil.copy2(item, dest)
            synced_count += 1
            print(f"  [+] Synced file: {item.name}")

    print(f"\n[OK] Successfully synchronized {synced_count} website components to project root.")

if __name__ == "__main__":
    sync_website()
