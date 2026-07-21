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
DEFAULT_INPUT = ROOT / "data" / "catalog_image_enrichment_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_image_attachment_action_queue_public.json"

WORKFLOW_PRIORITY = {
    "extract_from_existing_source_url": 10,
    "replace_generic_source_then_extract_image": 20,
    "review_gotouchi_official_candidates": 30,
}
ACTIONABLE_WORKFLOWS = set(WORKFLOW_PRIORITY)


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


def _compact_item(group: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    return {
        "catalog_index": item.get("catalog_index"),
        "workflow": group.get("workflow"),
        "source_store": group.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "official_search_url": item.get("official_search_url"),
        "catalog_field_import_template": template,
        "review_state": "exact_product_image_confirmation_required",
        "auto_apply_enabled": False,
    }


def build_report(enrichment_batches: dict[str, Any], *, max_batches: int = 18, batch_size: int = 20) -> dict[str, Any]:
    action_items: list[dict[str, Any]] = []
    excluded_workflows = Counter()
    actionable_group_rows = 0

    for group in enrichment_batches.get("groups", []):
        if not isinstance(group, dict):
            continue
        workflow = str(group.get("workflow") or "")
        missing_rows = int(group.get("missing_image_rows") or 0)
        if workflow not in ACTIONABLE_WORKFLOWS:
            excluded_workflows[workflow or "unknown"] += missing_rows
            continue
        actionable_group_rows += missing_rows
        for item in group.get("sample_items") or []:
            if isinstance(item, dict):
                action_items.append(_compact_item(group, item))

    action_items.sort(
        key=lambda row: (
            WORKFLOW_PRIORITY.get(str(row.get("workflow") or ""), 99),
            str(row.get("source_store") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in action_items:
        key = (str(item.get("workflow") or ""), str(item.get("source_store") or "unknown"))
        grouped.setdefault(key, []).append(item)

    batches: list[dict[str, Any]] = []
    for (workflow, source_store), rows in sorted(
        grouped.items(),
        key=lambda pair: (
            WORKFLOW_PRIORITY.get(pair[0][0], 99),
            -len(pair[1]),
            pair[0][1],
        ),
    ):
        for offset in range(0, len(rows), batch_size):
            if len(batches) >= max_batches:
                break
            chunk = rows[offset : offset + batch_size]
            batches.append(
                {
                    "batch_id": f"image-attachment-action-{len(batches) + 1:03d}",
                    "priority": WORKFLOW_PRIORITY.get(workflow, 99),
                    "workflow": workflow,
                    "source_store": source_store,
                    "row_count": len(chunk),
                    "offset": offset,
                    "review_state": "exact_product_image_confirmation_required",
                    "next_machine_step": {
                        "extract_from_existing_source_url": "extract_product_image_from_existing_exact_source_url",
                        "replace_generic_source_then_extract_image": "replace_generic_source_url_then_extract_image",
                        "review_gotouchi_official_candidates": "confirm_exact_gotouchi_product_type_then_attach_image",
                    }.get(workflow, "manual_image_review"),
                    "recommended_action": {
                        "extract_from_existing_source_url": "Review product page image and fill manual image_url.",
                        "replace_generic_source_then_extract_image": "Replace generic storefront URL with exact product page before image import.",
                        "review_gotouchi_official_candidates": "Confirm motif candidate matches product type before image import.",
                    }.get(workflow, "Review image evidence before import."),
                    "category_counts": _counter_pairs(chunk, "category"),
                    "items": chunk,
                    "auto_apply_enabled": False,
                }
            )
        if len(batches) >= max_batches:
            break

    queued_rows = sum(int(batch.get("row_count") or 0) for batch in batches)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_image_attachment_action_queue",
        "summary": {
            "actionable_image_rows": actionable_group_rows,
            "queued_image_rows": queued_rows,
            "action_batch_count": len(batches),
            "sample_action_item_rows": len(action_items),
            "batch_size": batch_size,
            "max_batches": max_batches,
            "by_workflow": _counter_pairs(action_items, "workflow"),
            "by_source_store": _counter_pairs(action_items, "source_store"),
            "excluded_workflow_rows": [[key, value] for key, value in excluded_workflows.most_common()],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue for image-url work that is closer to actionable than broad source discovery.",
            "Every image still needs exact product evidence before catalog mutation.",
            "Rows without source_url stay in catalog_image_enrichment_batches_public.json and source discovery queues.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-batches", type=int, default=18)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_batches=args.max_batches, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
