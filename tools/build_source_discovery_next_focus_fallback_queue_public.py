from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NEXT_PACK = DATA / "source_discovery_next_focus_pack_public.json"
FETCH_AUDIT = DATA / "source_discovery_next_focus_pack_fetch_audit_public.json"
REPORT = DATA / "source_discovery_next_focus_fallback_queue_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _catalog_index(item: dict[str, Any]) -> int | None:
    try:
        return int(item.get("catalog_index"))
    except (TypeError, ValueError):
        return None


def _search_terms(item: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in ("name_ja", "name_ko"):
        value = str(item.get(key) or "").strip()
        if value and value not in terms:
            terms.append(value)
    return terms


def _legacy_store_search_url(item: dict[str, Any]) -> str:
    if not _search_terms(item):
        return ""
    raw = str(item.get("official_search_url") or item.get("web_search_url") or "")
    return raw.replace("products/list.php", "sphone/products/list.php")


def _domain_limited_web_search_urls(item: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    domains = item.get("allowed_source_domains") or ["www.animate-onlineshop.jp"]
    domain = str(domains[0] or "www.animate-onlineshop.jp").strip()
    for term in _search_terms(item):
        queries = [
            f'site:{domain}/pn/ "{term}"',
            f'site:{domain}/pn/ "{term}" "pd/"',
            f'site:{domain}/pn/ "{term}" "アニメイト通販"',
        ]
        for query in queries:
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            if url not in urls:
                urls.append(url)
    return urls


def _fallback_search_queries(item: dict[str, Any]) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    domains = item.get("allowed_source_domains") or ["www.animate-onlineshop.jp"]
    domain = str(domains[0] or "www.animate-onlineshop.jp").strip()
    for term in _search_terms(item):
        for purpose, suffix in [
            ("exact_title_detail_page", ""),
            ("exact_title_pd_path", " pd/"),
            ("exact_title_animate_product_page", " アニメイト通販"),
        ]:
            query = f'site:{domain}/pn/ "{term}"{suffix}'
            queries.append(
                {
                    "purpose": purpose,
                    "query": query,
                    "search_url": f"https://www.google.com/search?q={quote_plus(query)}",
                }
            )
    return queries


def _fallback_work_order(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not queue_items:
        return []

    return [
        {
            "rank": 1,
            "lane": "domain_limited_exact_title_search",
            "description": "Open the first domain-limited query for each row and look for an exact Animate product detail page.",
            "queue_rows": len(queue_items),
            "query_count": sum(1 for item in queue_items if item.get("domain_limited_web_search_urls")),
            "sample_search_urls": [
                item["domain_limited_web_search_urls"][0]
                for item in queue_items[:5]
                if item.get("domain_limited_web_search_urls")
            ],
        },
        {
            "rank": 2,
            "lane": "legacy_mobile_store_search",
            "description": "If web search is weak, open the legacy mobile Animate search URL and inspect product-detail results manually.",
            "queue_rows": sum(1 for item in queue_items if item.get("fallback_store_search_url")),
            "sample_search_urls": [
                item["fallback_store_search_url"]
                for item in queue_items[:5]
                if item.get("fallback_store_search_url")
            ],
        },
        {
            "rank": 3,
            "lane": "evidence_fill_and_dry_run",
            "description": "Only after exact identity is confirmed, fill manual_confirmed_source_url/manual_evidence_url and run the dry-run importer.",
            "queue_rows": len(queue_items),
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
            "dry_run_report": "data/source_discovery_next_focus_fallback_import_dry_run_public.json",
        },
    ]


def build_report(
    next_pack: dict[str, Any],
    fetch_audit: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    pack_items = next_pack.get("items") or []
    audit_by_index = {
        _catalog_index(item): item
        for item in fetch_audit.get("items") or []
        if isinstance(item, dict) and _catalog_index(item) is not None
    }

    queue_items: list[dict[str, Any]] = []
    for item in pack_items:
        if not isinstance(item, dict):
            continue
        catalog_index = _catalog_index(item)
        audit_item = audit_by_index.get(catalog_index) or {}
        if not audit_item.get("needs_fallback_web_search"):
            continue
        queue_items.append(
            {
                "manual_review_status": "fallback_not_started",
                "manual_confirmed": False,
                "manual_confirmed_source_url": "",
                "manual_confirmed_image_url": "",
                "manual_evidence_url": "",
                "manual_note": "",
                "catalog_index": catalog_index,
                "focus_pack_id": item.get("focus_pack_id"),
                "pack_sequence": item.get("pack_sequence"),
                "source_store": item.get("source_store"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "search_query": item.get("search_query"),
                "review_state": item.get("review_state"),
                "workflow": item.get("workflow"),
                "official_search_url": item.get("official_search_url"),
                "official_search_fetch_status": audit_item.get("fetch_status"),
                "official_search_http_status": audit_item.get("http_status"),
                "web_search_url": item.get("web_search_url"),
                "fallback_store_search_url": _legacy_store_search_url(item),
                "fallback_search_terms": _search_terms(item),
                "domain_limited_web_search_urls": _domain_limited_web_search_urls(item),
                "fallback_search_queries": _fallback_search_queries(item),
                "allowed_source_domains": item.get("allowed_source_domains") or [],
                "manual_review_checklist": item.get("manual_review_checklist") or [],
                "acceptance_rule": item.get("acceptance_rule"),
                "fallback_reason": "official_search_url_unavailable",
                "review_instruction": (
                    "Find an exact product/detail page through web search, archived store pages, or alternate official store entry points. "
                    "Only fill manual_confirmed_source_url when title, product type, and character/variant match."
                ),
                "source_patch_template": item.get("source_patch_template") or {},
                "catalog_field_import_template": item.get("catalog_field_import_template") or {},
                "auto_apply_enabled": False,
            }
        )

    by_status = Counter(str(item.get("official_search_http_status")) for item in queue_items)
    by_store = Counter(str(item.get("source_store") or "unknown") for item in queue_items)
    by_category = Counter(str(item.get("category") or "unknown") for item in queue_items)
    fallback_query_count = sum(len(item.get("fallback_search_queries") or []) for item in queue_items)
    domain_limited_web_search_url_count = sum(
        len(item.get("domain_limited_web_search_urls") or []) for item in queue_items
    )
    work_order = _fallback_work_order(queue_items)
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_next_focus_fallback_queue",
        "source_reports": [
            str(NEXT_PACK.relative_to(ROOT)).replace("\\", "/"),
            str(FETCH_AUDIT.relative_to(ROOT)).replace("\\", "/"),
        ],
        "summary": {
            "focus_pack_id": (next_pack.get("summary") or {}).get("focus_pack_id"),
            "queue_rows": len(queue_items),
            "manual_confirmed_rows": sum(1 for item in queue_items if item.get("manual_confirmed") is True),
            "fallback_reason": "official_search_url_unavailable" if queue_items else "none",
            "by_http_status": by_status.most_common(),
            "by_source_store": by_store.most_common(),
            "by_category": by_category.most_common(),
            "fallback_query_count": fallback_query_count,
            "domain_limited_web_search_url_count": domain_limited_web_search_url_count,
            "work_order_steps": len(work_order),
            "work_order_lanes": [step["lane"] for step in work_order],
            "first_domain_limited_web_search_url": (
                queue_items[0].get("domain_limited_web_search_urls", [""])[0]
                if queue_items and queue_items[0].get("domain_limited_web_search_urls")
                else ""
            ),
            "first_fallback_store_search_url": (
                queue_items[0].get("fallback_store_search_url", "") if queue_items else ""
            ),
            "auto_apply_enabled": False,
            "recommended_next_action": "review_fallback_queue_and_fill_exact_manual_confirmed_source_urls",
        },
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
            "dry_run_report": "data/source_discovery_next_focus_fallback_import_dry_run_public.json",
        },
        "work_order": work_order,
        "items": queue_items,
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(NEXT_PACK), load_json(FETCH_AUDIT))
    if args.write:
        write_report(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
