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

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_REVIEW = DATA / "ichiban_kuji_prize_name_image_review_public.json"
DEFAULT_REPORT = DATA / "ichiban_kuji_prize_display_name_fix_public.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _should_apply(row: dict[str, Any]) -> bool:
    prize_rank = _text(row.get("prize_rank"))
    prize_item_name = _text(row.get("prize_item_name"))
    current = _text(row.get("display_name_ko"))
    expected = _text(row.get("expected_display_name_ko"))

    if not prize_rank or not prize_item_name or not current or not expected:
        return False
    if current == expected:
        return False
    if " - " not in expected:
        return False

    expected_tail = expected.split(" - ", 1)[1]
    if not expected_tail.startswith(prize_rank):
        return False

    return prize_item_name in expected_tail


def build_fix_report(
    catalog: dict[str, Any],
    review_report: dict[str, Any],
    *,
    write: bool = False,
) -> dict[str, Any]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog must contain an items list")

    by_index: dict[int, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            by_index[int(item.get("catalog_index"))] = item
        except (TypeError, ValueError):
            continue

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in review_report.get("review_rows", []):
        if not isinstance(row, dict):
            continue

        catalog_index = row.get("catalog_index")
        if not _should_apply(row):
            skipped.append(
                {
                    "catalog_index": catalog_index,
                    "reason": "not_a_safe_display_name_only_fix",
                }
            )
            continue

        try:
            catalog_index_int = int(catalog_index)
        except (TypeError, ValueError):
            skipped.append({"catalog_index": catalog_index, "reason": "invalid_catalog_index"})
            continue

        item = by_index.get(catalog_index_int)
        if item is None:
            skipped.append({"catalog_index": catalog_index_int, "reason": "catalog_index_not_found"})
            continue

        expected = _text(row.get("expected_display_name_ko"))
        current_catalog_name = _text(item.get("name_ko"))
        if current_catalog_name == expected:
            skipped.append({"catalog_index": catalog_index_int, "reason": "already_fixed"})
            continue

        applied.append(
            {
                "catalog_index": catalog_index_int,
                "source_url": row.get("source_url"),
                "series_name": row.get("series_name"),
                "prize_rank": row.get("prize_rank"),
                "prize_item_name": row.get("prize_item_name"),
                "field_changes": {
                    "name_ko": {
                        "from": item.get("name_ko"),
                        "to": expected,
                    }
                },
            }
        )
        if write:
            item["name_ko"] = expected

    return {
        "schema_version": 1,
        "scope": "ichiban_kuji_prize_display_name_fix",
        "summary": {
            "review_rows": len([row for row in review_report.get("review_rows", []) if isinstance(row, dict)]),
            "applied_rows": len(applied),
            "skipped_rows": len(skipped),
            "write": write,
            "auto_apply_policy": "display_name_only_when_prize_rank_and_item_name_are_present",
        },
        "applied_rows": applied,
        "skipped_rows": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    catalog = _load_json(args.catalog)
    review_report = _load_json(args.review)
    report = build_fix_report(catalog, review_report, write=args.write)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write:
        args.catalog.write_text(
            json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
