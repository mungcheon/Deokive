from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from build_catalog_boss_review_batch import (
        DEFAULT_BATCH_HTML,
        DEFAULT_BATCH_JSON,
        DEFAULT_CATALOG,
        DEFAULT_LEDGER,
        build_batch,
        write_batch,
    )
    from import_catalog_boss_review_decisions import (
        DEFAULT_APPROVED,
        DEFAULT_REWORK,
        build_approved_catalog,
        build_rework_queue,
        merge_ledger,
        _normalize_decisions,
    )
except ImportError:
    from tools.build_catalog_boss_review_batch import (
        DEFAULT_BATCH_HTML,
        DEFAULT_BATCH_JSON,
        DEFAULT_CATALOG,
        DEFAULT_LEDGER,
        build_batch,
        write_batch,
    )
    from tools.import_catalog_boss_review_decisions import (
        DEFAULT_APPROVED,
        DEFAULT_REWORK,
        build_approved_catalog,
        build_rework_queue,
        merge_ledger,
        _normalize_decisions,
    )


def advance_review(
    decisions_path: Path,
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    ledger_path: Path = DEFAULT_LEDGER,
    approved_path: Path = DEFAULT_APPROVED,
    rework_path: Path = DEFAULT_REWORK,
    batch_json_path: Path = DEFAULT_BATCH_JSON,
    batch_html_path: Path = DEFAULT_BATCH_HTML,
    batch_size: int = 10,
) -> dict[str, Any]:
    decisions = _normalize_decisions(decisions_path)
    ledger = merge_ledger(ledger_path, decisions)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    approved = build_approved_catalog(catalog_path, ledger)
    approved_path.parent.mkdir(parents=True, exist_ok=True)
    approved_path.write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rework = build_rework_queue(catalog_path, ledger)
    rework_path.parent.mkdir(parents=True, exist_ok=True)
    rework_path.write_text(json.dumps(rework, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    next_batch = build_batch(catalog_path=catalog_path, ledger_path=ledger_path, batch_size=batch_size)
    write_batch(next_batch, batch_json_path, batch_html_path)

    return {
        "imported_decisions": len(decisions),
        "reviewed_items": ledger["meta"]["reviewed_items"],
        "approved_items": ledger["meta"]["approved_items"],
        "blocked_items": ledger["meta"]["blocked_items"],
        "next_selected_items": next_batch["meta"]["selected_items"],
        "next_first_row_index": next_batch["meta"]["first_row_index"],
        "next_last_row_index": next_batch["meta"]["last_row_index"],
        "next_batch_html": str(batch_html_path),
        "approved_out": str(approved_path),
        "rework_out": str(rework_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import boss review decisions, update local review outputs, and build the next 10-item batch."
    )
    parser.add_argument("decisions", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--approved-out", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--rework-out", type=Path, default=DEFAULT_REWORK)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_BATCH_JSON)
    parser.add_argument("--out-html", type=Path, default=DEFAULT_BATCH_HTML)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")

    result = advance_review(
        args.decisions,
        catalog_path=args.catalog,
        ledger_path=args.ledger,
        approved_path=args.approved_out,
        rework_path=args.rework_out,
        batch_json_path=args.out_json,
        batch_html_path=args.out_html,
        batch_size=args.batch_size,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
