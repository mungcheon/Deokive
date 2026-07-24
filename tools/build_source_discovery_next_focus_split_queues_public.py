from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_next_focus_fallback_queue_public.json"
EXACT_URL_QUEUE = DATA / "source_discovery_next_focus_exact_url_review_queue_public.json"
IDENTITY_BACKFILL_QUEUE = DATA / "source_discovery_next_focus_identity_backfill_queue_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _base_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_store = Counter(str(item.get("source_store") or "") for item in items)
    by_category = Counter(str(item.get("category") or "") for item in items)
    by_status = Counter(str(item.get("identity_review_status") or "unknown") for item in items)
    by_review_url_kind = Counter(
        str(item.get("primary_review_url_kind") or "")
        for item in items
        if str(item.get("primary_review_url") or "")
    )
    return {
        "queue_rows": len(items),
        "manual_confirmed_rows": sum(1 for item in items if item.get("manual_confirmed") is True),
        "by_source_store": by_store.most_common(),
        "by_category": by_category.most_common(),
        "by_identity_review_status": by_status.most_common(),
        "primary_review_url_rows": sum(1 for item in items if str(item.get("primary_review_url") or "")),
        "primary_review_url_kind_counts": by_review_url_kind.most_common(),
        "first_primary_review_url": next(
            (str(item.get("primary_review_url") or "") for item in items if str(item.get("primary_review_url") or "")),
            "",
        ),
        "first_primary_review_url_kind": next(
            (
                str(item.get("primary_review_url_kind") or "")
                for item in items
                if str(item.get("primary_review_url") or "")
            ),
            "",
        ),
        "auto_apply_enabled": False,
    }


def _primary_review_url(row: dict[str, Any]) -> tuple[Any, str]:
    if row.get("primary_review_url"):
        return row.get("primary_review_url"), str(row.get("primary_review_url_kind") or "review_url")
    if row.get("first_domain_limited_web_search_url"):
        return row.get("first_domain_limited_web_search_url"), "domain_limited_web_search"
    if row.get("fallback_store_search_url"):
        return row.get("fallback_store_search_url"), "fallback_store_search"
    return "", ""


def _absolute_candidate_url(url: Any, row: dict[str, Any]) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    domains = (
        (row.get("source_url_review_guidance") or {}).get("allowed_source_domains")
        or row.get("allowed_source_domains")
        or []
    )
    domain = str(domains[0] if domains else "").strip()
    if raw.startswith("/") and not domain:
        for key in ("fallback_store_search_url", "primary_review_url", "first_domain_limited_web_search_url"):
            netloc = urlsplit(str(row.get(key) or "")).netloc
            if netloc and "google." not in netloc:
                domain = netloc
                break
    if raw.startswith("/") and domain:
        return f"https://{domain}{raw}"
    return raw


def _candidate_detail_links(row: dict[str, Any], fetch_audit_by_index: dict[int, dict[str, Any]]) -> list[str]:
    try:
        catalog_index = int(row.get("catalog_index"))
    except (TypeError, ValueError):
        return []
    audit_item = fetch_audit_by_index.get(catalog_index) or {}
    links: list[str] = []
    for link in audit_item.get("sample_product_detail_links") or []:
        absolute = _absolute_candidate_url(link, row)
        if absolute and absolute not in links:
            links.append(absolute)
    return links


def _candidate_detail_link_review_fields(
    row: dict[str, Any],
    fetch_audit_by_index: dict[int, dict[str, Any]],
    candidate_detail_links: list[str],
) -> dict[str, str]:
    if not candidate_detail_links:
        return {
            "candidate_detail_link_source": "",
            "candidate_detail_link_review_status": "",
            "candidate_detail_link_warning": "",
        }
    try:
        catalog_index = int(row.get("catalog_index"))
    except (TypeError, ValueError):
        audit_item: dict[str, Any] = {}
    else:
        audit_item = fetch_audit_by_index.get(catalog_index) or {}
    if audit_item.get("broad_result_page") is True:
        return {
            "candidate_detail_link_source": "official_search_result_sample_links",
            "candidate_detail_link_review_status": "broad_search_sample_requires_identity_check",
            "candidate_detail_link_warning": (
                "These links are sampled from a broad official search result and may not match this catalog row; "
                "use only as review starting points."
            ),
        }
    return {
        "candidate_detail_link_source": "fetch_audit_sample_product_detail_links",
        "candidate_detail_link_review_status": "candidate_detail_links_require_manual_identity_check",
        "candidate_detail_link_warning": (
            "These candidate links require manual identity confirmation before copying to source_url or image_url."
        ),
    }


def _exact_item(row: dict[str, Any], fetch_audit_by_index: dict[int, dict[str, Any]]) -> dict[str, Any]:
    primary_review_url, primary_review_url_kind = _primary_review_url(row)
    candidate_detail_links = _candidate_detail_links(row, fetch_audit_by_index)
    candidate_review_fields = _candidate_detail_link_review_fields(
        row,
        fetch_audit_by_index,
        candidate_detail_links,
    )
    return {
        "catalog_index": row.get("catalog_index"),
        "focus_pack_id": row.get("focus_pack_id"),
        "source_store": row.get("source_store"),
        "category": row.get("category"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "search_term": row.get("search_term"),
        "primary_review_url": primary_review_url,
        "primary_review_url_kind": primary_review_url_kind,
        "candidate_detail_links": candidate_detail_links,
        "candidate_detail_link_count": len(candidate_detail_links),
        "first_candidate_detail_link": candidate_detail_links[0] if candidate_detail_links else "",
        **candidate_review_fields,
        "first_domain_limited_web_search_url": row.get("first_domain_limited_web_search_url"),
        "fallback_store_search_url": row.get("fallback_store_search_url"),
        "manual_confirmed": False,
        "manual_confirmed_source_url": "",
        "manual_confirmed_image_url": "",
        "manual_evidence_url": "",
        "manual_note": "",
        "next_action": "open_search_url_confirm_exact_product_detail_page_then_fill_manual_confirmed_source_url",
        "acceptance_rule": row.get("acceptance_rule"),
        "source_url_review_guidance": row.get("source_url_review_guidance") or {},
        "identity_review_status": row.get("identity_review_status"),
        "identity_blockers": row.get("identity_blockers") or [],
        "auto_apply_enabled": False,
    }


def _identity_item(row: dict[str, Any]) -> dict[str, Any]:
    primary_review_url, primary_review_url_kind = _primary_review_url(row)
    return {
        "catalog_index": row.get("catalog_index"),
        "focus_pack_id": row.get("focus_pack_id"),
        "source_store": row.get("source_store"),
        "category": row.get("category"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "search_term": row.get("search_term"),
        "primary_review_url": primary_review_url,
        "primary_review_url_kind": primary_review_url_kind,
        "first_domain_limited_web_search_url": row.get("first_domain_limited_web_search_url"),
        "fallback_store_search_url": row.get("fallback_store_search_url"),
        "manual_confirmed": False,
        "manual_confirmed_name_ja": "",
        "manual_confirmed_variant_or_character": "",
        "manual_evidence_url": "",
        "manual_note": "",
        "next_action": "identify_exact_variant_or_character_before_source_url_confirmation",
        "source_url_review_guidance": row.get("source_url_review_guidance") or {},
        "identity_review_status": row.get("identity_review_status"),
        "identity_blockers": row.get("identity_blockers") or [],
        "requires_metadata_backfill": row.get("requires_metadata_backfill") is True,
        "requires_variant_disambiguation": row.get("requires_variant_disambiguation") is True,
        "auto_apply_enabled": False,
    }


def build_reports(
    payload: dict[str, Any],
    *,
    fetch_audit: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    generated_at = generated_at or _now_utc()
    rows = [row for row in payload.get("review_table") or [] if isinstance(row, dict)]
    fetch_audit_by_index: dict[int, dict[str, Any]] = {}
    for item in (fetch_audit or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        try:
            fetch_audit_by_index[int(item.get("catalog_index"))] = item
        except (TypeError, ValueError):
            continue
    exact_items = [
        _exact_item(row, fetch_audit_by_index)
        for row in rows
        if row.get("can_confirm_source_url_after_page_match") is True
    ]
    identity_items = [_identity_item(row) for row in rows if row.get("requires_variant_disambiguation") is True]

    exact_report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "source_discovery_next_focus_exact_url_review_queue",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            **_base_summary(exact_items),
            "blocked_identity_rows": len(identity_items),
            "candidate_detail_link_rows": sum(
                1 for item in exact_items if item.get("candidate_detail_links")
            ),
            "candidate_detail_links": sum(
                int(item.get("candidate_detail_link_count") or 0) for item in exact_items
            ),
            "candidate_detail_link_source_counts": Counter(
                str(item.get("candidate_detail_link_source") or "")
                for item in exact_items
                if item.get("candidate_detail_links")
            ).most_common(),
            "candidate_detail_link_review_status_counts": Counter(
                str(item.get("candidate_detail_link_review_status") or "")
                for item in exact_items
                if item.get("candidate_detail_links")
            ).most_common(),
            "candidate_detail_link_warning_rows": sum(
                1 for item in exact_items if str(item.get("candidate_detail_link_warning") or "")
            ),
            "broad_candidate_detail_link_rows": sum(
                1
                for item in exact_items
                if item.get("candidate_detail_link_review_status")
                == "broad_search_sample_requires_identity_check"
            ),
            "recommended_next_action": "confirm exact product detail source URLs for these rows before image attachment",
        },
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
        },
        "items": exact_items,
    }
    identity_report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "source_discovery_next_focus_identity_backfill_queue",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            **_base_summary(identity_items),
            "exact_url_review_ready_rows": len(exact_items),
            "metadata_backfill_required_rows": sum(
                1 for item in identity_items if item.get("requires_metadata_backfill")
            ),
            "variant_disambiguation_required_rows": sum(
                1 for item in identity_items if item.get("requires_variant_disambiguation")
            ),
            "recommended_next_action": "fill exact variant or character identity before source URL confirmation",
        },
        "automation_policy": {
            "auto_apply_metadata": False,
            "auto_apply_source_url": False,
            "requires_manual_review": True,
        },
        "items": identity_items,
    }
    return exact_report, identity_report


def write_reports(exact_report: dict[str, Any], identity_report: dict[str, Any]) -> None:
    EXACT_URL_QUEUE.write_text(json.dumps(exact_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    IDENTITY_BACKFILL_QUEUE.write_text(
        json.dumps(identity_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    exact_report, identity_report = build_reports(_load_json(args.input))
    if args.write:
        write_reports(exact_report, identity_report)
    print(
        json.dumps(
            {
                "exact_url_review_rows": exact_report["summary"]["queue_rows"],
                "identity_backfill_rows": identity_report["summary"]["queue_rows"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
