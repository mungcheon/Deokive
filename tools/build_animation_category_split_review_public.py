from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "animation_category_action_queue_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "animation_category_split_review_public.json"
CONFIRMED_TEMPLATE = "server/animation_category_name_split_confirmed_rows.template.json"
CONFIRMED_QUEUE = "server/animation_category_name_split_confirmed_rows.json"
IMPORT_TOOL = "tools/import_confirmed_animation_category_rows.py"
UNBLOCKS_WHEN = "name_level_split_manually_confirmed"


SPLIT_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "figure",
        "target_category": "피규어",
        "target_family": "figure",
        "folder_color_group": "green",
        "folder_color_hint": "mint",
        "folder_color_hex": "0xFF63D6A8",
        "folder_color_sort_order": 430,
        "folder_icon_key": "toys",
        "folder_icon_options": ["toys", "view_in_ar", "emoji_events", "category"],
        "match_keywords": ["フィギュア", "MASTERLISE", "figure", "피규어", "넨도로이드", "ねんどろいど"],
    },
    {
        "rule_id": "acrylic_stand",
        "target_category": "아크릴 스탠드",
        "target_family": "acrylic",
        "folder_color_group": "blue",
        "folder_color_hint": "sky",
        "folder_color_hex": "0xFF7DB7FF",
        "folder_color_sort_order": 220,
        "folder_icon_key": "view_carousel",
        "folder_icon_options": ["view_carousel", "crop_portrait", "badge", "category"],
        "match_keywords": ["アクリルスタンド", "アクスタ", "아크릴 스탠드", "acrylic stand", "stand"],
    },
    {
        "rule_id": "acrylic_keyring",
        "target_category": "아크릴 키링",
        "target_family": "keyring",
        "folder_color_group": "blue",
        "folder_color_hint": "aqua",
        "folder_color_hex": "0xFF66CFE8",
        "folder_color_sort_order": 235,
        "folder_icon_key": "local_offer",
        "folder_icon_options": ["local_offer", "key", "sell", "category"],
        "match_keywords": ["アクリルキーホルダー", "アクキー", "아크릴 키링", "아크릴 키홀더", "acrylic key"],
    },
    {
        "rule_id": "badge",
        "target_category": "캔뱃지",
        "target_family": "badge",
        "folder_color_group": "red",
        "folder_color_hint": "rose",
        "folder_color_hex": "0xFFFF8B9A",
        "folder_color_sort_order": 520,
        "folder_icon_key": "verified",
        "folder_icon_options": ["verified", "military_tech", "workspace_premium", "category"],
        "match_keywords": ["缶バッジ", "缶バッヂ", "캔뱃지", "캔배지", "badge", "バッジ"],
    },
    {
        "rule_id": "plush",
        "target_category": "인형",
        "target_family": "plush",
        "folder_color_group": "pink",
        "folder_color_hint": "pink",
        "folder_color_hex": "0xFFFF9BC7",
        "folder_color_sort_order": 540,
        "folder_icon_key": "face",
        "folder_icon_options": ["face", "child_care", "toys", "category"],
        "match_keywords": ["ぬいぐるみ", "ぬい", "マスコット", "인형", "마스코트", "plush", "nuigurumi"],
    },
    {
        "rule_id": "stationery",
        "target_category": "문구",
        "target_family": "stationery",
        "folder_color_group": "purple",
        "folder_color_hint": "lavender",
        "folder_color_hex": "0xFFB9A7FF",
        "folder_color_sort_order": 620,
        "folder_icon_key": "sticky_note_2",
        "folder_icon_options": ["sticky_note_2", "edit_note", "article", "category"],
        "match_keywords": ["ステーショナリー", "クリアファイル", "ステッカー", "ポストカード", "シール", "문구", "스티커", "카드", "file"],
    },
    {
        "rule_id": "board",
        "target_category": "보드",
        "target_family": "display",
        "folder_color_group": "neutral",
        "folder_color_hint": "stone",
        "folder_color_hex": "0xFFB8B8C7",
        "folder_color_sort_order": 130,
        "folder_icon_key": "dashboard",
        "folder_icon_options": ["dashboard", "wallpaper", "photo_size_select_actual", "category"],
        "match_keywords": ["ボード", "보드", "board", "キャンバス"],
    },
    {
        "rule_id": "towel_daily_goods",
        "target_category": "생활잡화",
        "target_family": "daily_goods",
        "folder_color_group": "yellow",
        "folder_color_hint": "lemon",
        "folder_color_hex": "0xFFFFDE66",
        "folder_color_sort_order": 720,
        "folder_icon_key": "inventory_2",
        "folder_icon_options": ["inventory_2", "redeem", "local_mall", "category"],
        "match_keywords": ["タオル", "컵", "マグ", "グラス", "파우치", "ポーチ", "towel", "mug", "pouch"],
    },
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _split_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for batch in payload.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for row in batch.get("categories", []):
            if isinstance(row, dict) and row.get("requires_name_level_split_review"):
                rows.append(row)
    return rows


def _matches(name: str, keywords: list[str]) -> bool:
    normalized = name.casefold()
    return any(keyword.casefold() in normalized for keyword in keywords)


def _candidate_template(source_category: str, rule: dict[str, Any], matched_samples: list[str]) -> dict[str, Any]:
    return {
        "manual_confirmed": False,
        "source_category": source_category,
        "match_keywords": rule["match_keywords"],
        "target_category": rule["target_category"],
        "target_family": rule["target_family"],
        "folder_name": rule["target_category"],
        "folder_color_hex": rule["folder_color_hex"],
        "folder_color_hint": rule["folder_color_hint"],
        "folder_color_group": rule["folder_color_group"],
        "folder_color_sort_order": rule["folder_color_sort_order"],
        "folder_icon_key": rule["folder_icon_key"],
        "folder_icon_options": rule["folder_icon_options"],
        "matched_sample_count": len(matched_samples),
        "matched_sample_names": matched_samples[:8],
        "blocked_until": UNBLOCKS_WHEN,
        "review_evidence_required": [
            "keywords_match_actual_goods_type",
            "same_prize_letter_variants_are_kept_as_separate_catalog_rows",
            "broad_source_category_is_not_applied_as_one_folder",
            "folder_color_and_icon_exist_in_app_catalog",
        ],
    }


def _review_item(row: dict[str, Any]) -> dict[str, Any]:
    source_category = str(row.get("category") or "").strip()
    samples = [str(name) for name in row.get("sample_names", []) if str(name).strip()]
    used_samples: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for rule in SPLIT_RULES:
        matched = [name for name in samples if _matches(name, rule["match_keywords"])]
        if matched:
            used_samples.update(matched)
            candidates.append(
                {
                    "rule_id": rule["rule_id"],
                    "target_category": rule["target_category"],
                    "target_family": rule["target_family"],
                    "folder_color_group": rule["folder_color_group"],
                    "folder_color_hint": rule["folder_color_hint"],
                    "folder_icon_key": rule["folder_icon_key"],
                    "match_keywords": rule["match_keywords"],
                    "matched_sample_count": len(matched),
                    "matched_sample_names": matched[:8],
                    "name_level_split_template": _candidate_template(source_category, rule, matched),
                }
            )

    unmatched = [name for name in samples if name not in used_samples]
    return {
        "source_category": source_category,
        "affected_catalog_rows": int(row.get("rows") or 0),
        "suggested_default_category": row.get("suggested_category") or source_category,
        "review_reason": row.get("review_reason"),
        "sample_names": samples[:8],
        "split_candidate_count": len(candidates),
        "matched_sample_count": sum(int(candidate["matched_sample_count"]) for candidate in candidates),
        "unmatched_sample_count": len(unmatched),
        "split_candidates": candidates,
        "unmatched_sample_names": unmatched[:8],
        "manual_confirmation_template": CONFIRMED_TEMPLATE,
        "confirmed_queue": CONFIRMED_QUEUE,
        "import_tool": IMPORT_TOOL,
        "unblocks_when": UNBLOCKS_WHEN,
        "auto_apply_enabled": False,
    }


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [_review_item(row) for row in _split_rows(payload)]
    rows.sort(key=lambda row: (-int(row.get("affected_catalog_rows") or 0), str(row.get("source_category") or "")))
    family_counts = Counter(
        candidate["target_family"] for row in rows for candidate in row.get("split_candidates", [])
    )
    matched_samples = sum(int(row.get("matched_sample_count") or 0) for row in rows)
    unmatched_samples = sum(int(row.get("unmatched_sample_count") or 0) for row in rows)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "animation_category_name_level_split_review",
        "summary": {
            "split_review_categories": len(rows),
            "affected_catalog_rows": sum(int(row.get("affected_catalog_rows") or 0) for row in rows),
            "candidate_split_rules": sum(int(row.get("split_candidate_count") or 0) for row in rows),
            "matched_sample_names": matched_samples,
            "unmatched_sample_names": unmatched_samples,
            "by_target_family": family_counts.most_common(),
            "manual_confirmed_rows": 0,
            "auto_apply_enabled": False,
        },
        "review_items": rows,
        "automation_policy": {
            "auto_apply_category_changes": False,
            "auto_create_folders": False,
            "requires_manual_review": True,
            "manual_confirmation_template": CONFIRMED_TEMPLATE,
            "confirmed_queue": CONFIRMED_QUEUE,
            "import_tool": IMPORT_TOOL,
            "unblocks_when": UNBLOCKS_WHEN,
            "reason": "Broad animation categories need name-level evidence before changing catalog categories or app folders.",
        },
        "instructions": [
            "Review each name_level_split_template and set manual_confirmed=true only after checking real item names.",
            "Leave unmatched_sample_names in the source category until a safer keyword or official category is confirmed.",
            "Use price and release metadata from the existing catalog; this report only prepares category/folder changes.",
            "Folder colors remain grouped by color family so similar colors stay sorted together in the app.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = build_report(_load(args.input))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
