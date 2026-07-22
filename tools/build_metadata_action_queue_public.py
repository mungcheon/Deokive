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
DEFAULT_INPUT = ROOT / "data" / "catalog_metadata_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_metadata_action_queue_public.json"

ACTIONABLE_FIELDS = {
    "release_date",
    "official_price_jpy",
    "name_ja",
}

FIELD_PRIORITY = {
    "release_date": 10,
    "official_price_jpy": 20,
    "name_ja": 30,
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


def _template_for_group(group: dict[str, Any]) -> dict[str, Any]:
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "field": group.get("field"),
        "manual_value": "",
        "evidence_url": "",
        "source_store": group.get("source_store"),
        "target_scope": "field_source_store_group",
        "target_missing_rows": group.get("missing_rows"),
        "target_catalog_indexes_sample": group.get("sample_catalog_indexes") or [],
        "requires_exact_official_or_trusted_evidence": True,
        "blocked_until": "manual_metadata_evidence_confirmed",
    }


def _compact_group(group: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    field = str(group.get("field") or "")
    return {
        "field": field,
        "source_store": group.get("source_store"),
        "missing_rows": int(group.get("missing_rows") or 0),
        "priority": FIELD_PRIORITY.get(field, int(group.get("priority") or 99)),
        "workflow": group.get("workflow"),
        "evidence_required": group.get("evidence_required"),
        "risk": group.get("risk"),
        "recommended_action": group.get("recommended_action") or batch.get("recommended_action"),
        "next_machine_step": group.get("next_machine_step") or batch.get("next_machine_step"),
        "sample_catalog_indexes": group.get("sample_catalog_indexes") or [],
        "sample_items": group.get("sample_items") or [],
        "catalog_field_import_template": _template_for_group(group),
        "auto_apply_enabled": False,
    }


def build_report(review_batches: dict[str, Any], *, max_groups: int = 200, batch_size: int = 12) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    excluded_fields = Counter()

    for batch in review_batches.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for group in batch.get("groups") or []:
            if not isinstance(group, dict):
                continue
            field = str(group.get("field") or "")
            missing_rows = int(group.get("missing_rows") or 0)
            if field not in ACTIONABLE_FIELDS:
                excluded_fields[field or "unknown"] += missing_rows
                continue
            groups.append(_compact_group(group, batch))

    groups.sort(
        key=lambda row: (
            FIELD_PRIORITY.get(str(row.get("field") or ""), 99),
            -int(row.get("missing_rows") or 0),
            str(row.get("source_store") or ""),
        )
    )
    published = groups[:max_groups]
    actionable_missing_cells = sum(int(row.get("missing_rows") or 0) for row in groups)
    queued_missing_cells = sum(int(row.get("missing_rows") or 0) for row in published)
    unqueued_actionable_group_count = max(len(groups) - len(published), 0)
    unqueued_actionable_missing_cells = max(actionable_missing_cells - queued_missing_cells, 0)
    group_queue_coverage = round(len(published) / len(groups), 4) if groups else 1.0
    missing_cell_queue_coverage = round(queued_missing_cells / actionable_missing_cells, 4) if actionable_missing_cells else 1.0

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(published), batch_size):
        chunk = published[offset : offset + batch_size]
        field_counts = Counter(str(row.get("field") or "") for row in chunk)
        store_counts = Counter(str(row.get("source_store") or "") for row in chunk)
        field_missing_cells = Counter()
        store_missing_cells = Counter()
        for row in chunk:
            missing_rows = int(row.get("missing_rows") or 0)
            field_missing_cells[str(row.get("field") or "")] += missing_rows
            store_missing_cells[str(row.get("source_store") or "")] += missing_rows
        batches.append(
            {
                "batch_id": f"metadata-action-{len(batches) + 1:03d}",
                "priority": min(int(row.get("priority") or 99) for row in chunk),
                "group_count": len(chunk),
                "missing_cell_count": sum(int(row.get("missing_rows") or 0) for row in chunk),
                "offset": offset,
                "field_counts": field_counts.most_common(),
                "source_store_counts": store_counts.most_common(),
                "missing_cells_by_field": field_missing_cells.most_common(),
                "missing_cells_by_source_store": store_missing_cells.most_common(),
                "review_state": "manual_metadata_evidence_confirmation_required",
                "next_machine_step": "fill_confirmed_metadata_patch_templates",
                "recommended_action": "Confirm official metadata evidence, then fill field/store patch templates.",
                "groups": chunk,
                "auto_apply_enabled": False,
            }
        )

    missing_cells_by_field = Counter()
    missing_cells_by_store = Counter()
    for row in groups:
        missing_rows = int(row.get("missing_rows") or 0)
        missing_cells_by_field[str(row.get("field") or "")] += missing_rows
        missing_cells_by_store[str(row.get("source_store") or "")] += missing_rows
    top_action_groups = [
        {
            "field": row.get("field"),
            "source_store": row.get("source_store"),
            "missing_rows": int(row.get("missing_rows") or 0),
            "priority": int(row.get("priority") or 99),
            "workflow": row.get("workflow"),
            "recommended_action": row.get("recommended_action"),
        }
        for row in sorted(
            groups,
            key=lambda row: (
                -int(row.get("missing_rows") or 0),
                int(row.get("priority") or 99),
                str(row.get("field") or ""),
                str(row.get("source_store") or ""),
            ),
        )[:20]
    ]

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_metadata_action_queue",
        "summary": {
            "actionable_group_count": len(groups),
            "queued_group_count": len(published),
            "unqueued_actionable_group_count": unqueued_actionable_group_count,
            "actionable_missing_cells": actionable_missing_cells,
            "queued_missing_cells": queued_missing_cells,
            "unqueued_actionable_missing_cells": unqueued_actionable_missing_cells,
            "group_queue_coverage": group_queue_coverage,
            "missing_cell_queue_coverage": missing_cell_queue_coverage,
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "max_groups": max_groups,
            "field_counts": _counter_pairs(groups, "field"),
            "source_store_counts": _counter_pairs(groups, "source_store")[:40],
            "missing_cells_by_field": missing_cells_by_field.most_common(),
            "missing_cells_by_source_store": missing_cells_by_store.most_common(40),
            "top_action_groups": top_action_groups,
            "excluded_field_missing_cells": [[key, value] for key, value in excluded_fields.most_common()],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue for metadata work not covered by source/image/barcode-specific queues.",
            "Every field/store group still requires exact official or trusted evidence before import.",
            "Barcode, source_url, and image_url remain in their dedicated queues.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_metadata": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-groups", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=12)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_groups=args.max_groups, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
