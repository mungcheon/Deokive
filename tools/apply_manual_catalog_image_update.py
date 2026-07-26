from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PIL import Image, ImageOps

try:
    from generate_seed_catalog_dart import generate
except ModuleNotFoundError:
    from tools.generate_seed_catalog_dart import generate

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_SEED_OUTPUT = ROOT / "lib" / "data" / "catalog" / "seed_catalog.dart"
APP_ASSET_DIR = ROOT / "assets" / "catalog_images"
WEB_ASSET_DIR = ROOT / "assets" / "assets" / "catalog_images"
ASSET_PREFIX = "assets/catalog_images"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
REFERER_BY_HOST = {
    "assets.1kuji.com": "https://1kuji.com/",
    "bsp-prize.jp": "https://bsp-prize.jp/",
    "chiikawamarket.jp": "https://chiikawamarket.jp/",
    "images.goodsmile.info": "https://www.goodsmile.info/",
    "images-goodsmile-info.s3-ap-northeast-1.amazonaws.com": "https://www.goodsmile.com/",
    "shop.kotobukiya.co.jp": "https://shop.kotobukiya.co.jp/",
    "tc-animate.techorus-cdn.com": "https://www.animate-onlineshop.jp/",
    "www.bandai.co.jp": "https://www.bandai.co.jp/",
    "www.movic.jp": "https://www.movic.jp/",
}


def _normalize_url(value: str) -> str:
    url = value.strip().replace("&amp;", "&")
    if url.startswith("//"):
        url = f"https:{url}"
    if not url.startswith(("http://", "https://")):
        raise SystemExit(f"Unsupported image URL: {value}")
    return url


def _cache_name(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return f"{digest}.webp"


def _download(url: str) -> bytes:
    parsed = urlparse(url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8,ko;q=0.7",
    }
    referer = REFERER_BY_HOST.get(parsed.netloc.lower())
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                raise SystemExit(f"URL did not return an image: {content_type}")
            return response.read()
    except Exception as error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(error):
            raise
        with urllib.request.urlopen(
            request,
            timeout=30,
            context=ssl._create_unverified_context(),
        ) as response:
            return response.read()


def _write_webp(image_bytes: bytes, targets: list[Path], max_size: int, quality: int) -> None:
    with Image.open(BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        for target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, format="WEBP", quality=quality, method=6)


def _replace_one_line_json_object(text: str, catalog_index: int, updates: dict[str, Any]) -> str:
    pattern = re.compile(rf'\{{"catalog_index":{catalog_index},[^{{}}]*\}}')
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"catalog_index {catalog_index} was not found")
    row = json.loads(match.group(0))
    before = dict(row)
    row.update({key: value for key, value in updates.items() if value is not None})
    if before == row:
        return text
    encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    return text[: match.start()] + encoded + text[match.end() :]


def _sync_flutter_seed(catalog: Path, output: Path) -> None:
    payload = json.loads(catalog.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{catalog} must contain a JSON list or an object with items")
    try:
        source_label = catalog.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        source_label = catalog.resolve().as_posix()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        generate([row for row in rows if isinstance(row, dict)], source_label=source_label),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update one public catalog image and cache it locally."
    )
    parser.add_argument("catalog_index", type=int)
    parser.add_argument("image_url")
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--source-store", default=None)
    parser.add_argument("--name-ko", default=None)
    parser.add_argument("--name-ja", default=None)
    parser.add_argument("--character-name", default=None)
    parser.add_argument(
        "--expect-name",
        default=None,
        help="Abort if the current Korean/Japanese/English name does not contain this text.",
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--seed-output", type=Path, default=DEFAULT_SEED_OUTPUT)
    parser.add_argument(
        "--skip-seed-sync",
        action="store_true",
        help="Do not regenerate Flutter's bundled public catalog seed after --write.",
    )
    parser.add_argument("--max-size", type=int, default=900)
    parser.add_argument("--quality", type=int, default=84)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    image_url = _normalize_url(args.image_url)
    file_name = _cache_name(image_url)
    local_path = f"{ASSET_PREFIX}/{file_name}"
    targets = [APP_ASSET_DIR / file_name, WEB_ASSET_DIR / file_name]

    image_bytes = _download(image_url)
    if args.write:
        _write_webp(image_bytes, targets, args.max_size, args.quality)

    updates = {
        "image_url": image_url,
        "local_image_path": local_path,
        "source_url": args.source_url.strip() if args.source_url else None,
        "source_store": args.source_store.strip() if args.source_store else None,
        "name_ko": args.name_ko.strip() if args.name_ko else None,
        "name_ja": args.name_ja.strip() if args.name_ja else None,
        "character_name": args.character_name.strip() if args.character_name else None,
    }
    text = args.catalog.read_text(encoding="utf-8")
    if args.expect_name:
        match = re.search(rf'\{{"catalog_index":{args.catalog_index},[^{{}}]*\}}', text)
        if not match:
            raise SystemExit(f"catalog_index {args.catalog_index} was not found")
        current_row = json.loads(match.group(0))
        current_name = " ".join(
            str(current_row.get(key) or "")
            for key in ("name_ko", "name_ja", "name_en")
        )
        if args.expect_name not in current_name:
            raise SystemExit(
                f"catalog_index {args.catalog_index} name mismatch: "
                f"expected to contain {args.expect_name!r}, got {current_name!r}"
            )
    updated_text = _replace_one_line_json_object(text, args.catalog_index, updates)
    if args.write:
        args.catalog.write_text(updated_text, encoding="utf-8")
        if not args.skip_seed_sync:
            _sync_flutter_seed(args.catalog, args.seed_output)

    print(
        json.dumps(
            {
                "catalog_index": args.catalog_index,
                "image_url": image_url,
                "local_image_path": local_path,
                "asset_files": [str(target.relative_to(ROOT)) for target in targets],
                "source_url": updates["source_url"],
                "source_store": updates["source_store"],
                "character_name": updates["character_name"],
                "flutter_seed_synced": bool(args.write and not args.skip_seed_sync),
                "seed_output": str(args.seed_output.relative_to(ROOT))
                if args.seed_output.is_relative_to(ROOT)
                else str(args.seed_output),
                "write": args.write,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.write:
        print("Dry run only. Re-run with --write to update files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
