from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
WORK_QUEUE = DATA / "catalog_missing_image_work_queue_public.json"
REPORT = DATA / "generic_storefront_missing_image_source_public.json"

TARGET_STRATEGY = "source_url_generic_storefront"
TARGET_SAFETY = "blocked_until_exact_product_url"
BLOCKED_UNTIL = "exact_product_source_url_replaces_generic_storefront"
EXCLUDED_SOURCE_STORES = {"Stellive Store"}


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


def queue_items(queue: dict[str, Any]) -> list[dict[str, Any]]:
    items = queue.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_missing_image_work_queue_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def queue_by_index(queue: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in queue_items(queue):
        row_index = item.get("row_index")
        if isinstance(row_index, int):
            result[row_index] = item
    return result


def counter_rows(counter: Counter[str], field: str, limit: int = 40) -> list[dict[str, Any]]:
    return [{field: key, "rows": count} for key, count in counter.most_common(limit)]


def build_search_query(row: dict[str, Any]) -> str:
    parts = [
        row.get("name_ja"),
        row.get("name_en"),
        row.get("name_ko"),
        row.get("affiliation"),
        row.get("category"),
    ]
    return " ".join(str(part).strip() for part in parts if present(part))


def build_item(row: dict[str, Any], queue_row: dict[str, Any]) -> dict[str, Any]:
    catalog_index = row.get("catalog_index")
    return {
        "catalog_index": catalog_index,
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "name_en": row.get("name_en"),
        "source_store": row.get("source_store"),
        "source_url": row.get("source_url"),
        "source_url_is_generic": True,
        "affiliation": row.get("affiliation"),
        "category": row.get("category"),
        "query": queue_row.get("query") or build_search_query(row),
        "strategy": queue_row.get("strategy"),
        "automation_safety": queue_row.get("automation_safety"),
        "manual_review_required": True,
        "source_discovery_template": {
            "catalog_index": catalog_index,
            "exact_source_url": None,
            "image_url": None,
            "evidence_url": None,
            "manual_confirmed": False,
            "blocked_until": BLOCKED_UNTIL,
        },
    }


def build_report(
    catalog: dict[str, Any],
    queue: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    qlookup = queue_by_index(queue)
    rows = []
    for row in catalog_items(catalog):
        catalog_index = row.get("catalog_index")
        queue_row = qlookup.get(catalog_index) if isinstance(catalog_index, int) else None
        if not queue_row:
            continue
        if present(row.get("image_url")):
            continue
        if queue_row.get("strategy") != TARGET_STRATEGY:
            continue
        if queue_row.get("automation_safety") != TARGET_SAFETY:
            continue
        if row.get("source_store") in EXCLUDED_SOURCE_STORES:
            continue
        rows.append(build_item(row, queue_row))

    by_store = Counter(str(row.get("source_store") or "") for row in rows)
    by_category = Counter(str(row.get("category") or "") for row in rows)
    by_affiliation = Counter(str(row.get("affiliation") or "") for row in rows)
    top_source_store, top_source_store_rows = ("", 0)
    if by_store:
        top_source_store, top_source_store_rows = by_store.most_common(1)[0]

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "generic_storefront_missing_image_source",
        "summary": {
            "generic_storefront_rows": len(rows),
            "source_store_count": len(by_store),
            "top_source_store": top_source_store,
            "top_source_store_rows": top_source_store_rows,
            "auto_apply_enabled": False,
        },
        "breakdowns": {
            "by_source_store": counter_rows(by_store, "source_store"),
            "by_category": counter_rows(by_category, "category"),
            "by_affiliation": counter_rows(by_affiliation, "affiliation"),
        },
        "items": rows,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_exact_product_url": True,
            "requires_manual_image_identity_confirmation": True,
            "blocked_until": BLOCKED_UNTIL,
        },
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CATALOG)
    parser.add_argument("--queue", type=Path, default=WORK_QUEUE)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), load_json(args.queue))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
