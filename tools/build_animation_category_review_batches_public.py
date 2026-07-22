from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "animation_goods_categories_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "animation_category_review_batches_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_queue(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    queue = payload.get("taxonomy_review_queue") or payload.get("unknown_categories")
    if not isinstance(queue, list):
        raise ValueError(f"{path} must contain a taxonomy_review_queue/unknown_categories list")
    return payload, [row for row in queue if isinstance(row, dict)]


def _priority(row: dict[str, Any]) -> int:
    return int(row.get("review_priority") or 999)


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    suggested_category = str(row.get("suggested_category") or row.get("category") or "")
    rows = int(row.get("rows") or 0)
    folder_template = {
        "folder_name": suggested_category,
        "family": row.get("suggested_family"),
        "color_hint": row.get("suggested_color_hint"),
        "color_hex": row.get("suggested_color_hex"),
        "color_group": row.get("suggested_color_group"),
        "color_sort_order": row.get("suggested_color_sort_order"),
        "primary_icon_key": row.get("suggested_primary_icon_key"),
        "icon_options": row.get("suggested_icon_options") or [],
        "source_category": row.get("category"),
        "requires_manual_review": True,
    }
    return {
        "category": row.get("category"),
        "rows": rows,
        "review_priority": _priority(row),
        "suggested_family": row.get("suggested_family"),
        "suggested_category": suggested_category,
        "suggested_color_hint": row.get("suggested_color_hint"),
        "suggested_color_hex": row.get("suggested_color_hex"),
        "suggested_color_group": row.get("suggested_color_group"),
        "suggested_color_sort_order": row.get("suggested_color_sort_order"),
        "suggested_primary_icon_key": row.get("suggested_primary_icon_key"),
        "suggested_icon_options": row.get("suggested_icon_options") or [],
        "review_reason": row.get("review_reason"),
        "sample_names": row.get("sample_names") or [],
        "folder_template": folder_template,
        "folder_creation_blocked_until": "category_mapping_manually_confirmed",
        "recommended_action": _recommended_action(row, rows),
        "auto_apply_enabled": False,
    }


def _recommended_action(row: dict[str, Any], rows: int) -> str:
    category = str(row.get("category") or "")
    suggested = str(row.get("suggested_category") or category)
    if category == suggested:
        return "Keep this category only after checking sample names; update folder visual tokens if it remains public."
    if rows >= 50:
        return "Split this broad category by product name first, then map reviewed rows into app folders."
    return "Review sample names and map the category to the suggested folder only when product type is clear."


def build_report(source: dict[str, Any], queue: list[dict[str, Any]], *, batch_size: int = 4) -> dict[str, Any]:
    rows = [_compact_row(row) for row in sorted(queue, key=lambda row: (_priority(row), str(row.get("category") or "")))]
    folder_color_palette = source.get("folder_color_palette") or []
    folder_visual_tokens = source.get("folder_visual_tokens") or []
    app_visual_catalog = source.get("app_folder_visual_catalog") or {}
    if not isinstance(app_visual_catalog, dict):
        app_visual_catalog = {}
    folder_icon_catalog = _folder_icon_catalog(folder_visual_tokens)
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(rows), batch_size):
        batch_rows = rows[offset : offset + batch_size]
        family_counts = Counter(str(row.get("suggested_family") or "") for row in batch_rows)
        color_counts = Counter(str(row.get("suggested_color_hint") or "") for row in batch_rows)
        color_group_counts = Counter(str(row.get("suggested_color_group") or "neutral") for row in batch_rows)
        folder_templates = [row.get("folder_template") for row in batch_rows if isinstance(row.get("folder_template"), dict)]
        batches.append(
            {
                "batch_id": f"animation-taxonomy-review-{len(batches) + 1:03d}",
                "priority": min(int(row.get("review_priority") or 999) for row in batch_rows),
                "category_count": len(batch_rows),
                "row_count": sum(int(row.get("rows") or 0) for row in batch_rows),
                "suggested_family_counts": family_counts.most_common(),
                "suggested_color_counts": color_counts.most_common(),
                "suggested_color_group_counts": color_group_counts.most_common(),
                "folder_templates": folder_templates,
                "folder_creation_blocked_until": "category_mapping_manually_confirmed",
                "recommended_action": "Review category names against samples, then record explicit category/folder decisions before catalog mutation.",
                "categories": batch_rows,
            }
        )

    total_rows = sum(int(row.get("rows") or 0) for row in rows)
    family_counts = Counter(str(row.get("suggested_family") or "") for row in rows)
    color_counts = Counter(str(row.get("suggested_color_hint") or "") for row in rows)
    color_group_counts = Counter(str(row.get("suggested_color_group") or "neutral") for row in rows)
    summary = {
        "source_categories": len(queue),
        "source_rows": total_rows,
        "batch_count": len(batches),
        "batch_size": batch_size,
        "by_suggested_family": family_counts.most_common(),
        "by_suggested_color": color_counts.most_common(),
        "by_suggested_color_group": color_group_counts.most_common(),
        "folder_color_palette_count": len(folder_color_palette),
        "folder_visual_token_count": len(folder_visual_tokens),
        "folder_template_count": len(rows),
        "folder_icon_family_count": len(folder_icon_catalog),
        "folder_icon_option_count": sum(int(row.get("icon_count") or 0) for row in folder_icon_catalog),
        "app_folder_color_count": int(app_visual_catalog.get("color_count") or 0),
        "app_folder_icon_option_count": int(app_visual_catalog.get("icon_count") or 0),
        "app_folder_icon_group_count": int(app_visual_catalog.get("icon_group_count") or 0),
        "app_folder_palette_section_count": int(app_visual_catalog.get("palette_section_count") or 0),
        "app_folder_palette_sorted_by_family": bool(app_visual_catalog.get("palette_sorted_by_family")),
        "app_animation_visuals_covered": bool(app_visual_catalog.get("animation_visuals_covered")),
        "auto_apply_enabled": False,
    }
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "animation_goods_taxonomy_review_batches",
        "summary": summary,
        "folder_color_palette": sorted(
            [row for row in folder_color_palette if isinstance(row, dict)],
            key=lambda row: int(row.get("sort_order") or 999),
        ),
        "app_folder_visual_catalog": app_visual_catalog,
        "folder_visual_tokens": folder_visual_tokens,
        "folder_icon_catalog": folder_icon_catalog,
        "batches": batches,
        "automation_policy": {
            "auto_apply_category_changes": False,
            "auto_apply_folder_visuals": False,
            "requires_manual_review": True,
            "reason": "Category and folder visual changes affect app navigation and user-created folders.",
        },
        "instructions": [
            "Review batches in priority order.",
            "Suggested category, color, and icon values are UI candidates, not catalog mutations.",
            "Keep color sorting by folder_color_palette so similar colors stay grouped in the app.",
        ],
    }


def _folder_icon_catalog(folder_visual_tokens: list[Any]) -> list[dict[str, Any]]:
    by_family: dict[str, set[str]] = {}
    primary_icons: dict[str, str] = {}
    for token in folder_visual_tokens:
        if not isinstance(token, dict):
            continue
        family = str(token.get("family") or "other")
        options = by_family.setdefault(family, set())
        primary = str(token.get("primary_icon_key") or "")
        if primary and family not in primary_icons:
            primary_icons[family] = primary
        for icon in token.get("icon_options") or []:
            if isinstance(icon, str) and icon:
                options.add(icon)
    return [
        {
            "family": family,
            "primary_icon_key": primary_icons.get(family) or sorted(icons)[0],
            "icon_options": sorted(icons),
            "icon_count": len(icons),
        }
        for family, icons in sorted(by_family.items())
        if icons
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    source, queue = _load_queue(args.input)
    report = build_report(source, queue, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
