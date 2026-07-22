from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_public.json"
DEFAULT_OUTPUT = DATA / "ichiban_kuji_prize_policy_audit_public.json"
REVIEW_BATCH_SIZE = 12

LAST_ONE_TOKENS = ("ラストワン賞", "ラストワン", "last one", "last-one", "lastone")
DOUBLE_CHANCE_TOKENS = (
    "ダブルチャンス賞",
    "ダブルチャンス",
    "double chance",
    "double-chance",
    "doublechance",
)
REISSUE_TOKENS = ("再販売", "再販", "reissue", "rerun")
NUMBERED_VARIANT_PATTERN = re.compile(r"[（(](\d+)\s*/\s*(\d+)[）)]")


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


def batch_groups(
    groups: list[dict[str, Any]],
    *,
    workflow: str,
    batch_id_prefix: str,
    recommended_action: str,
    review_reason: str,
    batch_size: int = REVIEW_BATCH_SIZE,
) -> list[dict[str, Any]]:
    batches = []
    for offset in range(0, len(groups), batch_size):
        batch_groups = groups[offset : offset + batch_size]
        batches.append(
            {
                "batch_id": f"{batch_id_prefix}-{(offset // batch_size) + 1:03d}",
                "workflow": workflow,
                "priority": 30 + (offset // batch_size),
                "group_count": len(batch_groups),
                "catalog_item_rows": sum(int(group.get("row_count") or 0) for group in batch_groups),
                "review_state": "manual_official_campaign_prize_confirmation_required",
                "recommended_action": recommended_action,
                "review_reason": review_reason,
                "groups": batch_groups,
            }
        )
    return batches


def numbered_variant_marks(row: dict[str, Any]) -> list[tuple[int, int]]:
    text = " ".join(str(row.get(field) or "") for field in ("name_ko", "name_ja", "name_en"))
    return [(int(match.group(1)), int(match.group(2))) for match in NUMBERED_VARIANT_PATTERN.finditer(text)]


def has_reissue_signal(row: dict[str, Any]) -> bool:
    blob = " ".join(
        str(row.get(field) or "") for field in ("name_ko", "name_ja", "name_en", "series_name", "sub_series", "source_url")
    ).lower()
    source_url = str(row.get("source_url") or "").lower().rstrip("/")
    return any(token.lower() in blob for token in REISSUE_TOKENS) or bool(re.search(r"-\d+$", source_url))


def normalized_reissue_review_name(row: dict[str, Any]) -> str:
    name = str(row.get("name_ko") or "").lower()
    for token in REISSUE_TOKENS:
        name = name.replace(token.lower(), "")
    name = name.replace("（ ）", " ").replace("（）", " ").replace("()", " ")
    return " ".join(name.split())


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

    numbered_variant_groups = []
    incomplete_numbered_variant_groups = []
    for (source_url, sub_series), rows in by_campaign_prize.items():
        marks: list[tuple[int, int]] = []
        for row in rows:
            marks.extend(numbered_variant_marks(row))
        if not marks:
            continue
        expected_count = max(denominator for _, denominator in marks)
        seen_numbers = sorted({number for number, _ in marks})
        missing_numbers = [number for number in range(1, expected_count + 1) if number not in seen_numbers]
        group = {
            "source_url": source_url,
            "sub_series": sub_series,
            "expected_variant_count": expected_count,
            "actual_row_count": len(rows),
            "numbered_variant_rows": len(marks),
            "seen_variant_numbers": seen_numbers[:120],
            "missing_variant_numbers": missing_numbers[:120],
            "coverage_complete": not missing_numbers and len(rows) >= expected_count,
            "sample_rows": [compact_row(row) for row in rows[:8]],
        }
        numbered_variant_groups.append(group)
        if not group["coverage_complete"]:
            incomplete_numbered_variant_groups.append(group)
    numbered_variant_groups.sort(
        key=lambda row: (-int(row["expected_variant_count"]), row["source_url"], row["sub_series"])
    )
    incomplete_numbered_variant_groups.sort(
        key=lambda row: (-len(row["missing_variant_numbers"]), -int(row["expected_variant_count"]), row["source_url"])
    )

    normalized_name_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in kuji_rows:
        key = normalized_reissue_review_name(row)
        if key:
            normalized_name_groups[key].append(row)
    repeated_name_different_source_groups = []
    probable_reissue_review_groups = []
    for rows in normalized_name_groups.values():
        source_urls = {str(row.get("source_url") or "") for row in rows}
        if len(rows) > 1 and len(source_urls) > 1:
            has_reissue = any(has_reissue_signal(row) for row in rows)
            group = {
                "normalized_name": str(rows[0].get("name_ko") or ""),
                "row_count": len(rows),
                "source_url_count": len(source_urls),
                "has_reissue_signal": has_reissue,
                "source_urls": sorted(source_urls)[:12],
                "sample_rows": [compact_row(row) for row in rows[:8]],
                "review_reason": "same displayed item name appears under multiple 1kuji campaign URLs; confirm re-release or exact duplicate before dedupe",
            }
            repeated_name_different_source_groups.append(group)
            if has_reissue:
                probable_reissue_review_groups.append(group)
    repeated_name_different_source_groups.sort(
        key=lambda row: (-int(row["source_url_count"]), -int(row["row_count"]), row["normalized_name"])
    )
    probable_reissue_review_groups.sort(
        key=lambda row: (-int(row["source_url_count"]), -int(row["row_count"]), row["normalized_name"])
    )

    prize_label_counts = Counter(str(row.get("sub_series") or "") for row in kuji_rows if row.get("sub_series"))
    multi_item_review_batches = batch_groups(
        multi_item_prize_groups,
        workflow="multi_item_prize_label_review",
        batch_id_prefix="ichiban-prize-policy-multi-item",
        recommended_action=(
            "Open the official campaign page and confirm every item listed under the same prize label before "
            "adding missing variants or merging duplicate-looking rows."
        ),
        review_reason=(
            "The same prize label has multiple catalog rows. This is often correct for Ichiban Kuji variants, "
            "but it must be checked against the official campaign lineup."
        ),
    )
    repeated_name_review_batches = batch_groups(
        repeated_name_different_source_groups,
        workflow="repeated_name_different_source_review",
        batch_id_prefix="ichiban-prize-policy-repeated-name",
        recommended_action=(
            "Compare official campaign URLs and release context, then mark each group as reissue, distinct "
            "variant, or exact duplicate before any dedupe mutation."
        ),
        review_reason=(
            "The same normalized item name appears under multiple campaign URLs. Re-releases must stay separate "
            "when they are official distinct runs."
        ),
    )
    price_exception_rows = len(last_one_nonzero) + len(last_one_missing) + len(double_chance_nonzero) + len(
        double_chance_missing
    )
    review_batches = (multi_item_review_batches + repeated_name_review_batches)[:40]

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
            "numbered_variant_prize_label_groups": len(numbered_variant_groups),
            "incomplete_numbered_variant_prize_label_groups": len(incomplete_numbered_variant_groups),
            "numbered_variant_coverage_policy_pass": not incomplete_numbered_variant_groups,
            "repeated_name_different_source_groups": len(repeated_name_different_source_groups),
            "probable_reissue_review_groups": len(probable_reissue_review_groups),
            "zero_price_violation_rows": price_exception_rows,
            "multi_item_prize_label_review_batch_count": len(multi_item_review_batches),
            "multi_item_prize_label_review_catalog_item_rows": sum(
                int(group.get("row_count") or 0) for group in multi_item_prize_groups
            ),
            "repeated_name_different_source_review_batch_count": len(repeated_name_review_batches),
            "repeated_name_different_source_review_catalog_item_rows": sum(
                int(group.get("row_count") or 0) for group in repeated_name_different_source_groups
            ),
            "prize_policy_review_batch_count": len(multi_item_review_batches) + len(repeated_name_review_batches),
            "auto_apply_enabled": False,
        },
        "policy": {
            "last_one_and_double_chance_price_jpy": 0,
            "auto_apply_enabled": False,
            "requires_manual_review_for_dedupe": True,
            "notes": [
                "Last-one and double-chance rows are non-purchase prize exceptions and must stay price 0.",
                "Multiple rows inside the same prize label can be correct when the official campaign has variants.",
                "Numbered variant labels such as (1/24) are audited for missing numbers before treating the prize group as complete.",
                "Repeated names across campaign URLs are review candidates, not automatic duplicates.",
            ],
        },
        "last_one_price_violations": [compact_row(row) for row in last_one_nonzero + last_one_missing],
        "double_chance_price_violations": [compact_row(row) for row in double_chance_nonzero + double_chance_missing],
        "multi_item_prize_label_groups": multi_item_prize_groups[:80],
        "numbered_variant_prize_label_groups": numbered_variant_groups[:80],
        "incomplete_numbered_variant_prize_label_groups": incomplete_numbered_variant_groups[:80],
        "repeated_name_different_source_groups": repeated_name_different_source_groups[:80],
        "probable_reissue_review_groups": probable_reissue_review_groups[:80],
        "review_batches": review_batches,
        "next_actions": [
            {
                "priority": 1,
                "workstream": "last_one_double_chance_zero_price_policy",
                "status": "pass" if price_exception_rows == 0 else "manual_fix_required",
                "rows": price_exception_rows,
                "recommended_next_action": "Keep Last One and Double Chance prize exceptions at official_price_jpy=0.",
            },
            {
                "priority": 2,
                "workstream": "multi_item_prize_label_review",
                "rows": len(multi_item_prize_groups),
                "batch_count": len(multi_item_review_batches),
                "next_batch_id": multi_item_review_batches[0]["batch_id"] if multi_item_review_batches else None,
                "recommended_next_action": "Review same-prize-label groups against official lineup pages before adding missing variants.",
            },
            {
                "priority": 3,
                "workstream": "repeated_name_different_source_review",
                "rows": len(repeated_name_different_source_groups),
                "batch_count": len(repeated_name_review_batches),
                "next_batch_id": repeated_name_review_batches[0]["batch_id"] if repeated_name_review_batches else None,
                "recommended_next_action": "Separate official reissues from exact duplicate rows before dedupe.",
            },
        ],
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
