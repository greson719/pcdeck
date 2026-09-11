#!/usr/bin/env python3
"""
tools/submit_indexnow.py
Submits all URLs listed in sitemap.xml to IndexNow and Bing for instant crawling and indexing.
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

HOST = "pcdeck.vercel.app"
KEY = "7b2d5f8a9e1c4a3b8d0f2e6c4b8a1d7e"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
SITEMAP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sitemap.xml")

ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]

def get_urls():
    tree = ET.parse(SITEMAP_PATH)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [elem.text.strip() for elem in tree.findall(".//sm:loc", ns) if elem.text]

def submit():
    urls = get_urls()
    print(f"Found {len(urls)} URLs in {SITEMAP_PATH}")

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")

    all_success = True
    for endpoint in ENDPOINTS:
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                print(f"[SUCCESS] {endpoint} -> HTTP {res.status} {res.reason}")
        except Exception as err:
            print(f"[ERROR]   {endpoint} -> {err}")
            all_success = False

    return all_success

if __name__ == "__main__":
    success = submit()
    sys.exit(0 if success else 1)
