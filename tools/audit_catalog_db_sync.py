from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from catalog_normalize import canonical_key, normalize_row
from sync_catalog_db_active import FIELDS, SYNC_FIELDS, _normalized_db_value, load_active_rows, load_seed_rows

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_DBS = [ROOT / "server" / "deokive_dev.db"]
DEFAULT_JSON = ROOT / "server" / "catalog_db_sync_audit.json"
DEFAULT_MD = ROOT / "server" / "catalog_db_sync_audit.md"


def _missing(row: dict[str, Any], field: str) -> bool:
    return row.get(field) in (None, "")


def audit_db(seed_rows: list[dict[str, Any]], db_path: Path) -> dict[str, Any]:
    seed_by_key = {canonical_key(row): row for row in seed_rows if canonical_key(row)[1]}
    seed_keys = set(seed_by_key)
    if not db_path.exists():
        return {
            "db": str(db_path),
            "exists": False,
            "ok": False,
            "active_rows": 0,
            "seed_keys": len(seed_keys),
            "stale_active_rows": 0,
            "missing_seed_rows": len(seed_keys),
            "updated_active_rows": 0,
            "duplicate_active_rows": 0,
            "missing_images": 0,
            "stale_sample": [],
            "missing_sample": [],
            "update_sample": [],
            "duplicate_sample": [],
        }

    conn = sqlite3.connect(db_path)
    try:
        active_rows = load_active_rows(conn)
    finally:
        conn.close()

    active_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in active_rows:
        key = canonical_key(normalize_row(row))
        if not key[1]:
            continue
        duplicate_groups[key].append(row)
        if key not in active_by_key:
            active_by_key[key] = row

    active_keys = set(active_by_key)
    stale_rows = [
        row
        for row in active_rows
        if not canonical_key(normalize_row(row))[1] or canonical_key(normalize_row(row)) not in seed_keys
    ]
    missing_rows = [row for key, row in seed_by_key.items() if key not in active_keys]

    update_rows: list[dict[str, Any]] = []
    changed_field_counts: Counter[str] = Counter()
    for key, seed_row in seed_by_key.items():
        active_row = active_by_key.get(key)
        if not active_row:
            continue
        changed_fields = [
            field
            for field in SYNC_FIELDS
            if _normalized_db_value(active_row.get(field)) != _normalized_db_value(seed_row.get(field))
        ]
        if changed_fields:
            changed_field_counts.update(changed_fields)
            update_rows.append(
                {
                    "id": active_row.get("id"),
                    "name_ko": active_row.get("name_ko"),
                    "source_store": active_row.get("source_store"),
                    "changed_fields": changed_fields,
                }
            )

    duplicate_rows: list[dict[str, Any]] = []
    for key, rows in duplicate_groups.items():
        if len(rows) > 1:
            duplicate_rows.extend(rows[1:])

    ok = not stale_rows and not missing_rows and not update_rows and not duplicate_rows
    return {
        "db": str(db_path),
        "exists": True,
        "ok": ok,
        "active_rows": len(active_rows),
        "seed_keys": len(seed_keys),
        "stale_active_rows": len(stale_rows),
        "missing_seed_rows": len(missing_rows),
        "updated_active_rows": len(update_rows),
        "duplicate_active_rows": len(duplicate_rows),
        "missing_images": sum(1 for row in active_rows if _missing(row, "image_url")),
        "changed_field_counts": changed_field_counts.most_common(),
        "stale_sample": [
            {
                "id": row.get("id"),
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "source_url": row.get("source_url"),
            }
            for row in stale_rows[:30]
        ],
        "missing_sample": [
            {
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "source_url": row.get("source_url"),
            }
            for row in missing_rows[:30]
        ],
        "update_sample": update_rows[:30],
        "duplicate_sample": [
            {
                "id": row.get("id"),
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "source_url": row.get("source_url"),
            }
            for row in duplicate_rows[:30]
        ],
    }


def build_report(seed_path: Path, db_paths: list[Path]) -> dict[str, Any]:
    seed_rows = load_seed_rows(seed_path)
    db_reports = [audit_db(seed_rows, path) for path in db_paths]
    return {
        "seed": str(seed_path),
        "seed_rows": len(seed_rows),
        "seed_keys": len({canonical_key(row) for row in seed_rows if canonical_key(row)[1]}),
        "ok": all(item.get("ok") for item in db_reports),
        "db_count": len(db_reports),
        "databases": db_reports,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog DB Sync Audit",
        "",
        f"- Seed rows: `{report.get('seed_rows')}`",
        f"- Seed keys: `{report.get('seed_keys')}`",
        f"- OK: `{report.get('ok')}`",
        "",
        "| DB | OK | Active | Missing Images | Stale | Missing Seed | Updated | Duplicates |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report.get("databases") or []:
        lines.append(
            "| {db} | {ok} | {active} | {images} | {stale} | {missing} | {updated} | {dupes} |".format(
                db=item.get("db"),
                ok=item.get("ok"),
                active=item.get("active_rows"),
                images=item.get("missing_images"),
                stale=item.get("stale_active_rows"),
                missing=item.get("missing_seed_rows"),
                updated=item.get("updated_active_rows"),
                dupes=item.get("duplicate_active_rows"),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--db", type=Path, action="append", default=None)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--fail-on-mismatch", action="store_true")
    args = parser.parse_args()

    report = build_report(args.seed, args.db or DEFAULT_DBS)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.markdown_output)
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "seed_rows": report["seed_rows"],
                "db_count": report["db_count"],
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if args.fail_on_mismatch and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
