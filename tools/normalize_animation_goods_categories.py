from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from catalog_normalize import normalize_row
from catalog_quality_report import source_group

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "animation_goods_category_normalize_report.json"

CATEGORY_NORMALIZATION = {
    "클리어파일": "문구",
    "카드": "문구",
    "미니어처": "피규어",
    "트레이딩 카드": "문구",
    "스티커": "문구",
    "클리어 보틀": "생활잡화",
    "파우치": "가방",
    "기타 굿즈": "액세서리",
}


def normalize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if source_group(row.get("source_store")) != "animation_goods":
            continue
        old_category = str(row.get("category") or "").strip()
        new_category = CATEGORY_NORMALIZATION.get(old_category)
        if not new_category or new_category == old_category:
            continue

        changed: dict[str, Any] = {"category": {"from": old_category, "to": new_category}}
        if row.get("sub_series") in (None, ""):
            row["sub_series"] = old_category
            changed["sub_series"] = {"from": None, "to": old_category}
        row["category"] = new_category
        normalize_row(row)
        changes.append(
            {
                "row_index": index,
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "changed": changed,
            }
        )
    return changes


def _load_payload(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload, [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return payload, [row for row in payload if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or an object with items")


def _missing_by_field(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    return {field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields}


def _write_payload(path: Path, payload: Any, rows: list[dict[str, Any]]) -> None:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        payload = dict(payload)
        meta = dict(payload.get("meta") or {})
        fields = meta.get("fields")
        payload["items"] = rows
        meta["generated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        meta["row_count"] = len(rows)
        meta["total_items"] = len(rows)
        if isinstance(fields, list):
            meta["missing"] = _missing_by_field(rows, [str(field) for field in fields])
        payload["meta"] = meta
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        return
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    payload, rows = _load_payload(args.input)

    changes = normalize(rows)
    report = {
        "write": args.write,
        "updated_rows": len(changes),
        "policy": "Only animation_goods rows are normalized. Existing sub_series is preserved; empty sub_series receives the old category.",
        "normalization": CATEGORY_NORMALIZATION,
        "changes": changes,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and changes:
        _write_payload(args.input, payload, rows)

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
