from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "catalog_reused_image_deduplication_review_public.json"
DEFAULT_OUTPUT = DATA / "catalog_reused_image_deduplication_confirmed_template_public.json"
DEFAULT_MARKDOWN = DATA / "catalog_reused_image_deduplication_confirmed_template_public.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _catalog_indexes(rows: list[dict[str, Any]]) -> list[int]:
    indexes: list[int] = []
    for row in rows:
        catalog_index = row.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            indexes.append(catalog_index)
    return indexes


def _top_row_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko") or "",
        "name_ja": row.get("name_ja") or "",
        "series_name": row.get("series_name") or "",
        "sub_series": row.get("sub_series") or "",
        "category": row.get("category") or "",
        "character_name": row.get("character_name") or "",
        "image_url": row.get("image_url") or "",
        "source_url": row.get("source_url") or "",
    }


def _template_item(item: dict[str, Any], review_order: int) -> dict[str, Any]:
    rows = [row for row in item.get("rows") or [] if isinstance(row, dict)]
    decision_template = dict(item.get("decision_template") or {})
    suggested_keep = decision_template.get("suggested_keep_catalog_index")
    suggested_drops = decision_template.get("suggested_drop_catalog_indexes") or []
    source_urls = [url for url in item.get("source_urls") or [] if isinstance(url, str)]
    image_urls = [url for url in item.get("image_urls") or [] if isinstance(url, str)]
    review_urls = [*source_urls, *image_urls]

    return {
        "review_order": review_order,
        "group_index": item.get("group_index"),
        "confidence": item.get("confidence") or "",
        "reason": item.get("reason") or "",
        "primary_review_url": source_urls[0] if source_urls else (image_urls[0] if image_urls else ""),
        "source_urls": source_urls,
        "image_urls": image_urls,
        "source_url_same": item.get("source_url_same") is True,
        "image_same": item.get("image_same") is True,
        "category_same": item.get("category_same") is True,
        "character_same": item.get("character_same") is True,
        "rank_same": item.get("rank_same") is True,
        "review_urls": review_urls,
        "same_flags": {
            "source_url_same": item.get("source_url_same") is True,
            "image_same": item.get("image_same") is True,
            "category_same": item.get("category_same") is True,
            "character_same": item.get("character_same") is True,
            "rank_same": item.get("rank_same") is True,
        },
        "suggested_keep_catalog_index": suggested_keep,
        "suggested_drop_catalog_indexes": suggested_drops,
        "manual_keep_catalog_index": None,
        "manual_drop_catalog_indexes": [],
        "manual_confirmed": False,
        "decision": "",
        "allowed_decisions": decision_template.get("allowed_decisions")
        or [
            "same_sellable_product_keep_one",
            "campaign_or_variant_keep_separate",
            "wrong_shared_image_clear_or_replace",
            "needs_more_evidence",
        ],
        "manual_note": "",
        "required_checks": decision_template.get("required_checks")
        or [
            "Confirm both rows point to the same official campaign URL.",
            "Confirm prize rank and item/variant name are the same sellable product.",
            "Keep separate if either row is a reissue, channel variant, or different campaign wave.",
            "Do not delete until manual_confirmed is true.",
        ],
        "keep_candidate": next((row for row in rows if row.get("catalog_index") == suggested_keep), rows[0] if rows else {}),
        "drop_candidates": [
            row for row in rows if row.get("catalog_index") in set(suggested_drops)
        ],
        "catalog_indexes": _catalog_indexes(rows),
        "rows": [_top_row_summary(row) for row in rows],
        "decision_template": {
            **decision_template,
            "manual_confirmed": False,
            "decision": "",
            "manual_keep_catalog_index": None,
            "manual_drop_catalog_indexes": [],
            "manual_note": "",
        },
        "auto_delete_enabled": False,
        "auto_merge_enabled": False,
    }


def build_template(review: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    by_reason: Counter[str] = Counter()
    by_confidence: Counter[str] = Counter()

    for index, item in enumerate(review.get("items") or [], start=1):
        if not isinstance(item, dict):
            continue
        template_item = _template_item(item, index)
        items.append(template_item)
        by_reason[str(template_item.get("reason") or "")] += 1
        by_confidence[str(template_item.get("confidence") or "")] += 1

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_reused_image_deduplication_confirmed_template",
        "summary": {
            "template_groups": len(items),
            "strong_candidate_groups": sum(
                1 for item in items if item.get("confidence") == "strong_manual_duplicate_candidate"
            ),
            "manual_confirmed_groups": 0,
            "ready_groups": 0,
            "drop_candidate_rows": sum(len(item.get("suggested_drop_catalog_indexes") or []) for item in items),
            "primary_review_url_groups": sum(1 for item in items if item.get("primary_review_url")),
            "by_reason": [[key, value] for key, value in by_reason.most_common(20) if key],
            "by_confidence": [[key, value] for key, value in by_confidence.most_common(20) if key],
            "auto_delete_enabled": False,
            "auto_merge_enabled": False,
        },
        "instructions": [
            "Start from review_order 1 and open primary_review_url plus image URLs before editing decisions.",
            "If the rows are the same sellable product, set decision_template.manual_confirmed=true and decision_template.decision=same_sellable_product_keep_one.",
            "Use manual_keep_catalog_index and manual_drop_catalog_indexes only when the suggested keep/drop is wrong.",
            "Leave manual_confirmed=false for reissues, different prize variants, shared lineup photos, or uncertain items.",
            "Run tools/import_confirmed_reused_image_deduplication_rows.py without --write first to preview removals.",
        ],
        "items": items,
        "automation_policy": {
            "auto_delete": False,
            "auto_merge": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_reused_image_deduplication_rows.py",
            "private_collection_storage": "local_device_only",
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Reused Image Dedupe Confirmation Template",
        "",
        "Manual confirmation is required. This report never deletes catalog rows by itself.",
        "",
        f"- Template groups: {report.get('summary', {}).get('template_groups', 0)}",
        f"- Strong candidate groups: {report.get('summary', {}).get('strong_candidate_groups', 0)}",
        f"- Manual confirmed groups: {report.get('summary', {}).get('manual_confirmed_groups', 0)}",
        "",
        "## Top Review Items",
        "",
    ]
    for item in report.get("items", [])[:20]:
        rows = item.get("rows") or []
        row_names = "; ".join(
            f"{row.get('catalog_index')}: {row.get('name_ko') or row.get('name_ja') or ''}"
            for row in rows
        )
        lines.extend(
            [
                f"### {item.get('review_order')}. Group {item.get('group_index')}",
                "",
                f"- Primary review URL: {item.get('primary_review_url') or ''}",
                f"- Suggested keep: {item.get('suggested_keep_catalog_index')}",
                f"- Suggested drops: {item.get('suggested_drop_catalog_indexes') or []}",
                f"- Rows: {row_names}",
                "",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_template(load_json(args.input))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_markdown(report, args.markdown)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
