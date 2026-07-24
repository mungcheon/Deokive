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

CONFIRMED_TEMPLATE = "server/ichiban_kuji_metadata_confirmed_rows.template.json"
CONFIRMED_QUEUE = "server/ichiban_kuji_metadata_confirmed_rows.json"
IMPORT_TOOL = "tools/import_confirmed_ichiban_metadata_rows.py"
UNBLOCKS_WHEN = "labeled_official_1kuji_campaign_metadata_confirmed"


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


def _primary_review_url(campaign: dict[str, Any], templates: list[dict[str, Any]]) -> str:
    url = str(campaign.get("url") or "").strip()
    if url:
        return url
    for template in templates:
        evidence_url = str(template.get("evidence_url") or "").strip()
        if evidence_url:
            return evidence_url
    return ""


def _review_url_kind(url: str) -> str:
    if not url:
        return ""
    if "1kuji.com/products/" in url:
        return "official_1kuji_campaign_page"
    if "1kuji.com" in url:
        return "official_1kuji_page"
    return "external_or_archive_evidence"


def _evidence_urls(campaign: dict[str, Any], templates: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for value in [campaign.get("url")] + [template.get("evidence_url") for template in templates]:
        url = str(value or "").strip()
        if url and url not in urls:
            urls.append(url)
    return urls


def _field_confirmation_rules(fields: list[str]) -> list[str]:
    rules: list[str] = []
    if "release_date" in fields:
        rules.extend(
            [
                "release_date_must_be_labeled_campaign_release_or_sales_start_date",
                "ignore_double_chance_entry_deadline_or_prize_shipping_dates",
            ]
        )
    if "official_price_jpy" in fields:
        rules.extend(
            [
                "official_price_jpy_must_be_labeled_draw_price_or_price_per_try",
                "do_not_use_last_one_or_double_chance_exception_zero_price_as_draw_price",
            ]
        )
    return rules


def _patch_summary(templates: list[dict[str, Any]], catalog_item_rows: Any) -> dict[str, Any]:
    fields = [str(template.get("field") or "") for template in templates if template.get("field")]
    target_scopes = sorted(
        {
            str(template.get("target_scope") or "")
            for template in templates
            if template.get("target_scope")
        }
    )
    requires_full_expansion = any(
        bool(template.get("requires_full_campaign_index_expansion"))
        for template in templates
    )
    requires_labeled_evidence = any(
        bool(template.get("requires_labeled_official_evidence"))
        for template in templates
    )
    target_rows = max(
        [
            int(template.get("target_catalog_item_rows") or 0)
            for template in templates
            if isinstance(template, dict)
        ]
        + [int(catalog_item_rows or 0)]
    )
    return {
        "field_count": len(fields),
        "fields": fields,
        "target_scopes": target_scopes,
        "target_catalog_item_rows": target_rows,
        "requires_full_campaign_index_expansion": requires_full_expansion,
        "requires_labeled_official_evidence": requires_labeled_evidence,
        "field_confirmation_rules": _field_confirmation_rules(fields),
    }


def _review_lane(workflow: Any, fields: list[str]) -> str:
    workflow_text = str(workflow or "")
    if "release_date" in fields and "official_price_jpy" in fields:
        return "confirm_release_date_and_draw_price"
    if workflow_text == "release_date_review" or "release_date" in fields:
        return "confirm_campaign_release_date"
    if workflow_text == "price_review" or "official_price_jpy" in fields:
        return "confirm_campaign_draw_price"
    return "confirm_campaign_metadata"


def _work_order(campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lane_order = [
        (
            "confirm_release_date_and_draw_price",
            "confirm_release_and_price",
            "Confirm both release date and draw price on the same official campaign page.",
            10,
        ),
        (
            "confirm_campaign_release_date",
            "confirm_release_dates",
            "Confirm labeled campaign release or sales-start dates first.",
            20,
        ),
        (
            "confirm_campaign_draw_price",
            "confirm_draw_prices",
            "Confirm labeled draw price or price-per-try after release dates.",
            30,
        ),
        (
            "confirm_campaign_metadata",
            "confirm_remaining_metadata",
            "Confirm remaining campaign metadata with labeled official evidence.",
            90,
        ),
    ]
    rows_by_lane: dict[str, list[dict[str, Any]]] = {}
    for campaign in campaigns:
        rows_by_lane.setdefault(str(campaign.get("review_lane") or ""), []).append(campaign)

    work_order: list[dict[str, Any]] = []
    for review_lane, lane, description, rank in lane_order:
        rows = rows_by_lane.get(review_lane) or []
        if not rows:
            continue
        field_counts = Counter(
            field
            for row in rows
            for field in row.get("patch_summary", {}).get("fields") or []
        )
        work_order.append(
            {
                "rank": rank,
                "lane": lane,
                "review_lane": review_lane,
                "description": description,
                "campaign_count": len(rows),
                "catalog_item_rows": sum(int(row.get("catalog_item_rows") or 0) for row in rows),
                "field_patch_template_counts": field_counts.most_common(),
                "manual_confirmation_template": CONFIRMED_TEMPLATE,
                "confirmed_queue": CONFIRMED_QUEUE,
                "import_tool": IMPORT_TOOL,
                "requires_manual_review": True,
                "auto_apply_enabled": False,
                "next_step": "fill_confirmed_ichiban_campaign_patch_templates",
                "guardrails": [
                    "official_campaign_title_matches_catalog_series",
                    "evidence_url_is_official_1kuji_campaign_or_captured_official_archive",
                    *_field_confirmation_rules(list(field_counts.keys())),
                ],
                "sample_campaigns": [
                    {
                        "slug": row.get("slug"),
                        "title": row.get("title"),
                        "url": row.get("url"),
                        "primary_review_url": row.get("primary_review_url"),
                        "primary_review_url_kind": row.get("primary_review_url_kind"),
                        "catalog_item_rows": row.get("catalog_item_rows"),
                    }
                    for row in rows[:5]
                ],
            }
        )
    return work_order


def _campaign_patch_work_order(campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, campaign in enumerate(campaigns, start=1):
        templates = [
            template
            for template in campaign.get("campaign_field_patch_templates") or []
            if isinstance(template, dict)
        ]
        fields = [
            str(template.get("field") or "")
            for template in templates
            if template.get("field")
        ]
        rows.append(
            {
                "rank": index,
                "review_lane": campaign.get("review_lane"),
                "slug": campaign.get("slug"),
                "title": campaign.get("title"),
                "url": campaign.get("url"),
                "primary_review_url": campaign.get("primary_review_url"),
                "primary_review_url_kind": campaign.get("primary_review_url_kind"),
                "evidence_urls": campaign.get("evidence_urls") or [],
                "evidence_url_count": campaign.get("evidence_url_count") or 0,
                "catalog_item_rows": campaign.get("catalog_item_rows"),
                "fields_to_confirm": fields,
                "field_patch_template_count": len(templates),
                "sample_catalog_indexes": campaign.get("sample_catalog_indexes") or [],
                "sample_names": campaign.get("sample_names") or [],
                "manual_confirmation_requirements": campaign.get(
                    "manual_confirmation_requirements"
                )
                or [],
                "field_patch_templates": templates,
                "manual_confirmed": False,
                "manual_confirmation_template": CONFIRMED_TEMPLATE,
                "confirmed_queue": CONFIRMED_QUEUE,
                "import_tool": IMPORT_TOOL,
                "blocked_until": UNBLOCKS_WHEN,
                "auto_apply_enabled": False,
            }
        )
    return rows


def _next_campaign_patch_review_batch(
    work_order_rows: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in work_order_rows[:limit]:
        templates = [
            template
            for template in row.get("field_patch_templates") or []
            if isinstance(template, dict)
        ]
        rows.append(
            {
                "manual_confirmed": False,
                "rank": row.get("rank"),
                "review_lane": row.get("review_lane"),
                "slug": row.get("slug"),
                "title": row.get("title"),
                "primary_review_url": row.get("primary_review_url"),
                "primary_review_url_kind": row.get("primary_review_url_kind"),
                "evidence_urls": row.get("evidence_urls") or [],
                "catalog_item_rows": row.get("catalog_item_rows"),
                "fields_to_confirm": row.get("fields_to_confirm") or [],
                "sample_catalog_indexes": row.get("sample_catalog_indexes") or [],
                "sample_names": (row.get("sample_names") or [])[:8],
                "field_patch_templates": templates,
                "manual_value_fields_to_fill": [
                    {
                        "field": template.get("field"),
                        "manual_value": "",
                        "evidence_url": template.get("evidence_url")
                        or row.get("primary_review_url")
                        or "",
                    }
                    for template in templates
                ],
                "operator_checklist": [
                    "Open primary_review_url first.",
                    "Confirm the campaign title matches the catalog series.",
                    "Use only labeled official 1kuji campaign metadata.",
                    "For release_date, ignore double chance deadlines and prize shipping dates.",
                    "For official_price_jpy, use the draw price or price-per-try, not Last One or Double Chance exception values.",
                    "Set manual_confirmed=true only after every field in fields_to_confirm is filled.",
                ],
                "blocked_until": row.get("blocked_until") or UNBLOCKS_WHEN,
                "manual_confirmation_template": CONFIRMED_TEMPLATE,
                "confirmed_queue": CONFIRMED_QUEUE,
                "import_tool": IMPORT_TOOL,
                "auto_apply_enabled": False,
            }
        )
    return rows


def _compact_campaign(campaign: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    templates = [
        template
        for template in campaign.get("campaign_field_patch_templates") or []
        if isinstance(template, dict)
    ]
    patch_summary = _patch_summary(templates, campaign.get("catalog_item_rows"))
    fields = patch_summary["fields"]
    primary_review_url = _primary_review_url(campaign, templates)
    evidence_urls = _evidence_urls(campaign, templates)
    return {
        "group_key": campaign.get("group_key"),
        "url": campaign.get("url"),
        "primary_review_url": primary_review_url,
        "primary_review_url_kind": _review_url_kind(primary_review_url),
        "evidence_urls": evidence_urls,
        "evidence_url_count": len(evidence_urls),
        "slug": campaign.get("slug"),
        "title": campaign.get("title"),
        "catalog_item_rows": campaign.get("catalog_item_rows"),
        "missing_fields": campaign.get("missing_fields") or [],
        "workflow": campaign.get("workflow"),
        "review_lane": _review_lane(campaign.get("workflow"), fields),
        "review_priority": campaign.get("review_priority"),
        "source_evidence_required": campaign.get("source_evidence_required"),
        "patch_summary": patch_summary,
        "manual_confirmation_requirements": [
            "official_campaign_title_matches_catalog_series",
            "evidence_url_is_official_1kuji_campaign_or_captured_official_archive",
            *patch_summary["field_confirmation_rules"],
        ],
        "next_machine_step": campaign.get("next_machine_step") or batch.get("next_machine_step"),
        "evidence_checklist": campaign.get("evidence_checklist") or batch.get("evidence_checklist") or [],
        "sample_catalog_indexes": campaign.get("sample_catalog_indexes") or [],
        "sample_names": campaign.get("sample_names") or [],
        "campaign_field_patch_templates": templates,
        "manual_confirmation_template": CONFIRMED_TEMPLATE,
        "confirmed_queue": CONFIRMED_QUEUE,
        "import_tool": IMPORT_TOOL,
        "unblocks_when": UNBLOCKS_WHEN,
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
    work_order = _work_order(published)
    campaign_patch_work_order = _campaign_patch_work_order(published)
    next_campaign_patch_review_batch = _next_campaign_patch_review_batch(
        campaign_patch_work_order
    )

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(published), batch_size):
        chunk = published[offset : offset + batch_size]
        workflow_counts = Counter(str(row.get("workflow") or "") for row in chunk)
        field_counts = Counter(field for row in chunk for field in row.get("missing_fields") or [])
        patch_template_counts = Counter(
            template["field"]
            for row in chunk
            for template in row.get("campaign_field_patch_templates") or []
            if isinstance(template, dict) and template.get("field")
        )
        batches.append(
            {
                "batch_id": f"ichiban-metadata-action-{len(batches) + 1:03d}",
                "priority": min(WORKFLOW_PRIORITY.get(str(row.get("workflow") or ""), 99) for row in chunk),
                "campaign_count": len(chunk),
                "catalog_item_rows": sum(int(row.get("catalog_item_rows") or 0) for row in chunk),
                "offset": offset,
                "workflow_counts": workflow_counts.most_common(),
                "missing_field_counts": field_counts.most_common(),
                "field_patch_template_counts": patch_template_counts.most_common(),
                "review_state": "manual_official_campaign_metadata_confirmation_required",
                "next_machine_step": "fill_confirmed_ichiban_campaign_patch_templates",
                "recommended_action": "Confirm labeled official 1kuji release dates and draw prices, then fill campaign patch templates.",
                "manual_confirmation_template": CONFIRMED_TEMPLATE,
                "confirmed_queue": CONFIRMED_QUEUE,
                "import_tool": IMPORT_TOOL,
                "unblocks_when": UNBLOCKS_WHEN,
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
    review_url_kind_counts = Counter(
        str(row.get("primary_review_url_kind") or "")
        for row in campaigns
        if row.get("primary_review_url")
    )
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "ichiban_kuji_metadata_action_queue",
        "summary": {
            "actionable_campaigns": len(campaigns),
            "queued_action_campaigns": len(published),
            "unqueued_action_campaigns": max(len(campaigns) - len(published), 0),
            "campaign_queue_coverage": round(len(published) / len(campaigns), 4) if campaigns else 0,
            "queued_catalog_item_rows": sum(int(row.get("catalog_item_rows") or 0) for row in published),
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "max_campaigns": max_campaigns,
            "by_workflow": _counter_pairs(campaigns, "workflow"),
            "field_patch_template_count": sum(patch_template_counts.values()),
            "field_patch_template_counts": patch_template_counts.most_common(),
            "primary_review_url_rows": sum(1 for row in campaigns if row.get("primary_review_url")),
            "queued_primary_review_url_rows": sum(1 for row in published if row.get("primary_review_url")),
            "primary_review_url_kind_counts": review_url_kind_counts.most_common(),
            "first_primary_review_url": next(
                (row.get("primary_review_url") for row in published if row.get("primary_review_url")),
                "",
            ),
            "work_order_steps": len(work_order),
            "work_order_lanes": [step["lane"] for step in work_order],
            "campaign_patch_work_order_rows": len(campaign_patch_work_order),
            "campaign_patch_work_order_template_rows": sum(
                int(row.get("field_patch_template_count") or 0)
                for row in campaign_patch_work_order
            ),
            "next_campaign_patch_review_batch_rows": len(next_campaign_patch_review_batch),
            "next_campaign_patch_review_batch_template_rows": sum(
                len(row.get("field_patch_templates") or [])
                for row in next_campaign_patch_review_batch
            ),
            "next_campaign_patch_review_batch_primary_review_url_rows": sum(
                1 for row in next_campaign_patch_review_batch if row.get("primary_review_url")
            ),
            "next_campaign_patch_review_batch_field_counts": Counter(
                field
                for row in next_campaign_patch_review_batch
                for field in row.get("fields_to_confirm") or []
            ).most_common(),
            "skipped_without_templates": skipped_without_templates,
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Work this queue before broad historical 1kuji research.",
            "Use only labeled official 1kuji campaign pages or captured official evidence.",
            "Fill templates only after manual confirmation; no campaign metadata is auto-applied.",
            f"Copy {CONFIRMED_TEMPLATE} to {CONFIRMED_QUEUE}, fill manual_value and confirmation flags, then run {IMPORT_TOOL}.",
        ],
        "work_order": work_order,
        "campaign_patch_work_order": campaign_patch_work_order,
        "next_campaign_patch_review_batch": next_campaign_patch_review_batch,
        "batches": batches,
        "automation_policy": {
            "auto_apply_release_date": False,
            "auto_apply_official_price_jpy": False,
            "requires_manual_review": True,
            "manual_confirmation_template": CONFIRMED_TEMPLATE,
            "confirmed_queue": CONFIRMED_QUEUE,
            "import_tool": IMPORT_TOOL,
            "unblocks_when": UNBLOCKS_WHEN,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-campaigns", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_campaigns=args.max_campaigns, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
