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
DEFAULT_SOURCE_URL_TEMPLATE = DATA / "catalog_image_source_url_confirmed_template_public.json"
DEFAULT_OUTPUT = DATA / "catalog_image_attachment_confirmed_template_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def source_url_hint_lookup(source_url_template: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not isinstance(source_url_template, dict):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for row in source_url_template.get("items") or []:
        if not isinstance(row, dict):
            continue
        for key in ("row_index", "catalog_index"):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                out.setdefault(value, row)
    return out


def _source_hint_for(
    item: dict[str, Any],
    template: dict[str, Any],
    hints_by_index: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    for key in (template.get("row_index"), item.get("catalog_index")):
        if isinstance(key, int) and not isinstance(key, bool) and key in hints_by_index:
            return hints_by_index[key]
    return None


def _template_item(
    batch: dict[str, Any],
    item: dict[str, Any],
    hints_by_index: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = dict(template) if isinstance(template, dict) else {}
    source_hint = _source_hint_for(item, template, hints_by_index)
    source_url = item.get("source_url") or template.get("candidate_source_url") or template.get("evidence_url")
    candidate_source_url = str(source_hint.get("candidate_source_url") or "") if source_hint else ""
    candidate_image_url = str(source_hint.get("candidate_image_url") or "") if source_hint else ""
    candidate_title = str(source_hint.get("candidate_title") or "") if source_hint else ""
    source_url_review_lane = str(source_hint.get("source_url_review_lane") or "") if source_hint else ""
    blockers = source_hint.get("source_url_review_blockers") if source_hint else []
    source_url_review_blockers = blockers if isinstance(blockers, list) else []
    return {
        **template,
        "manual_confirmed": False,
        "manual_value": "",
        "candidate_source_url": candidate_source_url,
        "candidate_image_url": candidate_image_url,
        "candidate_title": candidate_title,
        "source_url_review_lane": source_url_review_lane,
        "source_url_review_blockers": source_url_review_blockers,
        "evidence_url": candidate_source_url,
        "manual_note": "",
        "field": "image_url",
        "row_index": template.get("row_index", item.get("catalog_index")),
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_store": item.get("source_store") or batch.get("source_store"),
        "current_source_url": source_url,
        "official_search_url": item.get("official_search_url"),
        "workflow": item.get("workflow") or batch.get("workflow"),
        "batch_id": batch.get("batch_id"),
        "required_before_image_import": item.get("required_before_image_import") or [],
        "source_url_update_required": bool(item.get("source_url_update_required")),
        "representative_image": bool(item.get("representative_image_review_required")),
        "representative_image_review_required": bool(item.get("representative_image_review_required")),
        "image_url_ready": bool(item.get("image_url_ready")),
        "blocked_until": "manual_confirmed_image_url",
        "auto_apply_enabled": False,
    }


def build_template(
    action_queue: dict[str, Any],
    source_url_template: dict[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    by_batch: Counter[str] = Counter()
    by_workflow: Counter[str] = Counter()
    by_store: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_source_url_review_lane: Counter[str] = Counter()
    hints_by_index = source_url_hint_lookup(source_url_template)

    for batch in action_queue.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        batch_id = str(batch.get("batch_id") or "")
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            row = _template_item(batch, item, hints_by_index)
            items.append(row)
            by_batch[batch_id] += 1
            by_workflow[str(row.get("workflow") or "")] += 1
            by_store[str(row.get("source_store") or "")] += 1
            by_category[str(row.get("category") or "")] += 1
            by_source_url_review_lane[str(row.get("source_url_review_lane") or "")] += 1

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_image_attachment_confirmed_template",
        "summary": {
            "template_items": len(items),
            "manual_confirmed_rows": 0,
            "source_url_update_required_rows": sum(1 for item in items if item.get("source_url_update_required")),
            "representative_image_review_required_rows": sum(
                1 for item in items if item.get("representative_image_review_required")
            ),
            "image_url_ready_rows": sum(1 for item in items if item.get("image_url_ready")),
            "source_url_candidate_prefilled_rows": sum(
                1 for item in items if item.get("candidate_source_url") or item.get("candidate_image_url")
            ),
            "batch_count": len([key for key in by_batch if key]),
            "by_batch": [[key, value] for key, value in by_batch.most_common(30) if key],
            "by_workflow": [[key, value] for key, value in by_workflow.most_common(20) if key],
            "by_source_store": [[key, value] for key, value in by_store.most_common(20) if key],
            "by_category": [[key, value] for key, value in by_category.most_common(20) if key],
            "by_source_url_review_lane": [
                [key, value] for key, value in by_source_url_review_lane.most_common(20) if key
            ],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Copy this template before entering confirmed image evidence.",
            "Set manual_confirmed to true only after exact product image evidence is checked.",
            "Put the verified image URL in manual_value.",
            "Put the exact product/detail page in candidate_source_url or evidence_url.",
            "Rows with candidate_image_url are still blocked until candidate_source_url is exact-product confirmed.",
            "For representative images, keep representative_image true only when the product type match is acceptable.",
            "Dry-run tools/import_confirmed_image_attachment_rows.py before any --write import.",
        ],
        "items": items,
        "automation_policy": {
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_image_attachment_rows.py",
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--source-url-template", type=Path, default=DEFAULT_SOURCE_URL_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    template = build_template(
        load_json(args.input),
        load_json(args.source_url_template) if args.source_url_template.exists() else None,
    )
    if args.write:
        args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
