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
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_OUTPUT = ROOT / "lib" / "data" / "catalog" / "seed_catalog.dart"

FIELD_MAP = [
    ("nameKo", "name_ko", "string_required"),
    ("nameJa", "name_ja", "string"),
    ("nameEn", "name_en", "string"),
    ("category", "category", "string_required"),
    ("characterName", "character_name", "string_required"),
    ("affiliation", "affiliation", "string"),
    ("seriesName", "series_name", "string"),
    ("subSeries", "sub_series", "string"),
    ("officialPriceJpy", "official_price_jpy", "int"),
    ("officialPriceKrw", "official_price_krw", "int"),
    ("barcode", "barcode", "string"),
    ("imageUrl", "image_url", "string"),
    ("sourceUrl", "source_url", "string"),
    ("sourceStore", "source_store", "string"),
    ("releaseDate", "release_date", "string"),
]


def _dart_string(value: object) -> str:
    text = str(value)
    text = text.replace("\\", "\\\\").replace("$", r"\$")
    if "'" not in text and "\n" not in text and "\r" not in text:
        return f"'{text}'"
    escaped = text.replace("'", "\\'").replace("\r", "\\r").replace("\n", "\\n")
    return f"'{escaped}'"


def _int_value(value: object | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _entry_lines(row: dict[str, Any]) -> list[str]:
    lines = ["  GoodsCatalogEntry("]
    for dart_name, json_name, kind in FIELD_MAP:
        value = row.get(json_name)
        if kind == "int":
            number = _int_value(value)
            if number is not None:
                lines.append(f"    {dart_name}: {number},")
            continue
        if value in (None, ""):
            if kind == "string_required":
                value = ""
            else:
                continue
        lines.append(f"    {dart_name}: {_dart_string(value)},")
    lines.append("  ),")
    return lines


def generate(rows: list[dict[str, Any]]) -> str:
    lines = [
        "import '../../models/goods_catalog_entry.dart';",
        "",
        "/// Auto-generated from server/catalog_seed_from_local.json.",
        "/// Do not edit by hand; run tools/generate_seed_catalog_dart.py.",
        "const List<GoodsCatalogEntry> kSeedCatalog = [",
    ]
    for row in rows:
        if isinstance(row, dict):
            lines.extend(_entry_lines(row))
    lines.append("];")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{args.input} must contain a JSON list or catalog object with items")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
