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
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
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


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _catalog_image_lookup(catalog: dict[str, Any] | None) -> dict[int, bool]:
    if not catalog:
        return {}
    items = catalog.get("items")
    if not isinstance(items, list):
        return {}
    lookup: dict[int, bool] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        catalog_index = item.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            lookup[catalog_index] = _present(item.get("local_image_path")) or _present(item.get("image_url"))
    return lookup


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(str(row.get(key) or "") for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _build_workstreams(batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for batch in batches:
        workflow = str(batch.get("workflow") or "")
        source_store = str(batch.get("source_store") or "unknown")
        key = (workflow, source_store)
        bucket = grouped.setdefault(
            key,
            {
                "workflow": workflow,
                "source_store": source_store,
                "priority": int(batch.get("priority") or 99),
                "queued_image_rows": 0,
                "batch_ids": [],
                "source_url_update_template_rows": 0,
                "representative_image_review_rows": 0,
                "image_url_ready_rows": 0,
                "category_rows": Counter(),
                "sample_items": [],
            },
        )
        bucket["priority"] = min(int(bucket["priority"]), int(batch.get("priority") or 99))
        bucket["queued_image_rows"] += int(batch.get("row_count") or 0)
        bucket["batch_ids"].append(batch.get("batch_id"))
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            if item.get("source_url_import_template"):
                bucket["source_url_update_template_rows"] += 1
            if item.get("representative_image_review_required"):
                bucket["representative_image_review_rows"] += 1
            if item.get("image_url_ready"):
                bucket["image_url_ready_rows"] += 1
            category = str(item.get("category") or "")
            if category:
                bucket["category_rows"][category] += 1
            if len(bucket["sample_items"]) < 8:
                bucket["sample_items"].append(
                    {
                        "catalog_index": item.get("catalog_index"),
                        "review_lane": item.get("review_lane"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "category": item.get("category"),
                        "source_url": item.get("source_url"),
                        "official_search_url": item.get("official_search_url"),
                        "source_url_update_required": item.get("source_url_update_required"),
                        "representative_image_review_required": item.get(
                            "representative_image_review_required"
                        ),
                    }
                )

    rows = []
    for bucket in grouped.values():
        batch_ids = [batch_id for batch_id in bucket["batch_ids"] if batch_id]
        workflow = bucket["workflow"]
        rows.append(
            {
                "workflow": workflow,
                "source_store": bucket["source_store"],
                "priority": bucket["priority"],
                "queued_image_rows": bucket["queued_image_rows"],
                "batch_count": len(batch_ids),
                "next_batch_id": batch_ids[0] if batch_ids else None,
                "batch_ids": batch_ids,
                "next_machine_step": {
                    "extract_from_existing_source_url": "extract_product_image_from_existing_exact_source_url",
                    "replace_generic_source_then_extract_image": "replace_generic_source_url_then_extract_image",
                    "review_gotouchi_official_candidates": "confirm_exact_gotouchi_product_type_then_attach_image",
                }.get(workflow, "manual_image_review"),
                "source_url_update_template_rows": bucket["source_url_update_template_rows"],
                "representative_image_review_rows": bucket["representative_image_review_rows"],
                "image_url_ready_rows": bucket["image_url_ready_rows"],
                "category_rows": [
                    [category, count] for category, count in bucket["category_rows"].most_common()
                ],
                "review_summary": _workstream_review_summary(workflow, bucket),
                "sample_items": bucket["sample_items"],
                "auto_apply_enabled": False,
            }
        )
    rows.sort(
        key=lambda row: (
            int(row["priority"]),
            -int(row["queued_image_rows"]),
            str(row["source_store"]),
        )
    )
    return rows


def _compact_item(group: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    workflow = str(group.get("workflow") or "")
    source_url_update_required = workflow == "replace_generic_source_then_extract_image"
    representative_image_review_required = workflow == "review_gotouchi_official_candidates"
    image_url_ready = workflow == "extract_from_existing_source_url"
    source_url_template = _source_url_import_template(item, group) if source_url_update_required else None
    review_lane = _review_lane(workflow)
    return {
        "catalog_index": item.get("catalog_index"),
        "workflow": workflow,
        "review_lane": review_lane,
        "source_store": group.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "official_search_url": item.get("official_search_url"),
        "source_url_update_required": source_url_update_required,
        "representative_image_review_required": representative_image_review_required,
        "image_url_ready": image_url_ready,
        "required_before_image_import": _required_before_image_import(workflow),
        "image_import_blockers": _image_import_blockers(workflow),
        "manual_confirmation_requirements": _manual_confirmation_requirements(workflow),
        "source_url_import_template": source_url_template,
        "catalog_field_import_template": template,
        "review_state": "exact_product_image_confirmation_required",
        "auto_apply_enabled": False,
    }


def _source_url_import_template(item: dict[str, Any], group: dict[str, Any]) -> dict[str, Any]:
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "row_index": item.get("catalog_index"),
        "field": "source_url",
        "manual_value": "",
        "evidence_url": "",
        "candidate_source_url": "",
        "current_source_url": item.get("source_url"),
        "source_store": item.get("source_store") or group.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "official_search_url": item.get("official_search_url"),
        "workflow": group.get("workflow"),
        "blocked_until": "exact_product_source_url_confirmed",
        "auto_apply_enabled": False,
    }


def build_report(
    enrichment_batches: dict[str, Any],
    catalog: dict[str, Any] | None = None,
    *,
    max_batches: int = 18,
    batch_size: int = 20,
) -> dict[str, Any]:
    action_items: list[dict[str, Any]] = []
    excluded_workflows = Counter()
    actionable_group_rows = 0
    skipped_already_has_image_rows = 0
    has_image_by_index = _catalog_image_lookup(catalog)

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
                catalog_index = item.get("catalog_index")
                if isinstance(catalog_index, int) and has_image_by_index.get(catalog_index):
                    skipped_already_has_image_rows += 1
                    continue
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
    workstreams = _build_workstreams(batches)
    unqueued_actionable_rows = max(actionable_group_rows - queued_rows, 0)
    source_url_update_required_rows = sum(1 for item in action_items if item.get("source_url_update_required"))
    source_url_update_template_rows = sum(1 for item in action_items if item.get("source_url_import_template"))
    representative_image_review_required_rows = sum(
        1 for item in action_items if item.get("representative_image_review_required")
    )
    image_url_ready_rows = sum(1 for item in action_items if item.get("image_url_ready"))
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_image_attachment_action_queue",
        "summary": {
            "actionable_image_rows": actionable_group_rows,
            "queued_image_rows": queued_rows,
            "unqueued_actionable_image_rows": unqueued_actionable_rows,
            "sample_queue_coverage": round(queued_rows / actionable_group_rows, 4)
            if actionable_group_rows
            else 0,
            "action_batch_count": len(batches),
            "sample_action_item_rows": len(action_items),
            "skipped_already_has_image_rows": skipped_already_has_image_rows,
            "batch_size": batch_size,
            "max_batches": max_batches,
            "by_workflow": _counter_pairs(action_items, "workflow"),
            "by_source_store": _counter_pairs(action_items, "source_store"),
            "source_url_update_required_rows": source_url_update_required_rows,
            "source_url_update_template_rows": source_url_update_template_rows,
            "representative_image_review_required_rows": representative_image_review_required_rows,
            "image_url_ready_rows": image_url_ready_rows,
            "workstream_count": len(workstreams),
            "source_url_update_workstream_count": sum(
                1 for row in workstreams if row.get("source_url_update_template_rows")
            ),
            "representative_image_review_workstream_count": sum(
                1 for row in workstreams if row.get("representative_image_review_rows")
            ),
            "excluded_workflow_rows": [[key, value] for key, value in excluded_workflows.most_common()],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue for image-url work that is closer to actionable than broad source discovery.",
            "Every image still needs exact product evidence before catalog mutation.",
            "queued_image_rows is the current review sample; unqueued_actionable_image_rows remains for later batches.",
            "Rows without source_url stay in catalog_image_enrichment_batches_public.json and source discovery queues.",
            "For generic storefront rows, fill source_url_import_template before the image_url template.",
        ],
        "workstreams": workstreams,
        "next_actions": [
            {
                "priority": 1,
                "workstream": "replace_generic_source_then_extract_image",
                "rows": source_url_update_required_rows,
                "workstream_count": sum(
                    1 for row in workstreams if row.get("source_url_update_template_rows")
                ),
                "next_batch_id": next(
                    (
                        row.get("next_batch_id")
                        for row in workstreams
                        if row.get("source_url_update_template_rows")
                    ),
                    None,
                ),
                "recommended_next_action": "Confirm exact product detail URLs for generic storefront rows before image import.",
            },
            {
                "priority": 2,
                "workstream": "review_representative_image_candidates",
                "rows": representative_image_review_required_rows,
                "workstream_count": sum(
                    1 for row in workstreams if row.get("representative_image_review_rows")
                ),
                "next_batch_id": next(
                    (
                        row.get("next_batch_id")
                        for row in workstreams
                        if row.get("representative_image_review_rows")
                    ),
                    None,
                ),
                "recommended_next_action": "Confirm representative official candidates only when product type and variant match.",
            },
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def _required_before_image_import(workflow: str) -> list[str]:
    if workflow == "extract_from_existing_source_url":
        return ["confirm_product_page_image_url"]
    if workflow == "replace_generic_source_then_extract_image":
        return ["confirm_exact_product_source_url", "replace_generic_source_url", "confirm_product_page_image_url"]
    if workflow == "review_gotouchi_official_candidates":
        return ["confirm_exact_product_type", "confirm_representative_image_is_acceptable"]
    return ["manual_image_evidence_review"]


def _review_lane(workflow: str) -> str:
    if workflow == "extract_from_existing_source_url":
        return "image_url_review_ready"
    if workflow == "replace_generic_source_then_extract_image":
        return "source_url_replacement_first"
    if workflow == "review_gotouchi_official_candidates":
        return "representative_image_candidate_review"
    return "manual_image_research"


def _image_import_blockers(workflow: str) -> list[str]:
    if workflow == "extract_from_existing_source_url":
        return ["manual_image_url_confirmation"]
    if workflow == "replace_generic_source_then_extract_image":
        return [
            "generic_storefront_source_url",
            "missing_exact_product_detail_url",
            "missing_product_page_image_url",
        ]
    if workflow == "review_gotouchi_official_candidates":
        return [
            "representative_image_may_not_match_exact_variant",
            "product_type_confirmation_required",
        ]
    return ["manual_source_and_image_evidence_required"]


def _manual_confirmation_requirements(workflow: str) -> list[str]:
    if workflow == "extract_from_existing_source_url":
        return [
            "Open source_url.",
            "Confirm the page is for the exact catalog item.",
            "Copy the primary product image URL into the image attachment template.",
        ]
    if workflow == "replace_generic_source_then_extract_image":
        return [
            "Find the exact product detail page, not a storefront or search page.",
            "Fill source_url_import_template.manual_value with that exact product URL.",
            "Only after source_url is replaced, confirm and attach the product image URL.",
        ]
    if workflow == "review_gotouchi_official_candidates":
        return [
            "Confirm character, regional motif, product type, and variant.",
            "Use representative images only when the exact variant cannot be separated safely.",
            "Do not auto-apply if the official candidate shows a different product type.",
        ]
    return ["Manually confirm source and image evidence before catalog mutation."]


def _workstream_review_summary(workflow: str, bucket: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_lane": _review_lane(workflow),
        "queued_rows": bucket["queued_image_rows"],
        "source_url_update_required_rows": bucket["source_url_update_template_rows"],
        "representative_image_review_rows": bucket["representative_image_review_rows"],
        "image_url_ready_rows": bucket["image_url_ready_rows"],
        "primary_blockers": _image_import_blockers(workflow),
        "manual_confirmation_requirements": _manual_confirmation_requirements(workflow),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-batches", type=int, default=18)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()

    report = build_report(
        _load(args.input),
        _load(args.catalog) if args.catalog.exists() else None,
        max_batches=args.max_batches,
        batch_size=args.batch_size,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
