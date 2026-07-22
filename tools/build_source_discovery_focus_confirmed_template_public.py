from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_focus_packs_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_focus_confirmed_template_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def template_item(pack: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    row_index = item.get("row_index") or item.get("catalog_index")
    return {
        "manual_review_status": "not_started",
        "manual_confirmed_source_url": "",
        "manual_confirmed_image_url": "",
        "manual_note": "",
        "focus_pack_id": pack.get("focus_pack_id"),
        "pack_sequence": pack.get("pack_sequence"),
        "pack_review_status": pack.get("review_status"),
        "target_category": pack.get("target_category"),
        "source_store_total_rows": pack.get("source_store_total_rows"),
        "source_store_remaining_after_pack": pack.get("source_store_remaining_after_pack"),
        "first_official_search_url": pack.get("first_official_search_url"),
        "row_index": row_index,
        "source_store": item.get("source_store") or pack.get("source_store"),
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
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


def compact_work_order(pack: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {
        "priority": pack.get("pack_sequence") or sequence,
        "focus_pack_id": pack.get("focus_pack_id"),
        "source_store": pack.get("source_store"),
        "row_count": pack.get("row_count"),
        "review_status": pack.get("review_status"),
        "remaining_review_rows": pack.get("remaining_review_rows"),
        "target_category": pack.get("target_category"),
        "first_batch_id": (pack.get("batch_ids") or [None])[0],
        "first_official_search_url": pack.get("first_official_search_url"),
        "allowed_source_domains": pack.get("allowed_source_domains") or [],
        "source_store_remaining_after_pack": pack.get("source_store_remaining_after_pack"),
    }


def build_template(focus_packs: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    work_order: list[dict[str, Any]] = []
    by_pack: Counter[str] = Counter()
    by_store: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    for sequence, pack in enumerate(focus_packs.get("packs") or [], start=1):
        if not isinstance(pack, dict):
            continue
        work_order.append(compact_work_order(pack, sequence))
        pack_id = str(pack.get("focus_pack_id") or "")
        for item in pack.get("items") or []:
            if not isinstance(item, dict):
                continue
            row = template_item(pack, item)
            items.append(row)
            by_pack[pack_id] += 1
            by_store[str(row.get("source_store") or "")] += 1
            by_category[str(row.get("category") or "")] += 1

    next_pack = next((pack for pack in work_order if pack.get("review_status") != "completed"), None)
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_focus_confirmed_template",
        "summary": {
            "template_items": len(items),
            "manual_confirmed_rows": 0,
            "focus_pack_count": len([key for key in by_pack if key]),
            "work_order_pack_count": len(work_order),
            "next_focus_pack_id": next_pack.get("focus_pack_id") if next_pack else None,
            "next_source_store": next_pack.get("source_store") if next_pack else None,
            "next_target_category": next_pack.get("target_category") if next_pack else None,
            "next_focus_pack_rows": next_pack.get("row_count") if next_pack else 0,
            "next_official_search_url": next_pack.get("first_official_search_url") if next_pack else None,
            "by_focus_pack": [[key, value] for key, value in by_pack.most_common(30) if key],
            "by_source_store": [[key, value] for key, value in by_store.most_common(20) if key],
            "by_category": [[key, value] for key, value in by_category.most_common(20) if key],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Copy this template before entering reviewed source URLs.",
            "For exact product matches, set manual_review_status to source_confirmed or source_and_image_confirmed.",
            "Put the exact product/detail page in manual_confirmed_source_url.",
            "Only set manual_confirmed_image_url when the product image is verified from the accepted source.",
            "Review work_order from top to bottom; it points at the next focused store/category pack.",
            "Run tools/import_confirmed_source_discovery_rows.py as a dry run before using --write.",
        ],
        "work_order": work_order,
        "items": items,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    template = build_template(load_json(args.input))
    if args.write:
        args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
