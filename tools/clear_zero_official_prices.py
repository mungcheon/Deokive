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
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "zero_official_price_cleanup_report.json"

ZERO_PRICE_PRIZE_TERMS = (
    "ラストワン",
    "last one",
    "라스트원",
    "ダブルチャンス",
    "double chance",
    "더블찬스",
)


def _zero_price_prize_row(row: dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("name_ko", "name_ja", "name_en", "category", "series_name", "sub_series")
    ).lower()
    return any(term in text for term in ZERO_PRICE_PRIZE_TERMS)


def clear_zero_prices(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if row.get("official_price_jpy") != 0:
            continue
        if _zero_price_prize_row(row):
            continue
        row["official_price_jpy"] = None
        changes.append(
            {
                "row_index": index,
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "reason": "zero_is_not_a_valid_official_price_except_last_one_or_double_chance",
            }
        )
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise SystemExit(f"{args.input} must contain a JSON list")

    changes = clear_zero_prices(rows)
    report = {
        "write": args.write,
        "updated_rows": len(changes),
        "policy": "official_price_jpy must be a positive listed JPY price; use null when no official JPY price is known. Preserve 0 for Last One/Double Chance prize rows.",
        "changes": changes,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and changes:
        args.input.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "write": args.write,
                "updated_rows": len(changes),
                "report": str(args.report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.write:
        print("Dry run only. Re-run with --write to update the seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
