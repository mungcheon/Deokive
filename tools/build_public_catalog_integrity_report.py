from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_integrity_public.json"

KUJI_LAST_OR_DOUBLE_RE = re.compile(
    r"(라스트\s*원|라스트원|ラストワン|last\s*one|더블\s*찬스|더블찬스|ダブルチャンス|double\s*chance)",
    re.I,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def url_key(value: Any) -> str:
    url = str(value or "").strip().rstrip("/")
    if not url:
        return ""
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def is_generic_source_url(value: Any) -> bool:
    url = url_key(value)
    if not url:
        return True
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/").casefold()
    if not path or path == "/":
        return True
    return any(token in path for token in ("/search", "/shop", "/collections", "/category", "/categories"))


def load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise SystemExit(f"{path} must contain a JSON list or an object with items")
    return [item for item in items if isinstance(item, dict)]


def compact(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "source_store": row.get("source_store"),
        "source_url": row.get("source_url"),
        "release_date": row.get("release_date"),
        "category": row.get("category"),
        "sub_series": row.get("sub_series"),
        "barcode": row.get("barcode"),
        "image_url": row.get("image_url"),
        "local_image_path": row.get("local_image_path"),
    }


def duplicate_review_groups(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        name = norm(row.get("name_ko") or row.get("name_ja"))
        store = norm(row.get("source_store"))
        source = url_key(row.get("source_url"))
        barcode = norm(row.get("barcode"))
        if not name or not store:
            continue
        if not source and not barcode:
            continue
        groups[(store, name, source, barcode)].append(row)

    high_confidence: list[dict[str, Any]] = []
    review_needed: list[dict[str, Any]] = []
    for (_store, _name, source, barcode), items in groups.items():
        if len(items) < 2:
            continue
        image_keys = {
            norm(row.get("local_image_path") or row.get("image_url"))
            for row in items
            if present(row.get("local_image_path")) or present(row.get("image_url"))
        }
        same_image = len(image_keys) <= 1
        entry = {
            "rows": len(items),
            "reason": "same_store_name_and_source_or_barcode",
            "has_barcode": bool(barcode),
            "source_url_is_generic": is_generic_source_url(source),
            "same_display_image": same_image,
            "items": [compact(row) for row in items],
        }
        if barcode or (source and not is_generic_source_url(source) and same_image):
            high_confidence.append(entry)
        else:
            review_needed.append(entry)

    sorter = lambda item: (-int(item["rows"]), str(item["items"][0].get("source_store") or ""), str(item["items"][0].get("name_ko") or ""))
    return sorted(high_confidence, key=sorter), sorted(review_needed, key=sorter)


def kuji_last_double_price_violations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for row in rows:
        text = " ".join(str(row.get(field) or "") for field in ("name_ko", "name_ja", "sub_series"))
        source_url = str(row.get("source_url") or "")
        source_store = str(row.get("source_store") or "")
        is_kuji = "1kuji.com" in source_url or "一番くじ" in text or "이치방" in source_store
        if not is_kuji or not KUJI_LAST_OR_DOUBLE_RE.search(text):
            continue
        price_jpy = row.get("official_price_jpy")
        price_krw = row.get("official_price_krw")
        if price_jpy not in (None, "", 0) or price_krw not in (None, "", 0):
            violations.append({**compact(row), "official_price_jpy": price_jpy, "official_price_krw": price_krw})
    return violations


def build_report(rows: list[dict[str, Any]], *, generated_at: str | None = None) -> dict[str, Any]:
    high_confidence_duplicates, duplicate_review_needed = duplicate_review_groups(rows)
    display_image_missing = [
        row for row in rows if not present(row.get("local_image_path")) and not present(row.get("image_url"))
    ]
    last_double_violations = kuji_last_double_price_violations(rows)
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "public_catalog_integrity",
        "summary": {
            "row_count": len(rows),
            "display_image_missing_rows": len(display_image_missing),
            "high_confidence_duplicate_groups": len(high_confidence_duplicates),
            "duplicate_review_needed_groups": len(duplicate_review_needed),
            "kuji_last_or_double_chance_price_violations": len(last_double_violations),
            "auto_delete_enabled": False,
            "auto_price_mutation_enabled": False,
        },
        "high_confidence_duplicate_groups": high_confidence_duplicates[:100],
        "duplicate_review_needed_groups": duplicate_review_needed[:100],
        "kuji_last_or_double_chance_price_violations": last_double_violations[:200],
        "automation_policy": {
            "delete_duplicates_automatically": False,
            "requires_manual_review_for_generic_source_duplicates": True,
            "last_one_and_double_chance_should_have_zero_or_empty_official_price": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_catalog(args.input))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
