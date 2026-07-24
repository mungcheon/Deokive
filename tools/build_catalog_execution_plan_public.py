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
DATA = ROOT / "data"
DEFAULT_OUTPUT = DATA / "catalog_execution_plan_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(name: str) -> dict[str, Any]:
    path = DATA / name
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    return summary if isinstance(summary, dict) else {}


def _count(summary: dict[str, Any], key: str) -> int:
    value = summary.get(key)
    if isinstance(value, bool):
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _pair_counts(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        raw_items = value.items()
    elif isinstance(value, list):
        raw_items = value
    else:
        return {}

    counts: dict[str, int] = {}
    for item in raw_items:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        key, raw_count = item
        try:
            count = int(raw_count or 0)
        except (TypeError, ValueError):
            count = 0
        if count > 0:
            counts[str(key)] = count
    return counts


def _starter_group_key(group: dict[str, Any]) -> str:
    parts = [
        str(group.get("source_store") or "").strip(),
        str(group.get("affiliation") or "").strip(),
        str(group.get("category") or "").strip(),
    ]
    return " | ".join(part for part in parts if part) or "unknown_group"


def _action(
    *,
    priority: int,
    workstream: str,
    public_report: str,
    status: str,
    rows: int,
    command: str,
    next_step: str,
    blocker: str | None = None,
    auto_apply: bool = False,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "priority": priority,
        "workstream": workstream,
        "public_report": public_report,
        "status": status,
        "rows": rows,
        "command": command,
        "next_step": next_step,
        "blocker": blocker,
        "auto_apply_enabled": auto_apply,
        "evidence": evidence or {},
    }


def _build_plan(load_report) -> dict[str, Any]:
    operations = load_report("catalog_operations_public.json")
    image_batches = load_report("catalog_image_enrichment_batches_public.json")
    image_candidates = load_report("catalog_image_candidate_review_public.json")
    image_asset_audit = load_report("catalog_image_asset_audit_public.json")
    image_action_queue = load_report("catalog_image_attachment_action_queue_public.json")
    image_actionability = load_report("catalog_missing_image_actionability_public.json")
    source_batches = load_report("source_discovery_review_batches_public.json")
    source_action_queue = load_report("source_discovery_action_queue_public.json")
    source_focus_template = load_report("source_discovery_focus_confirmed_template_public.json")
    source_focus_template_import = load_report("source_discovery_focus_template_import_dry_run_public.json")
    source_next_focus_pack = load_report("source_discovery_next_focus_pack_public.json")
    source_next_focus_fetch_audit = load_report("source_discovery_next_focus_pack_fetch_audit_public.json")
    source_next_focus_detail_candidates = load_report(
        "source_discovery_next_focus_detail_candidates_public.json"
    )
    source_next_focus_fallback_queue = load_report("source_discovery_next_focus_fallback_queue_public.json")
    source_next_focus_exact_url_review_queue = load_report(
        "source_discovery_next_focus_exact_url_review_queue_public.json"
    )
    source_next_focus_identity_backfill_queue = load_report(
        "source_discovery_next_focus_identity_backfill_queue_public.json"
    )
    source_next_focus_identity_candidate_review_queue = load_report(
        "source_discovery_next_focus_identity_candidate_review_queue_public.json"
    )
    source_discovery_starter_queue = load_report("source_discovery_starter_queue_public.json")
    source_detail_candidate_action_queue = load_report("source_detail_candidate_action_queue_public.json")
    ensky_cache_candidate_action_queue = load_report("ensky_cache_candidate_action_queue_public.json")
    metadata_batches = load_report("catalog_metadata_review_batches_public.json")
    metadata_action_queue = load_report("catalog_metadata_action_queue_public.json")
    requested_batches = load_report("requested_focus_review_batches_public.json")
    requested_action_queue = load_report("requested_focus_action_queue_public.json")
    danganronpa_missing_media = load_report("danganronpa_missing_media_public.json")
    dedupe_catalog = load_report("catalog_deduplication_public.json")
    dedupe_batches = load_report("catalog_deduplication_review_batches_public.json")
    dedupe_action_queue = load_report("catalog_deduplication_action_queue_public.json")
    dedupe_fast_review = load_report("catalog_deduplication_fast_review_public.json")
    dedupe_template_import = load_report("catalog_deduplication_template_import_dry_run_public.json")
    kuji_reissue_decision_template = load_report("ichiban_kuji_reissue_decision_template_public.json")
    kuji_history = load_report("ichiban_kuji_history_public.json")
    kuji_historical_roadmap = load_report("ichiban_kuji_historical_roadmap_public.json")
    kuji_batches = load_report("ichiban_kuji_metadata_review_batches_public.json")
    kuji_action_queue = load_report("ichiban_kuji_metadata_action_queue_public.json")
    kuji_metadata_fast_review = load_report("ichiban_kuji_metadata_fast_review_public.json")
    kuji_policy = load_report("ichiban_kuji_prize_policy_audit_public.json")
    kuji_policy_issue_queue = load_report("ichiban_kuji_prize_policy_issue_queue_public.json")
    kuji_name_image = load_report("ichiban_kuji_prize_name_image_review_public.json")
    kuji_name_image_patch = load_report("ichiban_kuji_prize_name_image_patch_candidates_public.json")
    animation_goods_categories = load_report("animation_goods_categories_public.json")
    animation_coverage_audit = load_report("animation_category_coverage_audit_public.json")
    animation_batches = load_report("animation_category_review_batches_public.json")
    animation_action_queue = load_report("animation_category_action_queue_public.json")
    animation_split_review = load_report("animation_category_split_review_public.json")
    animation_unmatched_keywords = load_report("animation_category_unmatched_keyword_review_public.json")
    confirmed_readiness = load_report("catalog_confirmed_import_readiness_public.json")

    operations_summary = _summary(operations)
    open_queues = operations_summary.get("open_review_queues")
    if not isinstance(open_queues, dict):
        open_queues = {}
    image_summary = _summary(image_batches)
    image_candidate_summary = _summary(image_candidates)
    image_asset_summary = _summary(image_asset_audit)
    image_action_summary = _summary(image_action_queue)
    image_actionability_summary = _summary(image_actionability)
    source_summary = _summary(source_batches)
    source_action_summary = _summary(source_action_queue)
    source_focus_template_summary = _summary(source_focus_template)
    source_next_focus_fetch_audit_summary = _summary(source_next_focus_fetch_audit)
    source_next_focus_detail_summary = _summary(source_next_focus_detail_candidates)
    source_next_focus_fallback_summary = _summary(source_next_focus_fallback_queue)
    source_next_focus_exact_url_summary = _summary(source_next_focus_exact_url_review_queue)
    source_next_focus_identity_backfill_summary = _summary(
        source_next_focus_identity_backfill_queue
    )
    source_next_focus_identity_candidate_summary = _summary(
        source_next_focus_identity_candidate_review_queue
    )
    source_discovery_starter_summary = _summary(source_discovery_starter_queue)
    source_detail_candidate_action_summary = _summary(source_detail_candidate_action_queue)
    ensky_cache_candidate_action_summary = _summary(ensky_cache_candidate_action_queue)
    metadata_summary = _summary(metadata_batches)
    metadata_action_summary = _summary(metadata_action_queue)
    source_next_focus_pack_summary = _summary(source_next_focus_pack)
    requested_summary = _summary(requested_batches)
    requested_action_summary = _summary(requested_action_queue)
    danganronpa_media_summary = _summary(danganronpa_missing_media)
    dedupe_catalog_summary = _summary(dedupe_catalog)
    dedupe_summary = _summary(dedupe_batches)
    dedupe_action_summary = _summary(dedupe_action_queue)
    dedupe_fast_summary = _summary(dedupe_fast_review)
    dedupe_template_import_summary = _summary(dedupe_template_import)
    dedupe_completion = dedupe_action_queue.get("completion_readiness")
    if not isinstance(dedupe_completion, dict):
        dedupe_completion = {}
    kuji_reissue_decision_template_summary = _summary(kuji_reissue_decision_template)
    kuji_history_summary = _summary(kuji_history)
    kuji_historical_roadmap_summary = _summary(kuji_historical_roadmap)
    kuji_historical_readiness = kuji_historical_roadmap_summary.get("completion_readiness")
    if not isinstance(kuji_historical_readiness, dict):
        kuji_historical_readiness = {}
    dedupe_fast_breakdowns = dedupe_fast_review.get("breakdowns")
    if not isinstance(dedupe_fast_breakdowns, dict):
        dedupe_fast_breakdowns = {}
    kuji_summary = _summary(kuji_batches)
    kuji_action_summary = _summary(kuji_action_queue)
    kuji_metadata_fast_summary = _summary(kuji_metadata_fast_review)
    kuji_policy_summary = _summary(kuji_policy)
    kuji_policy_issue_summary = _summary(kuji_policy_issue_queue)
    kuji_name_image_summary = _summary(kuji_name_image)
    kuji_name_image_patch_summary = _summary(kuji_name_image_patch)
    animation_goods_summary = _summary(animation_goods_categories)
    animation_coverage_summary = _summary(animation_coverage_audit)
    animation_summary = _summary(animation_batches)
    animation_action_summary = _summary(animation_action_queue)
    animation_split_summary = _summary(animation_split_review)
    animation_unmatched_summary = _summary(animation_unmatched_keywords)
    animation_unmatched_product_type_candidates = _count(animation_unmatched_summary, "product_type_candidate_count")
    open_queues = dict(open_queues)
    open_queues[
        "animation_category_unmatched_keyword_product_type_candidates"
    ] = animation_unmatched_product_type_candidates
    confirmed_summary = _summary(confirmed_readiness)
    confirmed_work_order = confirmed_readiness.get("work_order")
    if not isinstance(confirmed_work_order, list):
        confirmed_work_order = []

    actions: list[dict[str, Any]] = []
    requested_template_counts = _pair_counts(requested_summary.get("field_patch_template_counts", []))
    requested_barcode_template_rows = requested_template_counts.get("barcode", 0)
    requested_actionable_template_rows = sum(
        count for field, count in requested_template_counts.items() if field != "barcode"
    )
    pending_import_rows = _count(confirmed_summary, "ready_or_pending_import_rows")
    blocked_confirmed_rows = _count(confirmed_summary, "blocked_confirmed_rows")
    template_items = _count(confirmed_summary, "template_items")
    public_action_queue_rows = _count(confirmed_summary, "public_action_queue_rows")
    public_action_queue_batches = _count(confirmed_summary, "public_action_queue_batches")
    confirmation_rows = template_items + public_action_queue_rows
    manual_confirmed_ready_rows = _count(confirmed_summary, "manual_confirmed_true")
    manual_confirmation_backlog_rows = max(confirmation_rows - manual_confirmed_ready_rows, 0)
    actions.append(
        _action(
            priority=5,
            workstream="confirmed_import_readiness",
            public_report="data/catalog_confirmed_import_readiness_public.json",
            status="pending_import" if pending_import_rows else "needs_manual_confirmation",
            rows=pending_import_rows or confirmation_rows,
            command=(
                "Run the matching guarded import dry-run, then write only manually confirmed exact rows."
                if pending_import_rows
                else "Review templates/action queues and mark exact rows manual_confirmed=true before importing."
            ),
            next_step="confirm_exact_rows_then_run_guarded_import",
            blocker=None if pending_import_rows else "No public workflow has manual_confirmed=true rows yet.",
            evidence={
                "workflow_count": _count(confirmed_summary, "workflow_count"),
                "confirmed_files": _count(confirmed_summary, "confirmed_files"),
                "template_items": template_items,
                "public_action_queue_rows": public_action_queue_rows,
                "public_action_queue_batches": public_action_queue_batches,
                "ready_or_pending_import_rows": pending_import_rows,
                "manual_confirmed_ready_rows": manual_confirmed_ready_rows,
                "manual_confirmation_backlog_rows": manual_confirmation_backlog_rows,
                "blocked_confirmed_rows": blocked_confirmed_rows,
                "work_order_lanes": _count(confirmed_summary, "work_order_lanes"),
                "top_work_order_row_count": _count(
                    confirmed_summary, "top_work_order_row_count"
                ),
                "top_work_order_lane": confirmed_summary.get("top_work_order_lane"),
                "top_work_order_workflow": confirmed_summary.get(
                    "top_work_order_workflow"
                ),
                "by_status": confirmed_summary.get("by_status", []),
                "top_work_orders": [
                    {
                        "workflow": row.get("workflow"),
                        "public_workstream": row.get("public_workstream"),
                        "lane": row.get("lane"),
                        "row_count": row.get("row_count", 0),
                        "batch_count": row.get("batch_count", 0),
                        "next_step": row.get("next_step"),
                        "template_file_exists": row.get("template_file_exists"),
                        "manual_confirmation_required": row.get(
                            "manual_confirmation_required"
                        ),
                        "auto_apply_enabled": row.get("auto_apply_enabled"),
                    }
                    for row in confirmed_work_order
                    if isinstance(row, dict)
                ][:8],
            },
        )
    )

    actions.append(
        _action(
            priority=10,
            workstream="requested_focus_review_batches",
            public_report="data/requested_focus_review_batches_public.json",
            status="manual_review",
            rows=_count(requested_summary, "review_row_count"),
            command="Work batches by topic, missing field, and source store; prepare reviewed patches only.",
            next_step="prioritize_user_requested_topics",
            blocker="Exact source evidence is required before catalog mutation.",
            evidence={
                "batch_count": _count(requested_summary, "batch_count"),
                "by_topic": requested_summary.get("by_topic", []),
                "by_missing_field": requested_summary.get("by_missing_field", []),
                "field_patch_template_count": _count(requested_summary, "field_patch_template_count"),
                "field_patch_template_counts": requested_summary.get("field_patch_template_counts", []),
                "actionable_non_barcode_template_rows": requested_actionable_template_rows,
                "barcode_template_rows": requested_barcode_template_rows,
            },
        )
    )

    actions.append(
        _action(
            priority=11,
            workstream="requested_focus_action_queue",
            public_report="data/requested_focus_action_queue_public.json",
            status="manual_review",
            rows=_count(requested_action_summary, "queued_action_rows"),
            command="Work the non-barcode requested-focus action queue before long barcode research.",
            next_step="review_actionable_source_image_date_price_name_batches",
            blocker="Exact source evidence is still required before catalog mutation.",
            evidence={
                "actionable_template_rows": _count(requested_action_summary, "actionable_template_rows"),
                "queued_action_rows": _count(requested_action_summary, "queued_action_rows"),
                "action_batch_count": _count(requested_action_summary, "action_batch_count"),
                "barcode_template_rows_excluded": _count(requested_action_summary, "barcode_template_rows_excluded"),
                "field_counts": requested_action_summary.get("field_counts", []),
                "topic_counts": requested_action_summary.get("topic_counts", []),
            },
        )
    )

    actions.append(
        _action(
            priority=12,
            workstream="danganronpa_missing_media",
            public_report="data/danganronpa_missing_media_public.json",
            status="manual_review",
            rows=_count(danganronpa_media_summary, "missing_media_rows"),
            command=(
                "Review Danganronpa rows missing both source and image evidence; fill exact official or licensed "
                "source URLs before attaching images."
            ),
            next_step="work_danganronpa_missing_media_review_batches",
            blocker="Exact official or licensed source evidence is required before catalog mutation.",
            evidence={
                "missing_media_rows": _count(danganronpa_media_summary, "missing_media_rows"),
                "missing_image_url_rows": _count(danganronpa_media_summary, "missing_image_url_rows"),
                "missing_source_url_rows": _count(danganronpa_media_summary, "missing_source_url_rows"),
                "review_batch_count": _count(danganronpa_media_summary, "review_batch_count"),
                "official_search_rows": _count(danganronpa_media_summary, "official_search_rows"),
                "licensed_retailer_review_rows": _count(
                    danganronpa_media_summary, "licensed_retailer_review_rows"
                ),
                "official_prize_search_rows": _count(danganronpa_media_summary, "official_prize_search_rows"),
                "by_source_store": danganronpa_media_summary.get("by_source_store", []),
                "by_source_kind": danganronpa_media_summary.get("by_source_kind", []),
            },
        )
    )

    actions.append(
        _action(
            priority=20,
            workstream="source_discovery_review_batches",
            public_report="data/source_discovery_review_batches_public.json",
            status="manual_review",
            rows=_count(source_summary, "source_discovery_rows"),
            command="Find exact official/detail source URLs for rows missing source_url.",
            next_step="attach_exact_source_url_before_image_import",
            blocker="Rows without exact source_url cannot safely import images.",
            evidence={
                "batch_count": _count(source_summary, "batch_count"),
                "by_workflow": source_summary.get("by_workflow", []),
            },
        )
    )

    if source_focus_template_summary:
        actions.append(
            _action(
                priority=20,
                workstream="source_discovery_focus_template",
                public_report="data/source_discovery_focus_confirmed_template_public.json",
                status="manual_review",
                rows=_count(source_focus_template_summary, "template_items"),
                command="Open the focus template work_order and confirm exact product source URLs for the next store/category pack.",
                next_step="work_source_focus_template_work_order_top_to_bottom",
                blocker="Imports stay dry-run only until exact product URLs are manually confirmed.",
                evidence={
                    "template_items": _count(source_focus_template_summary, "template_items"),
                    "work_order_pack_count": _count(source_focus_template_summary, "work_order_pack_count"),
                    "next_focus_pack_id": source_focus_template_summary.get("next_focus_pack_id"),
                    "next_source_store": source_focus_template_summary.get("next_source_store"),
                    "next_target_category": source_focus_template_summary.get("next_target_category"),
                    "next_focus_pack_rows": _count(source_focus_template_summary, "next_focus_pack_rows"),
                    "next_official_search_url": source_focus_template_summary.get("next_official_search_url"),
                    "current_focus_pack_id": source_next_focus_pack_summary.get("focus_pack_id"),
                    "pack_queue_preview_count": _count(source_next_focus_pack_summary, "pack_queue_preview_count"),
                    "next_pack_after_current": source_next_focus_pack_summary.get("next_pack_after_current"),
                    "pack_queue_preview": source_next_focus_pack.get("pack_queue_preview", []),
                    "manual_confirmed_rows": _count(source_focus_template_summary, "manual_confirmed_rows"),
                    "dry_run_updated_rows": _count(source_focus_template_import, "updated_rows"),
                    "dry_run_skipped_rows": _count(source_focus_template_import, "skipped_rows"),
                },
            )
        )

    if source_next_focus_fetch_audit_summary:
        fallback_required = bool(source_next_focus_fetch_audit_summary.get("fallback_web_search_required"))
        actions.append(
            _action(
                priority=20,
                workstream="source_discovery_next_focus_pack_fetch_audit",
                public_report="data/source_discovery_next_focus_pack_fetch_audit_public.json",
                status="fallback_required" if fallback_required else "manual_review",
                rows=_count(source_next_focus_fetch_audit_summary, "official_search_unavailable_rows"),
                command=(
                    "Use web search, store archives, or alternate official entry points to find exact product detail URLs for the current focus pack."
                    if fallback_required
                    else "Review reachable official search results and confirm exact product detail URLs."
                ),
                next_step="resolve_unavailable_official_search_urls_before_source_import",
                blocker=(
                    "Current focus pack official_search_url values are not fetchable; do not import source_url/image_url from these search URLs."
                    if fallback_required
                    else "Manual identity confirmation is still required before import."
                ),
                evidence={
                    "focus_pack_id": source_next_focus_fetch_audit_summary.get("focus_pack_id"),
                    "pack_items": _count(source_next_focus_fetch_audit_summary, "pack_items"),
                    "official_search_ok_rows": _count(source_next_focus_fetch_audit_summary, "official_search_ok_rows"),
                    "official_search_unavailable_rows": _count(
                        source_next_focus_fetch_audit_summary, "official_search_unavailable_rows"
                    ),
                    "status_counts": source_next_focus_fetch_audit_summary.get("status_counts", []),
                },
            )
        )

    if source_next_focus_detail_summary:
        lane_counts = source_next_focus_detail_summary.get("next_action_lanes")
        if not isinstance(lane_counts, list):
            lane_counts = []
        actions.append(
            _action(
                priority=20,
                workstream="source_discovery_next_focus_detail_candidates",
                public_report="data/source_discovery_next_focus_detail_candidates_public.json",
                status=(
                    "manual_review"
                    if _count(source_next_focus_detail_summary, "next_action_lane_count")
                    else "clear"
                ),
                rows=_count(source_next_focus_detail_summary, "pack_items"),
                command="Work the current focus pack by next_action_lanes so fallback search, variant metadata, and identity review are not mixed.",
                next_step="resolve_current_focus_pack_lanes_before_source_import",
                blocker="Rows still need exact product identity or source evidence before source/image import.",
                evidence={
                    "focus_pack_id": source_next_focus_detail_summary.get("focus_pack_id"),
                    "pack_items": _count(source_next_focus_detail_summary, "pack_items"),
                    "items_with_candidates": _count(
                        source_next_focus_detail_summary, "items_with_candidates"
                    ),
                    "candidate_rows": _count(source_next_focus_detail_summary, "candidate_rows"),
                    "next_action_lane_count": _count(
                        source_next_focus_detail_summary, "next_action_lane_count"
                    ),
                    "next_action_lanes": lane_counts,
                    "completion_readiness_status": source_next_focus_detail_summary.get(
                        "completion_readiness_status"
                    ),
                    "auto_apply_ready_rows": _count(
                        source_next_focus_detail_summary, "auto_apply_ready_rows"
                    ),
                    "auto_apply_enabled": bool(
                        source_next_focus_detail_summary.get("auto_apply_enabled", False)
                    ),
                },
            )
        )

    if source_next_focus_fallback_summary:
        actions.append(
            _action(
                priority=20,
                workstream="source_discovery_next_focus_fallback_queue",
                public_report="data/source_discovery_next_focus_fallback_queue_public.json",
                status="manual_review" if _count(source_next_focus_fallback_summary, "queue_rows") else "clear",
                rows=_count(source_next_focus_fallback_summary, "queue_rows"),
                command="Work fallback rows with web search, archives, or alternate official store entry points.",
                next_step="fill_exact_manual_confirmed_source_urls_from_fallback_research",
                blocker="Every fallback source_url still needs exact product identity confirmation before import.",
                evidence={
                    "focus_pack_id": source_next_focus_fallback_summary.get("focus_pack_id"),
                    "queue_rows": _count(source_next_focus_fallback_summary, "queue_rows"),
                    "manual_confirmed_rows": _count(source_next_focus_fallback_summary, "manual_confirmed_rows"),
                    "source_confirmation_ready_rows": _count(
                        source_next_focus_fallback_summary, "source_confirmation_ready_rows"
                    ),
                    "exact_url_review_queue_rows": _count(
                        source_next_focus_exact_url_summary, "queue_rows"
                    ),
                    "identity_backfill_queue_rows": _count(
                        source_next_focus_identity_backfill_summary, "queue_rows"
                    ),
                    "identity_candidate_review_queue_rows": _count(
                        source_next_focus_identity_candidate_summary, "queue_rows"
                    ),
                    "identity_candidate_review_candidate_rows": _count(
                        source_next_focus_identity_candidate_summary, "candidate_rows"
                    ),
                    "metadata_backfill_required_rows": _count(
                        source_next_focus_fallback_summary, "metadata_backfill_required_rows"
                    ),
                    "variant_disambiguation_required_rows": _count(
                        source_next_focus_fallback_summary,
                        "variant_disambiguation_required_rows",
                    ),
                    "by_identity_review_status": source_next_focus_fallback_summary.get(
                        "by_identity_review_status", []
                    ),
                    "fallback_reason": source_next_focus_fallback_summary.get("fallback_reason"),
                    "by_http_status": source_next_focus_fallback_summary.get("by_http_status", []),
                    "by_source_store": source_next_focus_fallback_summary.get("by_source_store", []),
                    "by_category": source_next_focus_fallback_summary.get("by_category", []),
                    "work_order_steps": _count(source_next_focus_fallback_summary, "work_order_steps"),
                    "work_order_lanes": source_next_focus_fallback_summary.get("work_order_lanes", []),
                    "first_domain_limited_web_search_url": source_next_focus_fallback_summary.get(
                        "first_domain_limited_web_search_url"
                    ),
                    "first_fallback_store_search_url": source_next_focus_fallback_summary.get(
                        "first_fallback_store_search_url"
                    ),
                    "first_primary_review_url": source_next_focus_fallback_summary.get(
                        "first_primary_review_url"
                    ),
                    "first_primary_review_url_kind": source_next_focus_fallback_summary.get(
                        "first_primary_review_url_kind"
                    ),
                },
            )
        )

    if source_next_focus_exact_url_summary:
        actions.append(
            _action(
                priority=20,
                workstream="source_discovery_next_focus_exact_url_review_queue",
                public_report="data/source_discovery_next_focus_exact_url_review_queue_public.json",
                status="manual_review"
                if _count(source_next_focus_exact_url_summary, "queue_rows")
                else "clear",
                rows=_count(source_next_focus_exact_url_summary, "queue_rows"),
                command="Confirm exact product detail URLs from the fallback queue before image attachment.",
                next_step="copy_exact_confirmed_source_urls_into_focus_template",
                blocker="Exact source URL review is manual-only until product identity is confirmed.",
                evidence={
                    "queue_rows": _count(source_next_focus_exact_url_summary, "queue_rows"),
                    "manual_confirmed_rows": _count(
                        source_next_focus_exact_url_summary, "manual_confirmed_rows"
                    ),
                    "blocked_identity_rows": _count(
                        source_next_focus_exact_url_summary, "blocked_identity_rows"
                    ),
                    "by_source_store": source_next_focus_exact_url_summary.get(
                        "by_source_store", []
                    ),
                    "by_category": source_next_focus_exact_url_summary.get("by_category", []),
                    "by_identity_review_status": source_next_focus_exact_url_summary.get(
                        "by_identity_review_status", []
                    ),
                    "primary_review_url_rows": _count(
                        source_next_focus_exact_url_summary, "primary_review_url_rows"
                    ),
                    "primary_review_url_kind_counts": source_next_focus_exact_url_summary.get(
                        "primary_review_url_kind_counts", []
                    ),
                    "first_primary_review_url": source_next_focus_exact_url_summary.get(
                        "first_primary_review_url"
                    ),
                    "first_primary_review_url_kind": source_next_focus_exact_url_summary.get(
                        "first_primary_review_url_kind"
                    ),
                    "auto_apply_enabled": bool(
                        source_next_focus_exact_url_summary.get("auto_apply_enabled", False)
                    ),
                },
            )
        )

    if source_discovery_starter_summary:
        actions.append(
            _action(
                priority=20,
                workstream="source_discovery_starter_queue",
                public_report="data/source_discovery_starter_queue_public.json",
                status=(
                    "manual_review"
                    if _count(source_discovery_starter_summary, "starter_queue_rows")
                    else "clear"
                ),
                rows=_count(source_discovery_starter_summary, "starter_queue_rows"),
                command=(
                    "Open starter search URLs and confirm exact official product/detail source pages for every "
                    "missing-source group before image imports."
                ),
                next_step="find_exact_official_product_source_url",
                blocker="Auto source/image import is disabled until exact product evidence is manually confirmed.",
                evidence={
                    "starter_queue_rows": _count(source_discovery_starter_summary, "starter_queue_rows"),
                    "starter_queue_groups": _count(source_discovery_starter_summary, "starter_queue_groups"),
                    "coverage_matches_missing_source_url_rows": bool(
                        source_discovery_starter_summary.get("coverage_matches_missing_source_url_rows", False)
                    ),
                    "by_source_store": source_discovery_starter_summary.get("by_source_store", []),
                    "top_groups": [
                        {
                            "group_key": row.get("group_key") or _starter_group_key(row),
                            "rows": row.get("rows", 0),
                            "source_store": row.get("source_store"),
                            "category": row.get("category"),
                            "first_search_url": row.get("first_search_url"),
                            "search_urls": row.get("search_urls", []),
                            "first_fallback_web_search_url": row.get("first_fallback_web_search_url"),
                            "fallback_web_search_urls": row.get("fallback_web_search_urls", []),
                        }
                        for row in source_discovery_starter_queue.get("groups", [])
                        if isinstance(row, dict)
                    ][:8],
                    "fallback_groups": [
                        {
                            "group_key": row.get("group_key") or _starter_group_key(row),
                            "rows": row.get("rows", 0),
                            "source_store": row.get("source_store"),
                            "category": row.get("category"),
                            "first_fallback_web_search_url": row.get("first_fallback_web_search_url"),
                            "fallback_web_search_urls": row.get("fallback_web_search_urls", []),
                        }
                        for row in source_discovery_starter_queue.get("groups", [])
                        if isinstance(row, dict) and row.get("fallback_web_search_urls")
                    ][:8],
                },
            )
        )

    actions.append(
        _action(
            priority=21,
            workstream="source_discovery_action_queue",
            public_report="data/source_discovery_action_queue_public.json",
            status="manual_review",
            rows=_count(source_action_summary, "queued_source_rows"),
            command="Confirm exact product/detail URLs from official search paths before broad source research.",
            next_step="confirm_exact_source_url_then_fill_source_templates",
            blocker="Auto source import is disabled; every source_url needs exact product evidence.",
            evidence={
                "actionable_source_rows": _count(source_action_summary, "actionable_source_rows"),
                "queued_source_rows": _count(source_action_summary, "queued_source_rows"),
                "action_batch_count": _count(source_action_summary, "action_batch_count"),
                "source_discovery_template_rows": _count(
                    source_action_summary, "source_discovery_template_rows"
                ),
                "source_discovery_template_batch_count": _count(
                    source_action_summary, "source_discovery_template_batch_count"
                ),
                "source_patch_template_count": _count(
                    source_action_summary, "source_patch_template_count"
                ),
                "catalog_field_import_template_count": _count(
                    source_action_summary, "catalog_field_import_template_count"
                ),
                "primary_review_url_rows": _count(source_action_summary, "primary_review_url_rows"),
                "primary_review_url_kind_counts": source_action_summary.get(
                    "primary_review_url_kind_counts", []
                ),
                "manual_research_backlog_rows": _count(
                    source_action_summary, "manual_research_backlog_rows"
                ),
                "manual_research_backlog_by_source_store": source_action_summary.get(
                    "manual_research_backlog_by_source_store", []
                ),
                "excluded_review_state_rows": source_action_summary.get("excluded_review_state_rows", []),
                "by_review_state": source_action_summary.get("by_review_state", []),
                "by_workflow": source_action_summary.get("by_workflow", []),
                "by_source_store": source_action_summary.get("by_source_store", []),
                "first_primary_review_url": source_action_summary.get("first_primary_review_url"),
                "first_primary_review_url_kind": source_action_summary.get("first_primary_review_url_kind"),
            },
        )
    )

    if source_detail_candidate_action_summary:
        actions.append(
            _action(
                priority=22,
                workstream="source_detail_candidate_action_queue",
                public_report="data/source_detail_candidate_action_queue_public.json",
                status="manual_review",
                rows=_count(source_detail_candidate_action_summary, "candidate_action_rows"),
                command="Review exact-looking product/detail candidates that already include source and image URLs.",
                next_step="manual_confirm_source_image_pair_then_fill_templates",
                blocker="Candidate source/image pairs can still be wrong variants; manual identity review is required.",
                evidence={
                    "candidate_action_rows": _count(
                        source_detail_candidate_action_summary, "candidate_action_rows"
                    ),
                    "safe_source_image_pair_rows": _count(
                        source_detail_candidate_action_summary, "safe_source_image_pair_rows"
                    ),
                    "manual_confirmation_shortlist_rows": _count(
                        source_detail_candidate_action_summary, "manual_confirmation_shortlist_rows"
                    ),
                    "near_or_better_candidate_rows": _count(
                        source_detail_candidate_action_summary, "near_or_better_candidate_rows"
                    ),
                    "ambiguous_or_weaker_candidate_rows": _count(
                        source_detail_candidate_action_summary, "ambiguous_or_weaker_candidate_rows"
                    ),
                    "manual_confirmed_true": _count(
                        source_detail_candidate_action_summary, "manual_confirmed_true"
                    ),
                    "by_source_store": source_detail_candidate_action_summary.get("by_source_store", []),
                    "by_review_risk": source_detail_candidate_action_summary.get("by_review_risk", []),
                    "by_candidate_count_bucket": source_detail_candidate_action_summary.get(
                        "by_candidate_count_bucket", []
                    ),
                },
            )
        )

    if ensky_cache_candidate_action_summary:
        actions.append(
            _action(
                priority=23,
                workstream="ensky_cache_candidate_action_queue",
                public_report="data/ensky_cache_candidate_action_queue_public.json",
                status="manual_review",
                rows=_count(ensky_cache_candidate_action_summary, "candidate_action_rows"),
                command="Review broad Ensky cache matches, then fill exact source_url and image_url templates only for confirmed products.",
                next_step="manual_confirm_ensky_cache_candidate_then_fill_source_and_image_templates",
                blocker="Broad cache candidates can match the wrong character or goods type, so auto-apply stays disabled.",
                evidence={
                    "candidate_action_rows": _count(ensky_cache_candidate_action_summary, "candidate_action_rows"),
                    "action_batch_count": _count(ensky_cache_candidate_action_summary, "action_batch_count"),
                    "manual_confirmed_true": _count(ensky_cache_candidate_action_summary, "manual_confirmed_true"),
                    "candidate_source_url_ready_rows": _count(
                        ensky_cache_candidate_action_summary,
                        "candidate_source_url_ready_rows",
                    ),
                    "candidate_image_url_ready_rows": _count(
                        ensky_cache_candidate_action_summary,
                        "candidate_image_url_ready_rows",
                    ),
                    "safe_exact_top_candidate_rows": _count(
                        ensky_cache_candidate_action_summary,
                        "safe_exact_top_candidate_rows",
                    ),
                    "can_import_now_rows": _count(
                        ensky_cache_candidate_action_summary,
                        "can_import_now_rows",
                    ),
                    "blocked_manual_review_rows": _count(
                        ensky_cache_candidate_action_summary,
                        "blocked_manual_review_rows",
                    ),
                    "import_readiness": ensky_cache_candidate_action_queue.get("import_readiness", {}),
                    "by_affiliation": ensky_cache_candidate_action_summary.get("by_affiliation", []),
                    "by_category": ensky_cache_candidate_action_summary.get("by_category", []),
                    "auto_apply_enabled": bool(
                        ensky_cache_candidate_action_summary.get("auto_apply_enabled", False)
                    ),
                },
            )
        )

    missing_images = _count(image_summary, "missing_image_rows")
    ready_image_rows = _count(image_summary, "source_url_ready_rows")
    actions.append(
        _action(
            priority=30,
            workstream="image_url_attachment",
            public_report="data/catalog_image_enrichment_batches_public.json",
            status="blocked" if ready_image_rows == 0 and missing_images else "ready",
            rows=missing_images,
            command="Extract images only after exact source_url evidence is confirmed.",
            next_step="resolve_source_url_blockers_then_extract_images",
            blocker="No exact source_url-ready image rows are currently published." if ready_image_rows == 0 else None,
            evidence={
                "known_image_asset_status": image_asset_summary.get("status"),
                "download_readiness_status": image_asset_summary.get(
                    "download_readiness_status"
                ),
                "image_url_rows": _count(image_asset_summary, "image_url_rows"),
                "local_image_path_rows": _count(
                    image_asset_summary, "local_image_path_rows"
                ),
                "image_url_without_local_path_rows": _count(
                    image_asset_summary, "image_url_without_local_path_rows"
                ),
                "missing_local_image_files": _count(
                    image_asset_summary, "missing_local_image_files"
                ),
                "missing_web_public_asset_files": _count(
                    image_asset_summary, "missing_web_public_asset_files"
                ),
                "known_image_download_blocker_rows": _count(
                    image_asset_summary, "known_image_download_blocker_rows"
                ),
                "auto_download_ready_rows": _count(
                    image_asset_summary, "auto_download_ready_rows"
                ),
                "rows_still_requiring_image_url_evidence": _count(
                    image_asset_summary, "rows_still_requiring_image_url_evidence"
                ),
                "source_url_ready_rows": ready_image_rows,
                "provider_candidate_items": _count(image_candidate_summary, "provider_candidate_items"),
                "manual_or_blocked_items": _count(image_candidate_summary, "manual_or_blocked_items"),
                "generic_source_url_rows": _count(image_summary, "generic_source_url_rows"),
                "needs_source_discovery_rows": _count(image_summary, "needs_source_discovery_rows"),
                "gotouchi_official_review_rows": _count(image_summary, "gotouchi_official_review_rows"),
            },
        )
    )

    actions.append(
        _action(
            priority=31,
            workstream="image_attachment_action_queue",
            public_report="data/catalog_image_attachment_action_queue_public.json",
            status="manual_review",
            rows=_count(image_action_summary, "queued_image_rows"),
            command="Work image attachment batches with exact product evidence before broad missing-image research.",
            next_step="confirm_source_then_fill_image_url_templates",
            blocker="Auto image import is disabled; every image URL needs reviewed product evidence.",
            evidence={
                "actionable_image_rows": _count(image_action_summary, "actionable_image_rows"),
                "queued_image_rows": _count(image_action_summary, "queued_image_rows"),
                "action_batch_count": _count(image_action_summary, "action_batch_count"),
                "source_url_update_required_rows": _count(
                    image_action_summary, "source_url_update_required_rows"
                ),
                "source_url_update_template_rows": _count(
                    image_action_summary, "source_url_update_template_rows"
                ),
                "source_url_update_template_batch_count": _count(
                    image_action_summary, "source_url_update_template_batch_count"
                ),
                "representative_image_review_required_rows": _count(
                    image_action_summary, "representative_image_review_required_rows"
                ),
                "image_url_ready_rows": _count(image_action_summary, "image_url_ready_rows"),
                "download_ready_after_manual_image_url_rows": _count(
                    image_action_summary, "download_ready_after_manual_image_url_rows"
                ),
                "suggested_local_image_path_rows": _count(
                    image_action_summary, "suggested_local_image_path_rows"
                ),
                "local_image_download_instruction_ready_rows": _count(
                    image_action_summary, "local_image_download_instruction_ready_rows"
                ),
                "image_attachment_template_rows": _count(
                    image_actionability_summary, "image_attachment_template_rows"
                ),
                "image_attachment_template_confirmed_rows": _count(
                    image_actionability_summary,
                    "image_attachment_template_confirmed_rows",
                ),
                "image_attachment_template_dry_run_updated_rows": _count(
                    image_actionability_summary,
                    "image_attachment_template_dry_run_updated_rows",
                ),
                "image_attachment_template_dry_run_skipped_rows": _count(
                    image_actionability_summary,
                    "image_attachment_template_dry_run_skipped_rows",
                ),
                "source_discovery_focus_template_rows": _count(
                    image_actionability_summary, "source_discovery_focus_template_rows"
                ),
                "source_discovery_focus_template_confirmed_rows": _count(
                    image_actionability_summary,
                    "source_discovery_focus_template_confirmed_rows",
                ),
                "workstream_count": _count(image_action_summary, "workstream_count"),
                "source_url_update_workstream_count": _count(
                    image_action_summary, "source_url_update_workstream_count"
                ),
                "representative_image_review_workstream_count": _count(
                    image_action_summary, "representative_image_review_workstream_count"
                ),
                "top_image_attachment_workstreams": [
                    {
                        "workflow": row.get("workflow"),
                        "source_store": row.get("source_store"),
                        "queued_image_rows": row.get("queued_image_rows", 0),
                        "batch_count": row.get("batch_count", 0),
                        "next_batch_id": row.get("next_batch_id"),
                        "source_url_update_template_rows": row.get("source_url_update_template_rows", 0),
                        "representative_image_review_rows": row.get("representative_image_review_rows", 0),
                    }
                    for row in image_action_queue.get("workstreams", [])
                    if isinstance(row, dict)
                ][:8],
                "excluded_workflow_rows": image_action_summary.get("excluded_workflow_rows", []),
                "by_workflow": image_action_summary.get("by_workflow", []),
            },
        )
    )

    actions.append(
        _action(
            priority=40,
            workstream="metadata_review_batches",
            public_report="data/catalog_metadata_review_batches_public.json",
            status="manual_review",
            rows=_count(metadata_summary, "missing_cell_count"),
            command="Fill titles, barcodes, dates, prices, sources, and images from reviewed evidence.",
            next_step="work_field_store_metadata_batches",
            blocker="Broad metadata updates require field-specific evidence policies.",
            evidence={
                "batch_count": _count(metadata_summary, "batch_count"),
                "field_missing_totals": metadata_summary.get("field_missing_totals", {}),
            },
        )
    )

    actions.append(
        _action(
            priority=41,
            workstream="metadata_action_queue",
            public_report="data/catalog_metadata_action_queue_public.json",
            status="manual_review",
            rows=_count(metadata_action_summary, "queued_missing_cells"),
            command="Confirm release dates, prices, and Japanese names from official evidence before barcode work.",
            next_step="fill_confirmed_metadata_patch_templates",
            blocker="Auto metadata import is disabled; every field/store group needs evidence.",
            evidence={
                "actionable_group_count": _count(metadata_action_summary, "actionable_group_count"),
                "queued_group_count": _count(metadata_action_summary, "queued_group_count"),
                "actionable_missing_cells": _count(metadata_action_summary, "actionable_missing_cells"),
                "queued_missing_cells": _count(metadata_action_summary, "queued_missing_cells"),
                "action_batch_count": _count(metadata_action_summary, "action_batch_count"),
                "field_counts": metadata_action_summary.get("field_counts", []),
                "missing_cells_by_field": metadata_action_summary.get("missing_cells_by_field", []),
                "missing_cells_by_source_store": metadata_action_summary.get("missing_cells_by_source_store", []),
                "top_action_groups": metadata_action_summary.get("top_action_groups", []),
            },
        )
    )

    if kuji_name_image_summary:
        kuji_name_image_review_rows = _count(kuji_name_image_summary, "review_rows")
        actions.append(
            _action(
                priority=45,
                workstream="ichiban_kuji_prize_name_image_review",
                public_report="data/ichiban_kuji_prize_name_image_review_public.json",
                status="manual_review" if kuji_name_image_review_rows else "clear",
                rows=kuji_name_image_review_rows,
                command=(
                    "Review Ichiban Kuji campaign title, prize rank, prize item name, variant detail, and image identity against official lineup pages."
                ),
                next_step="confirm_prize_name_components_and_image_identity",
                blocker="Official lineup evidence is required before mutating prize display names or replacing images.",
                evidence={
                    "kuji_rows": _count(kuji_name_image_summary, "kuji_rows"),
                    "review_rows": kuji_name_image_review_rows,
                    "name_structure_review_rows": _count(
                        kuji_name_image_summary, "name_structure_review_rows"
                    ),
                    "image_identity_review_rows": _count(
                        kuji_name_image_summary, "image_identity_review_rows"
                    ),
                    "same_campaign_prize_rank_name_duplicate_rows": _count(
                        kuji_name_image_summary, "same_campaign_prize_rank_name_duplicate_rows"
                    ),
                    "same_campaign_image_reused_different_name_rows": _count(
                        kuji_name_image_summary, "same_campaign_image_reused_different_name_rows"
                    ),
                    "multi_item_prize_rank_groups": _count(
                        kuji_name_image_summary, "multi_item_prize_rank_groups"
                    ),
                    "multi_item_prize_rank_catalog_rows": _count(
                        kuji_name_image_summary, "multi_item_prize_rank_catalog_rows"
                    ),
                    "review_reason_counts": kuji_name_image_summary.get("review_reason_counts", []),
                },
            )
        )

    if kuji_name_image_patch_summary:
        candidate_rows = _count(kuji_name_image_patch_summary, "candidate_rows")
        actions.append(
            _action(
                priority=46,
                workstream="ichiban_kuji_prize_name_image_patch_candidates",
                public_report="data/ichiban_kuji_prize_name_image_patch_candidates_public.json",
                status="manual_review" if candidate_rows else "clear",
                rows=candidate_rows,
                command="Manual-confirm exact official 1kuji name/image patch candidates before catalog mutation.",
                next_step="mark_exact_candidates_manual_confirmed_then_import",
                blocker="Auto-apply is disabled; exact-image matches still need human confirmation before catalog writes.",
                evidence={
                    "review_rows": _count(kuji_name_image_patch_summary, "review_rows"),
                    "candidate_rows": candidate_rows,
                    "exact_image_match_rows": _count(kuji_name_image_patch_summary, "exact_image_match_rows"),
                    "strong_name_match_rows": _count(kuji_name_image_patch_summary, "strong_name_match_rows"),
                    "blocked_rows": _count(kuji_name_image_patch_summary, "blocked_rows"),
                    "fetch_failure_urls": _count(kuji_name_image_patch_summary, "fetch_failure_urls"),
                },
            )
        )

    actions.append(
        _action(
            priority=50,
            workstream="deduplication_review",
            public_report="data/catalog_deduplication_review_batches_public.json",
            status="manual_review",
            rows=_count(dedupe_summary, "source_groups"),
            command="Review duplicate groups and record explicit keep/drop decisions before deletion.",
            next_step="compare_duplicate_group_evidence",
            blocker="auto_delete_enabled is false; variant risk requires manual decisions.",
            evidence={
                "duplicate_groups": _count(dedupe_catalog_summary, "duplicate_groups"),
                "duplicate_rows": _count(dedupe_catalog_summary, "duplicate_rows"),
                "published_groups": _count(dedupe_catalog_summary, "published_groups"),
                "by_key_type": dedupe_catalog_summary.get("by_key_type", []),
                "by_review_risk": dedupe_catalog_summary.get("by_review_risk", []),
                "top_review_risk": dedupe_catalog_summary.get("top_review_risk"),
                "batch_count": _count(dedupe_summary, "batch_count"),
                "by_review_confidence": dedupe_summary.get("by_review_confidence", []),
            },
        )
    )

    actions.append(
        _action(
            priority=51,
            workstream="deduplication_action_queue",
            public_report="data/catalog_deduplication_action_queue_public.json",
            status="manual_review",
            rows=_count(dedupe_action_summary, "queued_groups"),
            command="Review high/medium-confidence duplicate groups before variant-risk dedupe work.",
            next_step="record_manual_keep_drop_decisions_for_safe_dedupe_groups",
            blocker="Auto-merge and auto-delete remain disabled; every group needs explicit confirmation.",
            evidence={
                "actionable_groups": _count(dedupe_action_summary, "actionable_groups"),
                "queued_groups": _count(dedupe_action_summary, "queued_groups"),
                "unqueued_actionable_groups": _count(
                    dedupe_action_summary, "unqueued_actionable_groups"
                ),
                "queue_coverage": dedupe_action_summary.get("queue_coverage"),
                "action_batch_count": _count(dedupe_action_summary, "action_batch_count"),
                "by_key_type": dedupe_action_summary.get("by_key_type", []),
                "by_review_confidence": dedupe_action_summary.get("by_review_confidence", []),
                "by_merge_blocker": dedupe_action_summary.get("by_merge_blocker", []),
                "by_manual_review_required_reason": dedupe_action_summary.get(
                    "by_manual_review_required_reason", []
                ),
                "excluded_review_confidence": dedupe_action_summary.get("excluded_review_confidence", []),
                "completion_readiness_status": dedupe_action_summary.get(
                    "completion_readiness_status"
                ),
                "completion_readiness": dedupe_completion,
                "auto_merge_ready_groups": _count(
                    dedupe_action_summary, "auto_merge_ready_groups"
                ),
                "auto_delete_ready_groups": _count(
                    dedupe_action_summary, "auto_delete_ready_groups"
                ),
                "explicit_keep_drop_required_groups": _count(
                    dedupe_action_summary, "explicit_keep_drop_required_groups"
                ),
                "template_manual_confirmed_rows": _count(
                    dedupe_template_import_summary, "manual_confirmed_rows"
                ),
                "template_ready_decision_rows": _count(
                    dedupe_template_import_summary, "ready_decision_rows"
                ),
                "template_blocked_rows": _count(
                    dedupe_template_import_summary, "blocked_rows"
                ),
                "template_skip_reason_counts": dedupe_template_import_summary.get(
                    "skip_reason_counts", []
                ),
                "template_write_enabled": bool(
                    dedupe_template_import_summary.get("write", False)
                ),
                "ichiban_reissue_review_groups": _count(
                    dedupe_action_summary, "ichiban_reissue_review_groups"
                ),
                "ichiban_reissue_review_rows": _count(
                    dedupe_action_summary, "ichiban_reissue_review_rows"
                ),
                "ichiban_probable_reissue_review_groups": _count(
                    dedupe_action_summary, "ichiban_probable_reissue_review_groups"
                ),
                "ichiban_probable_reissue_sample_rows": _count(
                    dedupe_action_summary, "ichiban_probable_reissue_sample_rows"
                ),
                "ichiban_reissue_protected_groups": _count(
                    dedupe_action_summary, "ichiban_reissue_protected_groups"
                ),
                "ichiban_reissue_protected_rows": _count(
                    dedupe_action_summary, "ichiban_reissue_protected_rows"
                ),
                "fast_review_groups": _count(dedupe_fast_summary, "fast_review_groups"),
                "fast_review_same_barcode_groups": _count(dedupe_fast_summary, "same_barcode_groups"),
                "fast_review_same_source_url_groups": _count(dedupe_fast_summary, "same_source_url_groups"),
                "fast_review_same_image_url_groups": _count(dedupe_fast_summary, "same_image_url_groups"),
                "fast_review_manual_confirmed_true": _count(
                    dedupe_fast_summary, "manual_confirmed_true"
                ),
                "fast_review_variant_warning_groups": _count(
                    dedupe_fast_summary, "variant_warning_groups"
                ),
                "fast_review_lanes": dedupe_fast_breakdowns.get("by_fast_review_lane", []),
            },
        )
    )

    actions.append(
        _action(
            priority=52,
            workstream="ichiban_kuji_reissue_dedupe_review",
            public_report="data/ichiban_kuji_reissue_decision_template_public.json",
            status="manual_review",
            rows=_count(dedupe_action_summary, "ichiban_reissue_review_groups"),
            command="Verify same-name Ichiban Kuji rows against campaign pages before any dedupe decision.",
            next_step="fill_ichiban_reissue_decision_template_before_dedupe",
            blocker="Same display names can be re-releases or campaign-specific prizes; do not merge until official campaign evidence is checked.",
            evidence={
                "ichiban_reissue_review_groups": _count(
                    dedupe_action_summary, "ichiban_reissue_review_groups"
                ),
                "ichiban_reissue_review_rows": _count(
                    dedupe_action_summary, "ichiban_reissue_review_rows"
                ),
                "ichiban_probable_reissue_review_groups": _count(
                    dedupe_action_summary, "ichiban_probable_reissue_review_groups"
                ),
                "ichiban_probable_reissue_sample_rows": _count(
                    dedupe_action_summary, "ichiban_probable_reissue_sample_rows"
                ),
                "ichiban_reissue_work_order_rows": _count(
                    dedupe_action_summary, "ichiban_reissue_work_order_rows"
                ),
                "ichiban_reissue_decision_template_rows": _count(
                    dedupe_action_summary, "ichiban_reissue_decision_template_rows"
                ),
                "ichiban_reissue_manual_confirmed_rows": _count(
                    dedupe_action_summary, "ichiban_reissue_manual_confirmed_rows"
                ),
                "ichiban_reissue_decision_template_report": (
                    "data/ichiban_kuji_reissue_decision_template_public.json"
                ),
                "ichiban_reissue_item_template_rows": _count(
                    kuji_reissue_decision_template_summary, "item_template_rows"
                ),
                "ichiban_reissue_campaign_template_rows": _count(
                    kuji_reissue_decision_template_summary, "campaign_template_rows"
                ),
                "ichiban_reissue_template_manual_confirmed_item_rows": _count(
                    kuji_reissue_decision_template_summary, "manual_confirmed_item_rows"
                ),
                "ichiban_reissue_template_manual_confirmed_campaign_rows": _count(
                    kuji_reissue_decision_template_summary, "manual_confirmed_campaign_rows"
                ),
                "ichiban_reissue_protected_groups": _count(
                    dedupe_action_summary, "ichiban_reissue_protected_groups"
                ),
                "ichiban_reissue_protected_rows": _count(
                    dedupe_action_summary, "ichiban_reissue_protected_rows"
                ),
            },
        )
    )

    actions.append(
        _action(
            priority=60,
            workstream="ichiban_kuji_metadata",
            public_report="data/ichiban_kuji_metadata_review_batches_public.json",
            status="manual_review",
            rows=_count(kuji_summary, "catalog_item_rows"),
            command="Verify official 1kuji campaign pages before applying release dates or prices.",
            next_step="review_batched_1kuji_campaign_metadata",
            blocker="Old campaign date/price gaps remain blocked without labeled official evidence.",
            evidence={
                "batch_count": _count(kuji_summary, "batch_count"),
                "source_campaigns": _count(kuji_summary, "source_campaigns"),
                "campaign_rows": _count(kuji_history_summary, "campaign_rows"),
                "campaigns_without_catalog_items": _count(
                    kuji_history_summary, "campaigns_without_catalog_items"
                ),
                "missing_release_date_rows": _count(
                    kuji_history_summary, "missing_release_date_rows"
                ),
                "missing_official_price_jpy_rows": _count(
                    kuji_history_summary, "missing_official_price_jpy_rows"
                ),
                "campaign_metadata_review_queue_rows": _count(
                    kuji_history_summary, "campaign_metadata_review_queue_rows"
                ),
            },
        )
    )

    actions.append(
        _action(
            priority=61,
            workstream="ichiban_kuji_metadata_action_queue",
            public_report="data/ichiban_kuji_metadata_action_queue_public.json",
            status="manual_review",
            rows=_count(kuji_action_summary, "queued_action_campaigns"),
            command="Confirm labeled official 1kuji release dates and prices, then fill campaign patch templates.",
            next_step="fill_confirmed_ichiban_campaign_patch_templates",
            blocker="Historical 1kuji metadata is manual-only until official campaign evidence is confirmed.",
            evidence={
                "historical_readiness_status": kuji_historical_readiness.get("status"),
                "historical_next_safe_phase": kuji_historical_readiness.get(
                    "next_safe_phase"
                ),
                "metadata_resolution_readiness_status": kuji_history_summary.get(
                    "metadata_resolution_readiness_status"
                ),
                "metadata_manual_review_campaigns": _count(
                    kuji_history_summary, "metadata_manual_review_campaigns"
                ),
                "metadata_auto_apply_ready_campaigns": _count(
                    kuji_history_summary, "metadata_auto_apply_ready_campaigns"
                ),
                "metadata_review_queue_covers_all_price_campaign_groups": bool(
                    kuji_history_summary.get(
                        "metadata_review_queue_covers_all_price_campaign_groups"
                    )
                ),
                "actionable_campaigns": _count(kuji_action_summary, "actionable_campaigns"),
                "queued_action_campaigns": _count(kuji_action_summary, "queued_action_campaigns"),
                "unqueued_action_campaigns": _count(
                    kuji_action_summary, "unqueued_action_campaigns"
                ),
                "campaign_queue_coverage": kuji_action_summary.get(
                    "campaign_queue_coverage"
                ),
                "queued_catalog_item_rows": _count(kuji_action_summary, "queued_catalog_item_rows"),
                "missing_release_date_campaign_groups": _count(
                    kuji_history_summary, "missing_release_date_campaign_groups"
                ),
                "missing_official_price_jpy_campaign_groups": _count(
                    kuji_history_summary, "missing_official_price_jpy_campaign_groups"
                ),
                "official_price_jpy_review_queue_campaigns": _count(
                    kuji_history_summary, "official_price_jpy_review_queue_campaigns"
                ),
                "avg_missing_price_rows_per_campaign_group": kuji_history_summary.get(
                    "avg_missing_price_rows_per_campaign_group"
                ),
                "action_batch_count": _count(kuji_action_summary, "action_batch_count"),
                "field_patch_template_count": _count(
                    kuji_action_summary, "field_patch_template_count"
                ),
                "field_patch_template_counts": kuji_action_summary.get("field_patch_template_counts", []),
                "primary_review_url_rows": _count(
                    kuji_action_summary, "primary_review_url_rows"
                ),
                "queued_primary_review_url_rows": _count(
                    kuji_action_summary, "queued_primary_review_url_rows"
                ),
                "first_primary_review_url": kuji_action_summary.get(
                    "first_primary_review_url"
                ),
                "fast_review_campaigns": _count(
                    kuji_metadata_fast_summary, "fast_review_campaigns"
                ),
                "held_for_later_campaigns": _count(
                    kuji_metadata_fast_summary, "held_for_later_campaigns"
                ),
                "fast_review_template_rows": _count(
                    kuji_metadata_fast_summary, "fast_review_template_rows"
                ),
                "fast_review_manual_confirmed_true": _count(
                    kuji_metadata_fast_summary, "manual_confirmed_true"
                ),
                "work_order_steps": _count(kuji_action_summary, "work_order_steps"),
                "work_order_lanes": kuji_action_summary.get("work_order_lanes", []),
            },
        )
    )

    kuji_price_violation_rows = _count(kuji_policy_summary, "last_one_nonzero_price_rows")
    kuji_price_violation_rows += _count(kuji_policy_summary, "last_one_missing_price_rows")
    kuji_price_violation_rows += _count(kuji_policy_summary, "double_chance_nonzero_price_rows")
    kuji_price_violation_rows += _count(kuji_policy_summary, "double_chance_missing_price_rows")
    kuji_variant_total_groups = _count(kuji_policy_summary, "multi_item_prize_label_groups")
    kuji_variant_review_rows = _count(kuji_policy_summary, "multi_item_prize_label_manual_review_groups")
    if "multi_item_prize_label_manual_review_groups" not in kuji_policy_summary:
        kuji_variant_review_rows = kuji_variant_total_groups
    kuji_numbered_variant_complete_groups = _count(
        kuji_policy_summary,
        "numbered_variant_complete_prize_label_groups",
    )
    kuji_incomplete_numbered_variant_rows = _count(
        kuji_policy_summary, "incomplete_numbered_variant_prize_label_groups"
    )
    kuji_reissue_review_rows = _count(kuji_policy_summary, "repeated_name_different_source_groups")
    kuji_probable_reissue_review_rows = _count(kuji_policy_summary, "probable_reissue_review_groups")
    if (
        kuji_price_violation_rows
        or kuji_variant_review_rows
        or kuji_incomplete_numbered_variant_rows
        or kuji_reissue_review_rows
    ):
        actions.append(
            _action(
                priority=62,
                workstream="ichiban_kuji_prize_policy_audit",
                public_report="data/ichiban_kuji_prize_policy_audit_public.json",
                status="manual_review",
                rows=kuji_price_violation_rows
                or (kuji_incomplete_numbered_variant_rows + kuji_variant_review_rows + kuji_reissue_review_rows),
                command=(
                    "Apply confirmed last-one/double-chance zero-price fixes first; then review numbered variant coverage, multi-variant prize labels, and reissue duplicate candidates."
                ),
                next_step="review_ichiban_price_exceptions_then_numbered_variants_and_reissue_groups",
                blocker=None
                if kuji_price_violation_rows
                else "No zero-price violations remain; numbered variant, variant, and reissue groups still need official campaign review before mutation.",
                evidence={
                    "kuji_rows": _count(kuji_policy_summary, "kuji_rows"),
                    "zero_price_exception_policy_pass": bool(
                        kuji_policy_summary.get("zero_price_exception_policy_pass")
                    ),
                    "numbered_variant_coverage_policy_pass": bool(
                        kuji_policy_summary.get("numbered_variant_coverage_policy_pass")
                    ),
                    "numbered_variant_application_write": bool(
                        kuji_policy_summary.get("numbered_variant_application_write")
                    ),
                    "numbered_variant_source_prizes_considered": _count(
                        kuji_policy_summary, "numbered_variant_source_prizes_considered"
                    ),
                    "numbered_variant_applied_prizes": _count(
                        kuji_policy_summary, "numbered_variant_applied_prizes"
                    ),
                    "numbered_variant_updated_existing_rows": _count(
                        kuji_policy_summary, "numbered_variant_updated_existing_rows"
                    ),
                    "numbered_variant_created_rows": _count(
                        kuji_policy_summary, "numbered_variant_created_rows"
                    ),
                    "numbered_variant_application_skipped_rows": _count(
                        kuji_policy_summary, "numbered_variant_application_skipped_rows"
                    ),
                    "last_one_rows": _count(kuji_policy_summary, "last_one_rows"),
                    "last_one_nonzero_price_rows": _count(
                        kuji_policy_summary, "last_one_nonzero_price_rows"
                    ),
                    "last_one_missing_price_rows": _count(
                        kuji_policy_summary, "last_one_missing_price_rows"
                    ),
                    "double_chance_rows": _count(kuji_policy_summary, "double_chance_rows"),
                    "double_chance_nonzero_price_rows": _count(
                        kuji_policy_summary, "double_chance_nonzero_price_rows"
                    ),
                    "double_chance_missing_price_rows": _count(
                        kuji_policy_summary, "double_chance_missing_price_rows"
                    ),
                    "multi_item_prize_label_groups": kuji_variant_total_groups,
                    "multi_item_prize_label_manual_review_groups": kuji_variant_review_rows,
                    "numbered_variant_complete_prize_label_groups": kuji_numbered_variant_complete_groups,
                    "multi_item_prize_label_review_batch_count": _count(
                        kuji_policy_summary, "multi_item_prize_label_review_batch_count"
                    ),
                    "multi_item_prize_label_review_catalog_item_rows": _count(
                        kuji_policy_summary, "multi_item_prize_label_review_catalog_item_rows"
                    ),
                    "numbered_variant_prize_label_groups": _count(
                        kuji_policy_summary, "numbered_variant_prize_label_groups"
                    ),
                    "incomplete_numbered_variant_prize_label_groups": kuji_incomplete_numbered_variant_rows,
                    "repeated_name_different_source_groups": kuji_reissue_review_rows,
                    "repeated_name_different_source_review_batch_count": _count(
                        kuji_policy_summary, "repeated_name_different_source_review_batch_count"
                    ),
                    "repeated_name_different_source_review_catalog_item_rows": _count(
                        kuji_policy_summary, "repeated_name_different_source_review_catalog_item_rows"
                    ),
                    "probable_reissue_review_groups": kuji_probable_reissue_review_rows,
                    "probable_reissue_work_order_rows": _count(
                        kuji_policy_issue_summary, "probable_reissue_work_order_rows"
                    ),
                    "campaign_first_review_plan_rows": _count(
                        kuji_policy_issue_summary, "campaign_first_review_plan_rows"
                    ),
                    "campaign_first_review_item_work_order_rows": _count(
                        kuji_policy_issue_summary,
                        "campaign_first_review_item_work_order_rows",
                    ),
                    "campaign_first_review_plans_with_evidence_urls": _count(
                        kuji_policy_issue_summary,
                        "campaign_first_review_plans_with_evidence_urls",
                    ),
                    "campaign_first_review_first_evidence_url": kuji_policy_issue_summary.get(
                        "campaign_first_review_first_evidence_url"
                    ),
                    "issue_queue_rows": _count(kuji_policy_issue_summary, "issue_rows"),
                    "open_issue_rows": _count(kuji_policy_issue_summary, "open_issue_rows"),
                    "manual_review_rows": _count(kuji_policy_issue_summary, "manual_review_rows"),
                    "manual_confirmed_rows": _count(kuji_policy_issue_summary, "manual_confirmed_rows"),
                    "auto_apply_ready_rows": _count(kuji_policy_issue_summary, "auto_apply_ready_rows"),
                    "protected_unnumbered_multi_item_prize_groups": _count(
                        kuji_policy_issue_summary,
                        "protected_unnumbered_multi_item_prize_groups",
                    ),
                    "protected_unnumbered_multi_item_prize_rows": _count(
                        kuji_policy_issue_summary,
                        "protected_unnumbered_multi_item_prize_rows",
                    ),
                    "completion_readiness_status": kuji_policy_issue_summary.get(
                        "completion_readiness_status"
                    ),
                    "completion_readiness": kuji_policy_issue_queue.get("completion_readiness", {}),
                    "historical_roadmap_completion_readiness": kuji_historical_readiness,
                    "auto_merge_enabled": bool(kuji_policy_issue_summary.get("auto_merge_enabled", False)),
                    "auto_delete_enabled": bool(kuji_policy_issue_summary.get("auto_delete_enabled", False)),
                    "prize_policy_review_batch_count": _count(
                        kuji_policy_summary, "prize_policy_review_batch_count"
                    ),
                },
            )
        )

    actions.append(
        _action(
            priority=70,
            workstream="animation_category_review",
            public_report="data/animation_category_review_batches_public.json",
            status="manual_review",
            rows=_count(animation_summary, "source_rows"),
            command="Map unknown animation categories to reviewed app folder visual tokens.",
            next_step="apply_reviewed_category_and_folder_visual_mappings",
            blocker="Category changes can affect app navigation and must be reviewed.",
            evidence={
                "batch_count": _count(animation_summary, "batch_count"),
                "unknown_category_rows": _count(animation_goods_summary, "unknown_category_rows"),
                "unknown_category_count": _count(animation_goods_summary, "unknown_category_count"),
                "folder_visual_token_count": _count(animation_summary, "folder_visual_token_count"),
                "app_folder_color_count": _count(animation_goods_summary, "app_folder_color_count"),
                "app_folder_icon_option_count": _count(
                    animation_goods_summary, "app_folder_icon_option_count"
                ),
                "app_folder_palette_sorted_by_family": bool(
                    animation_goods_summary.get("app_folder_palette_sorted_by_family")
                ),
                "app_animation_visuals_covered": bool(
                    animation_goods_summary.get("app_animation_visuals_covered")
                ),
                "split_review_categories": _count(animation_split_summary, "split_review_categories"),
                "candidate_split_rules": _count(animation_split_summary, "candidate_split_rules"),
                "matched_catalog_rows": _count(animation_split_summary, "matched_catalog_rows"),
                "unmatched_catalog_rows": _count(animation_split_summary, "unmatched_catalog_rows"),
                "unmatched_keyword_candidates": _count(animation_unmatched_summary, "token_candidate_count"),
                "unmatched_keyword_product_type_candidates": animation_unmatched_product_type_candidates,
            },
        )
    )

    actions.append(
        _action(
            priority=69,
            workstream="animation_category_action_queue",
            public_report="data/animation_category_action_queue_public.json",
            status="manual_review",
            rows=max(
                _count(animation_action_summary, "queued_catalog_rows"),
                _count(animation_action_summary, "normalization_review_rows"),
            ),
            command="Confirm animation category-to-folder mapping templates before catalog mutation.",
            next_step="fill_confirmed_animation_category_mapping_templates",
            blocker="Folder/category mappings remain manual-only until sample names confirm product type.",
            evidence={
                "category_readiness_status": animation_goods_summary.get(
                    "category_readiness_status"
                ),
                "actionable_categories": _count(animation_action_summary, "actionable_categories"),
                "queued_categories": _count(animation_action_summary, "queued_categories"),
                "queued_catalog_rows": _count(animation_action_summary, "queued_catalog_rows"),
                "action_batch_count": _count(animation_action_summary, "action_batch_count"),
                "unknown_category_rows": _count(animation_goods_summary, "unknown_category_rows"),
                "normalization_review_categories": _count(
                    animation_action_summary, "normalization_review_categories"
                )
                or _count(animation_goods_summary, "normalization_review_queue_count"),
                "normalization_review_rows": _count(
                    animation_action_summary, "normalization_review_rows"
                )
                or _count(animation_goods_summary, "normalization_review_queue_rows"),
                "normalization_review_target_categories": animation_action_summary.get(
                    "normalization_review_target_categories", []
                ),
                "target_visual_token_rows": _count(
                    animation_action_summary, "target_visual_token_rows"
                ),
                "target_visual_token_catalog_rows": _count(
                    animation_action_summary, "target_visual_token_catalog_rows"
                ),
                "target_visual_palette_ordered": bool(
                    animation_action_summary.get("target_visual_palette_ordered")
                ),
                "coverage_audit_status": animation_coverage_summary.get("status"),
                "failed_check_count": _count(animation_coverage_summary, "failed_check_count"),
                "missing_visual_token_categories": _count(
                    animation_coverage_summary, "missing_visual_token_categories"
                ),
                "app_folder_color_count": _count(
                    animation_action_summary, "app_folder_color_count"
                )
                or _count(animation_goods_summary, "app_folder_color_count"),
                "app_folder_icon_option_count": _count(
                    animation_action_summary, "app_folder_icon_option_count"
                )
                or _count(
                    animation_goods_summary, "app_folder_icon_option_count"
                ),
                "app_folder_palette_sorted_by_family": bool(
                    animation_action_summary.get("app_folder_palette_sorted_by_family")
                    or animation_goods_summary.get("app_folder_palette_sorted_by_family")
                ),
                "by_suggested_family": animation_action_summary.get("by_suggested_family", []),
                "split_review_categories": _count(animation_action_summary, "split_review_categories"),
                "direct_mapping_categories": _count(animation_action_summary, "direct_mapping_categories"),
                "work_order_steps": _count(animation_action_summary, "work_order_steps"),
                "work_order_lanes": animation_action_summary.get("work_order_lanes", []),
                "split_first_blocked_categories": animation_action_summary.get(
                    "split_first_blocked_categories", []
                ),
                "candidate_split_rules": _count(animation_split_summary, "candidate_split_rules"),
                "matched_catalog_rows": _count(animation_split_summary, "matched_catalog_rows"),
                "unmatched_catalog_rows": _count(animation_split_summary, "unmatched_catalog_rows"),
                "unmatched_keyword_candidates": _count(animation_unmatched_summary, "token_candidate_count"),
                "unmatched_keyword_product_type_candidates": animation_unmatched_product_type_candidates,
                "auto_apply_enabled": bool(
                    animation_action_summary.get("auto_apply_enabled", False)
                ),
            },
        )
    )

    actions = [action for action in actions if int(action.get("rows") or 0) > 0]
    actions.sort(key=lambda row: (int(row["priority"]), str(row["workstream"])))
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "public_catalog_cleanup_execution_plan",
        "summary": {
            "action_count": len(actions),
            "blocked_action_count": sum(1 for action in actions if action["status"] == "blocked"),
            "manual_review_action_count": sum(1 for action in actions if action["status"] == "manual_review"),
            "pending_import_action_count": sum(1 for action in actions if action["status"] == "pending_import"),
            "total_action_rows": sum(int(action.get("rows") or 0) for action in actions),
            "open_review_queues": open_queues,
            "confirmed_import_template_rows": template_items,
            "confirmed_import_action_queue_rows": public_action_queue_rows,
            "confirmed_import_action_queue_batches": public_action_queue_batches,
            "confirmed_import_pending_rows": pending_import_rows,
            "confirmed_import_manual_confirmed_ready_rows": manual_confirmed_ready_rows,
            "confirmed_import_manual_confirmation_backlog_rows": manual_confirmation_backlog_rows,
            "confirmed_import_blocked_confirmed_rows": blocked_confirmed_rows,
            "confirmed_import_workflow_count": _count(confirmed_summary, "workflow_count"),
            "confirmed_import_work_order_lanes": _count(
                confirmed_summary, "work_order_lanes"
            ),
            "confirmed_import_top_work_order_row_count": _count(
                confirmed_summary, "top_work_order_row_count"
            ),
            "confirmed_import_top_work_order_lane": confirmed_summary.get(
                "top_work_order_lane"
            ),
            "confirmed_import_top_work_order_workflow": confirmed_summary.get(
                "top_work_order_workflow"
            ),
            "requested_focus_actionable_template_rows": requested_actionable_template_rows,
            "requested_focus_barcode_template_rows": requested_barcode_template_rows,
            "danganronpa_missing_media_rows": _count(danganronpa_media_summary, "missing_media_rows"),
            "danganronpa_missing_image_url_rows": _count(danganronpa_media_summary, "missing_image_url_rows"),
            "danganronpa_missing_source_url_rows": _count(
                danganronpa_media_summary, "missing_source_url_rows"
            ),
            "danganronpa_missing_media_review_batch_count": _count(
                danganronpa_media_summary, "review_batch_count"
            ),
            "danganronpa_official_search_rows": _count(danganronpa_media_summary, "official_search_rows"),
            "danganronpa_licensed_retailer_review_rows": _count(
                danganronpa_media_summary, "licensed_retailer_review_rows"
            ),
            "danganronpa_official_prize_search_rows": _count(
                danganronpa_media_summary, "official_prize_search_rows"
            ),
            "ichiban_campaign_rows": _count(kuji_history_summary, "campaign_rows"),
            "ichiban_catalog_kuji_item_rows": _count(kuji_history_summary, "catalog_kuji_item_rows"),
            "ichiban_campaigns_with_catalog_items": _count(
                kuji_history_summary, "campaigns_with_catalog_items"
            ),
            "ichiban_campaigns_without_catalog_items": _count(
                kuji_history_summary, "campaigns_without_catalog_items"
            ),
            "ichiban_campaign_metadata_review_queue_rows": _count(
                kuji_history_summary, "campaign_metadata_review_queue_rows"
            ),
            "ichiban_historical_readiness_status": kuji_historical_readiness.get(
                "status"
            ),
            "ichiban_historical_next_safe_phase": kuji_historical_readiness.get(
                "next_safe_phase"
            ),
            "ichiban_metadata_manual_review_campaigns": _count(
                kuji_history_summary, "metadata_manual_review_campaigns"
            ),
            "ichiban_metadata_auto_apply_ready_campaigns": _count(
                kuji_history_summary, "metadata_auto_apply_ready_campaigns"
            ),
            "ichiban_metadata_actionable_campaigns": _count(
                kuji_action_summary, "actionable_campaigns"
            ),
            "ichiban_metadata_queued_action_campaigns": _count(
                kuji_action_summary, "queued_action_campaigns"
            ),
            "ichiban_metadata_fast_review_campaigns": _count(
                kuji_metadata_fast_summary, "fast_review_campaigns"
            ),
            "ichiban_metadata_fast_review_manual_confirmed_true": _count(
                kuji_metadata_fast_summary, "manual_confirmed_true"
            ),
            "ichiban_missing_release_date_campaign_groups": _count(
                kuji_history_summary, "missing_release_date_campaign_groups"
            ),
            "ichiban_missing_official_price_jpy_campaign_groups": _count(
                kuji_history_summary, "missing_official_price_jpy_campaign_groups"
            ),
            "ichiban_zero_price_exception_policy_pass": bool(
                kuji_policy_summary.get("zero_price_exception_policy_pass")
            ),
            "ichiban_multi_item_prize_label_groups": kuji_variant_total_groups,
            "ichiban_multi_item_prize_label_manual_review_groups": kuji_variant_review_rows,
            "ichiban_numbered_variant_complete_prize_label_groups": kuji_numbered_variant_complete_groups,
            "ichiban_prize_policy_review_batch_count": _count(
                kuji_policy_summary, "prize_policy_review_batch_count"
            ),
            "ichiban_incomplete_numbered_variant_prize_label_groups": kuji_incomplete_numbered_variant_rows,
            "ichiban_numbered_variant_created_rows": _count(kuji_policy_summary, "numbered_variant_created_rows"),
            "ichiban_numbered_variant_application_skipped_rows": _count(
                kuji_policy_summary, "numbered_variant_application_skipped_rows"
            ),
            "ichiban_reissue_duplicate_review_groups": kuji_reissue_review_rows,
            "ichiban_probable_reissue_review_groups": kuji_probable_reissue_review_rows,
            "ichiban_probable_reissue_work_order_rows": _count(
                kuji_policy_issue_summary, "probable_reissue_work_order_rows"
            ),
            "ichiban_campaign_first_review_plan_rows": _count(
                kuji_policy_issue_summary, "campaign_first_review_plan_rows"
            ),
            "ichiban_prize_name_image_review_rows": _count(kuji_name_image_summary, "review_rows"),
            "ichiban_prize_name_image_name_structure_review_rows": _count(
                kuji_name_image_summary, "name_structure_review_rows"
            ),
            "ichiban_prize_name_image_image_identity_review_rows": _count(
                kuji_name_image_summary, "image_identity_review_rows"
            ),
            "ichiban_prize_name_image_multi_item_groups": _count(
                kuji_name_image_summary, "multi_item_prize_rank_groups"
            ),
            "ichiban_prize_name_image_patch_candidate_rows": _count(
                kuji_name_image_patch_summary, "candidate_rows"
            ),
            "ichiban_prize_name_image_patch_blocked_rows": _count(
                kuji_name_image_patch_summary, "blocked_rows"
            ),
            "dedupe_fast_review_groups": _count(dedupe_fast_summary, "fast_review_groups"),
            "dedupe_duplicate_groups": _count(dedupe_catalog_summary, "duplicate_groups"),
            "dedupe_duplicate_rows": _count(dedupe_catalog_summary, "duplicate_rows"),
            "dedupe_actionable_groups": _count(dedupe_action_summary, "actionable_groups"),
            "dedupe_queued_groups": _count(dedupe_action_summary, "queued_groups"),
            "dedupe_auto_merge_ready_groups": _count(
                dedupe_action_summary, "auto_merge_ready_groups"
            ),
            "dedupe_auto_delete_ready_groups": _count(
                dedupe_action_summary, "auto_delete_ready_groups"
            ),
            "dedupe_template_blocked_rows": _count(
                dedupe_template_import_summary, "blocked_rows"
            ),
            "dedupe_template_ready_decision_rows": _count(
                dedupe_template_import_summary, "ready_decision_rows"
            ),
            "dedupe_fast_review_same_source_url_groups": _count(
                dedupe_fast_summary, "same_source_url_groups"
            ),
            "dedupe_ichiban_reissue_review_groups": _count(
                dedupe_action_summary, "ichiban_reissue_review_groups"
            ),
            "dedupe_ichiban_probable_reissue_review_groups": _count(
                dedupe_action_summary, "ichiban_probable_reissue_review_groups"
            ),
            "dedupe_ichiban_reissue_work_order_rows": _count(
                dedupe_action_summary, "ichiban_reissue_work_order_rows"
            ),
            "dedupe_ichiban_reissue_decision_template_rows": _count(
                dedupe_action_summary, "ichiban_reissue_decision_template_rows"
            ),
            "dedupe_ichiban_reissue_manual_confirmed_rows": _count(
                dedupe_action_summary, "ichiban_reissue_manual_confirmed_rows"
            ),
            "image_action_source_url_update_required_rows": _count(
                image_action_summary, "source_url_update_required_rows"
            ),
            "image_candidate_provider_items": _count(image_candidate_summary, "provider_candidate_items"),
            "image_candidate_manual_or_blocked_items": _count(
                image_candidate_summary, "manual_or_blocked_items"
            ),
            "image_action_source_url_update_template_rows": _count(
                image_action_summary, "source_url_update_template_rows"
            ),
            "image_action_source_url_update_template_batch_count": _count(
                image_action_summary, "source_url_update_template_batch_count"
            ),
            "image_action_image_url_ready_rows": _count(image_action_summary, "image_url_ready_rows"),
            "image_action_workstream_count": _count(image_action_summary, "workstream_count"),
            "image_known_asset_status": image_asset_summary.get("status"),
            "image_download_readiness_status": image_asset_summary.get(
                "download_readiness_status"
            ),
            "image_url_without_local_path_rows": _count(
                image_asset_summary, "image_url_without_local_path_rows"
            ),
            "image_missing_local_image_files": _count(
                image_asset_summary, "missing_local_image_files"
            ),
            "image_rows_still_requiring_url_evidence": _count(
                image_asset_summary, "rows_still_requiring_image_url_evidence"
            ),
            "image_auto_download_ready_rows": _count(
                image_asset_summary, "auto_download_ready_rows"
            ),
            "image_attachment_template_rows": _count(
                image_actionability_summary, "image_attachment_template_rows"
            ),
            "image_attachment_template_confirmed_rows": _count(
                image_actionability_summary, "image_attachment_template_confirmed_rows"
            ),
            "image_attachment_template_dry_run_skipped_rows": _count(
                image_actionability_summary,
                "image_attachment_template_dry_run_skipped_rows",
            ),
            "source_focus_template_rows": _count(source_focus_template_summary, "template_items"),
            "source_focus_template_work_order_pack_count": _count(
                source_focus_template_summary, "work_order_pack_count"
            ),
            "source_focus_template_next_pack_rows": _count(
                source_focus_template_summary, "next_focus_pack_rows"
            ),
            "source_next_focus_detail_pack_items": _count(
                source_next_focus_detail_summary, "pack_items"
            ),
            "source_next_focus_detail_action_lane_count": _count(
                source_next_focus_detail_summary, "next_action_lane_count"
            ),
            "source_next_focus_detail_action_lanes": (
                source_next_focus_detail_summary.get("next_action_lanes") or []
            ),
            "source_next_focus_fallback_rows": _count(source_next_focus_fallback_summary, "queue_rows"),
            "source_next_focus_fallback_manual_confirmed_rows": _count(
                source_next_focus_fallback_summary, "manual_confirmed_rows"
            ),
            "source_next_focus_source_confirmation_ready_rows": _count(
                source_next_focus_fallback_summary, "source_confirmation_ready_rows"
            ),
            "source_next_focus_exact_url_review_rows": _count(
                source_next_focus_exact_url_summary, "queue_rows"
            ),
            "source_next_focus_exact_url_manual_confirmed_rows": _count(
                source_next_focus_exact_url_summary, "manual_confirmed_rows"
            ),
            "source_next_focus_identity_backfill_rows": _count(
                source_next_focus_identity_backfill_summary, "queue_rows"
            ),
            "source_next_focus_identity_candidate_review_rows": _count(
                source_next_focus_identity_candidate_summary, "queue_rows"
            ),
            "source_next_focus_identity_candidate_review_candidate_rows": _count(
                source_next_focus_identity_candidate_summary, "candidate_rows"
            ),
            "source_discovery_starter_queue_rows": _count(
                source_discovery_starter_summary, "starter_queue_rows"
            ),
            "source_discovery_starter_queue_groups": _count(
                source_discovery_starter_summary, "starter_queue_groups"
            ),
            "source_discovery_action_rows": _count(source_action_summary, "queued_source_rows"),
            "source_discovery_actionable_rows": _count(source_action_summary, "actionable_source_rows"),
            "source_discovery_template_rows": _count(
                source_action_summary, "source_discovery_template_rows"
            ),
            "source_discovery_template_batch_count": _count(
                source_action_summary, "source_discovery_template_batch_count"
            ),
            "source_discovery_unqueued_actionable_rows": _count(
                source_action_summary, "unqueued_actionable_source_rows"
            ),
            "source_discovery_manual_research_backlog_rows": _count(
                source_action_summary, "manual_research_backlog_rows"
            ),
            "animation_unknown_category_rows": _count(animation_goods_summary, "unknown_category_rows"),
            "animation_unknown_category_count": _count(animation_goods_summary, "unknown_category_count"),
            "animation_category_readiness_status": animation_goods_summary.get(
                "category_readiness_status"
            ),
            "animation_normalization_review_categories": _count(
                animation_action_summary, "normalization_review_categories"
            )
            or _count(animation_goods_summary, "normalization_review_queue_count"),
            "animation_normalization_review_rows": _count(
                animation_action_summary, "normalization_review_rows"
            )
            or _count(animation_goods_summary, "normalization_review_queue_rows"),
            "animation_coverage_audit_status": animation_coverage_summary.get("status"),
            "animation_missing_visual_token_categories": _count(
                animation_coverage_summary, "missing_visual_token_categories"
            ),
            "animation_failed_visual_check_count": _count(
                animation_coverage_summary, "failed_check_count"
            ),
            "animation_split_review_categories": _count(animation_split_summary, "split_review_categories"),
            "animation_candidate_split_rules": _count(animation_split_summary, "candidate_split_rules"),
            "animation_split_matched_catalog_rows": _count(animation_split_summary, "matched_catalog_rows"),
            "animation_split_unmatched_catalog_rows": _count(animation_split_summary, "unmatched_catalog_rows"),
            "animation_unmatched_keyword_candidates": _count(
                animation_unmatched_summary, "token_candidate_count"
            ),
            "animation_unmatched_keyword_product_type_candidates": animation_unmatched_product_type_candidates,
            "animation_app_folder_color_count": _count(animation_goods_summary, "app_folder_color_count"),
            "animation_app_folder_icon_option_count": _count(
                animation_goods_summary, "app_folder_icon_option_count"
            ),
            "animation_app_folder_palette_sorted_by_family": bool(
                animation_goods_summary.get("app_folder_palette_sorted_by_family")
            ),
            "animation_app_visuals_covered": bool(
                animation_goods_summary.get("app_animation_visuals_covered")
            ),
            "auto_apply_enabled": False,
        },
        "actions": actions,
        "instructions": [
            "Use actions in priority order to keep DB cleanup work aligned with public reports.",
            "Commands are workflow descriptions, not auto-executed mutations.",
            "Catalog writes remain disabled until exact source evidence or manual_confirmed=true rows exist.",
        ],
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
        },
    }


def build_plan_from_reports(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def load_report(name: str) -> dict[str, Any]:
        payload = reports.get(name)
        return payload if isinstance(payload, dict) else _load(name)

    return _build_plan(load_report)


def build_plan() -> dict[str, Any]:
    return _build_plan(_load)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_plan()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
