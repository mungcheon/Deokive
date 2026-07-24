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
DEFAULT_UNMATCHED_KEYWORD_REVIEW = ROOT / "data" / "animation_category_unmatched_keyword_review_public.json"
DEFAULT_NORMALIZATION_INPUT = ROOT / "data" / "animation_goods_categories_public.json"
CONFIRMED_TEMPLATE = "server/animation_category_confirmed_rows.template.json"
CONFIRMED_QUEUE = "server/animation_category_confirmed_rows.json"
IMPORT_TOOL = "tools/import_confirmed_animation_category_rows.py"
UNBLOCKS_WHEN = "category_mapping_manually_confirmed"

MODE_BLOCKERS = {
    "name_level_split_review_required": {
        "blocked_until": "name_level_split_rules_manually_confirmed",
        "blocked_reason": "broad_source_category_requires_name_level_split",
        "required_evidence": [
            "sample_names_match_product_type_split_rules",
            "broad_category_not_mapped_to_single_folder",
            "confirmed_split_target_category_for_each_rule",
        ],
    },
    "direct_category_mapping_review": {
        "blocked_until": "direct_category_mapping_manually_confirmed",
        "blocked_reason": "direct_category_mapping_requires_sample_review",
        "required_evidence": [
            "sample_names_match_single_target_goods_type",
            "target_folder_color_and_icon_exist_in_app_catalog",
            "manual_note_for_mapping_decision",
        ],
    },
    "unmatched_keyword_review": {
        "blocked_until": "unmatched_keywords_classified_or_rejected",
        "blocked_reason": "unmatched_product_type_keywords_need_review",
        "required_evidence": [
            "product_type_like_tokens_confirmed_with_samples",
            "series_source_store_noise_tokens_rejected",
            "new_split_rules_recorded_only_for_consistent_goods_types",
        ],
    },
    "canonical_category_normalization_review": {
        "blocked_until": "canonical_category_normalization_manually_confirmed",
        "blocked_reason": "subtype_category_may_need_sub_series_preservation",
        "required_evidence": [
            "sample_names_match_suggested_broader_category",
            "source_category_should_be_preserved_as_sub_series_or_note",
            "folder_color_and_icon_exist_in_app_catalog",
            "manual_note_for_category_semantics",
        ],
    },
}


def _mode_blocker(mode: str) -> dict[str, Any]:
    return dict(
        MODE_BLOCKERS.get(
            mode,
            {
                "blocked_until": "manual_review_completed",
                "blocked_reason": "manual_review_required",
                "required_evidence": ["manual_confirmation"],
            },
        )
    )

PRODUCT_TYPE_HINTS = [
    ("acrylic_stand", ("アクリルスタンド", "アクスタ", "acrylic stand", "standee", "스탠드")),
    ("acrylic_keyring", ("アクリルキーホルダー", "アクキー", "keyholder", "keyring", "키링")),
    ("badge", ("缶バッジ", "バッジ", "badge", "뱃지")),
    ("clear_file", ("クリアファイル", "file", "파일")),
    ("figure", ("フィギュア", "figure", "피규어")),
    ("plush", ("ぬいぐるみ", "マスコット", "plush", "인형", "누이")),
    ("card", ("カード", "ポストカード", "card", "카드")),
    ("towel", ("タオル", "towel", "타월", "수건")),
    ("stationery", ("ノート", "ステッカー", "シール", "メモ", "文具", "문구", "스티커")),
]


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


def _normalization_categories(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    return [
        row
        for row in payload.get("normalization_review_queue", [])
        if isinstance(row, dict)
    ]


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


def _sample_names(row: dict[str, Any], limit: int = 8) -> list[str]:
    return [str(name) for name in (row.get("sample_names") or [])[:limit]]


def _name_split_hints(row: dict[str, Any]) -> list[dict[str, Any]]:
    samples = _sample_names(row, limit=24)
    hints: list[dict[str, Any]] = []
    for hint_key, tokens in PRODUCT_TYPE_HINTS:
        matched_names = [
            name
            for name in samples
            if any(token.casefold() in name.casefold() for token in tokens)
        ]
        if matched_names:
            hints.append(
                {
                    "hint_key": hint_key,
                    "matched_sample_names": len(matched_names),
                    "sample_names": matched_names[:5],
                }
            )
    hints.sort(key=lambda item: (-int(item["matched_sample_names"]), str(item["hint_key"])))
    return hints


def _review_summary(row: dict[str, Any], mapping_mode: str) -> dict[str, Any]:
    split_hints = _name_split_hints(row)
    return {
        "affected_catalog_rows": int(row.get("rows") or 0),
        "mapping_mode": mapping_mode,
        "requires_name_level_split_review": mapping_mode == "name_level_split_review_required",
        "sample_name_count": len(row.get("sample_names") or []),
        "name_split_hint_count": len(split_hints),
        "name_split_hints": split_hints,
        "recommended_review_path": (
            "review_name_split_hints_before_category_mapping"
            if mapping_mode == "name_level_split_review_required"
            else "confirm_direct_category_mapping"
        ),
    }


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
        **_mode_blocker(mapping_mode),
        "blocked_until": _mode_blocker(mapping_mode)["blocked_until"],
        "review_evidence_required": [
            "sample_names_match_target_product_type",
            "broad_categories_are_split_before_mapping",
            "folder_color_and_icon_exist_in_app_catalog",
        ],
    }


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    mapping_mode = _mapping_mode(row)
    review_summary = _review_summary(row, mapping_mode)
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
        "review_summary": review_summary,
        "name_split_hints": review_summary["name_split_hints"],
        "sample_names": _sample_names(row),
        "category_mapping_template": _template(row),
        "manual_confirmation_template": CONFIRMED_TEMPLATE,
        "confirmed_queue": CONFIRMED_QUEUE,
        "import_tool": IMPORT_TOOL,
        "unblocks_when": UNBLOCKS_WHEN,
        "auto_apply_enabled": False,
        **_mode_blocker(mapping_mode),
    }


def _visual_tokens_by_category(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    tokens: dict[str, dict[str, Any]] = {}
    for row in payload.get("folder_visual_tokens") or []:
        if not isinstance(row, dict):
            continue
        category = str(row.get("category") or "").strip()
        if category:
            tokens[category] = row
    return tokens


def _compact_normalization(
    row: dict[str, Any],
    review_priority: int,
    visual_tokens: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    mapping_mode = "canonical_category_normalization_review"
    rows = int(row.get("affected_catalog_rows") or row.get("rows") or 0)
    sample_names = _sample_names(row)
    template = row.get("category_mapping_template") if isinstance(row.get("category_mapping_template"), dict) else {}
    blocker = _mode_blocker(mapping_mode)
    target_category = str(template.get("target_category") or row.get("suggested_category") or "").strip()
    target_visual = dict((visual_tokens or {}).get(target_category) or {})
    return {
        "review_id": row.get("review_id"),
        "category": row.get("category"),
        "rows": rows,
        "review_priority": review_priority,
        "mapping_mode": mapping_mode,
        "requires_name_level_split_review": False,
        "suggested_family": row.get("suggested_family") or target_visual.get("family") or row.get("suggested_category"),
        "suggested_category": row.get("suggested_category"),
        "suggested_color_group": row.get("suggested_color_group") or target_visual.get("color_group"),
        "suggested_color_hint": row.get("suggested_color_hint") or target_visual.get("color_hint"),
        "suggested_color_hex": row.get("suggested_color_hex") or target_visual.get("color_hex"),
        "suggested_color_sort_order": row.get("suggested_color_sort_order") or target_visual.get("color_sort_order"),
        "suggested_primary_icon_key": row.get("suggested_primary_icon_key") or target_visual.get("primary_icon_key"),
        "suggested_icon_options": row.get("suggested_icon_options") or target_visual.get("icon_options") or [],
        "target_category_visual_token": target_visual,
        "review_reason": row.get("review_reason"),
        "review_summary": {
            "affected_catalog_rows": rows,
            "mapping_mode": mapping_mode,
            "requires_name_level_split_review": False,
            "sample_name_count": len(sample_names),
            "name_split_hint_count": 0,
            "name_split_hints": [],
            "recommended_review_path": "confirm_canonical_category_normalization",
            "preserve_source_category_as_sub_series": bool(
                template.get("preserve_source_category_as_sub_series")
            ),
        },
        "name_split_hints": [],
        "sample_names": sample_names,
        "category_mapping_template": {
            "manual_confirmed": bool(template.get("manual_confirmed")),
            "mapping_mode": mapping_mode,
            "source_category": template.get("source_category") or row.get("category"),
            "target_category": target_category,
            "preserve_source_category_as_sub_series": bool(
                template.get("preserve_source_category_as_sub_series")
            ),
            "folder_name": target_category,
            "folder_color_hex": target_visual.get("color_hex"),
            "folder_color_hint": target_visual.get("color_hint"),
            "folder_color_group": target_visual.get("color_group"),
            "folder_color_sort_order": target_visual.get("color_sort_order"),
            "folder_icon_key": target_visual.get("primary_icon_key"),
            "folder_icon_options": target_visual.get("icon_options") or [],
            "affected_catalog_rows": rows,
            "manual_note": template.get("manual_note") or "",
            **blocker,
        },
        "manual_confirmation_template": CONFIRMED_TEMPLATE,
        "confirmed_queue": CONFIRMED_QUEUE,
        "import_tool": IMPORT_TOOL,
        "unblocks_when": "canonical_category_normalization_manually_confirmed",
        "manual_confirmation_required": True,
        "auto_apply_enabled": False,
        **blocker,
    }


def _is_noop_direct_mapping(row: dict[str, Any]) -> bool:
    if row.get("mapping_mode") != "direct_category_mapping_review":
        return False
    source = str(row.get("category") or "").strip().casefold()
    target = str(row.get("suggested_category") or row.get("category") or "").strip().casefold()
    return bool(source) and source == target


def _work_order(
    rows: list[dict[str, Any]],
    unmatched_keyword_review: dict[str, Any] | None = None,
    normalization_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    split_rows = [row for row in rows if row.get("requires_name_level_split_review")]
    direct_rows = [row for row in rows if not row.get("requires_name_level_split_review")]
    unmatched_summary = (
        unmatched_keyword_review.get("summary")
        if isinstance(unmatched_keyword_review, dict)
        and isinstance(unmatched_keyword_review.get("summary"), dict)
        else {}
    )
    unmatched_rows = int(unmatched_summary.get("unmatched_rows") or 0)
    token_candidates = int(unmatched_summary.get("token_candidate_count") or 0)
    product_type_candidates = int(unmatched_summary.get("product_type_candidate_count") or 0)
    top_product_type_candidates = (
        [
            row
            for row in unmatched_keyword_review.get("top_product_type_candidates", [])
            if isinstance(row, dict)
        ]
        if isinstance(unmatched_keyword_review, dict)
        else []
    )
    orders: list[dict[str, Any]] = []

    if split_rows:
        orders.append(
            {
                "rank": 1,
                "lane": "name_level_split_review",
                "source": "animation_category_split_review_public.json",
                "category_count": len(split_rows),
                "affected_catalog_rows": sum(int(row.get("rows") or 0) for row in split_rows),
                "next_step": "confirm_animation_category_name_split_templates",
                "template": "server/animation_category_name_split_confirmed_rows.template.json",
                "blocked_direct_mapping_categories": [row.get("category") for row in split_rows],
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                **_mode_blocker("name_level_split_review_required"),
                "notes": [
                    "Broad categories must be split by product-type keywords before any folder/category mapping.",
                    "Do not map an entire broad category such as acrylic or goods to one target folder.",
                ],
            }
        )

    if direct_rows:
        orders.append(
            {
                "rank": 2,
                "lane": "direct_category_mapping_review",
                "source": "animation_category_action_queue_public.json",
                "category_count": len(direct_rows),
                "affected_catalog_rows": sum(int(row.get("rows") or 0) for row in direct_rows),
                "next_step": "fill_confirmed_animation_category_mapping_templates",
                "template": CONFIRMED_TEMPLATE,
                "categories": [row.get("category") for row in direct_rows],
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                **_mode_blocker("direct_category_mapping_review"),
                "notes": ["Only use after sample names match a single target goods type."],
            }
        )

    normalization_rows = normalization_rows or []
    if normalization_rows:
        target_visual_tokens = []
        seen_target_categories: set[str] = set()
        for row in normalization_rows:
            category = str(row.get("suggested_category") or "").strip()
            token = row.get("target_category_visual_token")
            if category and isinstance(token, dict) and token and category not in seen_target_categories:
                target_visual_tokens.append(token)
                seen_target_categories.add(category)
        orders.append(
            {
                "rank": 3,
                "lane": "canonical_category_normalization_review",
                "source": "animation_goods_categories_public.json",
                "category_count": len(normalization_rows),
                "affected_catalog_rows": sum(int(row.get("rows") or 0) for row in normalization_rows),
                "next_step": "confirm_canonical_animation_category_normalization",
                "template": CONFIRMED_TEMPLATE,
                "categories": [row.get("category") for row in normalization_rows],
                "target_categories": sorted(
                    {
                        str(row.get("suggested_category") or "")
                        for row in normalization_rows
                        if str(row.get("suggested_category") or "")
                    }
                ),
                "target_category_visual_tokens": target_visual_tokens,
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                **_mode_blocker("canonical_category_normalization_review"),
                "notes": [
                    "Normalize subtype-like source categories only after confirming sample names.",
                    "Preserve the original source category as sub_series or a note when it helps user search.",
                ],
            }
        )

    if unmatched_rows or token_candidates:
        orders.append(
            {
                "rank": 4,
                "lane": "unmatched_keyword_review",
                "source": "animation_category_unmatched_keyword_review_public.json",
                "affected_catalog_rows": unmatched_rows,
                "token_candidate_count": token_candidates,
                "product_type_candidate_count": product_type_candidates,
                "top_product_type_candidate_count": len(top_product_type_candidates),
                "top_product_type_candidates": top_product_type_candidates[:12],
                "next_step": "review_unmatched_animation_keyword_candidates",
                "template": "server/animation_category_name_split_confirmed_rows.template.json",
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                **_mode_blocker("unmatched_keyword_review"),
                "notes": [
                    "Review product_type_like tokens first; add name-level split rules only when samples consistently match one goods type.",
                    "Treat series/source/store noise as exclusions, not category rules.",
                ],
            }
        )

    return orders


def build_queue(
    payload: dict[str, Any],
    *,
    max_categories: int = 24,
    batch_size: int = 6,
    unmatched_keyword_review: dict[str, Any] | None = None,
    normalization_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = [
        row
        for row in (_compact(category) for category in _categories(payload))
        if not _is_noop_direct_mapping(row)
    ]
    rows.sort(key=lambda row: (int(row.get("review_priority") or 999), str(row.get("category") or "")))
    queued = rows[:max_categories]
    visual_tokens = _visual_tokens_by_category(normalization_review)
    normalization_rows = [
        _compact_normalization(row, 700 + index, visual_tokens)
        for index, row in enumerate(_normalization_categories(normalization_review), start=1)
    ]
    normalization_rows.sort(key=lambda row: (int(row.get("review_priority") or 999), str(row.get("category") or "")))
    app_visual_catalog = payload.get("app_folder_visual_catalog") or {}
    if not isinstance(app_visual_catalog, dict):
        app_visual_catalog = {}
    if not app_visual_catalog and isinstance(normalization_review, dict):
        app_visual_catalog = normalization_review.get("app_folder_visual_catalog") or {}
        if not isinstance(app_visual_catalog, dict):
            app_visual_catalog = {}

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
                "manual_confirmation_template": CONFIRMED_TEMPLATE,
                "confirmed_queue": CONFIRMED_QUEUE,
                "import_tool": IMPORT_TOOL,
                "unblocks_when": UNBLOCKS_WHEN,
                "categories": chunk,
            }
        )
    for offset in range(0, len(normalization_rows), batch_size):
        chunk = normalization_rows[offset : offset + batch_size]
        target_counts = Counter(str(row.get("suggested_category") or "") for row in chunk)
        batches.append(
            {
                "batch_id": f"animation-category-normalization-{(offset // batch_size) + 1:03d}",
                "priority": min(int(row.get("review_priority") or 999) for row in chunk),
                "category_count": len(chunk),
                "affected_catalog_rows": sum(int(row.get("rows") or 0) for row in chunk),
                "target_category_counts": target_counts.most_common(),
                "review_state": "manual_canonical_category_normalization_required",
                "next_machine_step": "confirm_canonical_animation_category_normalization",
                "manual_confirmation_template": CONFIRMED_TEMPLATE,
                "confirmed_queue": CONFIRMED_QUEUE,
                "import_tool": IMPORT_TOOL,
                "unblocks_when": "canonical_category_normalization_manually_confirmed",
                "categories": chunk,
            }
        )

    all_rows = sum(int(row.get("rows") or 0) for row in rows)
    queued_rows = sum(int(row.get("rows") or 0) for row in queued)
    mapping_mode_counts = Counter(str(row.get("mapping_mode") or "") for row in rows)
    blocked_reason_counts = Counter(str(row.get("blocked_reason") or "") for row in rows)
    blocked_reason_counts.pop("", None)
    blocked_until_counts = Counter(str(row.get("blocked_until") or "") for row in rows)
    blocked_until_counts.pop("", None)
    unmatched_summary = (
        unmatched_keyword_review.get("summary")
        if isinstance(unmatched_keyword_review, dict)
        and isinstance(unmatched_keyword_review.get("summary"), dict)
        else {}
    )
    work_order = _work_order(queued, unmatched_keyword_review, normalization_rows)
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
        "by_blocked_reason": blocked_reason_counts.most_common(),
        "by_blocked_until": blocked_until_counts.most_common(),
        "split_review_categories": sum(1 for row in rows if _requires_split_review(row)),
        "direct_mapping_categories": sum(1 for row in rows if not _requires_split_review(row)),
        "normalization_review_categories": len(normalization_rows),
        "normalization_review_rows": sum(int(row.get("rows") or 0) for row in normalization_rows),
        "normalization_review_target_categories": Counter(
            str(row.get("suggested_category") or "") for row in normalization_rows
        ).most_common(),
        "app_folder_color_count": int(app_visual_catalog.get("color_count") or 0),
        "app_folder_icon_option_count": int(app_visual_catalog.get("icon_count") or 0),
        "app_folder_icon_group_count": int(app_visual_catalog.get("icon_group_count") or 0),
        "app_folder_palette_section_count": int(app_visual_catalog.get("palette_section_count") or 0),
        "app_folder_palette_sorted_by_family": bool(app_visual_catalog.get("palette_sorted_by_family")),
        "app_animation_visuals_covered": bool(app_visual_catalog.get("animation_visuals_covered")),
        "work_order_steps": len(work_order),
        "work_order_lanes": [
            str(row.get("lane") or "") for row in work_order if str(row.get("lane") or "")
        ],
        "split_first_blocked_categories": [
            category
            for row in work_order
            if row.get("lane") == "name_level_split_review"
            for category in row.get("blocked_direct_mapping_categories", [])
        ],
        "unmatched_keyword_review_rows": int(unmatched_summary.get("unmatched_rows") or 0),
        "unmatched_keyword_candidate_count": int(unmatched_summary.get("token_candidate_count") or 0),
        "unmatched_keyword_product_type_candidate_count": int(
            unmatched_summary.get("product_type_candidate_count") or 0
        ),
        "auto_apply_enabled": False,
    }
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "animation_category_action_queue",
        "summary": summary,
        "app_folder_visual_catalog": app_visual_catalog,
        "work_order": work_order,
        "batches": batches,
        "automation_policy": {
            "auto_apply_category_changes": False,
            "auto_create_folders": False,
            "requires_manual_review": True,
            "manual_confirmation_template": CONFIRMED_TEMPLATE,
            "confirmed_queue": CONFIRMED_QUEUE,
            "import_tool": IMPORT_TOOL,
            "unblocks_when": UNBLOCKS_WHEN,
            "blocked_until_default": "category_mapping_or_split_rules_manually_confirmed",
            "required_evidence": [
                "sample_names_match_target_product_type",
                "broad_categories_split_before_mapping",
                "folder_color_and_icon_exist_in_app_catalog",
                "manual_confirmation_for_public_template_rows",
            ],
            "reason": "Category mappings affect app navigation and user-facing folders.",
        },
        "instructions": [
            "Confirm each category_mapping_template before any catalog mutation.",
            "Split broad source categories such as acrylic before applying a single folder mapping.",
            "Review unmatched keyword candidates after the first split pass to reduce broad goods/category leftovers.",
            "Keep folder colors ordered by color_group/sort_order so similar colors remain grouped.",
            f"Copy confirmed category_mapping_template rows into {CONFIRMED_QUEUE}, set manual_confirmed=true, then run {IMPORT_TOOL}.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--unmatched-keyword-review", type=Path, default=DEFAULT_UNMATCHED_KEYWORD_REVIEW)
    parser.add_argument("--normalization-input", type=Path, default=DEFAULT_NORMALIZATION_INPUT)
    parser.add_argument("--max-categories", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=6)
    args = parser.parse_args()

    unmatched_keyword_review = (
        _load(args.unmatched_keyword_review)
        if args.unmatched_keyword_review.exists()
        else None
    )
    queue = build_queue(
        _load(args.input),
        max_categories=args.max_categories,
        batch_size=args.batch_size,
        unmatched_keyword_review=unmatched_keyword_review,
        normalization_review=_load(args.normalization_input) if args.normalization_input.exists() else None,
    )
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(queue["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
