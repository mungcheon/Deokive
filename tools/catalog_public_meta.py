from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

try:
    from catalog_normalize import canonical_key, normalize_row
except ImportError:
    from tools.catalog_normalize import canonical_key, normalize_row


PRIVACY_FLAGS = {
    "contains_user_accounts": False,
    "contains_local_folders": False,
    "contains_private_memos": False,
    "contains_device_profiles": False,
    "contains_server_tokens": False,
}


def is_missing(value: Any) -> bool:
    return value in (None, "")


def missing_counts(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    return {
        field: sum(1 for row in rows if is_missing(row.get(field)))
        for field in fields
        if field != "catalog_index"
    }


def duplicate_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(canonical_key(normalize_row(row)) for row in rows)
    duplicate_groups = [key for key, count in counts.items() if key[1] and count > 1]
    return {
        "duplicate_groups": len(duplicate_groups),
        "duplicate_rows": sum(counts[key] for key in duplicate_groups),
    }


def coverage_percent(total: int, missing: int) -> float:
    if total <= 0:
        return 0.0
    return round(((total - missing) / total) * 100, 2)


def quality_summary(rows: list[dict[str, Any]], missing: dict[str, int]) -> dict[str, Any]:
    row_count = len(rows)
    images_missing = int(missing.get("image_url", 0))
    local_images_missing = int(missing.get("local_image_path", images_missing))
    source_urls_missing = int(missing.get("source_url", 0))
    summary = {
        "row_count": row_count,
        **duplicate_summary(rows),
        "missing_images": images_missing,
        "missing_local_images": local_images_missing,
        "missing_source_urls": source_urls_missing,
        "missing_release_dates": int(missing.get("release_date", 0)),
        "missing_official_price_jpy": int(missing.get("official_price_jpy", 0)),
        "missing_barcodes": int(missing.get("barcode", 0)),
        "image_coverage_percent": coverage_percent(row_count, images_missing),
        "local_image_coverage_percent": coverage_percent(row_count, local_images_missing),
        "source_url_coverage_percent": coverage_percent(row_count, source_urls_missing),
    }
    return summary


def build_public_catalog_meta(
    rows: list[dict[str, Any]],
    *,
    fields: list[str],
    generated_at: str | None,
    source: str | Path = "data/catalog_public.json",
) -> dict[str, Any]:
    source_value = source.as_posix() if isinstance(source, Path) else source
    missing = missing_counts(rows, fields)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "source": source_value,
        "row_count": len(rows),
        "fields": fields,
        "missing": missing,
        "quality_summary": quality_summary(rows, missing),
        "privacy": dict(PRIVACY_FLAGS),
        "total_items": len(rows),
    }
