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
DEFAULT_INPUT = ROOT / "data" / "requested_focus_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "requested_focus_action_queue_public.json"

ACTIONABLE_FIELDS = {
    "source_url",
    "image_url",
    "release_date",
    "official_price_jpy",
    "name_ja",
}

FIELD_PRIORITY = {
    "source_url": 10,
    "image_url": 20,
    "release_date": 30,
    "official_price_jpy": 40,
    "name_ja": 50,
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _count_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(str(row.get(key) or "") for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _compact_action_item(batch: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    return {
        "catalog_index": item.get("catalog_index"),
        "topic_id": batch.get("topic_id"),
        "topic_label": batch.get("topic_label"),
        "missing_field": item.get("missing_field") or batch.get("missing_field"),
        "source_store": item.get("source_store") or batch.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "image_url": item.get("image_url"),
        "release_date": item.get("release_date"),
        "official_price_jpy": item.get("official_price_jpy"),
        "catalog_field_import_template": template,
        "next_machine_step": batch.get("next_machine_step"),
        "recommended_action": batch.get("recommended_action"),
        "auto_apply_enabled": False,
    }


def build_report(review_batches: dict[str, Any], *, max_batches: int = 24, batch_size: int = 25) -> dict[str, Any]:
    action_items: list[dict[str, Any]] = []
    barcode_template_rows = 0
    skipped_non_template_rows = 0

    for batch in review_batches.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            template = item.get("catalog_field_import_template")
            if not isinstance(template, dict):
                skipped_non_template_rows += 1
                continue
            field = str(template.get("field") or item.get("missing_field") or batch.get("missing_field") or "")
            if field == "barcode":
                barcode_template_rows += 1
                continue
            if field not in ACTIONABLE_FIELDS:
                continue
            action_items.append(_compact_action_item(batch, item))

    action_items.sort(
        key=lambda row: (
            FIELD_PRIORITY.get(str(row.get("missing_field") or ""), 99),
            int(row.get("catalog_index") or 999_999_999),
            str(row.get("topic_id") or ""),
            str(row.get("source_store") or ""),
        )
    )

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in action_items:
        key = (
            str(item.get("missing_field") or ""),
            str(item.get("topic_id") or ""),
            str(item.get("source_store") or "unknown"),
        )
        grouped.setdefault(key, []).append(item)

    action_batches: list[dict[str, Any]] = []
    for (field, topic_id, source_store), rows in sorted(
        grouped.items(),
        key=lambda pair: (
            FIELD_PRIORITY.get(pair[0][0], 99),
            -len(pair[1]),
            pair[0][1],
            pair[0][2],
        ),
    ):
        for offset in range(0, len(rows), batch_size):
            chunk = rows[offset : offset + batch_size]
            if len(action_batches) >= max_batches:
                break
            action_batches.append(
                {
                    "batch_id": f"requested-focus-action-{len(action_batches) + 1:03d}",
                    "priority": FIELD_PRIORITY.get(field, 99),
                    "topic_id": topic_id,
                    "missing_field": field,
                    "source_store": source_store,
                    "row_count": len(chunk),
                    "offset": offset,
                    "review_state": "manual_evidence_review_required",
                    "next_machine_step": chunk[0].get("next_machine_step") if chunk else "",
                    "recommended_action": chunk[0].get("recommended_action") if chunk else "",
                    "category_counts": _count_pairs(chunk, "category"),
                    "items": chunk,
                    "auto_apply_enabled": False,
                }
            )
        if len(action_batches) >= max_batches:
            break

    queued_rows = sum(int(batch.get("row_count") or 0) for batch in action_batches)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "requested_focus_action_queue",
        "summary": {
            "actionable_template_rows": len(action_items),
            "queued_action_rows": queued_rows,
            "action_batch_count": len(action_batches),
            "batch_size": batch_size,
            "max_batches": max_batches,
            "barcode_template_rows_excluded": barcode_template_rows,
            "skipped_non_template_rows": skipped_non_template_rows,
            "field_counts": _count_pairs(action_items, "missing_field"),
            "topic_counts": _count_pairs(action_items, "topic_id"),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue for user-requested focus rows that are actionable before barcode research.",
            "Each item still requires exact official or trusted evidence before any catalog patch is applied.",
            "Barcode-only rows are excluded here and remain in requested_focus_review_batches_public.json.",
        ],
        "batches": action_batches,
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
    parser.add_argument("--max-batches", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_batches=args.max_batches, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
