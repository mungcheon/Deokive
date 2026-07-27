from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from build_catalog_boss_review_batch import DEFAULT_CATALOG, DEFAULT_LEDGER, build_batch
except ImportError:
    from tools.build_catalog_boss_review_batch import DEFAULT_CATALOG, DEFAULT_LEDGER, build_batch

APPROVED_STATUSES = {"fixed_pass", "pass"}
BLOCKED_STATUSES = {"content_error", "image_error"}
STATUS_LABELS = {
    "image_error": "사진오류",
    "content_error": "내용오류",
    "fixed_pass": "수정후통과",
    "pass": "통과",
}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_items(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path, {})
    if isinstance(payload, dict):
        items = payload.get("items") or []
    else:
        items = payload
    return [item for item in items if isinstance(item, dict)]


def _ledger_decisions(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path, {"decisions": []})
    if not isinstance(payload, dict):
        return []
    return [item for item in payload.get("decisions") or [] if isinstance(item, dict)]


def build_status(
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    ledger_path: Path = DEFAULT_LEDGER,
    batch_size: int = 10,
) -> dict[str, Any]:
    items = _catalog_items(catalog_path)
    decisions = _ledger_decisions(ledger_path)
    reviewed_indexes: set[int] = set()
    status_counts: Counter[str] = Counter()
    for decision in decisions:
        row_index = decision.get("row_index")
        status = str(decision.get("status") or "")
        if isinstance(row_index, bool) or not isinstance(row_index, int):
            continue
        reviewed_indexes.add(row_index)
        status_counts[status] += 1

    total_items = len(items)
    reviewed_items = len(reviewed_indexes)
    pending_items = max(total_items - reviewed_items, 0)
    approved_items = sum(status_counts[status] for status in APPROVED_STATUSES)
    blocked_items = sum(status_counts[status] for status in BLOCKED_STATUSES)
    review_percent = round((reviewed_items / total_items) * 100, 4) if total_items else 0

    next_batch = build_batch(catalog_path=catalog_path, ledger_path=ledger_path, batch_size=batch_size)
    remaining_full_batches = pending_items // batch_size if batch_size else 0
    remaining_tail_items = pending_items % batch_size if batch_size else 0
    remaining_batches = remaining_full_batches + (1 if remaining_tail_items else 0)

    return {
        "total_items": total_items,
        "reviewed_items": reviewed_items,
        "pending_items": pending_items,
        "approved_items": approved_items,
        "blocked_items": blocked_items,
        "review_percent": review_percent,
        "batch_size": batch_size,
        "remaining_batches": remaining_batches,
        "remaining_tail_items": remaining_tail_items,
        "status_counts": {key: status_counts[key] for key in sorted(status_counts)},
        "status_labels": STATUS_LABELS,
        "next_batch": {
            "selected_items": next_batch["meta"]["selected_items"],
            "first_row_index": next_batch["meta"]["first_row_index"],
            "last_row_index": next_batch["meta"]["last_row_index"],
            "batch_number": next_batch["meta"]["batch_number"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Show boss review progress for the public catalog.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    print(
        json.dumps(
            build_status(catalog_path=args.catalog, ledger_path=args.ledger, batch_size=args.batch_size),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
