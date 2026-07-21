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
DEFAULT_QUEUE = SERVER / "catalog_deduplication_confirmed_rows.json"
FALLBACK_QUEUE = SERVER / "catalog_deduplication_confirmed_rows.template.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_REPORT = SERVER / "catalog_deduplication_confirmed_import_report.json"

VALID_DECISIONS = {"drop_duplicates", "merge_duplicates", "remove_duplicate_rows"}


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool):
            result.append(item)
        elif str(item).strip().isdigit():
            result.append(int(str(item).strip()))
    return result


def _iter_items(raw_queue: Any) -> list[dict[str, Any]]:
    if isinstance(raw_queue, list):
        return [item for item in raw_queue if isinstance(item, dict)]
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("items"), list):
            return [item for item in raw_queue["items"] if isinstance(item, dict)]
        if isinstance(raw_queue.get("dedupe_decision_template"), dict):
            return [raw_queue["dedupe_decision_template"]]
        if raw_queue.get("keep_catalog_index") is not None:
            return [raw_queue]
    raise SystemExit("queue must contain items, a list of items, or one dedupe decision object")


def _catalog_index_map(seed_rows: list[dict[str, Any]]) -> dict[int, tuple[int, dict[str, Any]]]:
    mapping: dict[int, tuple[int, dict[str, Any]]] = {}
    for row_index, row in enumerate(seed_rows):
        catalog_index = row.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            mapping[catalog_index] = (row_index, row)
    return mapping


def _key_matches(row: dict[str, Any], key_type: Any, key: Any) -> bool:
    field = str(key_type or "").strip()
    if field not in {"barcode", "source_url", "image_url"}:
        return True
    expected = str(key or "").strip().rstrip("/")
    actual = str(row.get(field) or "").strip().rstrip("/")
    return bool(expected) and actual == expected


def import_rows(review_queue: dict[str, Any] | list[Any], seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_seed = [dict(row) for row in seed_rows if isinstance(row, dict)]
    by_catalog_index = _catalog_index_map(normalized_seed)
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    drop_catalog_indexes: set[int] = set()
    keep_catalog_indexes: set[int] = set()

    for item in _iter_items(review_queue):
        keep_catalog_index = item.get("keep_catalog_index")
        drop_indexes = _int_list(item.get("drop_catalog_indexes"))
        key_type = item.get("key_type")
        key = item.get("key")

        base = {
            "key_type": key_type,
            "key": key,
            "keep_catalog_index": keep_catalog_index,
            "drop_catalog_indexes": drop_indexes,
        }
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue
        if str(item.get("decision") or "").strip() not in VALID_DECISIONS:
            skipped.append({**base, "reason": "unsupported_decision"})
            continue
        if not _confirmed(item.get("same_sellable_product_confirmed")):
            skipped.append({**base, "reason": "same_sellable_product_not_confirmed"})
            continue
        if not isinstance(keep_catalog_index, int) or isinstance(keep_catalog_index, bool):
            skipped.append({**base, "reason": "invalid_keep_catalog_index"})
            continue
        if not drop_indexes:
            skipped.append({**base, "reason": "drop_catalog_indexes_missing"})
            continue
        if keep_catalog_index in drop_indexes:
            skipped.append({**base, "reason": "keep_catalog_index_in_drop_indexes"})
            continue
        if keep_catalog_index in drop_catalog_indexes:
            skipped.append({**base, "reason": "keep_row_already_marked_for_drop"})
            continue
        if keep_catalog_index not in by_catalog_index:
            skipped.append({**base, "reason": "keep_catalog_index_not_found"})
            continue

        missing_drops = [index for index in drop_indexes if index not in by_catalog_index]
        if missing_drops:
            skipped.append({**base, "reason": "drop_catalog_index_not_found", "missing_drop_catalog_indexes": missing_drops})
            continue
        overlapping_drops = [index for index in drop_indexes if index in drop_catalog_indexes or index in keep_catalog_indexes]
        if overlapping_drops:
            skipped.append({**base, "reason": "catalog_index_used_by_prior_decision", "overlapping_catalog_indexes": overlapping_drops})
            continue

        rows_to_check = [by_catalog_index[keep_catalog_index][1]] + [by_catalog_index[index][1] for index in drop_indexes]
        if not all(_key_matches(row, key_type, key) for row in rows_to_check):
            skipped.append({**base, "reason": "dedupe_key_mismatch"})
            continue

        keep_catalog_indexes.add(keep_catalog_index)
        for drop_index in drop_indexes:
            drop_catalog_indexes.add(drop_index)
            _, drop_row = by_catalog_index[drop_index]
            _, keep_row = by_catalog_index[keep_catalog_index]
            updated.append(
                {
                    "action": "drop_duplicate_row",
                    "keep_catalog_index": keep_catalog_index,
                    "drop_catalog_index": drop_index,
                    "key_type": key_type,
                    "key": key,
                    "keep_name_ko": keep_row.get("name_ko"),
                    "drop_name_ko": drop_row.get("name_ko"),
                    "manual_note": item.get("manual_note") or "",
                }
            )

    filtered_seed = [row for row in normalized_seed if row.get("catalog_index") not in drop_catalog_indexes]
    return {"seed_rows": filtered_seed, "updated": updated, "skipped": skipped}


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
            "updated": [],
            "skipped_sample": [],
            "note": f"No confirmed queue found. Copy {FALLBACK_QUEUE.name} to {args.queue.name} after manual review.",
        }
        args.report.write_text(json.dumps(empty_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: empty_report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
        return 0

    review_queue = json.loads(args.queue.read_text(encoding="utf-8-sig"))
    seed_rows = _load_seed(args.seed)
    result = import_rows(review_queue, seed_rows)
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])
    report = {
        "write": args.write,
        "queue": str(args.queue),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and result["updated"]:
        args.seed.write_text(json.dumps(result["seed_rows"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Confirm same sellable products, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
