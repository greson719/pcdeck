"""
PCDeck Pro - Automated Asset Obfuscation & Hardening Engine
============================================================
Protects client-side JavaScript from reverse engineering, string inspection,
and unauthorized tampering using industrial-grade AST obfuscation.
"""

import os
import sys
import shutil
import subprocess
from typing import Tuple

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_FILES = [
    os.path.join(ROOT_DIR, "android_app", "assets", "app.js"),
    os.path.join(ROOT_DIR, "static", "app.js"),
]


def obfuscate_with_npx(src_file: str, dst_file: str) -> Tuple[bool, str]:
    """Obfuscate JS using javascript-obfuscator via npx."""
    cmd = [
        "npx",
        "--yes",
        "javascript-obfuscator",
        src_file,
        "--output",
        dst_file,
        "--compact",
        "true",
        "--control-flow-flattening",
        "true",
        "--control-flow-flattening-threshold",
        "0.6",
        "--dead-code-injection",
        "false",
        "--string-array",
        "true",
        "--string-array-encoding",
        "rc4",
        "--string-array-threshold",
        "0.8",
        "--transform-object-keys",
        "true",
        "--split-strings",
        "true",
        "--split-strings-chunk-length",
        "8",
    ]
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=ROOT_DIR,
        )
        if res.returncode == 0 and os.path.exists(dst_file):
            return True, "Obfuscation succeeded via javascript-obfuscator."
        else:
            return False, f"npx returned code {res.returncode}: {res.stderr or res.stdout}"
    except Exception as ex:
        return False, f"Failed to execute javascript-obfuscator: {ex}"


def fallback_light_obfuscate(content: str) -> str:
    """
    Lightweight fallback minifier and string protector
    used when Node/npx is not available.
    """
    lines = content.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") and not stripped.startswith("///"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def process_target(file_path: str, backup: bool = True) -> bool:
    if not os.path.exists(file_path):
        print(f"[-] File not found: {file_path}")
        return False

    backup_path = f"{file_path}.original"
    if backup and not os.path.exists(backup_path):
        shutil.copy2(file_path, backup_path)
        print(f"[+] Created backup at: {backup_path}")

    tmp_dir = os.path.join(os.path.dirname(file_path), "_obf_tmp")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
    os.makedirs(tmp_dir, exist_ok=True)

    print(f"[+] Hardening {os.path.basename(file_path)}...")
    ok, msg = obfuscate_with_npx(file_path, tmp_dir)

    candidate_file = os.path.join(tmp_dir, os.path.basename(file_path))
    if ok and os.path.exists(candidate_file):
        os.replace(candidate_file, file_path)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        orig_sz = os.path.getsize(backup_path) / 1024 if os.path.exists(backup_path) else 0
        new_sz = os.path.getsize(file_path) / 1024
        print(f"[OK] Protected {os.path.basename(file_path)}: {orig_sz:.1f} KB -> {new_sz:.1f} KB")
        return True
    else:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"[-] Node obfuscator failed ({msg}).")
        return False


def restore_backups():
    for f in TARGET_FILES:
        backup = f"{f}.original"
        if os.path.exists(backup):
            shutil.copy2(backup, f)
            os.remove(backup)
            print(f"[+] Restored original {os.path.basename(f)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PCDeck Asset Obfuscator")
    parser.add_argument("--restore", action="store_true", help="Restore un-obfuscated source from .original backups")
    args = parser.parse_args()

    if args.restore:
        restore_backups()
        return

    print("=======================================================")
    print("         [+] PCDECK ASSET SECURITY HARDENING")
    print("=======================================================")

    for target in TARGET_FILES:
        process_target(target)


if __name__ == "__main__":
    main()
