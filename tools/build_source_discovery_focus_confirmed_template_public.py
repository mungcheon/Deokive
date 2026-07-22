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
    return {
        "manual_review_status": "not_started",
        "manual_confirmed_source_url": "",
        "manual_confirmed_image_url": "",
        "manual_note": "",
        "focus_pack_id": pack.get("focus_pack_id"),
        "source_store": item.get("source_store") or pack.get("source_store"),
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "official_search_url": item.get("official_search_url"),
        "web_search_url": item.get("web_search_url"),
        "allowed_source_domains": item.get("allowed_source_domains") or [],
        "acceptance_rule": item.get("acceptance_rule"),
        "source_patch_template": item.get("source_patch_template") or {},
        "catalog_field_import_template": item.get("catalog_field_import_template") or {},
        "auto_apply_enabled": False,
    }


def build_template(focus_packs: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    by_pack: Counter[str] = Counter()
    by_store: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    for pack in focus_packs.get("packs") or []:
        if not isinstance(pack, dict):
            continue
        pack_id = str(pack.get("focus_pack_id") or "")
        for item in pack.get("items") or []:
            if not isinstance(item, dict):
                continue
            row = template_item(pack, item)
            items.append(row)
            by_pack[pack_id] += 1
            by_store[str(row.get("source_store") or "")] += 1
            by_category[str(row.get("category") or "")] += 1

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_focus_confirmed_template",
        "summary": {
            "template_items": len(items),
            "manual_confirmed_rows": 0,
            "focus_pack_count": len([key for key in by_pack if key]),
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
            "Run tools/import_confirmed_source_discovery_rows.py as a dry run before using --write.",
        ],
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
