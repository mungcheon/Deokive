from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
import re

from enrich_catalog_images import (
    _has_all_distinctive_token_matches,
    _has_goods_type_compatibility,
    _parenthetical_terms_match,
    _squash,
)
from image_enrichment_safety import is_product_specific_source_url, is_safe_source_image_pair
from import_manual_image_candidates import _candidate_title_matches_row

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_OUTPUT = ROOT / "server" / "catalog_image_auto_promotable_exact_candidates.json"
DEFAULT_REPORTS = [
    ROOT / "server" / "catalog_image_animate_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_ensky_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_goodsmile_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_kotobukiya_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_movic_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_taito_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_furyu_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_chiikawa_market_missing_current_dryrun.json",
]


def _load_seed_rows(seed_path: Path) -> list[dict[str, Any]]:
    rows = json.loads(seed_path.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise SystemExit(f"{seed_path} must contain a JSON list")
    return [row if isinstance(row, dict) else {} for row in rows]


def _read_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _top_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    top_candidates = item.get("top_candidates") or []
    if not isinstance(top_candidates, list) or not top_candidates:
        return None
    candidate = top_candidates[0]
    return candidate if isinstance(candidate, dict) else None


def _title_subsumes_query(query: str, title: str) -> bool:
    query_key = _squash(query)
    title_key = _squash(title)
    return bool(query_key and title_key and (query_key == title_key or query_key in title_key or title_key in query_key))


REVIEW_ONLY_TITLE_TERMS = ("×", "コラボ", "ランダム", "トレーディング", "セット", "全")


def _has_unrequested_review_only_term(query: str, title: str) -> bool:
    return any(term in title and term not in query for term in REVIEW_ONLY_TITLE_TERMS)


def _candidate_row_name_matches_current_seed(item: dict[str, Any], seed_row: dict[str, Any]) -> bool:
    item_ko = str(item.get("name_ko") or "").strip()
    item_ja = str(item.get("name_ja") or "").strip()
    query = str(item.get("query") or "").strip()
    row_ko = str(seed_row.get("name_ko") or "").strip()
    row_ja = str(seed_row.get("name_ja") or "").strip()
    if not item_ko and not item_ja and not query:
        return True
    return bool(
        (item_ko and item_ko == row_ko)
        or (item_ja and item_ja == row_ja)
        or (query and (query == row_ko or query == row_ja))
    )


def _promotable(item: dict[str, Any], candidate: dict[str, Any], seed_row: dict[str, Any]) -> bool:
    query = str(item.get("query") or item.get("name_ja") or item.get("name_ko") or "").strip()
    title = str(candidate.get("title") or "").strip()
    source_url = str(candidate.get("source_url") or "").strip()
    image_url = str(candidate.get("image_url") or "").strip()
    return (
        str(item.get("reason") or "") == "best_candidate_rejected"
        and _title_subsumes_query(query, title)
        and not _has_unrequested_review_only_term(query, title)
        and _has_goods_type_compatibility(query, title)
        and _has_all_distinctive_token_matches(query, title)
        and _parenthetical_terms_match(query, title)
        and _candidate_title_matches_row({"candidate_title": title}, seed_row)
        and is_product_specific_source_url(source_url)
        and is_safe_source_image_pair(source_url, image_url)
    )

def _provider_flag_promotable(item: dict[str, Any], candidate: dict[str, Any], seed_row: dict[str, Any]) -> bool:
    query = str(item.get("query") or item.get("name_ja") or item.get("name_ko") or "").strip()
    title = str(candidate.get("title") or "").strip()
    source_url = str(candidate.get("source_url") or "").strip()
    image_url = str(candidate.get("image_url") or "").strip()
    if str(item.get("reason") or "") != "best_candidate_rejected":
        return False
    if not re.search(r"[（(][^)）]+[)）]", query):
        return False
    if float(candidate.get("score_similarity") or 0) < 0.98:
        return False
    if _has_unrequested_review_only_term(query, title):
        return False
    return (
        bool(candidate.get("goods_type_compatible"))
        and bool(candidate.get("distinctive_token_match"))
        and bool(candidate.get("all_distinctive_token_match"))
        and bool(candidate.get("parenthetical_terms_match"))
        and bool(candidate.get("source_url_is_product_detail"))
        and bool(candidate.get("safe_source_image_pair"))
        and _candidate_title_matches_row({"candidate_title": title}, seed_row)
        and is_product_specific_source_url(source_url)
        and is_safe_source_image_pair(source_url, image_url)
    )


def build_candidates(report_paths: list[Path], seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen_rows: set[int] = set()
    for report_path in report_paths:
        payload = _read_report(report_path)
        for item in payload.get("unresolved") or []:
            if not isinstance(item, dict):
                continue
            row_index = item.get("row_index")
            if not isinstance(row_index, int) or isinstance(row_index, bool) or not (0 <= row_index < len(seed_rows)):
                skipped.append({"row_index": row_index, "reason": "invalid_row_index", "report": str(report_path)})
                continue
            if row_index in seen_rows:
                skipped.append({"row_index": row_index, "reason": "duplicate_row_index", "report": str(report_path)})
                continue
            seed_row = seed_rows[row_index]
            if not _candidate_row_name_matches_current_seed(item, seed_row):
                skipped.append(
                    {
                        "row_index": row_index,
                        "reason": "candidate_row_name_mismatch",
                        "candidate_name_ko": item.get("name_ko"),
                        "candidate_name_ja": item.get("name_ja"),
                        "current_name_ko": seed_row.get("name_ko"),
                        "current_name_ja": seed_row.get("name_ja"),
                        "report": str(report_path),
                    }
                )
                continue
            if seed_row.get("image_url"):
                skipped.append({"row_index": row_index, "reason": "already_has_image", "report": str(report_path)})
                continue
            candidate = _top_candidate(item)
            if not candidate or not (
                _promotable(item, candidate, seed_row)
                or _provider_flag_promotable(item, candidate, seed_row)
            ):
                continue
            seen_rows.add(row_index)
            items.append(
                {
                    "row_index": row_index,
                    "name_ko": item.get("name_ko"),
                    "query": item.get("query"),
                    "candidate_title": candidate.get("title"),
                    "source_store": item.get("source_store"),
                    "source_kind": "licensed_retailer_exact",
                    "confidence": 0.92,
                    "source_url": candidate.get("source_url"),
                    "image_url": candidate.get("image_url"),
                    "manual_confirmed": True,
                    "report": str(report_path),
                }
            )
    return {
        "items": items,
        "summary": {
            "candidate_items": len(items),
            "skipped_items": len(skipped),
            "reports": len(report_paths),
        },
        "skipped_sample": skipped[:100],
        "policy": [
            "Only unresolved best_candidate_rejected rows are considered.",
            "The top candidate title must subsume the query, match goods type, distinctive tokens, and parenthetical terms.",
            "The source URL must be product-specific and the source/image pair must pass safety checks.",
            "Rows already containing image_url are excluded.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--report", type=Path, action="append", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report_paths = args.report or DEFAULT_REPORTS
    payload = build_candidates(report_paths, _load_seed_rows(args.seed))
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**payload["summary"], "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
