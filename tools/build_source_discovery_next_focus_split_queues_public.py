from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    return {
        "queue_rows": len(items),
        "manual_confirmed_rows": sum(1 for item in items if item.get("manual_confirmed") is True),
        "by_source_store": by_store.most_common(),
        "by_category": by_category.most_common(),
        "by_identity_review_status": by_status.most_common(),
        "auto_apply_enabled": False,
    }


def _exact_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "focus_pack_id": row.get("focus_pack_id"),
        "source_store": row.get("source_store"),
        "category": row.get("category"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "search_term": row.get("search_term"),
        "first_domain_limited_web_search_url": row.get("first_domain_limited_web_search_url"),
        "fallback_store_search_url": row.get("fallback_store_search_url"),
        "manual_confirmed": False,
        "manual_confirmed_source_url": "",
        "manual_confirmed_image_url": "",
        "manual_evidence_url": "",
        "manual_note": "",
        "next_action": "open_search_url_confirm_exact_product_detail_page_then_fill_manual_confirmed_source_url",
        "acceptance_rule": row.get("acceptance_rule"),
        "identity_review_status": row.get("identity_review_status"),
        "identity_blockers": row.get("identity_blockers") or [],
        "auto_apply_enabled": False,
    }


def _identity_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "focus_pack_id": row.get("focus_pack_id"),
        "source_store": row.get("source_store"),
        "category": row.get("category"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "search_term": row.get("search_term"),
        "first_domain_limited_web_search_url": row.get("first_domain_limited_web_search_url"),
        "fallback_store_search_url": row.get("fallback_store_search_url"),
        "manual_confirmed": False,
        "manual_confirmed_name_ja": "",
        "manual_confirmed_variant_or_character": "",
        "manual_evidence_url": "",
        "manual_note": "",
        "next_action": "identify_exact_variant_or_character_before_source_url_confirmation",
        "identity_review_status": row.get("identity_review_status"),
        "identity_blockers": row.get("identity_blockers") or [],
        "requires_metadata_backfill": row.get("requires_metadata_backfill") is True,
        "requires_variant_disambiguation": row.get("requires_variant_disambiguation") is True,
        "auto_apply_enabled": False,
    }


def build_reports(payload: dict[str, Any], *, generated_at: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    generated_at = generated_at or _now_utc()
    rows = [row for row in payload.get("review_table") or [] if isinstance(row, dict)]
    exact_items = [_exact_item(row) for row in rows if row.get("can_confirm_source_url_after_page_match") is True]
    identity_items = [_identity_item(row) for row in rows if row.get("requires_variant_disambiguation") is True]

    exact_report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "source_discovery_next_focus_exact_url_review_queue",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            **_base_summary(exact_items),
            "blocked_identity_rows": len(identity_items),
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
