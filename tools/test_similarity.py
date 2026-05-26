"""
Test the bundled image-signature index to verify image search returns
diverse results for different queries.

Mirrors the Dart distance() function exactly:
  - gray  channel: L1
  - phash channel: 2 * L1  (weighted)
  - hist  channel: L1

Usage:  python tools/test_similarity.py
"""
from __future__ import annotations

import hashlib
import random
import re
import struct
import sys
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "lib" / "data" / "catalog"
BUNDLE = ROOT / "assets" / "catalog_signatures.bin"
GRID = 16
SIG = GRID * GRID * 3  # 768

NAME_RE = re.compile(r"nameKo\s*:\s*'([^']+)'")
IMAGE_RE = re.compile(r"imageUrl\s*:\s*'([^']+)'")


def load_catalog_entries() -> list[tuple[str, str, str]]:
    """Return (source_file, name, imageUrl) tuples from every catalog file."""
    out: list[tuple[str, str, str]] = []
    for dart in CATALOG_DIR.glob("*.dart"):
        if dart.name == "all.dart":
            continue
        src = dart.stem
        text = dart.read_text(encoding="utf-8")
        chunks = text.split("GoodsCatalogEntry(")
        for chunk in chunks[1:]:
            n = NAME_RE.search(chunk)
            i = IMAGE_RE.search(chunk)
            if not n or not i:
                continue
            name = n.group(1).strip()
            url = i.group(1).strip().replace("&amp;", "&")
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http"):
                out.append((src, name, url))
    return out


def url_key(url: str) -> bytes:
    return hashlib.sha256(url.encode("utf-8")).digest()[:8]


def load_bundle() -> dict[bytes, bytes]:
    raw = BUNDLE.read_bytes()
    assert raw[:4] == b"DKSG", "bundle magic mismatch"
    count = struct.unpack("<I", raw[8:12])[0]
    out: dict[bytes, bytes] = {}
    offset = 12
    for _ in range(count):
        key = raw[offset:offset + 8]
        sig = raw[offset + 8:offset + 8 + SIG]
        out[key] = sig
        offset += 8 + SIG
    return out


def signature_for_bytes(content: bytes) -> bytes | None:
    try:
        im = Image.open(BytesIO(content)).convert("RGB")
        w, h = im.size
        side = min(w, h) * 8 // 10
        left = (w - side) // 2
        top = (h - side) // 2
        im = im.crop((left, top, left + side, top + side))
        im = im.resize((GRID, GRID), Image.LANCZOS)

        gray = [0] * 256
        pixels = im.load()
        for y in range(GRID):
            for x in range(GRID):
                r_, g_, b_ = pixels[x, y]
                gray[y * GRID + x] = int(round(r_ * 0.299 + g_ * 0.587 + b_ * 0.114))

        median = sorted(gray)[128]
        phash = [255 if v > median else 0 for v in gray]

        hist = [0] * 256
        for y in range(GRID):
            for x in range(GRID):
                r_, g_, b_ = pixels[x, y]
                rn, gn, bn = r_ / 255.0, g_ / 255.0, b_ / 255.0
                mx = max(rn, gn, bn); mn = min(rn, gn, bn); delta = mx - mn
                if delta == 0: hue = 0.0
                elif mx == rn: hue = (60 * ((gn - bn) / delta) + 360) % 360
                elif mx == gn: hue = 60 * ((bn - rn) / delta) + 120
                else: hue = 60 * ((rn - gn) / delta) + 240
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


def distance(a: bytes, b: bytes) -> int:
    """Mirrors Dart distance(): gray ×1 + phash ×2 + hist ×1."""
    d = 0
    for i in range(256):
        d += abs(a[i] - b[i])
    for i in range(256, 512):
        d += 2 * abs(a[i] - b[i])
    for i in range(512, 768):
        d += abs(a[i] - b[i])
    return d


def search(query_sig: bytes, bundle: dict[bytes, bytes],
           url_lookup: dict[bytes, str], top_n: int = 5) -> list[tuple[int, str]]:
    scored = []
    for k, sig in bundle.items():
        scored.append((distance(query_sig, sig), url_lookup.get(k, "?")))
    scored.sort(key=lambda x: x[0])
    return scored[:top_n]


def main() -> int:
    print("Loading catalog and bundle…")
    catalog = load_catalog_entries()
    bundle = load_bundle()
    print(f"  catalog entries with image: {len(catalog)}")
    print(f"  bundle signatures: {len(bundle)}")

    # Group entries by source file (IP / store) so we can pick one per group.
    by_src: dict[str, list[tuple[str, str]]] = {}
    for src, name, url in catalog:
        by_src.setdefault(src, []).append((name, url))
    print(f"  source files: {sorted(by_src.keys())}")

    url_to_name = {url: name for _, name, url in catalog}
    hash_to_url = {url_key(url): url for _, _, url in catalog}

    # One query per source file (random within each group for variety).
    random.seed(20260526)
    queries: list[tuple[str, str]] = []
    for src in sorted(by_src.keys()):
        entries = by_src[src]
        if not entries:
            continue
        # Pick a few from each large group, one from small groups.
        n_pick = 2 if len(entries) >= 20 else 1
        for pick in random.sample(entries, min(n_pick, len(entries))):
            queries.append(pick)

    print(f"\nTesting {len(queries)} query images…\n")

    # Fetch query images in parallel.
    def fetch(url: str) -> tuple[str, bytes | None]:
        try:
            r = requests.get(url, timeout=8)
            if r.status_code == 200 and r.content:
                return url, r.content
        except Exception:
            pass
        return url, None

    fetched: dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for url, content in ex.map(fetch, [u for _, u in queries]):
            if content:
                fetched[url] = content

    # For each query, compute signature, search, print top-5.
    all_top_sets: list[set[str]] = []
    for q_name, q_url in queries:
        content = fetched.get(q_url)
        if not content:
            print(f"[skip] {q_name}  (fetch failed)")
            continue
        sig = signature_for_bytes(content)
        if not sig:
            print(f"[skip] {q_name}  (decode failed)")
            continue
        top = search(sig, bundle, hash_to_url, top_n=5)
        top_names = [url_to_name.get(u, u[:40]) for _, u in top]
        all_top_sets.append(set(top_names))
        print(f"Query: {q_name}")
        for dist, url in top:
            name = url_to_name.get(url, url[:40])
            print(f"   dist={dist:6d}  {name}")
        print()

    # Diversity check: how often do different queries produce overlapping
    # top-5 sets?
    if len(all_top_sets) >= 2:
        print("=" * 60)
        print("Diversity report")
        print("=" * 60)
        overlap_pairs = 0
        total_pairs = 0
        for i in range(len(all_top_sets)):
            for j in range(i + 1, len(all_top_sets)):
                total_pairs += 1
                inter = all_top_sets[i] & all_top_sets[j]
                if inter:
                    overlap_pairs += 1
        print(f"Query pairs with ANY shared top-5 hit: "
              f"{overlap_pairs}/{total_pairs}")
        all_unique = set()
        for s in all_top_sets:
            all_unique |= s
        print(f"Unique items across all top-5 lists: {len(all_unique)} "
              f"(out of theoretical max {5 * len(all_top_sets)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
