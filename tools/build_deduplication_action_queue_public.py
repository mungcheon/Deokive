from __future__ import annotations

import argparse
import json
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


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


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


def _compact_group(group: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    comparison = _row_comparison_summary(group)
    return {
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
            compact = _compact_group(group, batch)
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
            "excluded_review_confidence": _counter_to_pairs(excluded),
            "ichiban_reissue_protected_groups": protected_group_count,
            "ichiban_reissue_protected_rows": len(protected_row_indexes),
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        "instructions": [
            "Use this queue for the safest dedupe reviews first; it still never deletes automatically.",
            "Variant caution and manual identity check groups remain in catalog_deduplication_review_batches_public.json.",
            "Ichiban Kuji probable reissue rows stay out of this queue until a human confirms they are true duplicates, not re-releases.",
            "Every accepted group needs an explicit manual keep/drop decision before mutation.",
            f"Copy dedupe_decision_template rows into {CONFIRMED_QUEUE}, set manual_confirmed=true and decision=keep_drop_confirmed, then run {IMPORT_TOOL}.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_merge": False,
            "auto_delete": False,
            "requires_manual_review": True,
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
