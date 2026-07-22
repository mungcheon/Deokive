"""
Remove duplicate catalog rows.

Default mode dedupes server/catalog_seed_from_local.json in dry-run mode.
Use --write to update the JSON seed. Use --dart to run the older Dart-file
dedupe for lib/data/catalog/*.dart.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from catalog_normalize import canonical_key, normalize_row, row_richness

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "lib" / "data" / "catalog"
DEFAULT_JSON = ROOT / "server" / "catalog_seed_from_local.json"

ENTRY_START = "GoodsCatalogEntry("
ENTRY_END_LOOKAHEAD = re.compile(r"\),\s*(?=GoodsCatalogEntry\(|\];)")
FIELD_RE = re.compile(r"(\w+)\s*:\s*('(?:[^'\\]|\\.)*'|[^,()]+)")


def parse_entries(text: str) -> list[tuple[int, int, dict[str, str]]]:
    out: list[tuple[int, int, dict[str, str]]] = []
    pos = 0
    while True:
        start = text.find(ENTRY_START, pos)
        if start < 0:
            break
        match = ENTRY_END_LOOKAHEAD.search(text, start)
        if not match:
            break
        end = match.end()
        while end < len(text) and text[end] in " \t":
            end += 1
        if end < len(text) and text[end] == "\n":
            end += 1
        block = text[start:end]
        fields: dict[str, str] = {}
        for field_match in FIELD_RE.finditer(block):
            name = field_match.group(1)
            value = field_match.group(2).strip()
            if name not in fields:
                fields[name] = _dart_value(value)
        out.append((start, end, fields))
        pos = end
    return out


def process_dart_file(path: Path, write: bool) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    entries = parse_entries(text)
    if not entries:
        return (0, 0)

    by_key: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, (_, _, fields) in enumerate(entries):
        by_key[canonical_key(_dart_fields_to_json(fields))].append(index)

    drop_indices = _duplicate_indices(entries, by_key)
    if write and drop_indices:
        parts: list[str] = []
        cursor = 0
        for index, (start, end, _) in enumerate(entries):
            parts.append(text[cursor:start])
            if index not in drop_indices:
                parts.append(text[start:end])
            cursor = end
        parts.append(text[cursor:])
        path.write_text("".join(parts), encoding="utf-8")
    return (len(entries), len(drop_indices))


def process_json(path: Path, write: bool, report_path: Path | None) -> tuple[int, int]:
    payload, rows = _load_json_payload(path)

    original_rows = [dict(row) for row in rows if isinstance(row, dict)]
    normalized_rows = [normalize_row(row) for row in original_rows]
    by_key: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(normalized_rows):
        by_key[canonical_key(row)].append(index)

    keep_by_group: dict[tuple[str, str], int] = {}
    drops: set[int] = set()
    groups: list[dict[str, Any]] = []
    for key, indices in by_key.items():
        if len(indices) < 2 or not key[1]:
            continue
        keep = max(indices, key=lambda idx: (row_richness(normalized_rows[idx]), -idx))
        keep_by_group[key] = keep
        for idx in indices:
            if idx != keep:
                drops.add(idx)
        groups.append(
            {
                "key_type": key[0],
                "key": key[1],
                "keep_index": keep,
                "drop_indices": [idx for idx in indices if idx != keep],
                "names": [normalized_rows[idx].get("name_ko") for idx in indices],
            }
        )

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "input": str(path),
                    "rows": len(normalized_rows),
                    "duplicate_groups": len(groups),
                    "duplicates": len(drops),
                    "groups": groups,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    if write and drops:
        merged_rows: list[dict[str, Any]] = []
        for index, row in enumerate(original_rows):
            if index in drops:
                continue
            merged = dict(row)
            for key, keep_index in keep_by_group.items():
                if keep_index != index:
                    continue
                for drop_index in by_key[key]:
                    if drop_index == index:
                        continue
                    merged = _merge_rows(merged, original_rows[drop_index])
            merged_rows.append(merged)
        _write_json_payload(path, payload, merged_rows)
    return (len(normalized_rows), len(drops))


def _duplicate_indices(
    entries: list[tuple[int, int, dict[str, str]]],
    by_key: dict[tuple[str, str], list[int]],
) -> set[int]:
    drop_indices: set[int] = set()
    for key, indices in by_key.items():
        if len(indices) < 2 or not key[1]:
            continue
        best = max(
            indices,
            key=lambda idx: (
                row_richness(_dart_fields_to_json(entries[idx][2])),
                -idx,
            ),
        )
        for idx in indices:
            if idx != best:
                drop_indices.add(idx)
    return drop_indices


def _merge_rows(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    out = dict(primary)
    for key, value in secondary.items():
        if out.get(key) in (None, "") and value not in (None, ""):
            out[key] = value
    return out


def _load_json_payload(path: Path) -> tuple[Any, list[Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload, list(payload["items"])
    if isinstance(payload, list):
        return payload, payload
    raise SystemExit(f"{path} must contain a JSON list or an object with items")


def _missing_by_field(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    return {field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields}


def _write_json_payload(path: Path, payload: Any, rows: list[dict[str, Any]]) -> None:
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


def _dart_value(value: str) -> str:
    value = value.strip()
    if value == "null":
        return ""
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("\\'", "'").replace("\\\\", "\\")
    return value


def _dart_fields_to_json(fields: dict[str, str]) -> dict[str, Any]:
    mapping = {
        "nameKo": "name_ko",
        "nameJa": "name_ja",
        "nameEn": "name_en",
        "characterName": "character_name",
        "seriesName": "series_name",
        "subSeries": "sub_series",
        "officialPriceJpy": "official_price_jpy",
        "officialPriceKrw": "official_price_krw",
        "imageUrl": "image_url",
        "sourceUrl": "source_url",
        "sourceStore": "source_store",
    }
    out: dict[str, Any] = {}
    for key, value in fields.items():
        out[mapping.get(key, key)] = value
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report", type=Path, default=ROOT / "server" / "catalog_dedupe_report.json")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--dart", action="store_true", help="dedupe lib/data/catalog/*.dart instead of JSON")
    args = parser.parse_args()

    if args.dart:
        total_entries = 0
        total_dropped = 0
        for path in sorted(CATALOG_DIR.glob("*.dart")):
            if path.name == "all.dart":
                continue
            entries, dropped = process_dart_file(path, write=args.write)
            total_entries += entries
            total_dropped += dropped
            flag = "updated " if args.write and dropped else "        "
            print(f"{flag}{path.name:25s} {entries:5d} entries  -{dropped}")
        target = "removed" if args.write else "would remove"
        print(f"Total: {total_entries} entries, {target} {total_dropped} duplicates")
        return 0

    entries, dropped = process_json(args.input, write=args.write, report_path=args.report)
    target = "removed" if args.write else "would remove"
    print(f"{args.input}: {entries} rows, {target} {dropped} duplicates")
    print(f"Report: {args.report}")
    if not args.write:
        print("Dry run only. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
