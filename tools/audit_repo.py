#!/usr/bin/env python3
"""
PCDeck Automated Invariant & Blind-Spot Auditor.
Exits with code 1 if ANY architectural, parity, version, or security invariant is violated.
"""
import filecmp
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERRORS = []

def fail(msg: str):
    ERRORS.append(f"[FATAL INVARIANT VIOLATION] {msg}")

# 1. File Mirror Parity Check
MIRRORS = [
    ("static/app.js", "android_app/assets/app.js"),
    ("static/index.html", "android_app/assets/index.html"),
    ("version.json", "static/version.json"),
    ("version.json", "android_app/assets/version.json"),
    ("version.json", "website/version.json"),
]
for src, dst in MIRRORS:
    p1, p2 = ROOT / src, ROOT / dst
    if not p1.exists():
        fail(f"Source file missing: {src}")
    elif not p2.exists():
        fail(f"Mirror destination missing: {dst}")
    else:
        if not filecmp.cmp(p1, p2, shallow=False):
            fail(f"File mismatch: {src} != {dst}. Run sync script immediately.")

# 2. Cross-Platform Version Parity Check
try:
    ver_json = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
    v_code = str(ver_json["versionCode"])
    v_name = ver_json["versionName"]

    app_js = (ROOT / "static/app.js").read_text(encoding="utf-8")
    if f"CURRENT_APP_VERSION_CODE = {v_code}" not in app_js:
        fail(f"static/app.js CURRENT_APP_VERSION_CODE does not match version.json ({v_code})")
    if f"CURRENT_APP_VERSION_NAME = '{v_name}'" not in app_js and f'CURRENT_APP_VERSION_NAME = "{v_name}"' not in app_js:
        fail(f"static/app.js CURRENT_APP_VERSION_NAME does not match version.json ({v_name})")

    manifest = (ROOT / "android_app/AndroidManifest.xml").read_text(encoding="utf-8")
    if f'android:versionCode="{v_code}"' not in manifest or f'android:versionName="{v_name}"' not in manifest:
        fail(f"AndroidManifest.xml version does not match version.json ({v_name} / {v_code})")
except Exception as e:
    fail(f"Version parity check failed: {e}")

# 3. License Case-Sensitivity Regression Check (Anti-404 Guard)
LICENSE_FILES = ["static/app.js", "server/license_manager.py", "server/main.py", "server/gui.py"]
for fpath in LICENSE_FILES:
    p = ROOT / fpath
    if p.exists():
        content = p.read_text(encoding="utf-8")
        if re.search(r"license.*(?:\.upper\(\)|\.toUpperCase\(\))", content, re.IGNORECASE):
            fail(f"{fpath} contains uppercase conversion on a license key! Dodo UUIDs must be .lower() / .toLowerCase().")

# 4. Customer PII and Secret Leaks (Salted SHA-256 token matching across all files)
FORBIDDEN_PII_HASHES = {
    "939a63dd6e6e18ee3755478d5f8fe862c41291db82e0b08f3085814a18511ca0": "Customer email leaked in repository",
    "3bc0ee599608cbbd301827edac3c5014584266e91388455fc2a3d13d60fd9522": "Live customer license UUID leaked in repository",
    "2d08eb625e16d741fd953abe77071818c357cd3f6e02154488dbf2459f52be1c": "Live customer license UUID leaked in repository",
}

TOKEN_PATTERN = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

# Deprecated binaries forbidden from active distribution download cards & active build scripts
ACTIVE_DIST_FILES = [
    "index.html",
    "website/index.html",
    "download/index.html",
    "website/download/index.html",
    "build_exe.py",
    "build_msix.py",
    "build_apk.py",
    "PCDeck.spec",
]

for path in ROOT.rglob("*"):
    if path.is_file() and ".git" not in path.parts and ".venv" not in path.parts and "dist" not in path.parts:
        if path.name == "audit_repo.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token_match in TOKEN_PATTERN.finditer(text):
                raw_token = token_match.group(0).strip().lower()
                token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
                if token_hash in FORBIDDEN_PII_HASHES:
                    fail(f"{path.relative_to(ROOT)}: {FORBIDDEN_PII_HASHES[token_hash]}")
        except Exception:
            pass

# Check active distribution files for deprecated binaries
DEPRECATED_BIN_PATTERNS = [
    (r"PCDeck_Package\.zip", "Deprecated ZIP package offered in active download page/script"),
    (r"PCDeck-Setup\.exe", "Deprecated Inno Setup installer offered in active download page/script"),
]
for rel_path in ACTIVE_DIST_FILES:
    p = ROOT / rel_path
    if p.exists():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pattern, reason in DEPRECATED_BIN_PATTERNS:
            if re.search(pattern, text):
                fail(f"{rel_path}: {reason}")

# 5. Public Website Exposure Check (No internal markdown docs in website/)
if (ROOT / "website").exists():
    for md_file in (ROOT / "website").rglob("*.md"):
        fail(f"Internal markdown doc found in website/ ({md_file.name}). Vercel must not serve internal docs!")

# 6. APK Internal Asset Parity Check (Deterministic in-memory zip inspection)
apk_path = ROOT / "PCDeck.apk"
if not apk_path.exists():
    fail("PCDeck.apk is missing from repository root!")
else:
    try:
        with zipfile.ZipFile(apk_path, "r") as z:
            for asset_name, disk_file in [
                ("assets/app.js", ROOT / "static/app.js"),
                ("assets/index.html", ROOT / "static/index.html"),
            ]:
                apk_data = z.read(asset_name)
                disk_data = disk_file.read_bytes()
                apk_h = hashlib.sha256(apk_data.replace(b"\r\n", b"\n")).hexdigest()
                disk_h = hashlib.sha256(disk_data.replace(b"\r\n", b"\n")).hexdigest()
                if apk_h != disk_h:
                    fail(f"PCDeck.apk {asset_name} hash ({apk_h[:12]}) != {disk_file.name} ({disk_h[:12]}). Run python build_apk.py!")
    except Exception as e:
        fail(f"Failed to inspect PCDeck.apk zip contents: {e}")

# 7. Executable Freshness Check
exe_path = ROOT / "PCDeck.exe"
if exe_path.exists():
    exe_mtime = exe_path.stat().st_mtime
    for src in ["server/main.py", "server/gui.py", "server/license_manager.py", "server/screen_streamer.py", "PCDeck.apk"]:
        p = ROOT / src
        if p.exists() and p.stat().st_mtime > (exe_mtime + 2.0):
            print(f"[WARNING] {src} is newer than PCDeck.exe! Run `python build_exe.py` before releasing.")

# 8. CI Workflow Test Integrity Check (Anti-Reward Hacking)
workflow_path = ROOT / ".github/workflows/verify.yml"
if workflow_path.exists():
    wf_text = workflow_path.read_text(encoding="utf-8")
    if "pytest tests/" not in wf_text:
        fail(".github/workflows/verify.yml MUST run 'pytest tests/' across all tests. Cherry-picking test files in CI is forbidden!")

if ERRORS:
    print("\n".join(ERRORS))
    print(f"\nAUDIT FAILED WITH {len(ERRORS)} ERROR(S).")
    sys.exit(1)
else:
    print("ALL PCDECK INVARIANTS PASSED (0 errors).")
    sys.exit(0)
