from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "ichiban_kuji_metadata_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "ichiban_kuji_metadata_action_queue_public.json"

WORKFLOW_PRIORITY = {
    "release_and_price_review": 10,
    "release_date_review": 20,
    "price_review": 30,
    "metadata_review": 90,
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(str(row.get(key) or "") for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _compact_campaign(campaign: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    templates = [
        template
        for template in campaign.get("campaign_field_patch_templates") or []
        if isinstance(template, dict)
    ]
    return {
        "group_key": campaign.get("group_key"),
        "url": campaign.get("url"),
        "slug": campaign.get("slug"),
        "title": campaign.get("title"),
        "catalog_item_rows": campaign.get("catalog_item_rows"),
        "missing_fields": campaign.get("missing_fields") or [],
        "workflow": campaign.get("workflow"),
        "review_priority": campaign.get("review_priority"),
        "source_evidence_required": campaign.get("source_evidence_required"),
        "next_machine_step": campaign.get("next_machine_step") or batch.get("next_machine_step"),
        "evidence_checklist": campaign.get("evidence_checklist") or batch.get("evidence_checklist") or [],
        "sample_catalog_indexes": campaign.get("sample_catalog_indexes") or [],
        "sample_names": campaign.get("sample_names") or [],
        "campaign_field_patch_templates": templates,
        "auto_apply_enabled": False,
    }


def build_report(review_batches: dict[str, Any], *, max_campaigns: int = 32, batch_size: int = 8) -> dict[str, Any]:
    campaigns: list[dict[str, Any]] = []
    skipped_without_templates = 0
    for batch in review_batches.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for campaign in batch.get("campaigns") or []:
            if not isinstance(campaign, dict):
                continue
            compact = _compact_campaign(campaign, batch)
            if not compact["campaign_field_patch_templates"]:
                skipped_without_templates += 1
                continue
            campaigns.append(compact)

    campaigns.sort(
        key=lambda row: (
            WORKFLOW_PRIORITY.get(str(row.get("workflow") or ""), 99),
            int(row.get("review_priority") or 999),
            str(row.get("slug") or ""),
        )
    )
    published = campaigns[:max_campaigns]

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(published), batch_size):
        chunk = published[offset : offset + batch_size]
        workflow_counts = Counter(str(row.get("workflow") or "") for row in chunk)
        field_counts = Counter(field for row in chunk for field in row.get("missing_fields") or [])
        batches.append(
            {
                "batch_id": f"ichiban-metadata-action-{len(batches) + 1:03d}",
                "priority": min(WORKFLOW_PRIORITY.get(str(row.get("workflow") or ""), 99) for row in chunk),
                "campaign_count": len(chunk),
                "catalog_item_rows": sum(int(row.get("catalog_item_rows") or 0) for row in chunk),
                "offset": offset,
                "workflow_counts": workflow_counts.most_common(),
                "missing_field_counts": field_counts.most_common(),
                "review_state": "manual_official_campaign_metadata_confirmation_required",
                "next_machine_step": "fill_confirmed_ichiban_campaign_patch_templates",
                "recommended_action": "Confirm labeled official 1kuji release dates and draw prices, then fill campaign patch templates.",
                "campaigns": chunk,
                "auto_apply_enabled": False,
            }
        )

    patch_template_counts = Counter(
        template["field"]
        for row in campaigns
        for template in row.get("campaign_field_patch_templates") or []
        if isinstance(template, dict) and template.get("field")
    )
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "ichiban_kuji_metadata_action_queue",
        "summary": {
            "actionable_campaigns": len(campaigns),
            "queued_action_campaigns": len(published),
            "queued_catalog_item_rows": sum(int(row.get("catalog_item_rows") or 0) for row in published),
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "max_campaigns": max_campaigns,
            "by_workflow": _counter_pairs(campaigns, "workflow"),
            "field_patch_template_count": sum(patch_template_counts.values()),
            "field_patch_template_counts": patch_template_counts.most_common(),
            "skipped_without_templates": skipped_without_templates,
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Work this queue before broad historical 1kuji research.",
            "Use only labeled official 1kuji campaign pages or captured official evidence.",
            "Fill templates only after manual confirmation; no campaign metadata is auto-applied.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_release_date": False,
            "auto_apply_official_price_jpy": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-campaigns", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_campaigns=args.max_campaigns, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
