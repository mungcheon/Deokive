from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_deduplication_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_deduplication_review_batches_public.json"

RISK_PRIORITY = {
    "strong_identity_review": 10,
    "source_identity_review": 20,
    "image_identity_review": 30,
    "variant_risk_review": 40,
    "manual_identity_review": 50,
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_groups(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    groups = payload.get("items") or payload.get("groups")
    if not isinstance(groups, list):
        raise ValueError(f"{path} must contain an items/groups list")
    return payload, [group for group in groups if isinstance(group, dict)]


def _name_tokens(value: Any) -> set[str]:
    text = str(value or "").lower()
    for char in "/_-・()（）[]【】.,:;　":
        text = text.replace(char, " ")
    return {token for token in text.split() if len(token) >= 2}


def _shared_name_token_ratio(rows: list[dict[str, Any]]) -> float:
    token_sets = []
    for row in rows:
        tokens = _name_tokens(row.get("name_ja") or row.get("name_ko"))
        if tokens:
            token_sets.append(tokens)
    if len(token_sets) < 2:
        return 0.0
    shared = set.intersection(*token_sets)
    union = set.union(*token_sets)
    return round(len(shared) / len(union), 4) if union else 0.0


def _review_confidence(group: dict[str, Any]) -> str:
    key_type = str(group.get("key_type") or "")
    risk = str(group.get("review_risk") or "")
    rows = [row for row in group.get("rows") or [] if isinstance(row, dict)]
    stores = {str(row.get("source_store") or "") for row in rows}
    categories = {str(row.get("category") or "") for row in rows}
    shared_name_ratio = _shared_name_token_ratio(rows)
    if key_type == "barcode" and risk == "strong_identity_review" and len(categories) <= 1 and shared_name_ratio >= 0.35:
        return "high_review_confidence"
    if key_type in {"source_url", "image_url"} and len(stores) <= 2 and shared_name_ratio >= 0.25:
        return "medium_review_confidence"
    if len(categories) > 1 or risk == "variant_risk_review":
        return "variant_caution"
    return "manual_identity_check"


def _group_sort_key(group: dict[str, Any]) -> tuple[int, int, str, str]:
    return (
        int(group.get("review_priority") or RISK_PRIORITY.get(str(group.get("review_risk") or ""), 99)),
        RISK_PRIORITY.get(str(group.get("review_risk") or ""), 99),
        str(group.get("key_type") or ""),
        str(group.get("key") or ""),
    )


def _compact_group(group: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in group.get("rows") or [] if isinstance(row, dict)]
    stores = sorted({str(row.get("source_store") or "") for row in rows if row.get("source_store")})
    categories = sorted({str(row.get("category") or "") for row in rows if row.get("category")})
    confidence = _review_confidence(group)
    return {
        "key_type": group.get("key_type"),
        "key": group.get("key"),
        "review_priority": group.get("review_priority"),
        "review_risk": group.get("review_risk"),
        "review_confidence": confidence,
        "keep_catalog_index": group.get("keep_catalog_index"),
        "drop_catalog_indexes": group.get("drop_catalog_indexes") or [],
        "row_count": len(rows),
        "stores": stores,
        "categories": categories,
        "shared_name_token_ratio": _shared_name_token_ratio(rows),
        "evidence": group.get("evidence") or [],
        "recommended_action": _recommended_action(group, confidence),
        "rows": rows,
    }


def _recommended_action(group: dict[str, Any], confidence: str) -> str:
    if confidence == "high_review_confidence":
        return "Review images and names, then record a manual keep/drop decision; auto-delete remains disabled."
    if confidence == "variant_caution":
        return "Preserve as separate variants unless source evidence proves the rows are the same sellable product."
    if str(group.get("key_type") or "") == "image_url":
        return "Check whether the shared image is a lineup or placeholder before merging anything."
    if str(group.get("key_type") or "") == "source_url":
        return "Check whether the shared source page contains variants before merging anything."
    return "Compare product identity manually before any catalog patch."


def build_report(groups: list[dict[str, Any]], *, batch_size: int = 12) -> dict[str, Any]:
    compact_groups = [_compact_group(group) for group in sorted(groups, key=_group_sort_key)]
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(compact_groups), batch_size):
        batch_groups = compact_groups[offset : offset + batch_size]
        risk_counts = Counter(str(group.get("review_risk") or "") for group in batch_groups)
        confidence_counts = Counter(str(group.get("review_confidence") or "") for group in batch_groups)
        key_type_counts = Counter(str(group.get("key_type") or "") for group in batch_groups)
        batches.append(
            {
                "batch_id": f"dedupe-review-{len(batches) + 1:03d}",
                "priority": min(int(group.get("review_priority") or 99) for group in batch_groups),
                "group_count": len(batch_groups),
                "review_risk_counts": risk_counts.most_common(),
                "review_confidence_counts": confidence_counts.most_common(),
                "key_type_counts": key_type_counts.most_common(),
                "recommended_action": "Review every group manually and write explicit keep/drop decisions before any catalog mutation.",
                "groups": batch_groups,
            }
        )

    risk_counts = Counter(str(group.get("review_risk") or "") for group in compact_groups)
    confidence_counts = Counter(str(group.get("review_confidence") or "") for group in compact_groups)
    key_type_counts = Counter(str(group.get("key_type") or "") for group in compact_groups)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_public_deduplication_review_batches",
        "summary": {
            "source_groups": len(groups),
            "batch_count": len(batches),
            "batch_size": batch_size,
            "by_review_risk": risk_counts.most_common(),
            "by_review_confidence": confidence_counts.most_common(),
            "by_key_type": key_type_counts.most_common(),
            "auto_delete_enabled": False,
        },
        "batches": batches,
        "automation_policy": {
            "auto_delete": False,
            "auto_merge": False,
            "requires_manual_review": True,
            "reason": "Shared barcode/source/image evidence can represent reissues, variants, or retailer duplicates.",
        },
        "instructions": [
            "Review batches in priority order.",
            "A suggested drop row is not a deletion command.",
            "Keep/drop decisions should be recorded in a separate confirmed queue before mutating catalog data.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=12)
    args = parser.parse_args()

    _, groups = _load_groups(args.input)
    report = build_report(groups, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
