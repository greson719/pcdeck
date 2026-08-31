"""Regenerate the SHA-256 table published on the PCDeck download page.

The site tells people to verify their download against a published checksum,
which is the only trust signal an unsigned app has. That promise only holds if
the number on the page matches the file that is actually shipped, so the table
is generated from the binaries rather than typed by hand: a stale checksum is
worse than no checksum, because it tells an honest user their good download is
corrupt and sends them chasing a problem that does not exist.

Run this after every rebuild, before committing:
    python tools/update_checksums.py

It rewrites the block between the CHECKSUMS:BEGIN / CHECKSUMS:END markers in
website/index.html and leaves the rest of the file untouched. Exit code is 1 if
a binary is missing, so it can be wired into a release script.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SITE = os.path.join(ROOT, "website")
PAGE = os.path.join(SITE, "index.html")

# Order here is the order shown on the page: phone first, matching the cards.
TARGETS = ["PCDeck.apk", "PCDeck.aab", "PCDeck.exe", "PCDeck.msix", "PCDeck_Package.zip"]

BEGIN = "<!-- CHECKSUMS:BEGIN"
END = "<!-- CHECKSUMS:END -->"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    # 1 MB chunks: these are 60 MB files, so do not read them whole.
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    rows = []
    missing = []

    for name in TARGETS:
        path = os.path.join(SITE, name)
        if not os.path.exists(path):
            path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            missing.append(name)
            continue
        digest = sha256(path)
        size = os.path.getsize(path)
        rows.append(
            "        <dl class=\"sumrow\">\n"
            f"          <dt>{name}<span>{size:,} BYTES</span></dt>\n"
            f"          <dd>{digest}</dd>\n"
            "        </dl>"
        )
        print(f"{name:<22} {size:>12,} B  {digest}")

    if missing:
        print(f"\nERROR: not found in website/: {', '.join(missing)}", file=sys.stderr)
        print("Build them first, or drop them from TARGETS.", file=sys.stderr)
        return 1

    html = io.open(PAGE, encoding="utf-8").read()

    start = html.find(BEGIN)
    stop = html.find(END)
    if start == -1 or stop == -1:
        print(f"\nERROR: markers not found in {PAGE}", file=sys.stderr)
        return 1

    # Keep the BEGIN comment itself (it carries the do-not-hand-edit note) and
    # replace only what sits between it and END.
    head_end = html.index("-->", start) + 3
    new = html[:head_end] + "\n" + "\n".join(rows) + "\n        " + html[stop:]

    if new == html:
        print("\nNo change — checksums already current.")
        return 0

    io.open(PAGE, "w", encoding="utf-8", newline="\n").write(new)
    print(f"\nUpdated {os.path.normpath(PAGE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
