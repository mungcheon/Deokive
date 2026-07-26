from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_OUTPUT = DATA / "missing_image_variant_sibling_review_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON list or an object with items")
    return [row for row in rows if isinstance(row, dict)]


def group_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("source_url") or "").strip(),
        str(row.get("source_store") or "").strip(),
        str(row.get("series_name") or "").strip(),
        str(row.get("sub_series") or "").strip(),
    )


def compact_sibling(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "category": row.get("category"),
        "character_name": row.get("character_name"),
        "image_url": row.get("image_url"),
        "local_image_path": row.get("local_image_path"),
    }


def classify_review_item(row: dict[str, Any], siblings: list[dict[str, Any]]) -> str:
    categories = {str(sibling.get("category") or "") for sibling in siblings}
    characters = {str(sibling.get("character_name") or "") for sibling in siblings}
    category = str(row.get("category") or "")
    character = str(row.get("character_name") or "")
    if category not in categories:
        return "sibling_images_different_product_type"
    if character not in characters:
        return "sibling_images_different_character_or_variant"
    return "same_group_sibling_image_requires_exact_variant_check"


def build_report(rows: list[dict[str, Any]], *, generated_at: str | None = None) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = group_key(row)
        if key[0]:
            grouped[key].append(row)

    items: list[dict[str, Any]] = []
    for row in rows:
        if row.get("image_url"):
            continue
        key = group_key(row)
        if not key[0]:
            continue
        siblings = [sibling for sibling in grouped[key] if sibling is not row and sibling.get("image_url")]
        if not siblings:
            continue
        review_status = classify_review_item(row, siblings)
        items.append(
            {
                "manual_confirmed": False,
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "category": row.get("category"),
                "character_name": row.get("character_name"),
                "affiliation": row.get("affiliation"),
                "series_name": row.get("series_name"),
                "sub_series": row.get("sub_series"),
                "source_store": row.get("source_store"),
                "source_url": row.get("source_url"),
                "review_status": review_status,
                "imaged_sibling_rows": len(siblings),
                "imaged_sibling_sample": [compact_sibling(sibling) for sibling in siblings[:5]],
                "recommended_action": "do_not_copy_sibling_image_without_exact_variant_evidence",
                "required_evidence": [
                    "same source page or official page section",
                    "same product type",
                    "same character",
                    "same visible variant or exact prize/item label",
                ],
                "auto_apply_enabled": False,
            }
        )

    by_status = Counter(item["review_status"] for item in items)
    by_source_store = Counter(str(item.get("source_store") or "") for item in items)
    by_category = Counter(str(item.get("category") or "") for item in items)
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "missing_image_variant_sibling_review",
        "summary": {
            "review_rows": len(items),
            "manual_confirmed_rows": 0,
            "same_source_group_rows": len(items),
            "by_review_status": [[key, value] for key, value in sorted(by_status.items())],
            "by_source_store": by_source_store.most_common(),
            "by_category": by_category.most_common(),
            "auto_apply_enabled": False,
            "recommended_next_action": "review_exact_variant_before_reusing_or_replacing_images",
        },
        "items": items,
        "automation_policy": {
            "auto_apply_enabled": False,
            "reason": "Sibling images can be related but still show a different character, product type, or variant.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_catalog(args.catalog))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
