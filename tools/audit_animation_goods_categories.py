from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from catalog_quality_report import source_group

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_JSON = ROOT / "server" / "animation_goods_category_audit.json"
DEFAULT_MD = ROOT / "server" / "animation_goods_category_audit.md"

CATEGORY_FAMILIES = {
    "figure": {"피규어", "미니어처", "리플리카"},
    "plush": {"인형", "마스코트"},
    "badge": {"캔뱃지"},
    "acrylic": {"아크릴 스탠드"},
    "keyring": {"키링", "아크릴 키링"},
    "stationery": {"문구", "클리어파일", "카드", "트레이딩 카드", "스티커", "색지", "카드/브로마이드"},
    "daily_goods": {"머그컵", "타월", "가방", "생활잡화", "액세서리", "클리어 보틀", "파우치"},
    "display_goods": {"태피스트리", "보드"},
    "apparel": {"의류"},
    "fan_goods": {"응원용품", "응원봉", "콜라보 굿즈"},
}

FAMILY_VISUALS = {
    "figure": {"icon_key": "toys", "color_hint": "mint", "color_hex": "0xFF28D6C8"},
    "plush": {"icon_key": "face", "color_hint": "pink", "color_hex": "0xFFFF8FC3"},
    "badge": {"icon_key": "badge", "color_hint": "red", "color_hex": "0xFFD64562"},
    "acrylic": {"icon_key": "view_carousel", "color_hint": "blue", "color_hex": "0xFF5BA7F7"},
    "keyring": {"icon_key": "local_offer", "color_hint": "yellow", "color_hex": "0xFFFFD84D"},
    "stationery": {"icon_key": "sticky_note", "color_hint": "purple", "color_hex": "0xFFA78BFA"},
    "daily_goods": {"icon_key": "inventory", "color_hint": "green", "color_hex": "0xFF42A866"},
    "display_goods": {"icon_key": "photo", "color_hint": "indigo", "color_hex": "0xFF4F46E5"},
    "apparel": {"icon_key": "style", "color_hint": "neutral", "color_hex": "0xFF6B7280"},
    "fan_goods": {"icon_key": "celebration", "color_hint": "orange", "color_hex": "0xFFFF9F43"},
    "other": {"icon_key": "category", "color_hint": "neutral", "color_hex": "0xFF9CA3AF"},
}

CANONICAL_SUGGESTIONS = {
    "클리어파일": "문구",
    "카드": "문구",
    "미니어처": "피규어",
    "트레이딩 카드": "문구",
    "스티커": "문구",
    "클리어 보틀": "생활잡화",
    "파우치": "가방",
    "기타 굿즈": "액세서리",
}


def _missing(row: dict[str, Any], field: str) -> bool:
    return row.get(field) in (None, "")


def _counter_rows(counter: Counter[Any], keys: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    rows = []
    for values, count in counter.most_common(limit):
        if not isinstance(values, tuple):
            values = (values,)
        item = {key: value for key, value in zip(keys, values)}
        item["rows"] = count
        rows.append(item)
    return rows


def _category_family(category: str) -> str:
    for family, values in CATEGORY_FAMILIES.items():
        if category in values:
            return family
    return "other"


def build_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    animation_rows = [row for row in rows if source_group(row.get("source_store")) == "animation_goods"]
    by_category = Counter(str(row.get("category") or "") for row in animation_rows)
    by_family = Counter(_category_family(str(row.get("category") or "")) for row in animation_rows)
    by_store_category = Counter(
        (str(row.get("source_store") or ""), str(row.get("category") or "")) for row in animation_rows
    )
    by_category_missing_image = Counter(
        str(row.get("category") or "") for row in animation_rows if _missing(row, "image_url")
    )
    by_category_missing_source = Counter(
        str(row.get("category") or "") for row in animation_rows if _missing(row, "source_url")
    )
    by_sub_series = Counter(str(row.get("sub_series") or "") for row in animation_rows if row.get("sub_series"))

    suggestions: list[dict[str, Any]] = []
    for category, canonical in CANONICAL_SUGGESTIONS.items():
        affected = [row for row in animation_rows if row.get("category") == category]
        if not affected:
            continue
        suggestions.append(
            {
                "category": category,
                "suggested_category": canonical,
                "rows": len(affected),
                "risk": "medium",
                "reason": "Category is a subtype that may be better represented as sub_series while using the broader app category.",
                "sample_names": [row.get("name_ko") for row in affected[:8]],
            }
        )

    unknown_categories = [
        {"category": category, "rows": count}
        for category, count in by_category.most_common()
        if _category_family(category) == "other"
    ]

    store_profiles: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in animation_rows:
        grouped[str(row.get("source_store") or "")].append(row)
    for store, store_rows in grouped.items():
        store_profiles[store] = {
            "rows": len(store_rows),
            "categories": _counter_rows(Counter(str(row.get("category") or "") for row in store_rows), ("category",), 20),
            "missing": {
                "image_url": sum(1 for row in store_rows if _missing(row, "image_url")),
                "source_url": sum(1 for row in store_rows if _missing(row, "source_url")),
                "release_date": sum(1 for row in store_rows if _missing(row, "release_date")),
                "barcode": sum(1 for row in store_rows if _missing(row, "barcode")),
                "official_price_jpy": sum(1 for row in store_rows if _missing(row, "official_price_jpy")),
            },
        }

    category_visuals = []
    for category, count in by_category.most_common():
        family = _category_family(category)
        visual = FAMILY_VISUALS.get(family, FAMILY_VISUALS["other"])
        category_visuals.append(
            {
                "category": category,
                "family": family,
                "rows": count,
                "recommended_icon_key": visual["icon_key"],
                "recommended_color_hint": visual["color_hint"],
                "recommended_color_hex": visual["color_hex"],
            }
        )

    return {
        "rows": len(animation_rows),
        "category_count": len(by_category),
        "categories": _counter_rows(by_category, ("category",), 100),
        "category_families": _counter_rows(by_family, ("family",), 40),
        "category_visuals": category_visuals,
        "top_store_categories": _counter_rows(by_store_category, ("source_store", "category"), 120),
        "missing_image_by_category": _counter_rows(by_category_missing_image, ("category",), 60),
        "missing_source_url_by_category": _counter_rows(by_category_missing_source, ("category",), 60),
        "top_sub_series": _counter_rows(by_sub_series, ("sub_series",), 80),
        "normalization_suggestions": suggestions,
        "unknown_categories": unknown_categories,
        "store_profiles": store_profiles,
    }


def write_markdown(audit: dict[str, Any], path: Path) -> None:
    lines = [
        "# Animation Goods Category Audit",
        "",
        f"- Rows: `{audit['rows']}`",
        f"- Category count: `{audit['category_count']}`",
        "",
        "## Category Families",
        "",
    ]
    for item in audit["category_families"]:
        lines.append(f"- `{item['family']}`: `{item['rows']}`")
    lines.extend(["", "## Categories", ""])
    for item in audit["categories"][:40]:
        lines.append(f"- `{item['category']}`: `{item['rows']}`")
    lines.extend(["", "## Category UI Hints", ""])
    for item in audit["category_visuals"][:60]:
        lines.append(
            f"- `{item['category']}`: family `{item['family']}`, "
            f"icon `{item['recommended_icon_key']}`, "
            f"color `{item['recommended_color_hint']}` `{item['recommended_color_hex']}`"
        )
    lines.extend(["", "## Normalization Suggestions", ""])
    if not audit["normalization_suggestions"]:
        lines.append("- No automatic normalization suggestions.")
    for item in audit["normalization_suggestions"]:
        lines.append(
            f"- `{item['category']}` -> `{item['suggested_category']}`: "
            f"`{item['rows']}` rows, risk `{item['risk']}`"
        )
    lines.extend(["", "## Unknown Categories", ""])
    if not audit["unknown_categories"]:
        lines.append("- None.")
    for item in audit["unknown_categories"][:40]:
        lines.append(f"- `{item['category']}`: `{item['rows']}`")
    lines.extend(["", "## Missing Images By Category", ""])
    for item in audit["missing_image_by_category"][:30]:
        lines.append(f"- `{item['category']}`: `{item['rows']}`")
    lines.extend(["", "## Top Store Categories", ""])
    for item in audit["top_store_categories"][:40]:
        lines.append(f"- `{item['source_store']}` / `{item['category']}`: `{item['rows']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or an object with items")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    audit = build_audit(_load_rows(args.input))
    args.json_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(audit, args.markdown_output)
    print(
        json.dumps(
            {
                "rows": audit["rows"],
                "category_count": audit["category_count"],
                "suggestions": len(audit["normalization_suggestions"]),
                "unknown_categories": len(audit["unknown_categories"]),
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
