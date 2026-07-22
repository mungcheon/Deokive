from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_image_attachment_action_queue_public.json"
DEFAULT_CANDIDATES = DATA / "stellive_fanding_candidates_public.json"
DEFAULT_OUTPUT = DATA / "catalog_image_source_url_confirmed_template_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def candidate_lookup(candidate_report: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not isinstance(candidate_report, dict):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for row in candidate_report.get("queue") or []:
        if not isinstance(row, dict):
            continue
        row_index = row.get("row_index")
        if isinstance(row_index, int) and not isinstance(row_index, bool):
            out[row_index] = row
    return out


def _candidate_summary(candidate_row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(candidate_row, dict):
        return None
    top_candidates = candidate_row.get("top_candidates")
    top_candidates = top_candidates if isinstance(top_candidates, list) else []
    compact_candidates = []
    for candidate in top_candidates[:5]:
        if not isinstance(candidate, dict):
            continue
        compact_candidates.append(
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
    return {
        "candidate_status": candidate_row.get("candidate_status"),
        "candidate_count": len(top_candidates),
        "top_candidates": compact_candidates,
    }


def _template_item(
    batch: dict[str, Any],
    item: dict[str, Any],
    candidates_by_index: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    source_template = item.get("source_url_import_template")
    if not isinstance(source_template, dict):
        return None
    row_index = source_template.get("row_index", item.get("catalog_index"))
    candidate_summary = candidates_by_index.get(row_index) if isinstance(row_index, int) else None
    candidate_summary = _candidate_summary(candidate_summary)
    top_candidates = candidate_summary.get("top_candidates", []) if candidate_summary else []
    top_candidate = top_candidates[0] if top_candidates else {}
    return {
        **source_template,
        "manual_confirmed": False,
        "manual_value": "",
        "candidate_source_url": top_candidate.get("source_url") or "",
        "candidate_image_url": top_candidate.get("image_url") or "",
        "candidate_title": top_candidate.get("title") or "",
        "candidate_score": top_candidate.get("score"),
        "candidate_status": candidate_summary.get("candidate_status") if candidate_summary else None,
        "candidate_count": candidate_summary.get("candidate_count") if candidate_summary else 0,
        "candidate_options": top_candidates,
        "evidence_url": top_candidate.get("source_url") or "",
        "manual_note": "",
        "field": "source_url",
        "row_index": row_index,
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_store": item.get("source_store") or batch.get("source_store"),
        "current_source_url": item.get("source_url") or source_template.get("current_source_url"),
        "official_search_url": item.get("official_search_url"),
        "workflow": item.get("workflow") or batch.get("workflow"),
        "batch_id": batch.get("batch_id"),
        "required_before_image_import": item.get("required_before_image_import") or [],
        "blocked_until": "exact_product_source_url_confirmed",
        "next_after_confirmed_source_url": "extract_or_confirm_product_page_image_url",
        "auto_apply_enabled": False,
    }


def build_template(
    action_queue: dict[str, Any],
    candidate_report: dict[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    by_batch: Counter[str] = Counter()
    by_store: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_candidate_status: Counter[str] = Counter()
    candidates_by_index = candidate_lookup(candidate_report)

    for batch in action_queue.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        batch_id = str(batch.get("batch_id") or "")
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            row = _template_item(batch, item, candidates_by_index)
            if row is None:
                continue
            items.append(row)
            by_batch[batch_id] += 1
            by_store[str(row.get("source_store") or "")] += 1
            by_category[str(row.get("category") or "")] += 1
            by_candidate_status[str(row.get("candidate_status") or "no_candidate_report")] += 1

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_image_source_url_confirmed_template",
        "summary": {
            "template_items": len(items),
            "manual_confirmed_rows": 0,
            "batch_count": len([key for key in by_batch if key]),
            "by_batch": [[key, value] for key, value in by_batch.most_common(30) if key],
            "by_source_store": [[key, value] for key, value in by_store.most_common(20) if key],
            "by_category": [[key, value] for key, value in by_category.most_common(20) if key],
            "candidate_prefilled_rows": sum(1 for item in items if item.get("candidate_source_url")),
            "by_candidate_status": [
                [key, value] for key, value in by_candidate_status.most_common(20) if key
            ],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Copy this template before entering confirmed source_url evidence.",
            "Set manual_confirmed to true only after the exact product detail page is checked.",
            "Put the verified product detail URL in manual_value.",
            "Use evidence_url for the same official/detail page or a stronger supporting URL.",
            "candidate_source_url is only a review hint and must not be imported without manual_confirmed=true.",
            "After source_url is confirmed, use catalog_image_attachment_confirmed_template_public.json for image_url.",
            "Dry-run tools/import_confirmed_catalog_field_rows.py before any --write import.",
        ],
        "items": items,
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
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    template = build_template(
        load_json(args.input),
        load_json(args.candidates) if args.candidates.exists() else None,
    )
    if args.write:
        args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
