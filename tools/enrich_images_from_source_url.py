from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from catalog_normalize import is_generic_source_url
from image_enrichment_safety import (
    is_product_specific_source_url,
    is_safe_source_image_pair,
    looks_like_generic_image_url,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "source_url_image_enrichment_report.json"
DEFAULT_STALE_QUEUE = ROOT / "server" / "stale_source_cleanup_queue.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
OG_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
HTML_IMAGE_RE = re.compile(
    r'<(?:meta|link)[^>]+(?:itemprop=["\']image["\']|rel=["\']image_src["\'])[^>]+(?:content|href)=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _absolute_image_url(image_url: str, page_url: str) -> str | None:
    normalized = html.unescape(str(image_url or "").strip())
    if not normalized:
        return None
    if normalized.startswith("//"):
        normalized = "https:" + normalized
    if normalized.startswith("/"):
        normalized = urllib.parse.urljoin(page_url, normalized)
    return normalized if normalized.startswith(("http://", "https://")) else None


def _json_ld_images(value: Any) -> list[str]:
    images: list[str] = []
    if isinstance(value, dict):
        raw_type = value.get("@type")
        types = raw_type if isinstance(raw_type, list) else [raw_type]
        if any(str(item).lower() == "product" for item in types):
            image_value = value.get("image")
            if isinstance(image_value, str):
                images.append(image_value)
            elif isinstance(image_value, list):
                for item in image_value:
                    if isinstance(item, str):
                        images.append(item)
                    elif isinstance(item, dict) and isinstance(item.get("url"), str):
                        images.append(str(item["url"]))
            elif isinstance(image_value, dict) and isinstance(image_value.get("url"), str):
                images.append(str(image_value["url"]))
        for nested_key in ("@graph", "mainEntity", "offers", "itemListElement"):
            images.extend(_json_ld_images(value.get(nested_key)))
    elif isinstance(value, list):
        for item in value:
            images.extend(_json_ld_images(item))
    return images


def _image_from_json_ld(text: str, page_url: str) -> str | None:
    for match in JSON_LD_RE.finditer(text):
        raw = html.unescape(match.group(1)).strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for image_url in _json_ld_images(payload):
            absolute = _absolute_image_url(image_url, page_url)
            if absolute:
                return absolute
    return None


def _safe_image_for_source(url: str, image_url: str | None, allow_non_product_source: bool = False) -> str | None:
    if is_safe_source_image_pair(url, image_url):
        return image_url
    if allow_non_product_source and image_url and not looks_like_generic_image_url(image_url):
        return image_url
    return None


def fetch_image(url: str, allow_non_product_source: bool = False) -> str | None:
    if not is_product_specific_source_url(url) and not allow_non_product_source:
        return None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=15) as response:
            text = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return None
    match = OG_IMAGE_RE.search(text)
    if match:
        image_url = _absolute_image_url(match.group(1), url)
        return _safe_image_for_source(url, image_url, allow_non_product_source)
    match = HTML_IMAGE_RE.search(text)
    if match:
        image_url = _absolute_image_url(match.group(1), url)
        return _safe_image_for_source(url, image_url, allow_non_product_source)
    image_url = _image_from_json_ld(text, url)
    return _safe_image_for_source(url, image_url, allow_non_product_source)


def load_catalog(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        rows = payload.get("items")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)], payload
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], None
    raise SystemExit(f"{path} must contain a JSON list or catalog object with items")


def write_catalog(path: Path, rows: list[dict[str, Any]], wrapper: dict[str, Any] | None) -> None:
    if wrapper is not None:
        wrapper["items"] = rows
        payload: Any = wrapper
    else:
        payload = rows
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--stale-queue", type=Path, default=DEFAULT_STALE_QUEUE)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--allow-non-product-source", action="store_true")
    args = parser.parse_args()

    rows, wrapper = load_catalog(args.input)

    stale_indexes: set[int] = set()
    if args.stale_queue.exists():
        stale_payload = json.loads(args.stale_queue.read_text(encoding="utf-8-sig"))
        for item in (stale_payload.get("items") if isinstance(stale_payload, dict) else []) or []:
            try:
                stale_indexes.add(int(item.get("row_index")))
            except (AttributeError, TypeError, ValueError):
                pass

    candidates = [
        row for index, row in enumerate(rows)
        if isinstance(row, dict)
        and index not in stale_indexes
        and not row.get("image_url")
        and row.get("source_url")
        and (
            is_product_specific_source_url(row.get("source_url"))
            or (args.allow_non_product_source and not is_generic_source_url(row.get("source_url")))
        )
    ]
    if args.max_rows is not None:
        candidates = candidates[: args.max_rows]

    changes: list[dict[str, Any]] = []
    attempted: list[dict[str, Any]] = []
    for row in candidates:
        image_url = fetch_image(str(row["source_url"]), allow_non_product_source=args.allow_non_product_source)
        if not image_url:
            attempted.append(
                {
                    "name_ko": row.get("name_ko"),
                    "catalog_index": row.get("catalog_index"),
                    "source_store": row.get("source_store"),
                    "source_url": row.get("source_url"),
                    "status": "no_safe_image_found",
                }
            )
            continue
        row["image_url"] = image_url
        change = {
            "name_ko": row.get("name_ko"),
            "catalog_index": row.get("catalog_index"),
            "source_store": row.get("source_store"),
            "source_url": row.get("source_url"),
            "image_url": image_url,
            "status": "filled",
        }
        changes.append(change)
        attempted.append(change)
        time.sleep(0.2)

    args.report.write_text(
        json.dumps(
            {
                "candidates": len(candidates),
                "filled": len(changes),
                "unfilled": len(candidates) - len(changes),
                "stale_excluded": len(stale_indexes),
                "changes": changes,
                "attempted": attempted,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if args.write and changes:
        write_catalog(args.input, rows, wrapper)
    print(json.dumps({"candidates": len(candidates), "filled": len(changes), "report": str(args.report), "write": args.write}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to update the seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
