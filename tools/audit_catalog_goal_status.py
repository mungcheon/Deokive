from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from catalog_quality_report import load_catalog_rows
from catalog_normalize import canonical_key, normalize_row

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_QUALITY = ROOT / "server" / "catalog_quality_report.json"
DEFAULT_FIELD_QUEUE = ROOT / "server" / "catalog_field_enrichment_queue_current.json"
DEFAULT_FIELD_BATCHES = ROOT / "server" / "catalog_field_review_batches_current.json"
DEFAULT_IMAGE_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue_current.json"
DEFAULT_OFFICIAL_DETAIL_QUEUE = ROOT / "server" / "official_detail_match_queue.json"
DEFAULT_OFFICIAL_DETAIL_BATCHES = ROOT / "server" / "official_detail_review_batches.json"
DEFAULT_STORE_FRONT_QUEUE = ROOT / "server" / "storefront_match_review_queue.json"
DEFAULT_STOREFRONT_BATCHES = ROOT / "server" / "storefront_review_batches.json"
DEFAULT_ICHIBAN_OCR_QUEUE = ROOT / "server" / "ichiban_kuji_ocr_review_queue.json"
DEFAULT_DISCOVERY = ROOT / "server" / "ichiban_discovery_all_current.json"
DEFAULT_METADATA_AUDIT = ROOT / "server" / "ichiban_kuji_metadata_audit.json"
DEFAULT_ICHIBAN_CAMPAIGN_GAP_AUDIT = ROOT / "server" / "ichiban_kuji_campaign_gap_audit.json"
DEFAULT_ICHIBAN_PRIZE_STRUCTURE_AUDIT = ROOT / "server" / "ichiban_kuji_prize_structure_audit.json"
DEFAULT_ANIMATION_CATEGORY_AUDIT = ROOT / "server" / "animation_goods_category_audit.json"
DEFAULT_ANIMATION_ENRICHMENT_PRIORITY = ROOT / "server" / "animation_enrichment_priority_queue.json"
DEFAULT_BARCODE_APPLICABILITY_AUDIT = ROOT / "server" / "catalog_barcode_applicability_audit_current.json"
DEFAULT_METADATA_APPLICABILITY_AUDIT = ROOT / "server" / "catalog_metadata_applicability_audit_current.json"
DEFAULT_SOURCE_IMAGE_APPLICABILITY_AUDIT = ROOT / "server" / "catalog_source_image_applicability_audit_current.json"
DEFAULT_PRIZE_PROVIDER_FALLBACK_AUDIT = ROOT / "server" / "prize_provider_fallback_image_candidates_current.json"
DEFAULT_FOCUS_MISSING_IMAGE_QUEUE = ROOT / "server" / "focus_missing_image_queue_current.json"
DEFAULT_CONFIRMED_IMPORT_AUDIT = ROOT / "server" / "catalog_confirmed_import_queue_audit.json"
DEFAULT_CONFIRMED_ARCHIVE_REPORT = ROOT / "server" / "catalog_confirmed_archive_report.json"
DEFAULT_STORE_SOURCE_NETLOC_AUDIT = ROOT / "server" / "store_source_netloc_audit.json"
DEFAULT_DB = ROOT / "server" / "deokive_dev.db"
DEFAULT_JSON = ROOT / "server" / "catalog_goal_status_audit.json"
DEFAULT_MD = ROOT / "server" / "catalog_goal_status_audit.md"
DEFAULT_HTML = ROOT / "server" / "catalog_goal_status_audit.html"


def _read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _duplicate_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(canonical_key(normalize_row(row)) for row in rows)
    duplicate_groups = [key for key, count in counts.items() if count > 1]
    return {
        "duplicate_groups": len(duplicate_groups),
        "duplicate_rows": sum(counts[key] for key in duplicate_groups),
    }


def _db_summary(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {"exists": False}
    with sqlite3.connect(db_path) as conn:
        active_rows = conn.execute("select count(*) from goods_catalog where is_active = 1").fetchone()[0]
        total_rows = conn.execute("select count(*) from goods_catalog").fetchone()[0]
    return {"exists": True, "total_rows": total_rows, "active_rows": active_rows}


def _review_queue_summary(
    official_detail: dict[str, Any],
    official_detail_batches: dict[str, Any],
    storefront: dict[str, Any],
    storefront_batches: dict[str, Any],
    ichiban_ocr: dict[str, Any],
) -> dict[str, Any]:
    return {
        "official_detail": {
            "artifact": "server/official_detail_match_review.html",
            "batch_artifact": "server/official_detail_review_batches.html",
            "target_items": official_detail.get("target_items"),
            "candidate_rows": official_detail.get("candidate_rows"),
            "by_status": official_detail.get("by_status", []),
            "reviewable_seed_rows": official_detail_batches.get("reviewable_seed_rows"),
            "reviewable_candidate_rows": official_detail_batches.get("reviewable_candidate_rows"),
            "by_workflow": official_detail_batches.get("by_workflow", {}),
        },
        "storefront": {
            "artifact": "server/storefront_match_review.html",
            "batch_artifact": "server/storefront_review_batches.html",
            "generic_queue_rows": storefront.get("generic_queue_rows"),
            "fanding_queue_rows": storefront.get("fanding_queue_rows"),
            "reviewable_candidates": storefront.get("reviewable_candidates"),
            "image_reviewable_candidates": storefront.get("image_reviewable_candidates"),
            "image_reviewable_seed_rows": storefront.get("image_reviewable_seed_rows"),
            "release_only_reviewable_candidates": storefront.get("release_only_reviewable_candidates"),
            "release_only_seed_rows": storefront.get("release_only_seed_rows"),
            "manual_only_rows": storefront.get("manual_only_rows"),
            "reviewable_seed_rows": storefront_batches.get("reviewable_seed_rows"),
            "reviewable_candidate_rows": storefront_batches.get("reviewable_candidate_rows"),
            "by_workflow": storefront_batches.get("by_workflow", {}),
        },
        "ichiban_ocr": {
            "artifact": "server/ichiban_kuji_ocr_review.html",
            "markdown": "server/ichiban_kuji_ocr_review_queue.md",
            "rows": ichiban_ocr.get("rows"),
            "primary_review_rows": ichiban_ocr.get("primary_review_rows"),
            "by_campaign": ichiban_ocr.get("by_campaign", []),
        },
    }


def _next_actions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if payload["duplicate_groups"]:
        actions.append(
            {
                "priority": 1,
                "area": "dedupe",
                "action": "Run tools/dedupe_catalog.py --write and sync DB after review.",
                "evidence": f"{payload['duplicate_groups']} duplicate groups",
            }
        )
    review = payload.get("review_queues", {})
    storefront = review.get("storefront", {})
    storefront_seed_rows = storefront.get("reviewable_seed_rows") or storefront.get("image_reviewable_seed_rows") or 0
    storefront_candidates = storefront.get("reviewable_candidate_rows") or storefront.get("reviewable_candidates") or 0
    if storefront_candidates:
        actions.append(
            {
                "priority": 10,
                "area": "storefront images",
                "action": "Open server/storefront_review_batches.html first, confirm exact Fanding/storefront product rows, then run tools/import_confirmed_storefront_matches.py --write.",
                "evidence": f"{storefront_seed_rows} reviewable seed rows, {storefront_candidates} candidate cards",
            }
        )
    official = review.get("official_detail", {})
    reviewable_seed_rows = official.get("reviewable_seed_rows") or 0
    strong_count = 0
    needs_review_count = 0
    for status, count in official.get("by_status", []):
        if status == "strong_review_candidate":
            strong_count = count
        if status == "needs_manual_title_review":
            needs_review_count = count
    if reviewable_seed_rows or strong_count or needs_review_count:
        actions.append(
            {
                "priority": 20,
                "area": "official detail images",
                "action": "Open server/official_detail_review_batches.html first, confirm exact official detail candidates, then run tools/import_confirmed_official_detail_matches.py --write.",
                "evidence": f"{reviewable_seed_rows} reviewable seed rows; raw queue has {strong_count} strong, {needs_review_count} needs title review",
            }
        )
    ichiban = review.get("ichiban_ocr", {})
    if ichiban.get("primary_review_rows"):
        actions.append(
            {
                "priority": 30,
                "area": "Ichiban Kuji history",
                "action": "Open server/ichiban_kuji_ocr_review.html, fill confirmed OCR names, then run tools/import_confirmed_ichiban_ocr_rows.py --write.",
                "evidence": f"{ichiban.get('primary_review_rows')} primary OCR review rows",
            }
        )
    gaps = payload.get("ichiban_campaign_gaps") or {}
    gap_count = gaps.get("campaign_gap_count") or 0
    if gap_count:
        classifications = ", ".join(
            f"{classification}: {count}"
            for classification, count in gaps.get("by_classification", [])
        )
        actions.append(
            {
                "priority": 35,
                "area": "Ichiban Kuji campaign gaps",
                "action": "Open server/ichiban_kuji_campaign_gap_audit.md and keep archive/404 campaigns out of auto-merge unless a replacement official URL or prize-lineup evidence is found.",
                "evidence": f"{gap_count} campaign gaps; {classifications}",
            }
        )
    metadata = payload.get("ichiban_metadata") or {}
    if (
        metadata.get("rows_missing_release_date")
        or metadata.get("rows_missing_official_price_jpy")
    ) and not (
        metadata.get("safe_release_url_count")
        or metadata.get("safe_price_url_count")
    ):
        actions.append(
            {
                "priority": 36,
                "area": "Ichiban Kuji metadata",
                "action": "Keep missing old-campaign release dates/prices blank until exact official labels are found; current audit found no safe auto-fill candidates.",
                "evidence": (
                    f"{metadata.get('rows_missing_release_date')} release-date gaps, "
                    f"{metadata.get('rows_missing_official_price_jpy')} price gaps, "
                    "0 safe URL candidates"
                ),
            }
        )
    missing = payload.get("missing_enrichment") or {}
    if missing.get("barcode"):
        barcode = payload.get("barcode_applicability") or {}
        actionable = barcode.get("actionable_barcode_rows")
        kuji_not_public = barcode.get("kuji_not_public_barcode_rows")
        evidence = f"{missing.get('barcode')} missing barcodes"
        if actionable is not None:
            evidence += f"; {actionable} actionable"
        if kuji_not_public is not None:
            evidence += f"; {kuji_not_public} kuji rows without public JAN expectation"
        actions.append(
            {
                "priority": 40,
                "area": "barcodes",
                "action": "Open server/catalog_field_enrichment_review.html, copy confirmed field JSON rows, then run tools/import_confirmed_catalog_field_rows.py --write.",
                "evidence": evidence,
            }
        )
    animation_priority = payload.get("animation_enrichment_priority") or {}
    if animation_priority.get("queue_rows"):
        top_group = (animation_priority.get("items") or [{}])[0]
        actions.append(
            {
                "priority": 42,
                "area": "animation goods exact sources",
                "action": "Open server/animation_enrichment_priority_queue.html and process top category/store groups before image attachment.",
                "evidence": (
                    f"{animation_priority.get('queue_rows')} animation rows need source/image work; "
                    f"top group {top_group.get('category')} / {top_group.get('source_store')}: {top_group.get('rows')} rows"
                ),
            }
        )
    field_batches = payload.get("field_batches") or {}
    if field_batches.get("actionable_rows"):
        top_workflow = (field_batches.get("by_workflow") or [["", 0]])[0]
        actions.append(
            {
                "priority": 41,
                "area": "field review batches",
                "action": "Open server/catalog_field_review_batches.html to process missing source/image/date/price/barcode batches by store and field.",
                "evidence": (
                    f"{field_batches.get('actionable_rows')} actionable rows, "
                    f"{field_batches.get('batch_count')} batches; top workflow {top_workflow[0]}: {top_workflow[1]}"
                ),
            }
        )
    fallback = payload.get("prize_provider_fallback_images") or {}
    fallback_summary = fallback.get("summary") or {}
    if fallback_summary.get("fallback_candidate_rows"):
        actions.append(
            {
                "priority": 43,
                "area": "prize image fallback review",
                "action": "Open server/prize_provider_fallback_image_candidates_current.html and manually confirm whether the official fallback candidate is the same product line before importing any image URL.",
                "evidence": (
                    f"{fallback_summary.get('fallback_candidate_rows')} review-only fallback candidates "
                    f"from {', '.join(fallback_summary.get('target_stores') or [])}"
                ),
            }
        )
    focus_missing = payload.get("focus_missing_images") or {}
    if focus_missing.get("focus_missing_image_rows"):
        top_focuses = [
            item
            for item in focus_missing.get("focus_summaries") or []
            if item.get("missing_image_rows")
        ]
        top_focus = top_focuses[0] if top_focuses else {}
        actions.append(
            {
                "priority": 44,
                "area": "focus missing image queue",
                "action": "Open server/focus_missing_image_queue_current.html and process requested series/collab rows by exact source page before image attachment.",
                "evidence": (
                    f"{focus_missing.get('focus_missing_image_rows')} focus rows missing images; "
                    f"top focus {top_focus.get('focus_label')}: {top_focus.get('missing_image_rows')}"
                ),
            }
        )
    confirmed = payload.get("confirmed_import_queues") or {}
    for workflow in confirmed.get("workflows", []):
        status = workflow.get("status")
        if status not in {
            "template_ready_no_confirmed_file",
            "confirmed_rows_pending_import",
            "confirmed_rows_all_skipped",
        }:
            continue
        actions.append(
            {
                "priority": 45,
                "area": f"confirmed queue: {workflow.get('name')}",
                "action": workflow.get("next_action"),
                "evidence": (
                    f"status {status}; confirmed {workflow.get('manual_confirmed_true')}; "
                    f"template {workflow.get('template_items')}"
                ),
            }
        )
    archive_report = payload.get("confirmed_archive") or {}
    archive_summary = archive_report.get("summary") or {}
    if archive_summary.get("archivable_items"):
        actions.append(
            {
                "priority": 46,
                "area": "confirmed queue archive",
                "action": "Run tools/archive_completed_confirmed_rows.py --write to move completed/duplicate confirmed rows into archive files.",
                "evidence": f"{archive_summary.get('archivable_items')} safe rows can be archived",
            }
        )
    source_audit = payload.get("store_source_netloc_audit") or {}
    store_wrong = 0
    external_evidence = 0
    for severity, count in source_audit.get("by_severity", []):
        if severity == "store_probably_wrong":
            store_wrong = count
        elif severity == "external_evidence_source":
            external_evidence = count
    if store_wrong:
        actions.append(
            {
                "priority": 15,
                "area": "source store integrity",
                "action": "Open server/store_source_netloc_audit.md, confirm official-host mismatches, then run tools/import_confirmed_source_store_rows.py --write.",
                "evidence": f"{store_wrong} source_store values point at another official store host",
            }
        )
    if external_evidence:
        actions.append(
            {
                "priority": 47,
                "area": "external evidence sources",
                "action": "Review server/store_source_netloc_audit.md and replace external evidence URLs only when exact maker/store URLs become available.",
                "evidence": f"{external_evidence} rows intentionally rely on retailer/anime/news evidence",
            }
        )
    actions.sort(key=lambda item: int(item["priority"]))
    return actions


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_catalog_rows(args.seed)
    quality = _read_json(args.quality, {})
    field_queue = _read_json(args.field_queue, {})
    field_batches = _read_json(args.field_batches, {})
    image_queue = _read_json(args.image_queue, {})
    official_detail = _read_json(args.official_detail_queue, {})
    official_detail_batches = _read_json(args.official_detail_batches, {})
    storefront = _read_json(args.storefront_queue, {})
    storefront_batches = _read_json(args.storefront_batches, {})
    ichiban_ocr = _read_json(args.ichiban_ocr_queue, {})
    discovery = _read_json(args.discovery, {})
    metadata = _read_json(args.metadata_audit, {})
    ichiban_gap = _read_json(args.ichiban_campaign_gap_audit, {})
    ichiban_prize_structure = _read_json(args.ichiban_prize_structure_audit, {})
    animation_categories = _read_json(args.animation_category_audit, {})
    animation_enrichment_priority = _read_json(args.animation_enrichment_priority, {})
    barcode_applicability = _read_json(args.barcode_applicability_audit, {})
    metadata_applicability = _read_json(args.metadata_applicability_audit, {})
    source_image_applicability = _read_json(args.source_image_applicability_audit, {})
    prize_provider_fallback = _read_json(args.prize_provider_fallback_audit, {})
    focus_missing_images = _read_json(args.focus_missing_image_queue, {})
    confirmed_import_queues = _read_json(args.confirmed_import_audit, {})
    confirmed_archive = _read_json(args.confirmed_archive_report, {})
    store_source_netloc_audit = _read_json(args.store_source_netloc_audit, {})

    by_store = Counter(str(row.get("source_store") or "") for row in rows if isinstance(row, dict))
    by_category = Counter(str(row.get("category") or "") for row in rows if isinstance(row, dict))

    payload = {
        "seed": str(args.seed),
        "rows": len(rows),
        **_duplicate_summary([row for row in rows if isinstance(row, dict)]),
        "db": _db_summary(args.db),
        "top_source_stores": by_store.most_common(25),
        "top_categories": by_category.most_common(25),
        "missing_enrichment": quality.get("missing_enrichment"),
        "field_queue": {
            "missing_total": field_queue.get("missing_total"),
            "actionable_missing_total": field_queue.get("actionable_missing_total"),
            "non_actionable_missing_total": field_queue.get("non_actionable_missing_total"),
            "by_field": field_queue.get("by_field", []),
            "by_strategy": field_queue.get("by_strategy", []),
        },
        "field_batches": {
            "artifact": "server/catalog_field_review_batches.html",
            "markdown": "server/catalog_field_review_batches.md",
            "queue_rows": field_batches.get("queue_rows"),
            "actionable_rows": field_batches.get("actionable_rows"),
            "non_actionable_rows": field_batches.get("non_actionable_rows"),
            "batch_count": field_batches.get("batch_count"),
            "by_field": field_batches.get("by_field", []),
            "by_workflow": field_batches.get("by_workflow", []),
            "by_applicability": field_batches.get("by_applicability", []),
        },
        "image_queue": {
            "missing_images": image_queue.get("missing_images"),
            "by_strategy": image_queue.get("by_strategy", []),
            "top_strategy_stores": image_queue.get("top_strategy_stores", [])[:25],
        },
        "review_queues": _review_queue_summary(
            official_detail,
            official_detail_batches,
            storefront,
            storefront_batches,
            ichiban_ocr,
        ),
        "ichiban_discovery": {
            "campaign_file": discovery.get("campaign_file"),
            "existing_rows": discovery.get("existing_rows"),
            "discovered_new_rows": discovery.get("discovered_new_rows"),
            "selected_categories": discovery.get("selected_categories"),
            "by_category": discovery.get("by_category"),
        },
        "ichiban_metadata": {
            "urls_with_missing_metadata": metadata.get("urls_with_missing_metadata"),
            "audited_urls": metadata.get("audited_urls"),
            "failures": len(metadata.get("failures") or []),
            "rows_missing_release_date": metadata.get("rows_missing_release_date"),
            "rows_missing_official_price_jpy": metadata.get("rows_missing_official_price_jpy"),
            "safe_release_url_count": metadata.get("safe_release_url_count"),
            "safe_price_url_count": metadata.get("safe_price_url_count"),
        },
        "ichiban_campaign_gaps": {
            "campaign_count": ichiban_gap.get("campaign_count"),
            "seeded_campaign_url_count": ichiban_gap.get("seeded_campaign_url_count"),
            "campaign_gap_count": ichiban_gap.get("campaign_gap_count"),
            "audited_gap_count": ichiban_gap.get("audited_gap_count"),
            "by_status": ichiban_gap.get("by_status", []),
            "by_classification": ichiban_gap.get("by_classification", []),
            "zero_signal_summary": ichiban_gap.get("zero_signal_summary", {}),
            "artifact": "server/ichiban_kuji_campaign_gap_audit.md",
        },
        "ichiban_prize_structure": {
            "campaign_count": ichiban_prize_structure.get("campaign_count"),
            "seeded_campaign_url_count": ichiban_prize_structure.get("seeded_campaign_url_count"),
            "campaign_without_seed_rows_count": ichiban_prize_structure.get("campaign_without_seed_rows_count"),
            "prize_rows": ichiban_prize_structure.get("prize_rows"),
            "missing_sub_series_rows": ichiban_prize_structure.get("missing_sub_series_rows"),
            "fillable_sub_series_rows": ichiban_prize_structure.get("fillable_sub_series_rows"),
            "artifact": "server/ichiban_kuji_prize_structure_audit.md",
        },
        "animation_goods_categories": {
            "rows": animation_categories.get("rows"),
            "category_count": animation_categories.get("category_count"),
            "normalization_suggestions": len(animation_categories.get("normalization_suggestions") or []),
            "unknown_categories": len(animation_categories.get("unknown_categories") or []),
            "category_families": animation_categories.get("category_families", []),
            "artifact": "server/animation_goods_category_audit.md",
            "normalize_report": "server/animation_goods_category_normalize_current_dryrun.json",
        },
        "animation_enrichment_priority": {
            "queue_groups": animation_enrichment_priority.get("queue_groups"),
            "queue_rows": animation_enrichment_priority.get("queue_rows"),
            "missing_image_rows": animation_enrichment_priority.get("missing_image_rows"),
            "missing_source_rows": animation_enrichment_priority.get("missing_source_rows"),
            "by_workflow": animation_enrichment_priority.get("by_workflow", []),
            "items": animation_enrichment_priority.get("items", []),
            "artifact": "server/animation_enrichment_priority_queue.html",
        },
        "barcode_applicability": {
            "barcode_missing_rows": barcode_applicability.get("barcode_missing_rows"),
            "actionable_barcode_rows": barcode_applicability.get("actionable_barcode_rows"),
            "non_actionable_barcode_rows": barcode_applicability.get("non_actionable_barcode_rows"),
            "kuji_not_public_barcode_rows": barcode_applicability.get("kuji_not_public_barcode_rows"),
            "manual_only_or_not_public_rows": barcode_applicability.get("manual_only_or_not_public_rows"),
            "by_applicability": barcode_applicability.get("by_applicability", []),
            "actionable_top_source_stores": barcode_applicability.get("actionable_top_source_stores", []),
            "artifact": "server/catalog_barcode_applicability_audit_current.md",
        },
        "metadata_applicability": {
            "metadata_missing_rows": metadata_applicability.get("metadata_missing_rows"),
            "metadata_actionable_rows": metadata_applicability.get("metadata_actionable_rows"),
            "metadata_automation_candidate_rows": metadata_applicability.get("metadata_automation_candidate_rows"),
            "fields": metadata_applicability.get("fields", {}),
            "artifact": "server/catalog_metadata_applicability_audit_current.md",
        },
        "source_image_applicability": {
            "source_image_missing_rows": source_image_applicability.get("source_image_missing_rows"),
            "source_image_actionable_rows": source_image_applicability.get("source_image_actionable_rows"),
            "source_image_automation_candidate_rows": source_image_applicability.get("source_image_automation_candidate_rows"),
            "missing_image_and_source_url": source_image_applicability.get("missing_image_and_source_url"),
            "has_image_but_missing_source_url": source_image_applicability.get("has_image_but_missing_source_url"),
            "image_provider_candidate_items": source_image_applicability.get("image_provider_candidate_items"),
            "image_manual_or_blocked_items": source_image_applicability.get("image_manual_or_blocked_items"),
            "fields": source_image_applicability.get("fields", {}),
            "artifact": "server/catalog_source_image_applicability_audit_current.md",
        },
        "prize_provider_fallback_images": {
            "summary": prize_provider_fallback.get("summary", {}),
            "artifact": "server/prize_provider_fallback_image_candidates_current.html",
            "markdown": "server/prize_provider_fallback_image_candidates_current.md",
        },
        "focus_missing_images": {
            "focus_count": focus_missing_images.get("focus_count"),
            "focus_rows": focus_missing_images.get("focus_rows"),
            "focus_missing_image_rows": focus_missing_images.get("focus_missing_image_rows"),
            "focus_missing_source_rows": focus_missing_images.get("focus_missing_source_rows"),
            "focus_missing_image_and_source_rows": focus_missing_images.get("focus_missing_image_and_source_rows"),
            "focus_summaries": focus_missing_images.get("focus_summaries", []),
            "artifact": "server/focus_missing_image_queue_current.html",
            "markdown": "server/focus_missing_image_queue_current.md",
        },
        "confirmed_import_queues": {
            "summary": confirmed_import_queues.get("summary", {}),
            "workflows": confirmed_import_queues.get("workflows", []),
            "artifact": "server/catalog_confirmed_import_queue_audit.md",
        },
        "confirmed_archive": {
            "summary": confirmed_archive.get("summary", {}),
            "workflows": confirmed_archive.get("workflows", []),
            "report": "server/catalog_confirmed_archive_report.json",
        },
        "store_source_netloc_audit": {
            "mismatch_count": store_source_netloc_audit.get("mismatch_count"),
            "by_severity": store_source_netloc_audit.get("by_severity", []),
            "artifact": "server/store_source_netloc_audit.md",
        },
        "status_notes": [
            "Open server/catalog_operations_dashboard.html first for the current catalog workboard index.",
            "Duplicate groups are expected to remain zero after dedupe.",
            "Image/source/date/price queues are intentionally conservative; broad search pages are not treated as proof.",
            "Ichiban Kuji campaign discovery found no new official campaigns in the configured categories during the latest dry run.",
            "Ichiban Kuji metadata still has old campaign pages without safe price/release labels; keep those fields blank unless official evidence is added.",
            "Animation goods categories are audited separately; zero unknown categories means the current app category taxonomy is covering the group.",
            "Animation enrichment priority queue ranks category/store groups for exact source discovery before image attachment.",
            "Confirmed import queue audit shows whether manually reviewed rows are pending, skipped, duplicated, or ready for import.",
            "Completed confirmed rows can be archived after import reports prove they are already applied or canonical duplicates.",
        ],
    }
    payload["next_actions"] = _next_actions(payload)
    return payload


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog Goal Status Audit",
        "",
        "- Operations dashboard: `server/catalog_operations_dashboard.html`",
        f"- Rows: `{payload['rows']}`",
        f"- Duplicate groups: `{payload['duplicate_groups']}`",
        f"- Duplicate rows: `{payload['duplicate_rows']}`",
        f"- DB active rows: `{payload['db'].get('active_rows')}`",
        f"- Missing enrichment: `{json.dumps(payload.get('missing_enrichment'), ensure_ascii=False)}`",
        "",
        "## Field Queue",
        "",
    ]
    for field, count in payload["field_queue"].get("by_field", []):
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(["", "## Barcode Applicability", ""])
    barcode = payload.get("barcode_applicability") or {}
    for key in (
        "barcode_missing_rows",
        "actionable_barcode_rows",
        "non_actionable_barcode_rows",
        "kuji_not_public_barcode_rows",
        "manual_only_or_not_public_rows",
    ):
        lines.append(f"- `{key}`: `{barcode.get(key)}`")
    lines.append(f"- Artifact: `{barcode.get('artifact')}`")
    for item in barcode.get("by_applicability", [])[:10]:
        lines.append(f"- applicability `{item.get('value')}`: `{item.get('rows')}`")
    lines.extend(["", "## Metadata Applicability", ""])
    metadata_applicability = payload.get("metadata_applicability") or {}
    lines.append(f"- `metadata_missing_rows`: `{metadata_applicability.get('metadata_missing_rows')}`")
    lines.append(f"- `metadata_actionable_rows`: `{metadata_applicability.get('metadata_actionable_rows')}`")
    lines.append(
        f"- `metadata_automation_candidate_rows`: `{metadata_applicability.get('metadata_automation_candidate_rows')}`"
    )
    lines.append(f"- Artifact: `{metadata_applicability.get('artifact')}`")
    for field, summary in (metadata_applicability.get("fields") or {}).items():
        lines.append(f"- `{field}` missing/actionable/auto: `{summary.get('missing_rows')}` / `{summary.get('actionable_rows')}` / `{summary.get('automation_candidate_rows')}`")
    lines.extend(["", "## Source/Image Applicability", ""])
    source_image = payload.get("source_image_applicability") or {}
    for key in (
        "source_image_missing_rows",
        "source_image_actionable_rows",
        "source_image_automation_candidate_rows",
        "missing_image_and_source_url",
        "has_image_but_missing_source_url",
        "image_provider_candidate_items",
        "image_manual_or_blocked_items",
    ):
        lines.append(f"- `{key}`: `{source_image.get(key)}`")
    lines.append(f"- Artifact: `{source_image.get('artifact')}`")
    for field, summary in (source_image.get("fields") or {}).items():
        lines.append(f"- `{field}` missing/actionable/auto: `{summary.get('missing_rows')}` / `{summary.get('actionable_rows')}` / `{summary.get('automation_candidate_rows')}`")
    lines.extend(["", "## Prize Provider Fallback Images", ""])
    fallback = payload.get("prize_provider_fallback_images") or {}
    fallback_summary = fallback.get("summary") or {}
    for key in ("searched_rows", "fallback_candidate_rows", "unresolved_rows"):
        lines.append(f"- `{key}`: `{fallback_summary.get(key)}`")
    lines.append(f"- Target stores: `{', '.join(fallback_summary.get('target_stores') or [])}`")
    lines.append(f"- Artifact: `{fallback.get('artifact')}`")
    lines.append(f"- Markdown: `{fallback.get('markdown')}`")
    lines.append("- Policy: review-only; do not import until exact product line/title is manually confirmed.")
    lines.extend(["", "## Focus Missing Images", ""])
    focus_missing = payload.get("focus_missing_images") or {}
    for key in (
        "focus_count",
        "focus_rows",
        "focus_missing_image_rows",
        "focus_missing_source_rows",
        "focus_missing_image_and_source_rows",
    ):
        lines.append(f"- `{key}`: `{focus_missing.get(key)}`")
    lines.append(f"- Artifact: `{focus_missing.get('artifact')}`")
    lines.append(f"- Markdown: `{focus_missing.get('markdown')}`")
    for item in (focus_missing.get("focus_summaries") or [])[:10]:
        lines.append(
            f"- `{item.get('focus_label')}` rows/missing image/source: "
            f"`{item.get('rows')}` / `{item.get('missing_image_rows')}` / `{item.get('missing_source_rows')}`"
        )
    lines.extend(["", "## Image Queue", ""])
    for strategy, count in payload["image_queue"].get("by_strategy", []):
        lines.append(f"- `{strategy}`: `{count}`")
    lines.extend(["", "## Field Review Batches", ""])
    field_batches = payload.get("field_batches") or {}
    for key in ("queue_rows", "actionable_rows", "non_actionable_rows", "batch_count"):
        lines.append(f"- `{key}`: `{field_batches.get(key)}`")
    lines.append(f"- Artifact: `{field_batches.get('artifact')}`")
    for workflow, count in field_batches.get("by_workflow", [])[:12]:
        lines.append(f"- workflow `{workflow}`: `{count}`")
    lines.extend(["", "## Review Queues", ""])
    review = payload.get("review_queues", {})
    for name, data in review.items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- artifact: `{data.get('artifact')}`")
        for key, value in data.items():
            if key == "artifact":
                continue
            lines.append(f"- `{key}`: `{value}`")
        lines.append("")
    lines.extend(["## Next Actions", ""])
    for action in payload.get("next_actions", []):
        lines.append(f"- P{action['priority']} `{action['area']}`: {action['action']} ({action['evidence']})")
    lines.extend(["", "## Ichiban Discovery", ""])
    ichiban = payload["ichiban_discovery"]
    lines.append(f"- Existing campaign rows: `{ichiban.get('existing_rows')}`")
    lines.append(f"- New official campaign rows discovered: `{ichiban.get('discovered_new_rows')}`")
    for category, counts in (ichiban.get("by_category") or {}).items():
        lines.append(
            f"- `{category}`: official `{counts.get('official_rows')}`, new `{counts.get('new_rows')}`"
        )
    lines.extend(["", "## Ichiban Metadata", ""])
    meta = payload["ichiban_metadata"]
    for key, value in meta.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Ichiban Campaign Gaps", ""])
    gaps = payload["ichiban_campaign_gaps"]
    for key in ("campaign_count", "seeded_campaign_url_count", "campaign_gap_count", "audited_gap_count"):
        lines.append(f"- `{key}`: `{gaps.get(key)}`")
    for status, count in gaps.get("by_status", []):
        lines.append(f"- status `{status}`: `{count}`")
    for classification, count in gaps.get("by_classification", []):
        lines.append(f"- classification `{classification}`: `{count}`")
    lines.append(f"- Artifact: `{gaps.get('artifact')}`")
    lines.extend(["", "## Ichiban Prize Structure", ""])
    structure = payload["ichiban_prize_structure"]
    for key in (
        "campaign_count",
        "seeded_campaign_url_count",
        "campaign_without_seed_rows_count",
        "prize_rows",
        "missing_sub_series_rows",
        "fillable_sub_series_rows",
    ):
        lines.append(f"- `{key}`: `{structure.get(key)}`")
    lines.append(f"- Artifact: `{structure.get('artifact')}`")
    lines.extend(["", "## Animation Goods Categories", ""])
    animation = payload["animation_goods_categories"]
    lines.append(f"- Rows: `{animation.get('rows')}`")
    lines.append(f"- Category count: `{animation.get('category_count')}`")
    lines.append(f"- Normalization suggestions: `{animation.get('normalization_suggestions')}`")
    lines.append(f"- Unknown categories: `{animation.get('unknown_categories')}`")
    lines.append(f"- Artifact: `{animation.get('artifact')}`")
    for item in animation.get("category_families", [])[:20]:
        lines.append(f"- `{item.get('family')}`: `{item.get('rows')}`")
    animation_priority = payload.get("animation_enrichment_priority") or {}
    lines.extend(["", "## Animation Enrichment Priority", ""])
    lines.append(f"- Queue groups: `{animation_priority.get('queue_groups')}`")
    lines.append(f"- Queue rows: `{animation_priority.get('queue_rows')}`")
    lines.append(f"- Missing image rows: `{animation_priority.get('missing_image_rows')}`")
    lines.append(f"- Missing source rows: `{animation_priority.get('missing_source_rows')}`")
    lines.append(f"- Artifact: `{animation_priority.get('artifact')}`")
    for workflow, count in animation_priority.get("by_workflow", [])[:10]:
        lines.append(f"- workflow `{workflow}`: `{count}`")
    for item in animation_priority.get("items", [])[:10]:
        lines.append(
            f"- P{item.get('priority')} `{item.get('workflow')}` / `{item.get('category')}` / "
            f"`{item.get('source_store')}`: `{item.get('rows')}` rows"
        )
    lines.extend(["", "## Confirmed Import Queues", ""])
    confirmed = payload.get("confirmed_import_queues") or {}
    summary = confirmed.get("summary") or {}
    for key in (
        "workflow_count",
        "confirmed_files",
        "manual_confirmed_true",
        "template_items",
        "updated_rows",
        "skipped_rows",
        "duplicates",
    ):
        lines.append(f"- `{key}`: `{summary.get(key)}`")
    lines.append(f"- Artifact: `{confirmed.get('artifact')}`")
    for workflow in confirmed.get("workflows", []):
        lines.append(
            f"- `{workflow.get('name')}`: `{workflow.get('status')}`; "
            f"confirmed `{workflow.get('manual_confirmed_true')}`; "
            f"template `{workflow.get('template_items')}`"
        )
    lines.extend(["", "## Confirmed Queue Archive", ""])
    archive = payload.get("confirmed_archive") or {}
    archive_summary = archive.get("summary") or {}
    for key in ("queued_items", "archivable_items", "remaining_items", "archived_items", "archive_items"):
        lines.append(f"- `{key}`: `{archive_summary.get(key)}`")
    lines.append(f"- Report: `{archive.get('report')}`")
    lines.extend(["", "## Store Source Netloc Audit", ""])
    source_audit = payload.get("store_source_netloc_audit") or {}
    lines.append(f"- Mismatches: `{source_audit.get('mismatch_count')}`")
    lines.append(f"- Artifact: `{source_audit.get('artifact')}`")
    for severity, count in source_audit.get("by_severity", []):
        lines.append(f"- `{severity}`: `{count}`")
    lines.extend(["", "## Notes", ""])
    for note in payload["status_notes"]:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def _html_escape(value: Any) -> str:
    import html

    return html.escape(str(value or ""), quote=True)


def write_html(payload: dict[str, Any], path: Path) -> None:
    missing = payload.get("missing_enrichment") or {}
    animation = payload.get("animation_goods_categories") or {}
    gaps = payload.get("ichiban_campaign_gaps") or {}
    structure = payload.get("ichiban_prize_structure") or {}
    confirmed = payload.get("confirmed_import_queues") or {}
    confirmed_summary = confirmed.get("summary") or {}
    archive = payload.get("confirmed_archive") or {}
    archive_summary = archive.get("summary") or {}
    source_audit = payload.get("store_source_netloc_audit") or {}
    animation_priority = payload.get("animation_enrichment_priority") or {}
    focus_missing = payload.get("focus_missing_images") or {}
    field_batches = payload.get("field_batches") or {}
    field_cards = "\n".join(
        f"<article><span>{_html_escape(field)}</span><strong>{_html_escape(count)}</strong></article>"
        for field, count in payload["field_queue"].get("by_field", [])
    )
    image_rows = "\n".join(
        f"<tr><td>{_html_escape(strategy)}</td><td>{_html_escape(count)}</td></tr>"
        for strategy, count in payload["image_queue"].get("by_strategy", [])
    )
    review_cards = []
    for name, data in (payload.get("review_queues") or {}).items():
        detail_rows = "\n".join(
            f"<li><span>{_html_escape(key)}</span><strong>{_html_escape(value)}</strong></li>"
            for key, value in data.items()
            if key != "artifact"
        )
        review_cards.append(
            f"""
        <article class="review">
          <h3>{_html_escape(name)}</h3>
          <a href="{_html_escape(data.get('artifact'))}">Open artifact</a>
          <ul>{detail_rows}</ul>
        </article>"""
        )
    confirmed_cards = "\n".join(
        f"""
        <article class="review">
          <h3>{_html_escape(workflow.get('name'))}</h3>
          <a href="{_html_escape(workflow.get('review_artifact'))}">Open review</a>
          <ul>
            <li><span>Status</span><strong>{_html_escape(workflow.get('status'))}</strong></li>
            <li><span>Confirmed</span><strong>{_html_escape(workflow.get('manual_confirmed_true'))}</strong></li>
            <li><span>Template items</span><strong>{_html_escape(workflow.get('template_items'))}</strong></li>
            <li><span>Next</span><strong>{_html_escape(workflow.get('next_action'))}</strong></li>
          </ul>
        </article>"""
        for workflow in confirmed.get("workflows", [])
    )
    action_rows = "\n".join(
        f"<tr><td>P{_html_escape(action['priority'])}</td><td>{_html_escape(action['area'])}</td><td>{_html_escape(action['action'])}</td><td>{_html_escape(action['evidence'])}</td></tr>"
        for action in payload.get("next_actions", [])
    )
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Deokive Catalog Goal Status</title>
  <style>
    body {{ margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f8fa; color: #15171c; }}
    header {{ padding: 24px; background: #fff; border-bottom: 1px solid #dde2ea; }}
    main {{ max-width: 1180px; margin: auto; padding: 22px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; }}
    .summary, .fields, .reviews {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
    article, table {{ background: #fff; border: 1px solid #dfe3ea; border-radius: 10px; box-shadow: 0 4px 18px rgba(20,28,40,.05); }}
    article {{ padding: 14px; }}
    article span {{ display: block; color: #657082; }}
    strong {{ font-size: 22px; }}
    .missing strong {{ color: #a33b21; }}
    .review h3 {{ margin: 0 0 8px; }}
    .review ul {{ padding: 0; list-style: none; margin: 12px 0 0; }}
    .review li {{ display: flex; justify-content: space-between; gap: 12px; border-top: 1px solid #edf0f4; padding: 7px 0; }}
    .review li strong {{ font-size: 13px; text-align: right; }}
    table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #edf0f4; vertical-align: top; text-align: left; }}
    th {{ background: #f9fafb; }}
    a {{ color: #0b57d0; }}
  </style>
</head>
<body>
  <header>
    <h1>Deokive Catalog Goal Status</h1>
    <div>Current canonical catalog and enrichment workboard.</div>
  </header>
  <main>
    <section class="summary">
      <article><span>Rows</span><strong>{_html_escape(payload['rows'])}</strong></article>
      <article><span>Duplicate groups</span><strong>{_html_escape(payload['duplicate_groups'])}</strong></article>
      <article><span>DB active rows</span><strong>{_html_escape(payload['db'].get('active_rows'))}</strong></article>
      <article class="missing"><span>Missing images</span><strong>{_html_escape(missing.get('image_url'))}</strong></article>
      <article><span>Field batches</span><strong>{_html_escape(field_batches.get('batch_count'))}</strong></article>
      <article><span>Animation categories</span><strong>{_html_escape(animation.get('category_count'))}</strong></article>
      <article><span>Unknown animation categories</span><strong>{_html_escape(animation.get('unknown_categories'))}</strong></article>
      <article><span>Animation source queue</span><strong>{_html_escape(animation_priority.get('queue_rows'))}</strong></article>
      <article><span>Ichiban campaign gaps</span><strong>{_html_escape(gaps.get('campaign_gap_count'))}</strong></article>
      <article><span>Confirmed import rows</span><strong>{_html_escape(confirmed_summary.get('manual_confirmed_true'))}</strong></article>
      <article><span>Archivable confirmed rows</span><strong>{_html_escape(archive_summary.get('archivable_items'))}</strong></article>
      <article><span>Store/source mismatches</span><strong>{_html_escape(source_audit.get('mismatch_count'))}</strong></article>
      <article><span>Focus missing images</span><strong>{_html_escape(focus_missing.get('focus_missing_image_rows'))}</strong></article>
      <article><span>Focus missing sources</span><strong>{_html_escape(focus_missing.get('focus_missing_source_rows'))}</strong></article>
    </section>
    <h2>Missing Fields</h2>
    <section class="fields">{field_cards}</section>
    <h2>Image Queue</h2>
    <table><thead><tr><th>Strategy</th><th>Rows</th></tr></thead><tbody>{image_rows}</tbody></table>
    <h2>Field Review Batches</h2>
    <section class="fields">
      <article><span>Queue rows</span><strong>{_html_escape(field_batches.get('queue_rows'))}</strong></article>
      <article><span>Actionable rows</span><strong>{_html_escape(field_batches.get('actionable_rows'))}</strong></article>
      <article><span>Non-actionable rows</span><strong>{_html_escape(field_batches.get('non_actionable_rows'))}</strong></article>
      <article><span>Batch count</span><strong>{_html_escape(field_batches.get('batch_count'))}</strong></article>
    </section>
    <p><a href="{_html_escape(field_batches.get('artifact'))}">Open field review batches</a></p>
    <h2>Review Queues</h2>
    <section class="reviews">{''.join(review_cards)}</section>
    <h2>Animation Goods Categories</h2>
    <section class="fields">
      <article><span>Rows</span><strong>{_html_escape(animation.get('rows'))}</strong></article>
      <article><span>Category count</span><strong>{_html_escape(animation.get('category_count'))}</strong></article>
      <article><span>Normalization suggestions</span><strong>{_html_escape(animation.get('normalization_suggestions'))}</strong></article>
      <article><span>Unknown categories</span><strong>{_html_escape(animation.get('unknown_categories'))}</strong></article>
      <article><span>Priority queue groups</span><strong>{_html_escape(animation_priority.get('queue_groups'))}</strong></article>
      <article><span>Priority queue rows</span><strong>{_html_escape(animation_priority.get('queue_rows'))}</strong></article>
      <article><span>Missing source rows</span><strong>{_html_escape(animation_priority.get('missing_source_rows'))}</strong></article>
    </section>
    <p><a href="{_html_escape(animation_priority.get('artifact'))}">Open animation enrichment priority queue</a></p>
    <h2>Ichiban Kuji Organization</h2>
    <section class="fields">
      <article><span>Campaigns</span><strong>{_html_escape(gaps.get('campaign_count'))}</strong></article>
      <article><span>Seeded campaign URLs</span><strong>{_html_escape(gaps.get('seeded_campaign_url_count'))}</strong></article>
      <article><span>Campaign gaps</span><strong>{_html_escape(gaps.get('campaign_gap_count'))}</strong></article>
      <article><span>Prize rows</span><strong>{_html_escape(structure.get('prize_rows'))}</strong></article>
      <article><span>Missing sub-series</span><strong>{_html_escape(structure.get('missing_sub_series_rows'))}</strong></article>
      <article><span>Fillable sub-series</span><strong>{_html_escape(structure.get('fillable_sub_series_rows'))}</strong></article>
    </section>
    <h2>Confirmed Import Queues</h2>
    <section class="fields">
      <article><span>Confirmed files</span><strong>{_html_escape(confirmed_summary.get('confirmed_files'))}</strong></article>
      <article><span>Manual confirmed</span><strong>{_html_escape(confirmed_summary.get('manual_confirmed_true'))}</strong></article>
      <article><span>Template items</span><strong>{_html_escape(confirmed_summary.get('template_items'))}</strong></article>
      <article><span>Updated rows</span><strong>{_html_escape(confirmed_summary.get('updated_rows'))}</strong></article>
      <article><span>Skipped rows</span><strong>{_html_escape(confirmed_summary.get('skipped_rows'))}</strong></article>
      <article><span>Duplicates</span><strong>{_html_escape(confirmed_summary.get('duplicates'))}</strong></article>
    </section>
    <section class="reviews">{confirmed_cards}</section>
    <h2>Confirmed Queue Archive</h2>
    <section class="fields">
      <article><span>Queued items</span><strong>{_html_escape(archive_summary.get('queued_items'))}</strong></article>
      <article><span>Archivable items</span><strong>{_html_escape(archive_summary.get('archivable_items'))}</strong></article>
      <article><span>Remaining items</span><strong>{_html_escape(archive_summary.get('remaining_items'))}</strong></article>
      <article><span>Archived items</span><strong>{_html_escape(archive_summary.get('archived_items'))}</strong></article>
      <article><span>Archive total</span><strong>{_html_escape(archive_summary.get('archive_items'))}</strong></article>
    </section>
    <h2>Store Source Netloc Audit</h2>
    <section class="fields">
      <article><span>Mismatches</span><strong>{_html_escape(source_audit.get('mismatch_count'))}</strong></article>
      <article><span>Severity</span><strong>{_html_escape(source_audit.get('by_severity'))}</strong></article>
    </section>
    <h2>Next Actions</h2>
    <table><thead><tr><th>Priority</th><th>Area</th><th>Action</th><th>Evidence</th></tr></thead><tbody>{action_rows}</tbody></table>
  </main>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--field-queue", type=Path, default=DEFAULT_FIELD_QUEUE)
    parser.add_argument("--field-batches", type=Path, default=DEFAULT_FIELD_BATCHES)
    parser.add_argument("--image-queue", type=Path, default=DEFAULT_IMAGE_QUEUE)
    parser.add_argument("--official-detail-queue", type=Path, default=DEFAULT_OFFICIAL_DETAIL_QUEUE)
    parser.add_argument("--official-detail-batches", type=Path, default=DEFAULT_OFFICIAL_DETAIL_BATCHES)
    parser.add_argument("--storefront-queue", type=Path, default=DEFAULT_STORE_FRONT_QUEUE)
    parser.add_argument("--storefront-batches", type=Path, default=DEFAULT_STOREFRONT_BATCHES)
    parser.add_argument("--ichiban-ocr-queue", type=Path, default=DEFAULT_ICHIBAN_OCR_QUEUE)
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--metadata-audit", type=Path, default=DEFAULT_METADATA_AUDIT)
    parser.add_argument("--ichiban-campaign-gap-audit", type=Path, default=DEFAULT_ICHIBAN_CAMPAIGN_GAP_AUDIT)
    parser.add_argument("--ichiban-prize-structure-audit", type=Path, default=DEFAULT_ICHIBAN_PRIZE_STRUCTURE_AUDIT)
    parser.add_argument("--animation-category-audit", type=Path, default=DEFAULT_ANIMATION_CATEGORY_AUDIT)
    parser.add_argument("--animation-enrichment-priority", type=Path, default=DEFAULT_ANIMATION_ENRICHMENT_PRIORITY)
    parser.add_argument("--barcode-applicability-audit", type=Path, default=DEFAULT_BARCODE_APPLICABILITY_AUDIT)
    parser.add_argument("--metadata-applicability-audit", type=Path, default=DEFAULT_METADATA_APPLICABILITY_AUDIT)
    parser.add_argument("--source-image-applicability-audit", type=Path, default=DEFAULT_SOURCE_IMAGE_APPLICABILITY_AUDIT)
    parser.add_argument("--prize-provider-fallback-audit", type=Path, default=DEFAULT_PRIZE_PROVIDER_FALLBACK_AUDIT)
    parser.add_argument("--focus-missing-image-queue", type=Path, default=DEFAULT_FOCUS_MISSING_IMAGE_QUEUE)
    parser.add_argument("--confirmed-import-audit", type=Path, default=DEFAULT_CONFIRMED_IMPORT_AUDIT)
    parser.add_argument("--confirmed-archive-report", type=Path, default=DEFAULT_CONFIRMED_ARCHIVE_REPORT)
    parser.add_argument("--store-source-netloc-audit", type=Path, default=DEFAULT_STORE_SOURCE_NETLOC_AUDIT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    payload = build(args)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown_output)
    write_html(payload, args.html_output)
    print(
        json.dumps(
            {
                "rows": payload["rows"],
                "duplicate_groups": payload["duplicate_groups"],
                "missing_enrichment": payload.get("missing_enrichment"),
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
