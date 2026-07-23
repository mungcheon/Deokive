from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections import Counter

import enrich_fanding_store_from_shop_api as fanding


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
REPORT = DATA / "stellive_fanding_candidates_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def catalog_items(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def build_report(catalog: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    rows = catalog_items(catalog)
    updated, changes, rejected, summary, queue = fanding.enrich(rows)
    missing_image_queue = [item for item in queue if item.get("missing_image_url")]
    review_queue = [
        item
        for item in queue
        if item.get("candidate_status") in {"strong_manual_review_candidate", "weak_manual_review_candidate"}
    ]
    missing_image_review_queue = [item for item in review_queue if item.get("missing_image_url")]
    missing_image_status_counts = _counter_dict(missing_image_queue, "candidate_status")
    missing_image_manual_search_rows = missing_image_status_counts.get("no_candidate", 0)
    missing_image_candidate_review_rows = len(missing_image_queue) - missing_image_manual_search_rows

    summary = {
        **summary,
        "updated_rows": updated,
        "change_rows": len(changes),
        "queue_rows": len(queue),
        "missing_image_queue_rows": len(missing_image_queue),
        "review_queue_rows": len(review_queue),
        "missing_image_review_queue_rows": len(missing_image_review_queue),
        "candidate_review_lane_counts": _counter_dict(queue, "candidate_review_lane"),
        "missing_image_candidate_review_lane_counts": _counter_dict(
            missing_image_queue, "candidate_review_lane"
        ),
        "missing_image_resolution_readiness": {
            "exact_source_image_ready_rows": 0,
            "manual_search_required_rows": missing_image_manual_search_rows,
            "candidate_review_required_rows": missing_image_candidate_review_rows,
            "weak_candidate_review_rows": missing_image_status_counts.get(
                "weak_manual_review_candidate",
                0,
            ),
            "low_confidence_candidate_review_rows": missing_image_status_counts.get(
                "low_confidence_candidate",
                0,
            ),
            "blocking_reason": (
                "No missing-image Stellive/Fanding row has a unique exact product "
                "identity match. Confirm exact product detail pages before importing images."
            ),
            "next_safe_step": (
                f"Resolve the {missing_image_manual_search_rows} manual-search rows first, "
                f"then review the {missing_image_candidate_review_rows} candidate rows "
                "before image attachment."
            ),
        },
        "auto_apply_enabled": False,
    }
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "stellive_fanding_candidates",
        "summary": summary,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_human_review_before_source_or_image_attachment": True,
            "note": (
                "Fanding fuzzy candidates are review-only. Missing-image rows are not auto-updated; "
                "confirm exact product source_url and image_url before import."
            ),
        },
        "queue": queue,
        "missing_image_review_queue": missing_image_review_queue,
        "rejected_sample": rejected,
    }


def _counter_dict(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(str(row.get(field) or "unknown") for row in rows)
    return {key: counts[key] for key in sorted(counts)}


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
