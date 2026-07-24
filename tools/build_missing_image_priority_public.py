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
STARTER_QUEUE_REPORT = DATA / "source_discovery_starter_queue_public.json"


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


def image_reuse_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return identity_key(row)


def reusable_image_candidates(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_public.json must contain an items list")

    image_rows_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    missing_rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = image_reuse_key(item)
        if not all(key):
            continue
        if has_display_image(item):
            image_rows_by_key[key].append(item)
        else:
            missing_rows.append(item)

    candidates: list[dict[str, Any]] = []
    for item in missing_rows:
        matches = image_rows_by_key.get(image_reuse_key(item), [])
        local_paths = sorted(
            {
                str(match.get("local_image_path") or "").strip()
                for match in matches
                if present(match.get("local_image_path"))
            }
        )
        image_urls = sorted(
            {
                str(match.get("image_url") or "").strip()
                for match in matches
                if present(match.get("image_url"))
            }
        )
        if len(local_paths) != 1 or not image_urls:
            continue
        candidates.append(
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation"),
                "category": item.get("category"),
                "matched_catalog_indices": [
                    match.get("catalog_index") for match in matches[:10]
                ],
                "candidate_image_url": image_urls[0],
                "candidate_local_image_path": local_paths[0],
                "candidate_match_rows": len(matches),
                "review_required": True,
            }
        )
    return candidates


def counter_rows(counter: Counter[str], field: str, limit: int = 40) -> list[dict[str, Any]]:
    return [{field: key, "rows": count} for key, count in counter.most_common(limit)]


def compact_starter_item(item: dict[str, Any], queue_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "source_store": item.get("source_store") or queue_row.get("source_store"),
        "affiliation": item.get("affiliation"),
        "category": item.get("category"),
        "priority": queue_row.get("priority"),
        "strategy": queue_row.get("strategy"),
        "search_query": queue_row.get("query") or item.get("name_ja") or item.get("name_ko"),
        "search_url": queue_row.get("search_url"),
        "required_evidence": [
            "exact_product_source_url",
            "title_character_variant_type_match",
            "product_image_visible_on_confirmed_source",
        ],
    }


def starter_queue_rows(groups: dict[tuple[str, str, str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups.values():
        primary_strategy = ""
        if group["strategy_rows"]:
            primary_strategy = group["strategy_rows"].most_common(1)[0][0]
        rows.append(
            {
                "source_store": group["source_store"],
                "affiliation": group["affiliation"],
                "category": group["category"],
                "primary_strategy": primary_strategy,
                "priority": group["priority"],
                "rows": group["rows"],
                "sample_items": group["sample_items"],
                "recommended_workflow": recommended_workflow(
                    group["source_store"],
                    group["rows"],
                ),
                "next_step": "open_search_urls_and_confirm_exact_product_source_pages",
                "blocked_until": "exact_source_url_and_image_url_confirmed",
                "auto_apply_enabled": False,
            }
        )
    rows.sort(
        key=lambda row: (
            int(row.get("priority") or 999),
            -int(row.get("rows") or 0),
            str(row.get("source_store") or ""),
            str(row.get("affiliation") or ""),
            str(row.get("category") or ""),
        )
    )
    return rows


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
    reuse_candidates = reusable_image_candidates(catalog)
    source_discovery_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}

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
            group_key = (source_store, affiliation, category, strategy)
            group = source_discovery_groups.setdefault(
                group_key,
                {
                    "source_store": source_store,
                    "affiliation": affiliation,
                    "category": category,
                    "priority": int((queue_row or {}).get("priority") or 999),
                    "rows": 0,
                    "strategy_rows": Counter(),
                    "sample_items": [],
                },
            )
            group["rows"] += 1
            group["priority"] = min(
                int(group["priority"]),
                int((queue_row or {}).get("priority") or 999),
            )
            group["strategy_rows"][strategy] += 1
            if len(group["sample_items"]) < 5:
                group["sample_items"].append(compact_starter_item(item, queue_row or {}))
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
    source_discovery_starter_queue = starter_queue_rows(source_discovery_groups)

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
            "safe_existing_image_reuse_candidate_rows": len(reuse_candidates),
            "source_discovery_starter_queue_groups": len(source_discovery_starter_queue),
            "source_discovery_starter_queue_rows": sum(
                int(row.get("rows") or 0) for row in source_discovery_starter_queue
            ),
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
        "source_discovery_starter_queue": source_discovery_starter_queue[:30],
        "_source_discovery_starter_queue_full": source_discovery_starter_queue,
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
        "existing_image_reuse_candidates": reuse_candidates[:50],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_allowed_or_reviewed_source": True,
        },
    }


def build_starter_queue_report(
    missing_image_priority_report: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    summary = missing_image_priority_report.get("summary", {})
    groups_source = (
        missing_image_priority_report.get("_source_discovery_starter_queue_full")
        or missing_image_priority_report.get("source_discovery_starter_queue", [])
    )
    groups = [
        group
        for group in groups_source
        if isinstance(group, dict)
    ]
    rows = sum(int(group.get("rows") or 0) for group in groups)
    sample_items = sum(
        len(group.get("sample_items") or [])
        for group in groups
        if isinstance(group.get("sample_items"), list)
    )
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_starter_queue",
        "source_report": f"data/{REPORT.name}",
        "summary": {
            "starter_queue_groups": len(groups),
            "starter_queue_rows": rows,
            "sample_item_rows": sample_items,
            "missing_source_url_rows": int(summary.get("missing_source_url_rows") or 0),
            "coverage_matches_missing_source_url_rows": rows
            == int(summary.get("missing_source_url_rows") or 0),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue for missing-image rows that do not yet have exact source_url evidence.",
            "Open the provided search_url values and confirm the exact product/detail page before importing any source_url or image_url.",
            "Do not use representative or similar images unless a later manual review report explicitly allows that row.",
        ],
        "groups": groups,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_exact_product_source_url": True,
            "requires_product_image_visible_on_confirmed_source": True,
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
    payload = dict(report)
    payload.pop("_source_discovery_starter_queue_full", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
