from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_image_source_url_confirmed_template_public.json"
DEFAULT_OUTPUT = DATA / "catalog_provider_missing_source_url_queue_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(_compact_text(row.get(key)) for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _manual_import_template(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_index": row.get("row_index"),
        "catalog_index": row.get("catalog_index"),
        "field": "source_url",
        "manual_confirmed": False,
        "manual_value": "",
        "evidence_url": "",
        "current_source_url": row.get("current_source_url"),
        "manual_note": "",
    }


def _queue_item(row: dict[str, Any]) -> dict[str, Any]:
    hints = row.get("store_search_hints")
    hints = hints if isinstance(hints, dict) else {}
    return {
        "row_index": row.get("row_index"),
        "catalog_index": row.get("catalog_index"),
        "source_store": row.get("source_store"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "series_name": row.get("series_name"),
        "category": row.get("category"),
        "current_source_url": row.get("current_source_url"),
        "storefront_url": hints.get("storefront_url") or "",
        "store_search_url": hints.get("store_search_url") or "",
        "site_query": hints.get("site_query") or "",
        "fallback_search_queries": row.get("fallback_search_queries") or [],
        "source_url_import_template": _manual_import_template(row),
        "review_blockers": row.get("source_url_review_blockers") or [],
        "manual_confirmation_requirements": row.get("manual_confirmation_requirements") or [],
        "next_after_confirmed_source_url": row.get("next_after_confirmed_source_url")
        or "extract_or_confirm_product_page_image_url",
        "batch_id": row.get("batch_id"),
        "auto_apply_enabled": False,
    }


def _build_workstreams(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_store: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_store.setdefault(_compact_text(item.get("source_store")) or "unknown", []).append(item)

    workstreams: list[dict[str, Any]] = []
    for source_store, rows in by_store.items():
        first_hint = rows[0] if rows else {}
        workstreams.append(
            {
                "source_store": source_store,
                "row_count": len(rows),
                "storefront_url": first_hint.get("storefront_url") or "",
                "site_query": first_hint.get("site_query") or "",
                "store_search_url_count": sum(1 for row in rows if row.get("store_search_url")),
                "category_rows": _counter_pairs(rows, "category"),
                "rows": rows,
                "recommended_review_order": [
                    "Open store_search_url first when it is available.",
                    "If store search fails, use fallback_search_queries with site_query.",
                    "Confirm the exact product detail page, not a storefront, search page, or collection page.",
                    "Copy the verified official/detail URL into source_url_import_template.manual_value.",
                    "Set manual_confirmed=true only after title, product type, variant, and release context match.",
                ],
                "next_machine_step_after_review": "import_confirmed_source_urls_then_extract_images",
                "auto_apply_enabled": False,
            }
        )

    workstreams.sort(key=lambda row: (-int(row["row_count"]), str(row["source_store"])))
    return workstreams


def _review_readiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_with_search_url = [row for row in rows if row.get("store_search_url")]
    rows_with_site_query = [row for row in rows if row.get("site_query")]
    next_row = rows_with_search_url[0] if rows_with_search_url else (rows[0] if rows else {})
    return {
        "status": "provider_or_manual_refresh_required" if rows else "empty",
        "auto_apply_ready_rows": 0,
        "manual_review_rows": len(rows),
        "rows_with_store_search_url": len(rows_with_search_url),
        "rows_with_site_query": len(rows_with_site_query),
        "rows_without_search_hint": max(0, len(rows) - len(rows_with_search_url)),
        "next_review_row": {
            "catalog_index": next_row.get("catalog_index"),
            "name_ko": next_row.get("name_ko"),
            "source_store": next_row.get("source_store"),
            "category": next_row.get("category"),
            "store_search_url": next_row.get("store_search_url"),
            "site_query": next_row.get("site_query"),
            "fallback_search_queries": (next_row.get("fallback_search_queries") or [])[:3],
        }
        if next_row
        else {},
        "blocked_reason": "no_candidate_provider_result" if rows else None,
        "blocked_until": "provider_refreshed_or_manual_exact_source_url_found" if rows else None,
        "required_evidence": [
            "official_or_trusted_product_detail_source_url",
            "provider_result_rechecked_or_manual_source_found",
            "not_storefront_search_or_collection_url",
        ],
        "next_machine_step_after_review": "import_confirmed_source_urls_then_extract_images",
        "auto_apply_enabled": False,
    }


def build_queue(template: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    rows = [
        _queue_item(row)
        for row in template.get("items") or []
        if isinstance(row, dict) and row.get("source_url_review_lane") == "candidate_provider_missing"
    ]
    rows.sort(key=lambda row: (str(row.get("source_store") or ""), int(row.get("catalog_index") or 0)))
    workstreams = _build_workstreams(rows)
    by_store = Counter(str(row.get("source_store") or "") for row in rows)
    by_store.pop("", None)

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_provider_missing_source_url_queue",
        "summary": {
            "provider_missing_rows": len(rows),
            "workstream_count": len(workstreams),
            "by_source_store": [[key, value] for key, value in by_store.most_common()],
            "by_category": _counter_pairs(rows, "category"),
            "with_store_search_url": sum(1 for row in rows if row.get("store_search_url")),
            "with_site_query": sum(1 for row in rows if row.get("site_query")),
            "auto_apply_enabled": False,
        },
        "review_readiness": _review_readiness(rows),
        "instructions": [
            "This queue covers rows where no store-specific candidate provider result exists.",
            "Search hints are not evidence and must not be imported directly.",
            "Use only official product/detail pages as confirmed source_url evidence.",
            "After manual source URLs are confirmed, dry-run tools/import_confirmed_catalog_field_rows.py.",
            "Then rebuild the image attachment queue to extract or confirm image_url.",
        ],
        "workstreams": workstreams,
        "items": rows,
        "automation_policy": {
            "auto_apply_source_url": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_catalog_field_rows.py",
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_queue(load_json(args.input))
    if args.write:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
