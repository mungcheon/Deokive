from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUALITY = ROOT / "server" / "catalog_quality_report.json"
DEFAULT_FIELD_QUEUE = ROOT / "server" / "catalog_field_enrichment_queue_current.json"
DEFAULT_FIELD_BATCHES = ROOT / "server" / "catalog_field_review_batches_current.json"
DEFAULT_IMAGE_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue_current.json"
DEFAULT_IMAGE_BATCHES = ROOT / "server" / "catalog_image_review_batches.json"
DEFAULT_IMAGE_BATCH_PLAN = ROOT / "server" / "catalog_image_enrichment_batch_plan.json"
DEFAULT_IMAGE_PROVIDER_COVERAGE = ROOT / "server" / "catalog_image_provider_coverage_audit.json"
DEFAULT_SOURCE_DISCOVERY = ROOT / "server" / "catalog_source_discovery_queue.json"
DEFAULT_STALE_SOURCE_CLEANUP = ROOT / "server" / "stale_source_cleanup_queue.json"
DEFAULT_AGENT_IMAGE_CANDIDATES = ROOT / "server" / "agent_image_candidates_import_queue_current.json"
DEFAULT_AGENT_IMAGE_CANDIDATES_BROAD = ROOT / "server" / "agent_image_candidates_import_queue_broad.json"
DEFAULT_DB_SYNC = ROOT / "server" / "catalog_db_sync_audit.json"
DEFAULT_BARCODE_APPLICABILITY = ROOT / "server" / "catalog_barcode_applicability_audit_current.json"
DEFAULT_METADATA_APPLICABILITY = ROOT / "server" / "catalog_metadata_applicability_audit_current.json"
DEFAULT_SOURCE_IMAGE_APPLICABILITY = ROOT / "server" / "catalog_source_image_applicability_audit_current.json"
DEFAULT_IMAGE_REMAINING_AUDIT = ROOT / "server" / "catalog_remaining_image_enrichment_audit_current.json"
DEFAULT_SOURCE_BOTTLENECKS = ROOT / "server" / "source_url_bottlenecks_current.json"
DEFAULT_PRIZE_PROVIDER_FALLBACK = ROOT / "server" / "prize_provider_fallback_image_candidates_current.json"
DEFAULT_FOCUS_MISSING_IMAGES = ROOT / "server" / "focus_missing_image_queue_current.json"
DEFAULT_FOCUS_IMAGE_TEMPLATE = ROOT / "server" / "focus_image_confirmed_rows.template.json"
DEFAULT_CONFIRMED_IMPORT = ROOT / "server" / "catalog_confirmed_import_queue_audit.json"
DEFAULT_ICHIBAN_HISTORY_STATUS = ROOT / "server" / "ichiban_kuji_history_status_audit.json"
DEFAULT_ICHIBAN_METADATA = ROOT / "server" / "ichiban_kuji_metadata_audit.json"
DEFAULT_ICHIBAN_CAMPAIGN_GAP = ROOT / "server" / "ichiban_kuji_campaign_gap_audit.json"
DEFAULT_ICHIBAN_PRIZE_STRUCTURE = ROOT / "server" / "ichiban_kuji_prize_structure_audit.json"
DEFAULT_GOAL_STATUS = ROOT / "server" / "catalog_goal_status_current.json"
DEFAULT_JSON = ROOT / "server" / "catalog_report_consistency_audit.json"


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _by_field_map(value: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    if isinstance(value, dict):
        for key, count in value.items():
            out[str(key)] = int(count)
        return out
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                out[str(item[0])] = int(item[1])
    return out


def _counted_reasons_total(value: Any) -> int:
    total = 0
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                total += int(item[1])
    return total


def _queue_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("queue") or payload.get("items") or payload.get("rows") or []
    return [item for item in items if isinstance(item, dict)]


def _queue_field_items(field_queue: dict[str, Any], field: str) -> list[dict[str, Any]]:
    return [item for item in _queue_items(field_queue) if item.get("field") == field]


def _count(items: list[dict[str, Any]], key: str) -> int:
    return sum(1 for item in items if item.get(key))


def _count_evidence(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("search_url") or item.get("source_url"))


def _append_check(checks: list[dict[str, Any]], name: str, expected: int, actual: Any) -> None:
    checks.append({"name": name, "expected": int(expected or 0), "actual": int(actual or 0)})


def _audit_fields(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = payload.get("fields") or {}
    return {str(key): value for key, value in fields.items() if isinstance(value, dict)}


def _agent_candidate_checks(prefix: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = payload.get("summary") or {}
    ready_items = int(summary.get("ready_items") or 0)
    rejected_items = int(summary.get("rejected_items") or 0)
    duplicate_ready_items = 0
    for item in summary.get("rejected_reasons") or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2 and item[0] == "duplicate_ready_row_index":
            duplicate_ready_items += int(item[1] or 0)
    input_items = int(summary.get("input_items") or 0)
    return [
        {
            "name": f"{prefix}_ready_items_match_items",
            "expected": ready_items,
            "actual": len(payload.get("items") or []),
        },
        {
            "name": f"{prefix}_input_items_match_ready_plus_rejected",
            "expected": input_items,
            "actual": ready_items + rejected_items - duplicate_ready_items,
        },
        {
            "name": f"{prefix}_rejected_reasons_match_rejected_items",
            "expected": rejected_items,
            "actual": _counted_reasons_total(summary.get("rejected_reasons")),
        },
    ]


def _workflow(payload: dict[str, Any] | None, name: str) -> dict[str, Any]:
    if not payload:
        return {}
    for item in payload.get("workflows") or []:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return {}


def build_report(
    quality: dict[str, Any],
    field_queue: dict[str, Any],
    field_batches: dict[str, Any],
    image_queue: dict[str, Any],
    image_batches: dict[str, Any],
    image_batch_plan: dict[str, Any] | None = None,
    image_provider_coverage: dict[str, Any] | None = None,
    source_discovery: dict[str, Any] | None = None,
    stale_source_cleanup: dict[str, Any] | None = None,
    agent_image_candidates: dict[str, Any] | None = None,
    agent_image_candidates_broad: dict[str, Any] | None = None,
    db_sync: dict[str, Any] | None = None,
    barcode_applicability: dict[str, Any] | None = None,
    metadata_applicability: dict[str, Any] | None = None,
    source_image_applicability: dict[str, Any] | None = None,
    image_remaining_audit: dict[str, Any] | None = None,
    source_bottlenecks: dict[str, Any] | None = None,
    prize_provider_fallback: dict[str, Any] | None = None,
    focus_missing_images: dict[str, Any] | None = None,
    focus_image_template: dict[str, Any] | None = None,
    confirmed_import: dict[str, Any] | None = None,
    ichiban_history_status: dict[str, Any] | None = None,
    ichiban_metadata: dict[str, Any] | None = None,
    ichiban_campaign_gap: dict[str, Any] | None = None,
    ichiban_prize_structure: dict[str, Any] | None = None,
    goal_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_missing = {key: int(value) for key, value in (quality.get("missing_enrichment") or {}).items()}
    field_missing = _by_field_map(field_queue.get("by_field"))

    checks = [
        {
            "name": "field_queue_missing_total_matches_quality",
            "expected": sum(quality_missing.values()),
            "actual": int(field_queue.get("missing_total") or 0),
        },
        {
            "name": "field_batches_queue_rows_match_field_queue",
            "expected": int(field_queue.get("missing_total") or 0),
            "actual": int(field_batches.get("queue_rows") or 0),
        },
        {
            "name": "image_queue_matches_quality",
            "expected": int(quality_missing.get("image_url") or 0),
            "actual": int(image_queue.get("missing_images") or 0),
        },
        {
            "name": "image_batches_match_image_queue",
            "expected": int(image_queue.get("missing_images") or 0),
            "actual": int(image_batches.get("missing_images") or 0),
        },
    ]
    if image_batch_plan:
        checks.append(
            {
                "name": "image_batch_plan_matches_image_queue",
                "expected": int(image_queue.get("missing_images") or 0),
                "actual": int(image_batch_plan.get("missing_images") or 0),
            }
        )
    if image_provider_coverage:
        checks.append(
            {
                "name": "image_provider_coverage_matches_image_queue",
                "expected": int(image_queue.get("missing_images") or 0),
                "actual": int(image_provider_coverage.get("missing_images") or 0),
            }
        )
    if source_discovery:
        stale_indexes: set[int] = set()
        if stale_source_cleanup:
            for item in stale_source_cleanup.get("items") or []:
                try:
                    stale_indexes.add(int(item.get("row_index")))
                except (AttributeError, TypeError, ValueError):
                    pass
        expected_source_discovery = 0
        for item in image_queue.get("items") or image_queue.get("queue") or []:
            if not isinstance(item, dict) or item.get("source_url"):
                continue
            try:
                row_index = int(item.get("row_index"))
            except (TypeError, ValueError):
                row_index = -1
            if row_index not in stale_indexes:
                expected_source_discovery += 1
        checks.append(
            {
                "name": "source_discovery_matches_no_source_image_queue",
                "expected": expected_source_discovery,
                "actual": int((source_discovery.get("summary") or {}).get("source_discovery_rows") or 0),
            }
        )
    for field, expected in sorted(quality_missing.items()):
        checks.append(
            {
                "name": f"field_queue_by_field_matches_quality:{field}",
                "expected": expected,
                "actual": int(field_missing.get(field) or 0),
            }
        )
    if agent_image_candidates:
        checks.extend(_agent_candidate_checks("agent_image_candidates", agent_image_candidates))
    if agent_image_candidates_broad:
        checks.extend(_agent_candidate_checks("agent_image_candidates_broad", agent_image_candidates_broad))
    if db_sync:
        checks.append(
            {
                "name": "db_sync_seed_rows_match_quality",
                "expected": int(quality.get("rows") or 0),
                "actual": int(db_sync.get("seed_rows") or 0),
            }
        )
        db_ok_count = sum(1 for item in db_sync.get("databases") or [] if item.get("ok"))
        checks.append(
            {
                "name": "db_sync_all_databases_ok",
                "expected": int(db_sync.get("db_count") or 0),
                "actual": db_ok_count,
            }
        )
        for index, item in enumerate(db_sync.get("databases") or []):
            checks.append(
                {
                    "name": f"db_sync_active_rows_match_seed:{index}",
                    "expected": int(db_sync.get("seed_keys") or 0),
                    "actual": int(item.get("active_rows") or 0),
                }
            )
            checks.append(
                {
                    "name": f"db_sync_missing_images_match_quality:{index}",
                    "expected": int(quality_missing.get("image_url") or 0),
                    "actual": int(item.get("missing_images") or 0),
                }
            )
    if barcode_applicability:
        barcode_items = _queue_field_items(field_queue, "barcode")
        _append_check(checks, "barcode_applicability_missing_matches_field_queue", len(barcode_items), barcode_applicability.get("barcode_missing_rows"))
        _append_check(
            checks,
            "barcode_applicability_actionable_matches_field_queue",
            _count(barcode_items, "actionable_now"),
            barcode_applicability.get("actionable_barcode_rows"),
        )
        _append_check(
            checks,
            "barcode_applicability_non_actionable_matches_field_queue",
            len(barcode_items) - _count(barcode_items, "actionable_now"),
            barcode_applicability.get("non_actionable_barcode_rows"),
        )
        _append_check(
            checks,
            "barcode_applicability_kuji_not_public_matches_field_queue",
            sum(
                1
                for item in barcode_items
                if item.get("source_group") == "kuji" and item.get("applicability") == "not_publicly_available"
            ),
            barcode_applicability.get("kuji_not_public_barcode_rows"),
        )
        _append_check(
            checks,
            "barcode_applicability_manual_only_matches_field_queue",
            sum(1 for item in barcode_items if item.get("applicability") == "manual_only_or_not_public"),
            barcode_applicability.get("manual_only_or_not_public_rows"),
        )
    if metadata_applicability:
        metadata_fields = _audit_fields(metadata_applicability)
        metadata_missing = 0
        metadata_actionable = 0
        metadata_automation = 0
        for field in ("release_date", "official_price_jpy"):
            field_items = _queue_field_items(field_queue, field)
            summary = metadata_fields.get(field, {})
            metadata_missing += len(field_items)
            metadata_actionable += _count(field_items, "actionable_now")
            metadata_automation += _count(field_items, "automation_candidate")
            _append_check(checks, f"metadata_applicability_missing_matches_field_queue:{field}", len(field_items), summary.get("missing_rows"))
            _append_check(
                checks,
                f"metadata_applicability_actionable_matches_field_queue:{field}",
                _count(field_items, "actionable_now"),
                summary.get("actionable_rows"),
            )
            _append_check(
                checks,
                f"metadata_applicability_non_actionable_matches_field_queue:{field}",
                len(field_items) - _count(field_items, "actionable_now"),
                summary.get("non_actionable_rows"),
            )
            _append_check(
                checks,
                f"metadata_applicability_automation_matches_field_queue:{field}",
                _count(field_items, "automation_candidate"),
                summary.get("automation_candidate_rows"),
            )
        _append_check(checks, "metadata_applicability_total_missing_matches_fields", metadata_missing, metadata_applicability.get("metadata_missing_rows"))
        _append_check(checks, "metadata_applicability_total_actionable_matches_fields", metadata_actionable, metadata_applicability.get("metadata_actionable_rows"))
        _append_check(checks, "metadata_applicability_total_automation_matches_fields", metadata_automation, metadata_applicability.get("metadata_automation_candidate_rows"))
    if source_image_applicability:
        source_image_fields = _audit_fields(source_image_applicability)
        source_image_missing = 0
        source_image_actionable = 0
        source_image_automation = 0
        for field in ("source_url", "image_url"):
            field_items = _queue_field_items(field_queue, field)
            summary = source_image_fields.get(field, {})
            source_image_missing += len(field_items)
            source_image_actionable += _count(field_items, "actionable_now")
            source_image_automation += _count(field_items, "automation_candidate")
            _append_check(checks, f"source_image_applicability_missing_matches_field_queue:{field}", len(field_items), summary.get("missing_rows"))
            _append_check(
                checks,
                f"source_image_applicability_actionable_matches_field_queue:{field}",
                _count(field_items, "actionable_now"),
                summary.get("actionable_rows"),
            )
            _append_check(
                checks,
                f"source_image_applicability_automation_matches_field_queue:{field}",
                _count(field_items, "automation_candidate"),
                summary.get("automation_candidate_rows"),
            )
            _append_check(
                checks,
                f"source_image_applicability_evidence_matches_field_queue:{field}",
                _count_evidence(field_items),
                summary.get("evidence_url_rows"),
            )
            _append_check(
                checks,
                f"source_image_applicability_manual_no_evidence_matches_field_queue:{field}",
                len(field_items) - _count_evidence(field_items),
                summary.get("manual_or_no_evidence_rows"),
            )
        _append_check(checks, "source_image_applicability_total_missing_matches_fields", source_image_missing, source_image_applicability.get("source_image_missing_rows"))
        _append_check(checks, "source_image_applicability_total_actionable_matches_fields", source_image_actionable, source_image_applicability.get("source_image_actionable_rows"))
        _append_check(checks, "source_image_applicability_total_automation_matches_fields", source_image_automation, source_image_applicability.get("source_image_automation_candidate_rows"))
        if image_remaining_audit:
            _append_check(
                checks,
                "source_image_applicability_provider_candidates_match_image_audit",
                int(image_remaining_audit.get("provider_candidate_items") or 0),
                source_image_applicability.get("image_provider_candidate_items"),
            )
            _append_check(
                checks,
                "source_image_applicability_manual_blocked_match_image_audit",
                int(image_remaining_audit.get("manual_or_blocked_items") or 0),
                source_image_applicability.get("image_manual_or_blocked_items"),
            )
            _append_check(
                checks,
                "source_image_applicability_exact_source_match_image_audit",
                int(image_remaining_audit.get("missing_with_exact_source_url") or 0),
                source_image_applicability.get("image_missing_with_exact_source_url"),
            )
            _append_check(
                checks,
                "source_image_applicability_generic_source_match_image_audit",
                int(image_remaining_audit.get("missing_with_generic_source_url") or 0),
                source_image_applicability.get("image_missing_with_generic_source_url"),
            )
        if source_bottlenecks:
            _append_check(
                checks,
                "source_image_applicability_missing_both_match_bottlenecks",
                int(source_bottlenecks.get("missing_image_and_source_url") or 0),
                source_image_applicability.get("missing_image_and_source_url"),
            )
            _append_check(
                checks,
                "source_image_applicability_has_image_missing_source_match_bottlenecks",
                int(source_bottlenecks.get("has_image_but_missing_source_url") or 0),
                source_image_applicability.get("has_image_but_missing_source_url"),
            )
    if prize_provider_fallback:
        fallback_summary = prize_provider_fallback.get("summary") or {}
        _append_check(
            checks,
            "prize_provider_fallback_items_match_summary",
            len(prize_provider_fallback.get("items") or []),
            fallback_summary.get("fallback_candidate_rows"),
        )
    if focus_missing_images:
        focus_summaries = [
            item for item in focus_missing_images.get("focus_summaries") or [] if isinstance(item, dict)
        ]
        _append_check(
            checks,
            "focus_missing_image_items_match_summary",
            len(focus_missing_images.get("items") or []),
            focus_missing_images.get("focus_missing_image_rows"),
        )
        _append_check(
            checks,
            "focus_missing_image_summary_matches_focuses",
            sum(int(item.get("missing_image_rows") or 0) for item in focus_summaries),
            focus_missing_images.get("focus_missing_image_rows"),
        )
        _append_check(
            checks,
            "focus_missing_source_summary_matches_focuses",
            sum(int(item.get("missing_source_rows") or 0) for item in focus_summaries),
            focus_missing_images.get("focus_missing_source_rows"),
        )
        if focus_image_template:
            template_items = [
                item for item in focus_image_template.get("items") or [] if isinstance(item, dict)
            ]
            _append_check(
                checks,
                "focus_image_template_items_match_focus_missing_images",
                focus_missing_images.get("focus_missing_image_rows"),
                len(template_items),
            )
            _append_check(
                checks,
                "focus_image_template_manual_confirmed_false",
                0,
                sum(1 for item in template_items if item.get("manual_confirmed") is True),
            )
        if confirmed_import:
            focus_workflow = _workflow(confirmed_import, "focus_image")
            focus_workflow_template_items = int(focus_workflow.get("template_items") or 0)
            if focus_workflow_template_items == 0 and focus_image_template:
                focus_workflow_template_items = len(
                    [item for item in focus_image_template.get("items") or [] if isinstance(item, dict)]
                )
            _append_check(
                checks,
                "confirmed_import_focus_template_items_match_focus_missing_images",
                focus_missing_images.get("focus_missing_image_rows"),
                focus_workflow_template_items,
            )
            _append_check(
                checks,
                "confirmed_import_focus_manual_confirmed_matches_workflow",
                0,
                focus_workflow.get("manual_confirmed_true"),
            )
    if ichiban_history_status:
        if ichiban_campaign_gap:
            for key in (
                "campaign_count",
                "seeded_campaign_url_count",
                "campaign_gap_count",
                "audited_gap_count",
            ):
                _append_check(
                    checks,
                    f"ichiban_history_status_matches_campaign_gap:{key}",
                    ichiban_campaign_gap.get(key),
                    ichiban_history_status.get(key),
                )
        if ichiban_prize_structure:
            for key in (
                "campaign_count",
                "seeded_campaign_url_count",
                "prize_rows",
                "missing_sub_series_rows",
            ):
                _append_check(
                    checks,
                    f"ichiban_history_status_matches_prize_structure:{key}",
                    ichiban_prize_structure.get(key),
                    ichiban_history_status.get(key),
                )
        if ichiban_metadata:
            history_metadata = ichiban_history_status.get("metadata") or {}
            for key in (
                "urls_with_missing_metadata",
                "rows_missing_release_date",
                "rows_missing_official_price_jpy",
                "safe_release_url_count",
                "safe_price_url_count",
            ):
                _append_check(
                    checks,
                    f"ichiban_history_status_matches_metadata:{key}",
                    ichiban_metadata.get(key),
                    history_metadata.get(key),
                )
            _append_check(
                checks,
                "ichiban_history_status_metadata_blocked_rows_match_missing_fields",
                int(ichiban_metadata.get("rows_missing_release_date") or 0)
                + int(ichiban_metadata.get("rows_missing_official_price_jpy") or 0),
                history_metadata.get("blocked_rows"),
            )
            _append_check(
                checks,
                "ichiban_history_status_metadata_safe_updates_match_safe_urls",
                int(ichiban_metadata.get("safe_release_url_count") or 0)
                + int(ichiban_metadata.get("safe_price_url_count") or 0),
                history_metadata.get("safe_update_url_count"),
            )
        if ichiban_campaign_gap and ichiban_prize_structure:
            for key in ("campaign_count", "seeded_campaign_url_count"):
                _append_check(
                    checks,
                    f"ichiban_campaign_gap_matches_prize_structure:{key}",
                    ichiban_campaign_gap.get(key),
                    ichiban_prize_structure.get(key),
                )
    if goal_status:
        goal_missing = {key: int(value) for key, value in (goal_status.get("missing_enrichment") or {}).items()}
        for field, expected in sorted(quality_missing.items()):
            _append_check(checks, f"goal_status_missing_enrichment_matches_quality:{field}", expected, goal_missing.get(field))
        if barcode_applicability:
            goal_barcode = goal_status.get("barcode_applicability") or {}
            for key in (
                "barcode_missing_rows",
                "actionable_barcode_rows",
                "non_actionable_barcode_rows",
                "kuji_not_public_barcode_rows",
                "manual_only_or_not_public_rows",
            ):
                _append_check(checks, f"goal_status_barcode_applicability_matches_audit:{key}", barcode_applicability.get(key), goal_barcode.get(key))
        if metadata_applicability:
            goal_metadata = goal_status.get("metadata_applicability") or {}
            for key in ("metadata_missing_rows", "metadata_actionable_rows", "metadata_automation_candidate_rows"):
                _append_check(checks, f"goal_status_metadata_applicability_matches_audit:{key}", metadata_applicability.get(key), goal_metadata.get(key))
        if source_image_applicability:
            goal_source_image = goal_status.get("source_image_applicability") or {}
            for key in (
                "source_image_missing_rows",
                "source_image_actionable_rows",
                "source_image_automation_candidate_rows",
                "missing_image_and_source_url",
                "has_image_but_missing_source_url",
                "image_provider_candidate_items",
                "image_manual_or_blocked_items",
            ):
                _append_check(
                    checks,
                    f"goal_status_source_image_applicability_matches_audit:{key}",
                    source_image_applicability.get(key),
                    goal_source_image.get(key),
                )
        if prize_provider_fallback:
            fallback_summary = (prize_provider_fallback.get("summary") or {})
            goal_fallback_summary = ((goal_status.get("prize_provider_fallback_images") or {}).get("summary") or {})
            for key in ("searched_rows", "fallback_candidate_rows", "unresolved_rows"):
                _append_check(
                    checks,
                    f"goal_status_prize_provider_fallback_matches_audit:{key}",
                    fallback_summary.get(key),
                    goal_fallback_summary.get(key),
                )
        if focus_missing_images:
            goal_focus = goal_status.get("focus_missing_images") or {}
            for key in (
                "focus_count",
                "focus_rows",
                "focus_missing_image_rows",
                "focus_missing_source_rows",
                "focus_missing_image_and_source_rows",
            ):
                _append_check(
                    checks,
                    f"goal_status_focus_missing_images_matches_audit:{key}",
                    focus_missing_images.get(key),
                    goal_focus.get(key),
                )
        if ichiban_metadata:
            goal_ichiban_metadata = goal_status.get("ichiban_metadata") or {}
            for key in (
                "urls_with_missing_metadata",
                "rows_missing_release_date",
                "rows_missing_official_price_jpy",
                "safe_release_url_count",
                "safe_price_url_count",
            ):
                _append_check(
                    checks,
                    f"goal_status_ichiban_metadata_matches_audit:{key}",
                    ichiban_metadata.get(key),
                    goal_ichiban_metadata.get(key),
                )
        if ichiban_campaign_gap:
            goal_ichiban_gap = goal_status.get("ichiban_campaign_gaps") or {}
            for key in (
                "campaign_count",
                "seeded_campaign_url_count",
                "campaign_gap_count",
                "audited_gap_count",
            ):
                _append_check(
                    checks,
                    f"goal_status_ichiban_campaign_gap_matches_audit:{key}",
                    ichiban_campaign_gap.get(key),
                    goal_ichiban_gap.get(key),
                )
        if ichiban_prize_structure:
            goal_ichiban_structure = goal_status.get("ichiban_prize_structure") or {}
            for key in (
                "campaign_count",
                "seeded_campaign_url_count",
                "prize_rows",
                "missing_sub_series_rows",
            ):
                _append_check(
                    checks,
                    f"goal_status_ichiban_prize_structure_matches_audit:{key}",
                    ichiban_prize_structure.get(key),
                    goal_ichiban_structure.get(key),
                )

    failures = [
        {**check, "delta": int(check["actual"]) - int(check["expected"])}
        for check in checks
        if int(check["expected"]) != int(check["actual"])
    ]
    return {
        "ok": not failures,
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--field-queue", type=Path, default=DEFAULT_FIELD_QUEUE)
    parser.add_argument("--field-batches", type=Path, default=DEFAULT_FIELD_BATCHES)
    parser.add_argument("--image-queue", type=Path, default=DEFAULT_IMAGE_QUEUE)
    parser.add_argument("--image-batches", type=Path, default=DEFAULT_IMAGE_BATCHES)
    parser.add_argument("--image-batch-plan", type=Path, default=DEFAULT_IMAGE_BATCH_PLAN)
    parser.add_argument("--image-provider-coverage", type=Path, default=DEFAULT_IMAGE_PROVIDER_COVERAGE)
    parser.add_argument("--source-discovery", type=Path, default=DEFAULT_SOURCE_DISCOVERY)
    parser.add_argument("--stale-source-cleanup", type=Path, default=DEFAULT_STALE_SOURCE_CLEANUP)
    parser.add_argument("--agent-image-candidates", type=Path, default=DEFAULT_AGENT_IMAGE_CANDIDATES)
    parser.add_argument("--agent-image-candidates-broad", type=Path, default=DEFAULT_AGENT_IMAGE_CANDIDATES_BROAD)
    parser.add_argument("--db-sync", type=Path, default=DEFAULT_DB_SYNC)
    parser.add_argument("--barcode-applicability", type=Path, default=DEFAULT_BARCODE_APPLICABILITY)
    parser.add_argument("--metadata-applicability", type=Path, default=DEFAULT_METADATA_APPLICABILITY)
    parser.add_argument("--source-image-applicability", type=Path, default=DEFAULT_SOURCE_IMAGE_APPLICABILITY)
    parser.add_argument("--image-remaining-audit", type=Path, default=DEFAULT_IMAGE_REMAINING_AUDIT)
    parser.add_argument("--source-bottlenecks", type=Path, default=DEFAULT_SOURCE_BOTTLENECKS)
    parser.add_argument("--prize-provider-fallback", type=Path, default=DEFAULT_PRIZE_PROVIDER_FALLBACK)
    parser.add_argument("--focus-missing-images", type=Path, default=DEFAULT_FOCUS_MISSING_IMAGES)
    parser.add_argument("--focus-image-template", type=Path, default=DEFAULT_FOCUS_IMAGE_TEMPLATE)
    parser.add_argument("--confirmed-import", type=Path, default=DEFAULT_CONFIRMED_IMPORT)
    parser.add_argument("--ichiban-history-status", type=Path, default=DEFAULT_ICHIBAN_HISTORY_STATUS)
    parser.add_argument("--ichiban-metadata", type=Path, default=DEFAULT_ICHIBAN_METADATA)
    parser.add_argument("--ichiban-campaign-gap", type=Path, default=DEFAULT_ICHIBAN_CAMPAIGN_GAP)
    parser.add_argument("--ichiban-prize-structure", type=Path, default=DEFAULT_ICHIBAN_PRIZE_STRUCTURE)
    parser.add_argument("--goal-status", type=Path, default=DEFAULT_GOAL_STATUS)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--fail-on-mismatch", action="store_true")
    args = parser.parse_args()

    report = build_report(
        _read_json(args.quality),
        _read_json(args.field_queue),
        _read_json(args.field_batches),
        _read_json(args.image_queue),
        _read_json(args.image_batches),
        _read_json(args.image_batch_plan),
        _read_json(args.image_provider_coverage),
        _read_json(args.source_discovery),
        _read_json(args.stale_source_cleanup) if args.stale_source_cleanup.exists() else None,
        _read_json(args.agent_image_candidates) if args.agent_image_candidates.exists() else None,
        _read_json(args.agent_image_candidates_broad) if args.agent_image_candidates_broad.exists() else None,
        _read_json(args.db_sync) if args.db_sync.exists() else None,
        _read_json(args.barcode_applicability) if args.barcode_applicability.exists() else None,
        _read_json(args.metadata_applicability) if args.metadata_applicability.exists() else None,
        _read_json(args.source_image_applicability) if args.source_image_applicability.exists() else None,
        _read_json(args.image_remaining_audit) if args.image_remaining_audit.exists() else None,
        _read_json(args.source_bottlenecks) if args.source_bottlenecks.exists() else None,
        _read_json(args.prize_provider_fallback) if args.prize_provider_fallback.exists() else None,
        _read_json(args.focus_missing_images) if args.focus_missing_images.exists() else None,
        _read_json(args.focus_image_template) if args.focus_image_template.exists() else None,
        _read_json(args.confirmed_import) if args.confirmed_import.exists() else None,
        _read_json(args.ichiban_history_status) if args.ichiban_history_status.exists() else None,
        _read_json(args.ichiban_metadata) if args.ichiban_metadata.exists() else None,
        _read_json(args.ichiban_campaign_gap) if args.ichiban_campaign_gap.exists() else None,
        _read_json(args.ichiban_prize_structure) if args.ichiban_prize_structure.exists() else None,
        _read_json(args.goal_status) if args.goal_status.exists() else None,
    )
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("ok", "check_count", "failure_count")}, ensure_ascii=False, indent=2))
    print(f"Report: {args.json_output}")
    if args.fail_on_mismatch and not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
