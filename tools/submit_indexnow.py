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
KEYS = [
    "7b2d5f8a9e1c4a3b8d0f2e6c4b8a1d7e",
    "2b967b3e45cd4a0cafab08e647e1fc47",
]
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

    all_success = True
    for key in KEYS:
        key_loc = f"https://{HOST}/{key}.txt"
        payload = {
            "host": HOST,
            "key": key,
            "keyLocation": key_loc,
            "urlList": urls,
        }
        data = json.dumps(payload).encode("utf-8")

        for endpoint in ENDPOINTS:
            sent = False
            for attempt in range(3):
                req = urllib.request.Request(
                    endpoint,
                    data=data,
                    headers={"Content-Type": "application/json; charset=utf-8"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=30) as res:
                        print(f"[SUCCESS] {endpoint} (key: {key[:8]}...) -> HTTP {res.status} {res.reason}")
                        sent = True
                        break
                except Exception as err:
                    if attempt == 2:
                        print(f"[ERROR]   {endpoint} (key: {key[:8]}...) -> {err}")
                    else:
                        import time
                        time.sleep(1)
            if not sent:
                all_success = False

    return all_success

if __name__ == "__main__":
    success = submit()
    sys.exit(0 if success else 1)
