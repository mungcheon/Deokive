from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_QUEUE = DATA / "ichiban_variant_lineup_split_confirmed_public.json"
DEFAULT_TEMPLATE = DATA / "ichiban_variant_lineup_split_confirmed_template_public.json"
DEFAULT_REPORT = DATA / "ichiban_variant_lineup_split_import_report_public.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {"1", "true", "yes", "y", "confirmed"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_catalog(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise SystemExit(f"{path} must contain a JSON object with items")
    return payload


def _normalize_queue(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"items": payload}
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload
    if isinstance(payload, dict) and payload.get("source_catalog_index") is not None:
        return {"items": [payload]}
    raise SystemExit("queue must be a list, an object with items, or one split item")


def _find_by_catalog_index(rows: list[dict[str, Any]], catalog_index: Any) -> dict[str, Any] | None:
    try:
        wanted = int(catalog_index)
    except (TypeError, ValueError):
        return None
    for row in rows:
        try:
            if int(row.get("catalog_index")) == wanted:
                return row
        except (TypeError, ValueError):
            continue
    return None


def _max_catalog_index(rows: list[dict[str, Any]]) -> int:
    values: list[int] = []
    for row in rows:
        try:
            values.append(int(row.get("catalog_index")))
        except (TypeError, ValueError):
            continue
    return max(values, default=-1)


def _clean_variant(raw: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw, dict):
        return None, "variant_not_object"
    variant_name = _text(raw.get("variant_name"))
    character_name = _text(raw.get("character_name")) or "\uae30\ud0c0"
    if not variant_name:
        return None, "variant_name_missing"
    if len(variant_name) > 120:
        return None, "variant_name_too_long"
    if len(character_name) > 80:
        return None, "character_name_too_long"
    image_url = _text(raw.get("image_url"))
    local_image_path = _text(raw.get("local_image_path"))
    return {
        "variant_name": variant_name,
        "character_name": character_name,
        "image_url": image_url,
        "local_image_path": local_image_path,
    }, None


def _validate_variants(item: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    raw_variants = item.get("variants")
    if not isinstance(raw_variants, list) or not raw_variants:
        return [], "variants_missing"
    variants: list[dict[str, Any]] = []
    for raw_variant in raw_variants:
        variant, error = _clean_variant(raw_variant)
        if error:
            return [], error
        assert variant is not None
        variants.append(variant)
    names = [variant["variant_name"] for variant in variants]
    if len(set(names)) != len(names):
        return [], "duplicate_variant_name"
    expected_count = item.get("expected_variant_count")
    if isinstance(expected_count, int) and expected_count > 0 and len(variants) != expected_count:
        return [], "variant_count_mismatch"
    if not _confirmed(item.get("representative_image_ok")) and any(not variant["image_url"] for variant in variants):
        return [], "variant_image_missing_without_representative_image_ok"
    return variants, None


def _display_name(source_row: dict[str, Any], variant: dict[str, Any]) -> str:
    return " / ".join(
        part
        for part in (
            _text(source_row.get("series_name")),
            _text(source_row.get("sub_series")),
            variant["variant_name"],
            variant["character_name"],
        )
        if part
    )


def _variant_row(source_row: dict[str, Any], variant: dict[str, Any], catalog_index: int) -> dict[str, Any]:
    row = deepcopy(source_row)
    row["catalog_index"] = catalog_index
    row["name_ko"] = _display_name(source_row, variant)
    row["name_ja"] = f"{_text(source_row.get('sub_series'))} {variant['variant_name']}".strip()
    row["character_name"] = variant["character_name"]
    if variant["image_url"]:
        row["image_url"] = variant["image_url"]
        if variant["local_image_path"]:
            row["local_image_path"] = variant["local_image_path"]
        else:
            row.pop("local_image_path", None)
    row.pop("barcode", None)
    return row


def _refresh_meta(catalog: dict[str, Any]) -> None:
    rows = [row for row in catalog.get("items") or [] if isinstance(row, dict)]
    meta = catalog.setdefault("meta", {})
    fields = meta.get("fields") or []
    meta["generated_at"] = _now()
    meta["row_count"] = len(rows)
    catalog["total_items"] = len(rows)
    meta["total_items"] = len(rows)
    if fields:
        meta["missing"] = {field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields}


def import_splits(catalog: dict[str, Any], queue: dict[str, Any], *, write: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = catalog["items"]
    max_index = _max_catalog_index(rows)
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    existing_names = {_text(row.get("name_ko")) for row in rows}

    for item in queue.get("items") or []:
        if not isinstance(item, dict):
            continue
        source_index = item.get("source_catalog_index")
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({"source_catalog_index": source_index, "reason": "manual_confirmed_false"})
            continue
        source_row = _find_by_catalog_index(rows, source_index)
        if source_row is None:
            skipped.append({"source_catalog_index": source_index, "reason": "source_catalog_index_not_found"})
            continue
        if item.get("source_url") and _text(item.get("source_url")).rstrip("/") != _text(source_row.get("source_url")).rstrip("/"):
            skipped.append({"source_catalog_index": source_index, "reason": "source_url_mismatch"})
            continue
        variants, variant_error = _validate_variants(item)
        if variant_error:
            skipped.append({"source_catalog_index": source_index, "reason": variant_error})
            continue

        new_rows: list[dict[str, Any]] = []
        for offset, variant in enumerate(variants):
            target_index = int(source_row["catalog_index"]) if offset == 0 else max_index + 1
            if offset > 0:
                max_index += 1
            row = _variant_row(source_row, variant, target_index)
            if row["name_ko"] in existing_names and row["catalog_index"] != source_row.get("catalog_index"):
                skipped.append(
                    {
                        "source_catalog_index": source_index,
                        "variant_name": variant["variant_name"],
                        "reason": "variant_name_already_exists",
                    }
                )
                new_rows = []
                break
            new_rows.append(row)

        if not new_rows:
            continue
        if write:
            source_position = rows.index(source_row)
            rows[source_position] = new_rows[0]
            rows.extend(new_rows[1:])
            existing_names.update(row["name_ko"] for row in new_rows)
        applied.append(
            {
                "source_catalog_index": source_index,
                "created_or_updated_rows": len(new_rows),
                "updated_source_row": new_rows[0].get("catalog_index"),
                "created_catalog_indexes": [row.get("catalog_index") for row in new_rows[1:]],
                "variant_names": [variant["variant_name"] for variant in variants],
            }
        )

    if write and applied:
        _refresh_meta(catalog)
    return {
        "schema_version": 1,
        "scope": "ichiban_variant_lineup_split_import",
        "summary": {
            "write": write,
            "applied_items": len(applied),
            "skipped_items": len(skipped),
            "created_or_updated_rows": sum(int(item.get("created_or_updated_rows") or 0) for item in applied),
            "auto_apply_enabled": False,
        },
        "applied": applied,
        "skipped": skipped[:200],
    }


def _empty_report(queue_path: Path, write: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "scope": "ichiban_variant_lineup_split_import",
        "summary": {
            "write": write,
            "applied_items": 0,
            "skipped_items": 0,
            "created_or_updated_rows": 0,
            "auto_apply_enabled": False,
        },
        "applied": [],
        "skipped": [],
        "note": f"No confirmed queue found. Copy {DEFAULT_TEMPLATE.name} to {queue_path.name}, fill variants, and set manual_confirmed true.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not args.queue.exists():
        report = _empty_report(args.queue, args.write)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        return 0

    catalog = _load_catalog(args.catalog)
    queue = _normalize_queue(load_json(args.queue))
    report = import_splits(catalog, queue, write=args.write)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and report["summary"]["applied_items"]:
        args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write after reviewing the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
