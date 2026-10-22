#!/usr/bin/env python3
"""
tools/migrate_domain_to_getpcdeck.py
Comprehensive domain migration script to migrate all references from
https://pcdeck.vercel.app to https://getpcdeck.com across:
- Website HTML files (canonicals, OpenGraph, Twitter, JSON-LD schemas, breadcrumbs, footers)
- sitemap.xml & website/sitemap.xml
- robots.txt & website/robots.txt
- llms.txt & website/llms.txt
- version.json (all locations)
- api/version.js (both locations)
- install scripts (install.ps1, install.sh, run_linux.sh)
- app.js (static & android_app)
- desktop.html & connect.html
- server/gui.py
- tools/submit_indexnow.py & workflow
- AndroidManifest.xml (intent-filters)
- README.md & store listings
"""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OLD_DOMAIN = "pcdeck.vercel.app"
NEW_DOMAIN = "getpcdeck.com"
OLD_URL = f"https://{OLD_DOMAIN}"
NEW_URL = f"https://{NEW_DOMAIN}"

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "build", "dist", "build_android",
    "node_modules", "__pycache__", "brain"
}

def migrate_text_file(path: Path) -> int:
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return 0

    original = content

    # 1. Direct URL replacements
    content = content.replace(f"https://{OLD_DOMAIN}/", f"https://{NEW_DOMAIN}/")
    content = content.replace(f"https://{OLD_DOMAIN}", f"https://{NEW_DOMAIN}")
    content = content.replace(f"http://{OLD_DOMAIN}/", f"https://{NEW_DOMAIN}/")
    content = content.replace(f"http://{OLD_DOMAIN}", f"https://{NEW_DOMAIN}")

    # 2. Host string replacements in specific contexts (like IndexNow HOST or plain text)
    # Be careful not to replace in documentation explaining the alias
    if path.name in ("submit_indexnow.py", ".env.example", "indexnow.yml", "robots.txt"):
        content = content.replace(f"HOST = \"{OLD_DOMAIN}\"", f"HOST = \"{NEW_DOMAIN}\"")
        content = content.replace(f"host': '{OLD_DOMAIN}'", f"host': '{NEW_DOMAIN}'")
        content = content.replace(f"INDEXNOW_HOST={OLD_DOMAIN}", f"INDEXNOW_HOST={NEW_DOMAIN}")
        content = content.replace(f"robots.txt - {OLD_URL}/", f"robots.txt - {NEW_URL}/")

    if content != original:
        path.write_text(content, encoding="utf-8")
        return 1
    return 0

def migrate_all_files():
    total_modified = 0

    # Target specific extensions
    target_extensions = {".html", ".xml", ".txt", ".json", ".js", ".py", ".sh", ".ps1", ".md", ".iss"}

    for root_dir, dirs, files in os.walk(ROOT):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            p = Path(root_dir) / file
            if p.suffix.lower() in target_extensions or p.name in ("robots.txt", "llms.txt", "sitemap.xml", "version.json"):
                # Skip the migration script itself
                if p.name == "migrate_domain_to_getpcdeck.py":
                    continue
                # Skip PROJECT_CONTEXT.md and WEBSITE_CONTEXT.md from wholesale blind replace so our historical records stay accurate
                if p.name in ("PROJECT_CONTEXT.md", "WEBSITE_CONTEXT.md"):
                    continue

                if migrate_text_file(p):
                    total_modified += 1
                    rel = p.relative_to(ROOT)
                    print(f"  [+] Migrated: {rel}")

    print(f"\n[OK] Successfully migrated {total_modified} files to {NEW_DOMAIN}")

def update_manifest():
    manifest_path = ROOT / "android_app" / "AndroidManifest.xml"
    if not manifest_path.exists():
        return

    content = manifest_path.read_text(encoding="utf-8")
    if 'android:host="getpcdeck.com"' in content:
        print("  [*] AndroidManifest.xml already contains getpcdeck.com")
        return

    # Add getpcdeck.com and www.getpcdeck.com to the intent-filter
    old_target = '<data android:scheme="https" android:host="pcdeck.vercel.app" android:pathPrefix="/connect" />'
    replacement = (
        '<data android:scheme="https" android:host="getpcdeck.com" android:pathPrefix="/connect" />\n'
        '                <data android:scheme="http" android:host="getpcdeck.com" android:pathPrefix="/connect" />\n'
        '                <data android:scheme="https" android:host="www.getpcdeck.com" android:pathPrefix="/connect" />\n'
        '                <data android:scheme="https" android:host="pcdeck.vercel.app" android:pathPrefix="/connect" />'
    )

    if old_target in content:
        content = content.replace(old_target, replacement)
        manifest_path.write_text(content, encoding="utf-8")
        print("  [+] AndroidManifest.xml updated with getpcdeck.com App Links!")

def update_api_version():
    api_path = ROOT / "api" / "version.js"
    website_api_path = ROOT / "website" / "api" / "version.js"

    for p in (api_path, website_api_path):
        if p.exists():
            c = p.read_text(encoding="utf-8")
            c = c.replace('versionCode: 272', 'versionCode: 276')
            c = c.replace('versionName: "2.7.2"', 'versionName: "2.7.6"')
            c = c.replace(OLD_URL, NEW_URL)
            p.write_text(c, encoding="utf-8")
            print(f"  [+] Synchronized API version in: {p.relative_to(ROOT)}")

if __name__ == "__main__":
    print(f"[!] Beginning Migration: {OLD_DOMAIN} -> {NEW_DOMAIN} ...\n")
    migrate_all_files()
    update_manifest()
    update_api_version()
    print("\n[COMPLETE] Domain migration script finished successfully.")
