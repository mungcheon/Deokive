from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_POLICY_AUDIT = DATA / "ichiban_kuji_prize_policy_audit_public.json"
DEFAULT_DEDUPE_ACTION_QUEUE = DATA / "catalog_deduplication_action_queue_public.json"
DEFAULT_OUTPUT = DATA / "ichiban_kuji_prize_policy_issue_queue_public.json"


LANE_BLOCKERS = {
    "zero_price_policy_violation": {
        "blocked_until": "last_one_or_double_chance_identity_confirmed",
        "blocked_reason": "zero_price_exception_identity_requires_confirmation",
        "required_evidence": [
            "prize_label_is_last_one_or_double_chance",
            "official_campaign_page_confirms_exception_prize",
            "manual_note_before_setting_price_to_zero",
        ],
    },
    "numbered_variant_gap_review": {
        "blocked_until": "official_variant_number_coverage_confirmed",
        "blocked_reason": "numbered_variant_sequence_gap_requires_official_lineup_review",
        "required_evidence": [
            "official_variant_count",
            "all_variant_numbers_or_missing_numbers_confirmed",
            "image_url_for_each_confirmed_variant",
        ],
    },
    "unnumbered_multi_item_prize_review": {
        "blocked_until": "official_prize_lineup_relationship_confirmed",
        "blocked_reason": "same_prize_label_has_multiple_unnumbered_rows",
        "required_evidence": [
            "official_campaign_page_prize_block",
            "decision_separate_prizes_selectable_variants_or_duplicate",
            "manual_note_for_keep_separate_or_split_or_dedupe",
        ],
    },
    "probable_reissue_or_campaign_variant_review": {
        "blocked_until": "campaign_reissue_or_exact_duplicate_decision_confirmed",
        "blocked_reason": "same_name_across_campaign_urls_may_be_reissue",
        "required_evidence": [
            "campaign_titles_compared",
            "release_periods_compared",
            "prize_lineups_compared",
            "manual_decision_keep_separate_or_keep_drop",
        ],
    },
}


def lane_blocker(lane: str) -> dict[str, Any]:
    return dict(
        LANE_BLOCKERS.get(
            lane,
            {
                "blocked_until": "manual_review_completed",
                "blocked_reason": "manual_review_required",
                "required_evidence": ["manual_confirmation"],
            },
        )
    )


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _rows_from_groups(groups: list[dict[str, Any]]) -> int:
    indexes: set[int] = set()
    fallback = 0
    for group in groups:
        rows = [row for row in group.get("sample_rows") or [] if isinstance(row, dict)]
        fallback += int(group.get("row_count") or len(rows))
        for row in rows:
            catalog_index = row.get("catalog_index")
            if isinstance(catalog_index, int):
                indexes.add(catalog_index)
    return len(indexes) if indexes else fallback


def _unique_sorted(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        if value in (None, ""):
            continue
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return sorted(result, key=lambda item: str(item))


def _compact_review_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in [
            "catalog_index",
            "name_ko",
            "name_ja",
            "series_name",
            "campaign_title",
            "sub_series",
            "prize_rank",
            "prize_item_name",
            "variant_name",
            "identity_label",
            "official_price_jpy",
            "source_url",
            "image_url",
            "local_image_path",
            "release_date",
        ]
        if row.get(key) not in (None, "")
    }


def _sample_row_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "catalog_indexes": _unique_sorted([row.get("catalog_index") for row in rows]),
        "source_urls": _unique_sorted([row.get("source_url") for row in rows]),
        "series_names": _unique_sorted([row.get("series_name") for row in rows]),
        "campaign_titles": _unique_sorted([row.get("campaign_title") or row.get("series_name") for row in rows]),
        "prize_labels": _unique_sorted([row.get("sub_series") for row in rows]),
        "prize_ranks": _unique_sorted([row.get("prize_rank") or row.get("sub_series") for row in rows]),
        "prize_item_names": _unique_sorted([row.get("prize_item_name") for row in rows]),
        "variant_names": _unique_sorted([row.get("variant_name") for row in rows]),
        "identity_labels": _unique_sorted([row.get("identity_label") for row in rows]),
        "display_names": _unique_sorted([row.get("name_ja") or row.get("name_ko") for row in rows]),
        "official_price_jpy_values": _unique_sorted(
            [row.get("official_price_jpy") for row in rows]
        ),
        "release_dates": _unique_sorted([row.get("release_date") for row in rows]),
        "rows_with_image_reference": sum(
            1
            for row in rows
            if row.get("image_url") not in (None, "") or row.get("local_image_path") not in (None, "")
        ),
    }


def _source_url_evidence_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        source_url = str(row.get("source_url") or "").strip()
        if not source_url:
            source_url = "(missing source_url)"
        by_source.setdefault(source_url, []).append(row)

    evidence: list[dict[str, Any]] = []
    for source_url, source_rows in sorted(by_source.items()):
        summary = _sample_row_summary(source_rows)
        evidence.append(
            {
                "source_url": source_url,
                "catalog_indexes": summary["catalog_indexes"],
                "series_names": summary["series_names"],
                "campaign_titles": summary["campaign_titles"],
                "prize_labels": summary["prize_labels"],
                "prize_ranks": summary["prize_ranks"],
                "prize_item_names": summary["prize_item_names"],
                "variant_names": summary["variant_names"],
                "identity_labels": summary["identity_labels"],
                "display_names": summary["display_names"],
                "official_price_jpy_values": summary["official_price_jpy_values"],
                "release_dates": summary["release_dates"],
                "rows_with_image_reference": summary["rows_with_image_reference"],
                "row_count": len(source_rows),
            }
        )
    return evidence


def _compact_group(group: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in group.get("sample_rows") or [] if isinstance(row, dict)]
    return {
        "source_url": group.get("source_url"),
        "sub_series": group.get("sub_series"),
        "row_count": group.get("row_count"),
        "review_lane": group.get("review_lane"),
        "variant_summary": group.get("variant_summary") or {},
        "identity_summary": _sample_row_summary(rows),
        "source_url_evidence_rows": _source_url_evidence_rows(rows),
        "sample_rows": [_compact_review_row(row) for row in rows],
    }


def _manual_multi_item_groups(policy_audit: dict[str, Any]) -> list[dict[str, Any]]:
    groups = [
        group
        for group in policy_audit.get("multi_item_prize_label_groups") or []
        if isinstance(group, dict) and group.get("review_lane") == "unnumbered_multi_item_prize_review"
    ]
    if groups:
        return groups

    batch_groups: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for batch in policy_audit.get("review_batches") or []:
        if not isinstance(batch, dict) or batch.get("workflow") != "multi_item_prize_label_review":
            continue
        for group in batch.get("groups") or []:
            if not isinstance(group, dict):
                continue
            key = (str(group.get("source_url") or ""), str(group.get("sub_series") or ""))
            if key in seen:
                continue
            seen.add(key)
            batch_groups.append(group)
    return batch_groups


BRACKETED_LIMITED_LABEL_PATTERN = re.compile(r"【([^】]+)】")
VOL_VARIANT_PATTERN = re.compile(r"\bvol\.\s*\d+\b", re.IGNORECASE)
CIRCLED_NUMBER_PATTERN = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")
RELATED_GOODS_PREFIXES = (
    "菓子商品",
    "玩具菓子",
)


def _display_name(row: dict[str, Any]) -> str:
    return str(row.get("name_ja") or row.get("name_ko") or "").strip()


def _suffixes_from(pattern: re.Pattern[str], names: list[str]) -> list[str]:
    result: list[str] = []
    for name in names:
        match = pattern.search(name)
        result.append(match.group(0) if match else "")
    return result


def _unique_nonempty(values: list[str]) -> bool:
    cleaned = [value.strip() for value in values if value.strip()]
    return len(cleaned) == len(values) and len(set(cleaned)) == len(values)


def _already_distinct_parallel_prize_group(group: dict[str, Any]) -> bool:
    rows = [row for row in group.get("sample_rows") or [] if isinstance(row, dict)]
    if len(rows) < 2:
        return False

    names = [_display_name(row) for row in rows]
    if not _unique_nonempty(names):
        return False

    bracket_labels = []
    for name in names:
        labels = BRACKETED_LIMITED_LABEL_PATTERN.findall(name)
        bracket_labels.append(labels[-1] if labels else "")
    if _unique_nonempty(bracket_labels):
        return True

    circled_labels = _suffixes_from(CIRCLED_NUMBER_PATTERN, names)
    if _unique_nonempty(circled_labels):
        return True

    vol_labels = _suffixes_from(VOL_VARIANT_PATTERN, names)
    if _unique_nonempty(vol_labels):
        return True

    if str(group.get("sub_series") or "").strip() == "関連商品":
        prefixes = []
        for name in names:
            prefix = next((token for token in RELATED_GOODS_PREFIXES if name.startswith(token)), "")
            prefixes.append(prefix)
        if _unique_nonempty(prefixes):
            return True

    return False


def _parallel_prize_protection_reason(group: dict[str, Any]) -> str:
    rows = [row for row in group.get("sample_rows") or [] if isinstance(row, dict)]
    names = [_display_name(row) for row in rows]

    bracket_labels = []
    for name in names:
        labels = BRACKETED_LIMITED_LABEL_PATTERN.findall(name)
        bracket_labels.append(labels[-1] if labels else "")
    if _unique_nonempty(bracket_labels):
        return "distinct_limited_shop_or_channel_labels"

    circled_labels = _suffixes_from(CIRCLED_NUMBER_PATTERN, names)
    if _unique_nonempty(circled_labels):
        return "distinct_circled_number_labels"

    vol_labels = _suffixes_from(VOL_VARIANT_PATTERN, names)
    if _unique_nonempty(vol_labels):
        return "distinct_volume_labels"

    if str(group.get("sub_series") or "").strip() == "関連商品":
        prefixes = []
        for name in names:
            prefix = next((token for token in RELATED_GOODS_PREFIXES if name.startswith(token)), "")
            prefixes.append(prefix)
        if _unique_nonempty(prefixes):
            return "distinct_related_goods_prefixes"

    return "distinct_parallel_prize_names"


def _protected_parallel_prize_group(group: dict[str, Any]) -> dict[str, Any]:
    compact = _compact_group(group)
    compact.update(
        {
            "review_state": "protected_already_distinct_parallel_prizes",
            "protection_reason": _parallel_prize_protection_reason(group),
            "recommended_action": "Keep rows separate unless an official campaign comparison later proves they are accidental duplicates.",
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        }
    )
    return compact


def _split_manual_multi_item_groups(
    groups: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    review_groups: list[dict[str, Any]] = []
    protected_groups: list[dict[str, Any]] = []
    for group in groups:
        if _already_distinct_parallel_prize_group(group):
            protected_groups.append(group)
        else:
            review_groups.append(group)
    return review_groups, protected_groups


def _price_issue(
    *,
    issue_id: str,
    priority: int,
    title: str,
    rows: list[dict[str, Any]],
    review_reason: str,
) -> dict[str, Any]:
    return {
        "issue_id": issue_id,
        "priority": priority,
        "lane": "zero_price_policy_violation",
        "title": title,
        "open_rows": len(rows),
        "review_state": "manual_price_policy_fix_required",
        "review_reason": review_reason,
        "recommended_action": "Set official_price_jpy to 0 only after confirming the row is a Last One or Double Chance prize.",
        "items": rows,
        "manual_confirmed": False,
        "auto_apply_enabled": False,
        **lane_blocker("zero_price_policy_violation"),
    }


def _reissue_work_order(row: dict[str, Any], rank: int) -> dict[str, Any]:
    sample_rows = [item for item in row.get("sample_rows") or [] if isinstance(item, dict)]
    decision_template = row.get("decision_template") or {}
    return {
        "issue_id": f"ichiban-reissue-review-{rank:03d}",
        "priority": 300 + rank,
        "lane": "probable_reissue_or_campaign_variant_review",
        "title": row.get("normalized_name"),
        "open_rows": len(row.get("catalog_indexes") or []),
        "review_state": row.get("review_state") or "ichiban_reissue_identity_confirmation_required",
        "review_reason": "Same displayed item appears under multiple 1kuji campaign URLs; protect as possible reissue until manually confirmed.",
        "recommended_action": "Compare campaign title, release period, and prize lineup before deciding keep-separate or keep/drop.",
        "work_order_id": row.get("work_order_id"),
        "campaign_work_order_id": row.get("campaign_work_order_id"),
        "catalog_indexes": row.get("catalog_indexes") or [],
        "source_urls": row.get("source_urls") or [],
        "first_evidence_url": row.get("first_evidence_url") or _first_url(row.get("source_urls") or []),
        "evidence_url_count": row.get("evidence_url_count")
        or sum(1 for url in row.get("source_urls") or [] if str(url or "").strip()),
        "source_url_count": row.get("source_url_count"),
        "campaign_slug_families": row.get("campaign_slug_families") or [],
        "campaign_url_comparison": row.get("campaign_url_comparison") or {},
        "reissue_signal_reasons": row.get("reissue_signal_reasons") or [],
        "manual_review_checklist": row.get("manual_review_checklist") or [],
        "decision_options": decision_template.get("decision_options") or [],
        "decision_template": decision_template,
        "prize_identity_summary": row.get("prize_identity_summary") or {},
        "zero_price_exception_policy": row.get("zero_price_exception_policy") or {},
        "source_url_evidence_rows": _source_url_evidence_rows(sample_rows),
        "sample_rows": [_compact_review_row(item) for item in sample_rows],
        "merge_blockers": row.get("merge_blockers") or ["ichiban_reissue_manual_confirmation_required"],
        "manual_confirmed": False,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
        **lane_blocker("probable_reissue_or_campaign_variant_review"),
    }


def _first_url(urls: Any) -> str:
    if not isinstance(urls, list):
        return ""
    for url in urls:
        text = str(url or "").strip()
        if text:
            return text
    return ""


def _campaign_first_review_plan(dedupe_action_queue: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in dedupe_action_queue.get("ichiban_reissue_campaign_work_order") or []
        if isinstance(row, dict)
    ]
    plan: list[dict[str, Any]] = []
    for rank, row in enumerate(rows, start=1):
        decision_template = row.get("decision_template") if isinstance(row.get("decision_template"), dict) else {}
        source_urls = row.get("source_urls") or []
        plan.append(
            {
                "rank": rank,
                "campaign_work_order_id": row.get("campaign_work_order_id"),
                "priority": 250 + rank,
                "lane": "campaign_pair_reissue_or_duplicate_review",
                "review_state": row.get("review_state") or "campaign_pair_reissue_or_duplicate_decision_required",
                "source_urls": source_urls,
                "first_evidence_url": row.get("first_evidence_url") or _first_url(source_urls),
                "evidence_url_count": row.get("evidence_url_count")
                or sum(1 for url in source_urls if str(url or "").strip()),
                "campaign_url_comparison": row.get("campaign_url_comparison") or {},
                "item_work_order_count": row.get("item_work_order_count") or 0,
                "affected_item_work_order_ids": decision_template.get("affected_item_work_order_ids")
                or row.get("item_work_order_ids")
                or [],
                "catalog_indexes": row.get("catalog_indexes") or [],
                "prize_labels": row.get("prize_labels") or [],
                "decision_options": decision_template.get("decision_options") or [],
                "decision_template": decision_template,
                "recommended_action": "Decide whether this campaign URL pair is a reissue/wave or exact duplicate before item-level keep/drop review.",
                "manual_review_checklist": row.get("manual_review_checklist") or [],
                "manual_confirmed": False,
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
                **lane_blocker("probable_reissue_or_campaign_variant_review"),
            }
        )
    return plan


def _completion_readiness(
    *,
    issue_count: int,
    open_issue_rows: int,
    zero_price_violation_rows: int,
    zero_price_exception_policy_pass: bool,
    numbered_variant_coverage_policy_pass: bool,
    unnumbered_multi_item_prize_review_groups: int,
    unnumbered_multi_item_prize_review_rows: int,
    protected_unnumbered_multi_item_prize_groups: int,
    protected_unnumbered_multi_item_prize_rows: int,
    probable_reissue_work_order_rows: int,
    probable_reissue_review_groups: int,
    repeated_name_different_source_groups: int,
) -> dict[str, Any]:
    zero_price_policy_ready = (
        zero_price_exception_policy_pass is True and zero_price_violation_rows == 0
    )
    numbered_variant_policy_ready = numbered_variant_coverage_policy_pass is True

    blocked_reasons: list[str] = []
    next_safe_phase = "archive_prize_policy_completion"
    status = "no_open_policy_issues"

    if not zero_price_policy_ready:
        status = "zero_price_policy_fix_required"
        next_safe_phase = "fix_last_one_double_chance_zero_price_policy"
        blocked_reasons.append("last_one_or_double_chance_zero_price_policy_not_clean")
    if not numbered_variant_policy_ready:
        if status == "no_open_policy_issues":
            status = "numbered_variant_review_required"
            next_safe_phase = "verify_numbered_same_rank_variants"
        blocked_reasons.append("numbered_same_rank_variant_coverage_not_clean")
    if unnumbered_multi_item_prize_review_groups:
        if status == "no_open_policy_issues":
            status = "unnumbered_multi_item_prize_review_required"
            next_safe_phase = "verify_unnumbered_same_rank_prize_relationship"
        blocked_reasons.append("unnumbered_same_rank_prize_groups_require_lineup_review")
    if probable_reissue_work_order_rows or probable_reissue_review_groups:
        if status == "no_open_policy_issues":
            status = "ichiban_reissue_review_required"
            next_safe_phase = "verify_ichiban_campaign_pages_before_dedupe"
        blocked_reasons.append("same_name_across_campaign_urls_requires_keep_or_merge_decision")

    if not blocked_reasons:
        blocked_reasons.append("none")

    return {
        "status": status,
        "zero_price_policy_ready": zero_price_policy_ready,
        "numbered_variant_policy_ready": numbered_variant_policy_ready,
        "same_rank_unnumbered_policy_ready": unnumbered_multi_item_prize_review_groups == 0,
        "reissue_identity_policy_ready": probable_reissue_work_order_rows == 0
        and probable_reissue_review_groups == 0,
        "issue_rows": issue_count,
        "open_issue_rows": open_issue_rows,
        "manual_review_rows": open_issue_rows,
        "auto_apply_ready_rows": 0,
        "zero_price_violation_rows": zero_price_violation_rows,
        "unnumbered_multi_item_prize_review_groups": unnumbered_multi_item_prize_review_groups,
        "unnumbered_multi_item_prize_review_rows": unnumbered_multi_item_prize_review_rows,
        "protected_unnumbered_multi_item_prize_groups": protected_unnumbered_multi_item_prize_groups,
        "protected_unnumbered_multi_item_prize_rows": protected_unnumbered_multi_item_prize_rows,
        "probable_reissue_work_order_rows": probable_reissue_work_order_rows,
        "probable_reissue_review_groups": probable_reissue_review_groups,
        "repeated_name_different_source_groups": repeated_name_different_source_groups,
        "blocked_reasons": blocked_reasons,
        "next_safe_phase": next_safe_phase,
        "auto_apply_enabled": False,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
        "safety_note": (
            "Last One and Double Chance zero-price rows are policy exceptions; "
            "same-name Ichiban Kuji rows across campaign URLs must not be merged "
            "until official campaign evidence confirms the identity decision."
        ),
    }


def build_queue(
    policy_audit: dict[str, Any],
    dedupe_action_queue: dict[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or now_utc()
    summary = policy_audit.get("summary") if isinstance(policy_audit.get("summary"), dict) else {}
    dedupe_action_queue = dedupe_action_queue or {}
    dedupe_summary = (
        dedupe_action_queue.get("summary")
        if isinstance(dedupe_action_queue.get("summary"), dict)
        else {}
    )

    issues: list[dict[str, Any]] = []
    last_one_violations = [
        row for row in policy_audit.get("last_one_price_violations") or [] if isinstance(row, dict)
    ]
    double_chance_violations = [
        row for row in policy_audit.get("double_chance_price_violations") or [] if isinstance(row, dict)
    ]
    if last_one_violations:
        issues.append(
            _price_issue(
                issue_id="ichiban-last-one-price-policy",
                priority=10,
                title="Last One prize price must be 0 JPY",
                rows=last_one_violations,
                review_reason="Last One prize rows should not carry the regular ticket price.",
            )
        )
    if double_chance_violations:
        issues.append(
            _price_issue(
                issue_id="ichiban-double-chance-price-policy",
                priority=20,
                title="Double Chance prize price must be 0 JPY",
                rows=double_chance_violations,
                review_reason="Double Chance campaign prize rows should not carry the regular ticket price.",
            )
        )

    incomplete_numbered = [
        group
        for group in policy_audit.get("incomplete_numbered_variant_prize_label_groups") or []
        if isinstance(group, dict)
    ]
    if incomplete_numbered:
        issues.append(
            {
                "issue_id": "ichiban-numbered-variant-gap-review",
                "priority": 100,
                "lane": "numbered_variant_gap_review",
                "title": "Numbered variant coverage has missing variant numbers",
                "open_groups": len(incomplete_numbered),
                "open_rows": _rows_from_groups(incomplete_numbered),
                "review_state": "manual_official_campaign_prize_confirmation_required",
                "recommended_action": "Open the official campaign page and add or fix missing numbered variants.",
                "groups": [_compact_group(group) for group in incomplete_numbered],
                "manual_confirmed": False,
                "auto_apply_enabled": False,
                **lane_blocker("numbered_variant_gap_review"),
            }
        )

    raw_unnumbered_multi = _manual_multi_item_groups(policy_audit)
    unnumbered_multi, protected_unnumbered_multi = _split_manual_multi_item_groups(
        raw_unnumbered_multi
    )
    if unnumbered_multi:
        issues.append(
            {
                "issue_id": "ichiban-unnumbered-multi-item-prize-review",
                "priority": 200,
                "lane": "unnumbered_multi_item_prize_review",
                "title": "Same prize label has multiple unnumbered catalog rows",
                "open_groups": len(unnumbered_multi),
                "open_rows": _rows_from_groups(unnumbered_multi),
                "review_state": "manual_official_campaign_prize_confirmation_required",
                "recommended_action": "Confirm whether rows are separate listed prizes, selectable variants, or accidental duplicates.",
                "groups": [_compact_group(group) for group in unnumbered_multi],
                "manual_confirmed": False,
                "auto_apply_enabled": False,
                **lane_blocker("unnumbered_multi_item_prize_review"),
            }
        )

    reissue_work_orders = [
        row for row in dedupe_action_queue.get("ichiban_reissue_work_order") or [] if isinstance(row, dict)
    ]
    campaign_first_review_plan = _campaign_first_review_plan(dedupe_action_queue)
    for rank, row in enumerate(reissue_work_orders, start=1):
        issues.append(_reissue_work_order(row, rank))

    lane_counts = Counter(str(issue.get("lane") or "") for issue in issues)
    lane_counts.pop("", None)
    blocked_reason_counts = Counter(str(issue.get("blocked_reason") or "") for issue in issues)
    blocked_reason_counts.pop("", None)
    blocked_until_counts = Counter(str(issue.get("blocked_until") or "") for issue in issues)
    blocked_until_counts.pop("", None)
    open_issue_rows = sum(int(issue.get("open_rows") or 0) for issue in issues)
    protected_groups = [_protected_parallel_prize_group(group) for group in protected_unnumbered_multi]
    protected_reason_counts = Counter(
        str(group.get("protection_reason") or "unknown") for group in protected_groups
    )
    zero_price_violation_rows = int(summary.get("zero_price_violation_rows") or 0)
    zero_price_exception_policy_pass = bool(summary.get("zero_price_exception_policy_pass"))
    numbered_variant_coverage_policy_pass = bool(
        summary.get("numbered_variant_coverage_policy_pass")
    )
    unnumbered_multi_item_prize_review_groups = len(unnumbered_multi)
    unnumbered_multi_item_prize_review_rows = _rows_from_groups(unnumbered_multi)
    protected_unnumbered_multi_item_prize_groups = len(protected_unnumbered_multi)
    protected_unnumbered_multi_item_prize_rows = _rows_from_groups(
        protected_unnumbered_multi
    )
    probable_reissue_work_order_rows = len(reissue_work_orders)
    campaign_first_review_plan_rows = len(campaign_first_review_plan)
    probable_reissue_review_groups = int(
        dedupe_summary.get("ichiban_probable_reissue_review_groups")
        or summary.get("probable_reissue_review_groups")
        or 0
    )
    repeated_name_different_source_groups = int(
        summary.get("repeated_name_different_source_groups") or 0
    )
    completion_readiness = _completion_readiness(
        issue_count=len(issues),
        open_issue_rows=open_issue_rows,
        zero_price_violation_rows=zero_price_violation_rows,
        zero_price_exception_policy_pass=zero_price_exception_policy_pass,
        numbered_variant_coverage_policy_pass=numbered_variant_coverage_policy_pass,
        unnumbered_multi_item_prize_review_groups=unnumbered_multi_item_prize_review_groups,
        unnumbered_multi_item_prize_review_rows=unnumbered_multi_item_prize_review_rows,
        protected_unnumbered_multi_item_prize_groups=protected_unnumbered_multi_item_prize_groups,
        protected_unnumbered_multi_item_prize_rows=protected_unnumbered_multi_item_prize_rows,
        probable_reissue_work_order_rows=probable_reissue_work_order_rows,
        probable_reissue_review_groups=probable_reissue_review_groups,
        repeated_name_different_source_groups=repeated_name_different_source_groups,
    )

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "public_catalog_ichiban_kuji_prize_policy",
        "summary": {
            "issue_rows": len(issues),
            "open_issue_rows": open_issue_rows,
            "zero_price_violation_rows": zero_price_violation_rows,
            "last_one_nonzero_price_rows": int(summary.get("last_one_nonzero_price_rows") or 0),
            "double_chance_nonzero_price_rows": int(summary.get("double_chance_nonzero_price_rows") or 0),
            "zero_price_exception_policy_pass": zero_price_exception_policy_pass,
            "numbered_variant_coverage_policy_pass": numbered_variant_coverage_policy_pass,
            "numbered_variant_created_rows": int(summary.get("numbered_variant_created_rows") or 0),
            "numbered_variant_application_skipped_rows": int(
                summary.get("numbered_variant_application_skipped_rows") or 0
            ),
            "unnumbered_multi_item_prize_review_groups": unnumbered_multi_item_prize_review_groups,
            "unnumbered_multi_item_prize_review_rows": unnumbered_multi_item_prize_review_rows,
            "protected_unnumbered_multi_item_prize_groups": protected_unnumbered_multi_item_prize_groups,
            "protected_unnumbered_multi_item_prize_rows": protected_unnumbered_multi_item_prize_rows,
            "protected_unnumbered_multi_item_prize_reason_counts": [
                [reason, count] for reason, count in protected_reason_counts.most_common()
            ],
            "probable_reissue_work_order_rows": probable_reissue_work_order_rows,
            "campaign_first_review_plan_rows": campaign_first_review_plan_rows,
            "campaign_first_review_item_work_order_rows": sum(
                int(row.get("item_work_order_count") or 0)
                for row in campaign_first_review_plan
            ),
            "campaign_first_review_plans_with_evidence_urls": sum(
                1 for row in campaign_first_review_plan if row.get("first_evidence_url")
            ),
            "campaign_first_review_first_evidence_url": _first_url(
                [row.get("first_evidence_url") for row in campaign_first_review_plan]
            ),
            "probable_reissue_review_groups": probable_reissue_review_groups,
            "probable_reissue_sample_rows": int(
                dedupe_summary.get("ichiban_probable_reissue_sample_rows") or 0
            ),
            "repeated_name_different_source_groups": repeated_name_different_source_groups,
            "manual_confirmed_rows": 0,
            "manual_review_rows": open_issue_rows,
            "auto_apply_ready_rows": 0,
            "completion_readiness_status": completion_readiness["status"],
            "lane_counts": [[lane, count] for lane, count in lane_counts.most_common()],
            "by_blocked_reason": [
                [reason, count] for reason, count in blocked_reason_counts.most_common()
            ],
            "by_blocked_until": [
                [reason, count] for reason, count in blocked_until_counts.most_common()
            ],
            "auto_apply_enabled": False,
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        "policy_status": {
            "last_one_and_double_chance_prices": (
                "pass" if zero_price_exception_policy_pass else "manual_fix_required"
            ),
            "numbered_variants": (
                "pass" if numbered_variant_coverage_policy_pass else "manual_review"
            ),
            "probable_reissues": "manual_review" if reissue_work_orders else "clear",
            "unnumbered_multi_item_prizes": "manual_review" if unnumbered_multi else "clear",
        },
        "completion_readiness": completion_readiness,
        "protected_unnumbered_multi_item_prize_groups": protected_groups,
        "campaign_first_review_plan": campaign_first_review_plan,
        "issues": sorted(issues, key=lambda row: int(row.get("priority") or 9999)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-audit", type=Path, default=DEFAULT_POLICY_AUDIT)
    parser.add_argument("--dedupe-action-queue", type=Path, default=DEFAULT_DEDUPE_ACTION_QUEUE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    policy_audit = load_json(args.policy_audit)
    dedupe_action_queue = load_json(args.dedupe_action_queue) if args.dedupe_action_queue.exists() else {}
    report = build_queue(policy_audit, dedupe_action_queue)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), **report["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
