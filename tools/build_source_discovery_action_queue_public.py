from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "source_discovery_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "source_discovery_action_queue_public.json"

ACTIONABLE_REVIEW_STATES = {
    "official_search_review_required": 10,
    "licensed_retailer_review_required": 20,
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(str(row.get(key) or "") for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _source_store_workstreams(batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    workstreams: dict[str, dict[str, Any]] = {}
    for batch in batches:
        source_store = str(batch.get("source_store") or "unknown")
        bucket = workstreams.setdefault(
            source_store,
            {
                "source_store": source_store,
                "priority": int(batch.get("priority") or 99),
                "queued_source_rows": 0,
                "batch_ids": [],
                "workflow_rows": Counter(),
                "review_state_rows": Counter(),
                "category_rows": Counter(),
                "sample_items": [],
                "recommended_next_step": "confirm_exact_source_url_then_fill_source_templates",
                "auto_apply_enabled": False,
            },
        )
        bucket["priority"] = min(int(bucket["priority"]), int(batch.get("priority") or 99))
        row_count = int(batch.get("row_count") or 0)
        bucket["queued_source_rows"] += row_count
        bucket["batch_ids"].append(batch.get("batch_id"))
        bucket["workflow_rows"][str(batch.get("workflow") or "")] += row_count
        bucket["review_state_rows"][str(batch.get("review_state") or "")] += row_count
        for category, count in batch.get("category_counts") or []:
            bucket["category_rows"][str(category or "")] += int(count or 0)
        for item in batch.get("items") or []:
            if isinstance(item, dict) and len(bucket["sample_items"]) < 8:
                bucket["sample_items"].append(
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "category": item.get("category"),
                        "official_search_url": item.get("official_search_url"),
                        "allowed_source_domains": item.get("allowed_source_domains") or [],
                    }
                )

    rows: list[dict[str, Any]] = []
    for bucket in workstreams.values():
        rows.append(
            {
                "source_store": bucket["source_store"],
                "priority": bucket["priority"],
                "queued_source_rows": bucket["queued_source_rows"],
                "batch_ids": [batch_id for batch_id in bucket["batch_ids"] if batch_id],
                "workflow_rows": [[key, value] for key, value in bucket["workflow_rows"].most_common() if key],
                "review_state_rows": [[key, value] for key, value in bucket["review_state_rows"].most_common() if key],
                "category_rows": [[key, value] for key, value in bucket["category_rows"].most_common(12) if key],
                "sample_items": bucket["sample_items"],
                "recommended_next_step": bucket["recommended_next_step"],
                "auto_apply_enabled": False,
            }
        )
    return sorted(rows, key=lambda row: (int(row["priority"]), -int(row["queued_source_rows"]), str(row["source_store"])))


def _compact_item(batch: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    source_template = item.get("source_patch_template")
    source_template = source_template if isinstance(source_template, dict) else {}
    return {
        "catalog_index": item.get("catalog_index"),
        "workflow": batch.get("workflow"),
        "review_state": batch.get("review_state"),
        "source_store": item.get("source_store") or batch.get("source_store"),
        "category": item.get("category"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "official_search_url": item.get("official_search_url"),
        "web_search_url": item.get("web_search_url"),
        "allowed_source_domains": item.get("allowed_source_domains") or batch.get("allowed_source_domains") or [],
        "acceptance_rule": item.get("acceptance_rule") or batch.get("acceptance_rule"),
        "source_patch_template": source_template,
        "catalog_field_import_template": template,
        "next_machine_step": batch.get("next_machine_step"),
        "auto_apply_enabled": False,
    }


def build_report(review_batches: dict[str, Any], *, max_rows: int = 1000, batch_size: int = 20) -> dict[str, Any]:
    action_items: list[dict[str, Any]] = []
    manual_research_items: list[dict[str, Any]] = []
    excluded_review_states = Counter()
    actionable_source_rows = 0

    for batch in review_batches.get("batches", []):
        if not isinstance(batch, dict):
            continue
        review_state = str(batch.get("review_state") or "")
        row_count = int(batch.get("row_count") or 0)
        if review_state not in ACTIONABLE_REVIEW_STATES:
            excluded_review_states[review_state or "unknown"] += row_count
            if review_state == "manual_official_research_required":
                for item in batch.get("items") or []:
                    if isinstance(item, dict):
                        manual_research_items.append(_compact_item(batch, item))
            continue
        actionable_source_rows += row_count
        for item in batch.get("items") or []:
            if isinstance(item, dict):
                action_items.append(_compact_item(batch, item))

    action_items.sort(
        key=lambda row: (
            ACTIONABLE_REVIEW_STATES.get(str(row.get("review_state") or ""), 99),
            str(row.get("source_store") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )
    published = action_items[:max_rows]
    unqueued_actionable_source_rows = max(actionable_source_rows - len(published), 0)
    queue_coverage = round(len(published) / actionable_source_rows, 4) if actionable_source_rows else 1.0
    source_patch_template_count = sum(
        1 for item in published if item.get("source_patch_template")
    )
    catalog_field_import_template_count = sum(
        1 for item in published if item.get("catalog_field_import_template")
    )
    missing_template_items = [
        item.get("catalog_index")
        for item in published
        if not item.get("source_patch_template")
        or not item.get("catalog_field_import_template")
    ]

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in published:
        key = (
            str(item.get("review_state") or ""),
            str(item.get("workflow") or ""),
            str(item.get("source_store") or "unknown"),
        )
        grouped.setdefault(key, []).append(item)

    batches: list[dict[str, Any]] = []
    for (review_state, workflow, source_store), rows in sorted(
        grouped.items(),
        key=lambda pair: (
            ACTIONABLE_REVIEW_STATES.get(pair[0][0], 99),
            -len(pair[1]),
            pair[0][2],
        ),
    ):
        for offset in range(0, len(rows), batch_size):
            chunk = rows[offset : offset + batch_size]
            batches.append(
                {
                    "batch_id": f"source-discovery-action-{len(batches) + 1:03d}",
                    "priority": ACTIONABLE_REVIEW_STATES.get(review_state, 99),
                    "workflow": workflow,
                    "review_state": review_state,
                    "source_store": source_store,
                    "row_count": len(chunk),
                    "offset": offset,
                    "next_machine_step": "confirm_exact_source_url_then_fill_source_templates",
                    "recommended_action": "Open official search candidates, confirm exact product detail URLs, then fill source_url templates.",
                    "category_counts": _counter_pairs(chunk, "category"),
                    "items": chunk,
                    "auto_apply_enabled": False,
                }
            )

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "source_discovery_action_queue",
        "summary": {
            "actionable_source_rows": actionable_source_rows,
            "queued_source_rows": len(published),
            "unqueued_actionable_source_rows": unqueued_actionable_source_rows,
            "queue_coverage": queue_coverage,
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "max_rows": max_rows,
            "source_patch_template_count": source_patch_template_count,
            "catalog_field_import_template_count": catalog_field_import_template_count,
            "missing_template_item_count": len(missing_template_items),
            "missing_template_sample_catalog_indexes": missing_template_items[:25],
            "by_review_state": _counter_pairs(action_items, "review_state"),
            "by_workflow": _counter_pairs(action_items, "workflow"),
            "by_source_store": _counter_pairs(action_items, "source_store")[:40],
            "excluded_review_state_rows": [[key, value] for key, value in excluded_review_states.most_common()],
            "manual_research_backlog_rows": len(manual_research_items),
            "manual_research_backlog_by_source_store": _counter_pairs(manual_research_items, "source_store"),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue for source_url work with an existing official or trusted search path.",
            "Accepted source_url values must be exact product/detail pages, not search results or storefronts.",
            "After source_url is confirmed, image_url can be handled by the image attachment queues.",
        ],
        "source_store_workstreams": _source_store_workstreams(batches),
        "manual_research_backlog": [
            {
                "catalog_index": item.get("catalog_index"),
                "source_store": item.get("source_store"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "web_search_url": item.get("web_search_url"),
                "acceptance_rule": item.get("acceptance_rule"),
                "recommended_next_step": "find_official_domain_then_record_exact_product_detail_source",
                "auto_apply_enabled": False,
            }
            for item in manual_research_items
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-rows", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_rows=args.max_rows, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
