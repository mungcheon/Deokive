from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_QUEUE = DATA / "source_discovery_next_focus_variant_metadata_backfill_public.json"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_next_focus_variant_metadata_confirmed_rows.template.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    raise SystemExit("catalog must be a JSON list or an object with items")


def _display_path(path: Path) -> str:
    try:
        path = path.relative_to(ROOT)
    except ValueError:
        pass
    return path.as_posix()


def _catalog_by_index(catalog_payload: Any) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in _catalog_rows(catalog_payload):
        catalog_index = row.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            out[catalog_index] = row
    return out


def _first_candidate_url(item: dict[str, Any]) -> str:
    for candidate in item.get("candidate_samples") or []:
        if isinstance(candidate, dict) and candidate.get("source_url"):
            return str(candidate["source_url"])
    return ""


def _template_for_item(item: dict[str, Any], catalog_row: dict[str, Any] | None) -> dict[str, Any]:
    catalog_index = item.get("catalog_index")
    row = catalog_row or {}
    recommended_fields = [
        str(field)
        for field in item.get("recommended_metadata_fields") or []
        if str(field).strip()
    ]
    candidate_samples = [
        candidate
        for candidate in item.get("candidate_samples") or []
        if isinstance(candidate, dict)
    ][:5]
    return {
        "catalog_index": catalog_index,
        "current": {
            "name_ko": row.get("name_ko") or item.get("name_ko"),
            "name_ja": row.get("name_ja") or item.get("name_ja"),
            "category": row.get("category") or item.get("category"),
            "sub_series": row.get("sub_series") or item.get("sub_series"),
            "character_name": row.get("character_name") or item.get("character_name"),
            "affiliation": row.get("affiliation") or item.get("affiliation"),
            "source_store": row.get("source_store") or item.get("source_store"),
        },
        "review": {
            "variant_risk_flags": item.get("variant_risk_flags") or [],
            "recommended_metadata_fields": recommended_fields,
            "review_url": item.get("review_url") or "",
            "candidate_samples": candidate_samples,
        },
        "metadata_backfill_template": {
            "catalog_index": catalog_index,
            "manual_confirmed": False,
            "manual_confirmed_name_ja": "",
            "manual_confirmed_name_ko": "",
            "manual_confirmed_sub_series": "",
            "manual_confirmed_category": "",
            "manual_evidence_url": _first_candidate_url(item),
            "manual_note": "Fill only exact variant metadata after checking candidate_samples.",
        },
    }


def build_template(queue_payload: Any, catalog_payload: Any, *, generated_at: str | None = None) -> dict[str, Any]:
    catalog = _catalog_by_index(catalog_payload)
    items = [
        item
        for item in (queue_payload.get("items") if isinstance(queue_payload, dict) else [])
        if isinstance(item, dict)
    ]
    template_items = [
        _template_for_item(item, catalog.get(item.get("catalog_index")))
        for item in items
    ]
    missing_catalog_rows = [
        item.get("catalog_index")
        for item in items
        if item.get("catalog_index") not in catalog
    ]
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "source_discovery_next_focus_variant_metadata_confirmed_rows_template",
        "source_reports": [_display_path(DEFAULT_QUEUE), _display_path(DEFAULT_CATALOG)],
        "instructions": [
            "Copy this file to a confirmed rows file or edit the template entries after manual source review.",
            "Set manual_confirmed to true only when manual_evidence_url is an exact product page for this variant.",
            "Fill only fields that are proven by the evidence page; leave other manual_confirmed_* fields blank.",
            "Run tools/import_confirmed_variant_metadata_backfill_rows.py and review the dry-run report before --write.",
        ],
        "summary": {
            "template_rows": len(template_items),
            "missing_catalog_rows": len(missing_catalog_rows),
            "missing_catalog_indexes": missing_catalog_rows[:50],
        },
        "items": template_items,
    }


def write_template(template: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    template = build_template(_load_json(args.queue), _load_json(args.catalog))
    if args.write:
        write_template(template, args.output)
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to save the confirmed rows template.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
