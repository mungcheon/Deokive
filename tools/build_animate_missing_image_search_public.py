from __future__ import annotations

import argparse
import json
import re
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
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
MULTI_VARIANT_MARKERS = (
    "\ub79c\ub364",
    "\ud2b8\ub808\uc774\ub529",
    "\uc138\ud2b8",
    "\uba54\uc778",
    "\uc77c\ub2f9",
    "\ud30c",
    "\u30c8\u30ec\u30fc\u30c7\u30a3\u30f3\u30b0",
    "\u30e9\u30f3\u30c0\u30e0",
    "\u30bb\u30c3\u30c8",
    "\u30e1\u30a4\u30f3",
    "\uff06",
    "\u00d7",
    "VS",
    "&",
)
BROAD_CATEGORY_VALUES = {
    "\ubb38\uad6c",
    "\uce94\ubc43\uc9c0",
    "\uc0dd\ud65c\uc7a1\ud654",
    "\ud0a4\ub9c1",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def candidate_review_risk(row: dict[str, Any], qrow: dict[str, Any]) -> tuple[str, list[str], str]:
    reasons: list[str] = []
    name_ko = str(row.get("name_ko") or "")
    name_ja = str(row.get("name_ja") or "")
    category = str(row.get("category") or "")
    query = str(qrow.get("query") or "")
    search_text = " ".join([name_ko, name_ja, query])

    if not present(name_ja):
        reasons.append("missing_official_language_name")
    if HANGUL_RE.search(query):
        reasons.append("hangul_search_query_needs_japanese_rewrite")
    if any(marker in search_text for marker in MULTI_VARIANT_MARKERS):
        reasons.append("multi_variant_or_blind_pack_title")
    if category in BROAD_CATEGORY_VALUES:
        reasons.append("broad_goods_category")

    if "missing_official_language_name" in reasons or "hangul_search_query_needs_japanese_rewrite" in reasons:
        return "high", reasons, "add_or_confirm_japanese_product_name_before_image_attachment"
    if "multi_variant_or_blind_pack_title" in reasons:
        return "high", reasons, "confirm_exact_variant_or_package_image_on_official_detail_page"
    if "broad_goods_category" in reasons:
        return "medium", reasons, "confirm_exact_detail_page_before_import"
    return "medium", reasons or ["official_search_only"], "open_official_search_result_and_confirm_detail_page"


def research_status(review_reasons: list[str], search_url: Any) -> tuple[str, str]:
    reason_set = set(review_reasons)
    if "missing_official_language_name" in reason_set:
        return "needs_official_language_name", "add_japanese_or_official_product_name_before_search"
    if "hangul_search_query_needs_japanese_rewrite" in reason_set:
        return "needs_query_rewrite", "rewrite_search_query_to_japanese_official_terms"
    if not present(search_url):
        return "needs_search_url", "build_official_animate_search_url"
    if "multi_variant_or_blind_pack_title" in reason_set:
        return "needs_variant_confirmation", "confirm_exact_variant_or_package_on_animate_detail_page"
    return "reviewable_search_url", "open_search_url_and_confirm_exact_product_detail"


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
    by_candidate_review_risk: Counter[str] = Counter()
    by_research_status: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_affiliation: Counter[str] = Counter()
    source_research_required: list[dict[str, Any]] = []

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
        review_risk, review_reasons, next_action = candidate_review_risk(row, qrow)
        status, status_next_action = research_status(review_reasons, search_url)
        by_strategy[strategy] += 1
        by_automation_safety[automation_safety] += 1
        by_candidate_review_risk[review_risk] += 1
        by_research_status[status] += 1
        by_category[category] += 1
        by_affiliation[affiliation] += 1
        item = {
            "catalog_index": catalog_index,
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
            "affiliation": row.get("affiliation"),
            "category": row.get("category"),
            "query": qrow.get("query"),
            "search_url": search_url,
            "strategy": strategy,
            "automation_safety": automation_safety,
            "candidate_review_risk": review_risk,
            "candidate_review_reasons": review_reasons,
            "research_status": status,
            "research_next_action": status_next_action,
            "next_action": next_action,
            "manual_review_required": True,
            "import_template": {
                "catalog_index": catalog_index,
                "source_url": None,
                "image_url": None,
                "manual_confirmed": False,
                "blocked_until": "exact_animate_product_page_confirmed",
            },
        }
        matched_items.append(item)
        if status != "reviewable_search_url":
            source_research_required.append(
                {
                    **item,
                    "import_template": {
                        **item["import_template"],
                        "blocked_until": "official_animate_search_query_or_exact_source_confirmed",
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
            "reviewable_search_url_rows": by_research_status.get("reviewable_search_url", 0),
            "source_research_required_rows": len(source_research_required),
            "auto_apply_enabled": False,
            "search_page": ANIMATE_SEARCH_TEMPLATE,
        },
        "breakdowns": {
            "by_strategy": [{"strategy": key, "rows": value} for key, value in by_strategy.most_common()],
            "by_automation_safety": [
                {"automation_safety": key, "rows": value} for key, value in by_automation_safety.most_common()
            ],
            "by_candidate_review_risk": [
                {"candidate_review_risk": key, "rows": value}
                for key, value in by_candidate_review_risk.most_common()
            ],
            "by_research_status": [
                {"research_status": key, "rows": value}
                for key, value in by_research_status.most_common()
            ],
            "by_category": [{"category": key, "rows": value} for key, value in by_category.most_common(30)],
            "by_affiliation": [{"affiliation": key, "rows": value} for key, value in by_affiliation.most_common(30)],
        },
        "items": matched_items,
        "source_research_required": {
            "row_count": len(source_research_required),
            "by_research_status": [
                {"research_status": key, "rows": value}
                for key, value in Counter(
                    str(item.get("research_status") or "") for item in source_research_required
                ).most_common()
            ],
            "items": sorted(
                source_research_required,
                key=lambda item: (
                    str(item.get("research_status") or ""),
                    str(item.get("affiliation") or ""),
                    str(item.get("category") or ""),
                    int(item.get("catalog_index") or 999_999_999),
                ),
            )[:80],
        },
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
