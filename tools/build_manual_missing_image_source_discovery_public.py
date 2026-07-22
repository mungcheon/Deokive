from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORK_QUEUE = DATA / "catalog_missing_image_work_queue_public.json"
REPORT = DATA / "manual_missing_image_source_discovery_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def queue_items(queue: dict[str, Any]) -> list[dict[str, Any]]:
    items = queue.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_missing_image_work_queue_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def manual_rows(queue: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in queue_items(queue)
        if item.get("strategy") == "manual_review"
        and item.get("automation_safety") == "manual_research_required"
    ]


def counter_rows(counter: Counter[str], field: str, limit: int | None = None) -> list[dict[str, Any]]:
    return [{field: key, "rows": count} for key, count in counter.most_common(limit)]


def build_report(
    queue: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows = manual_rows(queue)
    by_store: Counter[str] = Counter(str(item.get("source_store") or "") for item in rows)
    by_category: Counter[str] = Counter(str(item.get("category") or "") for item in rows)
    by_affiliation: Counter[str] = Counter(str(item.get("affiliation") or "") for item in rows)

    items = [
        {
            "catalog_index": item.get("row_index"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "name_en": item.get("name_en"),
            "source_store": item.get("source_store"),
            "affiliation": item.get("affiliation"),
            "category": item.get("category"),
            "query": item.get("query"),
            "strategy": item.get("strategy"),
            "automation_safety": item.get("automation_safety"),
            "manual_review_required": True,
            "source_discovery_template": {
                "catalog_index": item.get("row_index"),
                "source_url": None,
                "image_url": None,
                "source_store": item.get("source_store"),
                "evidence_url": None,
                "manual_confirmed": False,
                "blocked_until": "exact_official_product_source_url_found",
            },
        }
        for item in rows
    ]

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "manual_missing_image_source_discovery",
        "summary": {
            "manual_source_discovery_rows": len(rows),
            "source_store_count": len(by_store),
            "top_source_store": by_store.most_common(1)[0][0] if by_store else None,
            "top_source_store_rows": by_store.most_common(1)[0][1] if by_store else 0,
            "auto_apply_enabled": False,
        },
        "breakdowns": {
            "by_source_store": counter_rows(by_store, "source_store", 40),
            "by_category": counter_rows(by_category, "category", 40),
            "by_affiliation": counter_rows(by_affiliation, "affiliation", 40),
        },
        "items": items,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_official_or_licensed_source_url": True,
            "requires_human_review_before_source_or_image_attachment": True,
        },
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=WORK_QUEUE)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.queue))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
