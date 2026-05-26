"""
Download DINOv2-small ONNX (pre-exported by Xenova on HuggingFace), copy
it into `assets/`, and use it to compute a 384-dim semantic embedding for
every catalog image URL. Writes the embedding bundle to
`assets/catalog_embeddings.bin`.

Bundle binary format (v3, magic 'DKE2'):
  bytes 0..3   : 'DKE2'                 (magic)
  bytes 4..7   : uint32 version (=2)    (little-endian)
  bytes 8..11  : uint32 dim    (=384)
  bytes 12..15 : uint32 count
  then `count` records of:
    bytes 0..7        : sha256(url)[:8]    (url hash)
    bytes 8..(8+dim*4): float32 embedding  (l2-normalized for fast cosine)

The L2-normalization on disk means runtime similarity is a single dot
product — no per-comparison normalization needed.

Usage:
    pip install onnxruntime pillow requests numpy huggingface_hub
    python tools/build_dinov2_bundle.py
"""
from __future__ import annotations

import hashlib
import re
import struct
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import numpy as np
    import onnxruntime as ort
    import requests
    from PIL import Image
except ImportError as e:
    print(f"Need: pip install onnxruntime pillow requests numpy  ({e})")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "lib" / "data" / "catalog"
ASSETS_DIR = ROOT / "assets"
MODEL_PATH = ASSETS_DIR / "dinov2_small.onnx"
OUT_PATH = ASSETS_DIR / "catalog_embeddings.bin"

MODEL_URL = (
    "https://huggingface.co/Xenova/dinov2-small/resolve/main/onnx/model.onnx"
)

EMBED_DIM = 384  # DINOv2-small CLS dim
INPUT_SIZE = 224
# ImageNet mean/std — DINOv2 normalization
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

IMAGE_URL_RE = re.compile(r"imageUrl\s*:\s*'([^']+)'")


def ensure_model() -> None:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        print(f"✓ Model already at {MODEL_PATH} ({MODEL_PATH.stat().st_size//1024} KB)")
        return
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading DINOv2-small ONNX → {MODEL_PATH}")
    print(f"   from {MODEL_URL}")
    with urllib.request.urlopen(MODEL_URL) as r, MODEL_PATH.open("wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        while True:
            chunk = r.read(1 << 20)  # 1MB
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = 100 * downloaded / total
                print(f"  {downloaded//1024//1024} MB / {total//1024//1024} MB ({pct:.0f}%)", end="\r")
    print()
    print(f"✓ Saved {MODEL_PATH.stat().st_size//1024//1024} MB")


def extract_urls() -> set[str]:
    urls: set[str] = set()
    for dart in CATALOG_DIR.glob("*.dart"):
        if dart.name == "all.dart":
            continue
        text = dart.read_text(encoding="utf-8")
        for m in IMAGE_URL_RE.finditer(text):
            raw = m.group(1).strip().replace("&amp;", "&")
            if raw.startswith("//"):
                raw = "https:" + raw
            if raw.startswith("http"):
                urls.add(raw)
    return urls


def url_hash(url: str) -> bytes:
    return hashlib.sha256(url.encode("utf-8")).digest()[:8]


def preprocess(img: Image.Image) -> np.ndarray:
    """Resize → center-crop → normalize → CHW float32."""
    # Resize shorter side to 256, center-crop 224x224 (standard ViT preproc)
    w, h = img.size
    scale = 256 / min(w, h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - INPUT_SIZE) // 2
    top = (nh - INPUT_SIZE) // 2
    img = img.crop((left, top, left + INPUT_SIZE, top + INPUT_SIZE))
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    arr = (arr - MEAN) / STD            # HWC
    arr = arr.transpose(2, 0, 1)        # CHW
    return np.expand_dims(arr, 0)       # NCHW


_session: ort.InferenceSession | None = None
_input_name: str | None = None
_output_index: int = 0


def get_session() -> tuple[ort.InferenceSession, str, int]:
    global _session, _input_name, _output_index
    if _session is None:
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        _session = ort.InferenceSession(str(MODEL_PATH), sess_options)
        _input_name = _session.get_inputs()[0].name
        outputs = _session.get_outputs()
        print(f"  inputs: {[i.name for i in _session.get_inputs()]}")
        print(f"  outputs: {[(o.name, o.shape) for o in outputs]}")
        # DINOv2 typically returns last_hidden_state [1, 257, 384] and may
        # also have pooler_output [1, 384]. Pick whichever is 2-D.
        _output_index = 0
        for i, o in enumerate(outputs):
            if len(o.shape) == 2 and o.shape[-1] == EMBED_DIM:
                _output_index = i
                break
    return _session, _input_name, _output_index  # type: ignore[return-value]


def embed_image(arr: np.ndarray) -> np.ndarray:
    sess, in_name, out_idx = get_session()
    out = sess.run(None, {in_name: arr})[out_idx]
    if out.ndim == 3:
        out = out[:, 0, :]              # take CLS token
    vec = out[0].astype(np.float32)
    norm = np.linalg.norm(vec) + 1e-9
    return (vec / norm).astype(np.float32)


def fetch_and_embed(url: str) -> tuple[str, np.ndarray | None]:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200 or not r.content:
            return url, None
        img = Image.open(BytesIO(r.content)).convert("RGB")
        arr = preprocess(img)
        emb = embed_image(arr)
        return url, emb
    except Exception:
        return url, None


def main() -> int:
    ensure_model()
    # Warm-load model & print I/O info
    get_session()

    urls = sorted(extract_urls())
    print(f"\nCatalog imageUrls: {len(urls)} unique")

    results: dict[bytes, np.ndarray] = {}
    # ONNX Runtime CPU is fast enough; modest parallelism on fetch only.
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_and_embed, u): u for u in urls}
        done = 0
        for fut in as_completed(futs):
            done += 1
            url, emb = fut.result()
            if emb is not None and emb.shape == (EMBED_DIM,):
                results[url_hash(url)] = emb
            if done % 25 == 0 or done == len(urls):
                print(f"  {done}/{len(urls)} ({len(results)} embedded)")

    print(f"\nWriting bundle → {OUT_PATH}")
    with OUT_PATH.open("wb") as f:
        f.write(b"DKE2")
        f.write(struct.pack("<I", 2))           # version
        f.write(struct.pack("<I", EMBED_DIM))   # dim
        f.write(struct.pack("<I", len(results)))
        for h, emb in results.items():
            f.write(h)
            f.write(emb.tobytes())              # float32 × 384 = 1536 bytes

    size_kb = OUT_PATH.stat().st_size / 1024
    print(
        f"✓ Wrote {len(results)} embeddings, "
        f"{size_kb:.0f} KB total "
        f"({len(results) * EMBED_DIM * 4 // 1024} KB embeddings + 16 B header)"
    )
    print()
    print("Add to pubspec.yaml assets:")
    print("    - assets/dinov2_small.onnx")
    print("    - assets/catalog_embeddings.bin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
