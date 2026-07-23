from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_deduplication_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_deduplication_action_queue_public.json"
DEFAULT_ICHIBAN_POLICY_AUDIT = ROOT / "data" / "ichiban_kuji_prize_policy_audit_public.json"

ACTIONABLE_CONFIDENCES = {"high_review_confidence", "medium_review_confidence"}
CONFIDENCE_PRIORITY = {
    "high_review_confidence": 10,
    "medium_review_confidence": 20,
}
CONFIRMED_TEMPLATE = "server/catalog_dedupe_confirmed_decisions.template.json"
CONFIRMED_QUEUE = "server/catalog_dedupe_confirmed_decisions.json"
IMPORT_TOOL = "tools/import_confirmed_dedupe_decisions.py"
UNBLOCKS_WHEN = "explicit_manual_keep_drop_decision_confirmed"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(str(row.get(key) or "") for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _counter_to_pairs(counter: Counter[str]) -> list[list[Any]]:
    return [[name, count] for name, count in counter.most_common()]


def _counter_from_values(values: list[str]) -> list[list[Any]]:
    return _counter_to_pairs(Counter(value for value in values if value))


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _unique_sorted(values: list[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _is_zero_price_exception_label(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return any(
        token in text
        for token in [
            "last one",
            "last-one",
            "double chance",
            "double-chance",
            "ラストワン",
            "ダブルチャンス",
            "더블찬스",
            "라스트원",
        ]
    )


def _price_value(row: dict[str, Any]) -> int | None:
    value = row.get("official_price_jpy")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _prize_identity_summary(sample_rows: list[dict[str, Any]]) -> dict[str, Any]:
    prize_labels = [
        row.get("sub_series") or row.get("name_ja") or row.get("name_ko")
        for row in sample_rows
    ]
    exception_rows = [
        row
        for row in sample_rows
        if _is_zero_price_exception_label(row.get("sub_series"))
        or _is_zero_price_exception_label(row.get("name_ja"))
        or _is_zero_price_exception_label(row.get("name_ko"))
    ]
    nonzero_exception_rows = [
        row
        for row in exception_rows
        if (price := _price_value(row)) is not None and price != 0
    ]
    return {
        "series_names": _unique_sorted([row.get("series_name") for row in sample_rows]),
        "prize_labels": _unique_sorted(prize_labels),
        "prize_label_count": len(_unique_sorted(prize_labels)),
        "display_names": _unique_sorted([row.get("name_ja") or row.get("name_ko") for row in sample_rows]),
        "display_name_count": len(_unique_sorted([row.get("name_ja") or row.get("name_ko") for row in sample_rows])),
        "official_price_jpy_values": sorted(
            {price for row in sample_rows if (price := _price_value(row)) is not None}
        ),
        "zero_price_exception_rows": len(exception_rows),
        "zero_price_exception_nonzero_rows": len(nonzero_exception_rows),
        "zero_price_exception_policy_pass": len(nonzero_exception_rows) == 0,
        "identity_fields_required": [
            "series_name",
            "source_url",
            "sub_series_or_prize_rank",
            "name_ja_or_official_prize_name",
            "official_price_jpy",
            "image_url",
        ],
    }


def _campaign_slug(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[-1] if parts else ""


def _slug_family(slug: str) -> str:
    return slug.rstrip("0123456789-_")


def _slug_numeric_suffix(slug: str) -> str:
    suffix = ""
    for char in reversed(slug):
        if not char.isdigit():
            break
        suffix = char + suffix
    return suffix


def _campaign_url_comparison(source_urls: list[str]) -> dict[str, Any]:
    slugs = [_campaign_slug(url) for url in source_urls]
    families = _unique_sorted([_slug_family(slug) for slug in slugs])
    suffixes = _unique_sorted([_slug_numeric_suffix(slug) for slug in slugs])
    return {
        "source_url_count": len(source_urls),
        "campaign_slugs": slugs,
        "campaign_slug_families": families,
        "campaign_slug_family_count": len(families),
        "numeric_suffixes": suffixes,
        "has_numbered_campaign_suffixes": bool(suffixes),
        "likely_same_campaign_family_reissue": len(families) == 1 and len(source_urls) > 1 and bool(suffixes),
        "dedupe_risk_note": (
            "Same slug family with numbered campaign URLs usually needs reissue/campaign-wave review before dedupe."
            if len(families) == 1 and len(source_urls) > 1 and bool(suffixes)
            else "Compare official campaign titles and prize lineup before deciding keep/drop."
        ),
    }


def protected_ichiban_reissue_catalog_indexes(policy_audit: dict[str, Any] | None) -> set[int]:
    if not policy_audit:
        return set()

    protected: set[int] = set()
    for group in policy_audit.get("probable_reissue_review_groups") or []:
        if not isinstance(group, dict):
            continue
        if not group.get("has_reissue_signal"):
            continue
        for row in group.get("sample_rows") or []:
            if not isinstance(row, dict):
                continue
            catalog_index = row.get("catalog_index")
            if isinstance(catalog_index, int):
                protected.add(catalog_index)
    return protected


def ichiban_reissue_review_index(policy_audit: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not policy_audit:
        return {}

    index: dict[int, dict[str, Any]] = {}
    for group in policy_audit.get("probable_reissue_review_groups") or []:
        if not isinstance(group, dict):
            continue
        reasons = sorted(str(reason) for reason in group.get("reissue_signal_reasons") or [])
        entry = {
            "normalized_name": group.get("normalized_name"),
            "source_urls": group.get("source_urls") or [],
            "reissue_signal_reasons": reasons,
            "review_reason": group.get("review_reason"),
            "has_reissue_signal": bool(group.get("has_reissue_signal")),
            "probable_reissue_review": bool(group.get("has_reissue_signal")),
        }
        for row in group.get("sample_rows") or []:
            if not isinstance(row, dict):
                continue
            catalog_index = row.get("catalog_index")
            if isinstance(catalog_index, int):
                index[catalog_index] = entry
    return index


def ichiban_reissue_review_lane(
    policy_audit: dict[str, Any] | None,
    *,
    limit: int = 80,
) -> list[dict[str, Any]]:
    if not policy_audit:
        return []

    lane: list[dict[str, Any]] = []
    for group in policy_audit.get("probable_reissue_review_groups") or []:
        if not isinstance(group, dict):
            continue
        sample_rows = [row for row in group.get("sample_rows") or [] if isinstance(row, dict)]
        prize_identity = _prize_identity_summary(sample_rows)
        source_urls = group.get("source_urls") or _unique_sorted([row.get("source_url") for row in sample_rows])
        lane.append(
            {
                "normalized_name": group.get("normalized_name"),
                "row_count": group.get("row_count"),
                "source_url_count": group.get("source_url_count"),
                "has_reissue_signal": bool(group.get("has_reissue_signal")),
                "reissue_signal_reasons": group.get("reissue_signal_reasons") or [],
                "campaign_slug_families": group.get("campaign_slug_families") or [],
                "source_urls": source_urls,
                "review_reason": group.get("review_reason"),
                "review_state": "probable_reissue_manual_confirmation_required",
                "next_machine_step": "verify_ichiban_campaign_pages_before_dedupe",
                "merge_blockers": ["ichiban_reissue_manual_confirmation_required"],
                "prize_identity_summary": prize_identity,
                "sample_rows": sample_rows,
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
            }
        )
    lane.sort(
        key=lambda row: (
            0 if row.get("has_reissue_signal") else 1,
            str(row.get("normalized_name") or ""),
        )
    )
    return lane[:limit]


def ichiban_reissue_work_order(
    review_lane: list[dict[str, Any]],
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    for rank, row in enumerate(review_lane[:limit], start=1):
        sample_rows = [sample for sample in row.get("sample_rows") or [] if isinstance(sample, dict)]
        catalog_indexes = sorted(
            {
                catalog_index
                for sample in sample_rows
                if isinstance((catalog_index := sample.get("catalog_index")), int)
            }
        )
        source_urls = [str(url).strip() for url in row.get("source_urls") or [] if str(url).strip()]
        prize_identity = _prize_identity_summary(sample_rows)
        campaign_url_comparison = _campaign_url_comparison(source_urls)
        orders.append(
            {
                "work_order_id": f"ichiban-reissue-dedupe-{rank:03d}",
                "priority": rank,
                "normalized_name": row.get("normalized_name"),
                "row_count": row.get("row_count"),
                "source_url_count": row.get("source_url_count"),
                "catalog_indexes": catalog_indexes,
                "source_urls": source_urls,
                "campaign_slug_families": row.get("campaign_slug_families") or [],
                "campaign_url_comparison": campaign_url_comparison,
                "reissue_signal_reasons": row.get("reissue_signal_reasons") or [],
                "review_state": "ichiban_reissue_identity_confirmation_required",
                "next_machine_step": "compare_campaign_pages_then_record_reissue_or_duplicate_decision",
                "manual_review_checklist": [
                    "Open every source_url and compare official campaign title/release period/prize lineup.",
                    "Verify the full product identity: release/campaign name, prize rank, official prize name, and variant name when one rank has multiple kinds.",
                    "If the same prize name appears in different campaigns or release waves, mark as reissue_or_campaign_variant and keep rows separate.",
                    "If rows are the exact same sellable prize from the same campaign/source, choose one keep_catalog_index and list drop_catalog_indexes.",
                    "Confirm Last One or Double Chance prize rows keep official price 0 when applicable.",
                    "Do not import any dedupe mutation until manual_confirmed is true with evidence_urls.",
                ],
                "decision_template": {
                    "work_order_id": f"ichiban-reissue-dedupe-{rank:03d}",
                    "manual_confirmed": False,
                    "decision": "",
                    "decision_options": [
                        "reissue_or_campaign_variant_keep_separate",
                        "same_sellable_product_keep_drop_confirmed",
                        "needs_more_source_evidence",
                    ],
                    "keep_catalog_index": None,
                    "drop_catalog_indexes": [],
                    "evidence_urls": source_urls,
                    "manual_note": "",
                    "protected_if_reissue": True,
                },
                "prize_identity_summary": prize_identity,
                "zero_price_exception_policy": {
                    "last_one_or_double_chance_rows_must_be_zero_jpy": True,
                    "current_group_pass": prize_identity["zero_price_exception_policy_pass"],
                    "nonzero_exception_rows": prize_identity["zero_price_exception_nonzero_rows"],
                },
                "sample_rows": sample_rows,
                "merge_blockers": ["ichiban_reissue_manual_confirmation_required"],
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
            }
        )
    return orders


def ichiban_reissue_campaign_work_order(
    reissue_work_orders: list[dict[str, Any]],
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for order in reissue_work_orders:
        source_urls = tuple(
            sorted(str(url).strip() for url in order.get("source_urls") or [] if str(url).strip())
        )
        if len(source_urls) < 2:
            continue
        grouped.setdefault(source_urls, []).append(order)

    campaign_orders: list[dict[str, Any]] = []
    for rank, (source_urls, orders) in enumerate(
        sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:limit],
        start=1,
    ):
        catalog_indexes = sorted(
            {
                catalog_index
                for order in orders
                for catalog_index in order.get("catalog_indexes") or []
                if isinstance(catalog_index, int)
            }
        )
        prize_labels = _unique_sorted(
            [
                label
                for order in orders
                for label in (order.get("prize_identity_summary") or {}).get("prize_labels") or []
            ]
        )
        sample_rows = [
            row
            for order in orders[:4]
            for row in order.get("sample_rows") or []
            if isinstance(row, dict)
        ][:12]
        campaign_orders.append(
            {
                "campaign_work_order_id": f"ichiban-reissue-campaign-{rank:03d}",
                "priority": rank,
                "source_urls": list(source_urls),
                "campaign_url_comparison": _campaign_url_comparison(list(source_urls)),
                "item_work_order_count": len(orders),
                "item_work_order_ids": [str(order.get("work_order_id") or "") for order in orders],
                "catalog_indexes": catalog_indexes,
                "catalog_row_count": len(catalog_indexes),
                "prize_labels": prize_labels,
                "review_state": "campaign_pair_reissue_or_duplicate_decision_required",
                "next_machine_step": "compare_campaign_pair_once_then_apply_decision_to_item_work_orders",
                "manual_review_checklist": [
                    "Open both campaign URLs and compare official campaign title, sale/release period, and lineup.",
                    "If the campaign pages are separate release waves or reissues, mark every item_work_order_id as reissue_or_campaign_variant_keep_separate.",
                    "If the pages are duplicate mirrors of the same campaign, review each item work order for keep/drop.",
                    "Do not delete or merge until every affected item work order has manual_confirmed=true.",
                ],
                "decision_template": {
                    "campaign_work_order_id": f"ichiban-reissue-campaign-{rank:03d}",
                    "manual_confirmed": False,
                    "decision": "",
                    "decision_options": [
                        "campaign_pair_reissue_keep_all_separate",
                        "campaign_pair_duplicate_review_each_item_keep_drop",
                        "needs_more_source_evidence",
                    ],
                    "affected_item_work_order_ids": [
                        str(order.get("work_order_id") or "") for order in orders
                    ],
                    "evidence_urls": list(source_urls),
                    "manual_note": "",
                },
                "sample_rows": sample_rows,
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
            }
        )
    return campaign_orders


def ichiban_reissue_policy_summary(policy_audit: dict[str, Any] | None) -> dict[str, int]:
    if not policy_audit:
        return {
            "ichiban_reissue_review_groups": 0,
            "ichiban_reissue_review_rows": 0,
            "ichiban_probable_reissue_review_groups": 0,
        }
    summary = policy_audit.get("summary") if isinstance(policy_audit.get("summary"), dict) else {}
    probable_groups = policy_audit.get("probable_reissue_review_groups") or []
    row_indexes: set[int] = set()
    for group in probable_groups:
        if not isinstance(group, dict):
            continue
        for row in group.get("sample_rows") or []:
            if not isinstance(row, dict):
                continue
            catalog_index = row.get("catalog_index")
            if isinstance(catalog_index, int):
                row_indexes.add(catalog_index)
    return {
        "ichiban_reissue_review_groups": int(summary.get("repeated_name_different_source_groups") or 0),
        "ichiban_reissue_review_rows": int(summary.get("repeated_name_different_source_review_catalog_item_rows") or 0),
        "ichiban_probable_reissue_review_groups": int(summary.get("probable_reissue_review_groups") or 0),
        "ichiban_probable_reissue_sample_rows": len(row_indexes),
    }


def _catalog_indexes(group: dict[str, Any]) -> set[int]:
    indexes: set[int] = set()
    for row in group.get("rows") or []:
        if not isinstance(row, dict):
            continue
        catalog_index = row.get("catalog_index")
        if isinstance(catalog_index, int):
            indexes.add(catalog_index)
    return indexes


def _row_richness(row: dict[str, Any]) -> int:
    value = row.get("richness")
    if isinstance(value, int):
        return value
    fields = [
        "name_ko",
        "name_ja",
        "name_en",
        "category",
        "character_name",
        "affiliation",
        "series_name",
        "sub_series",
        "official_price_jpy",
        "barcode",
        "image_url",
        "source_url",
        "source_store",
        "release_date",
    ]
    return sum(1 for field in fields if _present(row.get(field)))


def _keep_basis(group: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in group.get("rows") or [] if isinstance(row, dict)]
    keep_index = group.get("keep_catalog_index")
    keep_row = next((row for row in rows if row.get("catalog_index") == keep_index), None)
    if keep_row is None:
        return {
            "basis": "preselected_keep_row_from_review_queue",
            "keep_catalog_index": keep_index,
            "keep_richness": None,
            "max_richness": None,
            "keep_has_image": False,
            "keep_has_source_url": False,
        }
    keep_richness = _row_richness(keep_row)
    max_richness = max((_row_richness(row) for row in rows), default=keep_richness)
    return {
        "basis": "richest_or_equal_catalog_row" if keep_richness >= max_richness else "manual_recheck_keep_row",
        "keep_catalog_index": keep_index,
        "keep_richness": keep_richness,
        "max_richness": max_richness,
        "keep_has_image": _present(keep_row.get("image_url")),
        "keep_has_source_url": _present(keep_row.get("source_url")),
    }


def _row_comparison_summary(group: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in group.get("rows") or [] if isinstance(row, dict)]
    names = {str(row.get("name_ko") or "").strip() for row in rows if _present(row.get("name_ko"))}
    source_urls = {str(row.get("source_url") or "").strip() for row in rows if _present(row.get("source_url"))}
    image_urls = {str(row.get("image_url") or "").strip() for row in rows if _present(row.get("image_url"))}
    stores = {str(row.get("source_store") or "").strip() for row in rows if _present(row.get("source_store"))}
    categories = {str(row.get("category") or "").strip() for row in rows if _present(row.get("category"))}
    return {
        "name_count": len(names),
        "source_url_count": len(source_urls),
        "image_url_count": len(image_urls),
        "store_count": len(stores),
        "category_count": len(categories),
        "name_differs": len(names) > 1,
        "source_url_differs": len(source_urls) > 1,
        "image_url_differs": len(image_urls) > 1,
        "multi_store": len(stores) > 1,
        "multi_category": len(categories) > 1,
    }


def _confirmation_risk_flags(group: dict[str, Any], comparison: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if comparison.get("name_differs"):
        flags.append("name_differs")
    if comparison.get("image_url_differs"):
        flags.append("image_url_differs")
    if comparison.get("multi_store"):
        flags.append("multi_store_review")
    if comparison.get("multi_category"):
        flags.append("category_differs")
    flags.extend(str(flag) for flag in group.get("merge_blockers") or [])
    return sorted(set(flags))


def _manual_review_required_reasons(group: dict[str, Any]) -> list[str]:
    comparison = group.get("row_comparison_summary") or {}
    reasons = [
        "manual_keep_drop_confirmation_required",
        "same_sellable_product_identity_must_be_confirmed",
    ]
    if comparison.get("name_differs"):
        reasons.append("name_differs")
    if comparison.get("image_url_differs"):
        reasons.append("image_url_differs")
    if comparison.get("source_url_differs"):
        reasons.append("source_url_differs")
    if comparison.get("multi_store"):
        reasons.append("multi_store_variant_or_retailer_review")
    if comparison.get("multi_category"):
        reasons.append("category_differs")
    if group.get("ichiban_reissue_review"):
        reasons.append("ichiban_reissue_manual_confirmation_required")
    reasons.extend(str(reason) for reason in group.get("merge_blockers") or [])
    reasons.extend(str(flag) for flag in group.get("confirmation_risk_flags") or [])
    return sorted(set(reason for reason in reasons if reason))


def _compact_group(
    group: dict[str, Any],
    batch: dict[str, Any],
    *,
    reissue_review_index: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    comparison = _row_comparison_summary(group)
    compact = {
        "key_type": group.get("key_type"),
        "key": group.get("key"),
        "review_priority": group.get("review_priority"),
        "review_risk": group.get("review_risk"),
        "review_confidence": group.get("review_confidence"),
        "keep_catalog_index": group.get("keep_catalog_index"),
        "drop_catalog_indexes": group.get("drop_catalog_indexes") or [],
        "row_count": group.get("row_count"),
        "stores": group.get("stores") or [],
        "categories": group.get("categories") or [],
        "evidence": group.get("evidence") or [],
        "merge_blockers": group.get("merge_blockers") or [],
        "keep_basis": _keep_basis(group),
        "row_comparison_summary": comparison,
        "confirmation_risk_flags": _confirmation_risk_flags(group, comparison),
        "identity_checklist": group.get("identity_checklist") or batch.get("identity_checklist") or [],
        "recommended_action": group.get("recommended_action") or batch.get("recommended_action"),
        "dedupe_decision_template": group.get("dedupe_decision_template") or {},
        "manual_confirmation_template": CONFIRMED_TEMPLATE,
        "confirmed_queue": CONFIRMED_QUEUE,
        "import_tool": IMPORT_TOOL,
        "unblocks_when": UNBLOCKS_WHEN,
        "rows": group.get("rows") or [],
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }
    matched_reissue = []
    if reissue_review_index:
        for catalog_index in sorted(_catalog_indexes(group)):
            if catalog_index in reissue_review_index:
                matched_reissue.append({"catalog_index": catalog_index, **reissue_review_index[catalog_index]})
    if matched_reissue:
        reasons = sorted(
            {
                str(reason)
                for item in matched_reissue
                for reason in item.get("reissue_signal_reasons", [])
                if str(reason)
            }
        )
        compact["ichiban_reissue_review"] = True
        compact["ichiban_probable_reissue_review"] = any(
            bool(item.get("probable_reissue_review")) for item in matched_reissue
        )
        compact["ichiban_reissue_catalog_indexes"] = [item["catalog_index"] for item in matched_reissue]
        compact["ichiban_reissue_signal_reasons"] = reasons
        compact["ichiban_reissue_review_notes"] = matched_reissue
        compact["merge_blockers"] = sorted(
            set(compact["merge_blockers"]) | {"ichiban_reissue_manual_confirmation_required"}
        )
        compact["confirmation_risk_flags"] = sorted(
            set(compact["confirmation_risk_flags"]) | {"ichiban_reissue_manual_confirmation_required"}
        )
    compact["manual_review_required_reasons"] = _manual_review_required_reasons(compact)
    compact["auto_merge_blocked_reason"] = "explicit_manual_keep_drop_confirmation_required"
    compact["auto_delete_blocked_reason"] = "explicit_manual_keep_drop_confirmation_required"
    return compact


def build_report(
    review_batches: dict[str, Any],
    *,
    max_groups: int = 40,
    batch_size: int = 10,
    ichiban_policy_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actionable: list[dict[str, Any]] = []
    excluded = Counter()
    protected_indexes = protected_ichiban_reissue_catalog_indexes(ichiban_policy_audit)
    reissue_review_index = ichiban_reissue_review_index(ichiban_policy_audit)
    reissue_policy = ichiban_reissue_policy_summary(ichiban_policy_audit)
    reissue_lane = ichiban_reissue_review_lane(ichiban_policy_audit)
    reissue_work_orders = ichiban_reissue_work_order(reissue_lane)
    reissue_campaign_work_orders = ichiban_reissue_campaign_work_order(reissue_work_orders)
    protected_group_count = 0
    protected_row_indexes: set[int] = set()

    for batch in review_batches.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for group in batch.get("groups") or []:
            if not isinstance(group, dict):
                continue
            confidence = str(group.get("review_confidence") or "")
            if confidence not in ACTIONABLE_CONFIDENCES:
                excluded[confidence or "unknown"] += 1
                continue
            group_indexes = _catalog_indexes(group)
            matched_protected_indexes = group_indexes & protected_indexes
            if matched_protected_indexes:
                excluded["ichiban_reissue_protection"] += 1
                protected_group_count += 1
                protected_row_indexes.update(matched_protected_indexes)
                continue
            compact = _compact_group(group, batch, reissue_review_index=reissue_review_index)
            compact["queue_priority"] = CONFIDENCE_PRIORITY.get(confidence, 99)
            actionable.append(compact)

    actionable.sort(
        key=lambda group: (
            int(group.get("queue_priority") or 99),
            int(group.get("review_priority") or 99),
            str(group.get("key_type") or ""),
            str(group.get("key") or ""),
        )
    )
    published = actionable[:max_groups]
    unqueued_actionable_groups = max(len(actionable) - len(published), 0)
    queue_coverage = round(len(published) / len(actionable), 4) if actionable else 1.0
    merge_blocker_counts = _counter_from_values(
        [
            str(blocker)
            for group in actionable
            for blocker in group.get("merge_blockers", [])
        ]
    )
    confirmation_risk_counts = _counter_from_values(
        [
            str(flag)
            for group in actionable
            for flag in group.get("confirmation_risk_flags", [])
        ]
    )
    manual_reason_counts = _counter_from_values(
        [
            str(reason)
            for group in actionable
            for reason in group.get("manual_review_required_reasons", [])
        ]
    )
    manual_confirmed_reissue_rows = sum(
        1
        for order in reissue_work_orders
        if order.get("decision_template", {}).get("manual_confirmed") is True
    )
    completion_status = (
        "clear"
        if not actionable and not reissue_work_orders
        else "ichiban_reissue_review_required"
        if reissue_work_orders
        else "manual_keep_drop_confirmation_required"
    )
    completion_readiness = {
        "status": completion_status,
        "auto_merge_ready_groups": 0,
        "auto_delete_ready_groups": 0,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
        "manual_confirmed_groups": 0,
        "actionable_groups": len(actionable),
        "queued_groups": len(published),
        "unqueued_actionable_groups": unqueued_actionable_groups,
        "explicit_keep_drop_required_groups": len(actionable),
        "ichiban_reissue_review_groups": reissue_policy.get("ichiban_reissue_review_groups", 0),
        "ichiban_probable_reissue_review_groups": reissue_policy.get(
            "ichiban_probable_reissue_review_groups", 0
        ),
        "ichiban_reissue_work_order_rows": len(reissue_work_orders),
        "ichiban_reissue_manual_confirmed_rows": manual_confirmed_reissue_rows,
        "ichiban_reissue_protected_groups": protected_group_count,
        "blocked_reasons": [
            "explicit_manual_keep_drop_confirmation_required" if actionable else None,
            "ichiban_reissue_manual_confirmation_required" if reissue_work_orders else None,
            "variant_or_retailer_identity_review_required" if merge_blocker_counts else None,
        ],
        "next_safe_phase": (
            "verify_ichiban_campaign_pages_before_dedupe"
            if reissue_work_orders
            else "record_manual_keep_drop_decisions"
            if actionable
            else "no_dedupe_action_required"
        ),
        "safety_note": (
            "Duplicate evidence can represent retailer mirrors, variants, or reissues. "
            "No catalog row may be merged or deleted until an explicit manual keep/drop decision is recorded."
        ),
    }
    completion_readiness["blocked_reasons"] = [
        reason for reason in completion_readiness["blocked_reasons"] if reason
    ]

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(published), batch_size):
        groups = published[offset : offset + batch_size]
        batches.append(
            {
                "batch_id": f"dedupe-action-{len(batches) + 1:03d}",
                "priority": min(int(group.get("queue_priority") or 99) for group in groups),
                "group_count": len(groups),
                "offset": offset,
                "review_state": "explicit_keep_drop_confirmation_required",
                "next_machine_step": "record_manual_dedupe_decisions",
                "recommended_action": "Confirm same sellable product identity, then record manual keep/drop decisions.",
                "manual_confirmation_template": CONFIRMED_TEMPLATE,
                "confirmed_queue": CONFIRMED_QUEUE,
                "import_tool": IMPORT_TOOL,
                "unblocks_when": UNBLOCKS_WHEN,
                "review_confidence_counts": _counter_pairs(groups, "review_confidence"),
                "key_type_counts": _counter_pairs(groups, "key_type"),
                "review_risk_counts": _counter_pairs(groups, "review_risk"),
                "groups": groups,
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_deduplication_action_queue",
        "summary": {
            "actionable_groups": len(actionable),
            "queued_groups": len(published),
            "unqueued_actionable_groups": unqueued_actionable_groups,
            "queue_coverage": queue_coverage,
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "max_groups": max_groups,
            "by_review_confidence": _counter_pairs(actionable, "review_confidence"),
            "by_key_type": _counter_pairs(actionable, "key_type"),
            "by_merge_blocker": merge_blocker_counts,
            "by_confirmation_risk_flag": confirmation_risk_counts,
            "by_manual_review_required_reason": manual_reason_counts,
            "excluded_review_confidence": _counter_to_pairs(excluded),
            **reissue_policy,
            "ichiban_reissue_work_order_rows": len(reissue_work_orders),
            "ichiban_reissue_decision_template_rows": len(reissue_work_orders),
            "ichiban_reissue_campaign_work_order_rows": len(reissue_campaign_work_orders),
            "ichiban_reissue_campaign_decision_template_rows": len(reissue_campaign_work_orders),
            "ichiban_reissue_manual_confirmed_rows": manual_confirmed_reissue_rows,
            "ichiban_reissue_protected_groups": protected_group_count,
            "ichiban_reissue_protected_rows": len(protected_row_indexes),
            "completion_readiness_status": completion_status,
            "auto_merge_ready_groups": 0,
            "auto_delete_ready_groups": 0,
            "explicit_keep_drop_required_groups": len(actionable),
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        "completion_readiness": completion_readiness,
        "instructions": [
            "Use this queue for the safest dedupe reviews first; it still never deletes automatically.",
            "Variant caution and manual identity check groups remain in catalog_deduplication_review_batches_public.json.",
            "Ichiban Kuji probable reissue rows stay out of this queue until a human confirms they are true duplicates, not re-releases.",
            "Use ichiban_reissue_review_lane for same-name 1kuji campaign rows before any dedupe import.",
            "Use ichiban_reissue_work_order to record whether each repeated-name campaign group is a reissue/campaign variant or an exact duplicate.",
            "Use ichiban_reissue_campaign_work_order first when many item work orders share the same campaign URL pair.",
            "Every accepted group needs an explicit manual keep/drop decision before mutation.",
            f"Copy dedupe_decision_template rows into {CONFIRMED_QUEUE}, set manual_confirmed=true and decision=keep_drop_confirmed, then run {IMPORT_TOOL}.",
        ],
        "ichiban_reissue_review_lane": reissue_lane,
        "ichiban_reissue_campaign_work_order": reissue_campaign_work_orders,
        "ichiban_reissue_work_order": reissue_work_orders,
        "batches": batches,
        "automation_policy": {
            "auto_merge": False,
            "auto_delete": False,
            "requires_manual_review": True,
            "blocked_until": UNBLOCKS_WHEN,
            "default_blocked_reason": "explicit_manual_keep_drop_confirmation_required",
            "required_evidence": [
                "same_sellable_product_identity_confirmed",
                "keep_catalog_index_confirmed",
                "drop_catalog_indexes_confirmed",
                "evidence_urls_recorded",
                "manual_note_recorded",
            ],
            "protected_lanes": [
                "variant_caution",
                "manual_identity_check",
                "ichiban_probable_reissue_review",
            ],
            "manual_confirmation_template": CONFIRMED_TEMPLATE,
            "confirmed_queue": CONFIRMED_QUEUE,
            "import_tool": IMPORT_TOOL,
            "unblocks_when": UNBLOCKS_WHEN,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ichiban-policy-audit", type=Path, default=DEFAULT_ICHIBAN_POLICY_AUDIT)
    parser.add_argument("--max-groups", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    ichiban_policy_audit = _load(args.ichiban_policy_audit) if args.ichiban_policy_audit.exists() else None
    report = build_report(
        _load(args.input),
        max_groups=args.max_groups,
        batch_size=args.batch_size,
        ichiban_policy_audit=ichiban_policy_audit,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
