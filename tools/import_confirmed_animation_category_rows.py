from __future__ import annotations

import argparse
import json
import re
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
DEFAULT_QUEUE = SERVER / "animation_category_confirmed_rows.json"
FALLBACK_QUEUE = SERVER / "animation_category_confirmed_rows.template.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_REPORT = SERVER / "animation_category_confirmed_import_report.json"


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _clean_category(value: Any) -> tuple[str | None, str | None]:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return None, "category_missing"
    if len(text) > 60:
        return None, "category_too_long"
    if re.search(r"https?://", text, flags=re.I):
        return None, "category_contains_url"
    return text, None


def _iter_items(raw_queue: Any) -> list[dict[str, Any]]:
    if isinstance(raw_queue, list):
        return [item for item in raw_queue if isinstance(item, dict)]
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("items"), list):
            return [item for item in raw_queue["items"] if isinstance(item, dict)]
        if isinstance(raw_queue.get("category_mapping_template"), dict):
            return [raw_queue["category_mapping_template"]]
        if raw_queue.get("source_category") or raw_queue.get("target_category"):
            return [raw_queue]
    raise SystemExit("queue must contain items, a list of items, or one category mapping object")


def _count_source_category(seed_rows: list[dict[str, Any]], source_category: str) -> int:
    return sum(1 for row in seed_rows if row.get("category") == source_category)


def _item_name(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "name_en", "series_name", "sub_series")
        if str(row.get(field) or "").strip()
    )


def _match_keywords(item: dict[str, Any]) -> list[str]:
    raw_keywords = item.get("match_keywords")
    if not isinstance(raw_keywords, list):
        return []
    return [str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()]


def _matches_keywords(row: dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = _item_name(row).casefold()
    return any(keyword.casefold() in text for keyword in keywords)


def _matching_row_indexes(
    seed_rows: list[dict[str, Any]],
    source_category: str,
    keywords: list[str],
) -> list[int]:
    return [
        index
        for index, row in enumerate(seed_rows)
        if row.get("category") == source_category and _matches_keywords(row, keywords)
    ]


def _expected_row_count(item: dict[str, Any]) -> int | None:
    for field in ("expected_update_rows", "matched_catalog_row_count", "affected_catalog_rows"):
        value = item.get(field)
        if isinstance(value, int) and value >= 0:
            return value
    return None


def import_rows(
    review_queue: dict[str, Any] | list[Any],
    seed_rows: list[dict[str, Any]],
    *,
    allow_count_mismatch: bool = False,
) -> dict[str, Any]:
    normalized_seed = [dict(row) for row in seed_rows if isinstance(row, dict)]
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen_mappings: set[tuple[str, tuple[str, ...]]] = set()

    for item in _iter_items(review_queue):
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({"source_category": item.get("source_category"), "reason": "manual_confirmed_false"})
            continue

        source_category, source_error = _clean_category(item.get("source_category"))
        target_category, target_error = _clean_category(item.get("target_category"))
        if source_error or target_error:
            skipped.append(
                {
                    "source_category": item.get("source_category"),
                    "target_category": item.get("target_category"),
                    "reason": source_error or target_error,
                }
            )
            continue
        if source_category == target_category:
            skipped.append({"source_category": source_category, "target_category": target_category, "reason": "no_change"})
            continue
        keywords = _match_keywords(item)
        mapping_key = (source_category, tuple(keyword.casefold() for keyword in keywords))
        if mapping_key in seen_mappings:
            skipped.append({"source_category": source_category, "target_category": target_category, "reason": "duplicate_source_mapping"})
            continue
        seen_mappings.add(mapping_key)

        matched_indexes = _matching_row_indexes(normalized_seed, source_category, keywords)
        matched_rows = len(matched_indexes)
        expected_rows = _expected_row_count(item)
        if expected_rows is not None and expected_rows != matched_rows and not allow_count_mismatch:
            skipped.append(
                {
                    "source_category": source_category,
                    "target_category": target_category,
                    "reason": "affected_catalog_rows_mismatch",
                    "expected_rows": expected_rows,
                    "matched_rows": matched_rows,
                }
            )
            continue
        if matched_rows == 0:
            skipped.append({"source_category": source_category, "target_category": target_category, "reason": "source_category_not_found"})
            continue

        for index in matched_indexes:
            row = normalized_seed[index]
            row["category"] = target_category
            updated.append(
                {
                    "row_index": index,
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_category": source_category,
                    "target_category": target_category,
                    "target_family": item.get("target_family"),
                    "folder_name": item.get("folder_name"),
                    "folder_color_hex": item.get("folder_color_hex"),
                    "folder_icon_key": item.get("folder_icon_key"),
                    "match_keywords": keywords,
                }
            )

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
    parser.add_argument(
        "--allow-count-mismatch",
        action="store_true",
        help="Allow a confirmed source category mapping even if affected_catalog_rows no longer matches the seed.",
    )
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
    result = import_rows(review_queue, seed_rows, allow_count_mismatch=args.allow_count_mismatch)
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])
    report = {
        "write": args.write,
        "queue": str(args.queue),
        "allow_count_mismatch": args.allow_count_mismatch,
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
        print("Dry run only. Copy the template, confirm exact category mappings, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
