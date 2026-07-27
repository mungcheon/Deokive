from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from validate_agent_goods_intake import iter_input_files, load_json, validate_payload
except ImportError:
    from tools.validate_agent_goods_intake import iter_input_files, load_json, validate_payload


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_META = ROOT / "data" / "catalog_public_meta.json"
DEFAULT_INCOMING = ROOT / "data" / "intake" / "incoming"
DEFAULT_PROCESSED = ROOT / "data" / "intake" / "processed"
DEFAULT_REPORT = ROOT / "server" / "agent_goods_intake_import_report.json"

CATALOG_FIELDS = [
    "catalog_index",
    "name_ko",
    "name_ja",
    "name_en",
    "category",
    "character_name",
    "affiliation",
    "series_name",
    "sub_series",
    "official_price_jpy",
    "official_price_krw",
    "barcode",
    "image_url",
    "local_image_path",
    "source_url",
    "source_store",
    "release_date",
]


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).replace("\u3000", " ")).strip()
    return text or None


def normalize_key_part(value: Any) -> str:
    return clean_text(value).casefold() if clean_text(value) else ""


def catalog_identity(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        normalize_key_part(row.get("source_store")),
        normalize_key_part(row.get("name_ko") or row.get("name_ja") or row.get("name_en")),
        normalize_key_part(row.get("category")),
        normalize_key_part(row.get("character_name")),
        normalize_key_part(row.get("series_name")),
        normalize_key_part(row.get("sub_series")),
    )


def load_catalog(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path}: expected public catalog object with items array")
    return payload


def next_catalog_index(items: list[dict[str, Any]]) -> int:
    indexes = [item.get("catalog_index") for item in items]
    numeric = [value for value in indexes if isinstance(value, int) and not isinstance(value, bool)]
    return max(numeric, default=-1) + 1


def intake_item_to_catalog_row(item: dict[str, Any], catalog_index: int) -> dict[str, Any]:
    price_currency = item.get("official_price_currency")
    official_price = item.get("official_price")
    official_price_jpy = item.get("official_price_jpy")
    official_price_krw = None

    if price_currency == "JPY" and isinstance(official_price, int):
        official_price_jpy = official_price
    elif price_currency == "KRW" and isinstance(official_price, int):
        official_price_krw = official_price

    row: dict[str, Any] = {
        "catalog_index": catalog_index,
        "name_ko": clean_text(item.get("name_ko")) or clean_text(item.get("display_name")),
        "name_ja": clean_text(item.get("name_ja")),
        "name_en": clean_text(item.get("name_en")),
        "category": clean_text(item.get("category")),
        "character_name": clean_text(item.get("character_name")) or "",
        "affiliation": clean_text(item.get("affiliation")) or clean_text(item.get("series_name")),
        "series_name": clean_text(item.get("series_name")),
        "sub_series": clean_text(item.get("sub_series")),
        "official_price_jpy": official_price_jpy,
        "official_price_krw": official_price_krw,
        "barcode": clean_text(item.get("barcode")),
        "image_url": clean_text(item.get("image_url")),
        "local_image_path": None,
        "source_url": clean_text(item.get("source_url")),
        "source_store": clean_text(item.get("source_store")),
        "release_date": clean_text(item.get("release_date")),
    }
    return {field: row.get(field) for field in CATALOG_FIELDS}


def build_existing_indexes(items: list[dict[str, Any]]) -> dict[str, set[Any]]:
    source_urls: set[str] = set()
    barcodes: set[str] = set()
    identities: set[tuple[str, ...]] = set()
    for row in items:
        source_url = clean_text(row.get("source_url"))
        if source_url:
            source_urls.add(source_url.rstrip("/"))
        barcode = clean_text(row.get("barcode"))
        if barcode:
            barcodes.add(barcode)
        identities.add(catalog_identity(row))
    return {
        "source_urls": source_urls,
        "barcodes": barcodes,
        "identities": identities,
    }


def duplicate_reason(row: dict[str, Any], indexes: dict[str, set[Any]]) -> str | None:
    source_url = clean_text(row.get("source_url"))
    if source_url and source_url.rstrip("/") in indexes["source_urls"]:
        return "source_url_duplicate"
    barcode = clean_text(row.get("barcode"))
    if barcode and barcode in indexes["barcodes"]:
        return "barcode_duplicate"
    identity = catalog_identity(row)
    if identity in indexes["identities"]:
        return "catalog_identity_duplicate"
    return None


def register_row(row: dict[str, Any], indexes: dict[str, set[Any]]) -> None:
    source_url = clean_text(row.get("source_url"))
    if source_url:
        indexes["source_urls"].add(source_url.rstrip("/"))
    barcode = clean_text(row.get("barcode"))
    if barcode:
        indexes["barcodes"].add(barcode)
    indexes["identities"].add(catalog_identity(row))


def import_payloads(
    catalog: dict[str, Any],
    payloads: list[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    items = [item for item in catalog["items"] if isinstance(item, dict)]
    indexes = build_existing_indexes(items)
    next_index = next_catalog_index(items)
    added_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []

    for path, payload in payloads:
        for item_index, item in enumerate(payload.get("items", [])):
            if not isinstance(item, dict):
                skipped_rows.append(
                    {"path": str(path), "item_index": item_index, "reason": "item_not_object"}
                )
                continue
            row = intake_item_to_catalog_row(item, next_index)
            reason = duplicate_reason(row, indexes)
            if reason:
                skipped_rows.append(
                    {
                        "path": str(path),
                        "item_index": item_index,
                        "external_id": item.get("external_id"),
                        "name": row.get("name_ko") or row.get("name_ja") or row.get("name_en"),
                        "reason": reason,
                    }
                )
                continue
            register_row(row, indexes)
            items.append(row)
            added_rows.append(row)
            next_index += 1

    updated_catalog = dict(catalog)
    updated_catalog["items"] = items
    updated_catalog["total_items"] = len(items)
    meta = dict(updated_catalog.get("meta") or {})
    meta["total_items"] = len(items)
    meta["row_count"] = len(items)
    meta["generated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    updated_catalog["meta"] = meta

    return {
        "catalog": updated_catalog,
        "added_rows": added_rows,
        "skipped_rows": skipped_rows,
    }


def build_meta(catalog: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in catalog.get("items", []) if isinstance(item, dict)]
    missing: dict[str, int] = {}
    for field in CATALOG_FIELDS:
        missing[field] = sum(1 for item in items if item.get(field) in (None, ""))
    return {
        "schema_version": 1,
        "generated_at": catalog.get("meta", {}).get("generated_at"),
        "source": "data/catalog_public.json",
        "row_count": len(items),
        "fields": CATALOG_FIELDS,
        "missing": missing,
        "privacy": {
            "contains_user_accounts": False,
            "contains_local_folders": False,
            "contains_private_memos": False,
            "contains_device_profiles": False,
            "contains_server_tokens": False,
        },
        "total_items": len(items),
    }


def load_validated_payloads(paths: list[Path]) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    payloads: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    for path in iter_input_files(paths):
        payload = load_json(path)
        payload_errors, _summary = validate_payload(path, payload)
        if payload_errors:
            errors.extend(f"{path}: {error}" for error in payload_errors)
            continue
        if isinstance(payload, dict):
            payloads.append((path, payload))
    return payloads, errors


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def move_processed(paths: list[Path], processed_dir: Path) -> list[str]:
    moved: list[str] = []
    processed_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.parent.resolve() != DEFAULT_INCOMING.resolve():
            continue
        target = processed_dir / path.name
        if target.exists():
            target = processed_dir / f"{path.stem}.{dt.datetime.now().strftime('%Y%m%d%H%M%S')}{path.suffix}"
        shutil.move(str(path), str(target))
        moved.append(str(target.relative_to(ROOT)))
    return moved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import validated agent goods intake files into data/catalog_public.json."
    )
    parser.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_INCOMING])
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--meta", type=Path, default=DEFAULT_META)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-move-processed", action="store_true")
    args = parser.parse_args()

    payloads, errors = load_validated_payloads(args.paths)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    catalog = load_catalog(args.catalog)
    result = import_payloads(catalog, payloads)
    updated_catalog = result["catalog"]
    report = {
        "write": args.write,
        "input_files": [str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path) for path, _payload in payloads],
        "input_items": sum(len(payload.get("items", [])) for _path, payload in payloads),
        "added_rows": len(result["added_rows"]),
        "skipped_rows": len(result["skipped_rows"]),
        "catalog_rows_before": len(catalog["items"]),
        "catalog_rows_after": len(updated_catalog["items"]),
        "added_sample": result["added_rows"][:20],
        "skipped_sample": result["skipped_rows"][:50],
        "processed_files": [],
    }

    if args.write:
        write_json(args.catalog, updated_catalog)
        write_json(args.meta, build_meta(updated_catalog))
        if not args.no_move_processed:
            report["processed_files"] = move_processed([path for path, _payload in payloads], args.processed_dir)

    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to update the public catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
