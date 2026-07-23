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
DEFAULT_REPORT = ROOT / "server" / "public_catalog_category_correction_report.json"

CORRECTION_RULES = [
    {
        "rule_id": "acrylic_stand_to_acrylic_keyring",
        "source_category": "아크릴 스탠드",
        "target_category": "아크릴 키링",
        "keywords": (
            "アクリルキーホルダー",
            "アクリルキーホルダー",
            "アクリルキー ホルダー",
            "アクリルキー ホルダー",
            "아크릴 키홀더",
            "아크릴 키 홀더",
        ),
    },
    {
        "rule_id": "acrylic_stand_to_mascot",
        "source_category": "아크릴 스탠드",
        "target_category": "마스코트",
        "keywords": (
            "アクリルマスコット",
            "아크릴 마스코트",
        ),
    },
]


def _text(row: dict[str, Any]) -> str:
    raw = " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "name_en", "series_name", "sub_series")
        if str(row.get(field) or "").strip()
    )
    return unicodedata.normalize("NFC", raw)


def apply_corrections(rows: list[dict[str, Any]]) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    by_rule: dict[str, int] = {str(rule["rule_id"]): 0 for rule in CORRECTION_RULES}

    for row in rows:
        text = _text(row)
        for rule in CORRECTION_RULES:
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
    args = parser.parse_args()

    payload, rows = load_catalog(args.catalog)
    result = apply_corrections(rows)
    report = {
        "write": args.write,
        "catalog": str(args.catalog),
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
