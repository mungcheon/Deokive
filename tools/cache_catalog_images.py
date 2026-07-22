from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.request
from urllib.parse import urlparse
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_CACHE_DIR = ROOT / "assets" / "catalog_images"
DEFAULT_REPORT = ROOT / "data" / "catalog_image_cache_report_public.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
ASSET_PREFIX = "assets/catalog_images"
REFERER_BY_HOST = {
    "www.kotobukiya.co.jp": "https://www.kotobukiya.co.jp/",
    "kotobukiya.co.jp": "https://www.kotobukiya.co.jp/",
    "bsp-prize.jp": "https://bsp-prize.jp/",
    "one-piece.com": "https://one-piece.com/",
    "tc-animate.techorus-cdn.com": "https://www.animate-onlineshop.jp/",
    "www.bandai.co.jp": "https://www.bandai.co.jp/",
}
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def _normalize_url(value: object) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("&amp;", "&")
    if not text:
        return None
    if text.startswith("//"):
        text = f"https:{text}"
    return text


def _deterministic_image_name(url: str) -> str:
    clean = _normalize_url(url) or url
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:20]
    suffix = clean.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    if suffix not in {"jpg", "jpeg", "png", "webp", "gif"}:
        suffix = "jpg"
    suffix = re.sub(r"[^a-z0-9]", "", suffix) or "jpg"
    return f"{digest}.{suffix}"


def _load_catalog(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{path} must contain a JSON list or catalog object with items")
    return payload, rows


def _write_catalog(path: Path, payload: Any, rows: list[dict[str, Any]]) -> None:
    if isinstance(payload, dict):
        payload["items"] = rows
        meta = payload.get("meta")
        if isinstance(meta, dict):
            fields = list(meta.get("fields") or [])
            if "local_image_path" not in fields:
                fields.append("local_image_path")
            meta["fields"] = fields
            missing = dict(meta.get("missing") or {})
            missing["local_image_path"] = sum(
                1 for row in rows if not isinstance(row, dict) or not row.get("local_image_path")
            )
            meta["missing"] = missing
            meta["row_count"] = len(rows)
            meta["total_items"] = len(rows)
        output = payload
    else:
        output = rows
    path.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _cache_name(url: str) -> str:
    return f"{Path(_deterministic_image_name(url)).stem}.webp"


def _optimize_image_bytes(
    image_bytes: bytes,
    target: Path,
    max_size: int,
    quality: int,
) -> tuple[bool, str | None]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, format="WEBP", quality=quality, method=6)
        return True, None
    except Exception as error:
        return False, str(error)


def _download_image(
    url: str,
    target: Path,
    max_size: int,
    quality: int,
) -> tuple[bool, str | None]:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8,ko;q=0.7",
        }
        referer = REFERER_BY_HOST.get(host)
        if referer:
            headers["Referer"] = referer
        request = urllib.request.Request(url, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except Exception as error:
            if "CERTIFICATE_VERIFY_FAILED" not in str(error):
                raise
            response = urllib.request.urlopen(
                request,
                timeout=30,
                context=ssl._create_unverified_context(),
            )
        with response:
            content_type = response.headers.get_content_type()
            image_like_url = parsed.path.lower().endswith(IMAGE_SUFFIXES)
            if not content_type.startswith("image/") and not image_like_url:
                return False, f"not_image:{content_type}"
            return _optimize_image_bytes(response.read(), target, max_size, quality)
    except Exception as error:
        return False, str(error)


def cache_images(
    rows: list[dict[str, Any]],
    cache_dir: Path,
    max_rows: int | None,
    dry_run: bool,
    delay_seconds: float,
    max_size: int,
    quality: int,
) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    checked = 0
    downloaded = 0
    already_cached = 0
    assigned_existing = 0
    skipped_no_url = 0
    failed = 0
    failures: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        if max_rows is not None and checked >= max_rows:
            break
        if not isinstance(row, dict):
            continue

        raw_url = row.get("image_url")
        if not raw_url:
            skipped_no_url += 1
            continue
        checked += 1

        image_url = _normalize_url(raw_url) or ""
        if not image_url.startswith(("http://", "https://")):
            failures.append(
                {
                    "index": index,
                    "name_ko": row.get("name_ko"),
                    "image_url": raw_url,
                    "error": "unsupported_url",
                }
            )
            failed += 1
            continue

        file_name = _cache_name(image_url)
        target = cache_dir / file_name
        legacy_target = cache_dir / _deterministic_image_name(image_url)
        asset_path = f"{ASSET_PREFIX}/{file_name}"

        if target.exists():
            if row.get("local_image_path") != asset_path:
                row["local_image_path"] = asset_path
                assigned_existing += 1
            else:
                already_cached += 1
            continue

        if legacy_target.exists():
            ok, error = _optimize_image_bytes(
                legacy_target.read_bytes(),
                target,
                max_size,
                quality,
            )
            if ok:
                row["local_image_path"] = asset_path
                assigned_existing += 1
                if legacy_target != target:
                    legacy_target.unlink(missing_ok=True)
                continue
            legacy_target.unlink(missing_ok=True)
            failures.append(
                {
                    "index": index,
                    "name_ko": row.get("name_ko"),
                    "source_store": row.get("source_store"),
                    "image_url": raw_url,
                    "error": f"legacy_optimize_failed:{error}",
                }
            )

        if dry_run:
            downloaded += 1
            row["local_image_path"] = asset_path
            continue

        ok, error = _download_image(image_url, target, max_size, quality)
        if ok:
            row["local_image_path"] = asset_path
            downloaded += 1
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        else:
            failed += 1
            failures.append(
                {
                    "index": index,
                    "name_ko": row.get("name_ko"),
                    "source_store": row.get("source_store"),
                    "image_url": raw_url,
                    "error": error,
                }
            )

    return {
        "total_rows": len(rows),
        "checked_with_image_url": checked,
        "downloaded": downloaded,
        "already_cached": already_cached,
        "assigned_existing": assigned_existing,
        "skipped_no_image_url": skipped_no_url,
        "failed": failed,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--delay-seconds", type=float, default=0.02)
    parser.add_argument("--max-size", type=int, default=640)
    parser.add_argument("--quality", type=int, default=78)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    payload, rows = _load_catalog(args.input)
    result = cache_images(
        rows,
        args.cache_dir,
        args.max_rows,
        dry_run=not args.write,
        delay_seconds=args.delay_seconds,
        max_size=args.max_size,
        quality=args.quality,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.write:
        _write_catalog(args.input, payload, rows)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        print("Dry run only. Re-run with --write to download images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
