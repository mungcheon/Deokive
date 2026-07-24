from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_CONFIRMATIONS = ROOT / "server" / "confirmed_source_urls.json"
DEFAULT_REPORT = ROOT / "server" / "confirmed_source_url_import_report.json"


def _key(row: dict[str, Any]) -> str:
    return str(row.get("catalog_index") or row.get("name_ko") or "")


def _source_url_from_confirmation(item: dict[str, Any]) -> str:
    return str(
        item.get("source_url")
        or item.get("manual_value")
        or item.get("candidate_source_url")
        or ""
    ).strip()


def _confirmation_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    return []


def _confirmation_row_key(item: dict[str, Any]) -> str:
    value = item.get("catalog_index")
    if value is None or value == "":
        value = item.get("row_index")
    return "" if value is None else str(value)


def _is_product_detail_url(source_url: str) -> bool:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return False

    lowered_parts = [part.lower() for part in path_parts]
    non_detail_terms = {
        "home",
        "search",
        "shop",
        "collections",
        "collection",
        "category",
        "categories",
        "products",
    }
    if len(path_parts) <= 1 and lowered_parts[0] in non_detail_terms:
        return False
    if lowered_parts[-1] in non_detail_terms:
        return False
    if parsed.query and lowered_parts[-1] in {"search", "shop"}:
        return False

    return True


def import_confirmed(rows: list[dict[str, Any]], confirmations: list[dict[str, Any]]) -> dict[str, Any]:
    by_index = {
        str(row.get("catalog_index")): row
        for row in rows
        if isinstance(row, dict) and row.get("catalog_index") is not None
    }
    changes: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in confirmations:
        catalog_index = _confirmation_row_key(item)
        manual_confirmed = item.get("manual_confirmed")
        if manual_confirmed is False:
            skipped.append(
                {
                    "catalog_index": catalog_index,
                    "reason": "manual_confirmation_false",
                }
            )
            continue
        row = by_index.get(catalog_index)
        if row is None and catalog_index.isdigit():
            row_index = int(catalog_index)
            if 0 <= row_index < len(rows) and isinstance(rows[row_index], dict):
                row = rows[row_index]
        if not row:
            skipped.append({"catalog_index": catalog_index, "reason": "row_not_found"})
            continue
        expected_image = str(item.get("image_url") or "")
        if expected_image and str(row.get("image_url") or "") != expected_image:
            skipped.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "reason": "image_url_mismatch",
                    "expected": expected_image,
                    "actual": row.get("image_url"),
                }
            )
            continue
        expected_name = str(item.get("name_ko") or "")
        if expected_name and str(row.get("name_ko") or "") != expected_name:
            skipped.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "reason": "name_mismatch",
                    "expected": expected_name,
                    "actual": row.get("name_ko"),
                }
            )
            continue
        source_url = _source_url_from_confirmation(item)
        if not source_url:
            skipped.append({"catalog_index": catalog_index, "name_ko": row.get("name_ko"), "reason": "missing_source_url"})
            continue
        if not _is_product_detail_url(source_url):
            skipped.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "reason": "source_url_not_product_detail",
                    "source_url": source_url,
                }
            )
            continue
        if row.get("source_url") == source_url:
            skipped.append({"catalog_index": catalog_index, "name_ko": row.get("name_ko"), "reason": "already_set"})
            continue
        current_source_url = str(item.get("current_source_url") or "").strip()
        if row.get("source_url") and row.get("source_url") != current_source_url:
            skipped.append({"catalog_index": catalog_index, "name_ko": row.get("name_ko"), "reason": "source_url_already_different"})
            continue
        row["source_url"] = source_url
        changes.append(
            {
                "catalog_index": catalog_index,
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "source_url": source_url,
                "evidence": item.get("evidence"),
            }
        )
    return {"changes": changes, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--confirmations", type=Path, default=DEFAULT_CONFIRMATIONS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8-sig"))
    confirmations_payload = json.loads(args.confirmations.read_text(encoding="utf-8-sig"))
    confirmations = _confirmation_items(confirmations_payload)
    if not isinstance(rows, list) or not confirmations:
        raise SystemExit("Input must be a JSON list and confirmations must be a JSON list or an object with items")
    result = import_confirmed(rows, confirmations)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "change_candidates": len(result["changes"]),
                "updated_rows": len(result["changes"]) if args.write else 0,
                "write": args.write,
                "changes": result["changes"],
                "skipped": result["skipped"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if args.write and result["changes"]:
        args.input.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "change_candidates": len(result["changes"]),
                "updated_rows": len(result["changes"]) if args.write else 0,
                "skipped": len(result["skipped"]),
                "report": str(args.report),
                "write": args.write,
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
