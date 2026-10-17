#!/usr/bin/env python3
"""Import credited console hardware photos as optimized local WebP.

Each image is from Spela's Wikimedia Commons bundle. Original attribution and
licensing are recorded in data/console_photos.json. Do not mix with logo art.
"""
from __future__ import annotations
import concurrent.futures
import io
import json
import urllib.request
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/console_photos.json"
MAX_BYTES = 4_500_000
MAX_EDGE = 620

def import_photo(record):
    relative = str(record.get("file") or "")
    if not relative.startswith("assets/consoles/photos/") or ".." in relative or not relative.endswith(".webp"):
        return "invalid", relative
    target = ROOT / relative
    if target.exists() and target.stat().st_size > 400:
        return "cached", relative
    url = str(record.get("upstream") or "")
    if not url.startswith("https://raw.githubusercontent.com/mattias800/spela/"):
        return "invalid", relative
    request = urllib.request.Request(url, headers={"User-Agent": "NXFlowConsolePhotos/1.0", "Accept": "image/png"})
    with urllib.request.urlopen(request, timeout=40) as res:
        data = res.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "invalid", relative
    with Image.open(io.BytesIO(data)) as pic:
        pic.load()
        pic = ImageOps.exif_transpose(pic).convert("RGBA")
        if max(pic.size) > MAX_EDGE:
            pic.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        pic.save(target, "WEBP", quality=83, method=5, exact=True)
    return "saved", relative

def main():
    d = json.loads(META.read_text(encoding="utf-8"))
    photos = list(d["photos"].values())
    counts = {"saved": 0, "cached": 0, "invalid": 0, "error": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        results = list(pool.map(safely_import, photos))
    for status, target in results:
        counts[status] = counts.get(status,0) + 1
        print(status, target)
    print("Hardware photo import:", counts)
    if counts["saved"] + counts["cached"] < len(photos) - 2:
        raise RuntimeError("Too many photos missing; check image sources or network")

def safely_import(record):
    try:
        return import_photo(record)
    except Exception as exc:
        return "error", str(record.get("file"))+" -> "+str(exc)[:130]

if __name__ == "__main__":
    main()
