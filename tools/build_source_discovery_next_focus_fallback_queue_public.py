from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _store_search_url(item: dict[str, Any]) -> str:
    query = item.get("name_ja") or item.get("name_ko") or ""
    return str(item.get("official_search_url") or item.get("web_search_url") or "").replace("products/list.php", "sphone/products/list.php") if query else ""


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
                "official_search_url": item.get("official_search_url"),
                "official_search_fetch_status": audit_item.get("fetch_status"),
                "official_search_http_status": audit_item.get("http_status"),
                "web_search_url": item.get("web_search_url"),
                "fallback_store_search_url": _store_search_url(item),
                "allowed_source_domains": item.get("allowed_source_domains") or [],
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
            "auto_apply_enabled": False,
            "recommended_next_action": "review_fallback_queue_and_fill_exact_manual_confirmed_source_urls",
        },
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
