from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from validate_agent_catalog_image_updates import iter_input_files, load_json, validate_payload
except ImportError:
    from tools.validate_agent_catalog_image_updates import iter_input_files, load_json, validate_payload

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_META = ROOT / "data" / "catalog_public_meta.json"
DEFAULT_INCOMING = ROOT / "data" / "intake" / "image_updates" / "incoming"
DEFAULT_PROCESSED = ROOT / "data" / "intake" / "image_updates" / "processed"
DEFAULT_REPORT = ROOT / "server" / "agent_catalog_image_update_import_report.json"


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
            row = by_index.get(catalog_index)
            if not row:
                skipped_rows.append(
                    {
                        "path": str(path),
                        "update_index": update_index,
                        "catalog_index": catalog_index,
                        "reason": "catalog_index_not_found",
                    }
                )
                continue
            before = {
                "image_url": row.get("image_url"),
                "source_url": row.get("source_url"),
                "local_image_path": row.get("local_image_path"),
            }
            if row.get("image_url"):
                skipped_rows.append(
                    {
                        "path": str(path),
                        "update_index": update_index,
                        "catalog_index": catalog_index,
                        "reason": "image_url_already_present",
                    }
                )
                continue
            row["image_url"] = clean_text(update.get("image_url"))
            row["local_image_path"] = None
            if clean_text(update.get("source_url")):
                row["source_url"] = clean_text(update.get("source_url"))
            updated_rows.append(
                {
                    "path": str(path),
                    "update_index": update_index,
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "before": before,
                    "after": {
                        "image_url": row.get("image_url"),
                        "source_url": row.get("source_url"),
                        "local_image_path": row.get("local_image_path"),
                    },
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


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def build_meta(catalog: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in catalog.get("items", []) if isinstance(item, dict)]
    fields = list((catalog.get("meta") or {}).get("fields") or [])
    if not fields and items:
        fields = sorted({key for item in items for key in item})
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
        description="Import validated catalog image updates into data/catalog_public.json."
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
