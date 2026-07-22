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
    image_action_queue = load_report("catalog_image_attachment_action_queue_public.json")
    source_batches = load_report("source_discovery_review_batches_public.json")
    source_action_queue = load_report("source_discovery_action_queue_public.json")
    source_detail_candidate_action_queue = load_report("source_detail_candidate_action_queue_public.json")
    ensky_cache_candidate_action_queue = load_report("ensky_cache_candidate_action_queue_public.json")
    metadata_batches = load_report("catalog_metadata_review_batches_public.json")
    metadata_action_queue = load_report("catalog_metadata_action_queue_public.json")
    requested_batches = load_report("requested_focus_review_batches_public.json")
    requested_action_queue = load_report("requested_focus_action_queue_public.json")
    dedupe_batches = load_report("catalog_deduplication_review_batches_public.json")
    dedupe_action_queue = load_report("catalog_deduplication_action_queue_public.json")
    dedupe_fast_review = load_report("catalog_deduplication_fast_review_public.json")
    kuji_batches = load_report("ichiban_kuji_metadata_review_batches_public.json")
    kuji_action_queue = load_report("ichiban_kuji_metadata_action_queue_public.json")
    kuji_policy = load_report("ichiban_kuji_prize_policy_audit_public.json")
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
    image_action_summary = _summary(image_action_queue)
    source_summary = _summary(source_batches)
    source_action_summary = _summary(source_action_queue)
    source_detail_candidate_action_summary = _summary(source_detail_candidate_action_queue)
    ensky_cache_candidate_action_summary = _summary(ensky_cache_candidate_action_queue)
    metadata_summary = _summary(metadata_batches)
    metadata_action_summary = _summary(metadata_action_queue)
    requested_summary = _summary(requested_batches)
    requested_action_summary = _summary(requested_action_queue)
    dedupe_summary = _summary(dedupe_batches)
    dedupe_action_summary = _summary(dedupe_action_queue)
    dedupe_fast_summary = _summary(dedupe_fast_review)
    dedupe_fast_breakdowns = dedupe_fast_review.get("breakdowns")
    if not isinstance(dedupe_fast_breakdowns, dict):
        dedupe_fast_breakdowns = {}
    kuji_summary = _summary(kuji_batches)
    kuji_action_summary = _summary(kuji_action_queue)
    kuji_policy_summary = _summary(kuji_policy)
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
                "template_items": template_items,
                "public_action_queue_rows": public_action_queue_rows,
                "public_action_queue_batches": public_action_queue_batches,
                "ready_or_pending_import_rows": pending_import_rows,
                "blocked_confirmed_rows": blocked_confirmed_rows,
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
                "excluded_review_state_rows": source_action_summary.get("excluded_review_state_rows", []),
                "by_workflow": source_action_summary.get("by_workflow", []),
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
                "source_url_ready_rows": ready_image_rows,
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
                "representative_image_review_required_rows": _count(
                    image_action_summary, "representative_image_review_required_rows"
                ),
                "image_url_ready_rows": _count(image_action_summary, "image_url_ready_rows"),
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
                "action_batch_count": _count(dedupe_action_summary, "action_batch_count"),
                "by_review_confidence": dedupe_action_summary.get("by_review_confidence", []),
                "excluded_review_confidence": dedupe_action_summary.get("excluded_review_confidence", []),
                "fast_review_groups": _count(dedupe_fast_summary, "fast_review_groups"),
                "fast_review_same_barcode_groups": _count(dedupe_fast_summary, "same_barcode_groups"),
                "fast_review_same_source_url_groups": _count(dedupe_fast_summary, "same_source_url_groups"),
                "fast_review_same_image_url_groups": _count(dedupe_fast_summary, "same_image_url_groups"),
                "fast_review_lanes": dedupe_fast_breakdowns.get("by_fast_review_lane", []),
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
                "actionable_campaigns": _count(kuji_action_summary, "actionable_campaigns"),
                "queued_action_campaigns": _count(kuji_action_summary, "queued_action_campaigns"),
                "queued_catalog_item_rows": _count(kuji_action_summary, "queued_catalog_item_rows"),
                "action_batch_count": _count(kuji_action_summary, "action_batch_count"),
                "field_patch_template_counts": kuji_action_summary.get("field_patch_template_counts", []),
            },
        )
    )

    kuji_price_violation_rows = _count(kuji_policy_summary, "last_one_nonzero_price_rows")
    kuji_price_violation_rows += _count(kuji_policy_summary, "last_one_missing_price_rows")
    kuji_price_violation_rows += _count(kuji_policy_summary, "double_chance_nonzero_price_rows")
    kuji_price_violation_rows += _count(kuji_policy_summary, "double_chance_missing_price_rows")
    kuji_variant_review_rows = _count(kuji_policy_summary, "multi_item_prize_label_groups")
    kuji_reissue_review_rows = _count(kuji_policy_summary, "repeated_name_different_source_groups")
    if kuji_price_violation_rows or kuji_variant_review_rows or kuji_reissue_review_rows:
        actions.append(
            _action(
                priority=62,
                workstream="ichiban_kuji_prize_policy_audit",
                public_report="data/ichiban_kuji_prize_policy_audit_public.json",
                status="manual_review",
                rows=kuji_price_violation_rows or (kuji_variant_review_rows + kuji_reissue_review_rows),
                command=(
                    "Apply confirmed last-one/double-chance zero-price fixes first; then review multi-variant prize labels and reissue duplicate candidates."
                ),
                next_step="review_ichiban_price_exceptions_then_variant_and_reissue_groups",
                blocker=None
                if kuji_price_violation_rows
                else "No zero-price violations remain; variant/reissue groups still need official campaign review before mutation.",
                evidence={
                    "kuji_rows": _count(kuji_policy_summary, "kuji_rows"),
                    "zero_price_exception_policy_pass": bool(
                        kuji_policy_summary.get("zero_price_exception_policy_pass")
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
                    "multi_item_prize_label_groups": kuji_variant_review_rows,
                    "repeated_name_different_source_groups": kuji_reissue_review_rows,
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
                "folder_visual_token_count": _count(animation_summary, "folder_visual_token_count"),
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
            rows=_count(animation_action_summary, "queued_catalog_rows"),
            command="Confirm animation category-to-folder mapping templates before catalog mutation.",
            next_step="fill_confirmed_animation_category_mapping_templates",
            blocker="Folder/category mappings remain manual-only until sample names confirm product type.",
            evidence={
                "actionable_categories": _count(animation_action_summary, "actionable_categories"),
                "queued_categories": _count(animation_action_summary, "queued_categories"),
                "queued_catalog_rows": _count(animation_action_summary, "queued_catalog_rows"),
                "action_batch_count": _count(animation_action_summary, "action_batch_count"),
                "by_suggested_family": animation_action_summary.get("by_suggested_family", []),
                "split_review_categories": _count(animation_action_summary, "split_review_categories"),
                "direct_mapping_categories": _count(animation_action_summary, "direct_mapping_categories"),
                "candidate_split_rules": _count(animation_split_summary, "candidate_split_rules"),
                "matched_catalog_rows": _count(animation_split_summary, "matched_catalog_rows"),
                "unmatched_catalog_rows": _count(animation_split_summary, "unmatched_catalog_rows"),
                "unmatched_keyword_candidates": _count(animation_unmatched_summary, "token_candidate_count"),
                "unmatched_keyword_product_type_candidates": animation_unmatched_product_type_candidates,
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
            "requested_focus_actionable_template_rows": requested_actionable_template_rows,
            "requested_focus_barcode_template_rows": requested_barcode_template_rows,
            "ichiban_zero_price_exception_policy_pass": bool(
                kuji_policy_summary.get("zero_price_exception_policy_pass")
            ),
            "ichiban_multi_item_prize_label_groups": kuji_variant_review_rows,
            "ichiban_reissue_duplicate_review_groups": kuji_reissue_review_rows,
            "dedupe_fast_review_groups": _count(dedupe_fast_summary, "fast_review_groups"),
            "dedupe_fast_review_same_source_url_groups": _count(
                dedupe_fast_summary, "same_source_url_groups"
            ),
            "image_action_source_url_update_required_rows": _count(
                image_action_summary, "source_url_update_required_rows"
            ),
            "image_action_image_url_ready_rows": _count(image_action_summary, "image_url_ready_rows"),
            "animation_split_review_categories": _count(animation_split_summary, "split_review_categories"),
            "animation_candidate_split_rules": _count(animation_split_summary, "candidate_split_rules"),
            "animation_split_matched_catalog_rows": _count(animation_split_summary, "matched_catalog_rows"),
            "animation_split_unmatched_catalog_rows": _count(animation_split_summary, "unmatched_catalog_rows"),
            "animation_unmatched_keyword_candidates": _count(
                animation_unmatched_summary, "token_candidate_count"
            ),
            "animation_unmatched_keyword_product_type_candidates": animation_unmatched_product_type_candidates,
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
