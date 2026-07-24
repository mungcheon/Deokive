from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from enrich_catalog_images import _preferred_query_for_row


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
    query_row = dict(item)
    field_template = item.get("catalog_field_import_template")
    if isinstance(field_template, dict):
        for key in ("affiliation", "category", "name_ko", "name_ja", "source_store"):
            if not query_row.get(key) and field_template.get(key):
                query_row[key] = field_template.get(key)
    preferred = _preferred_query_for_row(query_row).strip()
    if preferred:
        terms.append(preferred)
    for key in ("name_ja", "name_ko"):
        value = str(item.get(key) or "").strip()
        if value and value not in terms:
            terms.append(value)
    return terms


def _legacy_store_search_url(item: dict[str, Any]) -> str:
    terms = _search_terms(item)
    if not terms:
        return ""
    raw = str(item.get("official_search_url") or item.get("web_search_url") or "")
    if "animate-onlineshop.jp" in raw:
        return (
            "https://www.animate-onlineshop.jp/sphone/products/list.php"
            f"?mode=search&smt={quote_plus(terms[0])}"
        )
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


def _first_value(values: list[Any] | None) -> str:
    if not values:
        return ""
    first = values[0]
    return first if isinstance(first, str) else ""


def _has_variant_marker(value: Any) -> bool:
    text = str(value or "")
    return any(marker in text for marker in ("(", ")", "（", "）", "①", "②", "③", "④", "⑤"))


def _identity_review(item: dict[str, Any]) -> dict[str, Any]:
    search_term = _first_value(item.get("fallback_search_terms"))
    blockers: list[str] = []
    if not str(item.get("name_ja") or "").strip():
        blockers.append("missing_name_ja")
    if not any(
        _has_variant_marker(value)
        for value in (item.get("name_ko"), item.get("name_ja"), search_term)
    ):
        blockers.append("variant_or_character_not_explicit")

    requires_variant_disambiguation = "variant_or_character_not_explicit" in blockers
    return {
        "identity_review_status": (
            "variant_disambiguation_required"
            if requires_variant_disambiguation
            else "exact_page_match_review_ready"
        ),
        "identity_blockers": blockers,
        "requires_metadata_backfill": "missing_name_ja" in blockers,
        "requires_variant_disambiguation": requires_variant_disambiguation,
        "can_confirm_source_url_after_page_match": not requires_variant_disambiguation,
    }


def _review_table(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for priority, item in enumerate(queue_items, start=1):
        field_template = item.get("catalog_field_import_template")
        if not isinstance(field_template, dict):
            field_template = {}
        identity_review = _identity_review(item)
        first_domain_url = _first_value(item.get("domain_limited_web_search_urls"))
        fallback_store_url = item.get("fallback_store_search_url") or ""
        primary_review_url = first_domain_url or fallback_store_url
        rows.append(
            {
                "review_priority": priority,
                "catalog_index": item.get("catalog_index"),
                "focus_pack_id": item.get("focus_pack_id"),
                "source_store": item.get("source_store"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "search_term": _first_value(item.get("fallback_search_terms")),
                "primary_review_url": primary_review_url,
                "primary_review_url_kind": (
                    "domain_limited_web_search"
                    if first_domain_url
                    else "legacy_mobile_store_search"
                    if fallback_store_url
                    else "missing_review_url"
                ),
                "first_domain_limited_web_search_url": first_domain_url,
                "fallback_store_search_url": fallback_store_url,
                "manual_confirmed": False,
                "manual_confirmed_source_url": "",
                "manual_confirmed_image_url": "",
                "manual_evidence_url": "",
                "manual_note": "",
                "import_field": field_template.get("field") or "source_url",
                "blocked_until": "exact_product_detail_source_url_confirmed",
                "acceptance_rule": item.get("acceptance_rule"),
                **identity_review,
            }
        )
    return rows


def _manual_entry_template(queue_items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "focused_template_file": "server/source_discovery_next_focus_fallback_confirmed_rows.template.json",
        "target_file": "server/source_discovery_confirmed_rows.json",
        "copy_from": "review_table",
        "required_fields": [
            "catalog_index",
            "manual_confirmed",
            "manual_confirmed_source_url",
            "manual_evidence_url",
        ],
        "optional_fields_after_source_verification": [
            "manual_confirmed_image_url",
            "manual_note",
        ],
        "ready_condition": (
            "manual_confirmed=true and manual_confirmed_source_url is an exact product detail URL "
            "on an allowed source domain; manual_confirmed_image_url may be filled only after the "
            "product image is verified on that exact page."
        ),
        "dry_run_command": (
            "python -m tools.import_confirmed_source_discovery_rows "
            "--queue server/source_discovery_confirmed_rows.json"
        ),
        "import_command": (
            "python -m tools.import_confirmed_source_discovery_rows "
            "--queue server/source_discovery_confirmed_rows.json --write"
        ),
        "row_count": len(queue_items),
    }


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
        first_domain_url = _first_value(queue_items[-1].get("domain_limited_web_search_urls"))
        fallback_store_url = queue_items[-1].get("fallback_store_search_url") or ""
        queue_items[-1]["primary_review_url"] = first_domain_url or fallback_store_url
        queue_items[-1]["primary_review_url_kind"] = (
            "domain_limited_web_search"
            if first_domain_url
            else "legacy_mobile_store_search"
            if fallback_store_url
            else "missing_review_url"
        )

    by_status = Counter(str(item.get("official_search_http_status")) for item in queue_items)
    by_store = Counter(str(item.get("source_store") or "unknown") for item in queue_items)
    by_category = Counter(str(item.get("category") or "unknown") for item in queue_items)
    fallback_query_count = sum(len(item.get("fallback_search_queries") or []) for item in queue_items)
    domain_limited_web_search_url_count = sum(
        len(item.get("domain_limited_web_search_urls") or []) for item in queue_items
    )
    work_order = _fallback_work_order(queue_items)
    review_table = _review_table(queue_items)
    identity_status = Counter(str(item.get("identity_review_status") or "unknown") for item in review_table)
    metadata_backfill_rows = sum(1 for item in review_table if item.get("requires_metadata_backfill"))
    variant_disambiguation_rows = sum(
        1 for item in review_table if item.get("requires_variant_disambiguation")
    )
    source_confirmation_ready_rows = sum(
        1 for item in review_table if item.get("can_confirm_source_url_after_page_match")
    )
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
            "review_table_rows": len(review_table),
            "manual_entry_template_rows": len(queue_items),
            "source_confirmation_ready_rows": source_confirmation_ready_rows,
            "metadata_backfill_required_rows": metadata_backfill_rows,
            "variant_disambiguation_required_rows": variant_disambiguation_rows,
            "by_identity_review_status": identity_status.most_common(),
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
            "first_primary_review_url": (
                queue_items[0].get("primary_review_url", "") if queue_items else ""
            ),
            "first_primary_review_url_kind": (
                queue_items[0].get("primary_review_url_kind", "") if queue_items else ""
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
        "manual_entry_template": _manual_entry_template(queue_items),
        "work_order": work_order,
        "review_table": review_table,
        "items": queue_items,
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        existing_text = path.read_text(encoding="utf-8-sig")
        if existing_text == serialized:
            return
        try:
            existing_report = json.loads(existing_text)
        except json.JSONDecodeError:
            existing_report = None
        if isinstance(existing_report, dict):
            existing_without_generated_at = {
                key: value for key, value in existing_report.items() if key != "generated_at"
            }
            report_without_generated_at = {
                key: value for key, value in report.items() if key != "generated_at"
            }
            if existing_without_generated_at == report_without_generated_at:
                return
    path.write_text(serialized, encoding="utf-8")


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
