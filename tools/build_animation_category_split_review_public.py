from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "animation_category_action_queue_public.json"
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
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
        "match_keywords": [
            "アクリルスタンド",
            "アクリルペンスタンド",
            "アクスタ",
            "ピックリルスタンド",
            "피크릴",
            "아크릴 스탠드",
            "아크릴 펜스탠드",
            "아크릴 펜 스탠드",
            "acrylic stand",
            "stand",
        ],
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
        "rule_id": "shikishi_board",
        "target_category": "색지",
        "target_family": "stationery",
        "folder_color_group": "purple",
        "folder_color_hint": "lilac",
        "folder_color_hex": "0xFFC4B5FD",
        "folder_color_sort_order": 625,
        "folder_icon_key": "article",
        "folder_icon_options": ["article", "sticky_note_2", "wallpaper", "category"],
        "match_keywords": ["색지", "色紙", "shikishi", "mini shikishi"],
    },
    {
        "rule_id": "sticker",
        "target_category": "스티커",
        "target_family": "stationery",
        "folder_color_group": "purple",
        "folder_color_hint": "violet",
        "folder_color_hex": "0xFFA78BFA",
        "folder_color_sort_order": 630,
        "folder_icon_key": "sticky_note_2",
        "folder_icon_options": ["sticky_note_2", "sell", "article", "category"],
        "match_keywords": ["스티커", "ステッカー", "シール", "sticker", "seal"],
    },
    {
        "rule_id": "card_bromide",
        "target_category": "카드/브로마이드",
        "target_family": "stationery",
        "folder_color_group": "purple",
        "folder_color_hint": "lavender",
        "folder_color_hex": "0xFFB9A7FF",
        "folder_color_sort_order": 635,
        "folder_icon_key": "view_carousel",
        "folder_icon_options": ["view_carousel", "style", "photo_library", "category"],
        "match_keywords": ["카드", "브로마이드", "カード", "ブロマイド", "トレーディングカード", "card", "bromide"],
    },
    {
        "rule_id": "clear_file",
        "target_category": "클리어 파일",
        "target_family": "stationery",
        "folder_color_group": "purple",
        "folder_color_hint": "periwinkle",
        "folder_color_hex": "0xFFA5B4FC",
        "folder_color_sort_order": 640,
        "folder_icon_key": "folder",
        "folder_icon_options": ["folder", "article", "inventory_2", "category"],
        "match_keywords": ["클리어 파일", "클리어파일", "クリアファイル", "clear file"],
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
        "match_keywords": [
            "タオル",
            "컵",
            "マグ",
            "グラス",
            "파우치",
            "ポーチ",
            "アクリルライト",
            "아크릴 라이트",
            "towel",
            "mug",
            "pouch",
        ],
    },
    {
        "rule_id": "tableware_daily_goods",
        "target_category": "생활잡화",
        "target_family": "daily_goods",
        "folder_color_group": "yellow",
        "folder_color_hint": "cream",
        "folder_color_hex": "0xFFF6D365",
        "folder_color_sort_order": 725,
        "folder_icon_key": "local_cafe",
        "folder_icon_options": ["local_cafe", "inventory_2", "redeem", "category"],
        "match_keywords": [
            "식기",
            "그릇",
            "접시",
            "컵",
            "머그",
            "食器",
            "皿",
            "プレート",
            "グラス",
            "カップ",
            "マグ",
            "tableware",
            "plate",
            "glass",
            "cup",
            "mug",
        ],
    },
    {
        "rule_id": "rubber_goods",
        "target_category": "액세서리",
        "target_family": "accessory",
        "folder_color_group": "orange",
        "folder_color_hint": "apricot",
        "folder_color_hex": "0xFFFFB36B",
        "folder_color_sort_order": 740,
        "folder_icon_key": "style",
        "folder_icon_options": ["style", "local_offer", "sell", "category"],
        "match_keywords": ["ラバーコレクション", "ラバーアソート", "ラバーチャーム", "rubber charm"],
    },
    {
        "rule_id": "acrylic_charm",
        "target_category": "아크릴 키링",
        "target_family": "keyring",
        "folder_color_group": "blue",
        "folder_color_hint": "aqua",
        "folder_color_hex": "0xFF66CFE8",
        "folder_color_sort_order": 238,
        "folder_icon_key": "local_offer",
        "folder_icon_options": ["local_offer", "key", "sell", "category"],
        "match_keywords": [
            "アクリルチャーム",
            "ツインアクリルチャーム",
            "アクリルコレクション",
            "アクリル雑貨アソート",
            "スクールアイコンボタン",
        ],
    },
    {
        "rule_id": "collab_goods",
        "target_category": "콜라보 굿즈",
        "target_family": "collab_goods",
        "folder_color_group": "orange",
        "folder_color_hint": "coral",
        "folder_color_hex": "0xFFFFA36A",
        "folder_color_sort_order": 760,
        "folder_icon_key": "diversity_3",
        "folder_icon_options": ["diversity_3", "handshake", "style", "category"],
        "match_keywords": [
            "콜라보",
            "コラボ",
            "collab",
            "부쿠부",
            "ぶくぶ",
            "大川ぶくぶ",
            "오오카와",
            "팝팀애픽",
            "ポプテピピック",
        ],
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


def _candidate_template(
    source_category: str,
    rule: dict[str, Any],
    matched_samples: list[str],
    *,
    expected_update_rows: int = 0,
) -> dict[str, Any]:
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
        "expected_update_rows": expected_update_rows,
        "matched_catalog_row_count": expected_update_rows,
        "matched_sample_names": matched_samples[:8],
        "blocked_until": UNBLOCKS_WHEN,
        "review_evidence_required": [
            "keywords_match_actual_goods_type",
            "same_prize_letter_variants_are_kept_as_separate_catalog_rows",
            "broad_source_category_is_not_applied_as_one_folder",
            "folder_color_and_icon_exist_in_app_catalog",
        ],
    }


def _catalog_rows(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        raw_rows = payload.get("items", [])
    else:
        raw_rows = payload
    return [row for row in raw_rows if isinstance(row, dict)]


def _item_name(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "name_en", "series_name", "sub_series")
        if str(row.get(field) or "").strip()
    )


def _catalog_sample(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "category": row.get("category"),
        "affiliation": row.get("affiliation"),
        "series_name": row.get("series_name"),
        "sub_series": row.get("sub_series"),
        "source_store": row.get("source_store"),
    }


def _catalog_row_id(row: dict[str, Any]) -> Any:
    if row.get("catalog_index") is not None:
        return row.get("catalog_index")
    return (_item_name(row), row.get("category"), row.get("source_store"))


def _catalog_matches_for_rule(catalog_rows: list[dict[str, Any]], rule: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in catalog_rows if _matches(_item_name(row), rule["match_keywords"])]


def _review_item(row: dict[str, Any], catalog_rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_category = str(row.get("category") or "").strip()
    samples = [str(name) for name in row.get("sample_names", []) if str(name).strip()]
    source_catalog_rows = [
        catalog_row for catalog_row in catalog_rows if str(catalog_row.get("category") or "").strip() == source_category
    ]
    used_samples: set[str] = set()
    used_catalog_indexes: set[Any] = set()
    candidates: list[dict[str, Any]] = []
    for rule in SPLIT_RULES:
        matched = [name for name in samples if _matches(name, rule["match_keywords"])]
        catalog_matches = _catalog_matches_for_rule(source_catalog_rows, rule)
        if matched or catalog_matches:
            used_samples.update(matched)
            used_catalog_indexes.update(_catalog_row_id(row) for row in catalog_matches)
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
                    "matched_catalog_row_count": len(catalog_matches),
                    "matched_catalog_samples": [_catalog_sample(catalog_row) for catalog_row in catalog_matches[:8]],
                    "name_level_split_template": _candidate_template(
                        source_category,
                        rule,
                        matched,
                        expected_update_rows=len(catalog_matches),
                    ),
                }
            )

    unmatched = [name for name in samples if name not in used_samples]
    unmatched_catalog_rows = [
        catalog_row for catalog_row in source_catalog_rows if _catalog_row_id(catalog_row) not in used_catalog_indexes
    ]
    return {
        "source_category": source_category,
        "affected_catalog_rows": int(row.get("rows") or 0),
        "catalog_category_rows": len(source_catalog_rows),
        "suggested_default_category": row.get("suggested_category") or source_category,
        "review_reason": row.get("review_reason"),
        "sample_names": samples[:8],
        "split_candidate_count": len(candidates),
        "matched_sample_count": sum(int(candidate["matched_sample_count"]) for candidate in candidates),
        "unmatched_sample_count": len(unmatched),
        "matched_catalog_rule_hit_count": sum(int(candidate["matched_catalog_row_count"]) for candidate in candidates),
        "matched_catalog_row_count": len(used_catalog_indexes),
        "unmatched_catalog_row_count": len(unmatched_catalog_rows),
        "split_candidates": candidates,
        "unmatched_sample_names": unmatched[:8],
        "unmatched_catalog_samples": [_catalog_sample(catalog_row) for catalog_row in unmatched_catalog_rows[:8]],
        "manual_confirmation_template": CONFIRMED_TEMPLATE,
        "confirmed_queue": CONFIRMED_QUEUE,
        "import_tool": IMPORT_TOOL,
        "unblocks_when": UNBLOCKS_WHEN,
        "auto_apply_enabled": False,
    }


def build_report(payload: dict[str, Any], catalog_payload: dict[str, Any] | list[Any] | None = None) -> dict[str, Any]:
    catalog_rows = _catalog_rows(catalog_payload or {})
    rows = [_review_item(row, catalog_rows) for row in _split_rows(payload)]
    rows.sort(key=lambda row: (-int(row.get("affected_catalog_rows") or 0), str(row.get("source_category") or "")))
    candidate_priority_queue: list[dict[str, Any]] = []
    for row in rows:
        for candidate in row.get("split_candidates", []):
            if not isinstance(candidate, dict):
                continue
            candidate_priority_queue.append(
                {
                    "source_category": row.get("source_category"),
                    "rule_id": candidate.get("rule_id"),
                    "target_category": candidate.get("target_category"),
                    "target_family": candidate.get("target_family"),
                    "folder_color_group": candidate.get("folder_color_group"),
                    "folder_color_hint": candidate.get("folder_color_hint"),
                    "folder_icon_key": candidate.get("folder_icon_key"),
                    "expected_update_rows": int(candidate.get("matched_catalog_row_count") or 0),
                    "matched_sample_count": int(candidate.get("matched_sample_count") or 0),
                    "matched_sample_names": candidate.get("matched_sample_names") or [],
                    "matched_catalog_samples": candidate.get("matched_catalog_samples") or [],
                    "manual_confirmation_template": candidate.get("name_level_split_template") or {},
                    "blocked_until": UNBLOCKS_WHEN,
                    "auto_apply_enabled": False,
                }
            )
    candidate_priority_queue.sort(
        key=lambda candidate: (
            -int(candidate.get("expected_update_rows") or 0),
            -int(candidate.get("matched_sample_count") or 0),
            str(candidate.get("source_category") or ""),
            str(candidate.get("rule_id") or ""),
        )
    )
    starter_confirmed_queue = {
        "schema_version": 1,
        "source_report": str(DEFAULT_OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "target_queue": CONFIRMED_QUEUE,
        "import_tool": IMPORT_TOOL,
        "manual_confirmed_default": False,
        "instructions": [
            "Review each item, then set manual_confirmed=true only for rules whose keywords match the goods type.",
            "Save confirmed items to server/animation_category_name_split_confirmed_rows.json before running the import tool.",
            "Keep count checks enabled unless the catalog was regenerated after this report.",
        ],
        "items": [
            dict(candidate.get("manual_confirmation_template") or {})
            for candidate in candidate_priority_queue
        ],
    }
    family_counts = Counter(
        candidate["target_family"] for row in rows for candidate in row.get("split_candidates", [])
    )
    matched_samples = sum(int(row.get("matched_sample_count") or 0) for row in rows)
    unmatched_samples = sum(int(row.get("unmatched_sample_count") or 0) for row in rows)
    matched_catalog_rule_hits = sum(int(row.get("matched_catalog_rule_hit_count") or 0) for row in rows)
    matched_catalog_rows = sum(int(row.get("matched_catalog_row_count") or 0) for row in rows)
    unmatched_catalog_rows = sum(int(row.get("unmatched_catalog_row_count") or 0) for row in rows)
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
            "catalog_scan_enabled": bool(catalog_rows),
            "catalog_source_category_rows": sum(int(row.get("catalog_category_rows") or 0) for row in rows),
            "matched_catalog_rule_hits": matched_catalog_rule_hits,
            "matched_catalog_rows": matched_catalog_rows,
            "unmatched_catalog_rows": unmatched_catalog_rows,
            "by_target_family": family_counts.most_common(),
            "candidate_priority_rows": len(candidate_priority_queue),
            "starter_confirmed_queue_rows": len(starter_confirmed_queue["items"]),
            "top_candidate_expected_update_rows": int(
                candidate_priority_queue[0].get("expected_update_rows") or 0
            )
            if candidate_priority_queue
            else 0,
            "top_candidate_source_category": candidate_priority_queue[0].get("source_category")
            if candidate_priority_queue
            else None,
            "top_candidate_target_category": candidate_priority_queue[0].get("target_category")
            if candidate_priority_queue
            else None,
            "manual_confirmed_rows": 0,
            "auto_apply_enabled": False,
        },
        "review_items": rows,
        "candidate_priority_queue": candidate_priority_queue,
        "starter_confirmed_queue": starter_confirmed_queue,
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
            "Use candidate_priority_queue to confirm the largest name-level split rules first.",
            "Use price and release metadata from the existing catalog; this report only prepares category/folder changes.",
            "Folder colors remain grouped by color family so similar colors stay sorted together in the app.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    catalog_payload: dict[str, Any] | list[Any] | None = None
    if args.catalog.exists():
        catalog_payload = json.loads(args.catalog.read_text(encoding="utf-8"))
    report = build_report(_load(args.input), catalog_payload)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
