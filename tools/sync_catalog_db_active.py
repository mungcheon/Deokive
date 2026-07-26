from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from catalog_normalize import canonical_key, normalize_row

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_DB = ROOT / "server" / "deokive_dev.db"

FIELDS = (
    "id",
    "name_ko",
    "name_ja",
    "name_en",
    "category",
    "character_name",
    "affiliation",
    "series_name",
    "sub_series",
    "official_price_jpy",
    "barcode",
    "image_url",
    "source_url",
    "source_store",
    "release_date",
    "is_active",
)

SYNC_FIELDS = tuple(field for field in FIELDS if field not in {"id", "is_active"})


def load_seed_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{path} must contain a JSON list or an object with items")
    return [normalize_row(row) for row in rows if isinstance(row, dict)]


def load_active_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cursor = conn.execute(f"select {', '.join(FIELDS)} from goods_catalog where is_active = 1")
    return [dict(zip(FIELDS, row)) for row in cursor.fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    seed_rows = load_seed_rows(args.seed)
    seed_by_key = {
        canonical_key(row): row
        for row in seed_rows
        if canonical_key(row)[1]
    }
    seed_keys = set(seed_by_key)
    conn = sqlite3.connect(args.db)
    try:
        active_rows = load_active_rows(conn)
        active_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for row in active_rows:
            key = canonical_key(normalize_row(row))
            if key[1] and key not in active_by_key:
                active_by_key[key] = row
        active_keys = set(active_by_key)
        deactivate: list[dict[str, Any]] = []
        for row in active_rows:
            key = canonical_key(normalize_row(row))
            if not key[1] or key not in seed_keys:
                deactivate.append(row)
        insert_rows = [row for key, row in seed_by_key.items() if key not in active_keys]
        update_rows: list[tuple[dict[str, Any], dict[str, Any], list[str]]] = []
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
                update_rows.append((active_row, seed_row, changed_fields))

        if args.write and deactivate:
            conn.executemany(
                "update goods_catalog set is_active = 0 where id = ?",
                [(row["id"],) for row in deactivate],
            )
        if args.write and update_rows:
            now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
            set_clause = ", ".join(f"{field} = ?" for field in SYNC_FIELDS) + ", updated_at = ?"
            conn.executemany(
                f"update goods_catalog set {set_clause} where id = ?",
                [
                    tuple(seed_row.get(field) for field in SYNC_FIELDS) + (now, active_row["id"])
                    for active_row, seed_row, _changed_fields in update_rows
                ],
            )
        if args.write and insert_rows:
            insert_fields = [field for field in FIELDS if field != "id"] + ["created_at", "updated_at"]
            placeholders = ", ".join("?" for _ in insert_fields)
            now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
            conn.executemany(
                f"insert into goods_catalog ({', '.join(insert_fields)}) values ({placeholders})",
                [
                    tuple(
                        1
                        if field == "is_active"
                        else now
                        if field in {"created_at", "updated_at"}
                        else row.get(field)
                        for field in insert_fields
                    )
                    for row in insert_rows
                ],
            )
        if args.write and (deactivate or update_rows or insert_rows):
            conn.commit()

        action = "deactivated" if args.write else "would deactivate"
        payload = {
            "db": str(args.db),
            "seed": str(args.seed),
            "active_rows": len(active_rows),
            "seed_keys": len(seed_keys),
            "stale_active_rows": len(deactivate),
            "updated_active_rows": len(update_rows),
            "missing_seed_rows": len(insert_rows),
            "write": args.write,
            "stale_sample": [
                {
                    "id": row.get("id"),
                    "name_ko": row.get("name_ko"),
                    "source_store": row.get("source_store"),
                    "source_url": row.get("source_url"),
                }
                for row in deactivate[:30]
            ],
            "missing_sample": [
                {
                    "name_ko": row.get("name_ko"),
                    "source_store": row.get("source_store"),
                    "source_url": row.get("source_url"),
                    "barcode": row.get("barcode"),
                }
                for row in insert_rows[:30]
            ],
            "update_sample": [
                {
                    "id": active_row.get("id"),
                    "name_ko": active_row.get("name_ko"),
                    "changed_fields": changed_fields,
                }
                for active_row, _seed_row, changed_fields in update_rows[:30]
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"{args.db}: {action} {len(deactivate)} stale active rows")
        print(f"{args.db}: {'updated' if args.write else 'would update'} {len(update_rows)} active rows")
        print(f"{args.db}: {'inserted' if args.write else 'would insert'} {len(insert_rows)} missing seed rows")
        if deactivate and not args.write:
            print("Dry run only. Re-run with --write to deactivate stale rows.")
        return 0
    finally:
        conn.close()


def _normalized_db_value(value: Any) -> Any:
    return None if value == "" else value


if __name__ == "__main__":
    raise SystemExit(main())
