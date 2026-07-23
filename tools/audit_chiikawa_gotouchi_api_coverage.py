from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from enrich_chiikawa_gotouchi_jp_api_images import (
    DEFAULT_SOURCE_URL,
    _aliases_for_theme,
    _aliases_for_type,
    _official_parts,
    fetch_official_images,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "server" / "chiikawa_gotouchi_api_coverage_audit.json"
CHIIKAWA_MARKET_NAMES = {"치이카와 마켓", "ご当地ちいかわ 공식(API)"}
GOTOCHI_MARKERS = {"ご当地"}

THEME_ALIASES: dict[str, tuple[str, ...]] = {
    "東京タワー": ("도쿄타워", "도쿄 타워", "東京タワー"),
    "スカイツリー": ("스카이트리", "スカイツリー"),
    "雷門": ("카미나리몬", "雷門"),
    "大阪": ("오사카", "大阪"),
    "たこ焼き": ("타코야키", "たこ焼き"),
    "富士山": ("후지산", "시즈오카 후지산", "富士山"),
    "伏見稲荷": ("후시미이나리", "伏見稲荷"),
    "舞妓はん": ("마이코", "舞妓"),
    "鹿": ("나라 사슴", "사슴", "鹿"),
    "忍者": ("닌자", "忍者"),
    "ラベンダー": ("라벤더", "ラベンダー"),
    "シマエナガ": ("시마에나가", "シマエナガ"),
    "カンフー": ("쿵푸", "カンフー"),
    "香港": ("홍콩", "香港"),
    "小樽運河": ("오타루", "오타루 운하", "小樽運河"),
    "紅芋タルト": ("베니이모", "홍고구마", "紅芋タルト"),
    "みかん": ("미캉", "귤", "みかん"),
}

TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "ぬいぐるみキーチェーン": ("마스코트", "봉제", "인형", "ぬいぐるみ", "マスコット"),
    "ダイカットキーホルダー": (
        "아크릴 키홀더",
        "아크릴 키링",
        "아크릴키홀더",
        "키홀더",
        "키링",
        "アクリルキーホルダー",
        "ダイカットキーホルダー",
    ),
    "推しキャラソックス": ("양말", "삭스", "ソックス"),
    "ソックス": ("양말", "삭스", "ソックス"),
    "ポーチ": ("파우치", "ポーチ"),
    "巾着": ("파우치", "긴착", "巾着"),
    "ティッシュケース": ("티슈 케이스", "ティッシュケース"),
    "かま口": ("파우치", "がま口", "かま口"),
    "記念メダル": ("메달", "記念メダル"),
}


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle and needle in text for needle in needles)


def _official_theme_type(alt: str) -> tuple[str | None, str | None]:
    theme, goods_type = _official_parts(alt)
    if theme and goods_type:
        return theme, goods_type
    theme = next((candidate for candidate in THEME_ALIASES if candidate in alt), None)
    goods_type = next((candidate for candidate in TYPE_ALIASES if candidate in alt), None)
    return theme, goods_type


def _row_theme_type(row: dict[str, Any], official_pairs: dict[tuple[str, str], list[dict[str, str]]]) -> tuple[str | None, str | None]:
    haystack = " ".join(
        str(row.get(key) or "")
        for key in ("name_ko", "name_ja", "category", "sub_series")
    )
    theme = next((candidate for candidate, _ in official_pairs if _contains_any(haystack, _aliases_for_theme(candidate))), None)
    if theme is None:
        theme = next((candidate for candidate, aliases in THEME_ALIASES.items() if _contains_any(haystack, aliases)), None)
    goods_type = next(
        (
            candidate
            for _, candidate in official_pairs
            if _contains_any(haystack, _aliases_for_type(candidate))
        ),
        None,
    )
    if goods_type is None:
        goods_type = next((candidate for candidate, aliases in TYPE_ALIASES.items() if _contains_any(haystack, aliases)), None)
    return theme, goods_type


def _is_gotouchi_target(row: dict[str, Any]) -> bool:
    source_store = str(row.get("source_store") or "")
    name_text = " ".join(str(row.get(key) or "") for key in ("name_ko", "name_ja"))
    return (
        source_store in CHIIKAWA_MARKET_NAMES
        and not row.get("image_url")
        and any(marker in name_text for marker in GOTOCHI_MARKERS)
    )


def build_audit(seed_rows: list[dict[str, Any]], source_url: str) -> dict[str, Any]:
    official_images = fetch_official_images(source_url)
    official_pairs: dict[tuple[str, str], list[dict[str, str]]] = {}
    for image in official_images:
        theme, goods_type = _official_theme_type(image.alt)
        if theme and goods_type:
            official_pairs.setdefault((theme, goods_type), []).append(
                {"alt": image.alt, "image_url": image.image_url}
            )

    targets: list[dict[str, Any]] = []
    for index, row in enumerate(seed_rows):
        if not isinstance(row, dict) or not _is_gotouchi_target(row):
            continue
        theme, goods_type = _row_theme_type(row, official_pairs)
        official_matches = official_pairs.get((theme or "", goods_type or ""), [])
        if official_matches:
            status = "official_pair_available"
        elif theme and any(pair_theme == theme for pair_theme, _ in official_pairs):
            status = "theme_available_type_missing"
        elif theme:
            status = "theme_not_in_current_official_api"
        else:
            status = "theme_unclassified"
        targets.append(
            {
                "catalog_index": row.get("catalog_index"),
                "row_index": index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "category": row.get("category"),
                "source_store": row.get("source_store"),
                "source_url": row.get("source_url"),
                "detected_theme": theme,
                "detected_type": goods_type,
                "status": status,
                "official_matches": official_matches[:3],
            }
        )

    status_counts = Counter(item["status"] for item in targets)
    theme_counts = Counter(item["detected_theme"] or "(unclassified)" for item in targets)
    return {
        "source_url": source_url,
        "official_image_count": len(official_images),
        "official_pair_count": len(official_pairs),
        "target_rows": len(targets),
        "status_counts": dict(status_counts),
        "theme_counts": dict(theme_counts.most_common()),
        "official_pairs": [
            {
                "theme": theme,
                "type": goods_type,
                "count": len(images),
                "sample_alt": images[0]["alt"],
                "sample_image_url": images[0]["image_url"],
            }
            for (theme, goods_type), images in sorted(official_pairs.items())
        ],
        "rows": targets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    args = parser.parse_args()

    payload = json.loads(args.seed.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{args.seed} must contain a JSON list or catalog object with items")
    audit = build_audit(rows, args.source_url)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "source_url": audit["source_url"],
                "official_image_count": audit["official_image_count"],
                "target_rows": audit["target_rows"],
                "status_counts": audit["status_counts"],
                "report": str(args.report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
