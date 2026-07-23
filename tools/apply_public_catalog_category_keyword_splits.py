from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "server" / "public_catalog_category_keyword_split_report.json"

ANIMATION_AFFILIATION_TOKENS = (
    "\ub2e8\uac04\ub860\ud30c",
    "\uc8fc\uc220\ud68c\uc804",
    "\ud5cc\ud130\ud5cc\ud130",
    "\ud504\ub9ac\ub80c",
    "\ucd5c\uc560\uc758\uc544\uc774",
    "\ub098\uc758 \ud788\uc5b4\ub85c",
)
ANIMATION_STORES = {
    "AmiAmi",
    "Cospa",
    "FuRyu",
    "Movic",
    "Re-ment",
    "Taito",
    "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
    "\uadc0\uba78\uc758 \uce7c\ub0a0 \uacf5\uc2dd",
    "\uba54\uac00\ud558\uc6b0\uc2a4",
    "\ubb34\uae30\uc640\ub77c\uc2a4\ud1a0\uc5b4",
    "\ubc18\ub2e4\uc774",
    "\uc560\ub2c8\uba54\uc774\ud2b8",
    "\uc5d4\uc2a4\uce74\uc774",
    "\uc810\ud504 \uce90\ub9ad\ud130\uc988 \uc2a4\ud1a0\uc5b4",
    "\uc810\ud504 \uc20d",
    "\uce74\ub3c4\uce74\uc640",
    "\ucf54\ud1a0\ubd80\ud0a4\uc57c",
}

CATEGORY_SPLIT_RULES = [
    {
        "rule_id": "goods_figure_sofvic_chokonokko",
        "source_category": "\uad7f\uc988",
        "target_category": "\ud53c\uaddc\uc5b4",
        "keywords": (
            "SOFVIC",
            "SOFVICS",
            "\u3061\u3087\u3053\u306e\u3063\u3053",
            "\u3061\u3073\u304d\u3085\u3093\u30ad\u30e3\u30e9",
            "\u304d\u3085\u3093\u30ad\u30e3\u30e9\u3073\u306d\u3063\u3068",
            "Revible Moment",
            "MASTERELIVE COLLECTION",
        ),
    },
    {
        "rule_id": "goods_badge_badge_set",
        "source_category": "\uad7f\uc988",
        "target_category": "\uce94\ubc43\uc9c0",
        "keywords": (
            "\u30d0\u30c3\u30b8",
            "\u30cf\u3099\u30c3\u30b7\u3099",
        ),
    },
    {
        "rule_id": "goods_keyring_strap_charm",
        "source_category": "\uad7f\uc988",
        "target_category": "\ud0a4\ub9c1",
        "keywords": (
            "\u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
            "\u30b9\u30c8\u30e9\u30c3\u30d7",
            "\u30b9\u30c8\u30e9\u30c3\u30d5\u309a",
            "\u3061\u3083\u30fc\u3080",
            "\u30c1\u30e3\u30fc\u30e0",
            "\u306d\u3064\u3051",
        ),
    },
    {
        "rule_id": "goods_acrylic_acrylitz",
        "source_category": "\uad7f\uc988",
        "target_category": "\uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
        "keywords": (
            "\u30a2\u30af\u30ea\u30c3\u30c4",
        ),
    },
    {
        "rule_id": "goods_stationery_sheets_notes",
        "source_category": "\uad7f\uc988",
        "target_category": "\ubb38\uad6c",
        "keywords": (
            "\u30ce\u30fc\u30c8",
            "\u30b7\u30fc\u30c8",
            "\u30af\u30ea\u30c3\u30d7",
            "\u30a2\u30eb\u30d0\u30e0",
        ),
    },
    {
        "rule_id": "goods_display_cross_art",
        "source_category": "\uad7f\uc988",
        "target_category": "\ud0dc\ud53c\uc2a4\ud2b8\ub9ac",
        "keywords": (
            "BIG\u30af\u30ed\u30b9",
            "\u30d3\u30b8\u30e5\u30a2\u30eb\u30af\u30ed\u30b9",
            "\u540d\u30b7\u30fc\u30f3\u30a2\u30fc\u30c8",
            "\u30b9\u30da\u30b7\u30e3\u30eb\u30b7\u30fc\u30f3\u30bb\u30ec\u30af\u30b7\u30e7\u30f3",
        ),
    },
    {
        "rule_id": "goods_fan_support_set",
        "source_category": "\uad7f\uc988",
        "target_category": "\uc751\uc6d0\uc6a9\ud488",
        "keywords": (
            "\u5fdc\u63f4\u30bb\u30c3\u30c8",
        ),
    },
    {
        "rule_id": "goods_daily_goods",
        "source_category": "\uad7f\uc988",
        "target_category": "\uc0dd\ud65c\uc7a1\ud654",
        "keywords": (
            "\u30af\u30c3\u30b7\u30e7\u30f3",
            "\u30bf\u30f3\u30d6\u30e9\u30fc",
            "\u30dc\u30c8\u30eb",
            "\u30b3\u30fc\u30b9\u30bf\u30fc",
            "\u30b5\u30b3\u30c3\u30b7\u30e5",
            "\u30ed\u30fc\u30eb\u30b1\u30fc\u30b9",
            "\u30de\u30eb\u30c1\u30c8\u30ec\u30a4",
            "\u30c1\u30c3\u30d7\u30b1\u30fc\u30b9",
            "\u30b1\u30fc\u30d6\u30eb\u30db\u30eb\u30c0\u30fc",
        ),
    },
    {
        "rule_id": "goods_accessory_clear_item_assort",
        "source_category": "\uad7f\uc988",
        "target_category": "\uc561\uc138\uc11c\ub9ac",
        "keywords": (
            "\u30af\u30ea\u30a2\u30a2\u30a4\u30c6\u30e0\u30a2\u30bd\u30fc\u30c8",
        ),
    },
]


def is_animation_goods(row: dict[str, Any]) -> bool:
    source_store = str(row.get("source_store") or "")
    if source_store in ANIMATION_STORES:
        return True
    target = " ".join(str(row.get(field) or "") for field in ("affiliation", "series_name"))
    return any(token in target for token in ANIMATION_AFFILIATION_TOKENS)


def item_text(row: dict[str, Any]) -> str:
    text = " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "name_en", "series_name", "sub_series")
        if str(row.get(field) or "").strip()
    )
    return unicodedata.normalize("NFC", text)


def apply_splits(rows: list[dict[str, Any]], *, animation_only: bool = True) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    by_rule: dict[str, int] = {str(rule["rule_id"]): 0 for rule in CATEGORY_SPLIT_RULES}

    for row in rows:
        if animation_only and not is_animation_goods(row):
            continue
        text = item_text(row)
        for rule in CATEGORY_SPLIT_RULES:
            source_category = str(rule["source_category"])
            target_category = str(rule["target_category"])
            if row.get("category") != source_category:
                continue
            keywords = tuple(unicodedata.normalize("NFC", str(keyword)) for keyword in rule["keywords"])
            matched_keyword = next((keyword for keyword in keywords if keyword in text), None)
            if matched_keyword is None:
                continue
            row["category"] = target_category
            by_rule[str(rule["rule_id"])] += 1
            updated.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_category": source_category,
                    "target_category": target_category,
                    "rule_id": rule["rule_id"],
                    "matched_keyword": matched_keyword,
                }
            )
            break

    return {
        "updated_rows": len(updated),
        "by_rule": [[rule_id, count] for rule_id, count in by_rule.items() if count],
        "updated": updated,
    }


def load_catalog(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise SystemExit(f"{path} must contain a public catalog object with items")
    rows = [row for row in payload["items"] if isinstance(row, dict)]
    return payload, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--include-non-animation", action="store_true")
    args = parser.parse_args()

    payload, rows = load_catalog(args.catalog)
    result = apply_splits(rows, animation_only=not args.include_non_animation)
    report = {
        "write": args.write,
        "catalog": str(args.catalog),
        "animation_only": not args.include_non_animation,
        **result,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write and result["updated_rows"]:
        payload["items"] = rows
        args.catalog.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "write": args.write,
                "updated_rows": result["updated_rows"],
                "by_rule": result["by_rule"],
                "report": str(args.report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
