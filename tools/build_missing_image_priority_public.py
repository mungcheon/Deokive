from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
WORK_QUEUE = DATA / "catalog_missing_image_work_queue_public.json"
REPORT = DATA / "catalog_missing_image_priority_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def has_display_image(item: dict[str, Any]) -> bool:
    return present(item.get("local_image_path")) or present(item.get("image_url"))


def catalog_missing_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict) and not has_display_image(item)]


def queue_by_catalog_index(queue: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = queue.get("items")
    if not isinstance(rows, list):
        raise ValueError("catalog_missing_image_work_queue_public.json must contain an items list")
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_index = row.get("row_index")
        if isinstance(row_index, int):
            result[row_index] = row
    return result


def identity_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("name_ko") or "").strip(),
        str(row.get("source_store") or "").strip(),
        str(row.get("affiliation") or "").strip(),
        str(row.get("category") or "").strip(),
    )


def queue_by_identity(queue: dict[str, Any]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    rows = queue.get("items")
    if not isinstance(rows, list):
        raise ValueError("catalog_missing_image_work_queue_public.json must contain an items list")
    result: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            result.setdefault(identity_key(row), row)
    return result


def counter_rows(counter: Counter[str], field: str, limit: int = 40) -> list[dict[str, Any]]:
    return [{field: key, "rows": count} for key, count in counter.most_common(limit)]


def source_url_state(item: dict[str, Any], queue_row: dict[str, Any] | None) -> str:
    if not present(item.get("source_url")):
        return "missing_source_url"
    if (queue_row or {}).get("source_url_is_generic"):
        return "generic_source_url"
    if (queue_row or {}).get("source_url_is_product_detail"):
        return "product_detail_source_url"
    return "unclassified_source_url"


def build_report(
    catalog: dict[str, Any],
    queue: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    missing_rows = catalog_missing_rows(catalog)
    queue_lookup = queue_by_catalog_index(queue)
    queue_identity_lookup = queue_by_identity(queue)

    by_source_store: Counter[str] = Counter()
    by_affiliation: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_strategy: Counter[str] = Counter()
    by_automation_safety: Counter[str] = Counter()
    by_source_url_state: Counter[str] = Counter()
    source_affiliation: dict[tuple[str, str], int] = defaultdict(int)

    queue_matched_rows = 0
    missing_source_url_rows = 0
    generic_source_url_rows = 0
    product_source_url_rows = 0
    high_priority_rows = []
    stale_index_matches = []
    unmatched_catalog_rows = []

    for item in missing_rows:
        catalog_index = item.get("catalog_index")
        queue_row = queue_lookup.get(catalog_index) if isinstance(catalog_index, int) else None
        if not queue_row:
            identity_match = queue_identity_lookup.get(identity_key(item))
            if identity_match:
                queue_row = identity_match
                stale_index_matches.append((item, identity_match))
            else:
                unmatched_catalog_rows.append(item)
        if queue_row:
            queue_matched_rows += 1
        source_store_value = item.get("source_store")
        if not present(source_store_value) and queue_row:
            source_store_value = queue_row.get("source_store")
        source_store = str(source_store_value or "unknown")
        affiliation = str(item.get("affiliation") or "unknown")
        category = str(item.get("category") or "unknown")
        strategy = str((queue_row or {}).get("strategy") or "manual_review")
        automation_safety = str((queue_row or {}).get("automation_safety") or "not_in_work_queue")

        by_source_store[source_store] += 1
        by_affiliation[affiliation] += 1
        by_category[category] += 1
        by_strategy[strategy] += 1
        by_automation_safety[automation_safety] += 1
        state = source_url_state(item, queue_row)
        by_source_url_state[state] += 1
        source_affiliation[(source_store, affiliation)] += 1

        if state == "missing_source_url":
            missing_source_url_rows += 1
        elif state == "generic_source_url":
            generic_source_url_rows += 1
        elif state == "product_detail_source_url":
            product_source_url_rows += 1

        priority = int((queue_row or {}).get("priority") or 999)
        if priority <= 20:
            high_priority_rows.append((priority, item, queue_row or {}))

    focus_groups = [
        {
            "source_store": source_store,
            "affiliation": affiliation,
            "rows": rows,
            "recommended_workflow": recommended_workflow(source_store, rows),
        }
        for (source_store, affiliation), rows in sorted(
            source_affiliation.items(), key=lambda pair: (-pair[1], pair[0][0], pair[0][1])
        )
    ][:30]

    high_priority_rows.sort(key=lambda row: (row[0], row[1].get("catalog_index") or 0))

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "public_catalog_missing_image_priority",
        "summary": {
            "missing_image_rows": len(missing_rows),
            "work_queue_rows": len(queue_lookup),
            "queue_matched_rows": queue_matched_rows,
            "stale_queue_index_matches": len(stale_index_matches),
            "unmatched_catalog_missing_rows": len(unmatched_catalog_rows),
            "missing_source_url_rows": missing_source_url_rows,
            "generic_source_url_rows": generic_source_url_rows,
            "product_source_url_rows": product_source_url_rows,
            "high_priority_rows": len(high_priority_rows),
            "auto_apply_enabled": False,
        },
        "breakdowns": {
            "by_source_store": counter_rows(by_source_store, "source_store"),
            "by_affiliation": counter_rows(by_affiliation, "affiliation"),
            "by_category": counter_rows(by_category, "category"),
            "by_strategy": counter_rows(by_strategy, "strategy"),
            "by_automation_safety": counter_rows(by_automation_safety, "automation_safety"),
            "by_source_url_state": counter_rows(by_source_url_state, "source_url_state"),
        },
        "next_action_queues": {
            "source_discovery_first": {
                "rows": missing_source_url_rows,
                "reason": "Attach exact product source URLs before image candidates can be trusted.",
            },
            "replace_generic_source_then_attach_image": {
                "rows": generic_source_url_rows,
                "reason": "Generic storefront URLs need exact product detail pages before image attachment.",
            },
            "image_attachment_ready": {
                "rows": product_source_url_rows,
                "reason": "Exact product source URLs are present; prioritize image extraction or manual image confirmation.",
            },
        },
        "focus_groups": focus_groups,
        "high_priority_samples": [
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation"),
                "category": item.get("category"),
                "priority": priority,
                "strategy": queue_row.get("strategy"),
                "search_url": queue_row.get("search_url"),
            }
            for priority, item, queue_row in high_priority_rows[:50]
        ],
        "stale_queue_index_samples": [
            {
                "catalog_index": item.get("catalog_index"),
                "queue_row_index": queue_row.get("row_index"),
                "name_ko": item.get("name_ko"),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation"),
            }
            for item, queue_row in stale_index_matches[:20]
        ],
        "unmatched_catalog_missing_samples": [
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation"),
                "category": item.get("category"),
            }
            for item in unmatched_catalog_rows[:20]
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_allowed_or_reviewed_source": True,
        },
    }


def recommended_workflow(source_store: str, rows: int) -> str:
    if source_store in {"FuRyu", "Taito", "Banpresto", "SEGA"}:
        return "official_prize_provider_search_then_exact_detail_match"
    if source_store in {"애니메이트", "엔스카이", "Movic", "코토부키야"}:
        return "official_storefront_search_then_exact_detail_match"
    if rows >= 20:
        return "batch_source_discovery_then_image_attachment_review"
    return "manual_exact_image_research"


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(CATALOG), load_json(WORK_QUEUE))
    if args.write:
        write_report(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
