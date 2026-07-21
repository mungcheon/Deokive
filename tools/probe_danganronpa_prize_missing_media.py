from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_detail_candidates as detail_candidates
from image_enrichment_safety import is_safe_source_image_pair


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = ROOT / "data" / "danganronpa_missing_media_public.json"
DEFAULT_REPORT = ROOT / "data" / "danganronpa_prize_probe_public.json"
TARGET_STORES = {"Taito", "FuRyu"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"[^0-9a-z\u3040-\u30ff\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: Any) -> set[str]:
    stop = {
        "figure",
        "\u30d5\u30a3\u30ae\u30e5\u30a2",
        "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1",
        "\u30d7\u30ec\u30df\u30a2\u30e0",
    }
    return {token for token in _norm(value).split() if len(token) >= 2 and token not in stop}


def _query_for(row: dict[str, Any]) -> str:
    return str(row.get("name_ja") or row.get("name_ko") or "").strip()


def _candidates_for(row: dict[str, Any]) -> list[dict[str, Any]]:
    query = _query_for(row)
    if row.get("source_store") == "Taito":
        return detail_candidates._taito_candidates(query)
    if row.get("source_store") == "FuRyu":
        return detail_candidates._furyu_candidates(query)
    return []


def _candidate_status(row: dict[str, Any], candidate: dict[str, Any]) -> str:
    title_tokens = _tokens(candidate.get("candidate_title"))
    query_tokens = _tokens(row.get("name_ja") or row.get("name_ko"))
    if not is_safe_source_image_pair(candidate.get("candidate_source_url"), candidate.get("candidate_image_url")):
        return "unsafe_source_image_pair"
    if query_tokens and query_tokens.issubset(title_tokens):
        return "exact_token_candidate"
    if query_tokens and len(query_tokens & title_tokens) >= max(1, len(query_tokens) - 1):
        return "near_token_candidate"
    return "title_mismatch"


def _load_queue(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def build_report(queue_items: list[dict[str, Any]], *, max_rows: int | None = None) -> dict[str, Any]:
    targets = [item for item in queue_items if item.get("source_store") in TARGET_STORES]
    if max_rows is not None:
        targets = targets[:max_rows]

    rows: list[dict[str, Any]] = []
    candidate_status_counts: dict[str, int] = {}
    for item in targets:
        try:
            candidates = _candidates_for(item)
            fetch_error = None
        except Exception as exc:
            candidates = []
            fetch_error = str(exc)

        compact_candidates = []
        for candidate in candidates[:8]:
            status = _candidate_status(item, candidate)
            candidate_status_counts[status] = candidate_status_counts.get(status, 0) + 1
            compact_candidates.append(
                {
                    "candidate_status": status,
                    "candidate_title": candidate.get("candidate_title"),
                    "candidate_source_url": candidate.get("candidate_source_url"),
                    "candidate_image_url": candidate.get("candidate_image_url"),
                }
            )

        exact_candidates = [candidate for candidate in compact_candidates if candidate["candidate_status"] == "exact_token_candidate"]
        near_candidates = [candidate for candidate in compact_candidates if candidate["candidate_status"] == "near_token_candidate"]
        if len(exact_candidates) == 1:
            review_state = "single_exact_candidate_review_required"
        elif len(exact_candidates) > 1:
            review_state = "ambiguous_exact_candidates"
        elif near_candidates:
            review_state = "near_candidate_review_required"
        elif fetch_error:
            review_state = "provider_fetch_failed"
        elif compact_candidates:
            review_state = "candidate_title_mismatch"
        else:
            review_state = "no_provider_candidates"

        rows.append(
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "query": _query_for(item),
                "review_state": review_state,
                "fetch_error": fetch_error,
                "candidate_count": len(candidates),
                "candidates": compact_candidates,
                "auto_apply_enabled": False,
                "recommended_action": "review_single_exact_candidate_before_patch"
                if review_state == "single_exact_candidate_review_required"
                else "manual_identity_review_required",
            }
        )

    by_state: dict[str, int] = {}
    by_store: dict[str, int] = {}
    for row in rows:
        by_state[row["review_state"]] = by_state.get(row["review_state"], 0) + 1
        by_store[str(row.get("source_store") or "unknown")] = by_store.get(str(row.get("source_store") or "unknown"), 0) + 1

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "danganronpa_prize_missing_media_probe",
        "summary": {
            "target_rows": len(rows),
            "single_exact_candidate_rows": by_state.get("single_exact_candidate_review_required", 0),
            "near_candidate_rows": by_state.get("near_candidate_review_required", 0),
            "provider_fetch_failed_rows": by_state.get("provider_fetch_failed", 0),
            "no_provider_candidate_rows": by_state.get("no_provider_candidates", 0),
            "by_review_state": sorted(by_state.items()),
            "by_source_store": sorted(by_store.items()),
            "candidate_status_counts": sorted(candidate_status_counts.items()),
            "auto_apply_enabled": False,
        },
        "items": rows,
        "instructions": [
            "This probe records Taito/FuRyu official prize API candidates for Danganronpa rows missing media.",
            "Single exact candidates still require manual product identity review before catalog patching.",
            "No marketplace or resale image is accepted by this probe.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()

    report = build_report(_load_queue(args.queue), max_rows=args.max_rows)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
