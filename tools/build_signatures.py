"""
Build a pre-computed signature index for the goods catalog.

For each entry in `lib/data/catalog/*.dart` that has an imageUrl, this script:
  1. Downloads the image
  2. Computes a 16×16 RGB signature (768 bytes) — same algorithm as the
     in-app ImageSimilarityService
  3. Writes a binary file at `assets/catalog_signatures.bin` mapping
     <url-hash:8 bytes> → <signature:768 bytes>

The app loads this file at startup and uses it directly — no network
required during the user's image search.

Usage:
    pip install pillow requests
    python tools/build_signatures.py

Re-run whenever the catalog changes significantly. The output file is
~1MB for 1300 entries.
"""
from __future__ import annotations

import hashlib
import os
import re
import struct
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

# Force UTF-8 stdout on Windows so Korean / em-dash etc. print cleanly.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import requests
    from PIL import Image
except ImportError:
    print("Need: pip install pillow requests")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "lib" / "data" / "catalog"
OUT_PATH = ROOT / "assets" / "catalog_signatures.bin"
GRID = 16
SIG_BYTES = GRID * GRID * 3  # 768

IMAGE_URL_RE = re.compile(r"imageUrl\s*:\s*'([^']+)'")


def extract_urls() -> set[str]:
    urls: set[str] = set()
    for dart in CATALOG_DIR.glob("*.dart"):
        if dart.name == "all.dart":
            continue
        text = dart.read_text(encoding="utf-8")
        for m in IMAGE_URL_RE.finditer(text):
            raw = m.group(1).strip()
            if not raw:
                continue
            raw = raw.replace("&amp;", "&")
            if raw.startswith("//"):
                raw = "https:" + raw
            if raw.startswith("http"):
                urls.add(raw)
    return urls


def url_hash(url: str) -> bytes:
    return hashlib.sha256(url.encode("utf-8")).digest()[:8]


def signature_for(url: str) -> bytes | None:
    """Three-channel 768-byte signature matching the Dart service.

    bytes 0..255   gray  (16x16 grayscale per-pixel)
    bytes 256..511 phash (median-based bit pattern, 0 or 255)
    bytes 512..767 hist  (HSV histogram: 16 H * 8 S * 2 V, max-normalized)
    """
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200 or not r.content:
            return None
        im = Image.open(BytesIO(r.content)).convert("RGB")
        w, h = im.size
        # Aggressive 80% center-crop to drop most background.
        side = min(w, h) * 8 // 10
        left = (w - side) // 2
        top = (h - side) // 2
        im = im.crop((left, top, left + side, top + side))
        im = im.resize((GRID, GRID), Image.LANCZOS)

        # gray (luminance)
        gray = [0] * 256
        pixels = im.load()
        for y in range(GRID):
            for x in range(GRID):
                r_, g_, b_ = pixels[x, y]
                v = int(round(r_ * 0.299 + g_ * 0.587 + b_ * 0.114))
                gray[y * GRID + x] = max(0, min(255, v))

        # pHash (median split)
        median = sorted(gray)[128]
        phash = [255 if v > median else 0 for v in gray]

        # HSV histogram (256 bins)
        hist = [0] * 256
        for y in range(GRID):
            for x in range(GRID):
                r_, g_, b_ = pixels[x, y]
                rn, gn, bn = r_ / 255.0, g_ / 255.0, b_ / 255.0
                mx = max(rn, gn, bn)
                mn = min(rn, gn, bn)
                delta = mx - mn
                if delta == 0:
                    hue = 0.0
                elif mx == rn:
                    hue = (60 * ((gn - bn) / delta) + 360) % 360
                elif mx == gn:
                    hue = 60 * ((bn - rn) / delta) + 120
                else:
                    hue = 60 * ((rn - gn) / delta) + 240
                sat = 0 if mx == 0 else delta / mx
                val = mx
                h_bin = min(15, int(hue / 360 * 16))
                s_bin = min(7, int(sat * 8))
                v_bin = min(1, int(val * 2))
                hist[h_bin * 16 + s_bin * 2 + v_bin] += 1
        hmax = max(hist) if max(hist) > 0 else 1
        hist_norm = [min(255, h * 255 // hmax) for h in hist]

        return bytes(gray) + bytes(phash) + bytes(hist_norm)
    except Exception:
        return None


def main() -> int:
    urls = sorted(extract_urls())
    print(f"Found {len(urls)} unique imageUrls")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results: dict[bytes, bytes] = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(signature_for, u): u for u in urls}
        done = 0
        for fut in as_completed(futures):
            done += 1
            url = futures[fut]
            sig = fut.result()
            if sig and len(sig) == SIG_BYTES:
                results[url_hash(url)] = sig
            if done % 50 == 0 or done == len(urls):
                print(f"  {done}/{len(urls)} ({len(results)} signed)")

    # Binary format:
    #   [magic:4 'DKSG'] [version:u32 = 1] [count:u32]
    #   then `count` records of (hash:8 bytes, sig:768 bytes)
    with OUT_PATH.open("wb") as f:
        f.write(b"DKSG")
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", len(results)))
        for h, sig in results.items():
            f.write(h)
            f.write(sig)

    size_kb = OUT_PATH.stat().st_size / 1024
    print(
        f"Wrote {OUT_PATH.relative_to(ROOT)} — {len(results)} signatures, "
        f"{size_kb:.0f} KB"
    )
    print("Add to pubspec.yaml:  - assets/catalog_signatures.bin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
