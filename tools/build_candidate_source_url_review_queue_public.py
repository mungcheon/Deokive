from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_image_source_url_confirmed_template_public.json"
DEFAULT_OUTPUT = DATA / "catalog_candidate_source_url_review_queue_public.json"
REVIEW_LANES = {"low_confidence_candidate_review", "weak_candidate_review"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(_compact_text(row.get(key)) for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _manual_import_template(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_index": row.get("row_index"),
        "catalog_index": row.get("catalog_index"),
        "field": "source_url",
        "manual_confirmed": False,
        "manual_value": "",
        "evidence_url": "",
        "current_source_url": row.get("current_source_url"),
        "candidate_source_url": "",
        "manual_note": "",
    }


def _candidate_options(row: dict[str, Any]) -> list[dict[str, Any]]:
    options = row.get("candidate_options")
    if not isinstance(options, list):
        return []
    out: list[dict[str, Any]] = []
    for candidate in options[:8]:
        if not isinstance(candidate, dict):
            continue
        out.append(
            {
                "product_no": candidate.get("product_no"),
                "title": candidate.get("title"),
                "source_url": candidate.get("source_url"),
                "image_url": candidate.get("image_url"),
                "release_date": candidate.get("release_date"),
                "score": candidate.get("score"),
                "shared_tokens": candidate.get("shared_tokens") or [],
                "query_overlap": candidate.get("query_overlap"),
                "title_overlap": candidate.get("title_overlap"),
            }
        )
    return out


def _queue_item(row: dict[str, Any]) -> dict[str, Any]:
    hints = row.get("store_search_hints")
    hints = hints if isinstance(hints, dict) else {}
    candidates = _candidate_options(row)
    top = candidates[0] if candidates else {}
    return {
        "row_index": row.get("row_index"),
        "catalog_index": row.get("catalog_index"),
        "source_store": row.get("source_store"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "series_name": row.get("series_name"),
        "category": row.get("category"),
        "current_source_url": row.get("current_source_url"),
        "source_url_review_lane": row.get("source_url_review_lane"),
        "candidate_status": row.get("candidate_status"),
        "candidate_score": row.get("candidate_score"),
        "candidate_count": len(candidates),
        "top_candidate": top,
        "candidate_options": candidates,
        "match_diagnostics": row.get("match_diagnostics") or {},
        "storefront_url": hints.get("storefront_url") or "",
        "store_search_url": hints.get("store_search_url") or "",
        "site_query": hints.get("site_query") or "",
        "fallback_search_queries": row.get("fallback_search_queries") or [],
        "source_url_import_template": _manual_import_template(row),
        "review_blockers": row.get("source_url_review_blockers") or [],
        "manual_confirmation_requirements": row.get("manual_confirmation_requirements") or [],
        "next_after_confirmed_source_url": row.get("next_after_confirmed_source_url")
        or "extract_or_confirm_product_page_image_url",
        "batch_id": row.get("batch_id"),
        "auto_apply_enabled": False,
    }


def _build_lane_workstreams(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_lane.setdefault(_compact_text(item.get("source_url_review_lane")) or "unknown", []).append(item)

    workstreams: list[dict[str, Any]] = []
    for lane, rows in by_lane.items():
        rows = sorted(rows, key=lambda row: (float(row.get("candidate_score") or 0), int(row.get("catalog_index") or 0)))
        workstreams.append(
            {
                "source_url_review_lane": lane,
                "row_count": len(rows),
                "by_source_store": _counter_pairs(rows, "source_store"),
                "by_category": _counter_pairs(rows, "category"),
                "candidate_rows": sum(1 for row in rows if row.get("candidate_options")),
                "rows": rows,
                "recommended_review_order": [
                    "Open top_candidate.source_url and compare it against the catalog row.",
                    "Reject related products, wrong release years, wrong variants, bundles, or generic items.",
                    "If none of the candidates is exact, use store_search_url or fallback_search_queries.",
                    "Only exact product/detail pages may be copied into source_url_import_template.manual_value.",
                    "Set manual_confirmed=true only after source URL identity is proven.",
                ],
                "next_machine_step_after_review": "import_confirmed_source_urls_then_extract_images",
                "auto_apply_enabled": False,
            }
        )
    workstreams.sort(key=lambda row: (-int(row["row_count"]), str(row["source_url_review_lane"])))
    return workstreams


def build_queue(template: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    rows = [
        _queue_item(row)
        for row in template.get("items") or []
        if isinstance(row, dict) and row.get("source_url_review_lane") in REVIEW_LANES
    ]
    rows.sort(key=lambda row: (str(row.get("source_url_review_lane") or ""), int(row.get("catalog_index") or 0)))
    workstreams = _build_lane_workstreams(rows)

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_candidate_source_url_review_queue",
        "summary": {
            "candidate_review_rows": len(rows),
            "workstream_count": len(workstreams),
            "by_source_url_review_lane": _counter_pairs(rows, "source_url_review_lane"),
            "by_candidate_status": _counter_pairs(rows, "candidate_status"),
            "by_source_store": _counter_pairs(rows, "source_store"),
            "by_category": _counter_pairs(rows, "category"),
            "with_candidate_options": sum(1 for row in rows if row.get("candidate_options")),
            "with_store_search_url": sum(1 for row in rows if row.get("store_search_url")),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "This queue covers low-confidence and weak candidate source URLs.",
            "Candidate URLs are review hints only, not import evidence.",
            "Leave manual_value blank when no candidate is an exact product/detail page.",
            "Dry-run tools/import_confirmed_catalog_field_rows.py after manual confirmations.",
            "Then rebuild image attachment queues to extract or confirm image_url.",
        ],
        "workstreams": workstreams,
        "items": rows,
        "automation_policy": {
            "auto_apply_source_url": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_catalog_field_rows.py",
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_queue(load_json(args.input))
    if args.write:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
