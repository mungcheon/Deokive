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
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"


def _row_text(row: dict[str, Any]) -> str:
    keys = (
        "name_ko",
        "name_ja",
        "name_en",
        "category",
        "source_store",
        "source_url",
        "barcode",
    )
    return " ".join(str(row.get(key) or "") for key in keys).casefold()


def main() -> int:
    parser = argparse.ArgumentParser(description="Find public catalog rows by text.")
    parser.add_argument("query", nargs="+")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--missing-image", action="store_true")
    args = parser.parse_args()

    data = json.loads(args.catalog.read_text(encoding="utf-8"))
    rows = data["items"] if isinstance(data, dict) and "items" in data else data
    terms = [term.casefold() for term in args.query]
    matches: list[dict[str, Any]] = []
    for row in rows:
        if args.missing_image and str(row.get("image_url") or "").strip():
            continue
        haystack = _row_text(row)
        if all(term in haystack for term in terms):
            matches.append(row)

    for row in matches[: args.limit]:
        print(
            json.dumps(
                {
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_store": row.get("source_store"),
                    "source_url": row.get("source_url"),
                    "image_url": row.get("image_url"),
                    "local_image_path": row.get("local_image_path"),
                },
                ensure_ascii=False,
            )
        )
    print(f"matched_rows={len(matches)} shown_rows={min(len(matches), args.limit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
