from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_action_queue_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_store_bottlenecks_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def counter_rows(counter: Counter[str], field: str, limit: int = 30) -> list[dict[str, Any]]:
    return [{field: key, "rows": value} for key, value in counter.most_common(limit) if key]


def compact_sample(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "official_search_url": item.get("official_search_url"),
        "web_search_url": item.get("web_search_url"),
        "allowed_source_domains": item.get("allowed_source_domains") or [],
        "source_patch_template": item.get("source_patch_template") or {},
        "auto_apply_enabled": False,
    }


def build_report(action_queue: dict[str, Any], *, generated_at: str | None = None, sample_limit: int = 8) -> dict[str, Any]:
    store_rows: dict[str, dict[str, Any]] = {}
    total_items = 0
    for batch in action_queue.get("batches", []):
        if not isinstance(batch, dict):
            continue
        source_store = str(batch.get("source_store") or "unknown")
        bucket = store_rows.setdefault(
            source_store,
            {
                "source_store": source_store,
                "rows": 0,
                "batch_ids": [],
                "workflow_rows": Counter(),
                "review_state_rows": Counter(),
                "category_rows": Counter(),
                "allowed_source_domains": Counter(),
                "sample_items": [],
            },
        )
        row_count = int(batch.get("row_count") or 0)
        bucket["rows"] += row_count
        bucket["batch_ids"].append(batch.get("batch_id"))
        bucket["workflow_rows"][str(batch.get("workflow") or "")] += row_count
        bucket["review_state_rows"][str(batch.get("review_state") or "")] += row_count
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            total_items += 1
            category = str(item.get("category") or "")
            if category:
                bucket["category_rows"][category] += 1
            for domain in item.get("allowed_source_domains") or []:
                bucket["allowed_source_domains"][str(domain)] += 1
            if len(bucket["sample_items"]) < sample_limit:
                bucket["sample_items"].append(compact_sample(item))

    stores = []
    for bucket in store_rows.values():
        allowed_domains = [
            {"domain": domain, "rows": count}
            for domain, count in bucket["allowed_source_domains"].most_common(8)
        ]
        stores.append(
            {
                "source_store": bucket["source_store"],
                "rows": bucket["rows"],
                "batch_count": len([batch_id for batch_id in bucket["batch_ids"] if batch_id]),
                "batch_ids": [batch_id for batch_id in bucket["batch_ids"] if batch_id][:12],
                "workflow_rows": counter_rows(bucket["workflow_rows"], "workflow"),
                "review_state_rows": counter_rows(bucket["review_state_rows"], "review_state"),
                "by_category": counter_rows(bucket["category_rows"], "category", 12),
                "allowed_source_domains": allowed_domains,
                "has_allowed_source_domain": bool(allowed_domains),
                "next_step": "open_official_search_and_confirm_exact_product_source_url"
                if allowed_domains
                else "manual_domain_research_before_source_url_import",
                "sample_items": bucket["sample_items"],
                "auto_apply_enabled": False,
            }
        )
    stores.sort(key=lambda row: (-int(row["rows"]), str(row["source_store"])))
    domainless_rows = sum(int(row["rows"]) for row in stores if not row["has_allowed_source_domain"])
    summary = action_queue.get("summary") if isinstance(action_queue.get("summary"), dict) else {}

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_store_bottlenecks",
        "summary": {
            "actionable_source_rows": int(summary.get("actionable_source_rows") or total_items),
            "queued_source_rows": int(summary.get("queued_source_rows") or total_items),
            "store_count": len(stores),
            "top_store_rows": stores[0]["rows"] if stores else 0,
            "top_store": stores[0]["source_store"] if stores else None,
            "domainless_store_rows": domainless_rows,
            "stores_without_allowed_domain": sum(1 for row in stores if not row["has_allowed_source_domain"]),
            "auto_apply_enabled": False,
        },
        "stores": stores,
        "instructions": [
            "Work stores with the largest rows first because one confirmed search pattern can clear many missing images.",
            "Accepted source_url values must be exact product detail pages, not search results or store home pages.",
            "After source_url is confirmed, use image attachment queues to review image_url.",
        ],
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-limit", type=int, default=8)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), sample_limit=args.sample_limit)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
