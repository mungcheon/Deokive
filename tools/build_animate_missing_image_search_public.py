from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
WORK_QUEUE = DATA / "catalog_missing_image_work_queue_public.json"
REPORT = DATA / "animate_missing_image_search_public.json"

ANIMATE_STORE = "\uc560\ub2c8\uba54\uc774\ud2b8"
ANIMATE_SEARCH_TEMPLATE = "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def catalog_items(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def queue_items(queue: dict[str, Any]) -> list[dict[str, Any]]:
    items = queue.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_missing_image_work_queue_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def missing_animate_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if item.get("source_store") == ANIMATE_STORE and not present(item.get("image_url"))
    ]


def animate_queue_rows(queue: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in queue_items(queue) if item.get("source_store") == ANIMATE_STORE]


def build_report(
    catalog: dict[str, Any],
    queue: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows = missing_animate_rows(catalog_items(catalog))
    qrows = animate_queue_rows(queue)
    queue_by_index = {item.get("row_index"): item for item in qrows if isinstance(item.get("row_index"), int)}

    matched_items: list[dict[str, Any]] = []
    missing_queue_rows: list[dict[str, Any]] = []
    missing_search_url_rows = 0
    by_strategy: Counter[str] = Counter()
    by_automation_safety: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_affiliation: Counter[str] = Counter()

    for row in rows:
        catalog_index = row.get("catalog_index")
        qrow = queue_by_index.get(catalog_index)
        if not qrow:
            missing_queue_rows.append(row)
            continue
        search_url = qrow.get("search_url")
        if not present(search_url):
            missing_search_url_rows += 1
        strategy = str(qrow.get("strategy") or "manual_review")
        automation_safety = str(qrow.get("automation_safety") or "manual_confirmation_required")
        category = str(row.get("category") or "")
        affiliation = str(row.get("affiliation") or "")
        by_strategy[strategy] += 1
        by_automation_safety[automation_safety] += 1
        by_category[category] += 1
        by_affiliation[affiliation] += 1
        matched_items.append(
            {
                "catalog_index": catalog_index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "affiliation": row.get("affiliation"),
                "category": row.get("category"),
                "query": qrow.get("query"),
                "search_url": search_url,
                "strategy": strategy,
                "automation_safety": automation_safety,
                "manual_review_required": True,
                "import_template": {
                    "catalog_index": catalog_index,
                    "source_url": None,
                    "image_url": None,
                    "manual_confirmed": False,
                    "blocked_until": "exact_animate_product_page_confirmed",
                },
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "animate_missing_image_search",
        "summary": {
            "missing_animate_image_rows": len(rows),
            "queue_rows": len(qrows),
            "matched_queue_rows": len(matched_items),
            "missing_queue_rows": len(missing_queue_rows),
            "missing_search_url_rows": missing_search_url_rows,
            "official_search_url_rows": sum(1 for item in matched_items if present(item.get("search_url"))),
            "auto_apply_enabled": False,
            "search_page": ANIMATE_SEARCH_TEMPLATE,
        },
        "breakdowns": {
            "by_strategy": [{"strategy": key, "rows": value} for key, value in by_strategy.most_common()],
            "by_automation_safety": [
                {"automation_safety": key, "rows": value} for key, value in by_automation_safety.most_common()
            ],
            "by_category": [{"category": key, "rows": value} for key, value in by_category.most_common(30)],
            "by_affiliation": [{"affiliation": key, "rows": value} for key, value in by_affiliation.most_common(30)],
        },
        "items": matched_items,
        "missing_queue_samples": [
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "affiliation": item.get("affiliation"),
                "category": item.get("category"),
            }
            for item in missing_queue_rows[:20]
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_exact_animate_product_page": True,
            "requires_human_review_before_source_or_image_attachment": True,
        },
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CATALOG)
    parser.add_argument("--queue", type=Path, default=WORK_QUEUE)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), load_json(args.queue))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
