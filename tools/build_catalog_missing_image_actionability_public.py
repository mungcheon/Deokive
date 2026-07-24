from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_ENRICHMENT = DATA / "catalog_image_enrichment_batches_public.json"
DEFAULT_ACTION_QUEUE = DATA / "catalog_image_attachment_action_queue_public.json"
DEFAULT_SOURCE_DETAIL_QUEUE = DATA / "source_detail_candidate_action_queue_public.json"
DEFAULT_SOURCE_DISCOVERY_FOCUS_PACKS = DATA / "source_discovery_focus_packs_public.json"
DEFAULT_SOURCE_DISCOVERY_FOCUS_TEMPLATE = DATA / "source_discovery_focus_confirmed_template_public.json"
DEFAULT_SOURCE_DISCOVERY_FOCUS_TEMPLATE_DRY_RUN = DATA / "source_discovery_focus_template_import_dry_run_public.json"
DEFAULT_SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES = (
    DATA / "source_discovery_next_focus_detail_candidates_public.json"
)
DEFAULT_SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE = (
    DATA / "source_discovery_next_focus_fallback_queue_public.json"
)
DEFAULT_IMAGE_ATTACHMENT_TEMPLATE = DATA / "catalog_image_attachment_confirmed_template_public.json"
DEFAULT_IMAGE_ATTACHMENT_TEMPLATE_DRY_RUN = DATA / "catalog_image_attachment_template_import_dry_run_public.json"
DEFAULT_OUTPUT = DATA / "catalog_missing_image_actionability_public.json"


WORKFLOW_LABELS = {
    "extract_from_existing_source_url": "이미 확인된 상세 source_url에서 image_url 추출",
    "replace_generic_source_then_extract_image": "일반 상점/목록 URL을 상품 상세 URL로 교체 후 이미지 첨부",
    "review_gotouchi_official_candidates": "고토치 공식 후보가 상품 종류까지 맞는지 검토 후 이미지 첨부",
    "find_source_then_extract_image": "정확한 공식 상품 source_url을 먼저 찾은 뒤 이미지 첨부",
    "manual_image_research": "공식/제조사 경로를 수동 조사",
}

WORKFLOW_NEXT_STEPS = {
    "extract_from_existing_source_url": "extract_product_image_from_existing_exact_source_url",
    "replace_generic_source_then_extract_image": "replace_generic_source_url_then_extract_image",
    "review_gotouchi_official_candidates": "confirm_exact_product_type_then_attach_image",
    "find_source_then_extract_image": "find_exact_official_source_url_then_extract_image",
    "manual_image_research": "manual_official_source_and_image_research",
}

READINESS_ORDER = {
    "image_url_candidate_review": 10,
    "source_url_replacement_required": 20,
    "representative_image_review_required": 25,
    "source_url_discovery_required": 30,
    "manual_research_required": 40,
}


READINESS_BLOCKERS = {
    "image_url_candidate_review": {
        "blocked_until": "manual_image_url_confirmed_from_exact_source",
        "blocked_reason": "candidate_image_requires_manual_review",
        "required_evidence": [
            "exact_product_source_url",
            "image_url_from_accepted_source_or_trusted_official_cdn",
            "same_product_title_character_variant_type_confirmed",
        ],
    },
    "source_detail_candidate_review": {
        "blocked_until": "source_detail_candidate_identity_confirmed",
        "blocked_reason": "source_and_image_candidate_identity_requires_manual_review",
        "required_evidence": [
            "candidate_source_url_exact_product_page",
            "candidate_image_url_matches_same_product",
            "candidate_title_character_variant_type_confirmed",
        ],
    },
    "source_detail_candidate_recheck_required": {
        "blocked_until": "candidate_identity_rechecked_or_replaced",
        "blocked_reason": "candidate_identity_warning_requires_recheck",
        "required_evidence": [
            "candidate_identity_flags_resolved",
            "replacement_candidate_source_url_if_current_candidate_is_wrong",
            "manual_note_explaining_keep_or_reject_decision",
        ],
    },
    "source_detail_candidate_count_review_required": {
        "blocked_until": "large_candidate_set_exact_identity_confirmed",
        "blocked_reason": "large_candidate_set_requires_exact_identity_review",
        "required_evidence": [
            "candidate_count_review_completed",
            "candidate_source_url_exact_product_page",
            "candidate_title_character_variant_type_confirmed",
            "candidate_image_url_matches_same_product",
        ],
    },
    "source_url_replacement_required": {
        "blocked_until": "generic_source_url_replaced_with_exact_product_source",
        "blocked_reason": "generic_or_listing_source_url_cannot_support_image_import",
        "required_evidence": [
            "exact_product_source_url",
            "existing_generic_source_url_replaced_or_preserved_with_reason",
            "image_url_from_exact_source_after_replacement",
        ],
    },
    "representative_image_review_required": {
        "blocked_until": "representative_image_exact_product_type_confirmed",
        "blocked_reason": "representative_image_requires_product_type_review",
        "required_evidence": [
            "official_source_matches_exact_product_type",
            "representative_image_is_not_wrong_variant_or_lineup_only",
            "manual_note_for_representative_image_choice",
        ],
    },
    "source_url_discovery_required": {
        "blocked_until": "exact_product_source_url_discovered",
        "blocked_reason": "missing_exact_source_url",
        "required_evidence": [
            "official_or_trusted_product_detail_source_url",
            "title_character_variant_type_match",
            "image_url_from_confirmed_source_or_trusted_official_cdn",
        ],
    },
    "manual_research_required": {
        "blocked_until": "manual_official_source_and_image_evidence_recorded",
        "blocked_reason": "structured_source_discovery_not_available",
        "required_evidence": [
            "trusted_source_url_or_manual_evidence_url",
            "image_url_source_explained",
            "manual_note_for_nonstandard_source",
        ],
    },
}


def readiness_blocker(readiness: str) -> dict[str, Any]:
    return dict(
        READINESS_BLOCKERS.get(
            readiness,
            {
                "blocked_until": "manual_review_completed",
                "blocked_reason": "manual_review_required",
                "required_evidence": ["manual_confirmation"],
            },
        )
    )


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def counter_rows(counter: Counter[str], field: str, limit: int = 30) -> list[dict[str, Any]]:
    return [{field: key, "rows": value} for key, value in counter.most_common(limit) if key]


def workflow_readiness(workflow: str) -> str:
    if workflow == "extract_from_existing_source_url":
        return "image_url_candidate_review"
    if workflow == "replace_generic_source_then_extract_image":
        return "source_url_replacement_required"
    if workflow == "review_gotouchi_official_candidates":
        return "representative_image_review_required"
    if workflow == "find_source_then_extract_image":
        return "source_url_discovery_required"
    return "manual_research_required"


def compact_sample(group: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "source_store": item.get("source_store") or group.get("source_store"),
        "affiliation": item.get("affiliation"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "official_search_url": item.get("official_search_url"),
    }


def summarize_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_readiness: dict[str, dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        workflow = str(group.get("workflow") or "manual_image_research")
        readiness = workflow_readiness(workflow)
        rows = int(group.get("missing_image_rows") or 0)
        bucket = by_readiness.setdefault(
            readiness,
            {
                "readiness": readiness,
                "rows": 0,
                "workflow_rows": Counter(),
                "source_store_rows": Counter(),
                "sample_items": [],
            },
        )
        bucket["rows"] += rows
        bucket["workflow_rows"][workflow] += rows
        source_store = str(group.get("source_store") or "")
        if source_store:
            bucket["source_store_rows"][source_store] += rows
        for item in group.get("sample_items") or []:
            if isinstance(item, dict) and len(bucket["sample_items"]) < 12:
                sample = compact_sample(group, item)
                sample["workflow"] = workflow
                bucket["sample_items"].append(sample)

    rows_out: list[dict[str, Any]] = []
    for readiness, bucket in by_readiness.items():
        workflow_rows = [
            {
                "workflow": workflow,
                "label": WORKFLOW_LABELS.get(workflow, workflow),
                "rows": count,
                "next_step": WORKFLOW_NEXT_STEPS.get(workflow, "manual_review"),
            }
            for workflow, count in bucket["workflow_rows"].most_common()
        ]
        rows_out.append(
            {
                "readiness": readiness,
                "priority": READINESS_ORDER.get(readiness, 99),
                "rows": bucket["rows"],
                "workflow_rows": workflow_rows,
                "by_source_store": counter_rows(bucket["source_store_rows"], "source_store"),
                "sample_items": bucket["sample_items"],
                "auto_apply_enabled": False,
                **readiness_blocker(readiness),
            }
        )
    return sorted(rows_out, key=lambda row: (int(row["priority"]), str(row["readiness"])))


def summarize_source_stores(groups: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    by_store: dict[str, dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        source_store = str(group.get("source_store") or "").strip()
        if not source_store:
            continue
        workflow = str(group.get("workflow") or "manual_image_research")
        readiness = workflow_readiness(workflow)
        rows = int(group.get("missing_image_rows") or 0)
        bucket = by_store.setdefault(
            source_store,
            {
                "source_store": source_store,
                "missing_image_rows": 0,
                "priority": READINESS_ORDER.get(readiness, 99),
                "readiness_rows": Counter(),
                "workflow_rows": Counter(),
                "sample_items": [],
            },
        )
        bucket["missing_image_rows"] += rows
        bucket["priority"] = min(int(bucket["priority"]), READINESS_ORDER.get(readiness, 99))
        bucket["readiness_rows"][readiness] += rows
        bucket["workflow_rows"][workflow] += rows
        for item in group.get("sample_items") or []:
            if isinstance(item, dict) and len(bucket["sample_items"]) < 8:
                sample = compact_sample(group, item)
                sample["workflow"] = workflow
                sample["readiness"] = readiness
                bucket["sample_items"].append(sample)

    rows_out: list[dict[str, Any]] = []
    for bucket in by_store.values():
        primary_workflow = ""
        if bucket["workflow_rows"]:
            primary_workflow = bucket["workflow_rows"].most_common(1)[0][0]
        rows_out.append(
            {
                "source_store": bucket["source_store"],
                "priority": bucket["priority"],
                "missing_image_rows": bucket["missing_image_rows"],
                "primary_workflow": primary_workflow,
                "recommended_next_step": WORKFLOW_NEXT_STEPS.get(primary_workflow, "manual_review"),
                **readiness_blocker(workflow_readiness(primary_workflow)),
                "readiness_rows": [
                    {"readiness": readiness, "rows": count}
                    for readiness, count in bucket["readiness_rows"].most_common()
                ],
                "workflow_rows": [
                    {
                        "workflow": workflow,
                        "label": WORKFLOW_LABELS.get(workflow, workflow),
                        "rows": count,
                        "next_step": WORKFLOW_NEXT_STEPS.get(workflow, "manual_review"),
                    }
                    for workflow, count in bucket["workflow_rows"].most_common()
                ],
                "sample_items": bucket["sample_items"],
                "auto_apply_enabled": False,
            }
        )
    return sorted(rows_out, key=lambda row: (int(row["priority"]), -int(row["missing_image_rows"]), str(row["source_store"])))[:limit]


def build_source_discovery_work_packs(groups: list[dict[str, Any]], limit: int = 16) -> list[dict[str, Any]]:
    packs: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        if str(group.get("workflow") or "") != "find_source_then_extract_image":
            continue
        source_store = str(group.get("source_store") or "").strip()
        samples = [
            compact_sample(group, item)
            for item in group.get("sample_items") or []
            if isinstance(item, dict)
        ]
        category_counts = Counter(str(item.get("category") or "") for item in samples)
        affiliation_counts = Counter(str(item.get("affiliation") or "") for item in samples)
        packs.append(
            {
                "pack_id": f"missing-image-source-discovery-{len(packs) + 1:03d}",
                "source_store": source_store,
                "row_count": int(group.get("missing_image_rows") or 0),
                "priority": int(group.get("priority") or READINESS_ORDER["source_url_discovery_required"]),
                "official_search_available": bool(group.get("official_search_available")),
                "next_step": "confirm_exact_source_url_then_fill_source_templates",
                "template": "source_discovery_focus_confirmed_template_public.json",
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                "review_checklist": [
                    "Open official_search_url for each sample item.",
                    "Confirm the exact official product detail page, not a search/listing page.",
                    "Fill candidate_source_url/evidence_url only after title, character, variant, and item type match.",
                    "Attach image_url only after exact source_url is confirmed.",
                ],
                **readiness_blocker("source_url_discovery_required"),
                "sample_category_counts": counter_rows(category_counts, "category", limit=8),
                "sample_affiliation_counts": counter_rows(affiliation_counts, "affiliation", limit=8),
                "sample_items": samples[:10],
            }
        )
    packs.sort(key=lambda row: (int(row["priority"]), -int(row["row_count"]), str(row["source_store"])))
    for rank, row in enumerate(packs[:limit], start=1):
        row["rank"] = rank
    return packs[:limit]


def next_focus_pack_from_template_summary(summary: dict[str, Any]) -> dict[str, Any] | None:
    focus_pack_id = summary.get("next_focus_pack_id")
    if not focus_pack_id:
        return None
    return {
        "focus_pack_id": focus_pack_id,
        "source_store": summary.get("next_source_store"),
        "target_category": summary.get("next_target_category"),
        "row_count": summary.get("next_focus_pack_rows") or 0,
        "first_official_search_url": summary.get("next_official_search_url"),
        "focused_pack_report": "data/source_discovery_next_focus_pack_public.json",
        "detail_candidates_report": "data/source_discovery_next_focus_detail_candidates_public.json",
        "confirmed_template": "data/source_discovery_focus_confirmed_template_public.json",
        "import_dry_run_report": "data/source_discovery_next_focus_pack_import_dry_run_public.json",
        "next_step": "review_next_focus_pack_then_fill_confirmed_source_urls",
        "auto_apply_enabled": False,
        **readiness_blocker("source_url_discovery_required"),
    }


def enrich_next_focus_pack(
    next_focus_pack: dict[str, Any] | None,
    detail_candidates: dict[str, Any] | None,
    fallback_queue: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not next_focus_pack:
        return None
    enriched = dict(next_focus_pack)
    detail_summary = (
        detail_candidates.get("summary")
        if isinstance(detail_candidates, dict) and isinstance(detail_candidates.get("summary"), dict)
        else {}
    )
    fallback_summary = (
        fallback_queue.get("summary")
        if isinstance(fallback_queue, dict) and isinstance(fallback_queue.get("summary"), dict)
        else {}
    )
    candidate_items = [
        item
        for item in (detail_candidates or {}).get("items", [])
        if isinstance(item, dict)
    ] if isinstance(detail_candidates, dict) else []
    fallback_items = [
        item for item in (fallback_queue or {}).get("items", []) if isinstance(item, dict)
    ] if isinstance(fallback_queue, dict) else []

    if detail_summary:
        enriched["candidate_review_summary"] = {
            "pack_items": int(detail_summary.get("pack_items") or 0),
            "items_with_candidates": int(detail_summary.get("items_with_candidates") or 0),
            "candidate_rows": int(detail_summary.get("candidate_rows") or 0),
            "manual_candidate_review_rows": int(
                detail_summary.get("manual_candidate_review_rows") or 0
            ),
            "no_candidate_items": int(detail_summary.get("no_candidate_items") or 0),
            "next_action_lane_count": int(
                detail_summary.get("next_action_lane_count") or 0
            ),
            "next_action_lanes": detail_summary.get("next_action_lanes") or [],
            "official_search_has_results": dict(
                detail_summary.get("official_search_audit_status_counts") or []
            ).get("official_search_has_results", 0),
            "official_search_no_results": dict(
                detail_summary.get("official_search_audit_status_counts") or []
            ).get("official_search_no_results", 0),
            "fallback_search_needed_items": sum(
                1 for item in candidate_items if item.get("needs_fallback_web_search")
            ),
        }
    if fallback_summary:
        enriched["fallback_review_summary"] = {
            "queue_rows": int(fallback_summary.get("queue_rows") or 0),
            "fallback_query_count": int(fallback_summary.get("fallback_query_count") or 0),
            "manual_confirmed_rows": int(fallback_summary.get("manual_confirmed_rows") or 0),
            "first_domain_limited_web_search_url": fallback_summary.get(
                "first_domain_limited_web_search_url"
            ),
            "first_fallback_store_search_url": fallback_summary.get(
                "first_fallback_store_search_url"
            ),
        }
    if candidate_items:
        enriched["candidate_review_samples"] = [
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "candidate_count": item.get("candidate_count"),
                "official_search_audit_status": item.get("official_search_audit_status"),
                "needs_fallback_web_search": bool(item.get("needs_fallback_web_search")),
                "status": item.get("status") or item.get("review_state"),
            }
            for item in candidate_items[:8]
        ]
    if fallback_items:
        enriched["fallback_review_samples"] = [
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "domain_limited_web_search_url_count": len(
                    item.get("domain_limited_web_search_urls") or []
                ),
                "fallback_store_search_url": item.get("fallback_store_search_url"),
            }
            for item in fallback_items[:8]
        ]
    if detail_summary or fallback_summary:
        enriched["next_step"] = "review_candidate_and_fallback_summaries_then_fill_confirmed_source_urls"
    return enriched


def build_work_order(
    summary: dict[str, Any],
    readiness_rows: list[dict[str, Any]],
    source_store_priority: list[dict[str, Any]],
    source_discovery_work_packs: list[dict[str, Any]] | None = None,
    next_source_discovery_focus_pack: dict[str, Any] | None = None,
    image_action_review_starts: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    readiness_by_name = {str(row.get("readiness") or ""): row for row in readiness_rows}
    source_discovery_row = readiness_by_name.get("source_url_discovery_required", {})
    source_discovery_rows = int(source_discovery_row.get("rows") or 0)
    focus_source_rows = int(summary.get("source_discovery_remaining_focus_review_rows") or 0)
    source_discovery_work_order_rows = focus_source_rows or source_discovery_rows
    top_generic_source_stores = [
        {
            "source_store": row.get("source_store"),
            "missing_image_rows": row.get("missing_image_rows"),
            "primary_workflow": row.get("primary_workflow"),
            "recommended_next_step": row.get("recommended_next_step"),
        }
        for row in source_store_priority
        if str(row.get("primary_workflow") or "")
        == "replace_generic_source_then_extract_image"
    ][:8]
    top_source_discovery_stores = [
        {
            "source_store": row.get("source_store"),
            "missing_image_rows": row.get("missing_image_rows"),
            "primary_workflow": row.get("primary_workflow"),
            "recommended_next_step": row.get("recommended_next_step"),
        }
        for row in source_store_priority
        if str(row.get("primary_workflow") or "") == "find_source_then_extract_image"
    ][:8]

    rows: list[dict[str, Any]] = []

    def add(
        *,
        rank: int,
        lane: str,
        source: str,
        row_count: int,
        next_step: str,
        template: str,
        notes: list[str] | None = None,
        top_stores: list[dict[str, Any]] | None = None,
        top_work_packs: list[dict[str, Any]] | None = None,
        current_focus_pack: dict[str, Any] | None = None,
        review_start: dict[str, Any] | None = None,
        blocked_until: str | None = None,
        blocked_reason: str | None = None,
        required_evidence: list[str] | None = None,
    ) -> None:
        if row_count <= 0:
            return
        rows.append(
            {
                "rank": rank,
                "lane": lane,
                "source": source,
                "row_count": row_count,
                "next_step": next_step,
                "template": template,
                "top_source_stores": top_stores or [],
                "top_work_packs": top_work_packs or [],
                "current_focus_pack": current_focus_pack or {},
                "review_start": review_start or {},
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                "blocked_until": blocked_until or "manual_confirmation_completed",
                "blocked_reason": blocked_reason or "manual_review_required",
                "required_evidence": required_evidence or ["manual_confirmation"],
                "notes": notes or [],
            }
        )

    add(
        rank=1,
        lane="confirm_source_detail_candidates",
        source="source_detail_candidate_action_queue_public.json",
        row_count=int(summary.get("source_detail_candidate_review_rows") or 0),
        next_step="confirm_exact_identity_then_import_source_and_image",
        template="source_detail_candidate_confirmed_rows_public.json",
        **readiness_blocker("source_detail_candidate_review"),
        notes=["Use only exact product detail candidates; recheck title/variant before import."],
    )
    add(
        rank=2,
        lane="review_large_source_detail_candidate_sets",
        source="source_detail_candidate_action_queue_public.json",
        row_count=int(summary.get("source_detail_candidate_count_review_required_rows") or 0),
        next_step="confirm_large_candidate_set_exact_identity_before_import",
        template="source_detail_candidate_confirmed_rows_public.json",
        **readiness_blocker("source_detail_candidate_count_review_required"),
        notes=[
            "These rows have a high-scoring candidate, but the source search returned many candidates.",
            "Do not import until the exact product detail page and image are confirmed.",
        ],
    )
    add(
        rank=3,
        lane="replace_generic_source_urls",
        source="catalog_image_attachment_action_queue_public.json",
        row_count=int(summary.get("image_attachment_template_source_update_required_rows") or 0),
        next_step="replace_generic_source_url_then_extract_image",
        template="catalog_image_attachment_confirmed_template_public.json",
        top_stores=top_generic_source_stores,
        review_start=(image_action_review_starts or {}).get(
            "replace_generic_source_then_extract_image"
        ),
        **readiness_blocker("source_url_replacement_required"),
        notes=["Rows already have generic storefront URLs; replace with exact product URLs first."],
    )
    add(
        rank=4,
        lane="discover_exact_source_urls",
        source="source_discovery_action_queue_public.json",
        row_count=source_discovery_work_order_rows,
        next_step="confirm_exact_source_url_then_fill_source_templates",
        template="source_discovery_focus_confirmed_template_public.json",
        top_stores=top_source_discovery_stores,
        top_work_packs=(source_discovery_work_packs or [])[:8],
        current_focus_pack=next_source_discovery_focus_pack,
        **readiness_blocker("source_url_discovery_required"),
        notes=[
            "Focus packs cover the highest-volume official-store gaps before broad manual research.",
            "Use current_focus_pack for the next concrete source discovery batch.",
            "If no focus pack is active yet, this lane falls back to every source_url_discovery_required missing-image row.",
        ],
    )
    add(
        rank=5,
        lane="review_representative_images",
        source="catalog_image_attachment_action_queue_public.json",
        row_count=int(summary.get("image_attachment_template_representative_review_rows") or 0),
        next_step="confirm_exact_product_type_then_attach_image",
        template="catalog_image_attachment_confirmed_template_public.json",
        review_start=(image_action_review_starts or {}).get(
            "review_gotouchi_official_candidates"
        ),
        **readiness_blocker("representative_image_review_required"),
        notes=["Representative images are allowed only when the official source matches the exact product type."],
    )
    add(
        rank=6,
        lane="recheck_source_detail_candidates",
        source="source_detail_candidate_action_queue_public.json",
        row_count=int(summary.get("source_detail_candidate_recheck_required_rows") or 0),
        next_step="refresh_or_replace_candidate_before_import",
        template="source_detail_candidate_confirmed_rows_public.json",
        **readiness_blocker("source_detail_candidate_recheck_required"),
        notes=["Do not import candidates with identity warning flags until the candidate is refreshed or replaced."],
    )
    manual_row = readiness_by_name.get("manual_research_required", {})
    add(
        rank=7,
        lane="manual_image_research",
        source="catalog_image_enrichment_batches_public.json",
        row_count=int(manual_row.get("rows") or summary.get("manual_image_research_rows") or 0),
        next_step="manual_official_source_and_image_research",
        template="manual_image_source_discovery_public.json",
        **readiness_blocker("manual_research_required"),
        notes=["Use this after structured source discovery lanes are exhausted."],
    )
    return rows


def build_completion_plan(
    summary: dict[str, Any],
    source_store_priority: list[dict[str, Any]],
    source_discovery_work_packs: list[dict[str, Any]] | None = None,
    next_source_discovery_focus_pack: dict[str, Any] | None = None,
    image_action_review_starts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    generic_source_rows = int(summary.get("image_attachment_template_source_update_required_rows") or 0)
    representative_rows = int(summary.get("image_attachment_template_representative_review_rows") or 0)
    source_first_rows = int(summary.get("source_first_rows") or 0)
    source_discovery_rows = max(source_first_rows - generic_source_rows, 0)
    focus_rows = int(summary.get("source_discovery_remaining_focus_review_rows") or 0)
    non_focus_rows = int(summary.get("source_discovery_non_focus_rows") or 0)
    if focus_rows + non_focus_rows != source_discovery_rows:
        non_focus_rows = max(source_discovery_rows - focus_rows, 0)
    manual_rows = int(summary.get("manual_image_research_rows") or 0)

    phases: list[dict[str, Any]] = []

    def add_phase(
        *,
        phase_id: str,
        title: str,
        row_count: int,
        source: str,
        next_step: str,
        template: str,
        blocker: str,
        notes: list[str] | None = None,
        top_source_stores: list[dict[str, Any]] | None = None,
        work_packs: list[dict[str, Any]] | None = None,
        current_batch: dict[str, Any] | None = None,
        review_start: dict[str, Any] | None = None,
    ) -> None:
        if row_count <= 0:
            return
        phases.append(
            {
                "rank": len(phases) + 1,
                "phase_id": phase_id,
                "title": title,
                "row_count": row_count,
                "source": source,
                "next_step": next_step,
                "template": template,
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                **readiness_blocker(blocker),
                "top_source_stores": top_source_stores or [],
                "work_packs": work_packs or [],
                "current_batch": current_batch or {},
                "review_start": review_start or {},
                "notes": notes or [],
            }
        )

    generic_stores = [
        {
            "source_store": row.get("source_store"),
            "missing_image_rows": row.get("missing_image_rows"),
            "recommended_next_step": row.get("recommended_next_step"),
        }
        for row in source_store_priority
        if str(row.get("primary_workflow") or "") == "replace_generic_source_then_extract_image"
    ][:8]
    discovery_stores = [
        {
            "source_store": row.get("source_store"),
            "missing_image_rows": row.get("missing_image_rows"),
            "recommended_next_step": row.get("recommended_next_step"),
        }
        for row in source_store_priority
        if str(row.get("primary_workflow") or "") == "find_source_then_extract_image"
    ][:10]

    add_phase(
        phase_id="replace_generic_source_urls",
        title="일반/목록 source_url을 정확한 상품 상세 URL로 교체",
        row_count=generic_source_rows,
        source="catalog_image_attachment_action_queue_public.json",
        next_step="replace_generic_source_url_then_extract_image",
        template="catalog_image_attachment_confirmed_template_public.json",
        blocker="source_url_replacement_required",
        top_source_stores=generic_stores,
        review_start=(image_action_review_starts or {}).get(
            "replace_generic_source_then_extract_image"
        ),
        notes=[
            "These rows already have a source_url, but it is a listing or generic storefront URL.",
            "Confirm the exact product detail page before attaching an image.",
        ],
    )
    add_phase(
        phase_id="review_representative_images",
        title="대표 이미지 후보가 정확한 상품 타입인지 확인",
        row_count=representative_rows,
        source="catalog_image_attachment_action_queue_public.json",
        next_step="confirm_exact_product_type_then_attach_image",
        template="catalog_image_attachment_confirmed_template_public.json",
        blocker="representative_image_review_required",
        review_start=(image_action_review_starts or {}).get(
            "review_gotouchi_official_candidates"
        ),
        notes=[
            "Do not use lineup or wrong-variant images as if they were exact product photos.",
        ],
    )
    add_phase(
        phase_id="complete_source_discovery_focus_packs",
        title="상위 스토어 source_url 발견 팩 처리",
        row_count=focus_rows,
        source="source_discovery_focus_packs_public.json",
        next_step="fill_source_discovery_focus_confirmed_template",
        template="source_discovery_focus_confirmed_template_public.json",
        blocker="source_url_discovery_required",
        top_source_stores=discovery_stores,
        work_packs=(source_discovery_work_packs or [])[:8],
        current_batch=next_source_discovery_focus_pack,
        notes=[
            "The current_batch is the next concrete 20-row pack to review.",
            "Rows stay dry-run safe until the public confirmation template is manually filled.",
        ],
    )
    add_phase(
        phase_id="triage_remaining_source_discovery_backlog",
        title="포커스 팩 밖 source_url 누락 항목 정리",
        row_count=non_focus_rows,
        source="source_discovery_action_queue_public.json",
        next_step="promote_next_store_groups_into_focus_packs",
        template="source_discovery_focus_confirmed_template_public.json",
        blocker="source_url_discovery_required",
        top_source_stores=discovery_stores[10:],
        notes=[
            "These rows are outside the current focus-pack coverage and should be rotated into later packs.",
        ],
    )
    add_phase(
        phase_id="manual_nonstandard_image_research",
        title="구조화 소스가 없는 항목 수동 조사",
        row_count=manual_rows,
        source="catalog_image_enrichment_batches_public.json",
        next_step="manual_official_source_and_image_evidence_recorded",
        template="manual_image_source_discovery_public.json",
        blocker="manual_research_required",
        notes=[
            "Use trusted official/manufacturer evidence and record why the source is acceptable.",
        ],
    )

    phase_total = sum(int(phase.get("row_count") or 0) for phase in phases)
    missing_image_rows = int(summary.get("missing_image_rows") or phase_total)
    return {
        "total_open_rows": missing_image_rows,
        "phase_rows_total": phase_total,
        "phase_count": len(phases),
        "status": "balanced" if phase_total == missing_image_rows else "needs_review",
        "phases": phases,
        "current_focus_pack": next_source_discovery_focus_pack or {},
        "overlay_review_flags": {
            "source_detail_candidate_recheck_required_rows": int(
                summary.get("source_detail_candidate_recheck_required_rows") or 0
            ),
            "source_detail_identity_warning_rows": int(
                summary.get("source_detail_identity_warning_rows") or 0
            ),
            "note": "Overlay rows may overlap with source discovery work and are not added to phase_rows_total.",
        },
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_manual_confirmation": True,
        },
    }


def build_manual_validation_focus(
    summary: dict[str, Any],
    work_order: list[dict[str, Any]],
) -> dict[str, Any]:
    auto_import_ready_rows = int(summary.get("image_attachment_template_dry_run_updated_rows") or 0) + int(
        summary.get("source_detail_ready_unflagged_candidate_rows") or 0
    )
    focus_lanes = [
        {
            "rank": row.get("rank"),
            "lane": row.get("lane"),
            "row_count": row.get("row_count"),
            "source": row.get("source"),
            "next_step": row.get("next_step"),
            "blocked_reason": row.get("blocked_reason"),
            "blocked_until": row.get("blocked_until"),
            "required_evidence": row.get("required_evidence") or [],
            "top_source_stores": row.get("top_source_stores") or [],
                "current_focus_pack": row.get("current_focus_pack") or {},
                "review_start": row.get("review_start") or {},
            }
        for row in sorted(
            work_order,
            key=lambda item: (int(item.get("rank") or 999), str(item.get("lane") or "")),
        )
        if int(row.get("row_count") or 0) > 0
    ][:5]
    return {
        "auto_import_ready_rows": auto_import_ready_rows,
        "manual_validation_required_rows": int(summary.get("missing_image_rows") or 0),
        "next_focus_lane": focus_lanes[0].get("lane") if focus_lanes else None,
        "next_focus_row_count": focus_lanes[0].get("row_count") if focus_lanes else 0,
        "next_focus_source": focus_lanes[0].get("source") if focus_lanes else None,
        "focus_lanes": focus_lanes,
        "blocked_summary": {
            "generic_source_url_replacement_rows": int(
                summary.get("image_attachment_template_source_update_required_rows") or 0
            ),
            "representative_image_review_rows": int(
                summary.get("image_attachment_template_representative_review_rows") or 0
            ),
            "source_detail_recheck_required_rows": int(
                summary.get("source_detail_candidate_recheck_required_rows") or 0
            ),
            "source_discovery_focus_rows": int(
                summary.get("source_discovery_remaining_focus_review_rows") or 0
            ),
            "manual_image_research_rows": int(summary.get("manual_image_research_rows") or 0),
        },
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "reason": (
                "No image row is ready until exact product identity and source/image "
                "evidence are manually confirmed."
            ),
        },
    }


def build_execution_queue_summary(
    summary: dict[str, Any],
    work_order: list[dict[str, Any]],
    completion_plan: dict[str, Any],
) -> dict[str, Any]:
    queues = []
    for row in sorted(
        work_order,
        key=lambda item: (int(item.get("rank") or 999), str(item.get("lane") or "")),
    ):
        row_count = int(row.get("row_count") or 0)
        if row_count <= 0:
            continue
        queues.append(
            {
                "rank": row.get("rank"),
                "lane": row.get("lane"),
                "row_count": row_count,
                "source": row.get("source"),
                "template": row.get("template"),
                "next_step": row.get("next_step"),
                "blocked_until": row.get("blocked_until"),
                "blocked_reason": row.get("blocked_reason"),
                "manual_confirmation_required": bool(row.get("manual_confirmation_required", True)),
                "auto_apply_enabled": bool(row.get("auto_apply_enabled", False)),
                "required_evidence": row.get("required_evidence") or [],
                "review_start": row.get("review_start") or {},
            }
        )

    open_missing_image_rows = int(summary.get("missing_image_rows") or 0)
    queued_rows_total = sum(int(queue.get("row_count") or 0) for queue in queues)
    phase_queue_breakdown = build_phase_queue_breakdown(completion_plan, queues)
    unqueued_phase_rows_total = sum(
        int(row.get("remaining_rows") or 0) for row in phase_queue_breakdown
    )
    phase_linked_lanes = {
        str(row.get("direct_queue_lane") or "")
        for row in phase_queue_breakdown
        if row.get("direct_queue_lane")
    }
    overlay_queue_rows = sum(
        int(queue.get("row_count") or 0)
        for queue in queues
        if str(queue.get("lane") or "") not in phase_linked_lanes
    )
    not_yet_queued_rows = max(0, open_missing_image_rows - queued_rows_total)
    unqueued_rows_breakdown = [
        {
            "bucket": "later_source_discovery_backlog",
            "phase_id": row.get("phase_id"),
            "phase_row_count": row.get("row_count"),
            "direct_queue_lane": row.get("direct_queue_lane"),
            "directly_queued_rows": row.get("queued_rows"),
            "remaining_phase_rows": row.get("remaining_rows"),
            "offset_by_overlay_queue_rows": overlay_queue_rows,
            "reported_not_yet_queued_rows": max(
                0, int(row.get("remaining_rows") or 0) - overlay_queue_rows
            ),
            "next_step": row.get("next_step"),
            "blocked_reason": row.get("blocked_reason"),
            "explanation": (
                "These rows are outside the current focused source-discovery "
                "pack. Overlay candidate recheck queues may cover some of the "
                "same catalog rows, so the displayed not_yet_queued_rows is "
                "remaining_phase_rows minus overlay_queue_rows."
            ),
        }
        for row in phase_queue_breakdown
        if str(row.get("phase_id") or "") == "triage_remaining_source_discovery_backlog"
        and int(row.get("remaining_rows") or 0) > 0
    ]
    next_queue = queues[0] if queues else {}
    return {
        "open_missing_image_rows": open_missing_image_rows,
        "auto_import_ready_rows": int(summary.get("image_attachment_template_dry_run_updated_rows") or 0)
        + int(summary.get("source_detail_ready_unflagged_candidate_rows") or 0),
        "queue_count": len(queues),
        "queued_rows_total": queued_rows_total,
        "not_yet_queued_rows": not_yet_queued_rows,
        "not_yet_queued_rows_explained": sum(
            int(row.get("reported_not_yet_queued_rows") or 0)
            for row in unqueued_rows_breakdown
        ),
        "unqueued_phase_rows_total": unqueued_phase_rows_total,
        "overlay_queue_rows": overlay_queue_rows,
        "completion_plan_status": completion_plan.get("status"),
        "next_queue": next_queue,
        "queues": queues,
        "phase_queue_breakdown": phase_queue_breakdown,
        "unqueued_rows_breakdown": unqueued_rows_breakdown,
        "operator_note": (
            "Work queues are dry-run safe. Fill the listed confirmation template only "
            "after exact product identity, source URL, and image evidence are verified."
        ),
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "manual_confirmation_required": True,
            "reason": "Every open image row still needs source/product/image identity evidence.",
        },
    }


def build_blocking_dashboard(
    summary: dict[str, Any],
    manual_validation_focus: dict[str, Any],
    execution_queue_summary: dict[str, Any],
    completion_plan: dict[str, Any],
) -> dict[str, Any]:
    blocked_reasons = [
        row
        for row in summary.get("by_blocked_reason") or []
        if isinstance(row, dict) and int(row.get("rows") or 0) > 0
    ]
    blocked_until = [
        row
        for row in summary.get("by_blocked_until") or []
        if isinstance(row, dict) and int(row.get("rows") or 0) > 0
    ]
    phases = [
        phase
        for phase in completion_plan.get("phases") or []
        if isinstance(phase, dict) and int(phase.get("row_count") or 0) > 0
    ]
    next_queue = execution_queue_summary.get("next_queue") or {}
    next_phase = phases[0] if phases else {}
    total_open_rows = int(summary.get("missing_image_rows") or 0)
    auto_import_ready_rows = int(
        execution_queue_summary.get("auto_import_ready_rows") or 0
    )
    manual_validation_required_rows = int(
        manual_validation_focus.get("manual_validation_required_rows") or 0
    )
    queued_rows_total = int(execution_queue_summary.get("queued_rows_total") or 0)
    not_yet_queued_rows = int(execution_queue_summary.get("not_yet_queued_rows") or 0)
    progress_blocked = manual_validation_required_rows > auto_import_ready_rows

    return {
        "status": "manual_evidence_required" if progress_blocked else "ready_for_import_review",
        "total_open_rows": total_open_rows,
        "auto_import_ready_rows": auto_import_ready_rows,
        "manual_validation_required_rows": manual_validation_required_rows,
        "queued_rows_total": queued_rows_total,
        "not_yet_queued_rows": not_yet_queued_rows,
        "queue_coverage": round(queued_rows_total / total_open_rows, 4)
        if total_open_rows
        else 1.0,
        "top_blocked_reason": blocked_reasons[0] if blocked_reasons else {},
        "top_blocked_until": blocked_until[0] if blocked_until else {},
        "next_queue": {
            "lane": next_queue.get("lane"),
            "row_count": next_queue.get("row_count") or 0,
            "source": next_queue.get("source"),
            "template": next_queue.get("template"),
            "next_step": next_queue.get("next_step"),
            "blocked_reason": next_queue.get("blocked_reason"),
            "blocked_until": next_queue.get("blocked_until"),
            "manual_confirmation_required": bool(
                next_queue.get("manual_confirmation_required", True)
            ),
            "auto_apply_enabled": bool(next_queue.get("auto_apply_enabled", False)),
        },
        "next_phase": {
            "phase_id": next_phase.get("phase_id"),
            "row_count": next_phase.get("row_count") or 0,
            "source": next_phase.get("source"),
            "template": next_phase.get("template"),
            "next_step": next_phase.get("next_step"),
            "blocked_reason": next_phase.get("blocked_reason"),
            "blocked_until": next_phase.get("blocked_until"),
        },
        "phase_status": completion_plan.get("status"),
        "phase_count": completion_plan.get("phase_count") or 0,
        "top_phase_rows": [
            {
                "phase_id": phase.get("phase_id"),
                "row_count": phase.get("row_count") or 0,
                "blocked_reason": phase.get("blocked_reason"),
                "next_step": phase.get("next_step"),
            }
            for phase in phases[:5]
        ],
        "manual_only": True,
        "auto_apply_enabled": False,
        "operator_message": (
            "No missing-image DB row can be imported automatically yet; fill the "
            "next confirmation template with exact product source/image evidence first."
            if progress_blocked
            else "Confirmed rows are available for import review."
        ),
    }


def build_phase_queue_breakdown(
    completion_plan: dict[str, Any],
    queues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    phase_to_lane = {
        "replace_generic_source_urls": "replace_generic_source_urls",
        "review_representative_images": "review_representative_images",
        "complete_source_discovery_focus_packs": "discover_exact_source_urls",
        "manual_nonstandard_image_research": "manual_image_research",
    }
    queue_rows_by_lane = {
        str(queue.get("lane") or ""): int(queue.get("row_count") or 0)
        for queue in queues
    }
    rows: list[dict[str, Any]] = []
    for phase in completion_plan.get("phases") or []:
        if not isinstance(phase, dict):
            continue
        phase_id = str(phase.get("phase_id") or "")
        lane = phase_to_lane.get(phase_id)
        row_count = int(phase.get("row_count") or 0)
        queued_rows = queue_rows_by_lane.get(lane or "", 0)
        rows.append(
            {
                "phase_id": phase_id,
                "row_count": row_count,
                "direct_queue_lane": lane,
                "queued_rows": min(row_count, queued_rows),
                "remaining_rows": max(0, row_count - queued_rows),
                "next_step": phase.get("next_step"),
                "blocked_reason": phase.get("blocked_reason"),
                "source": phase.get("source"),
                "template": phase.get("template"),
            }
        )
    return rows


def source_detail_items(source_detail_queue: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(source_detail_queue, dict):
        return []
    items: list[dict[str, Any]] = []
    for batch in source_detail_queue.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        for item in batch.get("items") or []:
            if isinstance(item, dict):
                items.append(item)
    return items


def source_detail_missing_items(source_detail_queue: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        item
        for item in source_detail_items(source_detail_queue)
        if item.get("current_catalog_state", {}).get("catalog_has_display_image") is False
    ]


def append_source_detail_readiness(
    readiness_rows: list[dict[str, Any]],
    source_detail_missing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ready_actions = {
        "confirm_exact_identity_before_source_or_image_patch",
        "priority_manual_confirm_source_and_image_patch",
        "priority_manual_review_safe_source_image_candidate",
    }
    ready_items = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") in ready_actions
    ]
    count_review_items = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") == "review_large_candidate_set_before_source_or_image_patch"
    ]
    recheck_items = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") == "recheck_candidate_identity_before_source_or_image_patch"
    ]
    if not ready_items and not count_review_items and not recheck_items:
        return readiness_rows
    ready_samples = [
        {
            "catalog_index": item.get("catalog_index"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "source_store": item.get("source_store"),
            "candidate_source_url": item.get("candidate_source_url"),
            "candidate_image_url": item.get("candidate_image_url"),
            "review_risk": item.get("review_risk"),
            "candidate_identity_flags": item.get("candidate_identity_flags") or [],
            "workflow": "confirm_source_detail_candidate_then_attach_image",
        }
        for item in ready_items[:12]
    ]
    out = list(readiness_rows)
    if ready_items:
        out.append(
            {
                "readiness": "source_detail_candidate_review",
                "priority": READINESS_ORDER["image_url_candidate_review"] + 1,
                "rows": len(ready_items),
                "workflow_rows": [
                    {
                        "workflow": "confirm_source_detail_candidate_then_attach_image",
                        "label": "정확한 상품 상세 후보를 확인한 뒤 source_url/image_url 첨부",
                        "rows": len(ready_items),
                        "next_step": "manual_confirm_then_import_source_and_image_templates",
                    }
                ],
                "by_source_store": counter_rows(Counter(str(item.get("source_store") or "") for item in ready_items), "source_store"),
                "sample_items": ready_samples,
                "auto_apply_enabled": False,
                **readiness_blocker("source_detail_candidate_review"),
            }
        )
    if count_review_items:
        out.append(
            {
                "readiness": "source_detail_candidate_count_review_required",
                "priority": READINESS_ORDER["source_url_discovery_required"] - 2,
                "rows": len(count_review_items),
                "workflow_rows": [
                    {
                        "workflow": "review_large_candidate_set_before_source_or_image_patch",
                        "label": "Review high-scoring candidates that came from a large result set",
                        "rows": len(count_review_items),
                        "next_step": "confirm_large_candidate_set_exact_identity_before_import",
                    }
                ],
                "by_source_store": counter_rows(
                    Counter(str(item.get("source_store") or "") for item in count_review_items),
                    "source_store",
                ),
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "source_store": item.get("source_store"),
                        "candidate_title": item.get("candidate_title"),
                        "candidate_source_url": item.get("candidate_source_url"),
                        "candidate_count": item.get("candidate_count"),
                        "candidate_count_bucket": item.get("candidate_count_bucket"),
                        "candidate_count_review_required": item.get("candidate_count_review_required"),
                        "workflow": "review_large_candidate_set_before_source_or_image_patch",
                    }
                    for item in count_review_items[:12]
                ],
                "auto_apply_enabled": False,
                **readiness_blocker("source_detail_candidate_count_review_required"),
            }
        )
    if recheck_items:
        out.append(
            {
                "readiness": "source_detail_candidate_recheck_required",
                "priority": READINESS_ORDER["source_url_discovery_required"] - 1,
                "rows": len(recheck_items),
                "workflow_rows": [
                    {
                        "workflow": "recheck_source_detail_candidate_identity",
                        "label": "후보 제목의 작품/캐릭터/변형 불일치 가능성 재확인",
                        "rows": len(recheck_items),
                        "next_step": "refresh_or_replace_candidate_before_import",
                    }
                ],
                "by_source_store": counter_rows(Counter(str(item.get("source_store") or "") for item in recheck_items), "source_store"),
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "source_store": item.get("source_store"),
                        "candidate_title": item.get("candidate_title"),
                        "candidate_source_url": item.get("candidate_source_url"),
                        "candidate_identity_flags": item.get("candidate_identity_flags") or [],
                        "workflow": "recheck_source_detail_candidate_identity",
                    }
                    for item in recheck_items[:12]
                ],
                "auto_apply_enabled": False,
                **readiness_blocker("source_detail_candidate_recheck_required"),
            }
        )
    return sorted(out, key=lambda row: (int(row["priority"]), str(row["readiness"])))


def build_image_action_review_starts(action_queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    starts: dict[str, dict[str, Any]] = {}
    for batch in action_queue.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        workflow = str(batch.get("workflow") or "")
        if not workflow or workflow in starts:
            continue
        first_url = str(batch.get("first_primary_review_url") or "").strip()
        first_kind = str(batch.get("first_primary_review_url_kind") or "").strip()
        sample_items = [
            item
            for item in batch.get("items") or []
            if isinstance(item, dict) and item.get("primary_review_url")
        ]
        starts[workflow] = {
            "workflow": workflow,
            "batch_id": batch.get("batch_id"),
            "source_store": batch.get("source_store"),
            "row_count": int(batch.get("row_count") or 0),
            "primary_review_url_rows": int(batch.get("primary_review_url_rows") or 0),
            "first_primary_review_url": first_url,
            "first_primary_review_url_kind": first_kind or "manual_lookup_required",
            "sample_items_with_primary_review_url": len(sample_items),
            "sample_primary_review_items": [
                {
                    "catalog_index": item.get("catalog_index"),
                    "name_ko": item.get("name_ko"),
                    "name_ja": item.get("name_ja"),
                    "primary_review_url": item.get("primary_review_url"),
                    "primary_review_url_kind": item.get("primary_review_url_kind"),
                }
                for item in sample_items[:5]
            ],
        }
    return starts


def build_report(
    enrichment: dict[str, Any],
    action_queue: dict[str, Any],
    source_detail_queue: dict[str, Any] | None = None,
    source_discovery_focus_packs: dict[str, Any] | None = None,
    source_discovery_focus_template: dict[str, Any] | None = None,
    source_discovery_focus_template_dry_run: dict[str, Any] | None = None,
    image_attachment_template: dict[str, Any] | None = None,
    image_attachment_template_dry_run: dict[str, Any] | None = None,
    source_discovery_next_focus_detail_candidates: dict[str, Any] | None = None,
    source_discovery_next_focus_fallback_queue: dict[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    summary = enrichment.get("summary") if isinstance(enrichment.get("summary"), dict) else {}
    action_summary = action_queue.get("summary") if isinstance(action_queue.get("summary"), dict) else {}
    focus_summary = (
        source_discovery_focus_packs.get("summary")
        if isinstance(source_discovery_focus_packs, dict)
        and isinstance(source_discovery_focus_packs.get("summary"), dict)
        else {}
    )
    focus_template_summary = (
        source_discovery_focus_template.get("summary")
        if isinstance(source_discovery_focus_template, dict)
        and isinstance(source_discovery_focus_template.get("summary"), dict)
        else {}
    )
    focus_template_dry_run_summary = (
        source_discovery_focus_template_dry_run
        if isinstance(source_discovery_focus_template_dry_run, dict)
        else {}
    )
    image_attachment_template_summary = (
        image_attachment_template.get("summary")
        if isinstance(image_attachment_template, dict)
        and isinstance(image_attachment_template.get("summary"), dict)
        else {}
    )
    image_attachment_template_dry_run_summary = (
        image_attachment_template_dry_run
        if isinstance(image_attachment_template_dry_run, dict)
        else {}
    )
    groups = [group for group in enrichment.get("groups", []) if isinstance(group, dict)]
    source_detail_missing = source_detail_missing_items(source_detail_queue)
    source_detail_ready = [
        item
        for item in source_detail_missing
        if item.get("recommended_action")
        in {
            "confirm_exact_identity_before_source_or_image_patch",
            "priority_manual_confirm_source_and_image_patch",
            "priority_manual_review_safe_source_image_candidate",
        }
    ]
    source_detail_recheck = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") == "recheck_candidate_identity_before_source_or_image_patch"
    ]
    base_readiness_rows = summarize_groups(groups)
    readiness_rows = append_source_detail_readiness(base_readiness_rows, source_detail_missing)
    source_store_priority = summarize_source_stores(groups)
    source_discovery_work_packs = build_source_discovery_work_packs(groups)
    image_action_review_starts = build_image_action_review_starts(action_queue)
    next_source_discovery_focus_pack = enrich_next_focus_pack(
        next_focus_pack_from_template_summary(focus_template_summary),
        source_discovery_next_focus_detail_candidates,
        source_discovery_next_focus_fallback_queue,
    )
    readiness_total = sum(int(row.get("rows") or 0) for row in base_readiness_rows)
    missing_image_rows = int(summary.get("missing_image_rows") or readiness_total)
    blocked_reason_counts = Counter(
        str(row.get("blocked_reason") or "manual_review_required")
        for row in readiness_rows
        for _ in range(int(row.get("rows") or 0))
    )
    blocked_until_counts = Counter(
        str(row.get("blocked_until") or "manual_confirmation_completed")
        for row in readiness_rows
        for _ in range(int(row.get("rows") or 0))
    )

    immediate_rows = sum(
        count
        for workflow, count in summary.get("by_workflow", [])
        if workflow == "extract_from_existing_source_url"
    )
    source_first_rows = sum(
        count
        for workflow, count in summary.get("by_workflow", [])
        if workflow in {"find_source_then_extract_image", "replace_generic_source_then_extract_image"}
    )
    review_before_attach_rows = sum(
        count
        for workflow, count in summary.get("by_workflow", [])
        if workflow == "review_gotouchi_official_candidates"
    )

    summary_out = {
        "missing_image_rows": missing_image_rows,
        "readiness_classified_rows": readiness_total,
        "unclassified_rows": max(missing_image_rows - readiness_total, 0),
        "exact_source_ready_rows": immediate_rows,
        "source_first_rows": source_first_rows,
        "review_before_attach_rows": review_before_attach_rows,
        "source_detail_candidate_review_rows": len(source_detail_ready),
        "source_detail_candidate_count_review_required_rows": sum(
            1
            for item in source_detail_missing
            if item.get("candidate_count_review_required") is True
        ),
        "source_detail_candidate_recheck_required_rows": len(source_detail_recheck),
        "source_detail_identity_warning_rows": sum(
            1 for item in source_detail_missing if item.get("candidate_identity_flags")
        ),
        "source_detail_unflagged_candidate_rows": sum(
            1 for item in source_detail_missing if not item.get("candidate_identity_flags")
        ),
        "source_detail_ready_unflagged_candidate_rows": sum(
            1 for item in source_detail_ready if not item.get("candidate_identity_flags")
        ),
        "manual_image_research_rows": int(summary.get("manual_image_research_rows") or 0),
        "source_discovery_focus_pack_rows": int(focus_summary.get("focus_source_rows") or 0),
        "source_discovery_focus_pack_count": int(focus_summary.get("focus_pack_count") or 0),
        "source_discovery_not_started_focus_pack_count": int(focus_summary.get("not_started_focus_pack_count") or 0),
        "source_discovery_remaining_focus_review_rows": int(focus_summary.get("remaining_focus_review_rows") or 0),
        "source_discovery_confirmed_focus_source_rows": int(focus_summary.get("confirmed_focus_source_rows") or 0),
        "source_discovery_focus_template_rows": int(focus_template_summary.get("template_items") or 0),
        "source_discovery_focus_template_confirmed_rows": int(focus_template_summary.get("manual_confirmed_rows") or 0),
        "source_discovery_next_focus_pack_id": (
            next_source_discovery_focus_pack.get("focus_pack_id")
            if next_source_discovery_focus_pack
            else None
        ),
        "source_discovery_next_focus_pack_rows": int(
            (next_source_discovery_focus_pack or {}).get("row_count") or 0
        ),
        "source_discovery_next_focus_action_lane_count": int(
            (
                (next_source_discovery_focus_pack or {})
                .get("candidate_review_summary", {})
                .get("next_action_lane_count")
            )
            or 0
        ),
        "source_discovery_next_focus_action_lanes": (
            (next_source_discovery_focus_pack or {})
            .get("candidate_review_summary", {})
            .get("next_action_lanes")
            or []
        ),
        "source_discovery_focus_template_dry_run_updated_rows": int(
            focus_template_dry_run_summary.get("updated_rows") or 0
        ),
        "source_discovery_focus_template_dry_run_skipped_rows": int(
            focus_template_dry_run_summary.get("skipped_rows") or 0
        ),
        "source_discovery_focus_coverage": float(focus_summary.get("focus_coverage") or 0),
        "source_discovery_non_focus_rows": int(focus_summary.get("non_focus_source_rows") or 0),
        "action_queue_rows": int(action_summary.get("queued_image_rows") or 0) + len(source_detail_ready),
        "direct_image_action_queue_rows": int(action_summary.get("queued_image_rows") or 0),
        "direct_image_action_primary_review_url_rows": int(
            action_summary.get("primary_review_url_rows") or 0
        ),
        "direct_image_action_primary_review_url_kind_counts": (
            action_summary.get("primary_review_url_kind_counts") or []
        ),
        "direct_image_action_workflows_with_review_start": len(image_action_review_starts),
        "image_attachment_template_rows": int(image_attachment_template_summary.get("template_items") or 0),
        "image_attachment_template_confirmed_rows": int(
            image_attachment_template_summary.get("manual_confirmed_rows") or 0
        ),
        "image_attachment_template_source_update_required_rows": int(
            image_attachment_template_summary.get("source_url_update_required_rows") or 0
        ),
        "image_attachment_template_representative_review_rows": int(
            image_attachment_template_summary.get("representative_image_review_required_rows") or 0
        ),
        "image_attachment_template_dry_run_updated_rows": int(
            image_attachment_template_dry_run_summary.get("updated_rows") or 0
        ),
        "image_attachment_template_dry_run_skipped_rows": int(
            image_attachment_template_dry_run_summary.get("skipped_rows") or 0
        ),
        "actionable_image_rows": int(action_summary.get("actionable_image_rows") or 0) + len(source_detail_ready),
        "source_discovery_work_pack_count": len(source_discovery_work_packs),
        "source_discovery_work_pack_rows": sum(int(row.get("row_count") or 0) for row in source_discovery_work_packs),
        "by_blocked_reason": counter_rows(blocked_reason_counts, "blocked_reason"),
        "by_blocked_until": counter_rows(blocked_until_counts, "blocked_until"),
        "auto_apply_enabled": False,
    }
    work_order = build_work_order(
        summary_out,
        readiness_rows,
        source_store_priority,
        source_discovery_work_packs,
        next_source_discovery_focus_pack,
        image_action_review_starts,
    )
    manual_validation_focus = build_manual_validation_focus(summary_out, work_order)
    completion_plan = build_completion_plan(
        summary_out,
        source_store_priority,
        source_discovery_work_packs,
        next_source_discovery_focus_pack,
        image_action_review_starts,
    )
    execution_queue_summary = build_execution_queue_summary(
        summary_out,
        work_order,
        completion_plan,
    )
    blocking_dashboard = build_blocking_dashboard(
        summary_out,
        manual_validation_focus,
        execution_queue_summary,
        completion_plan,
    )
    summary_out.update(
        {
            "completion_plan_total_open_rows": int(completion_plan.get("total_open_rows") or 0),
            "completion_plan_phase_rows_total": int(completion_plan.get("phase_rows_total") or 0),
            "completion_plan_phase_count": int(completion_plan.get("phase_count") or 0),
            "completion_plan_status": completion_plan.get("status"),
            "blocking_dashboard_status": blocking_dashboard.get("status"),
            "blocking_dashboard_queue_coverage": blocking_dashboard.get("queue_coverage"),
        }
    )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_missing_image_actionability",
        "summary": summary_out,
        "readiness": readiness_rows,
        "source_store_priority": source_store_priority,
        "source_discovery_work_packs": source_discovery_work_packs,
        "image_action_review_starts": image_action_review_starts,
        "next_source_discovery_focus_pack": next_source_discovery_focus_pack or {},
        "work_order": work_order,
        "manual_validation_focus": manual_validation_focus,
        "execution_queue_summary": execution_queue_summary,
        "blocking_dashboard": blocking_dashboard,
        "completion_plan": completion_plan,
        "recommended_order": [
            "source_url_replacement_required",
            "representative_image_review_required",
            "source_url_discovery_required",
            "manual_research_required",
            "image_url_candidate_review",
        ],
        "notes": [
            "exact_source_ready_rows means image_url can be reviewed from an already exact product source_url.",
            "source_first_rows must receive or replace source_url before any image_url import.",
            "action_queue_rows is a review sample queue, not permission for automatic catalog mutation.",
            "source_detail_candidate_review_rows are separate source_url/image_url candidate pairs and still require exact identity confirmation.",
            "source_detail_candidate_count_review_required_rows are high-scoring candidates from large result sets; confirm exact identity before importing.",
            "source_detail_identity_warning_rows counts candidates with generic-only shared tokens, crossover titles, or missing variant hints.",
            "by_blocked_reason and by_blocked_until summarize the highest-volume blockers before image attachment can be imported.",
            "source_discovery_focus_pack_rows summarizes the top-store source discovery packs that should be handled before broad manual research.",
            "source_discovery_focus_template_rows is a blank public confirmation template; import remains dry-run safe until rows are manually confirmed.",
            "source_discovery_work_packs split the largest missing-image source discovery lane into practical store packs.",
            "image_attachment_template_rows is a blank public image confirmation template for the direct image action queue.",
            "All image changes remain manual-review only until exact product identity is confirmed.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_exact_source_url_before_image_url": True,
            "blocked_until_default": "exact_product_identity_and_source_url_confirmed",
            "required_evidence": [
                "exact_product_source_url",
                "image_url_from_accepted_source_or_trusted_official_cdn",
                "title_character_variant_type_match",
                "manual_confirmation_for_public_template_rows",
            ],
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enrichment", type=Path, default=DEFAULT_ENRICHMENT)
    parser.add_argument("--action-queue", type=Path, default=DEFAULT_ACTION_QUEUE)
    parser.add_argument("--source-detail-queue", type=Path, default=DEFAULT_SOURCE_DETAIL_QUEUE)
    parser.add_argument("--source-discovery-focus-packs", type=Path, default=DEFAULT_SOURCE_DISCOVERY_FOCUS_PACKS)
    parser.add_argument("--source-discovery-focus-template", type=Path, default=DEFAULT_SOURCE_DISCOVERY_FOCUS_TEMPLATE)
    parser.add_argument(
        "--source-discovery-focus-template-dry-run",
        type=Path,
        default=DEFAULT_SOURCE_DISCOVERY_FOCUS_TEMPLATE_DRY_RUN,
    )
    parser.add_argument(
        "--source-discovery-next-focus-detail-candidates",
        type=Path,
        default=DEFAULT_SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES,
    )
    parser.add_argument(
        "--source-discovery-next-focus-fallback-queue",
        type=Path,
        default=DEFAULT_SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE,
    )
    parser.add_argument("--image-attachment-template", type=Path, default=DEFAULT_IMAGE_ATTACHMENT_TEMPLATE)
    parser.add_argument(
        "--image-attachment-template-dry-run",
        type=Path,
        default=DEFAULT_IMAGE_ATTACHMENT_TEMPLATE_DRY_RUN,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    focus_packs = load_json(args.source_discovery_focus_packs) if args.source_discovery_focus_packs.exists() else None
    focus_template = (
        load_json(args.source_discovery_focus_template)
        if args.source_discovery_focus_template.exists()
        else None
    )
    focus_template_dry_run = (
        load_json(args.source_discovery_focus_template_dry_run)
        if args.source_discovery_focus_template_dry_run.exists()
        else None
    )
    image_attachment_template = (
        load_json(args.image_attachment_template)
        if args.image_attachment_template.exists()
        else None
    )
    image_attachment_template_dry_run = (
        load_json(args.image_attachment_template_dry_run)
        if args.image_attachment_template_dry_run.exists()
        else None
    )
    next_focus_detail_candidates = (
        load_json(args.source_discovery_next_focus_detail_candidates)
        if args.source_discovery_next_focus_detail_candidates.exists()
        else None
    )
    next_focus_fallback_queue = (
        load_json(args.source_discovery_next_focus_fallback_queue)
        if args.source_discovery_next_focus_fallback_queue.exists()
        else None
    )
    report = build_report(
        load_json(args.enrichment),
        load_json(args.action_queue),
        load_json(args.source_detail_queue),
        focus_packs,
        focus_template,
        focus_template_dry_run,
        image_attachment_template,
        image_attachment_template_dry_run,
        source_discovery_next_focus_detail_candidates=next_focus_detail_candidates,
        source_discovery_next_focus_fallback_queue=next_focus_fallback_queue,
    )
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
