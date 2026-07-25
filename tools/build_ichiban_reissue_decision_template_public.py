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
DEFAULT_CATALOG_PUBLIC = DATA / "catalog_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _load_catalog_index(path: Path = DEFAULT_CATALOG_PUBLIC) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = _load_json(path)
    rows = payload.get("items")
    if not isinstance(rows, list):
        return {}
    index: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        catalog_index = row.get("catalog_index")
        if isinstance(catalog_index, int):
            index[catalog_index] = row
    return index


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


def _enrich_sample_rows_from_catalog(
    rows: list[dict[str, Any]],
    catalog_index: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not catalog_index:
        return rows
    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        index = row.get("catalog_index")
        catalog_row = catalog_index.get(index) if isinstance(index, int) else None
        if catalog_row:
            for field in (
                "release_date",
                "image_url",
                "local_image_path",
                "source_store",
                "category",
                "character_name",
            ):
                value = catalog_row.get(field)
                if value not in (None, ""):
                    enriched[field] = value
            if enriched.get("official_price_jpy") in (None, ""):
                enriched["official_price_jpy"] = catalog_row.get("official_price_jpy")
            if not enriched.get("source_url"):
                enriched["source_url"] = catalog_row.get("source_url")
        enriched_rows.append(enriched)
    return enriched_rows


def _unique_values(values: list[Any]) -> list[Any]:
    unique: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if value in (None, ""):
            continue
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return sorted(unique, key=lambda item: str(item))


def _sets_differ(sets: list[list[Any]]) -> bool:
    normalized = {
        json.dumps(_unique_values(values), ensure_ascii=False, sort_keys=True)
        for values in sets
        if _unique_values(values)
    }
    return len(normalized) > 1


def _source_url_catalog_evidence_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        source_url = str(row.get("source_url") or "").strip()
        if not source_url:
            continue
        by_source.setdefault(source_url, []).append(row)

    source_summaries: list[dict[str, Any]] = []
    for source_url in sorted(by_source):
        source_rows = by_source[source_url]
        source_summaries.append(
            {
                "source_url": source_url,
                "catalog_indexes": sorted(
                    index
                    for row in source_rows
                    if isinstance((index := row.get("catalog_index")), int)
                ),
                "release_dates": _unique_values(
                    [row.get("release_date") for row in source_rows]
                ),
                "image_urls": _unique_values(
                    [row.get("image_url") for row in source_rows]
                ),
                "local_image_paths": _unique_values(
                    [row.get("local_image_path") for row in source_rows]
                ),
                "official_price_jpy_values": _unique_values(
                    [row.get("official_price_jpy") for row in source_rows]
                ),
                "identity_labels": _unique_values(
                    [row.get("identity_label") for row in source_rows]
                ),
                "sample_names_ja": _unique_values(
                    [row.get("name_ja") for row in source_rows]
                )[:6],
                "row_count": len(source_rows),
            }
        )

    release_sets = [item["release_dates"] for item in source_summaries]
    image_sets = [item["image_urls"] for item in source_summaries]
    local_image_sets = [item["local_image_paths"] for item in source_summaries]
    price_sets = [item["official_price_jpy_values"] for item in source_summaries]
    signals: list[str] = []
    if _sets_differ(release_sets):
        signals.append("release_date_differs_by_source_url")
    if _sets_differ(image_sets):
        signals.append("image_url_differs_by_source_url")
    if _sets_differ(local_image_sets):
        signals.append("local_image_path_differs_by_source_url")
    if _sets_differ(price_sets):
        signals.append("official_price_jpy_differs_by_source_url")

    has_strong_keep_separate_signal = any(
        signal in signals
        for signal in (
            "release_date_differs_by_source_url",
            "image_url_differs_by_source_url",
            "local_image_path_differs_by_source_url",
        )
    )
    return {
        "source_url_count": len(source_summaries),
        "source_url_summaries": source_summaries,
        "release_date_sets_differ": _sets_differ(release_sets),
        "image_url_sets_differ": _sets_differ(image_sets),
        "local_image_path_sets_differ": _sets_differ(local_image_sets),
        "official_price_jpy_sets_differ": _sets_differ(price_sets),
        "reissue_evidence_signals": signals,
        "recommended_campaign_decision_from_local_evidence": (
            "campaign_pair_reissue_keep_all_separate"
            if has_strong_keep_separate_signal
            else "needs_more_source_evidence"
        ),
        "evidence_basis": "data/catalog_public.json rows matched by catalog_index",
        "manual_confirmation_required": True,
    }


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


def _price_policy_review(row: dict[str, Any], risk_summary: dict[str, Any]) -> dict[str, Any]:
    non_exception_missing = int(
        risk_summary.get("non_exception_missing_price_sample_rows") or 0
    )
    zero_exception_nonzero = int(
        risk_summary.get("zero_price_exception_nonzero_sample_rows") or 0
    )
    zero_exception_rows = int(risk_summary.get("zero_price_exception_sample_rows") or 0)
    blockers: list[str] = []
    if non_exception_missing:
        blockers.append("non_exception_official_price_missing")
    if zero_exception_nonzero:
        blockers.append("last_one_or_double_chance_price_must_be_zero")
    return {
        "status": "price_policy_review_required" if blockers else "price_policy_clear_for_identity_review",
        "blockers": blockers,
        "non_exception_missing_price_sample_rows": non_exception_missing,
        "zero_price_exception_sample_rows": zero_exception_rows,
        "zero_price_exception_nonzero_sample_rows": zero_exception_nonzero,
        "last_one_double_chance_expected_price_jpy": 0,
        "regular_prize_price_required_before_merge": bool(non_exception_missing),
        "blocks_keep_drop_decision": bool(blockers),
        "manual_confirmed": False,
        "source_urls": row.get("source_urls") or [],
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
    price_review = _price_policy_review(row, risk_summary)
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
        "price_policy_review": price_review,
        "price_policy_blocks_keep_drop": bool(
            price_review.get("blocks_keep_drop_decision")
        ),
        "manual_confirmed_allowed": False,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def _item_template(
    row: dict[str, Any],
    catalog_index: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    template = _copy_template(row)
    sample_rows = _enrich_sample_rows_from_catalog(
        row.get("sample_rows") or [],
        catalog_index or {},
    )
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
        "price_policy_review": _price_policy_review(row, risk_summary),
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


def _campaign_template(
    row: dict[str, Any],
    catalog_index: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    template = _copy_template(row)
    sample_rows = _enrich_sample_rows_from_catalog(
        row.get("sample_rows") or [],
        catalog_index or {},
    )
    risk_summary = _row_risk_summary(sample_rows)
    comparison = row.get("campaign_url_comparison") or {}
    catalog_evidence = _source_url_catalog_evidence_summary(sample_rows)
    review_tags = list(risk_summary["review_risk_tags"])
    if comparison.get("likely_same_campaign_family_reissue"):
        review_tags.append("likely_same_campaign_family_reissue")
    for signal in catalog_evidence.get("reissue_evidence_signals") or []:
        review_tags.append(signal)
    if int(row.get("item_work_order_count") or 0) >= 5:
        review_tags.append("high_impact_campaign_pair")
    risk_summary = {
        **risk_summary,
        "review_risk_tags": review_tags,
    }
    campaign_decision_guidance = _campaign_decision_guidance(row, risk_summary)
    local_recommendation = catalog_evidence.get(
        "recommended_campaign_decision_from_local_evidence"
    )
    if local_recommendation == "campaign_pair_reissue_keep_all_separate":
        campaign_decision_guidance = {
            **campaign_decision_guidance,
            "recommended_first_decision": local_recommendation,
            "local_catalog_evidence_supports_keep_separate": True,
            "local_catalog_evidence_signals": catalog_evidence.get(
                "reissue_evidence_signals"
            )
            or [],
        }
    template = {
        **template,
        "recommended_decision": campaign_decision_guidance.get(
            "recommended_first_decision"
        ),
        "recommended_decision_reason": (
            "local_catalog_evidence_supports_keep_separate"
            if campaign_decision_guidance.get(
                "local_catalog_evidence_supports_keep_separate"
            )
            else "campaign_url_family_requires_manual_reissue_review"
            if comparison.get("likely_same_campaign_family_reissue")
            else "official_campaign_evidence_required"
        ),
        "required_evidence": campaign_decision_guidance.get("required_evidence")
        or [],
        "local_catalog_evidence_signals": catalog_evidence.get(
            "reissue_evidence_signals"
        )
        or [],
        "price_policy_blocks_keep_drop": bool(
            campaign_decision_guidance.get("price_policy_blocks_keep_drop")
        ),
        "manual_review_required_before_mutation": True,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
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
        "catalog_evidence_summary": catalog_evidence,
        "review_risk_summary": risk_summary,
        "price_policy_review": _price_policy_review(row, risk_summary),
        "campaign_decision_guidance": campaign_decision_guidance,
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
                "price_policy_review": item.get("price_policy_review") or {},
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
        "price_policy_review": item.get("price_policy_review") or {},
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
                "catalog_evidence_summary": campaign.get("catalog_evidence_summary") or {},
                "review_risk_tags": (campaign.get("review_risk_summary") or {}).get("review_risk_tags") or [],
                "price_policy_review": campaign.get("price_policy_review") or {},
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


def _campaign_review_readiness(
    campaign_templates: list[dict[str, Any]],
    next_campaign_review_batch: list[dict[str, Any]],
) -> dict[str, Any]:
    batch_ids = {
        row.get("campaign_work_order_id")
        for row in next_campaign_review_batch
        if row.get("campaign_work_order_id")
    }
    batch_templates = [
        campaign
        for campaign in campaign_templates
        if campaign.get("campaign_work_order_id") in batch_ids
    ]
    price_blocked = [
        campaign
        for campaign in batch_templates
        if (campaign.get("price_policy_review") or {}).get("blocks_keep_drop_decision")
    ]
    likely_reissue = [
        campaign
        for campaign in batch_templates
        if (campaign.get("campaign_url_comparison") or {}).get(
            "likely_same_campaign_family_reissue"
        )
    ]
    return {
        "status": "campaign_review_ready_manual_only"
        if next_campaign_review_batch
        else "no_campaign_review_batch",
        "campaign_rows": len(next_campaign_review_batch),
        "item_work_order_rows": sum(
            int(campaign.get("item_work_order_count") or 0)
            for campaign in next_campaign_review_batch
        ),
        "catalog_index_rows": sum(
            int(campaign.get("catalog_index_count") or 0)
            for campaign in next_campaign_review_batch
        ),
        "campaigns_with_evidence_urls": sum(
            1 for campaign in next_campaign_review_batch if campaign.get("first_evidence_url")
        ),
        "campaigns_missing_evidence_urls": sum(
            1 for campaign in next_campaign_review_batch if not campaign.get("first_evidence_url")
        ),
        "likely_same_campaign_family_reissue_rows": len(likely_reissue),
        "price_policy_blocked_campaign_rows": len(price_blocked),
        "non_exception_missing_price_sample_rows": sum(
            int(
                (campaign.get("price_policy_review") or {}).get(
                    "non_exception_missing_price_sample_rows"
                )
                or 0
            )
            for campaign in batch_templates
        ),
        "zero_price_exception_sample_rows": sum(
            int(
                (campaign.get("price_policy_review") or {}).get(
                    "zero_price_exception_sample_rows"
                )
                or 0
            )
            for campaign in batch_templates
        ),
        "first_campaign_evidence_url": _first_url(
            [campaign.get("first_evidence_url") for campaign in next_campaign_review_batch]
        ),
        "recommended_next_action": (
            "review_campaign_pages_first_then_apply_campaign_decision_to_item_previews"
            if next_campaign_review_batch
            else "no_campaign_review_needed"
        ),
        "decision_order": [
            "Open first_evidence_url and every campaign source_url.",
            "Decide whether the campaign pair is a reissue/campaign wave or a duplicate campaign.",
            "If it is a reissue/campaign wave, mark affected item work orders keep-separate.",
            "If it is a duplicate campaign, review each item preview before keep/drop.",
            "Resolve price policy blockers before keep/drop mutation.",
        ],
        "manual_review_required_before_mutation": True,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def _known_price_candidate_for_campaign(campaign: dict[str, Any]) -> dict[str, Any] | None:
    comparison = campaign.get("campaign_url_comparison") or {}
    slugs = {
        str(slug)
        for slug in comparison.get("campaign_slugs") or []
        if isinstance(slug, str)
    }
    if {"onep6", "onep8"} <= slugs:
        return {
            "official_price_candidate_jpy": 500,
            "candidate_status": "secondary_official_evidence_requires_manual_confirmation",
            "candidate_evidence_urls": [
                "https://one-piece.com/figure/o1841/index.html",
                "https://one-piece.com/figure/o1843/index.html",
                "https://one-piece.com/figure/o1845/index.html",
                "https://one-piece.com/figure/o1847/index.html",
                "https://natalie.mu/comic/news/44718",
            ],
            "candidate_evidence_summary": (
                "ONE PIECE official figure pages and Natalie list the March 2011 "
                "Marineford Final Battle campaign price as 1 try / 500 JPY tax included. "
                "Confirm whether the September 2011 onep8 campaign used the same draw price "
                "before importing."
            ),
            "candidate_scope_note": (
                "Candidate covers the March 2011 onep6 campaign directly; onep8 still needs "
                "manual confirmation because the official 1kuji page copy lacks a price line."
            ),
            "candidate_requires_manual_confirmation": True,
        }
    return None


def _price_policy_blocked_campaign_reviews(
    next_campaign_review_batch: list[dict[str, Any]],
    *,
    limit: int = 5,
    sample_limit: int = 6,
) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    for campaign in next_campaign_review_batch:
        price_policy = campaign.get("price_policy_review") or {}
        if not price_policy.get("blocks_keep_drop_decision"):
            continue
        missing_samples: list[dict[str, Any]] = []
        zero_exception_samples: list[dict[str, Any]] = []
        for preview in campaign.get("item_review_preview") or []:
            if not isinstance(preview, dict):
                continue
            preview_price_policy = preview.get("price_policy_review") or {}
            if int(preview_price_policy.get("non_exception_missing_price_sample_rows") or 0):
                missing_samples.append(
                    {
                        "work_order_id": preview.get("work_order_id"),
                        "catalog_indexes": preview.get("catalog_indexes") or [],
                        "prize_rank": preview.get("prize_rank") or "",
                        "prize_item_name": preview.get("prize_item_name") or "",
                        "identity_label": preview.get("identity_label") or "",
                        "first_evidence_url": preview.get("first_evidence_url") or "",
                    }
                )
            if int(preview_price_policy.get("zero_price_exception_sample_rows") or 0):
                zero_exception_samples.append(
                    {
                        "work_order_id": preview.get("work_order_id"),
                        "catalog_indexes": preview.get("catalog_indexes") or [],
                        "prize_rank": preview.get("prize_rank") or "",
                        "prize_item_name": preview.get("prize_item_name") or "",
                        "identity_label": preview.get("identity_label") or "",
                        "expected_official_price_jpy": 0,
                    }
                )
        reviews.append(
            {
                "campaign_work_order_id": campaign.get("campaign_work_order_id"),
                "first_evidence_url": campaign.get("first_evidence_url") or "",
                "source_urls": campaign.get("source_urls") or [],
                "item_work_order_count": int(campaign.get("item_work_order_count") or 0),
                "price_policy_blockers": price_policy.get("blockers") or [],
                "non_exception_missing_price_sample_rows": int(
                    price_policy.get("non_exception_missing_price_sample_rows") or 0
                ),
                "zero_price_exception_sample_rows": int(
                    price_policy.get("zero_price_exception_sample_rows") or 0
                ),
                "last_one_double_chance_expected_price_jpy": int(
                    price_policy.get("last_one_double_chance_expected_price_jpy") or 0
                ),
                "missing_regular_price_samples": missing_samples[:sample_limit],
                "missing_regular_price_patch_samples": missing_samples,
                "missing_regular_price_sample_rows_visible": min(
                    len(missing_samples),
                    sample_limit,
                ),
                "missing_regular_price_sample_rows_hidden": max(
                    0,
                    len(missing_samples) - sample_limit,
                ),
                "zero_price_exception_samples": zero_exception_samples[:sample_limit],
                "manual_resolution_fields": {
                    "official_draw_price_jpy": None,
                    "manual_price_confirmed": False,
                    "manual_price_evidence_url": "",
                    "manual_note": "",
                },
                "official_price_candidate": _known_price_candidate_for_campaign(
                    campaign
                ),
                "unblocks_next_phase": "campaign_reissue_or_duplicate_identity_review",
            }
        )
        if len(reviews) >= limit:
            break
    return reviews


def _source_url_for_known_onep_price_candidate(
    catalog_index: int,
    source_urls: list[Any],
) -> str:
    onep6 = next((str(url) for url in source_urls if str(url).endswith("/onep6")), "")
    onep8 = next((str(url) for url in source_urls if str(url).endswith("/onep8")), "")
    if onep6 and onep8:
        return onep6 if catalog_index >= 16141 else onep8
    return str(source_urls[0]) if source_urls else ""


def _price_candidate_patch_template(
    price_policy_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    for review in price_policy_reviews:
        candidate = review.get("official_price_candidate")
        if not isinstance(candidate, dict):
            continue
        candidate_price = candidate.get("official_price_candidate_jpy")
        if candidate_price is None:
            continue
        evidence_urls = candidate.get("candidate_evidence_urls") or []
        source_urls = review.get("source_urls") or []

        patch_samples = (
            review.get("missing_regular_price_patch_samples")
            or review.get("missing_regular_price_samples")
            or []
        )
        for sample in patch_samples:
            if not isinstance(sample, dict):
                continue
            for catalog_index in sample.get("catalog_indexes") or []:
                source_url = _source_url_for_known_onep_price_candidate(
                    int(catalog_index),
                    source_urls,
                )
                source_slug = source_url.rstrip("/").split("/")[-1]
                direct_evidence = source_slug == "onep6"
                rows.append(
                    {
                        "campaign_work_order_id": review.get(
                            "campaign_work_order_id"
                        ),
                        "work_order_id": sample.get("work_order_id"),
                        "catalog_index": int(catalog_index),
                        "source_url": source_url,
                        "prize_rank": sample.get("prize_rank") or "",
                        "prize_item_name": sample.get("prize_item_name") or "",
                        "identity_label": sample.get("identity_label") or "",
                        "current_official_price_jpy": None,
                        "candidate_official_price_jpy": candidate_price,
                        "candidate_status": candidate.get("candidate_status") or "",
                        "candidate_evidence_urls": evidence_urls,
                        "confirmation_scope": (
                            "secondary_official_evidence_direct_candidate"
                            if direct_evidence
                            else "same_family_reissue_price_candidate_requires_campaign_confirmation"
                        ),
                        "manual_price_confirmed": False,
                        "manual_price_evidence_url": "",
                        "manual_note": "",
                        "auto_apply_enabled": False,
                        "blocked_until": "manual_price_confirmed",
                    }
                )

    direct_rows = sum(
        1
        for row in rows
        if row["confirmation_scope"] == "secondary_official_evidence_direct_candidate"
    )
    same_family_rows = sum(
        1
        for row in rows
        if row["confirmation_scope"]
        == "same_family_reissue_price_candidate_requires_campaign_confirmation"
    )
    return {
        "status": "manual_price_confirmation_required",
        "auto_apply_enabled": False,
        "ready_to_import_rows": 0,
        "template_rows": len(rows),
        "manual_confirmation_required_rows": len(rows),
        "direct_candidate_rows": direct_rows,
        "same_family_requires_confirmation_rows": same_family_rows,
        "rows": rows,
        "import_instructions": [
            "Confirm official_draw_price_jpy on the campaign page before editing catalog rows.",
            "Set manual_price_confirmed=true and manual_price_evidence_url only for rows whose source campaign price is confirmed.",
            "Keep auto_apply_enabled=false until every intended price row has human confirmation.",
        ],
    }


def _blocking_dashboard(
    summary: dict[str, Any],
    *,
    campaign_review_readiness: dict[str, Any],
    next_campaign_review_batch: list[dict[str, Any]],
) -> dict[str, Any]:
    item_rows = int(summary.get("item_template_rows") or 0)
    campaign_rows = int(summary.get("campaign_template_rows") or 0)
    campaign_batch_rows = int(summary.get("campaign_review_batch_rows") or 0)
    price_blocked_campaign_rows = int(
        summary.get("campaign_review_batch_price_policy_blocked_rows") or 0
    )
    missing_regular_price_rows = int(
        summary.get("campaign_review_batch_non_exception_missing_price_sample_rows") or 0
    )
    zero_price_exception_rows = int(
        summary.get("campaign_review_batch_zero_price_exception_sample_rows") or 0
    )
    missing_evidence_campaigns = int(
        campaign_review_readiness.get("campaigns_missing_evidence_urls") or 0
    )
    manual_required = bool(item_rows or campaign_rows)
    first_campaign = next_campaign_review_batch[0] if next_campaign_review_batch else {}
    price_policy_reviews = _price_policy_blocked_campaign_reviews(
        next_campaign_review_batch
    )
    price_candidate_patch_template = _price_candidate_patch_template(
        price_policy_reviews
    )

    if missing_evidence_campaigns:
        status = "campaign_evidence_url_required"
        next_safe_phase = "fill_campaign_evidence_urls_before_reissue_decisions"
    elif price_blocked_campaign_rows:
        status = "campaign_review_ready_price_policy_blocked"
        next_safe_phase = "confirm_campaign_prices_then_review_reissue_identity"
    elif campaign_batch_rows:
        status = "campaign_review_ready_manual_only"
        next_safe_phase = "review_campaign_pages_first_then_apply_campaign_decision"
    else:
        status = "no_reissue_decision_rows"
        next_safe_phase = "no_reissue_decision_needed"

    blocked_until: list[str] = []
    if missing_evidence_campaigns:
        blocked_until.append("official_campaign_evidence_urls_confirmed")
    if price_blocked_campaign_rows:
        blocked_until.append("non_exception_official_prices_confirmed")
    if manual_required:
        blocked_until.append("campaign_reissue_or_duplicate_decisions_manually_confirmed")

    return {
        "status": status,
        "manual_review_required_before_mutation": manual_required,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
        "next_safe_phase": next_safe_phase,
        "blocked_until": blocked_until,
        "campaign_template_rows": campaign_rows,
        "item_template_rows": item_rows,
        "campaign_review_batch_rows": campaign_batch_rows,
        "campaign_review_batch_item_work_order_rows": int(
            summary.get("campaign_review_batch_item_work_order_rows") or 0
        ),
        "campaign_review_batch_visible_item_preview_rows": int(
            summary.get("campaign_review_batch_visible_item_preview_rows") or 0
        ),
        "campaigns_with_evidence_urls": int(
            campaign_review_readiness.get("campaigns_with_evidence_urls") or 0
        ),
        "campaigns_missing_evidence_urls": missing_evidence_campaigns,
        "price_policy_blocked_campaign_rows": price_blocked_campaign_rows,
        "non_exception_missing_price_sample_rows": missing_regular_price_rows,
        "zero_price_exception_sample_rows": zero_price_exception_rows,
        "last_one_double_chance_expected_price_jpy": 0,
        "price_policy_blocked_campaign_reviews": price_policy_reviews,
        "next_price_policy_review": price_policy_reviews[0]
        if price_policy_reviews
        else None,
        "price_candidate_patch_template": price_candidate_patch_template,
        "price_candidate_patch_rows": price_candidate_patch_template["template_rows"],
        "price_candidate_patch_ready_to_import_rows": price_candidate_patch_template[
            "ready_to_import_rows"
        ],
        "first_campaign_review": {
            "campaign_work_order_id": first_campaign.get("campaign_work_order_id"),
            "first_evidence_url": first_campaign.get("first_evidence_url"),
            "item_work_order_count": int(first_campaign.get("item_work_order_count") or 0),
            "visible_item_review_preview_rows": int(
                first_campaign.get("visible_item_review_preview_rows") or 0
            ),
            "price_policy_blocks_keep_drop": bool(
                (first_campaign.get("price_policy_review") or {}).get(
                    "blocks_keep_drop_decision"
                )
            ),
        }
        if first_campaign
        else {},
        "decision_order": campaign_review_readiness.get("decision_order") or [],
        "safety_note": (
            "Review campaign pages first; do not merge or delete rows until official evidence "
            "confirms whether the pair is a true reissue/campaign wave or an exact duplicate."
        ),
    }


def build_report(
    action_queue: dict[str, Any],
    *,
    catalog_index: dict[int, dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    catalog_index = catalog_index or _load_catalog_index()
    item_templates = [
        _item_template(row, catalog_index)
        for row in _safe_list(action_queue.get("ichiban_reissue_work_order"))
    ]
    campaign_templates = [
        _campaign_template(row, catalog_index)
        for row in _safe_list(action_queue.get("ichiban_reissue_campaign_work_order"))
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
    campaign_review_readiness = _campaign_review_readiness(
        campaign_templates,
        next_campaign_review_batch,
    )

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
        "item_template_non_exception_missing_price_sample_rows": sum(
            int(
                (item.get("price_policy_review") or {}).get(
                    "non_exception_missing_price_sample_rows"
                )
                or 0
            )
            for item in item_templates
        ),
        "item_template_zero_price_exception_sample_rows": sum(
            int(
                (item.get("price_policy_review") or {}).get(
                    "zero_price_exception_sample_rows"
                )
                or 0
            )
            for item in item_templates
        ),
        "item_template_price_policy_blocked_rows": sum(
            1
            for item in item_templates
            if (item.get("price_policy_review") or {}).get(
                "blocks_keep_drop_decision"
            )
        ),
        "campaign_template_price_policy_blocked_rows": sum(
            1
            for campaign in campaign_templates
            if (campaign.get("price_policy_review") or {}).get(
                "blocks_keep_drop_decision"
            )
        ),
        "campaign_template_high_impact_rows": sum(
            1
            for campaign in campaign_templates
            if int(campaign.get("item_work_order_count") or 0) >= 5
        ),
        "campaign_template_local_catalog_evidence_rows": sum(
            1
            for campaign in campaign_templates
            if (campaign.get("catalog_evidence_summary") or {}).get(
                "source_url_count"
            )
        ),
        "campaign_template_release_date_differs_by_source_url_rows": sum(
            1
            for campaign in campaign_templates
            if (campaign.get("catalog_evidence_summary") or {}).get(
                "release_date_sets_differ"
            )
        ),
        "campaign_template_image_url_differs_by_source_url_rows": sum(
            1
            for campaign in campaign_templates
            if (campaign.get("catalog_evidence_summary") or {}).get(
                "image_url_sets_differ"
            )
        ),
        "campaign_template_local_keep_separate_recommended_rows": sum(
            1
            for campaign in campaign_templates
            if (campaign.get("catalog_evidence_summary") or {}).get(
                "recommended_campaign_decision_from_local_evidence"
            )
            == "campaign_pair_reissue_keep_all_separate"
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
        "campaign_review_readiness_status": campaign_review_readiness["status"],
        "campaign_review_readiness_price_policy_blocked_campaign_rows": campaign_review_readiness[
            "price_policy_blocked_campaign_rows"
        ],
        "campaign_review_readiness_campaigns_missing_evidence_urls": campaign_review_readiness[
            "campaigns_missing_evidence_urls"
        ],
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
        "campaign_review_batch_non_exception_missing_price_sample_rows": sum(
            int(
                (campaign.get("price_policy_review") or {}).get(
                    "non_exception_missing_price_sample_rows"
                )
                or 0
            )
            for campaign in campaign_templates
            if campaign.get("campaign_work_order_id")
            in {row.get("campaign_work_order_id") for row in next_campaign_review_batch}
        ),
        "campaign_review_batch_price_policy_blocked_rows": sum(
            1
            for campaign in campaign_templates
            if campaign.get("campaign_work_order_id")
            in {row.get("campaign_work_order_id") for row in next_campaign_review_batch}
            and (campaign.get("price_policy_review") or {}).get(
                "blocks_keep_drop_decision"
            )
        ),
        "campaign_review_batch_local_keep_separate_recommended_rows": sum(
            1
            for campaign in next_campaign_review_batch
            if (campaign.get("catalog_evidence_summary") or {}).get(
                "recommended_campaign_decision_from_local_evidence"
            )
            == "campaign_pair_reissue_keep_all_separate"
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
    blocking_dashboard = _blocking_dashboard(
        summary,
        campaign_review_readiness=campaign_review_readiness,
        next_campaign_review_batch=next_campaign_review_batch,
    )

    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "ichiban_kuji_reissue_decision_template",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": summary,
        "blocking_dashboard": blocking_dashboard,
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
        "campaign_review_readiness": campaign_review_readiness,
        "next_campaign_review_batch": next_campaign_review_batch,
        "item_templates": item_templates,
    }


def write_report(report: dict[str, Any], path: Path = DEFAULT_OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PUBLIC)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(
        _load_json(args.input),
        catalog_index=_load_catalog_index(args.catalog),
    )
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
