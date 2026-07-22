from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

    summary = {
        **summary,
        "updated_rows": updated,
        "change_rows": len(changes),
        "queue_rows": len(queue),
        "missing_image_queue_rows": len(missing_image_queue),
        "review_queue_rows": len(review_queue),
        "missing_image_review_queue_rows": len(missing_image_review_queue),
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
