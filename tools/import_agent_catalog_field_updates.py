from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from validate_agent_catalog_field_updates import iter_input_files, load_json, validate_payload
except ImportError:
    from tools.validate_agent_catalog_field_updates import iter_input_files, load_json, validate_payload

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_META = ROOT / "data" / "catalog_public_meta.json"
DEFAULT_INCOMING = ROOT / "data" / "intake" / "field_updates" / "incoming"
DEFAULT_PROCESSED = ROOT / "data" / "intake" / "field_updates" / "processed"
DEFAULT_REPORT = ROOT / "server" / "agent_catalog_field_update_import_report.json"


def load_catalog(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path}: expected public catalog object with items array")
    return payload


def build_index(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexes: dict[int, dict[str, Any]] = {}
    for item in items:
        catalog_index = item.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            indexes[catalog_index] = item
    return indexes


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def import_payloads(
    catalog: dict[str, Any],
    payloads: list[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    items = [item for item in catalog.get("items", []) if isinstance(item, dict)]
    by_index = build_index(items)
    updated_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []

    for path, payload in payloads:
        for update_index, update in enumerate(payload.get("updates", [])):
            if not isinstance(update, dict):
                skipped_rows.append({"path": str(path), "update_index": update_index, "reason": "update_not_object"})
                continue
            catalog_index = update.get("catalog_index")
            field = str(update.get("field") or "").strip()
            row = by_index.get(catalog_index)
            if row is None:
                skipped_rows.append(
                    {
                        "path": str(path),
                        "update_index": update_index,
                        "catalog_index": catalog_index,
                        "field": field,
                        "reason": "catalog_index_not_found",
                    }
                )
                continue
            confidence = str(update.get("confidence") or "").strip()
            if confidence != "confirmed":
                skipped_rows.append(
                    {
                        "path": str(path),
                        "update_index": update_index,
                        "catalog_index": catalog_index,
                        "field": field,
                        "reason": "confidence_not_confirmed",
                        "confidence": confidence,
                    }
                )
                continue
            existing = row.get(field)
            if present(existing):
                skipped_rows.append(
                    {
                        "path": str(path),
                        "update_index": update_index,
                        "catalog_index": catalog_index,
                        "field": field,
                        "reason": "field_already_present",
                        "existing": existing,
                    }
                )
                continue
            value = clean_value(update.get("value"))
            if not present(value):
                skipped_rows.append(
                    {
                        "path": str(path),
                        "update_index": update_index,
                        "catalog_index": catalog_index,
                        "field": field,
                        "reason": "empty_value",
                    }
                )
                continue
            row[field] = value
            updated_rows.append(
                {
                    "path": str(path),
                    "update_index": update_index,
                    "catalog_index": catalog_index,
                    "field": field,
                    "name_ko": row.get("name_ko"),
                    "before": existing,
                    "after": value,
                    "evidence": update.get("evidence") or [],
                }
            )

    updated_catalog = dict(catalog)
    updated_catalog["items"] = items
    meta = dict(updated_catalog.get("meta") or {})
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    meta["generated_at"] = now
    meta["row_count"] = len(items)
    meta["total_items"] = len(items)
    updated_catalog["meta"] = meta
    updated_catalog["total_items"] = len(items)
    return {"catalog": updated_catalog, "updated_rows": updated_rows, "skipped_rows": skipped_rows}


def load_validated_payloads(
    paths: list[Path],
    *,
    catalog: dict[str, Any] | None = None,
) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    payloads: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    catalog_rows = build_index([item for item in (catalog or {}).get("items", []) if isinstance(item, dict)]) if catalog else None
    for path in iter_input_files(paths):
        payload = load_json(path)
        payload_errors, _summary = validate_payload(path, payload, catalog_rows=catalog_rows)
        if payload_errors:
            errors.extend(f"{path}: {error}" for error in payload_errors)
            continue
        if isinstance(payload, dict):
            payloads.append((path, payload))
    return payloads, errors


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def build_meta(catalog: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in catalog.get("items", []) if isinstance(item, dict)]
    existing_fields = list((catalog.get("meta") or {}).get("fields") or [])
    seen = set(existing_fields)
    fields = existing_fields + [
        field
        for field in sorted({key for item in items for key in item})
        if field not in seen
    ]
    return {
        "schema_version": 1,
        "generated_at": (catalog.get("meta") or {}).get("generated_at"),
        "source": "data/catalog_public.json",
        "row_count": len(items),
        "fields": fields,
        "missing": {field: sum(1 for item in items if item.get(field) in (None, "")) for field in fields},
        "privacy": {
            "contains_user_accounts": False,
            "contains_local_folders": False,
            "contains_private_memos": False,
            "contains_device_profiles": False,
            "contains_server_tokens": False,
        },
        "total_items": len(items),
    }


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


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
        moved.append(display_path(target))
    return moved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import validated catalog field updates into data/catalog_public.json."
    )
    parser.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_INCOMING])
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--meta", type=Path, default=DEFAULT_META)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-move-processed", action="store_true")
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    payloads, errors = load_validated_payloads(args.paths, catalog=catalog)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    result = import_payloads(catalog, payloads)
    updated_catalog = result["catalog"]
    report = {
        "write": args.write,
        "input_files": [display_path(path) for path, _payload in payloads],
        "input_updates": sum(len(payload.get("updates", [])) for _path, payload in payloads),
        "updated_rows": len(result["updated_rows"]),
        "skipped_rows": len(result["skipped_rows"]),
        "catalog_rows": len(updated_catalog["items"]),
        "updated_sample": result["updated_rows"][:50],
        "skipped_sample": result["skipped_rows"][:50],
        "processed_files": [],
    }

    if args.write:
        write_json(args.catalog, updated_catalog, compact=True)
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
