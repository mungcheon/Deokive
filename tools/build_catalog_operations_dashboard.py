from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DATA = ROOT / "data"
DEFAULT_JSON = SERVER / "catalog_operations_dashboard.json"
DEFAULT_MD = SERVER / "catalog_operations_dashboard.md"
DEFAULT_HTML = SERVER / "catalog_operations_dashboard.html"


SOURCES = {
    "goal": SERVER / "catalog_goal_status_current.json",
    "quality": SERVER / "catalog_quality_report.json",
    "field_batches": SERVER / "catalog_field_review_batches.json",
    "image_queue": SERVER / "catalog_image_enrichment_queue_current.json",
    "image_batch_plan": SERVER / "catalog_image_enrichment_batch_plan.json",
    "image_exact_url_queue": SERVER / "catalog_image_exact_url_work_queue.json",
    "image_path_source_review": SERVER / "image_path_source_url_review_queue.json",
    "image_auto_promotable": SERVER / "auto_promotable_image_candidates_current.json",
    "image_auto_promotable_strict_import": SERVER / "auto_promotable_image_candidates_current_import_dryrun.json",
    "image_exact_confirmed_import": SERVER / "catalog_image_exact_url_confirmed.import.json",
    "image_provider_recheck": SERVER / "catalog_missing_images_report.json",
    "web_image_search_candidates": SERVER / "web_image_search_candidates_current.json",
    "piapro_prize_image_candidates": SERVER / "piapro_prize_image_candidates_current.json",
    "agent_image_candidates": SERVER / "agent_image_candidates_import_queue_current.json",
    "agent_image_candidates_broad": SERVER / "agent_image_candidates_import_queue_broad.json",
    "image_existing_candidates": SERVER / "catalog_image_existing_candidate_consolidated.json",
    "image_existing_candidates_strict_import": SERVER / "catalog_image_existing_candidate_consolidated_strict_current_dryrun.json",
    "remaining_image_audit": SERVER / "catalog_remaining_image_enrichment_audit_current.json",
    "source_discovery": SERVER / "catalog_source_discovery_queue.json",
    "source_url_bottlenecks": SERVER / "catalog_source_url_bottleneck_audit.json",
    "source_detail_candidates": SERVER / "catalog_source_detail_candidates.json",
    "source_detail_candidate_summary": SERVER / "catalog_source_detail_candidate_summary.json",
    "image_batches": SERVER / "catalog_image_review_batches.json",
    "unapplied_image_changes": SERVER / "catalog_unapplied_image_report_changes.json",
    "image_provider": SERVER / "catalog_image_provider_coverage_audit_current.json",
    "chiikawa_gotouchi_api": SERVER / "chiikawa_gotouchi_api_coverage_audit.json",
    "taito_brand_candidates": SERVER / "taito_brand_image_candidates_current.json",
    "storefront_match_review": SERVER / "storefront_match_review_queue.json",
    "storefront_batches": SERVER / "storefront_review_batches.json",
    "fanding_stellive": SERVER / "fanding_stellive_match_queue.json",
    "official_batches": SERVER / "official_detail_review_batches.json",
    "official_detail_animate_merged": SERVER / "official_detail_match_queue_animate_after_query_fix_merged_summary.json",
    "official_detail_ensky_merged": SERVER / "official_detail_match_queue_ensky_merged_current.json",
    "ichiban_gap": SERVER / "ichiban_kuji_gap_work_queue.json",
    "ichiban_replacement_urls": SERVER / "ichiban_replacement_url_queue.json",
    "ichiban_sub_series_batches": SERVER / "ichiban_kuji_sub_series_review_batches.json",
    "ichiban_structure": SERVER / "ichiban_kuji_prize_structure_audit.json",
    "ichiban_campaign_gap_audit": SERVER / "ichiban_kuji_campaign_gap_audit.json",
    "ichiban_metadata": SERVER / "ichiban_kuji_metadata_audit.json",
    "ichiban_metadata_review": SERVER / "ichiban_kuji_metadata_review_queue.json",
    "ichiban_history_status": SERVER / "ichiban_kuji_history_status_audit.json",
    "animation_categories": SERVER / "animation_goods_category_audit.json",
    "animation_enrichment_priority": SERVER / "animation_enrichment_priority_queue.json",
    "app_folder_visuals": SERVER / "app_folder_visual_catalog_audit.json",
    "confirmed_import": SERVER / "catalog_confirmed_import_queue_audit.json",
    "confirmed_archive": SERVER / "catalog_confirmed_archive_report.json",
    "requested_special_goods": SERVER / "requested_special_goods_queue.json",
    "report_consistency": SERVER / "catalog_report_consistency_audit.json",
    "db_sync": SERVER / "catalog_db_sync_audit.json",
    "store_source_netloc": SERVER / "store_source_netloc_audit.json",
    "live_source_identity": SERVER / "live_source_identity_audit.json",
    "stale_source_cleanup": SERVER / "stale_source_cleanup_queue.json",
    "product_identity_review": SERVER / "product_identity_review_queue.json",
    "generic_source_cleanup": SERVER / "generic_source_cleanup_queue.json",
    "prize_source_store_lines": SERVER / "prize_source_store_line_audit.json",
    "prize_line_expected_provider": SERVER / "prize_line_expected_provider_queue_current.json",
    "prize_line_official_detail": SERVER / "prize_line_official_detail_match_queue_current.json",
    "prize_provider_fallback_images": SERVER / "prize_provider_fallback_image_candidates_current.json",
    "focus_missing_images": SERVER / "focus_missing_image_queue_current.json",
    "focus_series_missing_images": SERVER / "focus_series_missing_image_work_queues_current.json",
    "pokemon_center_official": SERVER / "pokemon_center_official_latest_dryrun.json",
    "public_image_actionability": DATA / "catalog_missing_image_actionability_public.json",
    "public_source_focus_packs": DATA / "source_discovery_focus_packs_public.json",
    "public_source_focus_template": DATA / "source_discovery_focus_confirmed_template_public.json",
    "public_source_focus_template_import": DATA / "source_discovery_focus_template_import_dry_run_public.json",
    "public_source_next_focus_pack": DATA / "source_discovery_next_focus_pack_public.json",
    "public_image_attachment_template": DATA / "catalog_image_attachment_confirmed_template_public.json",
    "public_image_attachment_template_import": DATA / "catalog_image_attachment_template_import_dry_run_public.json",
    "public_deduplication": DATA / "catalog_deduplication_public.json",
    "public_deduplication_action_queue": DATA / "catalog_deduplication_action_queue_public.json",
    "public_deduplication_fast_review": DATA / "catalog_deduplication_fast_review_public.json",
    "public_deduplication_confirmed_template": DATA / "catalog_deduplication_confirmed_template_public.json",
    "public_deduplication_template_import": DATA / "catalog_deduplication_template_import_dry_run_public.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _link(path: str) -> str:
    return path.replace("\\", "/")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _top(value: Any, limit: int = 5) -> list[Any]:
    return value[:limit] if isinstance(value, list) else []


def _official_detail_processed_rows(payload: dict[str, Any]) -> int:
    for key in (
        "unique_processed_seed_rows",
        "unique_target_rows_with_candidates",
        "processed_seed_rows",
        "target_items",
    ):
        try:
            value = int(payload.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value:
            return value
    return 0


def build() -> dict[str, Any]:
    data = {name: _read_json(path) for name, path in SOURCES.items()}
    goal = data["goal"]
    quality = data.get("quality", {})
    field_batches = data["field_batches"]
    image_queue = data["image_queue"]
    image_batch_plan = data.get("image_batch_plan", {})
    image_exact_url_queue = data.get("image_exact_url_queue", {})
    image_exact_identity = dict(image_exact_url_queue.get("by_identity_review") or [])
    image_path_source_review = data.get("image_path_source_review", {})
    image_path_source_summary = image_path_source_review.get("summary") or {}
    image_auto_promotable = data.get("image_auto_promotable", {})
    image_auto_promotable_strict = data.get("image_auto_promotable_strict_import", {})
    image_exact_confirmed_import = data.get("image_exact_confirmed_import", {})
    image_provider_recheck = data.get("image_provider_recheck", {})
    image_provider_recheck_summary = image_provider_recheck.get("unresolved_summary") or {}
    web_image_search = data.get("web_image_search_candidates", {})
    piapro_prize = data.get("piapro_prize_image_candidates", {})
    agent_image_candidates = data.get("agent_image_candidates", {})
    agent_image_summary = agent_image_candidates.get("summary") or {}
    agent_image_broad = data.get("agent_image_candidates_broad", {})
    agent_image_broad_summary = agent_image_broad.get("summary") or {}
    image_existing_candidates = data.get("image_existing_candidates", {})
    image_existing_summary = image_existing_candidates.get("summary") or {}
    image_existing_strict = data.get("image_existing_candidates_strict_import", {})
    remaining_image_audit = data.get("remaining_image_audit", {})
    remaining_candidate_reviews = remaining_image_audit.get("candidate_reviews") or {}
    source_discovery = data.get("source_discovery", {})
    source_discovery_summary = source_discovery.get("summary") or {}
    source_url_bottlenecks = data.get("source_url_bottlenecks", {})
    source_detail_candidates = data.get("source_detail_candidates", {})
    source_detail_summary = source_detail_candidates.get("summary") or {}
    source_detail_candidate_summary = data.get("source_detail_candidate_summary", {})
    source_detail_candidate_summary_summary = source_detail_candidate_summary.get("summary") or {}
    image_batches = data["image_batches"]
    unapplied_image_changes = data["unapplied_image_changes"]
    image_provider = data["image_provider"]
    gotouchi_api = data.get("chiikawa_gotouchi_api", {})
    taito_brand = data.get("taito_brand_candidates", {})
    storefront_match = data.get("storefront_match_review", {})
    storefront = data["storefront_batches"]
    fanding_stellive = data.get("fanding_stellive", {})
    fanding_summary = fanding_stellive.get("summary") or {}
    fanding_status_counts = fanding_summary.get("candidate_status_counts") or {}
    official = data["official_batches"]
    official_animate = data.get("official_detail_animate_merged", {})
    official_ensky = data.get("official_detail_ensky_merged", {})
    official_detail_processed = _official_detail_processed_rows(official_animate) + _official_detail_processed_rows(
        official_ensky
    )
    official_detail_reviewable = (official_animate.get("reviewable_rows") or 0) + (
        official_ensky.get("reviewable_rows") or 0
    )
    official_detail_candidates = (official_animate.get("candidate_rows") or 0) + (
        official_ensky.get("candidate_rows") or 0
    )
    ichiban_gap = data["ichiban_gap"]
    ichiban_replacement = data.get("ichiban_replacement_urls", {})
    ichiban_sub_series_batches = data["ichiban_sub_series_batches"]
    ichiban_structure = data["ichiban_structure"]
    ichiban_campaign_gap = data.get("ichiban_campaign_gap_audit", {})
    ichiban_metadata = data.get("ichiban_metadata", {})
    ichiban_metadata_review = data.get("ichiban_metadata_review", {})
    ichiban_metadata_review_summary = ichiban_metadata_review.get("summary") or {}
    ichiban_history_status = data.get("ichiban_history_status", {})
    animation = data["animation_categories"]
    animation_priority = data.get("animation_enrichment_priority", {})
    app_folder_visuals = data.get("app_folder_visuals", {})
    confirmed = data["confirmed_import"]
    archive = data["confirmed_archive"]
    requested_special = data.get("requested_special_goods", {})
    report_consistency = data.get("report_consistency", {})
    db_sync = data.get("db_sync", {})
    store_source = data.get("store_source_netloc", {})
    live_source = data.get("live_source_identity", {})
    stale_source_cleanup = data.get("stale_source_cleanup", {})
    stale_source_summary = stale_source_cleanup.get("summary") or {}
    product_identity_review = data.get("product_identity_review", {})
    product_identity_summary = product_identity_review.get("summary") or {}
    generic_source_cleanup = data.get("generic_source_cleanup", {})
    generic_source_summary = generic_source_cleanup.get("summary") or {}
    prize_source_store_lines = data.get("prize_source_store_lines", {})
    prize_source_store_summary = prize_source_store_lines.get("summary") or {}
    prize_line_expected_provider = data.get("prize_line_expected_provider", {})
    prize_line_expected_summary = prize_line_expected_provider.get("summary") or {}
    prize_line_official_detail = data.get("prize_line_official_detail", {})
    prize_provider_fallback = data.get("prize_provider_fallback_images", {})
    prize_provider_fallback_summary = prize_provider_fallback.get("summary") or {}
    focus_missing_images = data.get("focus_missing_images", {})
    focus_series_missing_images = data.get("focus_series_missing_images", {})
    pokemon_center = data.get("pokemon_center_official", {})
    public_image_actionability = data.get("public_image_actionability", {})
    public_actionability_summary = public_image_actionability.get("summary") or {}
    public_focus_packs = data.get("public_source_focus_packs", {})
    public_focus_pack_summary = public_focus_packs.get("summary") or {}
    public_focus_template = data.get("public_source_focus_template", {})
    public_focus_template_summary = public_focus_template.get("summary") or {}
    public_focus_template_import = data.get("public_source_focus_template_import", {})
    public_source_next_focus_pack = data.get("public_source_next_focus_pack", {})
    public_source_next_focus_summary = public_source_next_focus_pack.get("summary") or {}
    public_image_attachment_template = data.get("public_image_attachment_template", {})
    public_image_attachment_template_summary = public_image_attachment_template.get("summary") or {}
    public_image_attachment_template_import = data.get("public_image_attachment_template_import", {})
    public_deduplication = data.get("public_deduplication", {})
    public_deduplication_summary = public_deduplication.get("summary") or {}
    public_deduplication_action_queue = data.get("public_deduplication_action_queue", {})
    public_deduplication_action_summary = public_deduplication_action_queue.get("summary") or {}
    public_deduplication_fast_review = data.get("public_deduplication_fast_review", {})
    public_deduplication_fast_summary = public_deduplication_fast_review.get("summary") or {}
    public_deduplication_confirmed_template = data.get("public_deduplication_confirmed_template", {})
    public_deduplication_template_summary = public_deduplication_confirmed_template.get("summary") or {}
    public_deduplication_template_import = data.get("public_deduplication_template_import", {})

    workboards = [
        {
            "area": "Field backfill",
            "artifact": "server/catalog_field_review_batches.html",
            "markdown": "server/catalog_field_review_batches.md",
            "primary_metric": field_batches.get("actionable_rows"),
            "primary_label": "actionable rows",
            "secondary_metric": field_batches.get("batch_count"),
            "secondary_label": "batches",
            "status": "ready_for_review" if field_batches.get("actionable_rows") else "empty",
            "next": "Review by store/category/field; copy exact values into catalog_field_confirmed_rows.json.",
        },
        {
            "area": "Image enrichment",
            "artifact": "server/catalog_image_exact_url_work_queue.html",
            "markdown": "server/catalog_source_discovery_queue.md",
            "secondary_artifact": "server/catalog_image_enrichment_batch_plan.md",
            "primary_metric": image_queue.get("missing_images"),
            "primary_label": "missing images",
            "secondary_metric": source_discovery_summary.get("source_discovery_rows")
            or image_batch_plan.get("workstream_count")
            or image_batches.get("batch_count")
            or image_provider.get("actionable_or_provider_work_images"),
            "secondary_label": "source discovery rows",
            "status": "provider_work_needed" if image_queue.get("missing_images") else "complete",
            "next": "Find exact source URLs for no-source rows first; then attach images only from exact product pages.",
            "quick_win_metric": image_exact_url_queue.get("item_count")
            or source_detail_candidate_summary_summary.get("unique_exact_candidate_store_row_pairs")
            or source_detail_summary.get("exact_candidate_rows")
            or unapplied_image_changes.get("candidate_count"),
            "quick_win_label": "exact/detail candidate rows",
            "identity_blocked_metric": image_exact_identity.get("blocked_by_identity_review", 0),
            "identity_blocked_label": "identity-blocked rows",
            "exact_research_metric": image_exact_identity.get("exact_url_research", 0),
            "exact_research_label": "exact URL research rows",
            "auto_promotable": (image_auto_promotable.get("summary") or {}).get("candidate_items"),
            "auto_promotable_strict_updated": image_auto_promotable_strict.get("updated_rows"),
            "auto_promotable_strict_skipped": image_auto_promotable_strict.get("skipped_rows"),
            "auto_promotable_strict_reasons": image_auto_promotable_strict.get("skipped_reasons"),
            "existing_candidate_strict_updated": image_existing_strict.get("updated_rows"),
            "existing_candidate_strict_skipped": image_existing_strict.get("skipped_rows"),
            "existing_candidate_strict_reasons": image_existing_strict.get("skipped_reasons"),
            "remaining_provider_candidate_items": remaining_image_audit.get("provider_candidate_items"),
            "remaining_manual_or_blocked_items": remaining_image_audit.get("manual_or_blocked_items"),
            "remaining_candidate_review_ready": remaining_candidate_reviews.get("ready_items"),
            "remaining_candidate_review_preflight": remaining_candidate_reviews.get("preflight_passed_items"),
            "remaining_candidate_review_reasons": _top(remaining_candidate_reviews.get("rejected_reasons"), 5),
            "confirmed_import_ready": (image_exact_confirmed_import.get("summary") or {}).get("ready_items"),
            "provider_recheck_processed_metric": image_provider_recheck.get("processed_rows"),
            "provider_recheck_processed_label": "provider recheck rows",
            "provider_recheck_no_candidates_metric": _summary_count(
                image_provider_recheck_summary, "by_reason", "no_provider_candidates"
            ),
            "provider_recheck_no_candidates_label": "no-provider-candidate rows",
            "provider_recheck_rejected_metric": _summary_count(
                image_provider_recheck_summary, "by_reason", "best_candidate_rejected"
            ),
            "provider_recheck_rejected_label": "rejected best candidates",
            "provider_recheck_failed_check": _top_mapping(image_provider_recheck_summary.get("by_failed_check"), 3),
            "top_source_discovery_batches": _top(
                source_discovery_summary.get("top_official_search_store_categories"),
                5,
            ),
        },
        {
            "area": "Public image recovery",
            "artifact": "data/catalog_missing_image_actionability_public.json",
            "markdown": "data/source_discovery_focus_packs_public.json",
            "secondary_artifact": "data/source_discovery_focus_confirmed_template_public.json",
            "primary_metric": public_actionability_summary.get("missing_image_rows"),
            "primary_label": "public DB rows missing images",
            "secondary_metric": public_actionability_summary.get("source_discovery_focus_pack_rows"),
            "secondary_label": "focus-pack source rows",
            "status": "manual_source_confirmation_needed"
            if public_actionability_summary.get("source_discovery_remaining_focus_review_rows")
            else "ready_for_image_import",
            "next": "Confirm exact source URLs in the focus template first; imports stay dry-run until manual confirmation is present.",
            "quick_win_metric": public_actionability_summary.get("actionable_image_rows"),
            "quick_win_label": "image action queue rows",
            "direct_image_action_queue_rows": public_actionability_summary.get("direct_image_action_queue_rows"),
            "source_detail_candidate_review_rows": public_actionability_summary.get("source_detail_candidate_review_rows"),
            "source_detail_candidate_recheck_required_rows": public_actionability_summary.get(
                "source_detail_candidate_recheck_required_rows"
            ),
            "manual_image_research_rows": public_actionability_summary.get("manual_image_research_rows"),
            "focus_pack_count": public_focus_pack_summary.get("focus_pack_count")
            or public_actionability_summary.get("source_discovery_focus_pack_count"),
            "not_started_focus_pack_count": public_focus_pack_summary.get("not_started_focus_pack_count")
            or public_actionability_summary.get("source_discovery_not_started_focus_pack_count"),
            "remaining_focus_review_rows": public_focus_pack_summary.get("remaining_focus_review_rows")
            or public_actionability_summary.get("source_discovery_remaining_focus_review_rows"),
            "confirmed_focus_source_rows": public_focus_pack_summary.get("confirmed_focus_source_rows")
            or public_actionability_summary.get("source_discovery_confirmed_focus_source_rows"),
            "focus_coverage": public_focus_pack_summary.get("focus_coverage")
            or public_actionability_summary.get("source_discovery_focus_coverage"),
            "focus_source_stores": public_focus_pack_summary.get("focus_source_stores"),
            "template_items": public_focus_template_summary.get("template_items"),
            "template_confirmed_rows": public_focus_template_summary.get("manual_confirmed_rows")
            or public_actionability_summary.get("source_discovery_focus_template_confirmed_rows"),
            "next_focus_pack_id": public_focus_template_summary.get("next_focus_pack_id"),
            "next_source_store": public_focus_template_summary.get("next_source_store"),
            "next_target_category": public_focus_template_summary.get("next_target_category"),
            "next_focus_pack_rows": public_focus_template_summary.get("next_focus_pack_rows"),
            "next_official_search_url": public_focus_template_summary.get("next_official_search_url"),
            "work_order_pack_count": public_focus_template_summary.get("work_order_pack_count"),
            "current_focus_pack_id": public_source_next_focus_summary.get("focus_pack_id"),
            "current_focus_pack_items": public_source_next_focus_summary.get("pack_items"),
            "focus_pack_progress_queue_count": public_source_next_focus_summary.get("focus_pack_progress_queue_count"),
            "focus_pack_progress_remaining_rows": public_source_next_focus_summary.get(
                "focus_pack_progress_remaining_rows"
            ),
            "focus_pack_progress_preview": _top(
                public_source_next_focus_pack.get("focus_pack_progress_queue"),
                5,
            ),
            "template_import_updated_rows": public_focus_template_import.get("updated_rows"),
            "template_import_skipped_rows": public_focus_template_import.get("skipped_rows"),
            "template_import_skip_reason_counts": public_focus_template_import.get("skip_reason_counts"),
            "image_attachment_template_items": public_image_attachment_template_summary.get("template_items"),
            "image_attachment_template_confirmed_rows": public_image_attachment_template_summary.get(
                "manual_confirmed_rows"
            ),
            "image_attachment_template_source_update_required_rows": public_image_attachment_template_summary.get(
                "source_url_update_required_rows"
            ),
            "image_attachment_template_representative_review_rows": public_image_attachment_template_summary.get(
                "representative_image_review_required_rows"
            ),
            "image_attachment_template_import_updated_rows": public_image_attachment_template_import.get("updated_rows"),
            "image_attachment_template_import_skipped_rows": public_image_attachment_template_import.get("skipped_rows"),
            "auto_apply_enabled": public_actionability_summary.get("auto_apply_enabled"),
        },
        {
            "area": "Public deduplication",
            "artifact": "data/catalog_deduplication_public.json",
            "markdown": "data/catalog_deduplication_confirmed_template_public.json",
            "secondary_artifact": "data/catalog_deduplication_fast_review_public.json",
            "primary_metric": public_deduplication_summary.get("duplicate_groups"),
            "primary_label": "duplicate review groups",
            "secondary_metric": public_deduplication_action_summary.get("queued_groups"),
            "secondary_label": "queued action groups",
            "status": "manual_confirmation_needed"
            if public_deduplication_template_summary.get("template_items")
            else ("review_needed" if public_deduplication_summary.get("duplicate_groups") else "clean"),
            "next": "Confirm same sellable product before setting any dedupe template row to drop/merge; automatic deletion stays disabled.",
            "quick_win_metric": public_deduplication_fast_summary.get("fast_review_groups"),
            "quick_win_label": "fast-review groups",
            "template_items": public_deduplication_template_summary.get("template_items"),
            "template_manual_confirmed_rows": public_deduplication_template_summary.get("manual_confirmed_rows"),
            "template_same_sellable_product_confirmed_rows": public_deduplication_template_summary.get(
                "same_sellable_product_confirmed_rows"
            ),
            "template_drop_candidate_rows": public_deduplication_template_summary.get("drop_candidate_rows"),
            "template_import_updated_rows": public_deduplication_template_import.get("updated_rows"),
            "template_import_skipped_rows": public_deduplication_template_import.get("skipped_rows"),
            "by_review_risk": public_deduplication_summary.get("by_review_risk"),
            "by_fast_review_lane": public_deduplication_template_summary.get("by_fast_review_lane"),
            "ichiban_reissue_work_order_rows": public_deduplication_action_summary.get(
                "ichiban_reissue_work_order_rows"
            ),
            "ichiban_campaign_url_comparison_preview": [
                {
                    "work_order_id": row.get("work_order_id"),
                    "normalized_name": row.get("normalized_name"),
                    "campaign_url_comparison": row.get("campaign_url_comparison"),
                }
                for row in _top(public_deduplication_action_queue.get("ichiban_reissue_work_order"), 5)
            ],
            "auto_merge_enabled": public_deduplication_template_summary.get("auto_merge_enabled"),
            "auto_delete_enabled": public_deduplication_template_summary.get("auto_delete_enabled"),
        },
        {
            "area": "Image path source review",
            "artifact": "server/image_path_source_url_review_queue.html",
            "markdown": "server/image_path_source_url_review_queue.md",
            "primary_metric": image_path_source_summary.get("review_items"),
            "primary_label": "review items",
            "secondary_metric": image_path_source_summary.get("source_report_rejected_count"),
            "secondary_label": "rejected source candidates",
            "status": "review_needed" if image_path_source_summary.get("review_items") else "clean",
            "next": "Review image-derived detail URLs that were rejected by title/HTTP checks; import only exact product pages.",
            "quick_win_metric": image_path_source_summary.get("source_report_updated_rows"),
            "quick_win_label": "auto-updated rows",
        },
        {
            "area": "Source URL bottlenecks",
            "artifact": "server/catalog_source_url_bottleneck_audit.md",
            "markdown": "server/catalog_source_url_bottleneck_audit.md",
            "primary_metric": source_url_bottlenecks.get("missing_source_url"),
            "primary_label": "missing source_url",
            "secondary_metric": source_url_bottlenecks.get("missing_image_and_source_url"),
            "secondary_label": "missing image+source",
            "status": "source_research_needed"
            if source_url_bottlenecks.get("missing_source_url")
            else "clean",
            "next": "Resolve exact product/detail source_url first; image import remains blocked while source_url is blank, generic, stale, or identity-uncertain.",
            "quick_win_metric": source_url_bottlenecks.get("automation_ready_source_candidates"),
            "quick_win_label": "automation-ready source candidates",
            "manual_review_metric": source_url_bottlenecks.get("manual_review_source_candidates"),
            "manual_review_label": "manual-review source candidates",
            "blocked_before_image_import": source_url_bottlenecks.get("blocked_before_image_import"),
            "top_missing_source_stores": _top(source_url_bottlenecks.get("missing_source_by_store"), 8),
            "top_missing_both_stores": _top(source_url_bottlenecks.get("missing_both_by_store"), 8),
            "bottleneck_counts": _top(source_url_bottlenecks.get("bottleneck_counts"), 10),
        },
        {
            "area": "Web image search candidates",
            "artifact": "server/web_image_search_candidates.json",
            "markdown": "server/catalog_image_existing_candidate_consolidated.json",
            "secondary_artifact": "server/catalog_image_existing_candidate_consolidated.json",
            "primary_metric": web_image_search.get("candidate_rows"),
            "primary_label": "web candidates",
            "secondary_metric": image_existing_summary.get("candidate_items"),
            "secondary_label": "safe consolidated candidates",
            "status": "import_candidates_ready"
            if image_existing_summary.get("candidate_items")
            else ("search_retry_needed" if web_image_search.get("stopped_early") else "empty"),
            "next": "Run web image search in small store/index batches; only import candidates that survive consolidation safety guards.",
            "quick_win_metric": web_image_search.get("rejected_rows"),
            "quick_win_label": "rejected rows",
            "failure_metric": _reason_count(web_image_search, "search_failed"),
            "failure_label": "search failures",
        },
        {
            "area": "Piapro prize candidates",
            "artifact": "server/piapro_prize_image_candidates_current.json",
            "markdown": "server/piapro_prize_image_candidates_current.md",
            "primary_metric": piapro_prize.get("candidate_rows"),
            "primary_label": "exact official candidates",
            "secondary_metric": piapro_prize.get("piapro_items"),
            "secondary_label": "Piapro prize items",
            "status": "import_candidates_ready" if piapro_prize.get("candidate_rows") else "exact_matches_empty",
            "next": "Use exact title + maker matches only; keep contained/generic title matches out of automatic imports.",
            "quick_win_metric": piapro_prize.get("blocker_rows"),
            "quick_win_label": "blocked rows",
        },
        {
            "area": "Prize line provider candidates",
            "artifact": "server/prize_line_official_detail_match_queue_current.html",
            "markdown": "server/prize_line_official_detail_match_queue_current.md",
            "secondary_artifact": "server/prize_line_expected_provider_queue_current.json",
            "primary_metric": prize_line_official_detail.get("candidate_rows"),
            "primary_label": "official detail candidates",
            "secondary_metric": prize_line_expected_summary.get("items"),
            "secondary_label": "source-store mismatch rows",
            "status": "manual_confirmation_needed"
            if prize_line_official_detail.get("candidate_rows")
            else "empty",
            "next": "Review weak/ambiguous prize-line candidates before changing source_store or importing image URLs.",
            "quick_win_metric": _summary_count(prize_line_official_detail, "by_status", "weak_or_ambiguous"),
            "quick_win_label": "weak/ambiguous rows",
        },
        {
            "area": "Prize provider fallback images",
            "artifact": "server/prize_provider_fallback_image_candidates_current.html",
            "markdown": "server/prize_provider_fallback_image_candidates_current.md",
            "secondary_artifact": "server/prize_provider_fallback_image_candidates_current.json",
            "primary_metric": prize_provider_fallback_summary.get("fallback_candidate_rows"),
            "primary_label": "review-only fallback candidates",
            "secondary_metric": prize_provider_fallback_summary.get("searched_rows"),
            "secondary_label": "searched rows",
            "status": "manual_confirmation_needed"
            if prize_provider_fallback_summary.get("fallback_candidate_rows")
            else "empty",
            "next": "Compare current DB line/title with the official fallback title before importing any image URL; broad character hits can be a different prize line.",
            "quick_win_metric": prize_provider_fallback_summary.get("unresolved_rows"),
            "quick_win_label": "unresolved rows",
            "target_stores": prize_provider_fallback_summary.get("target_stores"),
        },
        {
            "area": "Agent image candidate imports",
            "artifact": "server/agent_image_candidates_import_queue_current.html",
            "markdown": "server/agent_image_candidates_import_queue_current.md",
            "secondary_artifact": "server/agent_image_candidates_import_queue_current.json",
            "primary_metric": agent_image_summary.get("ready_items"),
            "primary_label": "ready import items",
            "secondary_metric": agent_image_summary.get("rejected_items"),
            "secondary_label": "rejected items",
            "status": "import_ready"
            if agent_image_summary.get("ready_items")
            else ("reviewed_no_safe_imports" if agent_image_summary.get("rejected_items") else "empty"),
            "next": "Use this queue after agent/manual research; import only ready items and leave rejected source/store/title conflicts in review.",
            "quick_win_metric": agent_image_summary.get("preflight_passed_items"),
            "quick_win_label": "preflight-passed items",
            "candidate_files_metric": agent_image_summary.get("candidate_files"),
            "candidate_files_label": "candidate files",
            "rejected_reasons": agent_image_summary.get("rejected_reasons"),
        },
        {
            "area": "Broad image candidate imports",
            "artifact": "server/agent_image_candidates_import_queue_broad.html",
            "markdown": "server/agent_image_candidates_import_queue_broad.md",
            "secondary_artifact": "server/agent_image_candidates_import_queue_broad.json",
            "primary_metric": agent_image_broad_summary.get("ready_items"),
            "primary_label": "ready import items",
            "secondary_metric": agent_image_broad_summary.get("rejected_items"),
            "secondary_label": "rejected items",
            "status": "import_ready"
            if agent_image_broad_summary.get("ready_items")
            else ("reviewed_no_safe_imports" if agent_image_broad_summary.get("rejected_items") else "empty"),
            "next": "Re-scan historical image candidate files against the current seed; import only ready items that still pass identity and safety checks.",
            "quick_win_metric": agent_image_broad_summary.get("preflight_passed_items"),
            "quick_win_label": "preflight-passed items",
            "candidate_files_metric": agent_image_broad_summary.get("candidate_files"),
            "candidate_files_label": "candidate files",
            "rejected_reasons": agent_image_broad_summary.get("rejected_reasons"),
        },
        {
            "area": "Storefront candidates",
            "artifact": "server/storefront_review_batches.html",
            "markdown": "server/storefront_review_batches.md",
            "secondary_artifact": "server/storefront_match_review.html",
            "primary_metric": storefront.get("reviewable_seed_rows"),
            "primary_label": "seed rows",
            "secondary_metric": storefront.get("reviewable_candidate_rows"),
            "secondary_label": "candidate rows",
            "status": "manual_confirmation_needed" if storefront.get("reviewable_seed_rows") else "empty",
            "next": "Resolve ambiguous storefront/Fanding product rows before importing exact source/image/release fields.",
            "ambiguous_metric": storefront_match.get("ambiguous_reviewable_candidates"),
            "ambiguous_label": "ambiguous candidates",
            "manual_only_metric": storefront_match.get("manual_only_rows"),
            "manual_only_label": "manual-only rows",
        },
        {
            "area": "Stellive Fanding candidates",
            "artifact": "server/fanding_stellive_match_queue.json",
            "markdown": "server/fanding_stellive_match_queue.csv",
            "primary_metric": fanding_stellive.get("rows"),
            "primary_label": "candidate rows",
            "secondary_metric": fanding_status_counts.get("weak_manual_review_candidate"),
            "secondary_label": "weak review candidates",
            "status": "manual_confirmation_needed"
            if fanding_status_counts.get("weak_manual_review_candidate")
            else ("no_exact_candidates" if fanding_stellive else "missing_report"),
            "next": "Review Fanding candidates manually; current fuzzy matches are not safe for automatic image/source import.",
            "quick_win_metric": fanding_status_counts.get("strong_manual_review_candidate"),
            "quick_win_label": "strong review candidates",
            "manual_only_metric": fanding_status_counts.get("no_candidate"),
            "manual_only_label": "no-candidate rows",
        },
        {
            "area": "Pokemon Center candidates",
            "artifact": "server/pokemon_center_official_latest_dryrun.json",
            "markdown": "server/pokemon_center_official_latest_dryrun.json",
            "primary_metric": pokemon_center.get("review_rows"),
            "primary_label": "review rows",
            "secondary_metric": pokemon_center.get("updated_rows"),
            "secondary_label": "auto updates",
            "status": "manual_confirmation_needed" if pokemon_center.get("review_rows") else "clean",
            "next": "Review Pokemon Center homepage rows; import only exact product pages because common terms produce multiple plausible products.",
        },
        {
            "area": "Official detail candidates",
            "artifact": "server/official_detail_review_batches.html",
            "markdown": "server/official_detail_review_batches.md",
            "primary_metric": official.get("reviewable_seed_rows"),
            "primary_label": "seed rows",
            "secondary_metric": official.get("reviewable_candidate_rows"),
            "secondary_label": "candidate rows",
            "status": "manual_confirmation_needed" if official.get("reviewable_seed_rows") else "empty",
            "next": "Confirm title/detail identity before writing official source/image fields.",
        },
        {
            "area": "Official detail provider sweeps",
            "artifact": "server/official_detail_match_queue_animate_after_query_fix_merged_summary.md",
            "markdown": "server/official_detail_match_queue_ensky_merged_current.md",
            "primary_metric": official_detail_processed,
            "primary_label": "processed seed rows",
            "secondary_metric": official_detail_reviewable,
            "secondary_label": "reviewable rows",
            "status": "manual_confirmation_needed"
            if official_detail_reviewable
            else ("reviewed_no_safe_imports" if official_detail_processed else "missing_report"),
            "next": "Confirm broad Animate representative rows first; Ensky has no safe official detail imports in the completed sweep.",
            "quick_win_metric": official_detail_candidates,
            "quick_win_label": "candidate rows scanned",
            "animate_reviewable": official_animate.get("reviewable_rows"),
            "ensky_reviewable": official_ensky.get("reviewable_rows"),
            "animate_statuses": _top(official_animate.get("by_status"), 5),
            "ensky_statuses": _top(official_ensky.get("by_status"), 5),
            "animate_manual_reasons": _top(official_animate.get("by_manual_review_reason"), 5),
            "ensky_manual_reasons": _top(official_ensky.get("by_manual_review_reason"), 5),
        },
        {
            "area": "Taito brand API candidates",
            "artifact": "server/taito_brand_image_candidates_current.json",
            "markdown": "server/taito_brand_image_candidates_current.json",
            "primary_metric": taito_brand.get("target_rows"),
            "primary_label": "brand API target rows",
            "secondary_metric": taito_brand.get("exact_match_rows"),
            "secondary_label": "exact matches",
            "status": "manual_review_needed" if taito_brand.get("target_rows") else "empty",
            "next": "Use official Taito brand API results as evidence; import only single exact character/title matches.",
            "quick_win_metric": (taito_brand.get("brand_counts") or {}).get("desktop_cute"),
            "quick_win_label": "Desktop Cute API rows",
        },
        {
            "area": "Chiikawa gotouchi API coverage",
            "artifact": "server/chiikawa_gotouchi_api_coverage_audit.json",
            "markdown": "server/chiikawa_gotouchi_api_coverage_audit.json",
            "primary_metric": gotouchi_api.get("target_rows"),
            "primary_label": "missing gotouchi rows",
            "secondary_metric": (gotouchi_api.get("status_counts") or {}).get("official_pair_available", 0),
            "secondary_label": "official pair available",
            "status": "official_api_gap"
            if gotouchi_api.get("target_rows") and not (gotouchi_api.get("status_counts") or {}).get("official_pair_available")
            else "review_available_pairs",
            "next": "Use this audit before searching gotouchi rows; most stale themes need external official evidence rather than JP-API auto-fill.",
            "quick_win_metric": gotouchi_api.get("official_image_count"),
            "quick_win_label": "official API images",
        },
        {
            "area": "Ichiban Kuji gaps",
            "artifact": "server/ichiban_kuji_gap_work_queue.html",
            "markdown": "server/ichiban_kuji_gap_work_queue.md",
            "audit_artifact": "server/ichiban_kuji_campaign_gap_audit.md",
            "secondary_artifact": "server/ichiban_replacement_url_queue.md",
            "primary_metric": ichiban_gap.get("total_items"),
            "primary_label": "gap items",
            "secondary_metric": _replacement_extractable_count(ichiban_replacement),
            "secondary_label": "extractable replacement candidates",
            "status": _ichiban_gap_queue_status(ichiban_gap),
            "next": "Review server/ichiban_replacement_url_queue.md first; import only official candidates that extract prize rows and match the missing campaign.",
            "quick_win_metric": _replacement_status_count(ichiban_replacement, "covered_by_seeded_counterpart"),
            "quick_win_label": "seeded counterparts",
            "documented_terminal_metric": ichiban_gap.get("documented_terminal_items"),
            "documented_terminal_label": "documented terminal gaps",
            "actionable_gap_metric": ichiban_gap.get("actionable_items"),
            "actionable_gap_label": "actionable gaps",
            "tertiary_metric": ichiban_sub_series_batches.get("batch_count"),
            "tertiary_label": "sub-series review batches",
        },
        {
            "area": "Ichiban Kuji campaign audit",
            "artifact": "server/ichiban_kuji_campaign_gap_audit.md",
            "markdown": "server/ichiban_kuji_metadata_audit.md",
            "secondary_artifact": "server/ichiban_kuji_prize_structure_audit.json",
            "primary_metric": ichiban_campaign_gap.get("campaign_gap_count"),
            "primary_label": "campaign gaps",
            "secondary_metric": ichiban_metadata.get("urls_with_missing_metadata"),
            "secondary_label": "metadata pages",
            "status": _ichiban_campaign_audit_status(ichiban_campaign_gap, ichiban_metadata),
            "next": "Keep archive/404/no-lineup campaigns documented; only add rows or metadata when exact official prize-lineup evidence is found.",
            "quick_win_metric": ichiban_structure.get("campaign_without_seed_rows_count"),
            "quick_win_label": "campaigns without seed rows",
            "rows_missing_release_date": ichiban_metadata.get("rows_missing_release_date"),
            "rows_missing_official_price_jpy": ichiban_metadata.get("rows_missing_official_price_jpy"),
            "metadata_review_metric": ichiban_metadata_review_summary.get("review_items"),
            "metadata_review_label": "metadata review items",
        },
        {
            "area": "Ichiban Kuji history status",
            "artifact": "server/ichiban_kuji_history_status_audit.md",
            "markdown": "server/ichiban_kuji_history_status_audit.md",
            "primary_metric": ichiban_history_status.get("campaign_count"),
            "primary_label": "campaigns",
            "secondary_metric": ichiban_history_status.get("documented_terminal_gap_items"),
            "secondary_label": "documented terminal gaps",
            "status": ichiban_history_status.get("status") or "missing_report",
            "next": "Keep documented terminal campaign gaps archived; import metadata only when labeled official release or yen-price evidence is safe.",
            "quick_win_metric": ichiban_history_status.get("prize_rows"),
            "quick_win_label": "prize rows",
            "campaign_coverage_rate": ichiban_history_status.get("campaign_coverage_rate"),
            "actionable_gap_items": ichiban_history_status.get("actionable_gap_items"),
            "missing_sub_series_rows": ichiban_history_status.get("missing_sub_series_rows"),
            "metadata_blocked_rows": (ichiban_history_status.get("metadata") or {}).get("blocked_rows"),
            "metadata_safe_update_url_count": (ichiban_history_status.get("metadata") or {}).get("safe_update_url_count"),
        },
        {
            "area": "Animation categories",
            "artifact": "server/animation_goods_category_audit.md",
            "markdown": "server/animation_goods_category_audit.md",
            "secondary_artifact": "server/animation_enrichment_priority_queue.html",
            "primary_metric": animation.get("rows"),
            "primary_label": "rows",
            "secondary_metric": len(animation.get("unknown_categories") or []),
            "secondary_label": "unknown categories",
            "status": "covered" if not animation.get("unknown_categories") else "taxonomy_review_needed",
            "next": "Keep taxonomy normalized; review missing images/source by category.",
            "priority_queue_groups": animation_priority.get("queue_groups"),
            "priority_queue_rows": animation_priority.get("queue_rows"),
            "priority_queue_by_workflow": animation_priority.get("by_workflow"),
            "top_missing_image_categories": _top(animation.get("missing_image_by_category"), 5),
            "top_missing_source_categories": _top(animation.get("missing_source_url_by_category"), 5),
            "category_family_count": len(animation.get("category_families") or []),
            "category_count": animation.get("category_count"),
        },
        {
            "area": "App folder visuals",
            "artifact": "server/app_folder_visual_catalog_audit.md",
            "markdown": "server/app_folder_visual_catalog_audit.md",
            "primary_metric": app_folder_visuals.get("icon_count"),
            "primary_label": "folder icons",
            "secondary_metric": app_folder_visuals.get("color_count"),
            "secondary_label": "folder colors",
            "status": "covered"
            if app_folder_visuals.get("animation_visuals_covered")
            and not app_folder_visuals.get("duplicate_icon_keys")
            and not app_folder_visuals.get("duplicate_colors")
            else "visual_catalog_review_needed",
            "next": "Keep folder colors grouped by palette sections and ensure animation category visual hints exist in the app icon/color catalogs.",
            "quick_win_metric": app_folder_visuals.get("palette_section_count"),
            "quick_win_label": "palette sections",
            "animation_visuals_covered": app_folder_visuals.get("animation_visuals_covered"),
            "duplicate_icon_keys": app_folder_visuals.get("duplicate_icon_keys"),
            "duplicate_colors": app_folder_visuals.get("duplicate_colors"),
        },
        {
            "area": "Confirmed queues",
            "artifact": "server/catalog_confirmed_import_queue_audit.md",
            "markdown": "server/catalog_confirmed_import_queue_audit.md",
            "primary_metric": (confirmed.get("summary") or {}).get("manual_confirmed_true"),
            "primary_label": "confirmed pending",
            "secondary_metric": (archive.get("summary") or {}).get("archive_items"),
            "secondary_label": "archived done",
            "status": "clean" if not (confirmed.get("summary") or {}).get("manual_confirmed_true") else "import_pending",
            "next": "Import only confirmed rows; completed duplicates are kept in archive files.",
        },
        {
            "area": "Store/source integrity",
            "artifact": "server/stale_source_cleanup_queue.html",
            "markdown": "server/stale_source_cleanup_queue.md",
            "secondary_artifact": "server/store_source_netloc_audit.md",
            "primary_metric": store_source.get("mismatch_count"),
            "primary_label": "mismatches",
            "secondary_metric": stale_source_summary.get("mismatch_rows") or live_source.get("mismatch_urls"),
            "secondary_label": "cleanup rows",
            "status": "live_source_review_needed"
            if stale_source_summary.get("mismatch_rows") or live_source.get("mismatch_urls")
            else ("review_external_evidence" if store_source.get("mismatch_count") else "clean"),
            "next": "Review stale source cleanup rows before propagating images; old product IDs can point to unrelated current products.",
            "quick_win_metric": _severity_count(store_source, "external_evidence_source"),
            "quick_win_label": "external evidence rows",
        },
        {
            "area": "Generic source cleanup",
            "artifact": "server/generic_source_cleanup_queue.html",
            "markdown": "server/generic_source_cleanup_queue.md",
            "primary_metric": generic_source_summary.get("generic_source_rows"),
            "primary_label": "generic source rows",
            "secondary_metric": generic_source_summary.get("generic_source_urls"),
            "secondary_label": "generic URLs",
            "status": "exact_source_needed" if generic_source_summary.get("generic_source_rows") else "clean",
            "next": "Replace homepage/storefront URLs with exact product detail pages before image import.",
            "candidate_status_counts": generic_source_summary.get("by_candidate_status"),
        },
        {
            "area": "Prize source-store line audit",
            "artifact": "server/prize_source_store_line_audit.html",
            "markdown": "server/prize_source_store_line_audit.md",
            "primary_metric": prize_source_store_summary.get("mismatch_rows"),
            "primary_label": "source-store mismatches",
            "secondary_metric": prize_source_store_summary.get("missing_image_mismatch_rows"),
            "secondary_label": "missing-image mismatches",
            "status": "provider_routing_review_needed"
            if prize_source_store_summary.get("mismatch_rows")
            else "clean",
            "next": "Review prize line rows before provider image runs; wrong source_store sends search to the wrong official provider.",
            "by_current_expected": prize_source_store_summary.get("by_current_expected"),
        },
        {
            "area": "Product identity review",
            "artifact": "server/product_identity_review_queue.html",
            "markdown": "server/product_identity_review_queue.md",
            "primary_metric": product_identity_summary.get("review_rows"),
            "primary_label": "blocked rows",
            "secondary_metric": product_identity_summary.get("skipped_rows"),
            "secondary_label": "skipped rows",
            "status": "identity_review_needed" if product_identity_summary.get("review_rows") else "clean",
            "next": "Verify or rename these rows before source/image import; exact official evidence is required.",
        },
        {
            "area": "Report consistency",
            "artifact": "server/catalog_report_consistency_audit.json",
            "markdown": "server/catalog_report_consistency_audit.json",
            "primary_metric": report_consistency.get("failure_count"),
            "primary_label": "mismatches",
            "secondary_metric": report_consistency.get("check_count"),
            "secondary_label": "checks",
            "status": "clean" if report_consistency.get("ok") else "stale_or_mismatched",
            "next": "Regenerate quality, field, image, and review-batch reports before making catalog decisions.",
        },
        {
            "area": "DB sync",
            "artifact": "server/catalog_db_sync_audit.md",
            "markdown": "server/catalog_db_sync_audit.md",
            "secondary_artifact": "server/catalog_db_sync_audit.json",
            "primary_metric": sum(1 for item in db_sync.get("databases") or [] if not item.get("ok")),
            "primary_label": "DBs with sync issues",
            "secondary_metric": db_sync.get("seed_rows"),
            "secondary_label": "seed rows",
            "status": "clean" if db_sync.get("ok") else "sync_needed",
            "next": "Run sync_catalog_db_active.py and dedupe_catalog_db.py when stale, missing, updated, or duplicate active DB rows appear.",
            "db_count_metric": db_sync.get("db_count"),
            "db_count_label": "audited DBs",
            "database_summaries": [
                {
                    "db": f"catalog_db_{index + 1}",
                    "ok": item.get("ok"),
                    "active_rows": item.get("active_rows"),
                    "missing_images": item.get("missing_images"),
                    "stale_active_rows": item.get("stale_active_rows"),
                    "missing_seed_rows": item.get("missing_seed_rows"),
                    "updated_active_rows": item.get("updated_active_rows"),
                    "duplicate_active_rows": item.get("duplicate_active_rows"),
                }
                for index, item in enumerate(db_sync.get("databases") or [])
            ],
        },
        {
            "area": "Requested special goods",
            "artifact": "server/requested_special_goods_review.html",
            "markdown": "server/requested_special_goods_queue.csv",
            "primary_metric": requested_special.get("already_present"),
            "primary_label": "already present",
            "secondary_metric": requested_special.get("missing"),
            "secondary_label": "missing requests",
            "status": "covered" if not requested_special.get("missing") else "import_needed",
            "next": "Keep this queue as the requested-list coverage gate before adding duplicate special goods.",
            "quick_win_metric": requested_special.get("with_candidate_image"),
            "quick_win_label": "with candidate image",
        },
        {
            "area": "Focus missing images",
            "artifact": "server/focus_missing_image_queue_current.html",
            "markdown": "server/focus_missing_image_queue_current.md",
            "secondary_artifact": "server/focus_missing_image_queue_current.json",
            "primary_metric": focus_missing_images.get("focus_missing_image_rows"),
            "primary_label": "focus rows missing images",
            "secondary_metric": focus_missing_images.get("focus_missing_source_rows"),
            "secondary_label": "focus rows missing source",
            "status": "source_research_needed" if focus_missing_images.get("focus_missing_image_rows") else "covered",
            "next": "Use the focus queue for requested series and collab goods; find exact source pages before attaching images.",
            "quick_win_metric": focus_missing_images.get("focus_missing_image_and_source_rows"),
            "quick_win_label": "missing both image/source",
        },
        {
            "area": "Focus series image work",
            "artifact": "server/focus_series_missing_image_work_queues_current.csv",
            "markdown": "server/focus_series_missing_image_work_queues_current.md",
            "secondary_artifact": "server/focus_series_missing_image_work_queues_current.json",
            "primary_metric": focus_series_missing_images.get("missing_image_rows"),
            "primary_label": "series rows missing images",
            "secondary_metric": focus_series_missing_images.get("missing_source_rows"),
            "secondary_label": "series rows missing source",
            "status": "source_research_needed" if focus_series_missing_images.get("missing_image_rows") else "covered",
            "next": "Use this narrowed queue for HUNTER, Stellive, Chiikawa MINISO/Gotouchi/Ensky, Bukubu, and Tapinui exact-source review.",
            "quick_win_metric": focus_series_missing_images.get("auto_write_ready"),
            "quick_win_label": "auto-write ready",
        },
    ]

    return {
        "summary": {
            "rows": quality.get("rows", goal.get("rows")),
            "duplicate_groups": quality.get("duplicate_groups", goal.get("duplicate_groups")),
            "missing_enrichment": quality.get("missing_enrichment", goal.get("missing_enrichment")),
            "field_actionable_rows": field_batches.get("actionable_rows"),
            "missing_images": image_queue.get("missing_images"),
            "image_workstreams": image_batch_plan.get("workstream_count"),
            "image_batches": image_batch_plan.get("batch_count"),
            "image_exact_url_work_items": image_exact_url_queue.get("item_count"),
            "image_exact_url_research_items": image_exact_identity.get("exact_url_research", 0),
            "image_exact_url_identity_blocked": image_exact_identity.get("blocked_by_identity_review", 0),
            "image_exact_url_identity_split": image_exact_url_queue.get("by_identity_review"),
            "image_path_source_review": {
                "review_items": image_path_source_summary.get("review_items"),
                "source_report_updated_rows": image_path_source_summary.get("source_report_updated_rows"),
                "source_report_rejected_count": image_path_source_summary.get("source_report_rejected_count"),
                "by_reason": image_path_source_summary.get("by_reason"),
                "by_host": image_path_source_summary.get("by_host"),
            },
            "image_auto_promotable_candidates": (image_auto_promotable.get("summary") or {}).get("candidate_items"),
            "image_auto_promotable_strict_import": {
                "candidate_rows": image_auto_promotable_strict.get("candidate_rows"),
                "updated_rows": image_auto_promotable_strict.get("updated_rows"),
                "skipped_rows": image_auto_promotable_strict.get("skipped_rows"),
                "skipped_reasons": image_auto_promotable_strict.get("skipped_reasons"),
            },
            "image_confirmed_import_ready": (image_exact_confirmed_import.get("summary") or {}).get("ready_items"),
            "web_image_search": {
                "target_rows": web_image_search.get("target_rows"),
                "candidate_rows": web_image_search.get("candidate_rows"),
                "rejected_rows": web_image_search.get("rejected_rows"),
                "stopped_early": web_image_search.get("stopped_early"),
                "rejected_reason_counts": web_image_search.get("rejected_reason_counts"),
            },
            "piapro_prize_candidates": {
                "piapro_items": piapro_prize.get("piapro_items"),
                "candidate_rows": piapro_prize.get("candidate_rows"),
                "blocker_rows": piapro_prize.get("blocker_rows"),
            },
            "image_existing_candidates": {
                "candidate_items": image_existing_summary.get("candidate_items"),
                "missing_rows": image_existing_summary.get("missing_rows"),
                "scanned_files": image_existing_summary.get("scanned_files"),
                "scanned_candidate_rows": image_existing_summary.get("scanned_candidate_rows"),
                "skipped_rows": image_existing_summary.get("skipped_rows"),
                "skipped_by_reason": image_existing_candidates.get("skipped_by_reason"),
                "strict_import": {
                    "candidate_rows": image_existing_strict.get("candidate_rows"),
                    "updated_rows": image_existing_strict.get("updated_rows"),
                    "skipped_rows": image_existing_strict.get("skipped_rows"),
                    "skipped_reasons": image_existing_strict.get("skipped_reasons"),
                },
            },
            "remaining_image_audit": {
                "missing_images": remaining_image_audit.get("missing_images"),
                "provider_candidate_items": remaining_image_audit.get("provider_candidate_items"),
                "manual_or_blocked_items": remaining_image_audit.get("manual_or_blocked_items"),
                "missing_with_source_url": remaining_image_audit.get("missing_with_source_url"),
                "missing_with_exact_source_url": remaining_image_audit.get("missing_with_exact_source_url"),
                "missing_with_generic_source_url": remaining_image_audit.get("missing_with_generic_source_url"),
                "candidate_reviews": {
                    "ready_items": remaining_candidate_reviews.get("ready_items"),
                    "preflight_passed_items": remaining_candidate_reviews.get("preflight_passed_items"),
                    "candidate_items": remaining_candidate_reviews.get("candidate_items"),
                    "rejected_reasons": remaining_candidate_reviews.get("rejected_reasons"),
                },
                "provider_blockers": _top(remaining_image_audit.get("provider_blockers"), 10),
            },
            "source_discovery": {
                "source_discovery_rows": source_discovery_summary.get("source_discovery_rows"),
                "stale_excluded_rows": source_discovery_summary.get("stale_excluded_rows"),
                "by_workflow": source_discovery_summary.get("by_workflow"),
                "top_store_categories": _top(source_discovery_summary.get("top_store_categories"), 10),
                "top_official_search_store_categories": _top(
                    source_discovery_summary.get("top_official_search_store_categories"),
                    10,
                ),
            },
            "source_url_bottlenecks": {
                "missing_source_url": source_url_bottlenecks.get("missing_source_url"),
                "missing_image_and_source_url": source_url_bottlenecks.get("missing_image_and_source_url"),
                "has_image_but_missing_source_url": source_url_bottlenecks.get("has_image_but_missing_source_url"),
                "automation_ready_source_candidates": source_url_bottlenecks.get("automation_ready_source_candidates"),
                "manual_review_source_candidates": source_url_bottlenecks.get("manual_review_source_candidates"),
                "blocked_before_image_import": source_url_bottlenecks.get("blocked_before_image_import"),
                "bottleneck_counts": source_url_bottlenecks.get("bottleneck_counts"),
                "top_missing_source_stores": _top(source_url_bottlenecks.get("missing_source_by_store"), 10),
                "top_missing_both_stores": _top(source_url_bottlenecks.get("missing_both_by_store"), 10),
            },
            "source_detail_candidates": {
                "source_queue_rows": source_detail_summary.get("source_queue_rows"),
                "supported_provider_rows": source_detail_summary.get("supported_provider_rows"),
                "unsupported_provider_rows": source_detail_summary.get("unsupported_provider_rows"),
                "scanned_rows": source_detail_summary.get("scanned_rows"),
                "exact_candidate_rows": source_detail_summary.get("exact_candidate_rows"),
                "candidate_review_rows": source_detail_summary.get("candidate_review_rows"),
                "status_counts": source_detail_summary.get("status_counts"),
                "top_unsupported_provider_stores": _top(
                    source_detail_summary.get("top_unsupported_provider_stores"),
                    10,
                ),
                "batch_summary": {
                    "report_count": source_detail_candidate_summary_summary.get("report_count"),
                    "processed_rows_reported": source_detail_candidate_summary_summary.get(
                        "processed_rows_reported"
                    ),
                    "unique_processed_store_row_pairs": source_detail_candidate_summary_summary.get(
                        "unique_processed_store_row_pairs"
                    ),
                    "unique_exact_candidate_store_row_pairs": source_detail_candidate_summary_summary.get(
                        "unique_exact_candidate_store_row_pairs"
                    ),
                    "unique_review_candidate_store_row_pairs": source_detail_candidate_summary_summary.get(
                        "unique_review_candidate_store_row_pairs"
                    ),
                    "actionable_report_count": source_detail_candidate_summary_summary.get(
                        "actionable_report_count"
                    ),
                    "time_budget_exhausted_reports": source_detail_candidate_summary_summary.get(
                        "time_budget_exhausted_reports"
                    ),
                    "rate_limit_skipped_stores": source_detail_candidate_summary_summary.get(
                        "rate_limit_skipped_stores"
                    ),
                    "top_stores": _top(source_detail_candidate_summary.get("by_store"), 10),
                },
            },
            "image_review_batches": image_batches.get("batch_count"),
            "unapplied_image_candidates": unapplied_image_changes.get("candidate_count"),
            "image_provider_recheck": {
                "filled": image_provider_recheck.get("filled"),
                "processed_rows": image_provider_recheck.get("processed_rows"),
                "time_budget_exhausted": image_provider_recheck.get("time_budget_exhausted"),
                "allowed_stores": image_provider_recheck.get("allowed_stores"),
                "unresolved_summary": image_provider_recheck_summary,
            },
            "storefront_reviewable_seed_rows": storefront.get("reviewable_seed_rows"),
            "storefront_reviewable_candidate_rows": storefront.get("reviewable_candidate_rows"),
            "storefront_ambiguous_candidates": storefront_match.get("ambiguous_reviewable_candidates"),
            "storefront_manual_only_rows": storefront_match.get("manual_only_rows"),
            "fanding_stellive": {
                "candidate_rows": fanding_stellive.get("rows"),
                "candidate_status_counts": fanding_status_counts,
            },
            "official_reviewable_seed_rows": official.get("reviewable_seed_rows"),
            "official_detail_provider_sweeps": {
                "processed_seed_rows": official_detail_processed,
                "candidate_rows": official_detail_candidates,
                "reviewable_rows": official_detail_reviewable,
                "animate": {
                    "processed_seed_rows": _official_detail_processed_rows(official_animate),
                    "candidate_rows": official_animate.get("candidate_rows"),
                    "reviewable_rows": official_animate.get("reviewable_rows"),
                    "by_status": official_animate.get("by_status"),
                    "by_manual_review_reason": official_animate.get("by_manual_review_reason"),
                },
                "ensky": {
                    "processed_seed_rows": official_ensky.get("unique_processed_seed_rows"),
                    "candidate_rows": official_ensky.get("candidate_rows"),
                    "reviewable_rows": official_ensky.get("reviewable_rows"),
                    "by_status": official_ensky.get("by_status"),
                    "by_manual_review_reason": official_ensky.get("by_manual_review_reason"),
                },
            },
            "pokemon_center_official": {
                "updated_rows": pokemon_center.get("updated_rows"),
                "review_rows": pokemon_center.get("review_rows"),
            },
            "taito_brand_target_rows": taito_brand.get("target_rows"),
            "taito_brand_exact_matches": taito_brand.get("exact_match_rows"),
            "chiikawa_gotouchi_api": {
                "target_rows": gotouchi_api.get("target_rows"),
                "official_image_count": gotouchi_api.get("official_image_count"),
                "status_counts": gotouchi_api.get("status_counts"),
            },
            "ichiban_gap_items": ichiban_gap.get("total_items"),
            "ichiban_gap_documented_terminal_items": ichiban_gap.get("documented_terminal_items"),
            "ichiban_gap_actionable_items": ichiban_gap.get("actionable_items"),
            "ichiban_gap_all_documented": ichiban_gap.get("all_gaps_documented"),
            "ichiban_replacement_extractable": _replacement_extractable_count(ichiban_replacement),
            "ichiban_replacement_seeded_counterparts": _replacement_status_count(
                ichiban_replacement,
                "covered_by_seeded_counterpart",
            ),
            "ichiban_replacement_statuses": ichiban_replacement.get("by_status"),
            "ichiban_campaign_gap_audit": {
                "campaign_count": ichiban_campaign_gap.get("campaign_count"),
                "seeded_campaign_url_count": ichiban_campaign_gap.get("seeded_campaign_url_count"),
                "campaign_gap_count": ichiban_campaign_gap.get("campaign_gap_count"),
                "audited_gap_count": ichiban_campaign_gap.get("audited_gap_count"),
                "by_classification": ichiban_campaign_gap.get("by_classification"),
            },
            "ichiban_metadata": {
                "urls_with_missing_metadata": ichiban_metadata.get("urls_with_missing_metadata"),
                "rows_missing_release_date": ichiban_metadata.get("rows_missing_release_date"),
                "rows_missing_official_price_jpy": ichiban_metadata.get("rows_missing_official_price_jpy"),
                "safe_release_url_count": ichiban_metadata.get("safe_release_url_count"),
                "safe_price_url_count": ichiban_metadata.get("safe_price_url_count"),
                "review_items": ichiban_metadata_review_summary.get("review_items"),
                "review_missing_release_rows": ichiban_metadata_review_summary.get("missing_release_rows"),
                "review_missing_price_rows": ichiban_metadata_review_summary.get("missing_price_rows"),
                "review_by_workflow": ichiban_metadata_review_summary.get("by_workflow"),
            },
            "ichiban_history_status": {
                "status": ichiban_history_status.get("status"),
                "campaign_count": ichiban_history_status.get("campaign_count"),
                "seeded_campaign_url_count": ichiban_history_status.get("seeded_campaign_url_count"),
                "campaign_coverage_rate": ichiban_history_status.get("campaign_coverage_rate"),
                "campaign_gap_count": ichiban_history_status.get("campaign_gap_count"),
                "documented_terminal_gap_items": ichiban_history_status.get("documented_terminal_gap_items"),
                "actionable_gap_items": ichiban_history_status.get("actionable_gap_items"),
                "import_safe_now": ichiban_history_status.get("import_safe_now"),
                "prize_rows": ichiban_history_status.get("prize_rows"),
                "missing_sub_series_rows": ichiban_history_status.get("missing_sub_series_rows"),
                "metadata": ichiban_history_status.get("metadata"),
            },
            "animation_unknown_categories": len(animation.get("unknown_categories") or []),
            "animation_category_count": animation.get("category_count"),
            "animation_category_families": animation.get("category_families"),
            "animation_missing_image_by_category": _top(animation.get("missing_image_by_category"), 10),
            "animation_missing_source_url_by_category": _top(animation.get("missing_source_url_by_category"), 10),
            "animation_enrichment_priority": {
                "queue_groups": animation_priority.get("queue_groups"),
                "queue_rows": animation_priority.get("queue_rows"),
                "missing_image_rows": animation_priority.get("missing_image_rows"),
                "missing_source_rows": animation_priority.get("missing_source_rows"),
                "by_workflow": animation_priority.get("by_workflow"),
            },
            "app_folder_visuals": {
                "icon_count": app_folder_visuals.get("icon_count"),
                "icon_group_count": app_folder_visuals.get("icon_group_count"),
                "color_count": app_folder_visuals.get("color_count"),
                "unique_color_count": app_folder_visuals.get("unique_color_count"),
                "palette_section_count": app_folder_visuals.get("palette_section_count"),
                "animation_visuals_covered": app_folder_visuals.get("animation_visuals_covered"),
                "missing_animation_icons": app_folder_visuals.get("missing_animation_icons"),
                "missing_animation_colors": app_folder_visuals.get("missing_animation_colors"),
            },
            "confirmed_pending": (confirmed.get("summary") or {}).get("manual_confirmed_true"),
            "confirmed_archive_items": (archive.get("summary") or {}).get("archive_items"),
            "db_sync": {
                "ok": db_sync.get("ok"),
                "db_count": db_sync.get("db_count"),
                "issue_dbs": sum(1 for item in db_sync.get("databases") or [] if not item.get("ok")),
                "seed_rows": db_sync.get("seed_rows"),
            },
            "store_source_mismatches": store_source.get("mismatch_count"),
            "store_source_wrong": _severity_count(store_source, "store_probably_wrong"),
            "store_source_external_evidence": _severity_count(store_source, "external_evidence_source"),
            "live_source_identity": {
                "scoped_rows": live_source.get("scoped_rows"),
                "audited_urls": live_source.get("audited_urls"),
                "mismatch_urls": live_source.get("mismatch_urls"),
                "failure_count": live_source.get("failure_count"),
                "status_counts": live_source.get("status_counts"),
            },
            "stale_source_cleanup": {
                "mismatch_rows": stale_source_summary.get("mismatch_rows"),
                "mismatch_urls": stale_source_summary.get("mismatch_urls"),
                "by_source_store": stale_source_summary.get("by_source_store"),
            },
            "product_identity_review": {
                "review_rows": product_identity_summary.get("review_rows"),
                "skipped_rows": product_identity_summary.get("skipped_rows"),
                "by_source_store": product_identity_summary.get("by_source_store"),
                "by_status": product_identity_summary.get("by_status"),
            },
            "generic_source_cleanup": {
                "generic_source_rows": generic_source_summary.get("generic_source_rows"),
                "generic_source_urls": generic_source_summary.get("generic_source_urls"),
                "by_source_store": generic_source_summary.get("by_source_store"),
                "by_candidate_status": generic_source_summary.get("by_candidate_status"),
            },
            "prize_source_store_lines": {
                "line_rows": prize_source_store_summary.get("line_rows"),
                "mismatch_rows": prize_source_store_summary.get("mismatch_rows"),
                "missing_image_mismatch_rows": prize_source_store_summary.get("missing_image_mismatch_rows"),
                "by_current_expected": prize_source_store_summary.get("by_current_expected"),
            },
            "prize_line_provider_candidates": {
                "expected_provider_items": prize_line_expected_summary.get("items"),
                "target_items": prize_line_official_detail.get("target_items"),
                "candidate_rows": prize_line_official_detail.get("candidate_rows"),
                "by_status": prize_line_official_detail.get("by_status"),
                "target_by_store": prize_line_official_detail.get("target_by_store"),
            },
            "prize_provider_fallback_images": {
                "target_stores": prize_provider_fallback_summary.get("target_stores"),
                "searched_rows": prize_provider_fallback_summary.get("searched_rows"),
                "fallback_candidate_rows": prize_provider_fallback_summary.get("fallback_candidate_rows"),
                "unresolved_rows": prize_provider_fallback_summary.get("unresolved_rows"),
            },
            "requested_special_goods": {
                "requested": requested_special.get("requested"),
                "already_present": requested_special.get("already_present"),
                "missing": requested_special.get("missing"),
                "with_candidate_image": requested_special.get("with_candidate_image"),
            },
            "focus_missing_images": {
                "focus_count": focus_missing_images.get("focus_count"),
                "focus_rows": focus_missing_images.get("focus_rows"),
                "focus_missing_image_rows": focus_missing_images.get("focus_missing_image_rows"),
                "focus_missing_source_rows": focus_missing_images.get("focus_missing_source_rows"),
                "focus_missing_image_and_source_rows": focus_missing_images.get("focus_missing_image_and_source_rows"),
                "top_focuses": (focus_missing_images.get("focus_summaries") or [])[:10],
            },
            "focus_series_missing_images": {
                "focus_count": focus_series_missing_images.get("focus_count"),
                "missing_image_rows": focus_series_missing_images.get("missing_image_rows"),
                "missing_source_rows": focus_series_missing_images.get("missing_source_rows"),
                "auto_write_ready": focus_series_missing_images.get("auto_write_ready"),
                "top_focuses": (focus_series_missing_images.get("focus_summaries") or [])[:10],
            },
            "public_image_recovery": {
                "missing_image_rows": public_actionability_summary.get("missing_image_rows"),
                "readiness_classified_rows": public_actionability_summary.get("readiness_classified_rows"),
                "unclassified_rows": public_actionability_summary.get("unclassified_rows"),
                "source_first_rows": public_actionability_summary.get("source_first_rows"),
                "review_before_attach_rows": public_actionability_summary.get("review_before_attach_rows"),
                "actionable_image_rows": public_actionability_summary.get("actionable_image_rows"),
                "direct_image_action_queue_rows": public_actionability_summary.get("direct_image_action_queue_rows"),
                "source_detail_candidate_review_rows": public_actionability_summary.get(
                    "source_detail_candidate_review_rows"
                ),
                "source_detail_candidate_recheck_required_rows": public_actionability_summary.get(
                    "source_detail_candidate_recheck_required_rows"
                ),
                "manual_image_research_rows": public_actionability_summary.get("manual_image_research_rows"),
                "focus_pack_rows": public_actionability_summary.get("source_discovery_focus_pack_rows"),
                "focus_pack_count": public_actionability_summary.get("source_discovery_focus_pack_count"),
                "remaining_focus_review_rows": public_actionability_summary.get(
                    "source_discovery_remaining_focus_review_rows"
                ),
                "confirmed_focus_source_rows": public_actionability_summary.get(
                    "source_discovery_confirmed_focus_source_rows"
                ),
                "focus_coverage": public_actionability_summary.get("source_discovery_focus_coverage"),
                "template_rows": public_actionability_summary.get("source_discovery_focus_template_rows"),
                "template_confirmed_rows": public_actionability_summary.get(
                    "source_discovery_focus_template_confirmed_rows"
                ),
                "next_focus_pack_id": public_focus_template_summary.get("next_focus_pack_id"),
                "next_source_store": public_focus_template_summary.get("next_source_store"),
                "next_target_category": public_focus_template_summary.get("next_target_category"),
                "next_focus_pack_rows": public_focus_template_summary.get("next_focus_pack_rows"),
                "next_official_search_url": public_focus_template_summary.get("next_official_search_url"),
                "work_order_pack_count": public_focus_template_summary.get("work_order_pack_count"),
                "current_focus_pack_id": public_source_next_focus_summary.get("focus_pack_id"),
                "current_focus_pack_items": public_source_next_focus_summary.get("pack_items"),
                "focus_pack_progress_queue_count": public_source_next_focus_summary.get(
                    "focus_pack_progress_queue_count"
                ),
                "focus_pack_progress_remaining_rows": public_source_next_focus_summary.get(
                    "focus_pack_progress_remaining_rows"
                ),
                "template_import_updated_rows": public_actionability_summary.get(
                    "source_discovery_focus_template_dry_run_updated_rows"
                ),
                "template_import_skipped_rows": public_actionability_summary.get(
                    "source_discovery_focus_template_dry_run_skipped_rows"
                ),
                "image_attachment_template_rows": public_actionability_summary.get("image_attachment_template_rows"),
                "image_attachment_template_confirmed_rows": public_actionability_summary.get(
                    "image_attachment_template_confirmed_rows"
                ),
                "image_attachment_template_source_update_required_rows": public_actionability_summary.get(
                    "image_attachment_template_source_update_required_rows"
                ),
                "image_attachment_template_representative_review_rows": public_actionability_summary.get(
                    "image_attachment_template_representative_review_rows"
                ),
                "image_attachment_template_dry_run_updated_rows": public_actionability_summary.get(
                    "image_attachment_template_dry_run_updated_rows"
                ),
                "image_attachment_template_dry_run_skipped_rows": public_actionability_summary.get(
                    "image_attachment_template_dry_run_skipped_rows"
                ),
                "auto_apply_enabled": public_actionability_summary.get("auto_apply_enabled"),
            },
            "public_deduplication": {
                "duplicate_groups": public_deduplication_summary.get("duplicate_groups"),
                "duplicate_rows": public_deduplication_summary.get("duplicate_rows"),
                "actionable_groups": public_deduplication_action_summary.get("actionable_groups"),
                "queued_groups": public_deduplication_action_summary.get("queued_groups"),
                "fast_review_groups": public_deduplication_fast_summary.get("fast_review_groups"),
                "held_for_later_groups": public_deduplication_fast_summary.get("held_for_later_groups"),
                "ichiban_reissue_work_order_rows": public_deduplication_action_summary.get(
                    "ichiban_reissue_work_order_rows"
                ),
                "template_items": public_deduplication_template_summary.get("template_items"),
                "template_manual_confirmed_rows": public_deduplication_template_summary.get("manual_confirmed_rows"),
                "template_drop_candidate_rows": public_deduplication_template_summary.get("drop_candidate_rows"),
                "template_import_updated_rows": public_deduplication_template_import.get("updated_rows"),
                "template_import_skipped_rows": public_deduplication_template_import.get("skipped_rows"),
                "auto_merge_enabled": public_deduplication_template_summary.get("auto_merge_enabled"),
                "auto_delete_enabled": public_deduplication_template_summary.get("auto_delete_enabled"),
            },
            "report_consistency_ok": report_consistency.get("ok"),
        },
        "next_actions": goal.get("next_actions", []),
        "workboards": workboards,
        "top_field_workflows": _top(field_batches.get("by_workflow"), 8),
        "top_image_strategies": _top(image_queue.get("by_strategy"), 8),
        "top_image_workstreams": _top(image_batch_plan.get("workstreams"), 8),
        "top_image_exact_url_work": _top(image_exact_url_queue.get("items"), 8),
        "top_ichiban_gap_workflows": _top(ichiban_gap.get("by_workflow"), 8),
        "top_ichiban_replacement_statuses": _top(ichiban_replacement.get("by_status"), 8),
        "top_ichiban_campaign_gap_classifications": _top(ichiban_campaign_gap.get("by_classification"), 8),
        "sources": {name: _display_path(path) for name, path in SOURCES.items()},
    }


def _replacement_extractable_count(report: dict[str, Any]) -> int:
    return _replacement_status_count(report, "replacement_extractable")


def _replacement_status_count(report: dict[str, Any], status_name: str) -> int:
    total = 0
    for status, count in report.get("by_status") or []:
        if status == status_name:
            try:
                total += int(count)
            except (TypeError, ValueError):
                pass
    return total


def _severity_count(report: dict[str, Any], severity_name: str) -> int:
    for severity, count in report.get("by_severity") or []:
        if severity == severity_name:
            try:
                return int(count)
            except (TypeError, ValueError):
                return 0
    return 0


def _reason_count(report: dict[str, Any], reason_name: str) -> int:
    for reason, count in report.get("rejected_reason_counts") or []:
        if reason == reason_name:
            try:
                return int(count)
            except (TypeError, ValueError):
                return 0
    return 0


def _summary_count(summary: dict[str, Any], group_name: str, item_name: str) -> int:
    group = summary.get(group_name)
    if isinstance(group, dict):
        try:
            return int(group.get(item_name) or 0)
        except (TypeError, ValueError):
            return 0
    if isinstance(group, list):
        for name, count in group:
            if name == item_name:
                try:
                    return int(count)
                except (TypeError, ValueError):
                    return 0
    return 0


def _top_mapping(value: Any, limit: int = 5) -> list[list[Any]]:
    if isinstance(value, dict):
        return [
            [name, count]
            for name, count in sorted(value.items(), key=lambda item: (-int(item[1] or 0), str(item[0])))[:limit]
        ]
    if isinstance(value, list):
        return value[:limit]
    return []


def _ichiban_campaign_audit_status(campaign_gap: dict[str, Any], metadata: dict[str, Any]) -> str:
    gap_count = int(campaign_gap.get("campaign_gap_count") or 0)
    safe_release = int(metadata.get("safe_release_url_count") or 0)
    safe_price = int(metadata.get("safe_price_url_count") or 0)
    classifications = {
        str(classification)
        for classification, _count in campaign_gap.get("by_classification") or []
    }
    documented_archive_classes = {
        "archive_shell_no_prize_lineup_detected",
        "official_online_archive_404",
    }
    if safe_release or safe_price:
        return "metadata_import_candidates_available"
    if gap_count and classifications and classifications <= documented_archive_classes:
        return "archive_gaps_documented"
    if gap_count:
        return "campaign_research_needed"
    if metadata.get("urls_with_missing_metadata"):
        return "metadata_manual_only"
    return "stable"


def _ichiban_gap_queue_status(ichiban_gap: dict[str, Any]) -> str:
    if not ichiban_gap.get("total_items"):
        return "stable"
    if ichiban_gap.get("all_gaps_documented"):
        return "archive_gaps_documented"
    if ichiban_gap.get("actionable_items"):
        return "archive_research_needed"
    return "archive_review_needed"


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog Operations Dashboard",
        "",
        f"- Rows: `{payload['summary'].get('rows')}`",
        f"- Duplicate groups: `{payload['summary'].get('duplicate_groups')}`",
        f"- Missing enrichment: `{json.dumps(payload['summary'].get('missing_enrichment'), ensure_ascii=False)}`",
        f"- Store/source mismatches: `{payload['summary'].get('store_source_mismatches')}`",
        "",
        "## Workboards",
    ]
    for board in payload["workboards"]:
        lines.append(
            f"- `{board['area']}`: {board['primary_metric']} {board['primary_label']}, "
            f"{board['secondary_metric']} {board['secondary_label']} -> `{board['artifact']}`"
        )
        if board.get("secondary_artifact"):
            lines.append(f"  - Secondary: `{board['secondary_artifact']}`")
    lines.extend(["", "## Next Actions"])
    for action in payload.get("next_actions", [])[:20]:
        lines.append(f"- P{action.get('priority')} `{action.get('area')}`: {action.get('action')} ({action.get('evidence')})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_html(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    missing = summary.get("missing_enrichment") or {}
    cards = "\n".join(
        f"""
        <article>
          <span>{html.escape(str(board['area']))}</span>
          <strong>{html.escape(str(board['primary_metric']))}</strong>
          <small>{html.escape(str(board['primary_label']))} · {html.escape(str(board['status']))}</small>
          <small>{html.escape(str(board.get('quick_win_metric') or ''))} {html.escape(str(board.get('quick_win_label') or ''))}</small>
          <small>{html.escape(str(board.get('exact_research_metric') or ''))} {html.escape(str(board.get('exact_research_label') or ''))}</small>
          <small>{html.escape(str(board.get('identity_blocked_metric') or ''))} {html.escape(str(board.get('identity_blocked_label') or ''))}</small>
          <p>{html.escape(str(board['next']))}</p>
          <a href="{html.escape(str(board['artifact']))}">Open</a>
        </article>"""
        for board in payload["workboards"]
    )
    actions = "\n".join(
        f"<tr><td>P{html.escape(str(action.get('priority')))}</td><td>{html.escape(str(action.get('area')))}</td><td>{html.escape(str(action.get('action')))}</td><td>{html.escape(str(action.get('evidence')))}</td></tr>"
        for action in payload.get("next_actions", [])[:24]
    )
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deokive Catalog Operations</title>
<style>
body {{ margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #16181d; }}
header {{ padding: 24px; background: #fff; border-bottom: 1px solid #dde2ea; }}
main {{ max-width: 1180px; margin: auto; padding: 22px; }}
h1 {{ margin: 0 0 8px; font-size: 24px; }}
h2 {{ margin: 28px 0 12px; font-size: 18px; }}
.summary, .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
article, table {{ background: #fff; border: 1px solid #dfe3ea; border-radius: 10px; box-shadow: 0 4px 18px rgba(20,28,40,.05); }}
article {{ padding: 14px; }}
article span, small {{ display: block; color: #667085; }}
article strong {{ display: block; font-size: 26px; margin: 4px 0; }}
article p {{ min-height: 44px; color: #303744; }}
table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #edf0f4; vertical-align: top; text-align: left; }}
th {{ background: #f9fafb; }}
a {{ color: #0b57d0; font-weight: 700; }}
</style>
</head>
<body>
<header>
  <h1>Deokive Catalog Operations</h1>
  <div>DB cleanup, enrichment, images, categories, and Ichiban Kuji workboards.</div>
</header>
<main>
  <section class="summary">
    <article><span>Rows</span><strong>{html.escape(str(summary.get('rows')))}</strong></article>
    <article><span>Duplicate groups</span><strong>{html.escape(str(summary.get('duplicate_groups')))}</strong></article>
    <article><span>Missing images</span><strong>{html.escape(str(missing.get('image_url')))}</strong></article>
    <article><span>Missing barcodes</span><strong>{html.escape(str(missing.get('barcode')))}</strong></article>
    <article><span>Field actionable</span><strong>{html.escape(str(summary.get('field_actionable_rows')))}</strong></article>
    <article><span>Confirmed pending</span><strong>{html.escape(str(summary.get('confirmed_pending')))}</strong></article>
    <article><span>Store/source mismatches</span><strong>{html.escape(str(summary.get('store_source_mismatches')))}</strong></article>
  </section>
  <h2>Workboards</h2>
  <section class="grid">{cards}</section>
  <h2>Next Actions</h2>
  <table><thead><tr><th>Priority</th><th>Area</th><th>Action</th><th>Evidence</th></tr></thead><tbody>{actions}</tbody></table>
</main>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()
    payload = build()
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown_output)
    write_html(payload, args.html_output)
    print(
        json.dumps(
            {
                "rows": payload["summary"].get("rows"),
                "workboards": len(payload["workboards"]),
                "next_actions": len(payload.get("next_actions", [])),
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
                "html": str(args.html_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
