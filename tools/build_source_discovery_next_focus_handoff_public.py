from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_FOCUS_PACK = DATA / "source_discovery_next_focus_pack_public.json"
DEFAULT_FALLBACK_QUEUE = DATA / "source_discovery_next_focus_fallback_queue_public.json"
DEFAULT_DETAIL_CANDIDATES = DATA / "source_discovery_next_focus_detail_candidates_public.json"
DEFAULT_LIVE_PROBE = DATA / "source_discovery_next_focus_live_source_probe_public.json"
DEFAULT_VARIANT_BACKFILL = DATA / "source_discovery_next_focus_variant_metadata_backfill_public.json"
DEFAULT_JSON_OUTPUT = DATA / "source_discovery_next_focus_handoff_public.json"
DEFAULT_MD_OUTPUT = DATA / "source_discovery_next_focus_handoff_public.md"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary")
    return value if isinstance(value, dict) else {}


def _fallback_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload.get("items", []) if isinstance(row, dict)]


def _domain_searches(row: dict[str, Any], limit: int = 3) -> list[str]:
    urls = row.get("domain_limited_web_search_urls")
    if not isinstance(urls, list):
        return []
    return [str(url) for url in urls[:limit] if str(url).strip()]


def _compact_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "source_store": row.get("source_store"),
        "affiliation": row.get("affiliation"),
        "category": row.get("category"),
        "manual_review_status": row.get("manual_review_status"),
        "identity_review_status": row.get("identity_review_status"),
        "fallback_store_search_url": row.get("fallback_store_search_url"),
        "domain_limited_web_search_urls": _domain_searches(row),
        "manual_confirmed_source_url": row.get("manual_confirmed_source_url"),
        "manual_confirmed_image_url": row.get("manual_confirmed_image_url"),
        "required_decision": "confirm_exact_detail_url_or_leave_blank",
        "required_evidence": [
            "exact product/detail URL on allowed official domain",
            "not a search/category page",
            "title matches series, character, product type, and variant",
            "image on page matches the catalog row before image import",
        ],
    }


def build_handoff(
    *,
    focus_pack: dict[str, Any],
    fallback_queue: dict[str, Any],
    detail_candidates: dict[str, Any],
    live_probe: dict[str, Any],
    variant_backfill: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    focus_summary = _summary(focus_pack)
    fallback_summary = _summary(fallback_queue)
    detail_summary = _summary(detail_candidates)
    live_summary = _summary(live_probe)
    variant_summary = _summary(variant_backfill)
    items = [_compact_item(row) for row in _fallback_items(fallback_queue)]
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "source_discovery_next_focus_handoff",
        "summary": {
            "recommended_active_focus_pack_id": focus_summary.get("recommended_active_focus_pack_id")
            or fallback_summary.get("focus_pack_id"),
            "source_store": focus_summary.get("source_store"),
            "target_category": focus_summary.get("target_category"),
            "pack_items": fallback_summary.get("queue_rows") or len(items),
            "source_discovery_remaining_rows": focus_summary.get("focus_pack_progress_remaining_rows"),
            "fallback_queue_rows": fallback_summary.get("queue_rows"),
            "fallback_query_count": fallback_summary.get("fallback_query_count"),
            "detail_candidate_rows": detail_summary.get("candidate_rows"),
            "exact_candidate_review_rows": detail_summary.get("exact_candidate_review_rows"),
            "live_probe_detail_candidate_rows": live_summary.get("detail_candidate_rows"),
            "variant_metadata_backfill_rows": variant_summary.get("queue_rows"),
            "auto_apply_ready_rows": 0,
            "completion_readiness_status": detail_summary.get("completion_readiness_status")
            or focus_summary.get("current_focus_resolution_status"),
            "recommended_next_action": fallback_summary.get("recommended_next_action"),
        },
        "work_order": [
            {
                "step": 1,
                "lane": "domain_limited_exact_title_search",
                "action": "Open the domain-limited search URLs and find an exact Ensky detail page.",
            },
            {
                "step": 2,
                "lane": "detail_identity_confirmation",
                "action": "Confirm title, character, product type, and variant before importing a source or image URL.",
            },
            {
                "step": 3,
                "lane": "manual_confirmed_rows_import",
                "action": "Fill manual_confirmed_source_url and manual_confirmed_image_url only for exact matches.",
            },
        ],
        "items": items,
        "automation_policy": {
            "auto_apply_enabled": False,
            "reason": "The next focus pack has no safe exact matches; official or domain-limited search results require identity review.",
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# Source Discovery Next Focus Handoff",
        "",
        f"- Focus pack: `{summary.get('recommended_active_focus_pack_id')}`",
        f"- Store/category: `{summary.get('source_store')}` / `{summary.get('target_category')}`",
        f"- Pack items: `{summary.get('pack_items')}`",
        f"- Remaining source-discovery rows: `{summary.get('source_discovery_remaining_rows')}`",
        f"- Auto-apply ready rows: `{summary.get('auto_apply_ready_rows')}`",
        f"- Status: `{summary.get('completion_readiness_status')}`",
        "",
        "## Work Order",
        "",
    ]
    for row in report["work_order"]:
        lines.append(f"{row['step']}. `{row['lane']}` - {row['action']}")
    lines.extend(["", "## Items", ""])
    for item in report["items"]:
        searches = item.get("domain_limited_web_search_urls") or []
        first_search = searches[0] if searches else item.get("fallback_store_search_url") or ""
        lines.append(
            f"- `{item.get('catalog_index')}` {item.get('name_ko')} / {item.get('name_ja')} "
            f"({item.get('affiliation')}, {item.get('category')})"
        )
        if first_search:
            lines.append(f"  - Review: {first_search}")
        lines.append("  - Decision: confirm exact detail URL or leave blank")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--focus-pack", type=Path, default=DEFAULT_FOCUS_PACK)
    parser.add_argument("--fallback-queue", type=Path, default=DEFAULT_FALLBACK_QUEUE)
    parser.add_argument("--detail-candidates", type=Path, default=DEFAULT_DETAIL_CANDIDATES)
    parser.add_argument("--live-probe", type=Path, default=DEFAULT_LIVE_PROBE)
    parser.add_argument("--variant-backfill", type=Path, default=DEFAULT_VARIANT_BACKFILL)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_handoff(
        focus_pack=_load(args.focus_pack),
        fallback_queue=_load(args.fallback_queue),
        detail_candidates=_load(args.detail_candidates),
        live_probe=_load(args.live_probe),
        variant_backfill=_load(args.variant_backfill),
    )
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.markdown_output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {args.json_output}")
    print(f"Markdown: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
