from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "data" / "chiikawa_market_name_ja_enrichment_public.json"
DEFAULT_CACHE = ROOT / "server" / ".catalog_image_cache" / "chiikawa_market_products_ja.json"

PRODUCTS_URL = "https://chiikawamarket.jp/products.json?limit=250&page={page}"
CHIIKAWA_MARKET = "치이카와 마켓"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path} must contain a catalog object with items")
    return payload


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def fetch_products(cache_path: Path | None = DEFAULT_CACHE) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    page = 1
    while True:
        request = urllib.request.Request(PRODUCTS_URL.format(page=page), headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            cached = load_cached_products(cache_path)
            if cached:
                return cached
            raise
        page_products = payload.get("products") or []
        if not page_products:
            break
        products.extend(item for item in page_products if isinstance(item, dict))
        page += 1
        time.sleep(0.05)
    save_cached_products(cache_path, products)
    return products


def load_cached_products(cache_path: Path | None) -> list[dict[str, Any]]:
    if cache_path is None or not cache_path.exists():
        return []
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []
    products = payload.get("products") if isinstance(payload, dict) else payload
    if not isinstance(products, list):
        return []
    return [item for item in products if isinstance(item, dict)]


def save_cached_products(cache_path: Path | None, products: list[dict[str, Any]]) -> None:
    if cache_path is None or not products:
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(cache_path, {"products": products, "count": len(products)})


def numeric_identity(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def source_handle(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    path = urllib.parse.urlsplit(text).path.rstrip("/")
    return numeric_identity(path.rsplit("/", 1)[-1])


def image_barcode(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"/files/(\d{8,14})(?:[_./?#-]|$)", text)
    return match.group(1) if match else ""


def product_identity(product: dict[str, Any]) -> str:
    variant = (product.get("variants") or [{}])[0] or {}
    for value in (variant.get("barcode"), variant.get("sku"), product.get("handle")):
        ident = numeric_identity(value)
        if ident:
            return ident
    return ""


def build_title_by_identity(products: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for product in products:
        ident = product_identity(product)
        title = str(product.get("title") or "").strip()
        if ident and title:
            out[ident] = title
    return out


def row_identity(row: dict[str, Any]) -> str:
    for value in (row.get("barcode"), source_handle(row.get("source_url")), image_barcode(row.get("image_url"))):
        ident = numeric_identity(value)
        if ident:
            return ident
    return ""


def enrich_catalog(catalog: dict[str, Any], products: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    items = [item for item in catalog.get("items", []) if isinstance(item, dict)]
    title_by_identity = build_title_by_identity(products)
    updated_items: list[dict[str, Any]] = []
    unmatched_samples: list[dict[str, Any]] = []
    changed_samples: list[dict[str, Any]] = []
    market_missing_before = 0
    matched_rows = 0
    updated_rows = 0

    for item in items:
        if item.get("source_store") != CHIIKAWA_MARKET or item.get("name_ja"):
            continue
        market_missing_before += 1
        ident = row_identity(item)
        title = title_by_identity.get(ident)
        if not title:
            if len(unmatched_samples) < 40:
                unmatched_samples.append(
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "barcode": item.get("barcode"),
                        "source_url": item.get("source_url"),
                        "image_url": item.get("image_url"),
                    }
                )
            continue
        matched_rows += 1
        item["name_ja"] = title
        updated_rows += 1
        updated_items.append(item)
        if len(changed_samples) < 40:
            changed_samples.append(
                {
                    "catalog_index": item.get("catalog_index"),
                    "name_ko": item.get("name_ko"),
                    "name_ja": title,
                    "identity": ident,
                    "source_url": item.get("source_url"),
                }
            )

    catalog.setdefault("meta", {})
    if isinstance(catalog["meta"], dict):
        catalog["meta"]["generated_at"] = generated_at
        missing = catalog["meta"].setdefault("missing", {})
        if isinstance(missing, dict):
            missing["name_ja"] = sum(1 for item in items if not item.get("name_ja"))

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "chiikawa_market_name_ja_enrichment",
        "summary": {
            "product_rows": len(products),
            "product_identity_rows": len(title_by_identity),
            "market_missing_name_ja_before": market_missing_before,
            "matched_rows": matched_rows,
            "updated_rows": updated_rows,
            "market_missing_name_ja_after": sum(
                1 for item in items if item.get("source_store") == CHIIKAWA_MARKET and not item.get("name_ja")
            ),
            "catalog_missing_name_ja_after": sum(1 for item in items if not item.get("name_ja")),
            "auto_apply_enabled": True,
            "evidence_source": PRODUCTS_URL.format(page=1),
            "match_policy": "barcode_or_product_handle_exact_numeric_identity",
        },
        "changed_samples": changed_samples,
        "unmatched_samples": unmatched_samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    generated_at = now_utc()
    catalog = load_catalog(args.input)
    products = fetch_products(args.cache)
    report = enrich_catalog(catalog, products, generated_at)
    if args.write:
        write_json(args.output, catalog, compact=True)
        write_json(args.report, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
