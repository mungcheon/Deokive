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
DEFAULT_INPUT = ROOT / "data" / "source_discovery_next_focus_fallback_queue_public.json"
DEFAULT_OUTPUT = ROOT / "server" / "source_discovery_next_focus_fallback_confirmed_rows.template.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _template_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("review_table")
    if not isinstance(rows, list):
        rows = payload.get("items") or []

    items: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        catalog_index = row.get("catalog_index")
        if not isinstance(catalog_index, int) or isinstance(catalog_index, bool):
            continue
        if catalog_index in seen:
            continue
        seen.add(catalog_index)
        items.append(
            {
                "catalog_index": catalog_index,
                "field": "source_url",
                "manual_confirmed": False,
                "manual_confirmed_source_url": "",
                "manual_confirmed_image_url": "",
                "manual_evidence_url": row.get("first_domain_limited_web_search_url") or "",
                "manual_note": "",
                "source_store": row.get("source_store"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "category": row.get("category"),
                "focus_pack_id": row.get("focus_pack_id"),
                "search_term": row.get("search_term"),
                "fallback_store_search_url": row.get("fallback_store_search_url") or "",
                "acceptance_criteria": row.get("acceptance_rule"),
                "blocked_until": "exact_product_detail_source_url_confirmed",
            }
        )
    return items


def build_template(payload: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items = _template_items(payload)
    by_store = Counter(str(item.get("source_store") or "") for item in items)
    by_category = Counter(str(item.get("category") or "") for item in items)
    focus_pack_ids = sorted({str(item.get("focus_pack_id") or "") for item in items if item.get("focus_pack_id")})
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "source_discovery_next_focus_fallback_confirmed_source_url_template",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "template_items": len(items),
            "manual_confirmed_true": 0,
            "focus_pack_ids": focus_pack_ids,
            "by_source_store": by_store.most_common(),
            "by_category": by_category.most_common(),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "This is the focused 17-row fallback source discovery template.",
            "Copy this file to server/source_discovery_confirmed_rows.json only after manual review.",
            "For each exact match, set manual_confirmed=true and fill manual_confirmed_source_url with the exact product/detail URL.",
            "Leave manual_confirmed_image_url empty unless the product image is verified on the exact confirmed source page.",
            "Run python -m tools.import_confirmed_source_discovery_rows --queue server/source_discovery_confirmed_rows.json before using --write.",
        ],
        "items": items,
        "automation_policy": {
            "auto_apply_enabled": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
            "confirmed_file": "server/source_discovery_confirmed_rows.json",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    template = build_template(_load_json(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    print(f"Template: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
