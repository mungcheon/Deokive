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
DEFAULT_INPUT = ROOT / "data" / "catalog_deduplication_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_deduplication_action_queue_public.json"

ACTIONABLE_CONFIDENCES = {"high_review_confidence", "medium_review_confidence"}
CONFIDENCE_PRIORITY = {
    "high_review_confidence": 10,
    "medium_review_confidence": 20,
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


def _compact_group(group: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "key_type": group.get("key_type"),
        "key": group.get("key"),
        "review_priority": group.get("review_priority"),
        "review_risk": group.get("review_risk"),
        "review_confidence": group.get("review_confidence"),
        "keep_catalog_index": group.get("keep_catalog_index"),
        "drop_catalog_indexes": group.get("drop_catalog_indexes") or [],
        "row_count": group.get("row_count"),
        "stores": group.get("stores") or [],
        "categories": group.get("categories") or [],
        "evidence": group.get("evidence") or [],
        "merge_blockers": group.get("merge_blockers") or [],
        "identity_checklist": group.get("identity_checklist") or batch.get("identity_checklist") or [],
        "recommended_action": group.get("recommended_action") or batch.get("recommended_action"),
        "dedupe_decision_template": group.get("dedupe_decision_template") or {},
        "rows": group.get("rows") or [],
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def build_report(review_batches: dict[str, Any], *, max_groups: int = 40, batch_size: int = 10) -> dict[str, Any]:
    actionable: list[dict[str, Any]] = []
    excluded = Counter()

    for batch in review_batches.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for group in batch.get("groups") or []:
            if not isinstance(group, dict):
                continue
            confidence = str(group.get("review_confidence") or "")
            if confidence not in ACTIONABLE_CONFIDENCES:
                excluded[confidence or "unknown"] += 1
                continue
            compact = _compact_group(group, batch)
            compact["queue_priority"] = CONFIDENCE_PRIORITY.get(confidence, 99)
            actionable.append(compact)

    actionable.sort(
        key=lambda group: (
            int(group.get("queue_priority") or 99),
            int(group.get("review_priority") or 99),
            str(group.get("key_type") or ""),
            str(group.get("key") or ""),
        )
    )
    published = actionable[:max_groups]
    unqueued_actionable_groups = max(len(actionable) - len(published), 0)
    queue_coverage = round(len(published) / len(actionable), 4) if actionable else 1.0

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(published), batch_size):
        groups = published[offset : offset + batch_size]
        batches.append(
            {
                "batch_id": f"dedupe-action-{len(batches) + 1:03d}",
                "priority": min(int(group.get("queue_priority") or 99) for group in groups),
                "group_count": len(groups),
                "offset": offset,
                "review_state": "explicit_keep_drop_confirmation_required",
                "next_machine_step": "record_manual_dedupe_decisions",
                "recommended_action": "Confirm same sellable product identity, then record manual keep/drop decisions.",
                "review_confidence_counts": _counter_pairs(groups, "review_confidence"),
                "key_type_counts": _counter_pairs(groups, "key_type"),
                "review_risk_counts": _counter_pairs(groups, "review_risk"),
                "groups": groups,
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_deduplication_action_queue",
        "summary": {
            "actionable_groups": len(actionable),
            "queued_groups": len(published),
            "unqueued_actionable_groups": unqueued_actionable_groups,
            "queue_coverage": queue_coverage,
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "max_groups": max_groups,
            "by_review_confidence": _counter_pairs(actionable, "review_confidence"),
            "by_key_type": _counter_pairs(actionable, "key_type"),
            "excluded_review_confidence": [[key, value] for key, value in excluded.most_common()],
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        "instructions": [
            "Use this queue for the safest dedupe reviews first; it still never deletes automatically.",
            "Variant caution and manual identity check groups remain in catalog_deduplication_review_batches_public.json.",
            "Every accepted group needs an explicit manual keep/drop decision before mutation.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_merge": False,
            "auto_delete": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-groups", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_groups=args.max_groups, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
