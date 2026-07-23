from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_public.json"
DEFAULT_OUTPUT = DATA / "ichiban_kuji_prize_name_image_review_public.json"

KUJI_PREFIX = "https://1kuji.com/products/"
LAST_ONE_LABEL = "ラストワン賞"
DOUBLE_CHANCE_LABEL = "ダブルチャンスキャンペーン"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def is_kuji_row(row: dict[str, Any]) -> bool:
    source_url = str(row.get("source_url") or "")
    source_store = str(row.get("source_store") or "")
    series_name = str(row.get("series_name") or "")
    name_ko = str(row.get("name_ko") or "")
    return (
        source_url.startswith(KUJI_PREFIX)
        or "1kuji.com" in source_url
        or source_store == "이치방쿠지"
        or "一番くじ" in series_name
        or "一番くじ" in name_ko
    )


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def expected_prize_display_name(row: dict[str, Any]) -> str:
    prize_rank = str(row.get("sub_series") or "").strip()
    prize_item_name = str(row.get("name_ja") or "").strip()
    if not prize_rank:
        return prize_item_name
    if not prize_item_name:
        return prize_rank
    if prize_item_name.startswith(prize_rank):
        return prize_item_name
    return f"{prize_rank} {prize_item_name}"


def expected_name_ko(row: dict[str, Any]) -> str:
    series_name = str(row.get("series_name") or "").strip()
    prize_display_name = expected_prize_display_name(row)
    if series_name and prize_display_name:
        return f"{series_name} - {prize_display_name}"
    return series_name or prize_display_name


def prize_label_matches_name(row: dict[str, Any]) -> bool:
    sub_series = str(row.get("sub_series") or "")
    name_ja = str(row.get("name_ja") or "")
    if not sub_series or not name_ja:
        return False
    if name_ja.startswith(sub_series):
        return True
    if sub_series == LAST_ONE_LABEL and ("ラストワン" in name_ja or "最後の1個" in name_ja):
        return True
    if sub_series == DOUBLE_CHANCE_LABEL and ("ダブルチャンス" in name_ja or "当選" in name_ja):
        return True
    return False


def compact_row(row: dict[str, Any], *, review_reason: str) -> dict[str, Any]:
    return {
        "manual_review_status": "not_started",
        "manual_confirmed": False,
        "catalog_index": row.get("catalog_index"),
        "series_name": row.get("series_name"),
        "prize_rank": row.get("sub_series"),
        "prize_item_name": row.get("name_ja"),
        "expected_prize_display_name": expected_prize_display_name(row),
        "display_name_ko": row.get("name_ko"),
        "expected_display_name_ko": expected_name_ko(row),
        "category": row.get("category"),
        "character_name": row.get("character_name"),
        "official_price_jpy": row.get("official_price_jpy"),
        "release_date": row.get("release_date"),
        "source_url": row.get("source_url"),
        "image_url": row.get("image_url"),
        "local_image_path": row.get("local_image_path"),
        "review_reason": review_reason,
        "name_policy": {
            "required_components": [
                "ichiban_release_name(series_name)",
                "prize_rank(sub_series)",
                "prize_item_name(name_ja)",
                "variant_or_character_detail_when_multiple_items_share_the_same_prize_rank",
            ],
            "display_name_ko_format": "<series_name> - <sub_series/prize item name>",
            "same_prize_multiple_items_rule": (
                "Keep each official item as a separate row and include numbering, character, color, or item-type detail in name_ja."
            ),
        },
        "image_review_policy": {
            "requires_same_campaign": True,
            "requires_same_prize_rank": True,
            "requires_same_variant_or_item": True,
            "do_not_reuse_neighbor_prize_image_without_official_lineup_match": True,
        },
        "manual_fix_template": {
            "catalog_index": row.get("catalog_index"),
            "name_ko": "<confirmed_display_name_or_blank>",
            "name_ja": "<confirmed_prize_item_name_or_blank>",
            "sub_series": "<confirmed_prize_rank_or_blank>",
            "image_url": "<confirmed_official_image_url_or_blank>",
            "evidence_url": row.get("source_url"),
            "manual_confirmed": False,
        },
        "auto_apply_enabled": False,
    }


def build_report(catalog: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    rows = [row for row in catalog.get("items", []) if isinstance(row, dict) and is_kuji_row(row)]
    name_structure_rows: list[dict[str, Any]] = []
    image_identity_rows: list[dict[str, Any]] = []

    groups_by_prize: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    groups_by_name: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    groups_by_image: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups_by_prize[(str(row.get("source_url") or ""), str(row.get("sub_series") or ""))].append(row)
        groups_by_name[
            (
                str(row.get("source_url") or ""),
                str(row.get("sub_series") or ""),
                str(row.get("name_ja") or ""),
            )
        ].append(row)
        groups_by_image[(str(row.get("source_url") or ""), str(row.get("image_url") or ""))].append(row)

        if not present(row.get("series_name")) or not present(row.get("sub_series")) or not present(row.get("name_ja")):
            name_structure_rows.append(compact_row(row, review_reason="missing_required_name_component"))
            continue
        if str(row.get("name_ko") or "") != expected_name_ko(row):
            name_structure_rows.append(compact_row(row, review_reason="display_name_does_not_match_series_and_prize_name"))
            continue
    duplicate_name_rows = []
    for group_rows in groups_by_name.values():
        if len(group_rows) > 1:
            duplicate_name_rows.extend(group_rows)
    for row in duplicate_name_rows:
        name_structure_rows.append(compact_row(row, review_reason="same_campaign_prize_rank_and_name_duplicate"))

    reused_image_rows = []
    for group_rows in groups_by_image.values():
        names = {str(row.get("name_ja") or "") for row in group_rows}
        if len(group_rows) > 1 and len(names) > 1:
            reused_image_rows.extend(group_rows)
    for row in reused_image_rows:
        image_identity_rows.append(compact_row(row, review_reason="same_campaign_image_used_by_different_prize_names"))

    multi_item_groups = [
        {
            "source_url": source_url,
            "prize_rank": prize_rank,
            "row_count": len(group_rows),
            "requires_variant_detail": True,
            "sample_rows": [
                {
                    "catalog_index": row.get("catalog_index"),
                    "name_ja": row.get("name_ja"),
                    "image_url": row.get("image_url"),
                }
                for row in group_rows[:12]
            ],
        }
        for (source_url, prize_rank), group_rows in groups_by_prize.items()
        if source_url and prize_rank and len(group_rows) > 1
    ]
    multi_item_groups.sort(key=lambda row: (-int(row["row_count"]), row["source_url"], row["prize_rank"]))

    review_rows_by_index: dict[Any, dict[str, Any]] = {}
    for row in name_structure_rows + image_identity_rows:
        review_rows_by_index.setdefault(row.get("catalog_index"), row)
    review_rows = sorted(
        review_rows_by_index.values(),
        key=lambda row: (str(row.get("source_url") or ""), str(row.get("prize_rank") or ""), int(row.get("catalog_index") or 0)),
    )

    reason_counts = Counter(str(row.get("review_reason") or "unknown") for row in review_rows)
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "ichiban_kuji_prize_name_image_review",
        "summary": {
            "kuji_rows": len(rows),
            "review_rows": len(review_rows),
            "name_structure_review_rows": len({row.get("catalog_index") for row in name_structure_rows}),
            "image_identity_review_rows": len({row.get("catalog_index") for row in image_identity_rows}),
            "same_campaign_prize_rank_name_duplicate_rows": len({row.get("catalog_index") for row in duplicate_name_rows}),
            "same_campaign_image_reused_different_name_rows": len({row.get("catalog_index") for row in reused_image_rows}),
            "multi_item_prize_rank_groups": len(multi_item_groups),
            "multi_item_prize_rank_catalog_rows": sum(int(group.get("row_count") or 0) for group in multi_item_groups),
            "review_reason_counts": reason_counts.most_common(),
            "auto_apply_enabled": False,
            "recommended_next_action": "confirm_ichiban_prize_names_and_images_against_official_campaign_lineups",
        },
        "name_policy": {
            "display_name_ko_format": "<ichiban_release_name> - <prize_rank> <prize_item_name_or_variant>",
            "fields": {
                "ichiban_release_name": "series_name",
                "prize_rank": "sub_series",
                "prize_item_name": "name_ja",
                "variant_or_character_detail": "name_ja / character_name / numbered_variant",
            },
            "last_one_and_double_chance_price_jpy": 0,
            "auto_apply_enabled": False,
        },
        "review_rows": review_rows[:400],
        "multi_item_prize_rank_groups": multi_item_groups[:120],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
