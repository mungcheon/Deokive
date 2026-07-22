from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_focus_confirmed_template_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_next_focus_pack_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _is_confirmed(item: dict[str, Any]) -> bool:
    if item.get("manual_confirmed") is True:
        return True
    status = str(item.get("manual_review_status") or "").strip().lower()
    return status in {"source_confirmed", "source_and_image_confirmed", "confirmed"}


def _pack_progress(template: dict[str, Any]) -> dict[str, dict[str, int]]:
    progress: dict[str, dict[str, int]] = {}
    for item in template.get("items") or []:
        if not isinstance(item, dict):
            continue
        pack_id = str(item.get("focus_pack_id") or "")
        if not pack_id:
            continue
        stats = progress.setdefault(pack_id, {"items": 0, "confirmed": 0, "remaining": 0})
        stats["items"] += 1
        if _is_confirmed(item):
            stats["confirmed"] += 1
        else:
            stats["remaining"] += 1
    return progress


def _next_work_order(template: dict[str, Any]) -> dict[str, Any]:
    progress = _pack_progress(template)
    work_order = template.get("work_order")
    if isinstance(work_order, list):
        for row in work_order:
            if not isinstance(row, dict):
                continue
            pack_id = str(row.get("focus_pack_id") or "")
            stats = progress.get(pack_id, {})
            remaining = int(
                stats.get("remaining")
                if stats
                else row.get("remaining_review_rows") or 0
            )
            if row.get("review_status") != "completed" and remaining:
                enriched = dict(row)
                enriched["row_count"] = int(stats.get("items") or enriched.get("row_count") or 0)
                enriched["confirmed_source_rows"] = int(stats.get("confirmed") or 0)
                enriched["remaining_review_rows"] = remaining
                enriched["review_status"] = "in_progress" if stats.get("confirmed") else row.get("review_status")
                return enriched
    summary = template.get("summary") if isinstance(template.get("summary"), dict) else {}
    focus_pack_id = summary.get("next_focus_pack_id")
    stats = progress.get(str(focus_pack_id or ""), {})
    return {
        "priority": 1,
        "focus_pack_id": focus_pack_id,
        "source_store": summary.get("next_source_store"),
        "row_count": stats.get("items") or summary.get("next_focus_pack_rows") or 0,
        "review_status": "not_started" if focus_pack_id else "empty",
        "confirmed_source_rows": stats.get("confirmed") or 0,
        "remaining_review_rows": stats.get("remaining") or summary.get("next_focus_pack_rows") or 0,
        "target_category": summary.get("next_target_category"),
        "first_official_search_url": summary.get("next_official_search_url"),
    }


def _pack_queue_preview(template: dict[str, Any], focus_pack_id: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    progress = _pack_progress(template)
    rows: list[dict[str, Any]] = []
    work_order = template.get("work_order")
    if not isinstance(work_order, list):
        return rows

    for row in work_order:
        if not isinstance(row, dict):
            continue
        pack_id = str(row.get("focus_pack_id") or "")
        stats = progress.get(pack_id, {})
        remaining = int(
            stats.get("remaining")
            if stats
            else row.get("remaining_review_rows") or row.get("row_count") or 0
        )
        if row.get("review_status") == "completed" or remaining <= 0:
            continue
        rows.append(
            {
                "priority": row.get("priority"),
                "focus_pack_id": row.get("focus_pack_id"),
                "is_current_pack": pack_id == str(focus_pack_id or ""),
                "source_store": row.get("source_store"),
                "target_category": row.get("target_category"),
                "row_count": int(stats.get("items") or row.get("row_count") or 0),
                "confirmed_source_rows": int(stats.get("confirmed") or 0),
                "remaining_review_rows": remaining,
                "review_status": "in_progress" if stats.get("confirmed") else row.get("review_status"),
                "first_official_search_url": row.get("first_official_search_url"),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "manual_review_status": item.get("manual_review_status") or "not_started",
        "manual_confirmed_source_url": item.get("manual_confirmed_source_url") or "",
        "manual_confirmed_image_url": item.get("manual_confirmed_image_url") or "",
        "manual_note": item.get("manual_note") or "",
        "focus_pack_id": item.get("focus_pack_id"),
        "pack_sequence": item.get("pack_sequence"),
        "row_index": item.get("row_index"),
        "catalog_index": item.get("catalog_index"),
        "source_store": item.get("source_store"),
        "category": item.get("category"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "search_query": item.get("search_query"),
        "review_state": item.get("review_state"),
        "workflow": item.get("workflow"),
        "official_search_url": item.get("official_search_url"),
        "web_search_url": item.get("web_search_url"),
        "allowed_source_domains": item.get("allowed_source_domains") or [],
        "manual_review_checklist": item.get("manual_review_checklist") or [],
        "acceptance_rule": item.get("acceptance_rule"),
        "source_patch_template": item.get("source_patch_template") or {},
        "catalog_field_import_template": item.get("catalog_field_import_template") or {},
        "auto_apply_enabled": False,
    }


def build_report(template: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    next_pack = _next_work_order(template)
    focus_pack_id = next_pack.get("focus_pack_id")
    pack_queue_preview = _pack_queue_preview(template, focus_pack_id)
    items = [
        _compact_item(item)
        for item in template.get("items") or []
        if isinstance(item, dict) and item.get("focus_pack_id") == focus_pack_id
    ]
    official_search_urls = sorted({str(item.get("official_search_url")) for item in items if item.get("official_search_url")})
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_next_focus_pack",
        "summary": {
            "focus_pack_id": focus_pack_id,
            "pack_priority": next_pack.get("priority"),
            "source_store": next_pack.get("source_store"),
            "target_category": next_pack.get("target_category"),
            "pack_items": len(items),
            "confirmed_source_rows": next_pack.get("confirmed_source_rows") or 0,
            "remaining_review_rows": next_pack.get("remaining_review_rows") or len(items),
            "work_order_pack_count": (template.get("summary") or {}).get("work_order_pack_count", 0),
            "template_items": (template.get("summary") or {}).get("template_items", 0),
            "official_search_url_count": len(official_search_urls),
            "first_official_search_url": next_pack.get("first_official_search_url"),
            "pack_queue_preview_count": len(pack_queue_preview),
            "next_pack_after_current": (
                pack_queue_preview[1].get("focus_pack_id")
                if len(pack_queue_preview) > 1
                else None
            ),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this focused pack before opening the full 427-row source discovery template.",
            "Confirm exact product/detail URLs on allowed official domains only.",
            "Fill manual_confirmed_source_url and set manual_review_status only after product identity matches.",
            "Run tools/import_confirmed_source_discovery_rows.py as a dry run before any write.",
        ],
        "next_pack": next_pack,
        "pack_queue_preview": pack_queue_preview,
        "official_search_urls": official_search_urls,
        "items": items,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "source_template": "data/source_discovery_focus_confirmed_template_public.json",
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
