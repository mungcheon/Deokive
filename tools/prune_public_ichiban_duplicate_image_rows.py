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
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_REPORT = DATA / "ichiban_duplicate_image_prune_public.json"
KUJI_PRODUCT_PREFIX = "https://1kuji.com/products/"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _is_official_kuji_product_row(row: dict[str, Any]) -> bool:
    return _text(row.get("source_url")).startswith(KUJI_PRODUCT_PREFIX)


def _is_legacy_root_kuji_row(row: dict[str, Any]) -> bool:
    source_url = _text(row.get("source_url")).rstrip("/")
    return source_url == "https://1kuji.com"


def _image_key(row: dict[str, Any]) -> str:
    image_url = _text(row.get("image_url"))
    if image_url:
        return f"image:{image_url}"
    local_image_path = _text(row.get("local_image_path"))
    if local_image_path:
        return f"local:{local_image_path}"
    return ""


def prune_duplicate_image_rows(catalog: dict[str, Any], *, write: bool = False) -> dict[str, Any]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog must contain an items list")

    official_by_image: dict[str, dict[str, Any]] = {}
    for row in items:
        if not isinstance(row, dict) or not _is_official_kuji_product_row(row):
            continue
        key = _image_key(row)
        if key:
            official_by_image.setdefault(key, row)

    kept: list[dict[str, Any]] = []
    pruned: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            kept.append(row)
            continue
        key = _image_key(row)
        official = official_by_image.get(key)
        if _is_legacy_root_kuji_row(row) and official is not None:
            pruned.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_url": row.get("source_url"),
                    "image_url": row.get("image_url"),
                    "local_image_path": row.get("local_image_path"),
                    "reason": "legacy_root_kuji_row_duplicated_by_official_product_image",
                    "official_keep": {
                        "catalog_index": official.get("catalog_index"),
                        "name_ko": official.get("name_ko"),
                        "name_ja": official.get("name_ja"),
                        "source_url": official.get("source_url"),
                    },
                }
            )
            continue
        kept.append(row)

    if write and pruned:
        catalog["items"] = kept
        meta = catalog.get("meta")
        if isinstance(meta, dict):
            meta["row_count"] = len(kept)
            meta["total_items"] = len(kept)
        catalog["total_items"] = len(kept)

    return {
        "schema_version": 1,
        "scope": "ichiban_duplicate_image_prune",
        "summary": {
            "input_rows": len(items),
            "pruned_rows": len(pruned),
            "output_rows": len(kept),
            "write": write,
            "rule": "legacy 1kuji root rows are removed only when an official 1kuji product row shares the same image",
        },
        "pruned_rows": pruned,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8-sig"))
    report = prune_duplicate_image_rows(catalog, write=args.write)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write:
        args.catalog.write_text(
            json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
