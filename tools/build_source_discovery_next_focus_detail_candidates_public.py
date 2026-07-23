from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from enrich_catalog_images import (
    AnimateSearchProvider,
    ProductImage,
    SEARCH_PROVIDERS,
    _has_all_distinctive_token_matches,
    _has_goods_type_compatibility,
    _parenthetical_terms_match,
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


SearchFn = Callable[[dict[str, Any]], list[ProductImage]]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _query_for_item(item: dict[str, Any]) -> str:
    return str(
        item.get("search_query")
        or item.get("name_ja")
        or item.get("name_ko")
        or ""
    ).strip()


def _candidate_status(
    query: str,
    candidate: ProductImage,
    score: tuple[int, float],
    rank: int,
) -> str:
    type_ok = _has_goods_type_compatibility(query, candidate.title)
    distinctive_ok = _has_all_distinctive_token_matches(query, candidate.title)
    parenthetical_ok = _parenthetical_terms_match(query, candidate.title)
    source_ok = bool(candidate.source_url and is_product_specific_source_url(candidate.source_url))
    pair_ok = bool(
        candidate.source_url
        and candidate.image_url
        and is_safe_source_image_pair(candidate.source_url, candidate.image_url)
    )
    if (
        rank == 1
        and score[0] >= 2
        and score[1] >= 0.62
        and type_ok
        and distinctive_ok
        and parenthetical_ok
        and source_ok
        and pair_ok
    ):
        return "exact_candidate_review"
    if source_ok and pair_ok:
        return "manual_candidate_review"
    if not source_ok:
        return "blocked_no_product_detail_url"
    if not pair_ok:
        return "blocked_no_safe_image_pair"
    return "weak_or_ambiguous"


def _candidate_row(query: str, candidate: ProductImage, rank: int) -> dict[str, Any]:
    score = _score(query, candidate.title)
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
    generated_at: str | None = None,
    candidate_limit: int = 5,
) -> dict[str, Any]:
    search = search_fn or _default_searcher()
    items: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    candidate_rows = 0
    items_with_candidates = 0
    for item in next_focus_pack.get("items") or []:
        if not isinstance(item, dict):
            continue
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
        else:
            status_counts["no_candidates_found" if fetch_status == "ok" else "candidate_fetch_error"] += 1
        for candidate in candidate_payload:
            status_counts[str(candidate.get("review_status") or "")] += 1
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
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "search_query": query,
                "official_search_url": item.get("official_search_url"),
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
            "candidate_rows": candidate_rows,
            "exact_candidate_review_rows": status_counts.get("exact_candidate_review", 0),
            "manual_candidate_review_rows": status_counts.get("manual_candidate_review", 0),
            "no_candidate_items": status_counts.get("no_candidates_found", 0),
            "candidate_fetch_error_items": status_counts.get("candidate_fetch_error", 0),
            "status_counts": [[key, value] for key, value in status_counts.most_common() if key],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Review each candidate_source_url as an exact product/detail page before confirmation.",
            "Only fill manual_confirmed_source_url and manual_confirmed_image_url after title, variant, category, and image identity match.",
            "This report is candidate-only; it never mutates catalog data.",
        ],
        "items": items,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "confirmed_template": "data/source_discovery_focus_confirmed_template_public.json",
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate-limit", type=int, default=5)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), candidate_limit=args.candidate_limit)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
