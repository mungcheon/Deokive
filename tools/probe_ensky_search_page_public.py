from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import enrich_ensky_from_sitemap_cache as ensky
from enrich_catalog_images import ENSKY_STORE, EnskySitemapProvider, ProductImage


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
REPORT = DATA / "ensky_search_page_probe_public.json"


class EnskySearchProvider(Protocol):
    def search_images(self, query: str) -> list[ProductImage]:
        ...

    def match(self, query: str) -> ProductImage | None:
        ...


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def catalog_items(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def missing_ensky_rows(items: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for fallback_index, item in enumerate(items):
        if item.get("source_store") != ensky.ENSKY_STORE:
            continue
        if present(item.get("image_url")):
            continue
        rows.append((fallback_index, item))
    return rows


def query_text(row: dict[str, Any]) -> str:
    return str(row.get("name_ja") or row.get("name_ko") or "").strip()


def product_payload(product: ProductImage) -> dict[str, Any]:
    return {
        "title": product.title,
        "source_url": product.source_url,
        "image_url": product.image_url,
    }


def build_probe_report(
    catalog: dict[str, Any],
    provider: EnskySearchProvider,
    *,
    limit: int = 30,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows = missing_ensky_rows(catalog_items(catalog))
    selected = rows[: max(0, limit)]
    items: list[dict[str, Any]] = []
    safe_match_rows = 0
    rejected_result_rows = 0
    no_result_rows = 0

    for fallback_index, row in selected:
        query = query_text(row)
        if not query:
            continue
        results = provider.search_images(query)
        match = provider.match(query)
        if match is not None:
            status = "safe_match"
            safe_match_rows += 1
        elif results:
            status = "rejected_search_results"
            rejected_result_rows += 1
        else:
            status = "no_search_results"
            no_result_rows += 1
        items.append(
            {
                "catalog_index": ensky.row_identifier(row, fallback_index),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "affiliation": row.get("affiliation"),
                "category": row.get("category"),
                "query": query,
                "status": status,
                "search_result_count": len(results),
                "safe_match": None if match is None else product_payload(match),
                "top_search_results": [product_payload(product) for product in results[:5]],
                "manual_review_required": True,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "ensky_search_page_probe",
        "summary": {
            "missing_ensky_image_rows": len(rows),
            "processed_rows": len(items),
            "limit": limit,
            "safe_match_rows": safe_match_rows,
            "rejected_search_result_rows": rejected_result_rows,
            "no_search_result_rows": no_result_rows,
            "auto_apply_enabled": False,
            "search_page": "https://www.enskyshop.com/products/list?name={query}",
        },
        "items": items,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_human_review_before_image_attachment": True,
        },
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    provider = EnskySitemapProvider(
        store_name=ENSKY_STORE,
        sitemap_url="https://www.enskyshop.com/sitemap.xml",
        allow_sitemap_fallback=False,
    )
    report = build_probe_report(load_json(args.input), provider, limit=args.limit)
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
