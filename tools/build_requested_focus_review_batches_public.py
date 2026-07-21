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
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REQUESTED = ROOT / "data" / "requested_special_goods_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "requested_focus_review_batches_public.json"

TRACKED_FIELDS = [
    "source_url",
    "image_url",
    "release_date",
    "official_price_jpy",
    "barcode",
    "name_ja",
]

FIELD_PRIORITY = {
    "source_url": 10,
    "image_url": 20,
    "release_date": 30,
    "official_price_jpy": 40,
    "barcode": 70,
    "name_ja": 80,
}

TOPICS = [
    {
        "topic_id": "requested_special_goods",
        "label": "사용자 요청 특별 리스트",
        "priority": 10,
        "terms": [],
        "reason": "User explicitly requested these special goods; keep them visible even when present.",
    },
    {
        "topic_id": "danganronpa",
        "label": "단간론파 굿즈",
        "priority": 20,
        "terms": ["단간론파", "ダンガンロンパ", "Danganronpa"],
        "reason": "Repeatedly requested, including nui and Bukubu-style goods.",
    },
    {
        "topic_id": "ichiban_kuji",
        "label": "이치방쿠지 굿즈",
        "priority": 30,
        "terms": ["이치방쿠지", "一番くじ", "1kuji"],
        "reason": "Large historical campaign set that needs campaign metadata organization.",
    },
    {
        "topic_id": "maho_saba",
        "label": "마법소녀의 마녀재판 굿즈",
        "priority": 40,
        "terms": ["마법소녀의 마녀재판", "마녀재판", "魔法少女ノ魔女裁判", "魔女裁判"],
        "reason": "Recently requested game goods; imported rows need spot-check coverage.",
    },
    {
        "topic_id": "bokubu_style",
        "label": "부쿠부 / 팝팀애픽 그림체 굿즈",
        "priority": 50,
        "terms": ["부쿠부", "大川ぶくぶ", "팝팀애픽", "ポプテピピック", "Pop Team Epic"],
        "reason": "Requested across Pop Team Epic, Gintama, Frieren, Danganronpa, and related goods.",
    },
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path} must contain a JSON object with an items list")
    return [item for item in payload["items"] if isinstance(item, dict)]


def _load_requested(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []
    items = payload.get("items") or []
    return [item for item in items if isinstance(item, dict)]


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _matches_terms(item: dict[str, Any], terms: list[str]) -> bool:
    haystack = json.dumps(item, ensure_ascii=False).lower()
    return any(term.lower() in haystack for term in terms)


def _request_catalog_matches(
    catalog_items: list[dict[str, Any]],
    requested_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_source = {
        str(item.get("source_url") or ""): item
        for item in catalog_items
        if _present(item.get("source_url"))
    }
    by_name = {
        str(item.get("name_ko") or ""): item
        for item in catalog_items
        if _present(item.get("name_ko"))
    }
    matched: list[dict[str, Any]] = []
    seen: set[int] = set()
    for request in requested_items:
        source_url = str(request.get("matched_source_url") or request.get("source_url") or "")
        name_ko = str(request.get("matched_name_ko") or request.get("name_ko") or "")
        item = by_source.get(source_url) or by_name.get(name_ko)
        if not item:
            continue
        index = int(item.get("catalog_index") or -1)
        if index in seen:
            continue
        seen.add(index)
        matched.append(item)
    return matched


def _compact_item(item: dict[str, Any], *, missing_field: str) -> dict[str, Any]:
    source_url = item.get("source_url") if _present(item.get("source_url")) else ""
    return {
        "catalog_index": item.get("catalog_index"),
        "missing_field": missing_field,
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_store": item.get("source_store"),
        "source_url": item.get("source_url"),
        "image_url": item.get("image_url"),
        "release_date": item.get("release_date"),
        "official_price_jpy": item.get("official_price_jpy"),
        "barcode": item.get("barcode"),
        "catalog_field_import_template": _catalog_field_import_template(item, missing_field, source_url),
        "auto_apply_enabled": False,
    }


def _catalog_field_import_template(item: dict[str, Any], missing_field: str, source_url: Any) -> dict[str, Any]:
    source_url_text = str(source_url or "").strip()
    evidence_url = source_url_text if source_url_text else ""
    blocked_until = "manual_official_evidence_confirmed"
    if missing_field == "source_url":
        blocked_until = "exact_product_source_url_confirmed"
        evidence_url = ""
    elif missing_field == "image_url" and not source_url_text:
        blocked_until = "exact_product_source_url_confirmed"
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "row_index": item.get("catalog_index"),
        "field": missing_field,
        "manual_value": "",
        "evidence_url": evidence_url,
        "candidate_source_url": source_url_text,
        "requires_exact_source_url": missing_field in {"source_url", "image_url"},
        "requires_labeled_official_evidence": missing_field in {"release_date", "official_price_jpy", "barcode", "name_ja"},
        "blocked_until": blocked_until,
    }


def _next_step_for_field(field: str) -> str:
    if field == "source_url":
        return "find_exact_official_or_trusted_source_url"
    if field == "image_url":
        return "extract_image_from_exact_reviewed_source_url"
    if field == "release_date":
        return "verify_release_date_from_official_campaign_or_product_page"
    if field == "official_price_jpy":
        return "verify_tax_included_jpy_price_from_official_source"
    if field == "barcode":
        return "verify_barcode_only_when_packaged_product_identity_supports_it"
    return "verify_japanese_name_from_official_source"


def build_report(
    catalog_items: list[dict[str, Any]],
    requested_items: list[dict[str, Any]] | None = None,
    *,
    batch_size: int = 30,
) -> dict[str, Any]:
    requested_items = requested_items or []
    batches: list[dict[str, Any]] = []
    topic_summaries: list[dict[str, Any]] = []
    requested_review_rows = [
        request
        for request in requested_items
        if request.get("status") != "already_present"
        or not request.get("has_candidate_image")
        or request.get("review_note")
    ]

    for topic in TOPICS:
        if topic["topic_id"] == "requested_special_goods":
            rows = _request_catalog_matches(catalog_items, requested_items)
            topic_requested_review_rows = requested_review_rows
        else:
            rows = [item for item in catalog_items if _matches_terms(item, list(topic["terms"]))]
            topic_requested_review_rows = [
                request for request in requested_review_rows if _matches_terms(request, list(topic["terms"]))
            ]

        rows_by_index: dict[int, dict[str, Any]] = {}
        for row in rows:
            rows_by_index[int(row.get("catalog_index") or -1)] = row
        rows = list(rows_by_index.values())

        missing_by_field = {
            field: [row for row in rows if not _present(row.get(field))]
            for field in TRACKED_FIELDS
        }
        open_indexes = {
            int(row.get("catalog_index") or -1)
            for field_rows in missing_by_field.values()
            for row in field_rows
        }
        field_totals = {field: len(field_rows) for field, field_rows in missing_by_field.items()}

        topic_summaries.append(
            {
                "topic_id": topic["topic_id"],
                "label": topic["label"],
                "priority": topic["priority"],
                "catalog_rows": len(rows),
                "requested_review_rows": len(topic_requested_review_rows),
                "open_catalog_rows": len(open_indexes),
                "open_rows": len(open_indexes) + len(topic_requested_review_rows),
                "field_missing_totals": field_totals,
                "review_reason": topic["reason"],
                "auto_apply_enabled": False,
            }
        )

        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for field, field_rows in missing_by_field.items():
            for row in field_rows:
                store = str(row.get("source_store") or "unknown")
                grouped[(field, store)].append(row)

        for (field, store), group_rows in sorted(
            grouped.items(),
            key=lambda pair: (
                int(topic["priority"]) + FIELD_PRIORITY.get(pair[0][0], 99),
                -len(pair[1]),
                pair[0][0],
                pair[0][1],
            ),
        ):
            for offset in range(0, len(group_rows), batch_size):
                batch_rows = group_rows[offset : offset + batch_size]
                categories = Counter(str(row.get("category") or "") for row in batch_rows)
                batch_id = f"requested-focus-{len(batches) + 1:03d}"
                priority = int(topic["priority"]) + FIELD_PRIORITY.get(field, 99)
                batches.append(
                    {
                        "batch_id": batch_id,
                        "priority": priority,
                        "topic_id": topic["topic_id"],
                        "topic_label": topic["label"],
                        "missing_field": field,
                        "source_store": store,
                        "row_count": len(batch_rows),
                        "offset": offset,
                        "review_state": "manual_evidence_review_required",
                        "next_machine_step": _next_step_for_field(field),
                        "recommended_action": _next_step_for_field(field),
                        "catalog_field_import_template_fields": [
                            "manual_confirmed",
                            "row_index",
                            "field",
                            "manual_value",
                            "evidence_url",
                            "candidate_source_url",
                        ],
                        "category_counts": categories.most_common(),
                        "items": [_compact_item(row, missing_field=field) for row in batch_rows],
                        "auto_apply_enabled": False,
                    }
                )

        if topic_requested_review_rows:
            batches.append(
                {
                    "batch_id": f"requested-focus-{len(batches) + 1:03d}",
                    "priority": int(topic["priority"]) + 5,
                    "topic_id": topic["topic_id"],
                    "topic_label": topic["label"],
                    "missing_field": "requested_item_evidence",
                    "source_store": "requested_special_goods_public",
                    "row_count": len(topic_requested_review_rows),
                    "offset": 0,
                    "review_state": "manual_evidence_review_required",
                    "next_machine_step": "review_requested_special_item_evidence",
                    "recommended_action": "Confirm requested item evidence before preparing catalog changes.",
                    "category_counts": [],
                    "items": [
                        {
                            "request_label": request.get("request_label"),
                            "status": request.get("status"),
                            "existing_count": request.get("existing_count"),
                            "has_candidate_image": request.get("has_candidate_image"),
                            "review_note": request.get("review_note"),
                            "auto_apply_enabled": False,
                        }
                        for request in topic_requested_review_rows
                    ],
                    "auto_apply_enabled": False,
                }
            )

    batches.sort(
        key=lambda batch: (
            int(batch.get("priority") or 999),
            -int(batch.get("row_count") or 0),
            str(batch.get("topic_id") or ""),
            str(batch.get("missing_field") or ""),
            str(batch.get("source_store") or ""),
        )
    )
    by_topic = Counter(str(batch.get("topic_id") or "") for batch in batches)
    by_field = Counter(str(batch.get("missing_field") or "") for batch in batches)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "requested_focus_full_review_batches",
        "summary": {
            "topic_count": len(TOPICS),
            "topic_with_batches_count": len(by_topic),
            "batch_count": len(batches),
            "batch_size": batch_size,
            "review_row_count": sum(int(batch.get("row_count") or 0) for batch in batches),
            "by_topic": by_topic.most_common(),
            "by_missing_field": by_field.most_common(),
            "auto_apply_enabled": False,
        },
        "topic_summaries": topic_summaries,
        "instructions": [
            "Use these batches for user-requested focus work before broad catalog metadata cleanup.",
            "Each batch isolates one topic, one missing field, and one source store when possible.",
            "Do not auto-apply any catalog patch from this report; exact source evidence is required first.",
            "Barcode work may be skipped for prize-only campaign rows unless a packaged product barcode is verified.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--requested", type=Path, default=DEFAULT_REQUESTED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=30)
    args = parser.parse_args()

    report = build_report(
        _load_catalog(args.catalog),
        _load_requested(args.requested),
        batch_size=args.batch_size,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
