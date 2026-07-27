from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue_current.json"
DEFAULT_FIELD_QUEUE = ROOT / "server" / "catalog_field_enrichment_queue_current.json"
DEFAULT_SOURCE_DISCOVERY = ROOT / "server" / "catalog_source_discovery_queue.json"
DEFAULT_QUALITY = ROOT / "server" / "catalog_quality_report.json"
DEFAULT_NAMING_QUEUE = ROOT / "server" / "catalog_naming_quality_queue.json"
DEFAULT_ICHIBAN_QUALITY_QUEUE = ROOT / "server" / "ichiban_public_quality_queue.json"
DEFAULT_IMAGE_PROVIDER_AUDIT = ROOT / "server" / "catalog_image_provider_coverage_audit.json"
DEFAULT_STALE_SOURCE_QUEUE = ROOT / "server" / "stale_source_cleanup_queue.json"
DEFAULT_PRIORITY_GOODS_QUEUE = ROOT / "server" / "priority_goods_queue_current.json"
DEFAULT_JSON = ROOT / "server" / "catalog_update_backlog.json"
DEFAULT_MD = ROOT / "server" / "catalog_update_backlog.md"


def _counter_rows(counter: Counter[tuple[str, ...]], keys: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for values, count in counter.most_common(limit):
        row = {key: value for key, value in zip(keys, values)}
        row["count"] = count
        rows.append(row)
    return rows


def _sample_field_items(items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for item in items[:limit]:
        samples.append(
            {
                "field": item.get("field"),
                "source_store": item.get("source_store"),
                "category": item.get("category"),
                "affiliation": item.get("affiliation"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "search_url": item.get("search_url"),
                "acceptance_criteria": item.get("acceptance_criteria"),
            }
        )
    return samples


def _sample_image_items(items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for item in items[:limit]:
        samples.append(
            {
                "row_index": item.get("row_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "category": item.get("category"),
                "query": item.get("query"),
                "search_url": item.get("search_url"),
                "source_url": item.get("source_url"),
            }
        )
    return samples


def _field_focus_packs(field_items: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in field_items:
        key = str(item.get("batch_key") or "")
        if not key:
            key = "|".join(
                [
                    str(item.get("source_group") or ""),
                    str(item.get("source_store") or ""),
                    str(item.get("category") or ""),
                    str(item.get("field") or ""),
                ]
            )
        grouped[key].append(item)

    packs: list[dict[str, Any]] = []
    for batch_key, items in grouped.items():
        first = items[0]
        packs.append(
            {
                "batch_key": batch_key,
                "missing": len(items),
                "field": first.get("field"),
                "source_group": first.get("source_group"),
                "source_store": first.get("source_store"),
                "category": first.get("category"),
                "strategy": first.get("strategy"),
                "workstream": first.get("workstream"),
                "field_action": first.get("field_action"),
                "risk": first.get("risk"),
                "automation_candidate": bool(first.get("automation_candidate")),
                "batch_hint": first.get("batch_hint"),
                "samples": _sample_field_items(items),
            }
        )
    packs.sort(
        key=lambda item: (
            0 if item["source_group"] == "animation_goods" else 1,
            0 if item["field"] in {"source_url", "release_date"} else 1,
            0 if item["automation_candidate"] else 1,
            -int(item["missing"]),
            str(item["source_store"]),
            str(item["category"]),
        )
    )
    return packs[:limit]


def _image_work_packs(image_items: list[dict[str, Any]], limit: int = 40) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in image_items:
        key = (
            str(item.get("automation_safety") or ""),
            str(item.get("strategy") or ""),
            str(item.get("source_store") or ""),
            str(item.get("category") or ""),
        )
        grouped[key].append(item)

    packs: list[dict[str, Any]] = []
    for (automation_safety, strategy, source_store, category), items in grouped.items():
        first = items[0]
        packs.append(
            {
                "automation_safety": automation_safety,
                "provider_status": first.get("provider_status"),
                "strategy": strategy,
                "source_store": source_store,
                "category": category,
                "missing_images": len(items),
                "priority": first.get("priority"),
                "next_action": _image_next_action(strategy, automation_safety),
                "samples": _sample_image_items(items),
            }
        )
    packs.sort(
        key=lambda item: (
            _image_safety_rank(str(item.get("automation_safety") or "")),
            int(item.get("priority") or 999),
            -int(item.get("missing_images") or 0),
            str(item.get("source_store") or ""),
            str(item.get("category") or ""),
        )
    )
    return packs[:limit]


def _image_safety_rank(value: str) -> int:
    ranks = {
        "candidate_provider_script_required": 0,
        "manual_confirmation_required": 1,
        "detail_page_validation_required": 2,
        "safe_if_exact_image_or_jsonld": 3,
        "manual_research_required": 4,
        "blocked_until_exact_product_url": 5,
    }
    return ranks.get(value, 99)


def _image_next_action(strategy: str, automation_safety: str) -> str:
    if automation_safety == "candidate_provider_script_required":
        return "run_verified_provider_search_then_confirm_exact_detail_matches"
    if automation_safety == "manual_confirmation_required":
        return "open_official_search_url_and_confirm_exact_product_before_import"
    if automation_safety == "detail_page_validation_required":
        return "validate_prize_detail_page_before_attaching_image"
    if automation_safety == "safe_if_exact_image_or_jsonld":
        return "extract_image_from_existing_exact_source_url"
    if strategy.startswith("source_url_"):
        return "replace_generic_source_with_exact_product_url_first"
    return "manual_official_or_trusted_source_research"


def build_backlog(
    queue_payload: dict[str, Any],
    quality_payload: dict[str, Any],
    field_queue_payload: dict[str, Any] | None = None,
    image_provider_audit: dict[str, Any] | None = None,
    source_discovery_payload: dict[str, Any] | None = None,
    stale_source_payload: dict[str, Any] | None = None,
    priority_goods_payload: dict[str, Any] | None = None,
    naming_queue_payload: dict[str, Any] | None = None,
    ichiban_quality_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    queue = [item for item in queue_payload.get("queue", []) if isinstance(item, dict)]
    by_strategy = Counter(str(item.get("strategy") or "") for item in queue)
    by_provider_status = Counter(str(item.get("provider_status") or "") for item in queue)
    by_automation_safety = Counter(str(item.get("automation_safety") or "") for item in queue)
    by_store = Counter(str(item.get("source_store") or "") for item in queue)
    by_store_strategy: dict[str, Counter[str]] = defaultdict(Counter)
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in queue:
        store = str(item.get("source_store") or "")
        strategy = str(item.get("strategy") or "")
        by_store_strategy[store][strategy] += 1
        if len(samples[store]) < 8:
            samples[store].append(
                {
                    "name_ko": item.get("name_ko"),
                    "name_ja": item.get("name_ja"),
                    "category": item.get("category"),
                    "query": item.get("query"),
                    "search_url": item.get("search_url"),
                }
            )

    actions = []
    for store, count in by_store.most_common():
        strategies = dict(by_store_strategy[store])
        if strategies.get("official_search"):
            next_action = "official_search_provider_or_manual_review"
        elif strategies.get("prize_detail_validation") or strategies.get("prize_maker_search"):
            next_action = "strict_prize_provider_needed"
        elif strategies.get("manual_official_search_review"):
            next_action = "manual_official_search_then_detail_validation"
        elif strategies.get("source_url_lookup"):
            next_action = "source_url_metadata_lookup"
        else:
            next_action = "find_official_source_or_manual_image_review"
        actions.append(
            {
                "source_store": store,
                "missing_images": count,
                "strategies": strategies,
                "next_action": next_action,
                "samples": samples[store],
            }
        )

    field_queue_payload = field_queue_payload or {}
    image_provider_audit = image_provider_audit or {}
    field_top = [
        item
        for item in field_queue_payload.get("top_store_fields", [])
        if isinstance(item, dict)
    ][:40]
    field_strategy_top = [
        item
        for item in field_queue_payload.get("top_strategy_store_fields", [])
        if isinstance(item, dict)
    ][:60]
    field_store_category_top = [
        item
        for item in field_queue_payload.get("top_store_category_fields", [])
        if isinstance(item, dict)
    ][:60]
    image_strategy_store_top = [
        item
        for item in queue_payload.get("top_strategy_stores", [])
        if isinstance(item, dict)
    ][:60]
    image_store_category_top = [
        item
        for item in queue_payload.get("top_store_categories", [])
        if isinstance(item, dict)
    ][:60]
    image_safety_store_top = _counter_rows(
        Counter(
            (
                str(item.get("automation_safety") or ""),
                str(item.get("source_store") or ""),
            )
            for item in queue
        ),
        ("automation_safety", "source_store"),
        80,
    )
    for item in image_safety_store_top:
        item["missing_images"] = item.pop("count")

    field_items = [
        item
        for item in field_queue_payload.get("queue", [])
        if isinstance(item, dict)
    ]
    field_by_strategy_store_category: Counter[tuple[str, str, str]] = Counter(
        (
            str(item.get("strategy") or ""),
            str(item.get("source_store") or ""),
            str(item.get("category") or ""),
        )
        for item in field_items
    )
    field_by_workstream: Counter[str] = Counter(str(item.get("workstream") or "") for item in field_items)
    field_by_action: Counter[str] = Counter(str(item.get("field_action") or "") for item in field_items)
    field_by_risk: Counter[str] = Counter(str(item.get("risk") or "") for item in field_items)
    source_discovery_payload = source_discovery_payload or {}
    source_summary = source_discovery_payload.get("summary") or {}
    source_items = [
        item
        for item in source_discovery_payload.get("items", [])
        if isinstance(item, dict)
    ]
    source_by_workflow: Counter[str] = Counter(str(item.get("workflow") or "") for item in source_items)
    source_by_store: Counter[str] = Counter(str(item.get("source_store") or "") for item in source_items)
    stale_source_payload = stale_source_payload or {}
    stale_summary = stale_source_payload.get("summary") or {}
    stale_items = [
        item
        for item in stale_source_payload.get("items", [])
        if isinstance(item, dict)
    ]
    stale_by_store: Counter[str] = Counter(str(item.get("source_store") or "") for item in stale_items)
    stale_by_risk: Counter[str] = Counter(str(item.get("risk") or "") for item in stale_items)
    priority_goods_payload = priority_goods_payload or {}
    priority_summaries = priority_goods_payload.get("summaries") or {}
    naming_queue_payload = naming_queue_payload or {}
    naming_summary = naming_queue_payload.get("summary") or {}
    naming_items = [
        item
        for item in naming_queue_payload.get("items", [])
        if isinstance(item, dict)
    ]
    naming_by_workflow: Counter[str] = Counter(str(item.get("workflow") or "") for item in naming_items)
    ichiban_quality_payload = ichiban_quality_payload or {}
    ichiban_quality_summary = ichiban_quality_payload.get("summary") or {}
    ichiban_quality_items = [
        item
        for item in ichiban_quality_payload.get("items", [])
        if isinstance(item, dict)
    ]
    ichiban_work_packs = [
        item
        for item in ichiban_quality_payload.get("work_packs", [])
        if isinstance(item, dict)
    ]
    ichiban_by_workflow: Counter[str] = Counter(
        str(item.get("workflow") or "") for item in ichiban_quality_items
    )

    return {
        "rows": quality_payload.get("rows"),
        "missing_enrichment": quality_payload.get("missing_enrichment"),
        "missing_images": queue_payload.get("missing_images"),
        "source_discovery_rows": source_summary.get("source_discovery_rows", len(source_items)),
        "source_discovery_by_workflow": source_by_workflow.most_common(),
        "source_discovery_top_stores": [
            {"source_store": store, "rows": count}
            for store, count in source_by_store.most_common(30)
        ],
        "source_discovery_top_store_categories": source_summary.get("top_store_categories", [])[:60],
        "stale_source_review": {
            "review_rows": stale_summary.get("review_rows", len(stale_items)),
            "mismatch_rows": stale_summary.get("mismatch_rows", 0),
            "weak_overlap_rows": stale_summary.get("weak_overlap_rows", 0),
            "mismatch_urls": stale_summary.get("mismatch_urls", 0),
            "weak_overlap_urls": stale_summary.get("weak_overlap_urls", 0),
            "by_source_store": [
                {"source_store": store, "rows": count}
                for store, count in stale_by_store.most_common(20)
            ],
            "by_risk": [
                {"risk": risk, "rows": count}
                for risk, count in stale_by_risk.most_common()
            ],
            "sample_rows": stale_items[:12],
        },
        "priority_goods_summary": priority_summaries,
        "priority_goods_incomplete_samples": [
            item
            for item in priority_goods_payload.get("items", [])
            if isinstance(item, dict) and item.get("missing_fields")
        ][:40],
        "naming_quality": {
            "queue_rows": naming_summary.get("queue_rows", len(naming_items)),
            "known_alias_rows": naming_summary.get("known_alias_rows", 0),
            "ja_token_mismatch_rows": naming_summary.get("ja_token_mismatch_rows", 0),
            "single_character_name_review_rows": naming_summary.get(
                "single_character_name_review_rows", 0
            ),
            "ichiban_naming_convention_review_rows": naming_summary.get(
                "ichiban_naming_convention_review_rows", 0
            ),
            "by_workflow": naming_by_workflow.most_common(),
            "sample_rows": naming_items[:20],
        },
        "ichiban_quality": {
            "queue_rows": ichiban_quality_summary.get("queue_rows", len(ichiban_quality_items)),
            "campaign_gap_queue_rows": ichiban_quality_summary.get("campaign_gap_queue_rows", 0),
            "exact_display_duplicate_queue_rows": ichiban_quality_summary.get(
                "exact_display_duplicate_queue_rows", 0
            ),
            "zero_price_policy_queue_rows": ichiban_quality_summary.get(
                "zero_price_policy_queue_rows", 0
            ),
            "naming_convention_queue_rows": ichiban_quality_summary.get(
                "naming_convention_queue_rows", 0
            ),
            "campaign_count": ichiban_quality_summary.get("campaign_count", 0),
            "seeded_campaign_url_count": ichiban_quality_summary.get(
                "seeded_campaign_url_count", 0
            ),
            "work_pack_rows": ichiban_quality_summary.get("work_pack_rows", len(ichiban_work_packs)),
            "by_workflow": ichiban_by_workflow.most_common(),
            "work_packs": ichiban_work_packs[:40],
            "sample_rows": ichiban_quality_items[:20],
        },
        "field_queue_missing_total": field_queue_payload.get("missing_total"),
        "field_queue_by_field": field_queue_payload.get("by_field", []),
        "field_queue_by_strategy": field_queue_payload.get("by_strategy", []),
        "field_queue_by_workstream": field_by_workstream.most_common(),
        "field_queue_by_action": field_by_action.most_common(),
        "field_queue_by_risk": field_by_risk.most_common(),
        "field_queue_by_source_group_field": field_queue_payload.get("by_source_group_field", []),
        "top_field_backlog": field_top,
        "top_field_strategy_store_backlog": field_strategy_top,
        "top_field_store_category_backlog": field_store_category_top,
        "top_field_strategy_store_category_backlog": _counter_rows(
            field_by_strategy_store_category,
            ("strategy", "source_store", "category"),
            80,
        ),
        "top_field_batch_backlog": field_queue_payload.get("top_batch_keys", [])[:80],
        "animation_goods_category_field_backlog": field_queue_payload.get("animation_goods_category_fields", [])[:80],
        "animation_goods_store_category_field_backlog": field_queue_payload.get(
            "animation_goods_store_category_fields",
            [],
        )[:80],
        "field_focus_packs": _field_focus_packs(field_items, 40),
        "image_queue_by_strategy": by_strategy.most_common(),
        "image_queue_by_provider_status": by_provider_status.most_common(),
        "image_queue_by_automation_safety": by_automation_safety.most_common(),
        "image_queue_by_category": queue_payload.get("by_category", []),
        "image_provider_recommendation_counts": image_provider_audit.get("recommendation_counts", []),
        "image_provider_reason_counts": image_provider_audit.get("reason_counts", []),
        "top_image_provider_actions": image_provider_audit.get("top_stores", [])[:30],
        "top_image_strategy_store_backlog": image_strategy_store_top,
        "top_image_safety_store_backlog": image_safety_store_top,
        "top_image_store_category_backlog": image_store_category_top,
        "image_work_packs": _image_work_packs(queue, 60),
        "top_image_backlog": actions[:60],
        "recommended_sequence": [
            "Start with field_focus_packs where automation_candidate is true; each pack is one store/category/field batch.",
            "For animation goods, clear source_url first, then use the exact detail pages to fill release_date, image_url, and price where available.",
            "Treat barcode as a high-risk field; many prizes and campaign items should stay blank unless JAN/barcode is explicitly published.",
            "Use priority_goods_summary before broad queue work when the user names focus collections like Danganronpa, Mahosaba, or Ichiban Kuji.",
            "Review naming_quality before bulk imports; alias fixes and Ichiban display-name convention issues are cheap to correct and make later dedupe safer.",
            "Review ichiban_quality before importing historical campaigns; it separates campaign gaps, reissue/duplicate review, zero-price policy, and non-prize related item classification.",
            "Review stale_source_review before importing source-derived images; weak overlap rows need a stronger exact source first.",
            "Run verified official providers only; avoid broad search result pages without strict matching.",
            "Use the field enrichment queue for source_url, release_date, barcode, price, and image work; image queue is only the photo subset.",
            "Goodsmile goodsmile.info search is available, but only exact title matches are safe; fuzzy hits can point to different variants.",
            "Animate search markup is supported, but use strict matches only because generic Korean catalog names can match several variants.",
            "FuRyu official API is supported; many older seed rows are not returned by the current public search API.",
            "Taito official API matching is supported, but it should be run in small batches because older prize rows may no longer be returned.",
            "Banpresto matching fetches detail pages and rejects broad search hits unless the title validation is strong.",
            "Kotobukiya and Movic matching fetches detail pages after search and only accepts exact or near-contained title matches.",
            "Continue Ensky sitemap cache in small batches, then review exact-match candidates.",
            "Find a separate official source for Chiikawa gotouchi/regional goods.",
            "Use manual review for VTuber/K-pop store rows where product pages are not public or stable.",
        ],
    }


def write_markdown(backlog: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog Update Backlog",
        "",
        f"- Rows: `{backlog.get('rows')}`",
        f"- Missing images: `{backlog.get('missing_images')}`",
        f"- Source discovery rows: `{backlog.get('source_discovery_rows')}`",
        f"- Missing field cells: `{backlog.get('field_queue_missing_total')}`",
        f"- Missing enrichment: `{json.dumps(backlog.get('missing_enrichment'), ensure_ascii=False)}`",
        "",
        "## Source Discovery",
        "",
    ]
    for workflow, count in backlog.get("source_discovery_by_workflow", []):
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "## Source Discovery Top Stores", ""])
    for item in backlog.get("source_discovery_top_stores", [])[:25]:
        lines.append(f"- `{item.get('source_store')}`: `{item.get('rows')}`")
    lines.extend(["", "## Source Discovery Store Categories", ""])
    for item in backlog.get("source_discovery_top_store_categories", [])[:25]:
        lines.append(
            f"- `{item.get('source_store')}` / `{item.get('category')}`: "
            f"`{item.get('rows')}`"
        )
    stale = backlog.get("stale_source_review") or {}
    lines.extend(["", "## Stale Source Review", ""])
    lines.append(f"- Review rows: `{stale.get('review_rows', 0)}`")
    lines.append(f"- Mismatch rows: `{stale.get('mismatch_rows', 0)}`")
    lines.append(f"- Weak overlap rows: `{stale.get('weak_overlap_rows', 0)}`")
    lines.append(f"- Mismatch URLs: `{stale.get('mismatch_urls', 0)}`")
    lines.append(f"- Weak overlap URLs: `{stale.get('weak_overlap_urls', 0)}`")
    lines.extend(["", "### Stale Source Stores", ""])
    for item in stale.get("by_source_store", [])[:20]:
        lines.append(f"- `{item.get('source_store')}`: `{item.get('rows')}`")
    lines.extend(["", "### Stale Source Risk", ""])
    for item in stale.get("by_risk", []):
        lines.append(f"- `{item.get('risk')}`: `{item.get('rows')}`")
    priority = backlog.get("priority_goods_summary") or {}
    lines.extend(["", "## Priority Goods", ""])
    if not priority:
        lines.append("- No priority goods queue loaded.")
    for label, summary in priority.items():
        lines.append(
            f"- `{label}`: `{summary.get('rows')}` rows, "
            f"`{summary.get('incomplete_rows')}` incomplete, "
            f"missing `{json.dumps(summary.get('missing_fields'), ensure_ascii=False)}`"
        )
    naming = backlog.get("naming_quality") or {}
    lines.extend(["", "## Naming Quality", ""])
    lines.append(f"- Queue rows: `{naming.get('queue_rows', 0)}`")
    lines.append(f"- Known alias rows: `{naming.get('known_alias_rows', 0)}`")
    lines.append(f"- Japanese token mismatch rows: `{naming.get('ja_token_mismatch_rows', 0)}`")
    lines.append(
        f"- Single-character review rows: `{naming.get('single_character_name_review_rows', 0)}`"
    )
    lines.append(
        "- Ichiban display-name convention rows: "
        f"`{naming.get('ichiban_naming_convention_review_rows', 0)}`"
    )
    lines.extend(["", "### Naming Workflows", ""])
    for workflow, count in naming.get("by_workflow", []):
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "### Naming Samples", ""])
    for item in naming.get("sample_rows", [])[:10]:
        lines.append(
            f"- `{item.get('workflow')}` / `{item.get('display_name')}` / "
            f"`{item.get('reason')}`"
        )
    ichiban = backlog.get("ichiban_quality") or {}
    lines.extend(["", "## Ichiban Quality", ""])
    lines.append(f"- Queue rows: `{ichiban.get('queue_rows', 0)}`")
    lines.append(f"- Campaign gaps: `{ichiban.get('campaign_gap_queue_rows', 0)}`")
    lines.append(
        f"- Duplicate/reissue review rows: `{ichiban.get('exact_display_duplicate_queue_rows', 0)}`"
    )
    lines.append(f"- Zero-price policy rows: `{ichiban.get('zero_price_policy_queue_rows', 0)}`")
    lines.append(
        f"- Naming/non-prize review rows: `{ichiban.get('naming_convention_queue_rows', 0)}`"
    )
    lines.append(
        f"- Seeded campaign URLs: `{ichiban.get('seeded_campaign_url_count', 0)}` / "
        f"`{ichiban.get('campaign_count', 0)}`"
    )
    lines.extend(["", "### Ichiban Workflows", ""])
    for workflow, count in ichiban.get("by_workflow", []):
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "### Ichiban Work Packs", ""])
    lines.append(f"- Total work packs: `{ichiban.get('work_pack_rows', 0)}`")
    for item in ichiban.get("work_packs", [])[:15]:
        lines.append(
            f"- `{item.get('workflow')}` / `{item.get('group_key')}`: "
            f"`{item.get('rows')}` rows, `{item.get('next_action')}`"
        )
    lines.extend(["", "### Ichiban Samples", ""])
    for item in ichiban.get("sample_rows", [])[:10]:
        lines.append(
            f"- `{item.get('workflow')}` / `{item.get('display_name')}` / "
            f"`{item.get('source_url')}` / `{item.get('reason')}`"
        )
    lines.extend(
        [
            "",
        "## Field Queue",
        "",
        ]
    )
    for field, count in backlog.get("field_queue_by_field", []):
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(["", "## Field Strategies", ""])
    for strategy, count in backlog.get("field_queue_by_strategy", []):
        lines.append(f"- `{strategy}`: `{count}`")
    lines.extend(["", "## Field Workstreams", ""])
    for workstream, count in backlog.get("field_queue_by_workstream", []):
        lines.append(f"- `{workstream}`: `{count}`")
    lines.extend(["", "## Field Actions", ""])
    for action, count in backlog.get("field_queue_by_action", []):
        lines.append(f"- `{action}`: `{count}`")
    lines.extend(["", "## Field Risk", ""])
    for risk, count in backlog.get("field_queue_by_risk", []):
        lines.append(f"- `{risk}`: `{count}`")
    lines.extend(["", "## Field Source Groups", ""])
    for item in backlog.get("field_queue_by_source_group_field", [])[:25]:
        lines.append(
            f"- `{item.get('source_group')}` / `{item.get('field')}`: "
            f"`{item.get('missing')}`"
        )
    lines.extend(["", "## Top Field Backlog", ""])
    for item in backlog.get("top_field_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('source_store')}` / `{item.get('field')}`: "
            f"`{item.get('missing')}`"
        )
    lines.extend(["", "## Top Field Strategy Store Backlog", ""])
    for item in backlog.get("top_field_strategy_store_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('strategy')}` / `{item.get('source_store')}` / "
            f"`{item.get('field')}`: `{item.get('missing')}`"
        )
    lines.extend(["", "## Top Field Store Category Backlog", ""])
    for item in backlog.get("top_field_store_category_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('source_store')}` / `{item.get('category')}` / "
            f"`{item.get('field')}`: `{item.get('missing')}`"
        )
    lines.extend(["", "## Animation Goods Field Backlog", ""])
    for item in backlog.get("animation_goods_category_field_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('category')}` / `{item.get('field')}`: "
            f"`{item.get('missing')}`"
        )
    lines.extend(["", "## Animation Goods Store Category Backlog", ""])
    for item in backlog.get("animation_goods_store_category_field_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('source_store')}` / `{item.get('category')}` / "
            f"`{item.get('field')}`: `{item.get('missing')}`"
        )
    lines.extend(["", "## Field Focus Packs", ""])
    for item in backlog.get("field_focus_packs", [])[:25]:
        lines.append(
            f"- `{item.get('batch_key')}`: `{item.get('missing')}` missing, "
            f"`{item.get('field_action')}`, risk `{item.get('risk')}`, "
            f"automation `{item.get('automation_candidate')}`"
        )
    lines.extend(["", "## Top Field Batch Keys", ""])
    for item in backlog.get("top_field_batch_backlog", [])[:25]:
        lines.append(f"- `{item.get('batch_key')}`: `{item.get('missing')}`")
    lines.extend(
        [
            "",
            "## Image Queue",
            "",
        ]
    )
    for strategy, count in backlog.get("image_queue_by_strategy", []):
        lines.append(f"- `{strategy}`: `{count}`")
    lines.extend(["", "## Image Provider Status", ""])
    for status, count in backlog.get("image_queue_by_provider_status", []):
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Image Automation Safety", ""])
    for safety, count in backlog.get("image_queue_by_automation_safety", []):
        lines.append(f"- `{safety}`: `{count}`")
    lines.extend(["", "## Image Categories", ""])
    for category, count in backlog.get("image_queue_by_category", [])[:20]:
        lines.append(f"- `{category}`: `{count}`")
    lines.extend(["", "## Image Provider Actions", ""])
    for item in backlog.get("image_provider_recommendation_counts", []):
        lines.append(f"- `{item.get('value')}`: `{item.get('count')}`")
    lines.extend(["", "## Image Provider Reasons", ""])
    for item in backlog.get("image_provider_reason_counts", []):
        lines.append(f"- `{item.get('value')}`: `{item.get('count')}`")
    lines.extend(["", "## Top Image Provider Stores", ""])
    for item in backlog.get("top_image_provider_actions", [])[:25]:
        lines.append(
            f"- `{item.get('source_store')}`: `{item.get('missing_images')}` missing, "
            f"{item.get('recommended_action')}"
        )
    lines.extend(["", "## Top Image Strategy Store Backlog", ""])
    for item in backlog.get("top_image_strategy_store_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('strategy')}` / `{item.get('source_store')}`: "
            f"`{item.get('missing_images')}`"
        )
    lines.extend(["", "## Top Image Safety Store Backlog", ""])
    for item in backlog.get("top_image_safety_store_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('automation_safety')}` / `{item.get('source_store')}`: "
            f"`{item.get('missing_images')}`"
        )
    lines.extend(["", "## Image Work Packs", ""])
    for item in backlog.get("image_work_packs", [])[:25]:
        sample = (item.get("samples") or [{}])[0]
        lines.append(
            f"- `{item.get('automation_safety')}` / `{item.get('strategy')}` / "
            f"`{item.get('source_store')}` / `{item.get('category')}`: "
            f"`{item.get('missing_images')}` missing, `{item.get('next_action')}`"
        )
        if sample:
            lines.append(
                f"  - sample `{sample.get('row_index')}` / `{sample.get('name_ko')}` / "
                f"`{sample.get('search_url')}`"
            )
    lines.extend(["", "## Top Image Store Category Backlog", ""])
    for item in backlog.get("top_image_store_category_backlog", [])[:25]:
        lines.append(
            f"- `{item.get('source_store')}` / `{item.get('category')}`: "
            f"`{item.get('missing_images')}`"
        )
    lines.extend(["", "## Recommended Sequence", ""])
    for item in backlog.get("recommended_sequence", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Top Stores", ""])
    for item in backlog.get("top_image_backlog", [])[:25]:
        lines.append(
            f"- `{item['source_store']}`: `{item['missing_images']}` missing, "
            f"`{item['next_action']}`"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--field-queue", type=Path, default=DEFAULT_FIELD_QUEUE)
    parser.add_argument("--source-discovery", type=Path, default=DEFAULT_SOURCE_DISCOVERY)
    parser.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--naming-queue", type=Path, default=DEFAULT_NAMING_QUEUE)
    parser.add_argument("--ichiban-quality-queue", type=Path, default=DEFAULT_ICHIBAN_QUALITY_QUEUE)
    parser.add_argument("--image-provider-audit", type=Path, default=DEFAULT_IMAGE_PROVIDER_AUDIT)
    parser.add_argument("--stale-source-queue", type=Path, default=DEFAULT_STALE_SOURCE_QUEUE)
    parser.add_argument("--priority-goods-queue", type=Path, default=DEFAULT_PRIORITY_GOODS_QUEUE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    queue_payload = json.loads(args.queue.read_text(encoding="utf-8-sig"))
    quality_payload = json.loads(args.quality.read_text(encoding="utf-8-sig"))
    field_queue_payload = (
        json.loads(args.field_queue.read_text(encoding="utf-8-sig"))
        if args.field_queue.exists()
        else {}
    )
    image_provider_audit = (
        json.loads(args.image_provider_audit.read_text(encoding="utf-8-sig"))
        if args.image_provider_audit.exists()
        else {}
    )
    source_discovery_payload = (
        json.loads(args.source_discovery.read_text(encoding="utf-8-sig"))
        if args.source_discovery.exists()
        else {}
    )
    stale_source_payload = (
        json.loads(args.stale_source_queue.read_text(encoding="utf-8-sig"))
        if args.stale_source_queue.exists()
        else {}
    )
    priority_goods_payload = (
        json.loads(args.priority_goods_queue.read_text(encoding="utf-8-sig"))
        if args.priority_goods_queue.exists()
        else {}
    )
    naming_queue_payload = (
        json.loads(args.naming_queue.read_text(encoding="utf-8-sig"))
        if args.naming_queue.exists()
        else {}
    )
    ichiban_quality_payload = (
        json.loads(args.ichiban_quality_queue.read_text(encoding="utf-8-sig"))
        if args.ichiban_quality_queue.exists()
        else {}
    )
    backlog = build_backlog(
        queue_payload,
        quality_payload,
        field_queue_payload,
        image_provider_audit,
        source_discovery_payload,
        stale_source_payload,
        priority_goods_payload,
        naming_queue_payload,
        ichiban_quality_payload,
    )
    args.json_output.write_text(json.dumps(backlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(backlog, args.markdown_output)
    print(
        json.dumps(
            {
                "missing_images": backlog["missing_images"],
                "source_discovery_rows": backlog.get("source_discovery_rows"),
                "stale_source_review_rows": (backlog.get("stale_source_review") or {}).get("review_rows"),
                "naming_quality_rows": (backlog.get("naming_quality") or {}).get("queue_rows"),
                "ichiban_quality_rows": (backlog.get("ichiban_quality") or {}).get("queue_rows"),
                "field_focus_pack_rows": len(backlog.get("field_focus_packs") or []),
                "field_focus_automation_pack_rows": sum(
                    1 for item in backlog.get("field_focus_packs") or [] if item.get("automation_candidate")
                ),
                "image_work_pack_rows": len(backlog.get("image_work_packs") or []),
                "ichiban_work_pack_rows": (backlog.get("ichiban_quality") or {}).get("work_pack_rows"),
                "priority_goods": sorted((backlog.get("priority_goods_summary") or {}).keys()),
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
