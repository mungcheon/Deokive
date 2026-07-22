from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "ichiban_kuji_metadata_action_queue_public.json"
OUTPUT = DATA / "ichiban_kuji_metadata_fast_review_public.json"

WORKFLOW_PRIORITY = {
    "release_and_price_review": 10,
    "release_date_review": 20,
    "price_review": 30,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def iter_campaigns(action_queue: dict[str, Any]) -> list[dict[str, Any]]:
    campaigns: list[dict[str, Any]] = []
    for batch in action_queue.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for campaign in batch.get("campaigns") or []:
            if isinstance(campaign, dict):
                campaigns.append(campaign)
    return campaigns


def compact_template(template: dict[str, Any]) -> dict[str, Any]:
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "field": template.get("field"),
        "manual_value": "",
        "evidence_url": template.get("evidence_url"),
        "campaign_slug": template.get("campaign_slug"),
        "campaign_title": template.get("campaign_title"),
        "workflow": template.get("workflow"),
        "target_scope": template.get("target_scope"),
        "target_catalog_item_rows": template.get("target_catalog_item_rows"),
        "target_catalog_indexes_sample": template.get("target_catalog_indexes_sample") or [],
        "requires_labeled_official_evidence": True,
        "blocked_until": "manual_official_evidence_confirmed",
    }


def compact_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    templates = [
        compact_template(template)
        for template in campaign.get("campaign_field_patch_templates") or []
        if isinstance(template, dict)
    ]
    return {
        "slug": campaign.get("slug"),
        "url": campaign.get("url"),
        "title": campaign.get("title"),
        "workflow": campaign.get("workflow"),
        "missing_fields": campaign.get("missing_fields") or [],
        "catalog_item_rows": campaign.get("catalog_item_rows") or 0,
        "review_priority": campaign.get("review_priority"),
        "sample_catalog_indexes": campaign.get("sample_catalog_indexes") or [],
        "sample_names": campaign.get("sample_names") or [],
        "campaign_field_patch_templates": templates,
        "evidence_checklist": campaign.get("evidence_checklist") or [],
        "manual_confirmation_template": campaign.get("manual_confirmation_template"),
        "confirmed_queue": campaign.get("confirmed_queue"),
        "import_tool": campaign.get("import_tool"),
        "unblocks_when": campaign.get("unblocks_when"),
        "auto_apply_enabled": False,
    }


def counter_rows(counter: Counter[str], field: str) -> list[dict[str, Any]]:
    return [{field: key, "campaigns": value} for key, value in counter.most_common()]


def build_report(
    action_queue: dict[str, Any],
    *,
    max_campaigns: int = 20,
    generated_at: str | None = None,
) -> dict[str, Any]:
    campaigns = [compact_campaign(campaign) for campaign in iter_campaigns(action_queue)]
    campaigns = [campaign for campaign in campaigns if campaign.get("campaign_field_patch_templates")]
    campaigns.sort(
        key=lambda campaign: (
            WORKFLOW_PRIORITY.get(str(campaign.get("workflow") or ""), 99),
            -int(campaign.get("catalog_item_rows") or 0),
            str(campaign.get("slug") or ""),
        )
    )
    fast_campaigns = campaigns[:max_campaigns]
    held_campaigns = campaigns[max_campaigns:]
    workflow_counts = Counter(str(campaign.get("workflow") or "") for campaign in fast_campaigns)
    missing_field_counts = Counter(
        str(field)
        for campaign in fast_campaigns
        for field in campaign.get("missing_fields") or []
    )
    patch_counts = Counter(
        str(template.get("field") or "")
        for campaign in fast_campaigns
        for template in campaign.get("campaign_field_patch_templates") or []
    )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "ichiban_kuji_metadata_fast_review",
        "summary": {
            "fast_review_campaigns": len(fast_campaigns),
            "held_for_later_campaigns": len(held_campaigns),
            "fast_review_catalog_item_rows": sum(int(campaign.get("catalog_item_rows") or 0) for campaign in fast_campaigns),
            "manual_confirmed_true": 0,
            "auto_apply_enabled": False,
        },
        "breakdowns": {
            "by_workflow": counter_rows(workflow_counts, "workflow"),
            "by_missing_field": counter_rows(missing_field_counts, "missing_field"),
            "by_patch_field": counter_rows(patch_counts, "patch_field"),
        },
        "items": fast_campaigns,
        "held_for_later_summary": {
            "by_workflow": counter_rows(
                Counter(str(campaign.get("workflow") or "") for campaign in held_campaigns),
                "workflow",
            ),
            "catalog_item_rows": sum(int(campaign.get("catalog_item_rows") or 0) for campaign in held_campaigns),
        },
        "automation_policy": {
            "auto_apply_release_date": False,
            "auto_apply_official_price_jpy": False,
            "requires_manual_review": True,
            "requires_labeled_official_evidence": True,
            "confirmed_queue": "server/ichiban_kuji_metadata_confirmed_rows.json",
            "import_tool": "tools/import_confirmed_ichiban_metadata_rows.py",
        },
    }


def write_report(report: dict[str, Any], path: Path = OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--max-campaigns", type=int, default=20)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), max_campaigns=args.max_campaigns)
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
