from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "animation_category_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "animation_category_action_queue_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _categories(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for batch in payload.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for row in batch.get("categories", []):
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _mapping_mode(row: dict[str, Any]) -> str:
    reason = str(row.get("review_reason") or "").lower()
    category = str(row.get("category") or "").strip().lower()
    rows = int(row.get("rows") or 0)
    if "split" in reason or "broad" in reason:
        return "name_level_split_review_required"
    if category in {"acrylic", "아크릴"}:
        return "name_level_split_review_required"
    if rows >= 50 and str(row.get("suggested_category") or "").strip().lower() != category:
        return "name_level_split_review_required"
    return "direct_category_mapping_review"


def _requires_split_review(row: dict[str, Any]) -> bool:
    return _mapping_mode(row) == "name_level_split_review_required"


def _template(row: dict[str, Any]) -> dict[str, Any]:
    folder = row.get("folder_template") if isinstance(row.get("folder_template"), dict) else {}
    mapping_mode = _mapping_mode(row)
    return {
        "manual_confirmed": False,
        "mapping_mode": mapping_mode,
        "requires_name_level_split_review": mapping_mode == "name_level_split_review_required",
        "source_category": row.get("category"),
        "target_category": row.get("suggested_category") or row.get("category"),
        "target_family": row.get("suggested_family"),
        "folder_name": folder.get("folder_name") or row.get("suggested_category") or row.get("category"),
        "folder_color_hex": folder.get("color_hex") or row.get("suggested_color_hex"),
        "folder_color_hint": folder.get("color_hint") or row.get("suggested_color_hint"),
        "folder_color_group": folder.get("color_group") or row.get("suggested_color_group"),
        "folder_color_sort_order": folder.get("color_sort_order") or row.get("suggested_color_sort_order"),
        "folder_icon_key": folder.get("primary_icon_key") or row.get("suggested_primary_icon_key"),
        "folder_icon_options": folder.get("icon_options") or row.get("suggested_icon_options") or [],
        "affected_catalog_rows": int(row.get("rows") or 0),
        "blocked_until": "category_mapping_manually_confirmed",
        "review_evidence_required": [
            "sample_names_match_target_product_type",
            "broad_categories_are_split_before_mapping",
            "folder_color_and_icon_exist_in_app_catalog",
        ],
    }


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    mapping_mode = _mapping_mode(row)
    return {
        "category": row.get("category"),
        "rows": int(row.get("rows") or 0),
        "review_priority": int(row.get("review_priority") or 999),
        "mapping_mode": mapping_mode,
        "requires_name_level_split_review": mapping_mode == "name_level_split_review_required",
        "suggested_family": row.get("suggested_family"),
        "suggested_category": row.get("suggested_category"),
        "suggested_color_group": row.get("suggested_color_group"),
        "suggested_color_hint": row.get("suggested_color_hint"),
        "suggested_primary_icon_key": row.get("suggested_primary_icon_key"),
        "review_reason": row.get("review_reason"),
        "sample_names": (row.get("sample_names") or [])[:8],
        "category_mapping_template": _template(row),
        "auto_apply_enabled": False,
    }


def build_queue(payload: dict[str, Any], *, max_categories: int = 24, batch_size: int = 6) -> dict[str, Any]:
    rows = [_compact(row) for row in _categories(payload)]
    rows.sort(key=lambda row: (int(row.get("review_priority") or 999), str(row.get("category") or "")))
    queued = rows[:max_categories]

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(queued), batch_size):
        chunk = queued[offset : offset + batch_size]
        family_counts = Counter(str(row.get("suggested_family") or "") for row in chunk)
        color_counts = Counter(str(row.get("suggested_color_group") or "neutral") for row in chunk)
        batches.append(
            {
                "batch_id": f"animation-category-action-{len(batches) + 1:03d}",
                "priority": min(int(row.get("review_priority") or 999) for row in chunk),
                "category_count": len(chunk),
                "affected_catalog_rows": sum(int(row.get("rows") or 0) for row in chunk),
                "family_counts": family_counts.most_common(),
                "color_group_counts": color_counts.most_common(),
                "review_state": "manual_category_mapping_confirmation_required",
                "next_machine_step": "fill_confirmed_animation_category_mapping_templates",
                "categories": chunk,
            }
        )

    all_rows = sum(int(row.get("rows") or 0) for row in rows)
    queued_rows = sum(int(row.get("rows") or 0) for row in queued)
    mapping_mode_counts = Counter(str(row.get("mapping_mode") or "") for row in rows)
    summary = {
        "actionable_categories": len(rows),
        "queued_categories": len(queued),
        "actionable_catalog_rows": all_rows,
        "queued_catalog_rows": queued_rows,
        "action_batch_count": len(batches),
        "batch_size": batch_size,
        "max_categories": max_categories,
        "by_suggested_family": Counter(str(row.get("suggested_family") or "") for row in rows).most_common(),
        "by_color_group": Counter(str(row.get("suggested_color_group") or "neutral") for row in rows).most_common(),
        "by_mapping_mode": mapping_mode_counts.most_common(),
        "split_review_categories": sum(1 for row in rows if _requires_split_review(row)),
        "direct_mapping_categories": sum(1 for row in rows if not _requires_split_review(row)),
        "auto_apply_enabled": False,
    }
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "animation_category_action_queue",
        "summary": summary,
        "batches": batches,
        "automation_policy": {
            "auto_apply_category_changes": False,
            "auto_create_folders": False,
            "requires_manual_review": True,
            "reason": "Category mappings affect app navigation and user-facing folders.",
        },
        "instructions": [
            "Confirm each category_mapping_template before any catalog mutation.",
            "Split broad source categories such as acrylic before applying a single folder mapping.",
            "Keep folder colors ordered by color_group/sort_order so similar colors remain grouped.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-categories", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=6)
    args = parser.parse_args()

    queue = build_queue(_load(args.input), max_categories=args.max_categories, batch_size=args.batch_size)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(queue["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
