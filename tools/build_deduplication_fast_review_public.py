from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "catalog_deduplication_action_queue_public.json"
OUTPUT = DATA / "catalog_deduplication_fast_review_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def iter_groups(action_queue: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for batch in action_queue.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for group in batch.get("groups") or []:
            if isinstance(group, dict):
                groups.append(group)
    return groups


def is_fast_review_group(group: dict[str, Any]) -> bool:
    return (
        group.get("review_confidence") == "high_review_confidence"
        and group.get("key_type") == "barcode"
        and bool(group.get("drop_catalog_indexes"))
    )


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "source_store": row.get("source_store"),
        "category": row.get("category"),
        "barcode": row.get("barcode"),
        "source_url": row.get("source_url"),
        "image_url": row.get("image_url"),
        "richness": row.get("richness"),
    }


def normalize_name(value: Any) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[\s/／・,\-_()（）\[\]【】]+", "", text)
    return text


def keep_reason(group: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    keep_index = group.get("keep_catalog_index")
    keep_row = next((row for row in rows if row.get("catalog_index") == keep_index), None)
    if not keep_row:
        return "preselected_keep_row_from_dedupe_review"
    keep_richness = int(keep_row.get("richness") or 0)
    max_richness = max((int(row.get("richness") or 0) for row in rows), default=keep_richness)
    if keep_richness >= max_richness:
        return "keeps_richest_catalog_row"
    return "keep_row_requires_manual_recheck"


def identity_delta(rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_names = sorted({normalize_name(row.get("name_ko")) for row in rows if row.get("name_ko")})
    source_urls = sorted({str(row.get("source_url") or "") for row in rows if row.get("source_url")})
    image_urls = sorted({str(row.get("image_url") or "") for row in rows if row.get("image_url")})
    stores = sorted({str(row.get("source_store") or "") for row in rows if row.get("source_store")})
    return {
        "normalized_name_count": len(normalized_names),
        "normalized_names": normalized_names[:8],
        "source_url_count": len(source_urls),
        "image_url_count": len(image_urls),
        "store_count": len(stores),
        "stores": stores,
        "name_differs": len(normalized_names) > 1,
        "source_url_differs": len(source_urls) > 1,
        "image_url_differs": len(image_urls) > 1,
    }


def fast_review_warning(delta: dict[str, Any]) -> str:
    if delta.get("name_differs"):
        return "name_delta_requires_variant_check"
    if delta.get("image_url_differs"):
        return "image_delta_requires_visual_check"
    return "no_identity_delta_detected"


def compact_group(group: dict[str, Any]) -> dict[str, Any]:
    rows = [compact_row(row) for row in group.get("rows") or [] if isinstance(row, dict)]
    evidence = group.get("evidence") or []
    same_barcode = "same_barcode" in evidence
    same_source_url = "same_source_url" in evidence
    same_image_url = "same_image_url" in evidence
    fast_review_lane = _fast_review_lane(same_barcode, same_source_url, same_image_url)
    decision_template = dict(group.get("dedupe_decision_template") or {})
    decision_template.update(
        {
            "manual_confirmed": False,
            "decision": "review_required",
            "fast_review_lane": fast_review_lane,
        }
    )
    delta = identity_delta(rows)
    warning = fast_review_warning(delta)
    return {
        "key_type": group.get("key_type"),
        "key": group.get("key"),
        "review_confidence": group.get("review_confidence"),
        "review_risk": group.get("review_risk"),
        "keep_catalog_index": group.get("keep_catalog_index"),
        "drop_catalog_indexes": group.get("drop_catalog_indexes") or [],
        "stores": group.get("stores") or [],
        "categories": group.get("categories") or [],
        "evidence": evidence,
        "merge_blockers": group.get("merge_blockers") or [],
        "same_barcode": same_barcode,
        "same_source_url": same_source_url,
        "same_image_url": same_image_url,
        "fast_review_lane": fast_review_lane,
        "fast_review_warning": warning,
        "keep_reason": keep_reason(group, rows),
        "identity_delta": delta,
        "dedupe_decision_template": decision_template,
        "rows": rows,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def counter_rows(counter: Counter[str], field: str) -> list[dict[str, Any]]:
    return [{field: key, "groups": value} for key, value in counter.most_common()]


def _fast_review_lane(same_barcode: bool, same_source_url: bool, same_image_url: bool) -> str:
    if same_barcode and same_source_url and same_image_url:
        return "same_barcode_source_and_image"
    if same_barcode and same_source_url:
        return "same_barcode_and_source_url"
    if same_barcode and same_image_url:
        return "same_barcode_and_image_url"
    if same_barcode:
        return "same_barcode_high_confidence"
    return "high_confidence_manual_review"


def build_report(action_queue: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    all_groups = iter_groups(action_queue)
    fast_groups = [compact_group(group) for group in all_groups if is_fast_review_group(group)]
    held_groups = [group for group in all_groups if not is_fast_review_group(group)]
    by_store = Counter()
    by_category = Counter()
    by_blocker = Counter()
    by_fast_review_lane = Counter()
    by_fast_review_warning = Counter()
    same_barcode_groups = 0
    same_source_url_groups = 0
    same_image_url_groups = 0
    name_delta_groups = 0
    image_delta_groups = 0
    for group in fast_groups:
        if group.get("same_barcode"):
            same_barcode_groups += 1
        if group.get("same_source_url"):
            same_source_url_groups += 1
        if group.get("same_image_url"):
            same_image_url_groups += 1
        delta = group.get("identity_delta") or {}
        if delta.get("name_differs"):
            name_delta_groups += 1
        if delta.get("image_url_differs"):
            image_delta_groups += 1
        by_fast_review_lane[str(group.get("fast_review_lane") or "unknown")] += 1
        by_fast_review_warning[str(group.get("fast_review_warning") or "unknown")] += 1
        for store in group.get("stores") or []:
            by_store[str(store)] += 1
        for category in group.get("categories") or []:
            by_category[str(category)] += 1
        blockers = group.get("merge_blockers") or ["none"]
        for blocker in blockers:
            by_blocker[str(blocker)] += 1

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_deduplication_fast_review",
        "summary": {
            "fast_review_groups": len(fast_groups),
            "held_for_later_groups": len(held_groups),
            "same_barcode_groups": same_barcode_groups,
            "same_source_url_groups": same_source_url_groups,
            "same_image_url_groups": same_image_url_groups,
            "name_delta_groups": name_delta_groups,
            "image_delta_groups": image_delta_groups,
            "variant_warning_groups": sum(
                1 for group in fast_groups if group.get("fast_review_warning") != "no_identity_delta_detected"
            ),
            "manual_confirmed_true": 0,
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        "breakdowns": {
            "by_fast_review_lane": counter_rows(by_fast_review_lane, "fast_review_lane"),
            "by_fast_review_warning": counter_rows(by_fast_review_warning, "fast_review_warning"),
            "by_source_store": counter_rows(by_store, "source_store"),
            "by_category": counter_rows(by_category, "category"),
            "by_merge_blocker": counter_rows(by_blocker, "merge_blocker"),
        },
        "items": fast_groups,
        "held_for_later_summary": {
            "by_review_confidence": counter_rows(
                Counter(str(group.get("review_confidence") or "") for group in held_groups),
                "review_confidence",
            ),
            "by_key_type": counter_rows(Counter(str(group.get("key_type") or "") for group in held_groups), "key_type"),
        },
        "automation_policy": {
            "auto_merge": False,
            "auto_delete": False,
            "requires_manual_review": True,
            "requires_same_sellable_product": True,
            "confirmed_queue": "server/catalog_dedupe_confirmed_decisions.json",
            "import_tool": "tools/import_confirmed_dedupe_decisions.py",
        },
    }


def write_report(report: dict[str, Any], path: Path = OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
