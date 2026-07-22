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
DEFAULT_OUTPUT = DATA / "ichiban_kuji_prize_policy_audit_public.json"

LAST_ONE_TOKENS = ("ラストワン賞", "ラストワン", "last one", "last-one", "lastone")
DOUBLE_CHANCE_TOKENS = (
    "ダブルチャンス賞",
    "ダブルチャンス",
    "double chance",
    "double-chance",
    "doublechance",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def text_blob(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "name_en", "category", "series_name", "sub_series", "source_url")
    ).lower()


def is_ichiban_row(row: dict[str, Any]) -> bool:
    source_url = str(row.get("source_url") or "")
    name = str(row.get("name_ko") or "")
    series = str(row.get("series_name") or "")
    return "1kuji.com" in source_url or "一番くじ" in name or "一番くじ" in series


def has_token(row: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    blob = text_blob(row)
    return any(token.lower() in blob for token in tokens)


def price_is_zero(row: dict[str, Any]) -> bool:
    value = row.get("official_price_jpy")
    return value == 0 or value == "0"


def price_missing(row: dict[str, Any]) -> bool:
    return row.get("official_price_jpy") in (None, "")


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "series_name": row.get("series_name"),
        "sub_series": row.get("sub_series"),
        "official_price_jpy": row.get("official_price_jpy"),
        "source_url": row.get("source_url"),
    }


def build_report(catalog: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items = [row for row in catalog.get("items", []) if isinstance(row, dict)]
    kuji_rows = [row for row in items if is_ichiban_row(row)]
    last_one_rows = [row for row in kuji_rows if has_token(row, LAST_ONE_TOKENS)]
    double_chance_rows = [row for row in kuji_rows if has_token(row, DOUBLE_CHANCE_TOKENS)]

    last_one_nonzero = [row for row in last_one_rows if not price_missing(row) and not price_is_zero(row)]
    last_one_missing = [row for row in last_one_rows if price_missing(row)]
    double_chance_nonzero = [row for row in double_chance_rows if not price_missing(row) and not price_is_zero(row)]
    double_chance_missing = [row for row in double_chance_rows if price_missing(row)]

    by_campaign_prize: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in kuji_rows:
        source_url = str(row.get("source_url") or "")
        sub_series = str(row.get("sub_series") or "")
        if source_url and sub_series:
            by_campaign_prize[(source_url, sub_series)].append(row)

    multi_item_prize_groups = [
        {
            "source_url": source_url,
            "sub_series": sub_series,
            "row_count": len(rows),
            "sample_rows": [compact_row(row) for row in rows[:8]],
        }
        for (source_url, sub_series), rows in by_campaign_prize.items()
        if len(rows) > 1
    ]
    multi_item_prize_groups.sort(key=lambda row: (-int(row["row_count"]), row["source_url"], row["sub_series"]))

    normalized_name_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in kuji_rows:
        key = " ".join(str(row.get("name_ko") or "").lower().split())
        if key:
            normalized_name_groups[key].append(row)
    repeated_name_different_source_groups = []
    for rows in normalized_name_groups.values():
        source_urls = {str(row.get("source_url") or "") for row in rows}
        if len(rows) > 1 and len(source_urls) > 1:
            repeated_name_different_source_groups.append(
                {
                    "normalized_name": str(rows[0].get("name_ko") or ""),
                    "row_count": len(rows),
                    "source_url_count": len(source_urls),
                    "sample_rows": [compact_row(row) for row in rows[:8]],
                    "review_reason": "same displayed item name appears under multiple 1kuji campaign URLs; confirm re-release or exact duplicate before dedupe",
                }
            )
    repeated_name_different_source_groups.sort(
        key=lambda row: (-int(row["source_url_count"]), -int(row["row_count"]), row["normalized_name"])
    )

    prize_label_counts = Counter(str(row.get("sub_series") or "") for row in kuji_rows if row.get("sub_series"))

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "ichiban_kuji_prize_policy_audit",
        "summary": {
            "kuji_rows": len(kuji_rows),
            "last_one_rows": len(last_one_rows),
            "last_one_nonzero_price_rows": len(last_one_nonzero),
            "last_one_missing_price_rows": len(last_one_missing),
            "double_chance_rows": len(double_chance_rows),
            "double_chance_nonzero_price_rows": len(double_chance_nonzero),
            "double_chance_missing_price_rows": len(double_chance_missing),
            "zero_price_exception_policy_pass": not (
                last_one_nonzero or last_one_missing or double_chance_nonzero or double_chance_missing
            ),
            "campaign_prize_label_groups": len(by_campaign_prize),
            "multi_item_prize_label_groups": len(multi_item_prize_groups),
            "repeated_name_different_source_groups": len(repeated_name_different_source_groups),
            "auto_apply_enabled": False,
        },
        "policy": {
            "last_one_and_double_chance_price_jpy": 0,
            "auto_apply_enabled": False,
            "requires_manual_review_for_dedupe": True,
            "notes": [
                "Last-one and double-chance rows are non-purchase prize exceptions and must stay price 0.",
                "Multiple rows inside the same prize label can be correct when the official campaign has variants.",
                "Repeated names across campaign URLs are review candidates, not automatic duplicates.",
            ],
        },
        "last_one_price_violations": [compact_row(row) for row in last_one_nonzero + last_one_missing],
        "double_chance_price_violations": [compact_row(row) for row in double_chance_nonzero + double_chance_missing],
        "multi_item_prize_label_groups": multi_item_prize_groups[:80],
        "repeated_name_different_source_groups": repeated_name_different_source_groups[:80],
        "top_prize_labels": [[label, count] for label, count in prize_label_counts.most_common(80)],
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
