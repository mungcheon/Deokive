from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import enrich_ensky_from_sitemap_cache as ensky
from enrich_catalog_images import _distinctive_query_tokens, _squash


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
CACHE = ROOT / "server" / ".catalog_image_cache" / "ensky_sitemap_index.json"
REPORT = DATA / "ensky_missing_image_cache_coverage_public.json"


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


def usable_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        product
        for product in products
        if isinstance(product, dict)
        and present(product.get("title"))
        and present(product.get("image_url"))
        and present(product.get("source_url"))
    ]


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


def query_tokens(row: dict[str, Any]) -> list[str]:
    query = query_text(row)
    tokens = [_squash(token) for token in _distinctive_query_tokens(query)]
    common = {_squash(token) for token in ensky.COMMON_TOKENS}
    return [token for token in tokens if token and token not in common]


def broad_candidate_score(
    *,
    title_key: str,
    tokens: list[str],
    affiliation: str,
    category: str,
) -> tuple[int, list[str]]:
    matched_tokens = [token for token in tokens if token in title_key]
    score = len(matched_tokens) * 10

    if affiliation and affiliation in title_key:
        score += 8
        matched_tokens.append(affiliation)

    if category and category in title_key:
        score += 4
        matched_tokens.append(category)

    return score, sorted(set(matched_tokens))


def candidate_products(row: dict[str, Any], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query = query_text(row)
    tokens = query_tokens(row)
    affiliation = _squash(str(row.get("affiliation") or ""))
    category = _squash(str(row.get("category") or ""))
    candidates: list[dict[str, Any]] = []
    for product in products:
        title = str(product.get("title") or "")
        title_key = _squash(title)
        safe = ensky._safe_match(query, title)
        score, matched_tokens = broad_candidate_score(
            title_key=title_key,
            tokens=tokens,
            affiliation=affiliation,
            category=category,
        )
        if not safe and score < 20:
            continue
        candidates.append(
            {
                "title": product.get("title"),
                "source_url": product.get("source_url"),
                "image_url": product.get("image_url"),
                "safe_exact_match": safe,
                "score": 999 if safe else score,
                "matched_tokens": matched_tokens,
            }
        )
    candidates.sort(key=lambda item: (-int(item["safe_exact_match"]), -int(item["score"]), str(item["title"])))
    return candidates


def build_report(
    catalog: dict[str, Any],
    products: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    items = catalog_items(catalog)
    cache_products = usable_products(products)
    rows = missing_ensky_rows(items)

    by_affiliation: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    report_items: list[dict[str, Any]] = []

    exact_safe_match_rows = 0
    broad_candidate_rows = 0
    no_candidate_rows = 0

    for fallback_index, row in rows:
        by_affiliation[str(row.get("affiliation") or "unknown")] += 1
        by_category[str(row.get("category") or "unknown")] += 1

        candidates = candidate_products(row, cache_products)
        exact_candidates = [candidate for candidate in candidates if candidate["safe_exact_match"]]
        if exact_candidates:
            status = "exact_safe_match"
            exact_safe_match_rows += 1
        elif candidates:
            status = "broad_cache_candidate"
            broad_candidate_rows += 1
        else:
            status = "no_cache_candidate"
            no_candidate_rows += 1
        by_status[status] += 1

        report_items.append(
            {
                "catalog_index": ensky.row_identifier(row, fallback_index),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_store": row.get("source_store"),
                "affiliation": row.get("affiliation"),
                "category": row.get("category"),
                "status": status,
                "candidate_count": len(candidates),
                "top_candidates": candidates[:5],
                "manual_review_required": True,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "ensky_missing_image_cache_coverage",
        "summary": {
            "missing_ensky_image_rows": len(rows),
            "cache_products": len(cache_products),
            "exact_safe_match_rows": exact_safe_match_rows,
            "broad_cache_candidate_rows": broad_candidate_rows,
            "no_cache_candidate_rows": no_candidate_rows,
            "manual_review_rows": len(rows),
            "auto_apply_enabled": False,
            "cache_source": "server/.catalog_image_cache/ensky_sitemap_index.json",
        },
        "breakdowns": {
            "by_affiliation": [{"affiliation": key, "rows": value} for key, value in by_affiliation.most_common()],
            "by_category": [{"category": key, "rows": value} for key, value in by_category.most_common()],
            "by_status": [{"status": key, "rows": value} for key, value in by_status.most_common()],
        },
        "items": sorted(report_items, key=lambda item: int(item.get("catalog_index") or 0)),
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_human_review_before_image_attachment": True,
        },
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CATALOG)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), load_json(args.cache))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
