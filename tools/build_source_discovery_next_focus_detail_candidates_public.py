from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from enrich_catalog_images import (
    AnimateSearchProvider,
    ProductImage,
    SEARCH_PROVIDERS,
    _distinctive_query_tokens,
    _has_all_distinctive_token_matches,
    _has_goods_type_compatibility,
    _parenthetical_terms_match,
    _preferred_query_for_row,
    _score,
)
from image_enrichment_safety import is_product_specific_source_url, is_safe_source_image_pair


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_next_focus_pack_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_next_focus_detail_candidates_public.json"
DEFAULT_FETCH_AUDIT = DATA / "source_discovery_next_focus_pack_fetch_audit_public.json"


SearchFn = Callable[[dict[str, Any]], list[ProductImage]]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _catalog_index(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fetch_audit_by_index(fetch_audit: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not isinstance(fetch_audit, dict):
        return {}
    rows: dict[int, dict[str, Any]] = {}
    for item in fetch_audit.get("items") or []:
        if not isinstance(item, dict):
            continue
        catalog_index = _catalog_index(item.get("catalog_index"))
        if catalog_index is not None:
            rows[catalog_index] = item
    return rows


def _query_for_item(item: dict[str, Any]) -> str:
    query_row = dict(item)
    field_template = item.get("catalog_field_import_template")
    if isinstance(field_template, dict):
        for key in ("affiliation", "category", "name_ko", "name_ja", "source_store"):
            if not query_row.get(key) and field_template.get(key):
                query_row[key] = field_template.get(key)
    preferred = _preferred_query_for_row(query_row)
    if preferred:
        return preferred
    return str(item.get("search_query") or item.get("name_ja") or item.get("name_ko") or "").strip()


def _candidate_status(
    query: str,
    candidate: ProductImage,
    score: tuple[int, float],
    rank: int,
) -> str:
    blockers = _candidate_exact_review_blockers(query, candidate, score, rank)
    source_ok = bool(candidate.source_url and is_product_specific_source_url(candidate.source_url))
    pair_ok = bool(
        candidate.source_url
        and candidate.image_url
        and is_safe_source_image_pair(candidate.source_url, candidate.image_url)
    )
    if not blockers:
        return "exact_candidate_review"
    if source_ok and pair_ok:
        return "manual_candidate_review"
    if not source_ok:
        return "blocked_no_product_detail_url"
    if not pair_ok:
        return "blocked_no_safe_image_pair"
    return "weak_or_ambiguous"


def _candidate_exact_review_blockers(
    query: str,
    candidate: ProductImage,
    score: tuple[int, float],
    rank: int,
) -> list[str]:
    blockers: list[str] = []
    parenthetical_terms = [
        term.strip()
        for term in re.findall(r"\(([^)]+)\)", query or "")
        if term.strip()
    ]
    source_ok = bool(candidate.source_url and is_product_specific_source_url(candidate.source_url))
    pair_ok = bool(
        candidate.source_url
        and candidate.image_url
        and is_safe_source_image_pair(candidate.source_url, candidate.image_url)
    )

    if rank != 1:
        blockers.append("rank_not_first")
    if score[0] < 2:
        blockers.append("token_overlap_below_2")
    if score[1] < 0.62:
        blockers.append("similarity_below_0_62")
    if not _has_goods_type_compatibility(query, candidate.title):
        blockers.append("goods_type_mismatch")
    if not _has_all_distinctive_token_matches(query, candidate.title):
        blockers.append("distinctive_tokens_missing")
    if not _parenthetical_terms_match(query, candidate.title):
        blockers.append("parenthetical_terms_missing")
    if not parenthetical_terms and len(_distinctive_query_tokens(query)) <= 2:
        blockers.append("broad_query_without_variant")
    if not source_ok:
        blockers.append("non_product_source_url")
    if not pair_ok:
        blockers.append("unsafe_source_image_pair")
    return blockers


def _candidate_row(query: str, candidate: ProductImage, rank: int) -> dict[str, Any]:
    score = _score(query, candidate.title)
    blockers = _candidate_exact_review_blockers(query, candidate, score, rank)
    return {
        "rank": rank,
        "candidate_title": candidate.title,
        "candidate_source_url": candidate.source_url,
        "candidate_image_url": candidate.image_url,
        "token_overlap": score[0],
        "similarity": round(score[1], 4),
        "type_compatible": _has_goods_type_compatibility(query, candidate.title),
        "all_distinctive_token_match": _has_all_distinctive_token_matches(query, candidate.title),
        "parenthetical_terms_match": _parenthetical_terms_match(query, candidate.title),
        "product_source_url": bool(candidate.source_url and is_product_specific_source_url(candidate.source_url)),
        "safe_source_image_pair": bool(
            candidate.source_url
            and candidate.image_url
            and is_safe_source_image_pair(candidate.source_url, candidate.image_url)
        ),
        "exact_candidate_gate_passed": not blockers,
        "exact_candidate_blockers": blockers,
        "review_status": _candidate_status(query, candidate, score, rank),
    }


def _default_searcher() -> SearchFn:
    provider = AnimateSearchProvider("애니메이트", SEARCH_PROVIDERS["애니메이트"]["search_url"])

    def search(item: dict[str, Any]) -> list[ProductImage]:
        query = _query_for_item(item)
        if not query:
            return []
        return provider.search_images(query)

    return search


def build_report(
    next_focus_pack: dict[str, Any],
    *,
    search_fn: SearchFn | None = None,
    fetch_audit: dict[str, Any] | None = None,
    generated_at: str | None = None,
    candidate_limit: int = 8,
) -> dict[str, Any]:
    search = search_fn or _default_searcher()
    audit_by_index = _fetch_audit_by_index(fetch_audit)
    items: list[dict[str, Any]] = []
    candidate_confirmation_template: list[dict[str, Any]] = []
    exact_candidate_confirmation_shortlist: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    audit_status_counts: Counter[str] = Counter()
    candidate_rows = 0
    items_with_candidates = 0
    candidate_items_with_official_no_results = 0
    candidate_rows_from_fallback_search = 0
    for item in next_focus_pack.get("items") or []:
        if not isinstance(item, dict):
            continue
        audit_item = audit_by_index.get(_catalog_index(item.get("catalog_index")) or -1) or {}
        official_search_no_results = bool(audit_item.get("no_results_page"))
        needs_fallback_web_search = bool(audit_item.get("needs_fallback_web_search"))
        audit_status = (
            "official_search_no_results"
            if official_search_no_results
            else "official_search_unavailable"
            if needs_fallback_web_search
            else "official_search_has_results"
            if audit_item
            else "fetch_audit_missing"
        )
        audit_status_counts[audit_status] += 1
        query = _query_for_item(item)
        try:
            candidates = search(item)
            fetch_status = "ok"
            fetch_error = ""
        except Exception as exc:
            candidates = []
            fetch_status = "error"
            fetch_error = str(exc)
        candidate_payload = [
            _candidate_row(query, candidate, rank)
            for rank, candidate in enumerate(candidates[:candidate_limit], start=1)
        ]
        if candidate_payload:
            items_with_candidates += 1
            if official_search_no_results:
                candidate_items_with_official_no_results += 1
                candidate_rows_from_fallback_search += len(candidate_payload)
        else:
            status_counts["no_candidates_found" if fetch_status == "ok" else "candidate_fetch_error"] += 1
        for candidate in candidate_payload:
            status_counts[str(candidate.get("review_status") or "")] += 1
            template_row = {
                "manual_confirmed": False,
                "manual_review_status": "not_started",
                "manual_note": "",
                "focus_pack_id": item.get("focus_pack_id"),
                "catalog_index": item.get("catalog_index"),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation")
                or (item.get("catalog_field_import_template") or {}).get("affiliation"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "search_query": query,
                "candidate_rank": candidate.get("rank"),
                "candidate_review_status": candidate.get("review_status"),
                "candidate_title": candidate.get("candidate_title"),
                "candidate_source_url": candidate.get("candidate_source_url"),
                "candidate_image_url": candidate.get("candidate_image_url"),
                "manual_confirmed_source_url": "",
                "manual_confirmed_image_url": "",
                "evidence_url": candidate.get("candidate_source_url") or item.get("official_search_url"),
                "acceptance_criteria": (
                    "confirm exact product title, character/variant, category, source page, and image identity"
                ),
                "blocked_until": "manual_confirmed_true",
            }
            candidate_confirmation_template.append(template_row)
            if candidate.get("review_status") == "exact_candidate_review":
                exact_candidate_confirmation_shortlist.append(
                    {
                        **template_row,
                        "shortlist_reason": "exact_candidate_gate_passed",
                        "recommended_next_step": (
                            "Open candidate_source_url and confirm the product image/variant before copying to manual_confirmed_* fields."
                        ),
                    }
                )
        candidate_rows += len(candidate_payload)
        items.append(
            {
                "manual_review_status": "not_started",
                "manual_confirmed_source_url": "",
                "manual_confirmed_image_url": "",
                "manual_note": "",
                "focus_pack_id": item.get("focus_pack_id"),
                "catalog_index": item.get("catalog_index"),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation")
                or (item.get("catalog_field_import_template") or {}).get("affiliation"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "search_query": query,
                "official_search_url": item.get("official_search_url"),
                "official_search_audit_status": audit_status,
                "official_search_no_results": official_search_no_results,
                "needs_fallback_web_search": needs_fallback_web_search,
                "official_search_product_detail_link_count": int(
                    audit_item.get("product_detail_link_count") or 0
                ),
                "official_search_fetch_block_reason": audit_item.get("fetch_block_reason") or "",
                "fetch_status": fetch_status,
                "fetch_error": fetch_error,
                "candidate_count": len(candidates),
                "candidates": candidate_payload,
                "source_patch_template": item.get("source_patch_template") or {},
                "catalog_field_import_template": item.get("catalog_field_import_template") or {},
                "auto_apply_enabled": False,
            }
        )

    next_summary = next_focus_pack.get("summary") if isinstance(next_focus_pack.get("summary"), dict) else {}
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_next_focus_detail_candidates",
        "source_report": "data/source_discovery_next_focus_pack_public.json",
        "summary": {
            "focus_pack_id": next_summary.get("focus_pack_id"),
            "source_store": next_summary.get("source_store"),
            "target_category": next_summary.get("target_category"),
            "pack_items": len(items),
            "items_with_candidates": items_with_candidates,
            "items_with_candidates_from_official_no_results": candidate_items_with_official_no_results,
            "candidate_rows_from_fallback_search": candidate_rows_from_fallback_search,
            "candidate_rows": candidate_rows,
            "exact_candidate_review_rows": status_counts.get("exact_candidate_review", 0),
            "manual_candidate_review_rows": status_counts.get("manual_candidate_review", 0),
            "no_candidate_items": status_counts.get("no_candidates_found", 0),
            "candidate_fetch_error_items": status_counts.get("candidate_fetch_error", 0),
            "candidate_confirmation_template_rows": len(candidate_confirmation_template),
            "exact_candidate_confirmation_shortlist_rows": len(exact_candidate_confirmation_shortlist),
            "candidate_confirmation_exact_review_rows": sum(
                1
                for row in candidate_confirmation_template
                if row.get("candidate_review_status") == "exact_candidate_review"
            ),
            "candidate_confirmation_manual_review_rows": sum(
                1
                for row in candidate_confirmation_template
                if row.get("candidate_review_status") == "manual_candidate_review"
            ),
            "candidate_confirmation_manual_confirmed_rows": sum(
                1 for row in candidate_confirmation_template if row.get("manual_confirmed") is True
            ),
            "status_counts": [[key, value] for key, value in status_counts.most_common() if key],
            "official_search_audit_status_counts": [
                [key, value] for key, value in audit_status_counts.most_common() if key
            ],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Review each candidate_source_url as an exact product/detail page before confirmation.",
            "Only fill manual_confirmed_source_url and manual_confirmed_image_url after title, variant, category, and image identity match.",
            "This report is candidate-only; it never mutates catalog data.",
        ],
        "items": items,
        "exact_candidate_confirmation_shortlist": exact_candidate_confirmation_shortlist,
        "candidate_confirmation_template": candidate_confirmation_template,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "candidate_confirmation_template": "candidate_confirmation_template",
            "confirmed_template": "data/source_discovery_focus_confirmed_template_public.json",
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fetch-audit", type=Path, default=DEFAULT_FETCH_AUDIT)
    parser.add_argument("--candidate-limit", type=int, default=8)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    fetch_audit = load_json(args.fetch_audit) if args.fetch_audit.exists() else None
    report = build_report(load_json(args.input), fetch_audit=fetch_audit, candidate_limit=args.candidate_limit)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
