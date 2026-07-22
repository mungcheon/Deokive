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
DEFAULT_CANDIDATES = DATA / "ichiban_kuji_prize_name_image_patch_candidates_public.json"
DEFAULT_REPORT = DATA / "ichiban_kuji_prize_name_image_patch_import_dry_run_public.json"
PATCH_FIELDS = ("name_ko", "name_ja", "sub_series", "image_url")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _confirmed_patch_rows(candidate_report: dict[str, Any]) -> list[dict[str, Any]]:
    confirmed: list[dict[str, Any]] = []
    for row in candidate_report.get("candidates", []):
        if not isinstance(row, dict) or row.get("manual_confirmed") is not True:
            continue
        template = row.get("catalog_patch_template")
        if not isinstance(template, dict) or template.get("manual_confirmed") is not True:
            continue
        confirmed.append(row)
    return confirmed


def build_import_report(catalog: dict[str, Any], candidate_report: dict[str, Any], *, write: bool = False) -> dict[str, Any]:
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

    confirmed_rows = _confirmed_patch_rows(candidate_report)
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in confirmed_rows:
        template = row["catalog_patch_template"]
        try:
            catalog_index = int(template.get("catalog_index"))
        except (TypeError, ValueError):
            skipped.append({"catalog_index": template.get("catalog_index"), "reason": "invalid_catalog_index"})
            continue

        item = by_index.get(catalog_index)
        if item is None:
            skipped.append({"catalog_index": catalog_index, "reason": "catalog_index_not_found"})
            continue

        field_changes: dict[str, dict[str, Any]] = {}
        for field in PATCH_FIELDS:
            new_value = template.get(field)
            if new_value in (None, ""):
                continue
            old_value = item.get(field)
            if old_value == new_value:
                continue
            field_changes[field] = {"from": old_value, "to": new_value}
            if write:
                item[field] = new_value

        if not field_changes:
            skipped.append({"catalog_index": catalog_index, "reason": "no_field_changes"})
            continue

        applied.append(
            {
                "catalog_index": catalog_index,
                "source_url": template.get("evidence_url") or row.get("source_url"),
                "field_changes": field_changes,
            }
        )

    return {
        "schema_version": 1,
        "scope": "ichiban_kuji_prize_name_image_patch_import",
        "summary": {
            "candidate_rows": len(candidate_report.get("candidates", [])),
            "confirmed_rows": len(confirmed_rows),
            "applied_rows": len(applied),
            "skipped_rows": len(skipped),
            "write": write,
            "auto_apply_enabled": False,
        },
        "applied_rows": applied,
        "skipped_rows": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    catalog = _load_json(args.catalog)
    candidate_report = _load_json(args.candidates)
    report = build_import_report(catalog, candidate_report, write=args.write)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write:
        args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
