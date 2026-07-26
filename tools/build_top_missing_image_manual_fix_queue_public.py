from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_GOTOUCHI_QUEUE = DATA / "gotouchi_official_candidate_review_queue_public.json"
DEFAULT_ONLINE_KUJI_REPAIR = DATA / "chiikawa_online_kuji_public_image_repair_report.json"
DEFAULT_OUTPUT = DATA / "top_missing_image_manual_fix_queue_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise ValueError(f"{path} must contain a JSON list or an object with items")


def load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def missing_image_rows(rows: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    return [
        (index, row)
        for index, row in enumerate(rows)
        if not present(row.get("image_url")) or not present(row.get("local_image_path"))
    ]


def review_lane(row: dict[str, Any]) -> str:
    source_url = str(row.get("source_url") or "")
    source_store = str(row.get("source_store") or "")
    if source_url and source_url.rstrip("/") != "https://online-kuji.chiikawamarket.jp":
        return "open_existing_source_url"
    if "online" in source_url.lower() or "온라인" in source_store or "쿠지" in source_store:
        return "official_campaign_identity_review"
    if source_store:
        return "official_store_search"
    return "manual_web_search"


def quote_arg(value: Any) -> str:
    return '"' + str(value or "").replace('"', '\\"') + '"'


def manual_command(row: dict[str, Any]) -> str:
    catalog_index = row.get("catalog_index")
    name = row.get("name_ja") or row.get("name_ko") or ""
    return (
        "python -X utf8 tools\\apply_manual_catalog_image_update.py "
        f"{catalog_index} {quote_arg('IMAGE_URL')} "
        f"--source-url {quote_arg('SOURCE_URL')} "
        f"--expect-name {quote_arg(name)} "
        "--write"
    )


def _index_value(item: dict[str, Any]) -> int | None:
    value = item.get("catalog_index", item.get("row_index"))
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def build_candidate_context(
    *,
    gotouchi_queue: dict[str, Any] | None = None,
    online_kuji_repair: dict[str, Any] | None = None,
) -> dict[int, dict[str, Any]]:
    context: dict[int, dict[str, Any]] = {}
    for item in (gotouchi_queue or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        catalog_index = _index_value(item)
        if catalog_index is None:
            continue
        context[catalog_index] = {
            "candidate_context_source": "gotouchi_official_candidate_review_queue_public.json",
            "candidate_status": item.get("candidate_status"),
            "candidate_count": item.get("candidate_count"),
            "rejected_candidate_count": item.get("rejected_candidate_count"),
            "candidate_options": item.get("candidate_options") or [],
            "rejected_candidate_options": item.get("rejected_candidate_options") or [],
            "top_candidate": item.get("top_candidate") or {},
            "top_rejected_candidate": item.get("top_rejected_candidate") or {},
            "review_blockers": item.get("review_blockers") or [],
            "manual_confirmation_requirements": item.get("manual_confirmation_requirements") or [],
        }

    for item in (online_kuji_repair or {}).get("skipped") or []:
        if not isinstance(item, dict):
            continue
        catalog_index = _index_value(item)
        if catalog_index is None:
            continue
        context[catalog_index] = {
            **context.get(catalog_index, {}),
            "candidate_context_source": "chiikawa_online_kuji_public_image_repair_report.json",
            "candidate_status": "blocked",
            "review_blockers": [item.get("reason") or "manual_review_required"],
            "repair_candidate_count": item.get("candidate_count"),
            "repair_skip_reason": item.get("reason"),
        }
    return context


def build_queue(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    candidate_context: dict[int, dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    missing = missing_image_rows(rows)
    selected = missing[:limit]
    items: list[dict[str, Any]] = []
    for row_index, row in selected:
        catalog_index = row.get("catalog_index")
        extra = (
            candidate_context.get(catalog_index, {})
            if candidate_context and isinstance(catalog_index, int) and not isinstance(catalog_index, bool)
            else {}
        )
        checklist = [
            "Image URL opens as an actual image.",
            "Source URL is official or clearly identifies the exact product/campaign.",
            "Product name, prize rank, goods type, and variant match this row.",
            "Do not use storefront, search result, logo, banner, or unrelated sample images.",
            "Run cache/report/audit commands after applying confirmed rows.",
        ]
        manual_requirements = extra.get("manual_confirmation_requirements")
        if isinstance(manual_requirements, list):
            checklist.extend(str(item) for item in manual_requirements if item)
        items.append(
            {
                "manual_confirmed": False,
                "row_index": row_index,
                "catalog_index": catalog_index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "category": row.get("category"),
                "character_name": row.get("character_name"),
                "affiliation": row.get("affiliation"),
                "series_name": row.get("series_name"),
                "sub_series": row.get("sub_series"),
                "source_store": row.get("source_store"),
                "current_source_url": row.get("source_url"),
                "review_lane": review_lane(row),
                "manual_image_url": "",
                "manual_source_url": row.get("source_url") or "",
                "manual_note": "",
                "safe_apply_command": manual_command(row),
                "confirmation_checklist": list(dict.fromkeys(checklist)),
                **extra,
            }
        )

    by_store = Counter(str(row.get("source_store") or "") for _, row in selected)
    by_lane = Counter(item["review_lane"] for item in items)
    with_context_rows = sum(1 for item in items if item.get("candidate_context_source"))
    with_candidate_options = sum(1 for item in items if item.get("candidate_options"))
    with_rejected_candidate_options = sum(1 for item in items if item.get("rejected_candidate_options"))
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "top_missing_image_manual_fix_queue",
        "summary": {
            "catalog_rows": len(rows),
            "missing_image_rows": len(missing),
            "queue_rows": len(items),
            "limit": limit,
            "manual_confirmed_rows": 0,
            "candidate_context_rows": with_context_rows,
            "candidate_option_rows": with_candidate_options,
            "rejected_candidate_option_rows": with_rejected_candidate_options,
            "by_source_store": [[key, value] for key, value in by_store.most_common(20) if key],
            "by_review_lane": [[key, value] for key, value in by_lane.most_common()],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Work from the top of items in order.",
            "Fill manual_image_url and manual_source_url only after exact visual identity review.",
            "Use safe_apply_command as the one-row apply command after replacing IMAGE_URL and SOURCE_URL.",
            "After applying rows, run update_public_catalog_reports.py and audit_public_catalog_image_assets.py.",
        ],
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--gotouchi-queue", type=Path, default=DEFAULT_GOTOUCHI_QUEUE)
    parser.add_argument("--online-kuji-repair", type=Path, default=DEFAULT_ONLINE_KUJI_REPAIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_queue(
        load_rows(args.catalog),
        limit=args.limit,
        candidate_context=build_candidate_context(
            gotouchi_queue=load_report(args.gotouchi_queue),
            online_kuji_repair=load_report(args.online_kuji_repair),
        ),
    )
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
