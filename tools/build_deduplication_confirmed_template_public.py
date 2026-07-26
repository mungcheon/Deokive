from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_deduplication_fast_review_public.json"
DEFAULT_OUTPUT = DATA / "catalog_deduplication_confirmed_template_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _template_item(group: dict[str, Any]) -> dict[str, Any]:
    template = dict(group.get("dedupe_decision_template") or {})
    warning = group.get("fast_review_warning") or template.get("fast_review_warning") or ""
    if warning == "no_identity_delta_detected":
        recommended_manual_action = "confirm_and_remove_duplicate_if_review_urls_match"
    elif warning == "image_delta_requires_visual_check":
        recommended_manual_action = "compare_images_before_confirming_duplicate"
    elif warning == "name_delta_requires_variant_check":
        recommended_manual_action = "confirm_name_difference_is_not_a_variant_before_merging"
    else:
        recommended_manual_action = "manual_identity_review_required"
    return {
        **template,
        "manual_confirmed": False,
        "same_sellable_product_confirmed": False,
        "decision": "review_required",
        "manual_note": "",
        "key_type": group.get("key_type") or template.get("key_type"),
        "key": group.get("key") or template.get("key"),
        "review_confidence": group.get("review_confidence") or template.get("review_confidence"),
        "review_risk": group.get("review_risk"),
        "keep_catalog_index": group.get("keep_catalog_index") or template.get("keep_catalog_index"),
        "drop_catalog_indexes": group.get("drop_catalog_indexes") or template.get("drop_catalog_indexes") or [],
        "fast_review_lane": group.get("fast_review_lane") or template.get("fast_review_lane"),
        "fast_review_warning": warning,
        "recommended_manual_action": recommended_manual_action,
        "primary_review_url": group.get("primary_review_url") or template.get("primary_review_url") or "",
        "primary_review_url_kind": group.get("primary_review_url_kind")
        or template.get("primary_review_url_kind")
        or "",
        "review_urls": group.get("review_urls") or template.get("review_urls") or [],
        "identity_delta": group.get("identity_delta") or template.get("identity_delta") or {},
        "image_url_only_same_identity": bool(
            group.get("image_url_only_same_identity")
            or template.get("image_url_only_same_identity")
        ),
        "requires_same_sellable_product": True,
        "requires_variant_difference_disproved": bool(template.get("requires_variant_difference_disproved")),
        "operator_checklist": [
            "Open primary_review_url first, then compare any image URLs listed in review_urls.",
            "Confirm barcode, official product title, character/variant, goods type, and image identity.",
            "If fast_review_warning is name_delta_requires_variant_check, do not merge until the name difference is proven harmless.",
            "If fast_review_warning is image_delta_requires_visual_check, do not merge until the images are proven to show the same item.",
            "Keep manual_confirmed=false for retailer mirrors, reissues, lineup images, or uncertain variants.",
        ],
        "stores": group.get("stores") or [],
        "categories": group.get("categories") or [],
        "evidence": group.get("evidence") or [],
        "merge_blockers": group.get("merge_blockers") or [],
        "rows": group.get("rows") or [],
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def build_template(fast_review: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    by_lane: Counter[str] = Counter()
    by_store: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_blocker: Counter[str] = Counter()
    by_warning: Counter[str] = Counter()
    by_recommended_action: Counter[str] = Counter()

    for group in fast_review.get("items") or []:
        if not isinstance(group, dict):
            continue
        item = _template_item(group)
        items.append(item)
        by_lane[str(item.get("fast_review_lane") or "")] += 1
        by_warning[str(item.get("fast_review_warning") or "")] += 1
        by_recommended_action[str(item.get("recommended_manual_action") or "")] += 1
        for store in item.get("stores") or []:
            by_store[str(store)] += 1
        for category in item.get("categories") or []:
            by_category[str(category)] += 1
        for blocker in item.get("merge_blockers") or ["none"]:
            by_blocker[str(blocker)] += 1

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_deduplication_confirmed_template",
        "summary": {
            "template_items": len(items),
            "manual_confirmed_rows": 0,
            "same_sellable_product_confirmed_rows": 0,
            "drop_candidate_rows": sum(len(item.get("drop_catalog_indexes") or []) for item in items),
            "by_fast_review_lane": [[key, value] for key, value in by_lane.most_common(20) if key],
            "by_fast_review_warning": [[key, value] for key, value in by_warning.most_common(20) if key],
            "by_recommended_manual_action": [
                [key, value] for key, value in by_recommended_action.most_common(20) if key
            ],
            "primary_review_url_rows": sum(1 for item in items if item.get("primary_review_url")),
            "identity_delta_rows": sum(1 for item in items if item.get("identity_delta")),
            "image_url_only_same_identity_rows": sum(
                1 for item in items if item.get("image_url_only_same_identity")
            ),
            "by_source_store": [[key, value] for key, value in by_store.most_common(20) if key],
            "by_category": [[key, value] for key, value in by_category.most_common(20) if key],
            "by_merge_blocker": [[key, value] for key, value in by_blocker.most_common(20) if key],
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        "instructions": [
            "Copy this template before entering dedupe decisions.",
            "Set manual_confirmed and same_sellable_product_confirmed to true only after comparing every row in the group.",
            "Change decision to drop_duplicates, merge_duplicates, or remove_duplicate_rows only for true duplicate sellable products.",
            "Leave review_required for variants, reissues, retailer-only mirrors, or uncertain names.",
            "Dry-run tools/import_confirmed_deduplication_rows.py before any --write import.",
        ],
        "items": items,
        "automation_policy": {
            "auto_merge": False,
            "auto_delete": False,
            "requires_manual_review": True,
            "requires_same_sellable_product": True,
            "import_tool": "tools/import_confirmed_deduplication_rows.py",
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    template = build_template(load_json(args.input))
    if args.write:
        args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
