from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "data" / "catalog_character_name_policy_public.json"

ICHIBAN_PREFIX = "一番くじ"
LAST_ONE_LABEL = "ラストワン賞"
DOUBLE_CHANCE_LABELS = ("ダブルチャンス", "Wチャンス")

CHARACTER_MOJIBAKE_OR_ALIAS_FINDINGS = {
    "펀": {
        "expected": "페른",
        "fields": ("character_name", "affiliation"),
        "reason": "likely_korean_frieren_character_typo",
    },
}


def load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        rows = payload.get("items")
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain an item list or an items array")
    return [row for row in rows if isinstance(row, dict)]


def is_ichiban_row(row: dict[str, Any]) -> bool:
    return str(row.get("series_name") or "").startswith(ICHIBAN_PREFIX) or ICHIBAN_PREFIX in str(
        row.get("name_ko") or ""
    )


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    character_alias_violations: list[dict[str, Any]] = []
    ichiban_display_name_violations: list[dict[str, Any]] = []
    zero_price_violations: list[dict[str, Any]] = []

    for row in rows:
        catalog_index = row.get("catalog_index")
        for bad_value, rule in CHARACTER_MOJIBAKE_OR_ALIAS_FINDINGS.items():
            for field in rule["fields"]:
                value = row.get(field)
                if value == bad_value:
                    character_alias_violations.append(
                        {
                            "catalog_index": catalog_index,
                            "field": field,
                            "value": value,
                            "expected": rule["expected"],
                            "reason": rule["reason"],
                            "name_ko": row.get("name_ko"),
                        }
                    )

        if not is_ichiban_row(row):
            continue

        name_ko = str(row.get("name_ko") or "")
        parts = [part.strip() for part in name_ko.split(" / ")]
        if len(parts) != 4 or not parts[0].startswith(ICHIBAN_PREFIX) or not parts[1].endswith("賞"):
            ichiban_display_name_violations.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "series_name": row.get("series_name"),
                    "sub_series": row.get("sub_series"),
                    "character_name": row.get("character_name"),
                    "reason": "expected_kuji_campaign_prize_product_character_display_name",
                }
            )

        sub_series = str(row.get("sub_series") or "")
        if (
            LAST_ONE_LABEL in sub_series
            or any(label in sub_series for label in DOUBLE_CHANCE_LABELS)
            or "라스트원" in name_ko
            or "더블찬스" in name_ko
        ) and row.get("official_price_jpy") not in (0, None):
            zero_price_violations.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "sub_series": row.get("sub_series"),
                    "official_price_jpy": row.get("official_price_jpy"),
                    "reason": "last_one_and_double_chance_rows_must_have_zero_price",
                }
            )

    findings = (
        len(character_alias_violations)
        + len(ichiban_display_name_violations)
        + len(zero_price_violations)
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "catalog_character_name_policy",
        "summary": {
            "rows": len(rows),
            "ichiban_rows": sum(1 for row in rows if is_ichiban_row(row)),
            "character_alias_violations": len(character_alias_violations),
            "ichiban_display_name_violations": len(ichiban_display_name_violations),
            "zero_price_violations": len(zero_price_violations),
            "findings": findings,
            "status": "pass" if findings == 0 else "needs_review",
        },
        "policy": {
            "character_name_aliases": CHARACTER_MOJIBAKE_OR_ALIAS_FINDINGS,
            "ichiban_display_name_format": "一番くじ 발매명 / ?賞 / 상품이름 / 캐릭터명",
            "last_one_and_double_chance_price_jpy": 0,
        },
        "character_alias_violations": character_alias_violations,
        "ichiban_display_name_violations": ichiban_display_name_violations,
        "zero_price_violations": zero_price_violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero when the catalog still has character/name policy findings.",
    )
    args = parser.parse_args()

    report = audit(load_catalog(args.catalog))
    if args.write:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.fail_on_findings and report["summary"]["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
