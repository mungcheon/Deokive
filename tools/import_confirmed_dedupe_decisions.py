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

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DEFAULT_QUEUE = SERVER / "catalog_dedupe_confirmed_decisions.json"
FALLBACK_QUEUE = SERVER / "catalog_dedupe_confirmed_decisions.template.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_REPORT = SERVER / "catalog_dedupe_confirmed_import_report.json"
ACCEPTED_DECISIONS = {"keep_drop_confirmed", "merge_duplicates", "deactivate_drops"}


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    out: list[int] = []
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool):
            out.append(item)
    return out


def _iter_items(raw_queue: Any) -> list[dict[str, Any]]:
    if isinstance(raw_queue, list):
        return [item for item in raw_queue if isinstance(item, dict)]
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("items"), list):
            return [item for item in raw_queue["items"] if isinstance(item, dict)]
        if isinstance(raw_queue.get("dedupe_decision_template"), dict):
            return [raw_queue["dedupe_decision_template"]]
        if raw_queue.get("keep_catalog_index") is not None and raw_queue.get("drop_catalog_indexes") is not None:
            return [raw_queue]
    raise SystemExit("queue must contain items, a list of decisions, or one dedupe decision object")


def _catalog_index(row: dict[str, Any], row_index: int) -> int:
    value = row.get("catalog_index")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return row_index


def import_decisions(
    review_queue: dict[str, Any] | list[Any],
    seed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_seed = [dict(row) for row in seed_rows if isinstance(row, dict)]
    by_catalog_index = {
        _catalog_index(row, index): index
        for index, row in enumerate(normalized_seed)
    }
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    touched_drop_indexes: set[int] = set()

    for item in _iter_items(review_queue):
        keep_index = item.get("keep_catalog_index")
        drop_indexes = _int_list(item.get("drop_catalog_indexes"))
        base = {
            "key_type": item.get("key_type"),
            "key": item.get("key"),
            "keep_catalog_index": keep_index,
            "drop_catalog_indexes": drop_indexes,
        }
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue
        decision = str(item.get("decision") or "").strip()
        if decision not in ACCEPTED_DECISIONS:
            skipped.append({**base, "reason": "unsupported_decision", "decision": decision})
            continue
        if not isinstance(keep_index, int) or isinstance(keep_index, bool):
            skipped.append({**base, "reason": "keep_catalog_index_missing"})
            continue
        if not drop_indexes:
            skipped.append({**base, "reason": "drop_catalog_indexes_missing"})
            continue
        keep_row_index = by_catalog_index.get(keep_index)
        if keep_row_index is None:
            skipped.append({**base, "reason": "keep_catalog_index_not_found"})
            continue
        missing_drops = [catalog_index for catalog_index in drop_indexes if catalog_index not in by_catalog_index]
        if missing_drops:
            skipped.append({**base, "reason": "drop_catalog_index_not_found", "missing_drops": missing_drops})
            continue
        if keep_index in drop_indexes:
            skipped.append({**base, "reason": "keep_catalog_index_in_drop_list"})
            continue

        changed_drop_indexes: list[int] = []
        for drop_index in drop_indexes:
            row_index = by_catalog_index[drop_index]
            if row_index in touched_drop_indexes:
                skipped.append({**base, "reason": "drop_catalog_index_already_touched", "drop_catalog_index": drop_index})
                continue
            row = normalized_seed[row_index]
            existing_active = row.get("is_active", True)
            if existing_active is False or existing_active == 0:
                skipped.append({**base, "reason": "drop_row_already_inactive", "drop_catalog_index": drop_index})
                continue
            row["is_active"] = False
            row["dedupe_keep_catalog_index"] = keep_index
            if item.get("manual_note"):
                row["dedupe_manual_note"] = item.get("manual_note")
            touched_drop_indexes.add(row_index)
            changed_drop_indexes.append(drop_index)

        if changed_drop_indexes:
            updated.append(
                {
                    **base,
                    "decision": decision,
                    "deactivated_catalog_indexes": changed_drop_indexes,
                    "keep_name_ko": normalized_seed[keep_row_index].get("name_ko"),
                }
            )
        else:
            skipped.append({**base, "reason": "no_change"})

    return {"seed_rows": normalized_seed, "updated": updated, "skipped": skipped}


def _load_seed(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or an object with items")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not args.queue.exists():
        empty_report = {
            "write": args.write,
            "queue": str(args.queue),
            "updated_rows": 0,
            "skipped_rows": 0,
            "updated_decisions": 0,
            "skipped_decisions": 0,
            "updated": [],
            "skipped_sample": [],
            "note": f"No confirmed dedupe queue found. Copy {FALLBACK_QUEUE.name} to {args.queue.name} after manual review.",
        }
        args.report.write_text(json.dumps(empty_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: empty_report[key] for key in ("updated_decisions", "skipped_decisions", "queue", "write")}, ensure_ascii=False, indent=2))
        return 0

    review_queue = json.loads(args.queue.read_text(encoding="utf-8-sig"))
    seed_rows = _load_seed(args.seed)
    result = import_decisions(review_queue, seed_rows)
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])
    report = {
        "write": args.write,
        "queue": str(args.queue),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "updated_decisions": len(result["updated"]),
        "skipped_decisions": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and result["updated"]:
        args.seed.write_text(json.dumps(result["seed_rows"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("updated_decisions", "skipped_decisions", "queue", "write")}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Confirm keep/drop decisions, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
