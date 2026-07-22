from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "ensky_missing_image_cache_coverage_public.json"
DEFAULT_OUTPUT = DATA / "ensky_cache_candidate_action_queue_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def counter_rows(rows: list[dict[str, Any]], field: str) -> list[list[Any]]:
    counts = Counter(str(row.get(field) or "") for row in rows)
    counts.pop("", None)
    return [[key, value] for key, value in counts.most_common()]


def compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_title": candidate.get("title"),
        "candidate_source_url": candidate.get("source_url"),
        "candidate_image_url": candidate.get("image_url"),
        "safe_exact_match": candidate.get("safe_exact_match") is True,
        "score": candidate.get("score"),
        "matched_tokens": candidate.get("matched_tokens") or [],
    }


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        compact_candidate(candidate)
        for candidate in item.get("top_candidates", [])
        if isinstance(candidate, dict)
    ]
    top_candidate = candidates[0] if candidates else {}
    return {
        "manual_confirmed": False,
        "catalog_index": item.get("catalog_index"),
        "row_index": item.get("catalog_index"),
        "source_store": item.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "affiliation": item.get("affiliation"),
        "category": item.get("category"),
        "candidate_status": item.get("status"),
        "candidate_count": item.get("candidate_count"),
        "top_candidates": candidates[:5],
        "source_patch_template": {
            "manual_confirmed": False,
            "row_index": item.get("catalog_index"),
            "field": "source_url",
            "manual_value": top_candidate.get("candidate_source_url") or "",
            "evidence_url": top_candidate.get("candidate_source_url") or "",
            "candidate_source_url": top_candidate.get("candidate_source_url") or "",
            "source_store": item.get("source_store"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
        },
        "image_patch_template": {
            "manual_confirmed": False,
            "row_index": item.get("catalog_index"),
            "field": "image_url",
            "manual_value": top_candidate.get("candidate_image_url") or "",
            "evidence_url": top_candidate.get("candidate_source_url") or "",
            "candidate_source_url": top_candidate.get("candidate_source_url") or "",
            "source_store": item.get("source_store"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
        },
        "acceptance_criteria": [
            "Candidate title must match the exact product, character, and variant in the catalog row.",
            "Candidate source URL must be an Ensky product detail page, not search or category results.",
            "Candidate image must be the product image from the accepted Ensky product page.",
            "Leave manual_confirmed false for related goods, wrong characters, wrong goods type, or broad brand-only matches.",
        ],
        "recommended_action": "manual_review_ensky_cache_candidate_before_source_or_image_patch",
        "auto_apply_enabled": False,
    }


def build_report(cache_coverage: dict[str, Any], *, generated_at: str | None = None, batch_size: int = 10) -> dict[str, Any]:
    items = [
        compact_item(item)
        for item in cache_coverage.get("items", [])
        if isinstance(item, dict) and item.get("status") == "broad_cache_candidate"
    ]
    items.sort(
        key=lambda row: (
            -int(row.get("candidate_count") or 0),
            str(row.get("affiliation") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(items), batch_size):
        chunk = items[offset : offset + batch_size]
        batches.append(
            {
                "batch_id": f"ensky-cache-candidate-action-{len(batches) + 1:03d}",
                "row_count": len(chunk),
                "offset": offset,
                "review_state": "manual_identity_review_required",
                "source_store": "엔스카이",
                "next_machine_step": "manual_confirm_then_import_source_and_image_templates",
                "recommended_action": "Review broad Ensky cache candidates and confirm only exact product matches.",
                "by_affiliation": counter_rows(chunk, "affiliation"),
                "by_category": counter_rows(chunk, "category"),
                "items": chunk,
                "auto_apply_enabled": False,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "ensky_cache_candidate_action_queue",
        "summary": {
            "candidate_action_rows": len(items),
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "manual_confirmed_true": sum(1 for item in items if item.get("manual_confirmed") is True),
            "by_affiliation": counter_rows(items, "affiliation"),
            "by_category": counter_rows(items, "category"),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "These are broad Ensky sitemap cache candidates, not safe automatic matches.",
            "Only exact product, character, variant, and goods-type matches may be manually confirmed.",
            "Do not import source_url or image_url unless manual_confirmed is set true after review.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), batch_size=args.batch_size)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
