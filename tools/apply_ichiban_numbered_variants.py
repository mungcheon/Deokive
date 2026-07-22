from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "data" / "ichiban_kuji_multi_variant_official_public.json"
DEFAULT_APPLY_REPORT = ROOT / "data" / "ichiban_kuji_numbered_variant_application_public.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--apply-report", type=Path, default=DEFAULT_APPLY_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit-prizes", type=int, default=0)
    parser.add_argument(
        "--choice",
        choices=["all", "selectable", "blind"],
        default="all",
        help="Filter by 1kuji choice text: all, selectable=選べる, blind=選べない.",
    )
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = catalog["items"]
    official = json.loads(args.report.read_text(encoding="utf-8"))

    split_ready = list(official.get("split_ready") or [])
    split_ready = [item for item in split_ready if _choice_matches(item, args.choice)]
    if args.limit_prizes:
        split_ready = split_ready[: args.limit_prizes]

    row_by_url_tier = _single_rows_by_url_tier(rows)
    max_catalog_index = max(
        (row.get("catalog_index") for row in rows if isinstance(row.get("catalog_index"), int)),
        default=-1,
    )

    updated_catalog_indexes: list[int] = []
    created_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    applied_prizes: list[dict[str, Any]] = []

    for item in split_ready:
        url = item.get("source_url")
        tier = item.get("tier")
        suggestions = item.get("suggested_variant_rows") or []
        if not isinstance(url, str) or not isinstance(tier, str) or len(suggestions) <= 1:
            skipped.append({"source_url": url, "tier": tier, "reason": "missing_url_tier_or_suggestions"})
            continue
        base_row = row_by_url_tier.get((url, tier))
        if base_row is None:
            skipped.append({"source_url": url, "tier": tier, "reason": "catalog_row_not_single_or_missing"})
            continue

        variant_rows: list[dict[str, Any]] = []
        for index, suggestion in enumerate(suggestions, start=1):
            if index == 1:
                _apply_variant_to_row(base_row, suggestion)
                updated_catalog_indexes.append(base_row.get("catalog_index"))
                variant_rows.append(_snapshot(base_row))
                continue

            max_catalog_index += 1
            new_row = dict(base_row)
            new_row["catalog_index"] = max_catalog_index
            _apply_variant_to_row(new_row, suggestion)
            new_row.pop("barcode", None)
            rows.append(new_row)
            created_rows.append(_snapshot(new_row))
            variant_rows.append(_snapshot(new_row))

        applied_prizes.append(
            {
                "source_url": url,
                "tier": tier,
                "official_name": item.get("official_name"),
                "official_variant_count": item.get("official_variant_count"),
                "choice_text": item.get("choice_text"),
                "updated_catalog_index": variant_rows[0].get("catalog_index") if variant_rows else None,
                "created_count": max(0, len(variant_rows) - 1),
                "variant_rows": variant_rows,
            }
        )

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if args.write:
        catalog["meta"]["generated_at"] = now
        catalog["meta"]["row_count"] = len(rows)
        catalog["meta"]["total_items"] = len(rows)
        catalog["meta"]["missing"] = _missing_by_field(rows, catalog["meta"].get("fields") or [])
        args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    apply_report = {
        "generated_at": now,
        "write": args.write,
        "choice": args.choice,
        "source_prizes_considered": len(split_ready),
        "applied_prizes": len(applied_prizes),
        "updated_existing_rows": len(updated_catalog_indexes),
        "created_variant_rows": len(created_rows),
        "skipped": skipped,
        "applied": applied_prizes,
    }
    args.apply_report.write_text(json.dumps(apply_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "write": args.write,
                "choice": args.choice,
                "source_prizes_considered": len(split_ready),
                "applied_prizes": len(applied_prizes),
                "updated_existing_rows": len(updated_catalog_indexes),
                "created_variant_rows": len(created_rows),
                "skipped": len(skipped),
                "rows_after": len(rows),
                "apply_report": str(args.apply_report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _choice_matches(item: dict[str, Any], choice: str) -> bool:
    if choice == "all":
        return True
    if choice == "selectable":
        return item.get("choice_text") == "選べる"
    if choice == "blind":
        return item.get("choice_text") == "選べない"
    return True


def _single_rows_by_url_tier(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        url = row.get("source_url")
        tier = row.get("sub_series")
        if not isinstance(url, str) or not isinstance(tier, str):
            continue
        if not url.startswith("https://1kuji.com/products/"):
            continue
        grouped.setdefault((url, tier), []).append(row)
    return {key: values[0] for key, values in grouped.items() if len(values) == 1}


def _apply_variant_to_row(row: dict[str, Any], suggestion: dict[str, Any]) -> None:
    variant_name = suggestion["name_ja"]
    row["name_ja"] = variant_name
    row["name_ko"] = _display_name(row, variant_name)
    row["sub_series"] = suggestion.get("sub_series") or row.get("sub_series")
    row["image_url"] = suggestion.get("image_url") or row.get("image_url")
    row.pop("local_image_path", None)


def _display_name(row: dict[str, Any], variant_name: str) -> str:
    series_name = str(row.get("series_name") or "").strip()
    if series_name:
        return f"{series_name} - {variant_name}"
    current = str(row.get("name_ko") or "").strip()
    if " - " in current:
        return f"{current.rsplit(' - ', 1)[0]} - {variant_name}"
    return variant_name


def _missing_by_field(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    return {field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields}


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "series_name": row.get("series_name"),
        "sub_series": row.get("sub_series"),
        "image_url": row.get("image_url"),
        "local_image_path": row.get("local_image_path"),
        "source_url": row.get("source_url"),
    }


if __name__ == "__main__":
    main()
