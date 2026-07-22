from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_ACTION_QUEUE = DATA / "source_discovery_action_queue_public.json"
DEFAULT_BOTTLENECKS = DATA / "source_discovery_store_bottlenecks_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_focus_packs_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def counter_pairs(counter: Counter[str], field: str, limit: int = 12) -> list[dict[str, Any]]:
    return [{field: key, "rows": value} for key, value in counter.most_common(limit) if key]


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "manual_review_status": "not_started",
        "manual_confirmed_source_url": "",
        "manual_confirmed_image_url": "",
        "manual_note": "",
        "catalog_index": item.get("catalog_index"),
        "source_store": item.get("source_store"),
        "category": item.get("category"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "official_search_url": item.get("official_search_url"),
        "web_search_url": item.get("web_search_url"),
        "allowed_source_domains": item.get("allowed_source_domains") or [],
        "source_patch_template": item.get("source_patch_template") or {},
        "catalog_field_import_template": item.get("catalog_field_import_template") or {},
        "acceptance_rule": item.get("acceptance_rule"),
        "auto_apply_enabled": False,
    }


def collect_action_items(action_queue: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_store: dict[str, list[dict[str, Any]]] = {}
    for batch in action_queue.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        batch_id = batch.get("batch_id")
        source_store = str(batch.get("source_store") or "unknown")
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["batch_id"] = batch_id
            row["source_store"] = row.get("source_store") or source_store
            by_store.setdefault(source_store, []).append(row)
    for rows in by_store.values():
        category_counts = Counter(str(row.get("category") or "") for row in rows)
        rows.sort(
            key=lambda row: (
                -category_counts[str(row.get("category") or "")],
                str(row.get("category") or ""),
                int(row.get("catalog_index") or 999_999_999),
            )
        )
    return by_store


def top_stores_from_bottlenecks(bottlenecks: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    stores = [store for store in bottlenecks.get("stores") or [] if isinstance(store, dict)]
    stores.sort(key=lambda row: (-int(row.get("rows") or 0), str(row.get("source_store") or "")))
    return stores[:limit]


def build_report(
    action_queue: dict[str, Any],
    bottlenecks: dict[str, Any],
    *,
    generated_at: str | None = None,
    top_store_limit: int = 5,
    pack_size: int = 20,
) -> dict[str, Any]:
    by_store = collect_action_items(action_queue)
    focus_stores = top_stores_from_bottlenecks(bottlenecks, top_store_limit)
    focus_store_names = [str(store.get("source_store") or "") for store in focus_stores]

    packs: list[dict[str, Any]] = []
    work_order: list[dict[str, Any]] = []
    for store in focus_stores:
        source_store = str(store.get("source_store") or "")
        rows = by_store.get(source_store, [])
        for offset in range(0, len(rows), pack_size):
            chunk = rows[offset : offset + pack_size]
            if not chunk:
                continue
            category_counts = Counter(str(item.get("category") or "") for item in chunk)
            domain_counts: Counter[str] = Counter()
            batch_ids: list[str] = []
            for item in chunk:
                if item.get("batch_id") and item.get("batch_id") not in batch_ids:
                    batch_ids.append(str(item.get("batch_id")))
                for domain in item.get("allowed_source_domains") or []:
                    domain_counts[str(domain)] += 1
            pack = {
                "focus_pack_id": f"source-discovery-focus-{len(packs) + 1:03d}",
                "source_store": source_store,
                "pack_sequence": offset // pack_size + 1,
                "row_count": len(chunk),
                "offset": offset,
        "source_store_total_rows": len(rows),
        "source_store_remaining_after_pack": max(len(rows) - offset - len(chunk), 0),
        "review_status": "not_started",
        "confirmed_source_rows": 0,
        "remaining_review_rows": len(chunk),
        "needs_manual_review_rows": len(chunk),
        "blocked_rows": 0,
        "batch_ids": batch_ids,
                "target_category": category_counts.most_common(1)[0][0] if category_counts else None,
                "category_rows": counter_pairs(category_counts, "category"),
                "allowed_source_domains": counter_pairs(domain_counts, "domain"),
                "first_official_search_url": next((item.get("official_search_url") for item in chunk if item.get("official_search_url")), None),
                "recommended_action": "confirm exact source_url values for this focused store/category pack",
                "items": [compact_item(item) for item in chunk],
                "auto_apply_enabled": False,
            }
            packs.append(pack)
            work_order.append(
                {
                    "focus_pack_id": pack["focus_pack_id"],
                    "source_store": source_store,
                    "row_count": len(chunk),
                    "review_status": pack["review_status"],
                    "remaining_review_rows": pack["remaining_review_rows"],
                    "target_category": pack["target_category"],
                    "first_batch_id": batch_ids[0] if batch_ids else None,
                    "first_official_search_url": pack["first_official_search_url"],
                }
            )

    action_summary = action_queue.get("summary") if isinstance(action_queue.get("summary"), dict) else {}
    actionable_source_rows = int(action_summary.get("actionable_source_rows") or 0)
    focus_rows = sum(int(pack.get("row_count") or 0) for pack in packs)

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_focus_packs",
        "summary": {
            "focus_store_count": len(focus_store_names),
            "focus_source_rows": focus_rows,
            "focus_pack_count": len(packs),
            "not_started_focus_pack_count": len(packs),
            "in_progress_focus_pack_count": 0,
            "completed_focus_pack_count": 0,
            "remaining_focus_review_rows": focus_rows,
            "confirmed_focus_source_rows": 0,
            "pack_size": pack_size,
            "actionable_source_rows": actionable_source_rows,
            "focus_coverage": round(focus_rows / actionable_source_rows, 4) if actionable_source_rows else 0,
            "non_focus_source_rows": max(actionable_source_rows - focus_rows, 0),
            "focus_source_stores": focus_store_names,
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use one focus pack at a time to confirm exact product source_url values.",
            "Accepted source_url values must be exact product/detail pages, not search results.",
            "After source_url is confirmed, image_url should still be reviewed before catalog import.",
        ],
        "work_order": work_order,
        "packs": packs,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-queue", type=Path, default=DEFAULT_ACTION_QUEUE)
    parser.add_argument("--bottlenecks", type=Path, default=DEFAULT_BOTTLENECKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-store-limit", type=int, default=5)
    parser.add_argument("--pack-size", type=int, default=20)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(
        load_json(args.action_queue),
        load_json(args.bottlenecks),
        top_store_limit=args.top_store_limit,
        pack_size=args.pack_size,
    )
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
