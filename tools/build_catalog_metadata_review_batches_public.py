from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_metadata_review_batches_public.json"

TRACKED_FIELDS = [
    "name_ja",
    "barcode",
    "release_date",
    "image_url",
    "source_url",
    "official_price_jpy",
]

FIELD_PRIORITY = {
    "source_url": 10,
    "image_url": 20,
    "release_date": 30,
    "official_price_jpy": 40,
    "barcode": 50,
    "name_ja": 60,
}

FIELD_POLICIES = {
    "source_url": {
        "workflow": "source_url_discovery",
        "evidence_required": "exact official or trusted licensed product detail page",
        "next_machine_step": "find_exact_official_product_source_url",
        "risk": "identity_mismatch",
    },
    "image_url": {
        "workflow": "source_then_image_import",
        "evidence_required": "product image from exact source_url after identity verification",
        "next_machine_step": "find_source_url_before_image_import",
        "risk": "wrong_product_image",
    },
    "release_date": {
        "workflow": "official_metadata_review",
        "evidence_required": "official product or campaign page showing release/sale date",
        "next_machine_step": "collect_official_metadata_evidence",
        "risk": "campaign_or_reissue_date_confusion",
    },
    "official_price_jpy": {
        "workflow": "official_metadata_review",
        "evidence_required": "official product or campaign page showing tax-inclusive or stated JPY price",
        "next_machine_step": "collect_official_metadata_evidence",
        "risk": "retailer_price_or_prize_price_confusion",
    },
    "barcode": {
        "workflow": "barcode_evidence_review",
        "evidence_required": "JAN/barcode from official listing or trusted retailer product detail",
        "next_machine_step": "collect_barcode_evidence",
        "risk": "shared_variant_or_box_barcode",
    },
    "name_ja": {
        "workflow": "official_title_review",
        "evidence_required": "original Japanese title from official or trusted listing",
        "next_machine_step": "collect_official_title_evidence",
        "risk": "translated_or_inferred_title",
    },
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path} must contain a JSON object with an items list")
    return [item for item in payload["items"] if isinstance(item, dict)]


def _sample_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "image_url": item.get("image_url"),
    }


def _recommended_action(field: str) -> str:
    return {
        "source_url": "Find exact product source URLs before image import.",
        "image_url": "Attach images only after source_url evidence is exact.",
        "release_date": "Verify official release/sale dates before importing.",
        "official_price_jpy": "Verify official stated JPY prices before importing.",
        "barcode": "Import JAN/barcodes only when directly shown by a trusted source.",
        "name_ja": "Verify original Japanese product titles from official listings.",
    }.get(field, "Review missing metadata with trusted evidence.")


def build_report(items: list[dict[str, Any]], *, batch_size: int = 12) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    field_totals: Counter[str] = Counter()
    store_totals: Counter[str] = Counter()
    for item in items:
        store = str(item.get("source_store") or "unknown")
        missing_fields = [field for field in TRACKED_FIELDS if not _present(item.get(field))]
        if missing_fields:
            store_totals[store] += 1
        for field in missing_fields:
            grouped[(field, store)].append(item)
            field_totals[field] += 1

    groups: list[dict[str, Any]] = []
    for (field, store), rows in grouped.items():
        policy = FIELD_POLICIES[field]
        groups.append(
            {
                "field": field,
                "source_store": store,
                "missing_rows": len(rows),
                "priority": FIELD_PRIORITY[field],
                "workflow": policy["workflow"],
                "evidence_required": policy["evidence_required"],
                "next_machine_step": policy["next_machine_step"],
                "risk": policy["risk"],
                "recommended_action": _recommended_action(field),
                "sample_catalog_indexes": [row.get("catalog_index") for row in rows[:8]],
                "sample_items": [_sample_item(row) for row in rows[:8]],
                "auto_apply_enabled": False,
            }
        )
    groups.sort(key=lambda row: (int(row["priority"]), -int(row["missing_rows"]), str(row["source_store"])))

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(groups), batch_size):
        batch_groups = groups[offset : offset + batch_size]
        fields = Counter(str(row.get("field") or "") for row in batch_groups)
        workflows = Counter(str(row.get("workflow") or "") for row in batch_groups)
        batches.append(
            {
                "batch_id": f"metadata-review-{len(batches) + 1:03d}",
                "priority": min(int(row["priority"]) for row in batch_groups),
                "group_count": len(batch_groups),
                "missing_cell_count": sum(int(row.get("missing_rows") or 0) for row in batch_groups),
                "field_counts": fields.most_common(),
                "workflow_counts": workflows.most_common(),
                "review_state": "metadata_evidence_required",
                "next_machine_step": "collect_official_metadata_evidence",
                "recommended_action": "Work field/store groups in priority order; prepare reviewed patches only from trusted evidence.",
                "groups": batch_groups,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "catalog_metadata_full_review_batches",
        "summary": {
            "catalog_rows": len(items),
            "tracked_fields": TRACKED_FIELDS,
            "field_store_group_count": len(groups),
            "batch_count": len(batches),
            "batch_size": batch_size,
            "missing_cell_count": sum(field_totals.values()),
            "field_missing_totals": dict(field_totals),
            "top_source_stores_with_missing_metadata": store_totals.most_common(40),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Review batches in priority order.",
            "This file groups all tracked public metadata gaps by field and source_store.",
            "Do not infer dates, prices, barcodes, images, source URLs, or original titles without trusted evidence.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_metadata": False,
            "requires_manual_review": True,
            "reason": "Metadata fields can affect identity, search, pricing, and historical accuracy.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=12)
    args = parser.parse_args()

    report = build_report(_load_items(args.input), batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
