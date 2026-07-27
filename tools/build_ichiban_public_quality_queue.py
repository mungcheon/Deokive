from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

try:
    from catalog_quality_report import build_report, load_catalog_rows
except ImportError:
    from tools.catalog_quality_report import build_report, load_catalog_rows


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_JSON = ROOT / "server" / "ichiban_public_quality_queue.json"
DEFAULT_CSV = ROOT / "server" / "ichiban_public_quality_queue.csv"


def build_queue(quality_report: dict[str, Any]) -> dict[str, Any]:
    ichiban = quality_report.get("ichiban_kuji") or {}
    campaign_gap_urls = ichiban.get("campaign_gap_urls")
    if not isinstance(campaign_gap_urls, list):
        campaign_gap_urls = ichiban.get("campaign_gap_sample", [])
    gap_items = [
        {
            "workflow": "campaign_gap_research",
            "priority": 10,
            "status": "needs_official_or_archive_evidence",
            "source_url": url,
            "recommended_action": (
                "Find replacement official/archive evidence before creating or importing prize rows."
            ),
        }
        for url in campaign_gap_urls
        if isinstance(url, str) and url.strip()
    ]

    duplicate_items: list[dict[str, Any]] = []
    duplicate_review_groups = ichiban.get("exact_display_duplicate_review")
    if not isinstance(duplicate_review_groups, list):
        duplicate_review_groups = ichiban.get("exact_display_duplicate_review_sample", [])
    for group in duplicate_review_groups:
        if not isinstance(group, dict):
            continue
        duplicate_items.append(
            {
                "workflow": "exact_display_duplicate_reissue_review",
                "priority": 20,
                "status": "needs_reissue_or_duplicate_decision",
                "display_name": group.get("display_name"),
                "row_count": group.get("rows"),
                "source_urls": group.get("source_urls") or [],
                "catalog_indexes": group.get("catalog_indexes") or [],
                "recommended_action": (
                    "Confirm whether rows are separate reissues/campaigns or true duplicates before merging."
                ),
            }
        )

    zero_price_items = [
        {
            "workflow": "zero_price_policy_review",
            "priority": 5,
            "status": "unexpected_zero_price",
            "catalog_index": row.get("catalog_index"),
            "display_name": row.get("name_ko"),
            "source_url": row.get("source_url"),
            "recommended_action": (
                "Set normal prize price or confirm this is a last-one/double-chance exception."
            ),
        }
        for row in ichiban.get("zero_price_non_exception_sample", [])
        if isinstance(row, dict)
    ]

    naming_items: list[dict[str, Any]] = []
    for row in ichiban.get("naming_convention_review_sample", []):
        if not isinstance(row, dict):
            continue
        reason = row.get("reason")
        if reason == "non_prize_or_related_item_needs_classification":
            workflow = "non_prize_related_item_classification"
            recommended_action = (
                "Classify as related/campaign/non-prize goods or find exact prize-rank evidence."
            )
            priority = 30
        else:
            workflow = "display_name_convention_review"
            recommended_action = (
                "Rewrite display_name as release name / prize rank / prize name / character name."
            )
            priority = 25
        naming_items.append(
            {
                "workflow": workflow,
                "priority": priority,
                "status": "needs_display_or_classification_review",
                "catalog_index": row.get("catalog_index"),
                "display_name": row.get("name_ko"),
                "source_url": row.get("source_url"),
                "reason": reason,
                "display_parts": row.get("display_parts") or [],
                "recommended_action": recommended_action,
            }
        )

    items = zero_price_items + gap_items + duplicate_items + naming_items
    items.sort(
        key=lambda item: (
            int(item.get("priority") or 99),
            str(item.get("source_url") or ""),
            str(item.get("display_name") or ""),
        )
    )
    return {
        "source": "data/catalog_public.json",
        "quality_report_source": "server/catalog_quality_report.json",
        "summary": {
            "ichiban_rows": ichiban.get("rows", 0),
            "campaign_count": ichiban.get("campaign_count", 0),
            "seeded_campaign_url_count": ichiban.get("seeded_campaign_url_count", 0),
            "campaign_gap_count": ichiban.get("campaign_gap_count", 0),
            "campaign_gap_queue_rows": len(gap_items),
            "exact_display_duplicate_review_groups": ichiban.get(
                "exact_display_duplicate_review_groups", 0
            ),
            "exact_display_duplicate_review_rows": ichiban.get(
                "exact_display_duplicate_review_rows", 0
            ),
            "exact_display_duplicate_queue_rows": len(duplicate_items),
            "zero_price_exception_rows": ichiban.get("zero_price_exception_rows", 0),
            "zero_price_non_exception_rows": ichiban.get("zero_price_non_exception_rows", 0),
            "zero_price_policy_queue_rows": len(zero_price_items),
            "naming_convention_review_rows": ichiban.get("naming_convention_review_rows", 0),
            "naming_convention_queue_rows": len(naming_items),
            "queue_rows": len(items),
        },
        "items": items,
    }


def write_csv(queue: dict[str, Any], path: Path) -> None:
    fields = [
        "workflow",
        "priority",
        "status",
        "catalog_index",
        "source_url",
        "display_name",
        "row_count",
        "reason",
        "display_parts",
        "catalog_indexes",
        "source_urls",
        "recommended_action",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in queue.get("items", []):
            row = {field: item.get(field, "") for field in fields}
            for field in ("catalog_indexes", "source_urls", "display_parts"):
                if isinstance(row[field], list):
                    row[field] = " | ".join(str(value) for value in row[field])
            writer.writerow(row)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a public-catalog Ichiban Kuji quality work queue."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    quality_report = build_report(load_catalog_rows(args.catalog))
    queue = build_queue(quality_report)
    write_json(args.json_output, queue)
    write_csv(queue, args.csv_output)
    print(json.dumps(queue["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
