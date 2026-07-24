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
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_deduplication_action_queue_public.json"
DEFAULT_OUTPUT = DATA / "ichiban_kuji_reissue_decision_template_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _copy_template(row: dict[str, Any]) -> dict[str, Any]:
    template = dict(row.get("decision_template") or {})
    template["manual_confirmed"] = False
    template["decision"] = ""
    template.setdefault("evidence_urls", row.get("source_urls") or [])
    template.setdefault("manual_note", "")
    return template


def _first_url(urls: Any) -> str:
    if not isinstance(urls, list):
        return ""
    for url in urls:
        if isinstance(url, str) and url.strip():
            return url.strip()
    return ""


def _evidence_url_count(row: dict[str, Any]) -> int:
    return sum(1 for url in row.get("source_urls") or [] if isinstance(url, str) and url.strip())


def _sample_rows_with_identity(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if row.get("campaign_title")
        and (row.get("prize_rank") or row.get("sub_series"))
        and row.get("prize_item_name")
        and row.get("identity_label")
    )


def _is_zero_price_prize(row: dict[str, Any]) -> bool:
    label = " ".join(
        str(row.get(key) or "")
        for key in ("name_ko", "name_ja", "sub_series", "prize_rank", "prize_item_name")
    )
    return any(token in label for token in ("ラストワン", "LAST ONE", "Last One", "더블찬스", "ダブルチャンス"))


def _row_risk_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    zero_exception_rows = [row for row in rows if _is_zero_price_prize(row)]
    missing_price_rows = [
        row
        for row in rows
        if row.get("official_price_jpy") in (None, "")
        and not _is_zero_price_prize(row)
    ]
    zero_exception_nonzero_rows = [
        row
        for row in zero_exception_rows
        if row.get("official_price_jpy") not in (0, None, "")
    ]
    tags: list[str] = []
    if zero_exception_rows:
        tags.append("zero_price_exception_rows_present")
    if zero_exception_nonzero_rows:
        tags.append("zero_price_exception_price_review")
    if missing_price_rows:
        tags.append("non_exception_price_missing")
    if _sample_rows_with_identity(rows) == len(rows) and rows:
        tags.append("identity_fields_complete")
    return {
        "sample_row_count": len(rows),
        "zero_price_exception_sample_rows": len(zero_exception_rows),
        "zero_price_exception_nonzero_sample_rows": len(zero_exception_nonzero_rows),
        "non_exception_missing_price_sample_rows": len(missing_price_rows),
        "identity_field_sample_rows": _sample_rows_with_identity(rows),
        "review_risk_tags": tags,
    }


def _reissue_review_lane(row: dict[str, Any], risk_summary: dict[str, Any]) -> str:
    comparison = row.get("campaign_url_comparison") or {}
    if comparison.get("likely_same_campaign_family_reissue"):
        return "same_campaign_family_reissue_review"
    if "zero_price_exception_rows_present" in (risk_summary.get("review_risk_tags") or []):
        return "zero_price_exception_reissue_review"
    if int(risk_summary.get("non_exception_missing_price_sample_rows") or 0) > 0:
        return "price_then_reissue_identity_review"
    return "item_pair_review"


def _campaign_decision_guidance(row: dict[str, Any], risk_summary: dict[str, Any]) -> dict[str, Any]:
    comparison = row.get("campaign_url_comparison") or {}
    high_impact = int(row.get("item_work_order_count") or 0) >= 5
    required_evidence = [
        "official campaign title on every source URL",
        "sale or release period on every source URL",
        "full prize lineup compared by rank",
        "same-rank prize item names compared",
        "variant names checked when one rank contains multiple kinds",
    ]
    if int(risk_summary.get("non_exception_missing_price_sample_rows") or 0) > 0:
        required_evidence.append("non-exception official price confirmed or explicitly left unknown")
    if int(risk_summary.get("zero_price_exception_sample_rows") or 0) > 0:
        required_evidence.append("Last One or Double Chance rows keep official_price_jpy=0")
    return {
        "status": "campaign_pair_reissue_decision_required",
        "likely_same_campaign_family_reissue": bool(
            comparison.get("likely_same_campaign_family_reissue")
        ),
        "high_impact_campaign_pair": high_impact,
        "required_evidence": required_evidence,
        "decision_options": [
            "campaign_pair_reissue_keep_all_separate",
            "campaign_pair_duplicate_review_each_item_keep_drop",
            "needs_more_source_evidence",
        ],
        "recommended_first_decision": (
            "campaign_pair_reissue_keep_all_separate"
            if comparison.get("likely_same_campaign_family_reissue")
            else "needs_more_source_evidence"
        ),
        "manual_confirmed_allowed": False,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def _item_template(row: dict[str, Any]) -> dict[str, Any]:
    template = _copy_template(row)
    sample_rows = row.get("sample_rows") or []
    risk_summary = _row_risk_summary(sample_rows)
    comparison = row.get("campaign_url_comparison") or {}
    review_tags = list(risk_summary["review_risk_tags"])
    if comparison.get("likely_same_campaign_family_reissue"):
        review_tags.append("likely_same_campaign_family_reissue")
    risk_summary = {**risk_summary, "review_risk_tags": review_tags}
    return {
        "work_order_id": row.get("work_order_id"),
        "campaign_work_order_id": row.get("campaign_work_order_id"),
        "priority": row.get("priority"),
        "normalized_name": row.get("normalized_name"),
        "catalog_indexes": row.get("catalog_indexes") or [],
        "source_urls": row.get("source_urls") or [],
        "first_evidence_url": _first_url(row.get("source_urls")),
        "evidence_url_count": _evidence_url_count(row),
        "campaign_slug_families": row.get("campaign_slug_families") or [],
        "campaign_url_comparison": row.get("campaign_url_comparison") or {},
        "reissue_signal_reasons": row.get("reissue_signal_reasons") or [],
        "manual_review_checklist": row.get("manual_review_checklist") or [],
        "sample_rows": sample_rows,
        "sample_rows_with_identity_fields": _sample_rows_with_identity(sample_rows),
        "review_risk_summary": risk_summary,
        "recommended_review_lane": _reissue_review_lane(row, risk_summary),
        "recommended_reviewer_action": (
            "Treat same-family numbered 1kuji URLs as possible reissues first; only record keep/drop after official campaign pages prove an exact duplicate."
        ),
        "decision_template": template,
        "manual_confirmed": False,
        "decision": template.get("decision") or "",
        "keep_catalog_index": template.get("keep_catalog_index"),
        "drop_catalog_indexes": template.get("drop_catalog_indexes") or [],
        "evidence_urls": template.get("evidence_urls") or [],
        "manual_note": template.get("manual_note") or "",
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def _campaign_template(row: dict[str, Any]) -> dict[str, Any]:
    template = _copy_template(row)
    sample_rows = row.get("sample_rows") or []
    risk_summary = _row_risk_summary(sample_rows)
    comparison = row.get("campaign_url_comparison") or {}
    review_tags = list(risk_summary["review_risk_tags"])
    if comparison.get("likely_same_campaign_family_reissue"):
        review_tags.append("likely_same_campaign_family_reissue")
    if int(row.get("item_work_order_count") or 0) >= 5:
        review_tags.append("high_impact_campaign_pair")
    risk_summary = {
        **risk_summary,
        "review_risk_tags": review_tags,
    }
    return {
        "campaign_work_order_id": row.get("campaign_work_order_id"),
        "priority": row.get("priority"),
        "source_urls": row.get("source_urls") or [],
        "first_evidence_url": _first_url(row.get("source_urls")),
        "evidence_url_count": _evidence_url_count(row),
        "item_work_order_count": row.get("item_work_order_count") or 0,
        "affected_item_work_order_ids": template.get("affected_item_work_order_ids") or [],
        "catalog_indexes": row.get("catalog_indexes") or [],
        "prize_labels": row.get("prize_labels") or [],
        "campaign_url_comparison": comparison,
        "manual_review_checklist": row.get("manual_review_checklist") or [],
        "sample_rows": sample_rows,
        "sample_rows_with_identity_fields": _sample_rows_with_identity(sample_rows),
        "review_risk_summary": risk_summary,
        "campaign_decision_guidance": _campaign_decision_guidance(row, risk_summary),
        "recommended_review_lane": (
            "campaign_pair_first"
            if int(row.get("item_work_order_count") or 0) > 1
            else "item_pair_review"
        ),
        "recommended_reviewer_action": (
            "Compare the official campaign pages first; one campaign decision can settle all affected item work orders."
        ),
        "decision_template": template,
        "manual_confirmed": False,
        "decision": template.get("decision") or "",
        "evidence_urls": template.get("evidence_urls") or [],
        "manual_note": template.get("manual_note") or "",
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def _campaign_item_decision_preview(
    campaign: dict[str, Any],
    item_templates_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    affected_ids = campaign.get("affected_item_work_order_ids") or []
    for work_order_id in affected_ids:
        if not isinstance(work_order_id, str):
            continue
        item = item_templates_by_id.get(work_order_id, {})
        previews.append(
            {
                "work_order_id": work_order_id,
                "catalog_indexes": item.get("catalog_indexes") or [],
                "source_urls": item.get("source_urls") or campaign.get("source_urls") or [],
                "first_evidence_url": item.get("first_evidence_url")
                or _first_url(campaign.get("source_urls")),
                "campaign_url_comparison": item.get("campaign_url_comparison") or {},
                "recommended_review_lane": item.get("recommended_review_lane") or "",
                "review_risk_tags": (item.get("review_risk_summary") or {}).get("review_risk_tags") or [],
                "suggested_decision_if_campaign_is_reissue": (
                    "reissue_or_campaign_variant_keep_separate"
                ),
                "suggested_decision_if_campaign_is_duplicate": (
                    "same_sellable_product_keep_drop_confirmed"
                ),
                "keep_drop_still_requires_item_review": True,
                "manual_confirmed": False,
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
            }
        )
    return previews


def _compact_campaign_item_preview(
    preview: dict[str, Any],
    item_templates_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    work_order_id = str(preview.get("work_order_id") or "")
    item = item_templates_by_id.get(work_order_id, {})
    sample_rows = item.get("sample_rows") or []
    sample = sample_rows[0] if sample_rows and isinstance(sample_rows[0], dict) else {}
    return {
        "work_order_id": work_order_id,
        "catalog_indexes": preview.get("catalog_indexes") or [],
        "first_evidence_url": preview.get("first_evidence_url") or "",
        "campaign_title": sample.get("campaign_title") or "",
        "prize_rank": sample.get("prize_rank") or sample.get("sub_series") or "",
        "prize_item_name": sample.get("prize_item_name") or "",
        "variant_name": sample.get("variant_name") or "",
        "identity_label": sample.get("identity_label") or "",
        "sample_name_ko": sample.get("name_ko") or "",
        "sample_name_ja": sample.get("name_ja") or "",
        "campaign_url_comparison": item.get("campaign_url_comparison") or {},
        "recommended_review_lane": item.get("recommended_review_lane") or "",
        "review_risk_tags": (item.get("review_risk_summary") or {}).get("review_risk_tags") or [],
        "suggested_decision_if_campaign_is_reissue": preview.get(
            "suggested_decision_if_campaign_is_reissue"
        ),
        "suggested_decision_if_campaign_is_duplicate": preview.get(
            "suggested_decision_if_campaign_is_duplicate"
        ),
        "keep_drop_still_requires_item_review": bool(
            preview.get("keep_drop_still_requires_item_review")
        ),
        "manual_confirmed": False,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def _next_campaign_review_batch(
    campaign_templates: list[dict[str, Any]],
    item_templates_by_id: dict[str, dict[str, Any]],
    *,
    limit: int = 4,
    item_preview_limit: int = 12,
) -> list[dict[str, Any]]:
    def score(campaign: dict[str, Any]) -> tuple[int, int, int, int]:
        risk = campaign.get("review_risk_summary") or {}
        return (
            int(campaign.get("item_work_order_count") or 0),
            int(risk.get("non_exception_missing_price_sample_rows") or 0),
            int(risk.get("zero_price_exception_sample_rows") or 0),
            int(campaign.get("evidence_url_count") or 0),
        )

    ordered = sorted(campaign_templates, key=score, reverse=True)
    batch: list[dict[str, Any]] = []
    for campaign in ordered[:limit]:
        item_previews = [
            _compact_campaign_item_preview(preview, item_templates_by_id)
            for preview in (campaign.get("item_decision_application_preview") or [])
            if isinstance(preview, dict)
        ]
        visible_item_previews = item_previews[:item_preview_limit]
        hidden_preview_rows = max(0, len(item_previews) - len(visible_item_previews))
        batch.append(
            {
                "campaign_work_order_id": campaign.get("campaign_work_order_id"),
                "priority": campaign.get("priority"),
                "item_work_order_count": campaign.get("item_work_order_count") or 0,
                "catalog_index_count": len(campaign.get("catalog_indexes") or []),
                "first_evidence_url": campaign.get("first_evidence_url") or "",
                "source_urls": campaign.get("source_urls") or [],
                "prize_labels": campaign.get("prize_labels") or [],
                "campaign_url_comparison": campaign.get("campaign_url_comparison") or {},
                "review_risk_tags": (campaign.get("review_risk_summary") or {}).get("review_risk_tags") or [],
                "recommended_review_lane": campaign.get("recommended_review_lane"),
                "recommended_reviewer_action": campaign.get("recommended_reviewer_action"),
                "campaign_decision_guidance": campaign.get("campaign_decision_guidance")
                or {},
                "affected_item_work_order_ids": campaign.get("affected_item_work_order_ids") or [],
                "item_review_preview_rows": len(item_previews),
                "visible_item_review_preview_rows": len(visible_item_previews),
                "hidden_item_review_preview_rows": hidden_preview_rows,
                "item_review_preview": visible_item_previews,
                "item_review_preview_truncated": hidden_preview_rows > 0,
                "manual_confirmed": False,
            }
        )
    return batch


def build_report(action_queue: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    item_templates = [_item_template(row) for row in _safe_list(action_queue.get("ichiban_reissue_work_order"))]
    campaign_templates = [
        _campaign_template(row) for row in _safe_list(action_queue.get("ichiban_reissue_campaign_work_order"))
    ]
    item_templates_by_id = {
        str(item.get("work_order_id")): item
        for item in item_templates
        if item.get("work_order_id")
    }
    for campaign in campaign_templates:
        campaign["item_decision_application_preview"] = _campaign_item_decision_preview(
            campaign,
            item_templates_by_id,
        )
        campaign["item_decision_application_preview_rows"] = len(
            campaign["item_decision_application_preview"]
        )
    next_campaign_review_batch = _next_campaign_review_batch(campaign_templates, item_templates_by_id)

    item_decisions = Counter(item["decision"] or "unconfirmed" for item in item_templates)
    campaign_decisions = Counter(item["decision"] or "unconfirmed" for item in campaign_templates)
    item_review_lanes = Counter(
        item.get("recommended_review_lane") or "item_pair_review"
        for item in item_templates
    )
    campaign_review_lanes = Counter(
        item.get("recommended_review_lane") or "campaign_pair_first"
        for item in campaign_templates
    )
    campaign_covered_item_ids = {
        work_order_id
        for campaign in campaign_templates
        for work_order_id in campaign.get("affected_item_work_order_ids", [])
        if isinstance(work_order_id, str)
    }
    summary = {
        "item_template_rows": len(item_templates),
        "campaign_template_rows": len(campaign_templates),
        "manual_confirmed_item_rows": sum(1 for item in item_templates if item.get("manual_confirmed") is True),
        "manual_confirmed_campaign_rows": sum(
            1 for item in campaign_templates if item.get("manual_confirmed") is True
        ),
        "same_sellable_product_keep_drop_ready_rows": sum(
            1
            for item in item_templates
            if item.get("manual_confirmed") is True
            and item.get("decision") == "same_sellable_product_keep_drop_confirmed"
        ),
        "keep_separate_confirmed_rows": sum(
            1
            for item in item_templates
            if item.get("manual_confirmed") is True
            and item.get("decision") == "reissue_or_campaign_variant_keep_separate"
        ),
        "item_decision_counts": [[key, count] for key, count in sorted(item_decisions.items())],
        "campaign_decision_counts": [[key, count] for key, count in sorted(campaign_decisions.items())],
        "item_review_lane_counts": [[key, count] for key, count in sorted(item_review_lanes.items())],
        "campaign_review_lane_counts": [[key, count] for key, count in sorted(campaign_review_lanes.items())],
        "same_campaign_family_reissue_item_rows": item_review_lanes.get(
            "same_campaign_family_reissue_review",
            0,
        ),
        "zero_price_exception_reissue_item_rows": item_review_lanes.get(
            "zero_price_exception_reissue_review",
            0,
        ),
        "campaign_covered_item_template_rows": sum(
            1 for item in item_templates if item.get("work_order_id") in campaign_covered_item_ids
        ),
        "standalone_item_template_rows": sum(
            1 for item in item_templates if item.get("work_order_id") not in campaign_covered_item_ids
        ),
        "campaign_item_decision_preview_rows": sum(
            int(campaign.get("item_decision_application_preview_rows") or 0)
            for campaign in campaign_templates
        ),
        "item_templates_with_evidence_urls": sum(1 for item in item_templates if item.get("first_evidence_url")),
        "item_templates_with_identity_fields": sum(
            1 for item in item_templates if int(item.get("sample_rows_with_identity_fields") or 0) > 0
        ),
        "campaign_templates_with_evidence_urls": sum(
            1 for campaign in campaign_templates if campaign.get("first_evidence_url")
        ),
        "campaign_templates_with_identity_fields": sum(
            1 for campaign in campaign_templates if int(campaign.get("sample_rows_with_identity_fields") or 0) > 0
        ),
        "campaign_review_batch_rows": len(next_campaign_review_batch),
        "campaign_review_batch_item_work_order_rows": sum(
            int(campaign.get("item_work_order_count") or 0)
            for campaign in next_campaign_review_batch
        ),
        "campaign_review_batch_catalog_index_rows": sum(
            int(campaign.get("catalog_index_count") or 0)
            for campaign in next_campaign_review_batch
        ),
        "campaign_review_batch_zero_price_exception_sample_rows": sum(
            int(
                (campaign.get("review_risk_summary") or {}).get(
                    "zero_price_exception_sample_rows"
                )
                or 0
            )
            for campaign in campaign_templates
            if campaign.get("campaign_work_order_id")
            in {row.get("campaign_work_order_id") for row in next_campaign_review_batch}
        ),
        "campaign_review_batch_item_preview_rows": sum(
            int(campaign.get("item_review_preview_rows") or 0)
            for campaign in next_campaign_review_batch
        ),
        "campaign_review_batch_visible_item_preview_rows": sum(
            len(campaign.get("item_review_preview") or [])
            for campaign in next_campaign_review_batch
        ),
        "campaign_review_batch_truncated_campaigns": sum(
            1
            for campaign in next_campaign_review_batch
            if campaign.get("item_review_preview_truncated")
        ),
        "first_item_evidence_url": _first_url(
            [item.get("first_evidence_url") for item in item_templates]
        ),
        "first_campaign_evidence_url": _first_url(
            [campaign.get("first_evidence_url") for campaign in campaign_templates]
        ),
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
        "manual_review_required_before_mutation": True,
        "recommended_next_action": "fill_campaign_decisions_first_then_confirm_item_keep_drop_or_keep_separate",
    }

    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "ichiban_kuji_reissue_decision_template",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": summary,
        "instructions": [
            "Review campaign_templates first when one campaign URL pair covers many item work orders.",
            "Set manual_confirmed=true only after checking official campaign pages and evidence_urls.",
            "Use reissue_or_campaign_variant_keep_separate when rows are legitimate reissues or campaign waves.",
            "Use same_sellable_product_keep_drop_confirmed only for exact duplicates, with one keep_catalog_index and explicit drop_catalog_indexes.",
            "Do not import any merge/delete mutation from this file unless manual_confirmed=true and evidence_urls prove the decision.",
        ],
        "automation_policy": {
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
            "manual_review_required_before_mutation": True,
        },
        "campaign_templates": campaign_templates,
        "next_campaign_review_batch": next_campaign_review_batch,
        "item_templates": item_templates,
    }


def write_report(report: dict[str, Any], path: Path = DEFAULT_OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(_load_json(args.input))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
