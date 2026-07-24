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
DEFAULT_INPUT = ROOT / "data" / "requested_focus_action_queue_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "requested_focus_next_work_public.json"


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


def _compact_item(item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    return {
        "catalog_index": item.get("catalog_index"),
        "topic_id": item.get("topic_id"),
        "topic_label": item.get("topic_label"),
        "missing_field": item.get("missing_field"),
        "source_store": item.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "image_url": item.get("image_url"),
        "release_date": item.get("release_date"),
        "official_price_jpy": item.get("official_price_jpy"),
        "primary_review_url": item.get("primary_review_url"),
        "primary_review_url_kind": item.get("primary_review_url_kind"),
        "manual_value_field": template.get("field"),
        "manual_value": template.get("manual_value"),
        "evidence_url": template.get("evidence_url"),
        "manual_confirmed": bool(template.get("manual_confirmed")),
        "blocked_until": item.get("blocked_until"),
        "blocked_reason": item.get("blocked_reason"),
        "required_evidence": item.get("required_evidence") or [],
    }


def _compact_batch(batch: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in batch.get("items") or [] if isinstance(item, dict)]
    compact_items = [_compact_item(item) for item in items]
    return {
        "batch_id": batch.get("batch_id"),
        "priority": batch.get("priority"),
        "topic_id": batch.get("topic_id"),
        "missing_field": batch.get("missing_field"),
        "source_store": batch.get("source_store"),
        "row_count": batch.get("row_count"),
        "review_state": batch.get("review_state"),
        "next_machine_step": batch.get("next_machine_step"),
        "recommended_action": batch.get("recommended_action"),
        "blocked_until": batch.get("blocked_until"),
        "blocked_reason": batch.get("blocked_reason"),
        "required_evidence": batch.get("required_evidence") or [],
        "first_primary_review_url": batch.get("first_primary_review_url"),
        "first_primary_review_url_kind": batch.get("first_primary_review_url_kind"),
        "category_counts": batch.get("category_counts") or _count_pairs(compact_items, "category"),
        "items": compact_items,
        "auto_apply_enabled": False,
    }


def build_report(
    action_queue: dict[str, Any],
    *,
    preview_batches: int = 6,
    generated_at: str | None = None,
) -> dict[str, Any]:
    batches = [batch for batch in action_queue.get("batches") or [] if isinstance(batch, dict)]
    next_batch = _compact_batch(batches[0]) if batches else None
    preview = [_compact_batch(batch) for batch in batches[:preview_batches]]
    preview_items = [item for batch in preview for item in batch.get("items", [])]
    summary = action_queue.get("summary") if isinstance(action_queue.get("summary"), dict) else {}
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "requested_focus_next_work",
        "summary": {
            "source_report": "data/requested_focus_action_queue_public.json",
            "actionable_template_rows": int(summary.get("actionable_template_rows") or 0),
            "queued_action_rows": int(summary.get("queued_action_rows") or 0),
            "action_batch_count": int(summary.get("action_batch_count") or 0),
            "preview_batch_count": len(preview),
            "preview_row_count": sum(int(batch.get("row_count") or 0) for batch in preview),
            "next_batch_id": next_batch.get("batch_id") if next_batch else "",
            "next_topic_id": next_batch.get("topic_id") if next_batch else "",
            "next_missing_field": next_batch.get("missing_field") if next_batch else "",
            "next_source_store": next_batch.get("source_store") if next_batch else "",
            "next_row_count": int(next_batch.get("row_count") or 0) if next_batch else 0,
            "next_review_url": next_batch.get("first_primary_review_url") if next_batch else "",
            "preview_field_counts": _count_pairs(preview_items, "missing_field"),
            "preview_topic_counts": _count_pairs(preview_items, "topic_id"),
            "preview_source_store_counts": _count_pairs(preview_items, "source_store"),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Start with next_batch, confirm exact evidence, then copy confirmed values into the linked catalog_field_import_template fields.",
            "Do not import from this report directly; it is a small review surface for the requested_focus_action_queue.",
            "Rows remain blocked until manual_confirmed is true with a matching evidence_url and manual note when needed.",
        ],
        "next_batch": next_batch,
        "preview_batches": preview,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preview-batches", type=int, default=6)
    args = parser.parse_args()

    report = build_report(_load(args.input), preview_batches=args.preview_batches)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
