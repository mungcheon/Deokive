from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "ichiban_kuji_history_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "ichiban_kuji_metadata_review_batches_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_queue(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    queue = payload.get("campaign_metadata_review_queue")
    if not isinstance(queue, list):
        raise ValueError(f"{path} must contain a campaign_metadata_review_queue list")
    return payload, [row for row in queue if isinstance(row, dict)]


def _workflow(row: dict[str, Any]) -> str:
    missing = set(str(field) for field in row.get("missing_fields") or [])
    if {"release_date", "official_price_jpy"} <= missing:
        return "release_and_price_review"
    if "release_date" in missing:
        return "release_date_review"
    if "official_price_jpy" in missing:
        return "price_review"
    return "metadata_review"


def _next_step(workflow: str) -> str:
    if workflow == "release_date_review":
        return "verify_labeled_official_release_date"
    if workflow == "price_review":
        return "verify_labeled_official_price_jpy"
    if workflow == "release_and_price_review":
        return "verify_labeled_official_release_date_and_price"
    return "review_official_campaign_metadata"


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    workflow = _workflow(row)
    return {
        "group_key": row.get("group_key"),
        "url": row.get("url"),
        "slug": row.get("slug"),
        "title": row.get("title"),
        "catalog_item_rows": int(row.get("catalog_item_rows") or 0),
        "missing_fields": row.get("missing_fields") or [],
        "review_priority": int(row.get("review_priority") or 999),
        "workflow": workflow,
        "source_evidence_required": row.get("source_evidence_required"),
        "recommended_action": row.get("recommended_action"),
        "sample_catalog_indexes": row.get("sample_catalog_indexes") or [],
        "sample_names": row.get("sample_names") or [],
        "next_machine_step": _next_step(workflow),
        "auto_apply_enabled": False,
    }


def build_report(source: dict[str, Any], queue: list[dict[str, Any]], *, batch_size: int = 8) -> dict[str, Any]:
    rows = [_compact_row(row) for row in sorted(queue, key=lambda row: (int(row.get("review_priority") or 999), str(row.get("slug") or "")))]
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(rows), batch_size):
        batch_rows = rows[offset : offset + batch_size]
        workflows = Counter(str(row.get("workflow") or "") for row in batch_rows)
        missing_fields = Counter(field for row in batch_rows for field in row.get("missing_fields") or [])
        batches.append(
            {
                "batch_id": f"ichiban-metadata-review-{len(batches) + 1:03d}",
                "priority": min(int(row.get("review_priority") or 999) for row in batch_rows),
                "campaign_count": len(batch_rows),
                "catalog_item_rows": sum(int(row.get("catalog_item_rows") or 0) for row in batch_rows),
                "workflow_counts": workflows.most_common(),
                "missing_field_counts": missing_fields.most_common(),
                "review_state": "official_campaign_evidence_required",
                "next_machine_step": "verify_ichiban_campaign_page",
                "recommended_action": "Verify labeled official campaign metadata before preparing any catalog patch.",
                "campaigns": batch_rows,
            }
        )

    workflow_counts = Counter(str(row.get("workflow") or "") for row in rows)
    missing_field_counts = Counter(field for row in rows for field in row.get("missing_fields") or [])
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "ichiban_kuji_metadata_review_batches",
        "summary": {
            "source_campaigns": len(queue),
            "catalog_item_rows": sum(int(row.get("catalog_item_rows") or 0) for row in rows),
            "batch_count": len(batches),
            "batch_size": batch_size,
            "missing_release_date_rows": source.get("summary", {}).get("missing_release_date_rows", 0),
            "missing_official_price_jpy_rows": source.get("summary", {}).get("missing_official_price_jpy_rows", 0),
            "by_workflow": workflow_counts.most_common(),
            "by_missing_field": missing_field_counts.most_common(),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Review batches in priority order.",
            "Use only labeled official 1kuji campaign metadata or captured official evidence.",
            "Do not apply unlabeled dates, double-chance dates, or inferred historical prices.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_release_date": False,
            "auto_apply_official_price_jpy": False,
            "requires_manual_review": True,
            "reason": "Historical 1kuji pages can expose unlabeled campaign dates and prices that are unsafe to import automatically.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    source, queue = _load_queue(args.input)
    report = build_report(source, queue, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
