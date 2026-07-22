from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_detail_probe_public.json"
DEFAULT_OUTPUT = DATA / "source_detail_candidate_action_queue_public.json"


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


def candidate_count_bucket(row: dict[str, Any]) -> str:
    candidate_count = int(row.get("candidate_count") or 0)
    if candidate_count <= 0:
        return "no_candidate_count"
    if candidate_count == 1:
        return "single_candidate"
    if candidate_count <= 3:
        return "near_single_candidate"
    if candidate_count <= 10:
        return "small_candidate_set"
    return "large_candidate_set"


def candidate_risk(row: dict[str, Any]) -> str:
    score = row.get("score")
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        numeric_score = 0.0
    candidate_count = int(row.get("candidate_count") or 0)
    if row.get("status") == "exact_candidate_available" and numeric_score >= 0.8 and candidate_count == 1:
        return "strong_single_candidate_review"
    if numeric_score >= 0.75 and candidate_count <= 2:
        return "near_single_candidate_review"
    if numeric_score >= 0.5:
        return "ambiguous_candidate_review"
    return "weak_candidate_review"


def compact_item(row: dict[str, Any]) -> dict[str, Any]:
    risk = candidate_risk(row)
    return {
        "manual_confirmed": False,
        "catalog_index": row.get("catalog_index"),
        "row_index": row.get("catalog_index"),
        "source_store": row.get("source_store"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "query": row.get("query"),
        "candidate_status": row.get("status"),
        "candidate_count": row.get("candidate_count"),
        "candidate_count_bucket": candidate_count_bucket(row),
        "candidate_source_url": row.get("candidate_source_url"),
        "candidate_title": row.get("candidate_title"),
        "candidate_image_url": row.get("candidate_image_url"),
        "score": row.get("score"),
        "shared_tokens": row.get("shared_tokens") or [],
        "safe_source_image_pair": row.get("safe_source_image_pair"),
        "source_report": row.get("source_report"),
        "review_risk": risk,
        "review_priority": {
            "strong_single_candidate_review": 10,
            "near_single_candidate_review": 20,
            "ambiguous_candidate_review": 30,
            "weak_candidate_review": 40,
        }.get(risk, 99),
        "recommended_action": "confirm_exact_identity_before_source_or_image_patch",
        "source_patch_template": {
            "manual_confirmed": False,
            "row_index": row.get("catalog_index"),
            "field": "source_url",
            "manual_value": row.get("candidate_source_url") or "",
            "evidence_url": row.get("candidate_source_url") or "",
            "candidate_source_url": row.get("candidate_source_url") or "",
            "source_store": row.get("source_store"),
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
        },
        "image_patch_template": {
            "manual_confirmed": False,
            "row_index": row.get("catalog_index"),
            "field": "image_url",
            "manual_value": row.get("candidate_image_url") or "",
            "evidence_url": row.get("candidate_source_url") or "",
            "candidate_source_url": row.get("candidate_source_url") or "",
            "source_store": row.get("source_store"),
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
        },
        "acceptance_criteria": [
            "Candidate title must describe the same product, character, and variant as the catalog row.",
            "Candidate source URL must be an exact product/detail page.",
            "Candidate image must be the product image from the accepted source page or trusted official CDN.",
            "Leave manual_confirmed false when the candidate is a related product, bundle, or wrong variant.",
        ],
        "auto_apply_enabled": False,
    }


def build_report(source_detail_probe: dict[str, Any], *, generated_at: str | None = None, batch_size: int = 10) -> dict[str, Any]:
    items = [compact_item(row) for row in source_detail_probe.get("review_candidates") or [] if isinstance(row, dict)]
    items.sort(
        key=lambda row: (
            {"strong_single_candidate_review": 10, "near_single_candidate_review": 20, "ambiguous_candidate_review": 30}.get(
                str(row.get("review_risk") or ""),
                40,
            ),
            str(row.get("source_store") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(items), batch_size):
        chunk = items[offset : offset + batch_size]
        batches.append(
            {
                "batch_id": f"source-detail-candidate-action-{len(batches) + 1:03d}",
                "row_count": len(chunk),
                "offset": offset,
                "review_state": "manual_identity_review_required",
                "next_machine_step": "manual_confirm_then_import_source_and_image_templates",
                "recommended_action": "Review candidate identity and set manual_confirmed only for exact product matches.",
                "by_source_store": counter_rows(chunk, "source_store"),
                "by_review_risk": counter_rows(chunk, "review_risk"),
                "by_candidate_count_bucket": counter_rows(chunk, "candidate_count_bucket"),
                "safe_source_image_pair_rows": sum(1 for item in chunk if item.get("safe_source_image_pair") is True),
                "items": chunk,
                "auto_apply_enabled": False,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_detail_candidate_action_queue",
        "summary": {
            "candidate_action_rows": len(items),
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "manual_confirmed_true": sum(1 for item in items if item.get("manual_confirmed") is True),
            "safe_source_image_pair_rows": sum(1 for item in items if item.get("safe_source_image_pair") is True),
            "near_or_better_candidate_rows": sum(
                1
                for item in items
                if item.get("review_risk")
                in {"strong_single_candidate_review", "near_single_candidate_review"}
            ),
            "ambiguous_or_weaker_candidate_rows": sum(
                1
                for item in items
                if item.get("review_risk")
                not in {"strong_single_candidate_review", "near_single_candidate_review"}
            ),
            "by_source_store": counter_rows(items, "source_store"),
            "by_review_risk": counter_rows(items, "review_risk"),
            "by_candidate_count_bucket": counter_rows(items, "candidate_count_bucket"),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue only after reviewing source_detail_probe_public review candidates.",
            "Do not import candidate source_url or image_url unless manual_confirmed is set true after exact identity review.",
            "Rows may contain related products; wrong character or variant candidates must remain unconfirmed.",
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
