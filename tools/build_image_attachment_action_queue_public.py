from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlsplit, urlunsplit


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_image_enrichment_batches_public.json"
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_GOTOUCHI_CANDIDATES = ROOT / "data" / "gotouchi_chiikawa_image_candidates_public.json"
DEFAULT_SOURCE_CANDIDATES = ROOT / "data" / "catalog_candidate_source_url_review_queue_public.json"
DEFAULT_SOURCE_CANDIDATE_FALLBACK = ROOT / "data" / "catalog_image_attachment_confirmed_template_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_image_attachment_action_queue_public.json"

WORKFLOW_PRIORITY = {
    "extract_from_existing_source_url": 10,
    "replace_generic_source_then_extract_image": 20,
    "review_gotouchi_official_candidates": 30,
}
ACTIONABLE_WORKFLOWS = set(WORKFLOW_PRIORITY)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _catalog_image_lookup(catalog: dict[str, Any] | None) -> dict[int, bool]:
    if not catalog:
        return {}
    items = catalog.get("items")
    if not isinstance(items, list):
        return {}
    lookup: dict[int, bool] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        catalog_index = item.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            lookup[catalog_index] = _present(item.get("local_image_path")) or _present(item.get("image_url"))
    return lookup


def _representative_candidate_lookup(
    candidate_report: dict[str, Any] | None,
) -> dict[int, dict[str, Any]]:
    if not candidate_report:
        return {}
    lookup: dict[int, dict[str, Any]] = {}
    for item in candidate_report.get("items") or []:
        if not isinstance(item, dict):
            continue
        catalog_index = item.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            lookup[catalog_index] = {
                "candidate_status": item.get("candidate_status"),
                "top_candidates": item.get("top_candidates") or [],
            }
    return lookup


def _source_candidate_lookup(candidate_report: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not candidate_report:
        return {}
    lookup: dict[int, dict[str, Any]] = {}
    for item in candidate_report.get("items") or []:
        if not isinstance(item, dict):
            continue
        catalog_index = item.get("catalog_index", item.get("row_index"))
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            row = {
                key: item.get(key)
                for key in (
                    "source_url_review_lane",
                    "candidate_status",
                    "candidate_score",
                    "candidate_count",
                    "candidate_options",
                    "source_url_review_blockers",
                    "match_diagnostics",
                    "fallback_search_queries",
                    "store_search_hints",
                    "store_search_url",
                )
                if key in item
            }
            if not row.get("candidate_status"):
                lane = str(row.get("source_url_review_lane") or "")
                if lane in {"manual_search_required", "candidate_provider_missing"}:
                    row["candidate_status"] = "no_candidate"
                elif lane == "weak_candidate_review":
                    row["candidate_status"] = "weak_manual_review_candidate"
            lookup[catalog_index] = row
    return lookup


def _merged_source_candidate_lookup(
    primary_report: dict[str, Any] | None,
    fallback_report: dict[str, Any] | None,
) -> dict[int, dict[str, Any]]:
    merged = _source_candidate_lookup(fallback_report)
    for catalog_index, row in _source_candidate_lookup(primary_report).items():
        base = dict(merged.get(catalog_index) or {})
        base.update(row)
        merged[catalog_index] = base
    return merged


def _with_representative_candidates(
    item: dict[str, Any],
    candidate_lookup: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    catalog_index = item.get("catalog_index")
    candidate = (
        candidate_lookup.get(catalog_index)
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool)
        else None
    )
    if not candidate:
        return item
    return {
        **item,
        "candidate_status": item.get("candidate_status") or candidate.get("candidate_status"),
        "top_candidates": item.get("top_candidates") or candidate.get("top_candidates") or [],
    }


def _with_source_candidates(
    item: dict[str, Any],
    candidate_lookup: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    catalog_index = item.get("catalog_index")
    candidate = (
        candidate_lookup.get(catalog_index)
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool)
        else None
    )
    if not candidate:
        return item
    merged = dict(item)
    for key, value in candidate.items():
        if value not in (None, "", []):
            merged[key] = value
    return merged


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(str(row.get(key) or "") for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _source_url_review_guidance(row: dict[str, Any]) -> dict[str, Any]:
    source_store = str(row.get("source_store") or "")
    candidate_status = str(row.get("candidate_status") or "")
    primary_review_url_kind = str(row.get("primary_review_url_kind") or "")
    accepted_url_patterns = ["exact product detail URL, not a storefront/search URL"]
    if "Stellive" in source_store:
        accepted_url_patterns = [
            "https://fanding.kr/@stellive/shop/{product_no}",
            "page title/product card must preserve member, event, product type, and variant terms",
        ]
    elif "Weverse" in source_store:
        accepted_url_patterns = [
            "shop.weverse.io product detail URL for the exact artist/item",
            "avoid collection, category, cart, search, or sold-out mirror pages unless they identify the exact product",
        ]
    elif "포켓몬" in source_store or "Pokemon" in source_store:
        accepted_url_patterns = [
            "pokemoncenter-online.com product detail URL for the exact product",
            "confirm official product name, Pokemon/character, and goods type before using the URL",
        ]
    blocker_note = {
        "low_confidence_candidate": "Candidate options are review hints only; do not copy the top candidate without exact title/member/event/type confirmation.",
        "weak_manual_review_candidate": "Candidate score is weak; use only if the opened detail page proves the exact item identity.",
        "no_candidate": "No usable candidate was found; use source_search_url, store_search_hints, or fallback_search_queries for manual lookup.",
    }.get(
        candidate_status,
        "Manual confirmation is still required before any source_url mutation.",
    )
    return {
        "source_store": source_store,
        "primary_review_url_kind": primary_review_url_kind,
        "candidate_status": candidate_status,
        "accepted_url_patterns": accepted_url_patterns,
        "required_evidence": [
            "exact product detail page",
            "product title preserves the catalog name or official variant wording",
            "goods type/category matches the catalog row",
            "product image or page context can later support image_url attachment",
        ],
        "manual_confirmed_allowed_when": "manual_value, evidence_url, and candidate_source_url all point to the same exact product detail page",
        "do_not_use": [
            "storefront root URL",
            "search results URL",
            "category/listing page",
            "low-score candidate with only generic token overlap",
        ],
        "candidate_review_note": blocker_note,
        "auto_apply_allowed": False,
    }


REPRESENTATIVE_CANDIDATE_REVIEW_GUIDANCE = {
    "motif_only_type_mismatch": {
        "risk": "official_candidate_matches_regional_motif_but_not_product_type",
        "recommended_action": "reject_candidate_or_find_exact_same_product_type_image",
        "required_evidence": [
            "same character",
            "same regional motif",
            "same product type",
            "same visible variant when separated by character or design",
        ],
        "manual_confirmed_allowed": False,
    },
    "no_official_candidate": {
        "risk": "no_official_candidate_image_found_for_exact_item",
        "recommended_action": "search_official_or_trusted_source_before_import",
        "required_evidence": [
            "exact product name or official listing context",
            "same character",
            "same regional motif",
            "same product type",
        ],
        "manual_confirmed_allowed": False,
    },
    "rejected_visual_mismatch": {
        "risk": "candidate_was_rejected_by_visual_or_identity_check",
        "recommended_action": "do_not_reuse_rejected_candidate_search_new_evidence",
        "required_evidence": [
            "fresh image URL from exact product evidence",
            "same character",
            "same regional motif",
            "same product type",
        ],
        "manual_confirmed_allowed": False,
    },
}


def _representative_candidate_review_guidance(status: Any) -> dict[str, Any]:
    normalized = str(status or "").strip()
    guidance = REPRESENTATIVE_CANDIDATE_REVIEW_GUIDANCE.get(normalized)
    if guidance is None:
        guidance = {
            "risk": "representative_candidate_status_unknown",
            "recommended_action": "inspect_candidate_and_require_exact_identity_evidence",
            "required_evidence": [
                "same character",
                "same motif or variant",
                "same product type",
                "official or trusted source URL",
            ],
            "manual_confirmed_allowed": False,
        }
    return {
        "status": normalized or "unknown",
        **guidance,
        "auto_apply_allowed": False,
    }


def _representative_candidate_guidance_summary(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts = Counter(str(row.get("representative_candidate_status") or "") for row in rows)
    counts.pop("", None)
    return [
        {
            "status": status,
            "rows": count,
            **_representative_candidate_review_guidance(status),
        }
        for status, count in counts.most_common()
    ]


def _list_counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter()
    for row in rows:
        values = row.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            name = str(value or "")
            if name:
                counts[name] += 1
    return [[name, count] for name, count in counts.most_common()]


def _attachment_readiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    local_download_ready_rows = sum(
        1
        for row in rows
        if (row.get("local_image_download_instruction") or {}).get("status")
        == "ready_after_manual_image_url_confirmation"
    )
    source_blocked_rows = sum(1 for row in rows if row.get("source_url_update_required"))
    representative_blocked_rows = sum(
        1 for row in rows if row.get("representative_image_review_required")
    )
    image_url_ready_rows = sum(1 for row in rows if row.get("image_url_ready"))
    primary_review_url_rows = sum(1 for row in rows if row.get("primary_review_url"))
    return {
        "row_count": len(rows),
        "local_image_download_instruction_ready_rows": local_download_ready_rows,
        "suggested_local_image_path_rows": sum(
            1 for row in rows if row.get("suggested_local_image_path")
        ),
        "primary_review_url_rows": primary_review_url_rows,
        "primary_review_url_missing_rows": len(rows) - primary_review_url_rows,
        "blocked_by_source_url_rows": source_blocked_rows,
        "blocked_by_representative_review_rows": representative_blocked_rows,
        "image_url_review_ready_rows": image_url_ready_rows,
        "blocked_before_image_import_rows": source_blocked_rows + representative_blocked_rows,
        "can_import_image_urls_now_rows": image_url_ready_rows,
        "download_ready_after_manual_image_url_rows": local_download_ready_rows,
        "readiness_lane_counts": [
            ["source_url_replacement_first", source_blocked_rows],
            ["representative_image_candidate_review", representative_blocked_rows],
            ["image_url_review_ready", image_url_ready_rows],
        ],
        "manual_confirmation_required": bool(rows),
        "auto_apply_enabled": False,
    }


def _build_workstreams(batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for batch in batches:
        workflow = str(batch.get("workflow") or "")
        source_store = str(batch.get("source_store") or "unknown")
        key = (workflow, source_store)
        bucket = grouped.setdefault(
            key,
            {
                "workflow": workflow,
                "source_store": source_store,
                "priority": int(batch.get("priority") or 99),
                "queued_image_rows": 0,
                "batch_ids": [],
                "source_url_update_template_rows": 0,
                "representative_image_review_rows": 0,
                "image_url_ready_rows": 0,
                "primary_review_url_rows": 0,
                "first_primary_review_url": "",
                "first_primary_review_url_kind": "manual_lookup_required",
                "category_rows": Counter(),
                "sample_items": [],
                "items": [],
            },
        )
        bucket["priority"] = min(int(bucket["priority"]), int(batch.get("priority") or 99))
        bucket["queued_image_rows"] += int(batch.get("row_count") or 0)
        bucket["batch_ids"].append(batch.get("batch_id"))
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            if item.get("source_url_import_template"):
                bucket["source_url_update_template_rows"] += 1
            if item.get("representative_image_review_required"):
                bucket["representative_image_review_rows"] += 1
            if item.get("image_url_ready"):
                bucket["image_url_ready_rows"] += 1
            if item.get("primary_review_url"):
                bucket["primary_review_url_rows"] += 1
                if not bucket["first_primary_review_url"]:
                    bucket["first_primary_review_url"] = item.get("primary_review_url")
                    bucket["first_primary_review_url_kind"] = item.get(
                        "primary_review_url_kind", "manual_lookup_required"
                    )
            category = str(item.get("category") or "")
            if category:
                bucket["category_rows"][category] += 1
            if len(bucket["sample_items"]) < 8:
                bucket["sample_items"].append(
                    {
                        "catalog_index": item.get("catalog_index"),
                        "review_lane": item.get("review_lane"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "category": item.get("category"),
                        "source_url": item.get("source_url"),
                        "official_search_url": item.get("official_search_url"),
                        "primary_review_url": item.get("primary_review_url"),
                        "primary_review_url_kind": item.get("primary_review_url_kind"),
                        "first_fallback_web_search_url": item.get(
                            "first_fallback_web_search_url"
                        ),
                        "suggested_local_image_path": item.get(
                            "suggested_local_image_path"
                        ),
                        "representative_candidate_status": item.get(
                            "representative_candidate_status"
                        ),
                        "representative_candidate_review_guidance": _representative_candidate_review_guidance(
                            item.get("representative_candidate_status")
                        ),
                        "representative_top_candidates": item.get(
                            "representative_top_candidates"
                        )
                        or [],
                        "source_url_update_required": item.get("source_url_update_required"),
                        "representative_image_review_required": item.get(
                            "representative_image_review_required"
                        ),
                    }
                )
            bucket["items"].append(item)

    rows = []
    for bucket in grouped.values():
        batch_ids = [batch_id for batch_id in bucket["batch_ids"] if batch_id]
        workflow = bucket["workflow"]
        rows.append(
            {
                "workflow": workflow,
                "source_store": bucket["source_store"],
                "priority": bucket["priority"],
                "queued_image_rows": bucket["queued_image_rows"],
                "batch_count": len(batch_ids),
                "next_batch_id": batch_ids[0] if batch_ids else None,
                "batch_ids": batch_ids,
                "next_machine_step": {
                    "extract_from_existing_source_url": "extract_product_image_from_existing_exact_source_url",
                    "replace_generic_source_then_extract_image": "replace_generic_source_url_then_extract_image",
                    "review_gotouchi_official_candidates": "confirm_exact_gotouchi_product_type_then_attach_image",
                }.get(workflow, "manual_image_review"),
                "source_url_update_template_rows": bucket["source_url_update_template_rows"],
                "representative_image_review_rows": bucket["representative_image_review_rows"],
                "image_url_ready_rows": bucket["image_url_ready_rows"],
                "primary_review_url_rows": bucket["primary_review_url_rows"],
                "first_primary_review_url": bucket["first_primary_review_url"],
                "first_primary_review_url_kind": bucket["first_primary_review_url_kind"],
                "category_rows": [
                    [category, count] for category, count in bucket["category_rows"].most_common()
                ],
                "attachment_readiness": _attachment_readiness(bucket["items"]),
                "review_summary": _workstream_review_summary(workflow, bucket),
                "sample_items": bucket["sample_items"],
                "auto_apply_enabled": False,
            }
        )
    rows.sort(
        key=lambda row: (
            int(row["priority"]),
            -int(row["queued_image_rows"]),
            str(row["source_store"]),
        )
    )
    return rows


def _build_source_url_update_work_order(action_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in action_items:
        if not item.get("source_url_update_required"):
            continue
        source_store = str(item.get("source_store") or "unknown")
        bucket = grouped.setdefault(
            source_store,
            {
                "source_store": source_store,
                "rows": [],
                "current_source_urls": Counter(),
                "categories": Counter(),
                "official_search_url_rows": 0,
                "missing_official_search_url_rows": 0,
                "fallback_web_search_url_rows": 0,
            },
        )
        bucket["rows"].append(item)
        source_url = str(item.get("source_url") or "")
        if source_url:
            bucket["current_source_urls"][source_url] += 1
        category = str(item.get("category") or "")
        if category:
            bucket["categories"][category] += 1
        if item.get("official_search_url"):
            bucket["official_search_url_rows"] += 1
        else:
            bucket["missing_official_search_url_rows"] += 1
        if item.get("fallback_web_search_urls"):
            bucket["fallback_web_search_url_rows"] += 1

    work_order: list[dict[str, Any]] = []
    for bucket in grouped.values():
        rows = sorted(
            bucket["rows"],
            key=lambda row: (
                0 if row.get("official_search_url") else 1,
                int(row.get("catalog_index") or 999_999_999),
            ),
        )
        current_source_urls = [
            {"source_url": url, "rows": count}
            for url, count in bucket["current_source_urls"].most_common()
        ]
        samples = [
            {
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "series_name": row.get("series_name"),
                "category": row.get("category"),
                "current_source_url": row.get("source_url"),
                "official_search_url": row.get("official_search_url"),
                "primary_review_url": row.get("primary_review_url"),
                "primary_review_url_kind": row.get("primary_review_url_kind"),
                "first_fallback_web_search_url": row.get("first_fallback_web_search_url"),
                "fallback_web_search_urls": row.get("fallback_web_search_urls") or [],
                "source_url_review_lane": row.get("source_url_review_lane"),
                "source_url_review_blockers": row.get("source_url_review_blockers") or [],
                "candidate_status": row.get("candidate_status"),
                "candidate_score": row.get("candidate_score"),
                "candidate_count": row.get("candidate_count"),
                "candidate_options": row.get("candidate_options") or [],
                "match_diagnostics": row.get("match_diagnostics") or {},
                "fallback_search_queries": row.get("fallback_search_queries") or [],
                "store_search_hints": row.get("store_search_hints") or {},
                "source_url_review_guidance": row.get("source_url_review_guidance")
                or _source_url_review_guidance(row),
                "suggested_local_image_path": row.get("suggested_local_image_path"),
                "local_image_download_instruction": row.get(
                    "local_image_download_instruction"
                ),
                "source_url_import_template": row.get("source_url_import_template"),
            }
            for row in rows[:12]
        ]
        work_order.append(
            {
                "source_store": bucket["source_store"],
                "row_count": len(rows),
                "source_url_update_template_rows": sum(
                    1 for row in rows if row.get("source_url_import_template")
                ),
                "official_search_url_rows": bucket["official_search_url_rows"],
                "missing_official_search_url_rows": bucket[
                    "missing_official_search_url_rows"
                ],
                "fallback_web_search_url_rows": bucket["fallback_web_search_url_rows"],
                "current_source_urls": current_source_urls,
                "category_rows": [
                    [category, count] for category, count in bucket["categories"].most_common()
                ],
                "recommended_review_order": [
                    "Open official_search_url when present.",
                    "If official_search_url is empty, open first_fallback_web_search_url as a starting point.",
                    "Confirm the exact product detail page, not a storefront/search page.",
                    "Treat low-confidence candidate_options as hints; reject them unless title, member/event, category, and product type all match.",
                    "Fill source_url_import_template.manual_value and evidence_url.",
                    "After source_url is confirmed, run image extraction/attachment review.",
                ],
                "source_url_review_guidance": _source_url_review_guidance(
                    {"source_store": bucket["source_store"]}
                ),
                "blocked_until": "exact_product_source_url_confirmed",
                "sample_items": samples,
                "auto_apply_enabled": False,
            }
        )
    work_order.sort(
        key=lambda row: (
            -int(row["row_count"]),
            int(row["missing_official_search_url_rows"]),
            str(row["source_store"]),
        )
    )
    return work_order


def _source_url_update_templates(action_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        item["source_url_import_template"]
        for item in action_items
        if isinstance(item.get("source_url_import_template"), dict)
    ]
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("source_store") or ""),
            0 if row.get("source_search_url") or row.get("official_search_url") else 1,
            int(row.get("row_index") or 999_999_999),
        ),
    )


def _build_source_url_update_template_batches(
    templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in templates:
        source_store = str(row.get("source_store") or "unknown")
        grouped.setdefault(source_store, []).append(row)

    batches = []
    for index, (source_store, rows) in enumerate(
        sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])),
        start=1,
    ):
        batches.append(
            {
                "template_batch_id": f"source-url-update-template-{index:03d}",
                "source_store": source_store,
                "row_count": len(rows),
                "official_search_url_rows": sum(
                    1
                    for row in rows
                    if row.get("source_search_url") or row.get("official_search_url")
                ),
                "fallback_web_search_url_rows": sum(
                    1 for row in rows if row.get("fallback_web_search_urls")
                ),
                "rows": rows,
                "manual_review_required": True,
                "auto_apply_enabled": False,
            }
        )
    return batches


def _build_next_source_url_review_batch(
    templates: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in templates[:limit]:
        rows.append(
            {
                "manual_confirmed": False,
                "row_index": row.get("row_index"),
                "source_store": row.get("source_store"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "series_name": row.get("series_name"),
                "category": row.get("category"),
                "current_source_url": row.get("current_source_url"),
                "primary_review_url": row.get("primary_review_url"),
                "primary_review_url_kind": row.get("primary_review_url_kind"),
                "source_search_url": row.get("source_search_url"),
                "first_fallback_web_search_url": row.get(
                    "first_fallback_web_search_url"
                ),
                "fallback_web_search_urls": row.get("fallback_web_search_urls")
                or [],
                "source_url_review_lane": row.get("source_url_review_lane"),
                "source_url_review_blockers": row.get("source_url_review_blockers")
                or [],
                "candidate_status": row.get("candidate_status"),
                "candidate_score": row.get("candidate_score"),
                "candidate_count": row.get("candidate_count"),
                "candidate_options": row.get("candidate_options") or [],
                "match_diagnostics": row.get("match_diagnostics") or {},
                "fallback_search_queries": row.get("fallback_search_queries") or [],
                "store_search_hints": row.get("store_search_hints") or {},
                "source_url_review_guidance": row.get("source_url_review_guidance")
                or _source_url_review_guidance(row),
                "manual_value": "",
                "evidence_url": "",
                "candidate_source_url": "",
                "blocked_until": row.get("blocked_until")
                or "exact_product_source_url_confirmed",
                "operator_checklist": [
                    "Open primary_review_url first.",
                    "Confirm the exact product detail page, not a storefront/search page.",
                    "Use candidate_options only as hints when candidate_status is low-confidence or weak.",
                    "Paste the exact product detail URL into manual_value, evidence_url, and candidate_source_url.",
                    "Leave manual_confirmed=false until the source URL proves the exact item identity.",
                ],
                "unblocks": "image_url_extraction_and_attachment_review",
                "auto_apply_enabled": False,
            }
        )
    return rows


def _build_next_representative_image_review_batch(
    action_items: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    review_rows = [
        item
        for item in action_items
        if item.get("representative_image_review_required")
    ]
    review_rows.sort(
        key=lambda row: (
            0 if row.get("primary_review_url") else 1,
            str(row.get("source_store") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )
    rows: list[dict[str, Any]] = []
    for row in review_rows[:limit]:
        template = row.get("catalog_field_import_template")
        if not isinstance(template, dict):
            template = {}
        rows.append(
            {
                "manual_confirmed": False,
                "catalog_index": row.get("catalog_index"),
                "source_store": row.get("source_store"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "series_name": row.get("series_name"),
                "category": row.get("category"),
                "source_url": row.get("source_url"),
                "primary_review_url": row.get("primary_review_url"),
                "primary_review_url_kind": row.get("primary_review_url_kind"),
                "first_fallback_web_search_url": row.get(
                    "first_fallback_web_search_url"
                ),
                "fallback_web_search_urls": row.get("fallback_web_search_urls")
                or [],
                "manual_image_url": "",
                "evidence_url": "",
                "candidate_source_url": template.get("candidate_source_url")
                or row.get("source_url")
                or "",
                "representative_candidate_status": row.get(
                    "representative_candidate_status"
                ),
                "representative_candidate_review_guidance": _representative_candidate_review_guidance(
                    row.get("representative_candidate_status")
                ),
                "representative_top_candidates": row.get(
                    "representative_top_candidates"
                )
                or [],
                "suggested_local_image_path": row.get("suggested_local_image_path"),
                "local_image_download_instruction": row.get(
                    "local_image_download_instruction"
                ),
                "catalog_field_import_template": template,
                "blocked_until": "representative_image_exact_product_type_confirmed",
                "operator_checklist": [
                    "Open primary_review_url first.",
                    "Confirm character, regional motif, product type, and variant.",
                    "Use representative images only when the exact variant cannot be separated safely.",
                    "Paste the confirmed product image URL into manual_image_url and evidence_url.",
                    "Leave manual_confirmed=false if the official candidate shows a different product type.",
                ],
                "unblocks": "manual_catalog_image_url_import",
                "auto_apply_enabled": False,
            }
        )
    return rows


def _first_workstream_batch_id(workstreams: list[dict[str, Any]], field: str) -> Any:
    return next(
        (
            row.get("next_batch_id")
            for row in workstreams
            if int(row.get(field) or 0) > 0
        ),
        None,
    )


def _first_workstream_review_value(
    workstreams: list[dict[str, Any]],
    field: str,
    value_key: str,
) -> Any:
    return next(
        (
            row.get(value_key)
            for row in workstreams
            if int(row.get(field) or 0) > 0 and row.get(value_key)
        ),
        "",
    )


def _build_execution_readiness(
    *,
    source_url_update_required_rows: int,
    representative_image_review_required_rows: int,
    image_url_ready_rows: int,
    workstreams: list[dict[str, Any]],
    source_url_update_work_order: list[dict[str, Any]],
) -> dict[str, Any]:
    source_url_batch_id = _first_workstream_batch_id(
        workstreams, "source_url_update_template_rows"
    )
    source_url_review_url = _first_workstream_review_value(
        workstreams,
        "source_url_update_template_rows",
        "first_primary_review_url",
    )
    source_url_review_url_kind = _first_workstream_review_value(
        workstreams,
        "source_url_update_template_rows",
        "first_primary_review_url_kind",
    )
    representative_batch_id = _first_workstream_batch_id(
        workstreams, "representative_image_review_rows"
    )
    representative_review_url = _first_workstream_review_value(
        workstreams,
        "representative_image_review_rows",
        "first_primary_review_url",
    )
    representative_review_url_kind = _first_workstream_review_value(
        workstreams,
        "representative_image_review_rows",
        "first_primary_review_url_kind",
    )
    image_ready_batch_id = _first_workstream_batch_id(workstreams, "image_url_ready_rows")
    image_ready_review_url = _first_workstream_review_value(
        workstreams,
        "image_url_ready_rows",
        "first_primary_review_url",
    )
    image_ready_review_url_kind = _first_workstream_review_value(
        workstreams,
        "image_url_ready_rows",
        "first_primary_review_url_kind",
    )
    blocked_before_image_import_rows = (
        source_url_update_required_rows + representative_image_review_required_rows
    )

    if source_url_update_required_rows:
        status = "source_url_replacement_required"
        recommended_first_workstream = "replace_generic_source_then_extract_image"
        recommended_first_batch_id = source_url_batch_id
        blocking_reason = "Exact product source URLs must be confirmed before image URLs can be attached."
    elif image_url_ready_rows:
        status = "image_url_review_ready"
        recommended_first_workstream = "extract_from_existing_source_url"
        recommended_first_batch_id = image_ready_batch_id
        blocking_reason = "Image URL rows are ready for manual evidence review before import."
    elif representative_image_review_required_rows:
        status = "representative_image_review_required"
        recommended_first_workstream = "review_gotouchi_official_candidates"
        recommended_first_batch_id = representative_batch_id
        blocking_reason = "Representative candidates must be checked against exact product variants."
    else:
        status = "no_actionable_image_attachment_rows"
        recommended_first_workstream = None
        recommended_first_batch_id = None
        blocking_reason = "No sampled rows are currently ready for image attachment work."

    return {
        "status": status,
        "can_auto_apply_catalog_changes": False,
        "can_import_image_urls_now": image_url_ready_rows > 0,
        "requires_manual_review": True,
        "image_url_ready_rows": image_url_ready_rows,
        "source_url_replacement_required_rows": source_url_update_required_rows,
        "source_url_update_work_order_count": len(source_url_update_work_order),
        "representative_image_review_required_rows": representative_image_review_required_rows,
        "blocked_before_image_import_rows": blocked_before_image_import_rows,
        "recommended_first_workstream": recommended_first_workstream,
        "recommended_first_batch_id": recommended_first_batch_id,
        "blocking_reason": blocking_reason,
        "evidence": {
            "source_url_replacement_next_batch_id": source_url_batch_id,
            "source_url_replacement_first_primary_review_url": source_url_review_url,
            "source_url_replacement_first_primary_review_url_kind": source_url_review_url_kind,
            "representative_review_next_batch_id": representative_batch_id,
            "representative_review_first_primary_review_url": representative_review_url,
            "representative_review_first_primary_review_url_kind": representative_review_url_kind,
            "image_url_ready_next_batch_id": image_ready_batch_id,
            "image_url_ready_first_primary_review_url": image_ready_review_url,
            "image_url_ready_first_primary_review_url_kind": image_ready_review_url_kind,
        },
    }


def _build_next_operator_actions(
    *,
    source_url_update_required_rows: int,
    representative_image_review_required_rows: int,
    image_url_ready_rows: int,
    workstreams: list[dict[str, Any]],
    source_url_update_work_order: list[dict[str, Any]],
    next_source_url_review_batch: list[dict[str, Any]],
    next_representative_image_review_batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    if source_url_update_required_rows:
        first_review_url = _first_workstream_review_value(
            workstreams,
            "source_url_update_template_rows",
            "first_primary_review_url",
        )
        actions.append(
            {
                "priority": 1,
                "lane": "source_url_replacement_first",
                "workflow": "replace_generic_source_then_extract_image",
                "rows": source_url_update_required_rows,
                "work_order_count": len(source_url_update_work_order),
                "next_batch_id": _first_workstream_batch_id(
                    workstreams, "source_url_update_template_rows"
                ),
                "first_primary_review_url": first_review_url,
                "first_primary_review_url_kind": _first_workstream_review_value(
                    workstreams,
                    "source_url_update_template_rows",
                    "first_primary_review_url_kind",
                ),
                "status": "manual_source_url_confirmation_required",
                "candidate_status_counts": _counter_pairs(
                    next_source_url_review_batch,
                    "candidate_status",
                ),
                "candidate_review_lane_counts": _counter_pairs(
                    next_source_url_review_batch,
                    "source_url_review_lane",
                ),
                "operator_step": "Fill source_url_import_template with exact product detail URLs before image attachment.",
                "unblocks": "image_url_extraction_and_attachment_review",
                "auto_apply_enabled": False,
            }
        )

    if image_url_ready_rows:
        first_review_url = _first_workstream_review_value(
            workstreams,
            "image_url_ready_rows",
            "first_primary_review_url",
        )
        actions.append(
            {
                "priority": 2,
                "lane": "image_url_review_ready",
                "workflow": "extract_from_existing_source_url",
                "rows": image_url_ready_rows,
                "next_batch_id": _first_workstream_batch_id(workstreams, "image_url_ready_rows"),
                "first_primary_review_url": first_review_url,
                "first_primary_review_url_kind": _first_workstream_review_value(
                    workstreams,
                    "image_url_ready_rows",
                    "first_primary_review_url_kind",
                ),
                "status": "manual_image_url_confirmation_required",
                "operator_step": "Confirm exact product image URLs and fill the image attachment template.",
                "unblocks": "manual_catalog_image_url_import",
                "auto_apply_enabled": False,
            }
        )

    if representative_image_review_required_rows:
        first_review_url = _first_workstream_review_value(
            workstreams,
            "representative_image_review_rows",
            "first_primary_review_url",
        )
        actions.append(
            {
                "priority": 3,
                "lane": "representative_image_candidate_review",
                "workflow": "review_gotouchi_official_candidates",
                "rows": representative_image_review_required_rows,
                "next_batch_id": _first_workstream_batch_id(
                    workstreams, "representative_image_review_rows"
                ),
                "first_primary_review_url": first_review_url,
                "first_primary_review_url_kind": _first_workstream_review_value(
                    workstreams,
                    "representative_image_review_rows",
                    "first_primary_review_url_kind",
                ),
                "status": "manual_variant_confirmation_required",
                "representative_candidate_status_counts": _counter_pairs(
                    next_representative_image_review_batch,
                    "representative_candidate_status",
                ),
                "representative_candidate_review_guidance": _representative_candidate_guidance_summary(
                    next_representative_image_review_batch
                ),
                "operator_step": "Confirm product type and variant before accepting representative official images.",
                "unblocks": "manual_catalog_image_url_import",
                "auto_apply_enabled": False,
            }
        )

    return actions


def _compact_item(group: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    workflow = str(group.get("workflow") or "")
    source_url_update_required = workflow == "replace_generic_source_then_extract_image"
    representative_image_review_required = workflow == "review_gotouchi_official_candidates"
    image_url_ready = workflow == "extract_from_existing_source_url"
    source_url_template = _source_url_import_template(item, group) if source_url_update_required else None
    review_lane = _review_lane(workflow)
    source_search_url = _source_search_url(item, template)
    fallback_web_search_urls = _fallback_web_search_urls(item, group, source_search_url)
    catalog_template = _normalized_catalog_field_template(template, source_search_url)
    suggested_local_image_path = _suggested_local_image_path(item)
    if suggested_local_image_path:
        catalog_template["suggested_local_image_path"] = suggested_local_image_path
        catalog_template["local_image_path_field"] = "local_image_path"
    if source_url_template is not None:
        source_url_template["first_fallback_web_search_url"] = (
            fallback_web_search_urls[0] if fallback_web_search_urls else ""
        )
        source_url_template["fallback_web_search_urls"] = fallback_web_search_urls
    compact = {
        "catalog_index": item.get("catalog_index"),
        "workflow": workflow,
        "review_lane": review_lane,
        "source_store": group.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "official_search_url": source_search_url,
        "source_search_url": source_search_url,
        "first_fallback_web_search_url": fallback_web_search_urls[0]
        if fallback_web_search_urls
        else "",
        "fallback_web_search_urls": fallback_web_search_urls,
        "source_url_update_required": source_url_update_required,
        "representative_image_review_required": representative_image_review_required,
        "image_url_ready": image_url_ready,
        "required_before_image_import": _required_before_image_import(workflow),
        "image_import_blockers": _image_import_blockers(workflow),
        "manual_confirmation_requirements": _manual_confirmation_requirements(workflow),
        "source_url_import_template": source_url_template,
        "catalog_field_import_template": catalog_template,
        "representative_candidate_status": item.get("candidate_status")
        if representative_image_review_required
        else None,
        "representative_candidate_review_guidance": _representative_candidate_review_guidance(
            item.get("candidate_status")
        )
        if representative_image_review_required
        else {},
        "representative_top_candidates": item.get("top_candidates") or []
        if representative_image_review_required
        else [],
        "source_url_review_lane": item.get("source_url_review_lane"),
        "source_url_review_blockers": item.get("source_url_review_blockers") or [],
        "candidate_status": item.get("candidate_status"),
        "candidate_score": item.get("candidate_score"),
        "candidate_count": item.get("candidate_count"),
        "candidate_options": item.get("candidate_options") or [],
        "match_diagnostics": item.get("match_diagnostics") or {},
        "fallback_search_queries": item.get("fallback_search_queries") or [],
        "store_search_hints": item.get("store_search_hints") or {},
        "suggested_local_image_path": suggested_local_image_path,
        "local_image_download_instruction": _local_image_download_instruction(
            suggested_local_image_path
        ),
        "review_state": "exact_product_image_confirmation_required",
        "auto_apply_enabled": False,
    }
    primary_review_url, primary_review_url_kind = _primary_review_url(compact)
    compact["primary_review_url"] = primary_review_url
    compact["primary_review_url_kind"] = primary_review_url_kind
    if source_url_template is not None:
        source_url_template["primary_review_url"] = primary_review_url
        source_url_template["primary_review_url_kind"] = primary_review_url_kind
        source_url_template["source_url_review_guidance"] = _source_url_review_guidance(
            source_url_template
        )
        compact["source_url_review_guidance"] = source_url_template[
            "source_url_review_guidance"
        ]
    return compact


def _suggested_local_image_path(item: dict[str, Any]) -> str:
    catalog_index = item.get("catalog_index")
    if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
        return f"assets/catalog_images/catalog_{catalog_index}.webp"
    row_index = item.get("row_index")
    if isinstance(row_index, int) and not isinstance(row_index, bool):
        return f"assets/catalog_images/catalog_{row_index}.webp"
    return ""


def _local_image_download_instruction(suggested_local_image_path: str) -> dict[str, Any]:
    if not suggested_local_image_path:
        return {
            "status": "manual_path_required",
            "target_local_image_path": "",
            "target_public_asset_path": "",
            "after_manual_image_url_confirmed": [],
        }
    return {
        "status": "ready_after_manual_image_url_confirmation",
        "target_local_image_path": suggested_local_image_path,
        "target_public_asset_path": f"assets/{suggested_local_image_path}",
        "after_manual_image_url_confirmed": [
            "download_confirmed_image_url_to_target_local_image_path",
            "write_local_image_path_with_image_url_import",
            "verify_file_exists_in_assets_and_web_public_assets",
        ],
    }


def _primary_review_url(item: dict[str, Any]) -> tuple[str, str]:
    workflow = str(item.get("workflow") or "")
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    first_fallback = str(item.get("first_fallback_web_search_url") or "").strip()
    fallback_urls = item.get("fallback_web_search_urls")
    if not first_fallback and isinstance(fallback_urls, list) and fallback_urls:
        first_fallback = str(fallback_urls[0] or "").strip()

    if workflow == "replace_generic_source_then_extract_image":
        candidates = [
            ("source_search_url", item.get("source_search_url")),
            ("official_search_url", item.get("official_search_url")),
            ("fallback_web_search", first_fallback),
            ("current_source_url", item.get("source_url")),
        ]
    elif workflow == "review_gotouchi_official_candidates":
        candidates = [
            ("current_source_url", item.get("source_url")),
            ("candidate_source_url", template.get("candidate_source_url")),
            ("fallback_web_search", first_fallback),
            ("source_search_url", item.get("source_search_url")),
            ("official_search_url", item.get("official_search_url")),
        ]
    else:
        candidates = [
            ("current_source_url", item.get("source_url")),
            ("candidate_source_url", template.get("candidate_source_url")),
            ("source_search_url", item.get("source_search_url")),
            ("official_search_url", item.get("official_search_url")),
            ("fallback_web_search", first_fallback),
        ]

    for kind, value in candidates:
        url = str(value or "").strip()
        if url:
            return url, kind
    return "", "manual_lookup_required"


def _source_search_url(item: dict[str, Any], template: dict[str, Any] | None = None) -> Any:
    template = template if isinstance(template, dict) else {}
    return _normalize_source_search_url(
        item.get("official_search_url")
        or item.get("source_search_url")
        or template.get("official_search_url")
        or template.get("source_search_url")
    )


def _normalize_source_search_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    parsed = urlsplit(url)
    if parsed.netloc.lower() == "stellive.fanding.kr" and parsed.path.rstrip("/") == "/search":
        return urlunsplit(("https", "fanding.kr", "/@stellive/shop", parsed.query, parsed.fragment))
    return url


def _fallback_web_search_urls(
    item: dict[str, Any],
    group: dict[str, Any],
    source_search_url: str,
    *,
    limit: int = 4,
) -> list[str]:
    if source_search_url:
        return []
    name = str(item.get("name_ja") or item.get("name_ko") or "").strip()
    if not name:
        return []
    series = str(item.get("series_name") or "").strip()
    category = str(item.get("category") or "").strip()
    source_store = str(item.get("source_store") or group.get("source_store") or "").strip()
    source_url = str(item.get("source_url") or "").strip()
    host = urlsplit(source_url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    domain_terms = []
    if host:
        domain_terms.append(f"site:{host}")
    store_domains = _store_search_domains(source_store)
    for domain in store_domains:
        if domain and domain not in {term.removeprefix("site:") for term in domain_terms}:
            domain_terms.append(f"site:{domain}")

    base_terms = " ".join(part for part in [name, series, category] if part)
    queries = []
    for domain_term in domain_terms:
        queries.append(" ".join(part for part in [domain_term, base_terms] if part))
    queries.append(" ".join(part for part in [source_store, base_terms] if part))

    urls: list[str] = []
    seen: set[str] = set()
    for query in queries:
        query = query.strip()
        if not query:
            continue
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def _store_search_domains(source_store: str) -> list[str]:
    normalized = source_store.lower()
    if "weverse" in normalized:
        return ["shop.weverse.io"]
    if "포켓몬" in source_store or "pokemon" in normalized:
        return ["pokemoncenter-online.com", "pokemoncenter.co.kr"]
    if "stellive" in normalized or "스텔라이브" in source_store:
        return ["fanding.kr", "stellive.fanding.kr"]
    return []


def _normalized_catalog_field_template(template: dict[str, Any], source_search_url: str) -> dict[str, Any]:
    normalized = dict(template)
    if source_search_url:
        if normalized.get("official_search_url"):
            normalized["official_search_url"] = source_search_url
        if normalized.get("source_search_url"):
            normalized["source_search_url"] = source_search_url
    return normalized


def _source_url_import_template(item: dict[str, Any], group: dict[str, Any]) -> dict[str, Any]:
    image_template = item.get("catalog_field_import_template")
    image_template = image_template if isinstance(image_template, dict) else {}
    source_search_url = _source_search_url(item, image_template)
    row = {
        "manual_confirmed": False,
        "manual_note": "",
        "row_index": item.get("catalog_index"),
        "field": "source_url",
        "manual_value": "",
        "evidence_url": "",
        "candidate_source_url": "",
        "current_source_url": item.get("source_url"),
        "source_store": item.get("source_store") or group.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "official_search_url": source_search_url,
        "source_search_url": source_search_url,
        "workflow": group.get("workflow"),
        "blocked_until": "exact_product_source_url_confirmed",
        "auto_apply_enabled": False,
    }
    for key in (
        "source_url_review_lane",
        "candidate_status",
        "candidate_score",
        "candidate_count",
        "candidate_options",
        "source_url_review_blockers",
        "match_diagnostics",
        "fallback_search_queries",
        "store_search_hints",
        "store_search_url",
    ):
        value = item.get(key)
        if value not in (None, "", []):
            row[key] = value
    row["source_url_review_guidance"] = _source_url_review_guidance(row)
    return row


def build_report(
    enrichment_batches: dict[str, Any],
    catalog: dict[str, Any] | None = None,
    representative_candidates: dict[str, Any] | None = None,
    source_candidates: dict[str, Any] | None = None,
    source_candidate_fallback: dict[str, Any] | None = None,
    *,
    max_batches: int = 18,
    batch_size: int = 20,
) -> dict[str, Any]:
    action_items: list[dict[str, Any]] = []
    excluded_workflows = Counter()
    actionable_group_rows = 0
    skipped_already_has_image_rows = 0
    has_image_by_index = _catalog_image_lookup(catalog)
    representative_candidate_by_index = _representative_candidate_lookup(
        representative_candidates
    )
    source_candidate_by_index = _merged_source_candidate_lookup(
        source_candidates,
        source_candidate_fallback,
    )

    for group in enrichment_batches.get("groups", []):
        if not isinstance(group, dict):
            continue
        workflow = str(group.get("workflow") or "")
        missing_rows = int(group.get("missing_image_rows") or 0)
        if workflow not in ACTIONABLE_WORKFLOWS:
            excluded_workflows[workflow or "unknown"] += missing_rows
            continue
        actionable_group_rows += missing_rows
        for item in group.get("sample_items") or []:
            if isinstance(item, dict):
                catalog_index = item.get("catalog_index")
                if isinstance(catalog_index, int) and has_image_by_index.get(catalog_index):
                    skipped_already_has_image_rows += 1
                    continue
                item = _with_source_candidates(item, source_candidate_by_index)
                action_items.append(
                    _compact_item(
                        group,
                        _with_representative_candidates(
                            item, representative_candidate_by_index
                        ),
                    )
                )

    action_items.sort(
        key=lambda row: (
            WORKFLOW_PRIORITY.get(str(row.get("workflow") or ""), 99),
            str(row.get("source_store") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in action_items:
        key = (str(item.get("workflow") or ""), str(item.get("source_store") or "unknown"))
        grouped.setdefault(key, []).append(item)

    batches: list[dict[str, Any]] = []
    for (workflow, source_store), rows in sorted(
        grouped.items(),
        key=lambda pair: (
            WORKFLOW_PRIORITY.get(pair[0][0], 99),
            -len(pair[1]),
            pair[0][1],
        ),
    ):
        for offset in range(0, len(rows), batch_size):
            if len(batches) >= max_batches:
                break
            chunk = rows[offset : offset + batch_size]
            first_primary_review_item = next(
                (row for row in chunk if row.get("primary_review_url")),
                {},
            )
            review_lane_counts = _counter_pairs(chunk, "review_lane")
            image_import_blocker_counts = _list_counter_pairs(
                chunk, "image_import_blockers"
            )
            batches.append(
                {
                    "batch_id": f"image-attachment-action-{len(batches) + 1:03d}",
                    "priority": WORKFLOW_PRIORITY.get(workflow, 99),
                    "workflow": workflow,
                    "source_store": source_store,
                    "row_count": len(chunk),
                    "offset": offset,
                    "review_state": "exact_product_image_confirmation_required",
                    "next_machine_step": {
                        "extract_from_existing_source_url": "extract_product_image_from_existing_exact_source_url",
                        "replace_generic_source_then_extract_image": "replace_generic_source_url_then_extract_image",
                        "review_gotouchi_official_candidates": "confirm_exact_gotouchi_product_type_then_attach_image",
                    }.get(workflow, "manual_image_review"),
                    "recommended_action": {
                        "extract_from_existing_source_url": "Review product page image and fill manual image_url.",
                        "replace_generic_source_then_extract_image": "Replace generic storefront URL with exact product page before image import.",
                        "review_gotouchi_official_candidates": "Confirm motif candidate matches product type before image import.",
                    }.get(workflow, "Review image evidence before import."),
                    "category_counts": _counter_pairs(chunk, "category"),
                    "review_lane_counts": review_lane_counts,
                    "image_import_blocker_counts": image_import_blocker_counts,
                    "attachment_readiness": _attachment_readiness(chunk),
                    "suggested_local_image_path_rows": sum(
                        1 for row in chunk if row.get("suggested_local_image_path")
                    ),
                    "local_image_download_instruction_ready_rows": sum(
                        1
                        for row in chunk
                        if (row.get("local_image_download_instruction") or {}).get("status")
                        == "ready_after_manual_image_url_confirmation"
                    ),
                    "primary_review_url_rows": sum(
                        1 for row in chunk if row.get("primary_review_url")
                    ),
                    "first_primary_review_url": first_primary_review_item.get(
                        "primary_review_url", ""
                    ),
                    "first_primary_review_url_kind": first_primary_review_item.get(
                        "primary_review_url_kind", "manual_lookup_required"
                    ),
                    "items": chunk,
                    "auto_apply_enabled": False,
                }
            )
        if len(batches) >= max_batches:
            break

    queued_rows = sum(int(batch.get("row_count") or 0) for batch in batches)
    workstreams = _build_workstreams(batches)
    unqueued_actionable_rows = max(actionable_group_rows - queued_rows, 0)
    source_url_update_required_rows = sum(1 for item in action_items if item.get("source_url_update_required"))
    source_url_update_template_rows = sum(1 for item in action_items if item.get("source_url_import_template"))
    source_url_update_search_hint_rows = sum(
        1
        for item in action_items
        if item.get("source_url_update_required")
        and (item.get("source_search_url") or item.get("official_search_url"))
    )
    source_url_update_fallback_web_search_rows = sum(
        1
        for item in action_items
        if item.get("source_url_update_required") and item.get("fallback_web_search_urls")
    )
    source_url_update_any_search_hint_rows = sum(
        1
        for item in action_items
        if item.get("source_url_update_required")
        and (
            item.get("source_search_url")
            or item.get("official_search_url")
            or item.get("fallback_web_search_urls")
        )
    )
    representative_image_review_required_rows = sum(
        1 for item in action_items if item.get("representative_image_review_required")
    )
    image_url_ready_rows = sum(1 for item in action_items if item.get("image_url_ready"))
    suggested_local_image_path_rows = sum(
        1 for item in action_items if item.get("suggested_local_image_path")
    )
    primary_review_url_rows = sum(1 for item in action_items if item.get("primary_review_url"))
    source_url_update_primary_review_url_rows = sum(
        1
        for item in action_items
        if item.get("source_url_update_required") and item.get("primary_review_url")
    )
    primary_review_url_kind_counts = _counter_pairs(action_items, "primary_review_url_kind")
    attachment_readiness = _attachment_readiness(action_items)
    first_primary_review_item = next(
        (item for item in action_items if item.get("primary_review_url")),
        {},
    )
    source_url_update_work_order = _build_source_url_update_work_order(action_items)
    source_url_update_template = _source_url_update_templates(action_items)
    source_url_update_template_batches = _build_source_url_update_template_batches(
        source_url_update_template
    )
    next_source_url_review_batch = _build_next_source_url_review_batch(
        source_url_update_template
    )
    next_representative_image_review_batch = (
        _build_next_representative_image_review_batch(action_items)
    )
    execution_readiness = _build_execution_readiness(
        source_url_update_required_rows=source_url_update_required_rows,
        representative_image_review_required_rows=representative_image_review_required_rows,
        image_url_ready_rows=image_url_ready_rows,
        workstreams=workstreams,
        source_url_update_work_order=source_url_update_work_order,
    )
    next_operator_actions = _build_next_operator_actions(
        source_url_update_required_rows=source_url_update_required_rows,
        representative_image_review_required_rows=representative_image_review_required_rows,
        image_url_ready_rows=image_url_ready_rows,
        workstreams=workstreams,
        source_url_update_work_order=source_url_update_work_order,
        next_source_url_review_batch=next_source_url_review_batch,
        next_representative_image_review_batch=next_representative_image_review_batch,
    )
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_image_attachment_action_queue",
        "summary": {
            "actionable_image_rows": actionable_group_rows,
            "queued_image_rows": queued_rows,
            "unqueued_actionable_image_rows": unqueued_actionable_rows,
            "sample_queue_coverage": round(queued_rows / actionable_group_rows, 4)
            if actionable_group_rows
            else 0,
            "action_batch_count": len(batches),
            "sample_action_item_rows": len(action_items),
            "skipped_already_has_image_rows": skipped_already_has_image_rows,
            "batch_size": batch_size,
            "max_batches": max_batches,
            "by_workflow": _counter_pairs(action_items, "workflow"),
            "by_source_store": _counter_pairs(action_items, "source_store"),
            "by_review_lane": _counter_pairs(action_items, "review_lane"),
            "image_import_blocker_counts": _list_counter_pairs(
                action_items, "image_import_blockers"
            ),
            "source_url_update_required_rows": source_url_update_required_rows,
            "source_url_update_template_rows": source_url_update_template_rows,
            "source_url_update_search_hint_rows": source_url_update_search_hint_rows,
            "source_url_update_missing_search_hint_rows": (
                source_url_update_required_rows - source_url_update_search_hint_rows
            ),
            "source_url_update_fallback_web_search_rows": (
                source_url_update_fallback_web_search_rows
            ),
            "source_url_update_any_search_hint_rows": source_url_update_any_search_hint_rows,
            "source_url_update_missing_any_search_hint_rows": (
                source_url_update_required_rows - source_url_update_any_search_hint_rows
            ),
            "source_url_update_primary_review_url_rows": source_url_update_primary_review_url_rows,
            "source_url_update_missing_primary_review_url_rows": (
                source_url_update_required_rows - source_url_update_primary_review_url_rows
            ),
            "source_url_update_review_start_coverage": (
                round(
                    source_url_update_primary_review_url_rows / source_url_update_required_rows,
                    4,
                )
                if source_url_update_required_rows
                else 0
            ),
            "source_url_candidate_status_counts": _counter_pairs(
                next_source_url_review_batch,
                "candidate_status",
            ),
            "source_url_review_lane_counts": _counter_pairs(
                next_source_url_review_batch,
                "source_url_review_lane",
            ),
            "primary_review_url_rows": primary_review_url_rows,
            "primary_review_url_kind_counts": primary_review_url_kind_counts,
            "primary_review_url_missing_rows": attachment_readiness[
                "primary_review_url_missing_rows"
            ],
            "first_primary_review_url": first_primary_review_item.get(
                "primary_review_url", ""
            ),
            "first_primary_review_url_kind": first_primary_review_item.get(
                "primary_review_url_kind", "manual_lookup_required"
            ),
            "representative_image_review_required_rows": representative_image_review_required_rows,
            "representative_candidate_status_counts": _counter_pairs(
                action_items,
                "representative_candidate_status",
            ),
            "representative_candidate_review_guidance": _representative_candidate_guidance_summary(
                action_items
            ),
            "image_url_ready_rows": image_url_ready_rows,
            "blocked_before_image_import_rows": attachment_readiness[
                "blocked_before_image_import_rows"
            ],
            "download_ready_after_manual_image_url_rows": attachment_readiness[
                "download_ready_after_manual_image_url_rows"
            ],
            "suggested_local_image_path_rows": suggested_local_image_path_rows,
            "local_image_download_instruction_ready_rows": sum(
                1
                for item in action_items
                if (item.get("local_image_download_instruction") or {}).get("status")
                == "ready_after_manual_image_url_confirmation"
            ),
            "workstream_count": len(workstreams),
            "source_url_update_workstream_count": sum(
                1 for row in workstreams if row.get("source_url_update_template_rows")
            ),
            "source_url_update_work_order_count": len(source_url_update_work_order),
            "source_url_update_template_batch_count": len(source_url_update_template_batches),
            "next_source_url_review_batch_rows": len(next_source_url_review_batch),
            "next_source_url_review_batch_store_count": len(
                {
                    row.get("source_store")
                    for row in next_source_url_review_batch
                    if row.get("source_store")
                }
            ),
            "next_source_url_review_batch_primary_review_url_rows": sum(
                1 for row in next_source_url_review_batch if row.get("primary_review_url")
            ),
            "next_source_url_review_batch_primary_review_url_kind_counts": _counter_pairs(
                next_source_url_review_batch,
                "primary_review_url_kind",
            ),
            "next_representative_image_review_batch_rows": len(
                next_representative_image_review_batch
            ),
            "next_representative_image_review_batch_store_count": len(
                {
                    row.get("source_store")
                    for row in next_representative_image_review_batch
                    if row.get("source_store")
                }
            ),
            "next_representative_image_review_batch_primary_review_url_rows": sum(
                1
                for row in next_representative_image_review_batch
                if row.get("primary_review_url")
            ),
            "next_representative_image_review_batch_local_path_rows": sum(
                1
                for row in next_representative_image_review_batch
                if row.get("suggested_local_image_path")
            ),
            "next_representative_image_review_batch_primary_review_url_kind_counts": _counter_pairs(
                next_representative_image_review_batch,
                "primary_review_url_kind",
            ),
            "next_representative_image_review_batch_candidate_status_counts": _counter_pairs(
                next_representative_image_review_batch,
                "representative_candidate_status",
            ),
            "next_representative_image_review_batch_guidance": _representative_candidate_guidance_summary(
                next_representative_image_review_batch
            ),
            "representative_image_review_workstream_count": sum(
                1 for row in workstreams if row.get("representative_image_review_rows")
            ),
            "excluded_workflow_rows": [[key, value] for key, value in excluded_workflows.most_common()],
            "auto_apply_enabled": False,
        },
        "attachment_readiness": attachment_readiness,
        "instructions": [
            "Use this queue for image-url work that is closer to actionable than broad source discovery.",
            "Every image still needs exact product evidence before catalog mutation.",
            "queued_image_rows is the current review sample; unqueued_actionable_image_rows remains for later batches.",
            "Rows without source_url stay in catalog_image_enrichment_batches_public.json and source discovery queues.",
            "For generic storefront rows, fill source_url_import_template before the image_url template.",
        ],
        "execution_readiness": execution_readiness,
        "workstreams": workstreams,
        "source_url_update_work_order": source_url_update_work_order,
        "source_url_update_template": source_url_update_template,
        "source_url_update_template_batches": source_url_update_template_batches,
        "next_source_url_review_batch": next_source_url_review_batch,
        "next_representative_image_review_batch": next_representative_image_review_batch,
        "next_operator_actions": next_operator_actions,
        "next_actions": [
            {
                "priority": 1,
                "workstream": "replace_generic_source_then_extract_image",
                "rows": source_url_update_required_rows,
                "workstream_count": sum(
                    1 for row in workstreams if row.get("source_url_update_template_rows")
                ),
                "next_batch_id": next(
                    (
                        row.get("next_batch_id")
                        for row in workstreams
                        if row.get("source_url_update_template_rows")
                    ),
                    None,
                ),
                "first_primary_review_url": _first_workstream_review_value(
                    workstreams,
                    "source_url_update_template_rows",
                    "first_primary_review_url",
                ),
                "first_primary_review_url_kind": _first_workstream_review_value(
                    workstreams,
                    "source_url_update_template_rows",
                    "first_primary_review_url_kind",
                ),
                "recommended_next_action": "Confirm exact product detail URLs for generic storefront rows before image import.",
            },
            {
                "priority": 2,
                "workstream": "review_representative_image_candidates",
                "rows": representative_image_review_required_rows,
                "workstream_count": sum(
                    1 for row in workstreams if row.get("representative_image_review_rows")
                ),
                "next_batch_id": next(
                    (
                        row.get("next_batch_id")
                        for row in workstreams
                        if row.get("representative_image_review_rows")
                    ),
                    None,
                ),
                "first_primary_review_url": _first_workstream_review_value(
                    workstreams,
                    "representative_image_review_rows",
                    "first_primary_review_url",
                ),
                "first_primary_review_url_kind": _first_workstream_review_value(
                    workstreams,
                    "representative_image_review_rows",
                    "first_primary_review_url_kind",
                ),
                "recommended_next_action": "Confirm representative official candidates only when product type and variant match.",
            },
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def _required_before_image_import(workflow: str) -> list[str]:
    if workflow == "extract_from_existing_source_url":
        return ["confirm_product_page_image_url"]
    if workflow == "replace_generic_source_then_extract_image":
        return ["confirm_exact_product_source_url", "replace_generic_source_url", "confirm_product_page_image_url"]
    if workflow == "review_gotouchi_official_candidates":
        return ["confirm_exact_product_type", "confirm_representative_image_is_acceptable"]
    return ["manual_image_evidence_review"]


def _review_lane(workflow: str) -> str:
    if workflow == "extract_from_existing_source_url":
        return "image_url_review_ready"
    if workflow == "replace_generic_source_then_extract_image":
        return "source_url_replacement_first"
    if workflow == "review_gotouchi_official_candidates":
        return "representative_image_candidate_review"
    return "manual_image_research"


def _image_import_blockers(workflow: str) -> list[str]:
    if workflow == "extract_from_existing_source_url":
        return ["manual_image_url_confirmation"]
    if workflow == "replace_generic_source_then_extract_image":
        return [
            "generic_storefront_source_url",
            "missing_exact_product_detail_url",
            "missing_product_page_image_url",
        ]
    if workflow == "review_gotouchi_official_candidates":
        return [
            "representative_image_may_not_match_exact_variant",
            "product_type_confirmation_required",
        ]
    return ["manual_source_and_image_evidence_required"]


def _manual_confirmation_requirements(workflow: str) -> list[str]:
    if workflow == "extract_from_existing_source_url":
        return [
            "Open source_url.",
            "Confirm the page is for the exact catalog item.",
            "Copy the primary product image URL into the image attachment template.",
        ]
    if workflow == "replace_generic_source_then_extract_image":
        return [
            "Find the exact product detail page, not a storefront or search page.",
            "Fill source_url_import_template.manual_value with that exact product URL.",
            "Only after source_url is replaced, confirm and attach the product image URL.",
        ]
    if workflow == "review_gotouchi_official_candidates":
        return [
            "Confirm character, regional motif, product type, and variant.",
            "Use representative images only when the exact variant cannot be separated safely.",
            "Do not auto-apply if the official candidate shows a different product type.",
        ]
    return ["Manually confirm source and image evidence before catalog mutation."]


def _workstream_review_summary(workflow: str, bucket: dict[str, Any]) -> dict[str, Any]:
    attachment_readiness = _attachment_readiness(bucket.get("items") or [])
    return {
        "review_lane": _review_lane(workflow),
        "queued_rows": bucket["queued_image_rows"],
        "source_url_update_required_rows": bucket["source_url_update_template_rows"],
        "representative_image_review_rows": bucket["representative_image_review_rows"],
        "image_url_ready_rows": bucket["image_url_ready_rows"],
        "primary_review_url_rows": bucket["primary_review_url_rows"],
        "first_primary_review_url": bucket["first_primary_review_url"],
        "first_primary_review_url_kind": bucket["first_primary_review_url_kind"],
        "primary_blockers": _image_import_blockers(workflow),
        "attachment_readiness": attachment_readiness,
        "manual_confirmation_requirements": _manual_confirmation_requirements(workflow),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--gotouchi-candidates", type=Path, default=DEFAULT_GOTOUCHI_CANDIDATES)
    parser.add_argument("--source-candidates", type=Path, default=DEFAULT_SOURCE_CANDIDATES)
    parser.add_argument(
        "--source-candidate-fallback",
        type=Path,
        default=DEFAULT_SOURCE_CANDIDATE_FALLBACK,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-batches", type=int, default=18)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()

    report = build_report(
        _load(args.input),
        _load(args.catalog) if args.catalog.exists() else None,
        _load(args.gotouchi_candidates) if args.gotouchi_candidates.exists() else None,
        _load(args.source_candidates) if args.source_candidates.exists() else None,
        _load(args.source_candidate_fallback)
        if args.source_candidate_fallback.exists()
        else None,
        max_batches=args.max_batches,
        batch_size=args.batch_size,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
