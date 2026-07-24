from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "requested_focus_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "requested_focus_action_queue_public.json"

ACTIONABLE_FIELDS = {
    "source_url",
    "image_url",
    "release_date",
    "official_price_jpy",
    "name_ja",
}

FIELD_PRIORITY = {
    "source_url": 10,
    "image_url": 20,
    "release_date": 30,
    "official_price_jpy": 40,
    "name_ja": 50,
}

FIELD_BLOCKERS: dict[str, dict[str, Any]] = {
    "source_url": {
        "blocked_until": "exact_product_source_url_confirmed",
        "blocked_reason": "missing_exact_source_url_for_requested_focus",
        "required_evidence": [
            "exact_official_or_trusted_product_source_url",
            "title_character_variant_type_match",
            "manual_note_for_source_choice",
        ],
    },
    "image_url": {
        "blocked_until": "exact_source_url_and_image_url_confirmed",
        "blocked_reason": "image_url_requires_confirmed_source_evidence",
        "required_evidence": [
            "exact_product_source_url",
            "image_url_from_accepted_source_or_trusted_official_cdn",
            "same_product_image_identity_confirmed",
        ],
    },
    "release_date": {
        "blocked_until": "labeled_release_date_confirmed",
        "blocked_reason": "release_date_requires_labeled_source_evidence",
        "required_evidence": [
            "official_labeled_release_date",
            "source_url_or_evidence_url",
            "manual_note_for_ambiguous_dates",
        ],
    },
    "official_price_jpy": {
        "blocked_until": "labeled_official_price_confirmed",
        "blocked_reason": "price_requires_labeled_yen_evidence",
        "required_evidence": [
            "official_labeled_yen_price",
            "currency_jpy_confirmed",
            "manual_note_if_campaign_price_applies",
        ],
    },
    "name_ja": {
        "blocked_until": "official_japanese_name_confirmed",
        "blocked_reason": "name_ja_requires_official_label_evidence",
        "required_evidence": [
            "official_japanese_product_name",
            "title_matches_requested_item",
            "manual_note_for_translation_or_normalization",
        ],
    },
}

BARCODE_EXCLUDED_BLOCKER = {
    "blocked_until": "non_barcode_requested_focus_queue_completed",
    "blocked_reason": "barcode_research_deferred_from_requested_focus_action_queue",
    "required_evidence": [
        "manufacturer_or_retailer_barcode_label",
        "barcode_matches_exact_product_variant",
        "manual_confirmation_before_import",
    ],
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _count_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(str(row.get(key) or "") for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _blocker_for_field(field: str) -> dict[str, Any]:
    return FIELD_BLOCKERS.get(field, {})


def _with_blocker(template: dict[str, Any], field: str) -> dict[str, Any]:
    blocker = _blocker_for_field(field)
    if not blocker:
        return dict(template)
    enriched = dict(template)
    enriched["blocked_until"] = blocker["blocked_until"]
    enriched["blocked_reason"] = blocker["blocked_reason"]
    enriched["required_evidence"] = list(blocker["required_evidence"])
    return enriched


STORE_SEARCH_DOMAINS = {
    "AmiAmi": "www.amiami.jp",
    "FuRyu": "furyuprize.com",
    "Movic": "www.movic.jp",
    "Taito": "www.taito.co.jp",
    "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8": "www.goodsmile.info",
    "\uc560\ub2c8\uba54\uc774\ud2b8": "www.animate-onlineshop.jp",
    "\uc5d4\uc2a4\uce74\uc774": "www.enskyshop.com",
    "\ucf54\ud1a0\ubd80\ud0a4\uc57c": "shop.kotobukiya.co.jp",
}


def _review_query(item: dict[str, Any], batch: dict[str, Any]) -> str:
    title = str(item.get("name_ja") or item.get("name_ko") or "").strip()
    topic = str(batch.get("topic_label") or batch.get("topic_id") or "").strip()
    category = str(item.get("category") or "").strip()
    return " ".join(part for part in (title, topic, category) if part)


def _primary_review_url(batch: dict[str, Any], item: dict[str, Any], field: str) -> tuple[str, str]:
    source_url = str(item.get("source_url") or "").strip()
    if field in {"image_url", "release_date", "official_price_jpy", "name_ja"} and source_url:
        return source_url, "existing_source_url"

    source_store = str(item.get("source_store") or batch.get("source_store") or "").strip()
    domain = STORE_SEARCH_DOMAINS.get(source_store)
    query = _review_query(item, batch)
    if domain and query:
        encoded = urllib.parse.quote(f'site:{domain} "{query}"')
        return f"https://www.google.com/search?q={encoded}", "domain_limited_web_search"
    if query:
        encoded = urllib.parse.quote(f"{query} {source_store}".strip())
        return f"https://www.google.com/search?q={encoded}", "web_search"
    return "", "manual_lookup_required"


def _compact_action_item(batch: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("catalog_field_import_template")
    template = template if isinstance(template, dict) else {}
    field = str(template.get("field") or item.get("missing_field") or batch.get("missing_field") or "")
    blocker = _blocker_for_field(field)
    primary_url, primary_kind = _primary_review_url(batch, item, field)
    return {
        "catalog_index": item.get("catalog_index"),
        "topic_id": batch.get("topic_id"),
        "topic_label": batch.get("topic_label"),
        "missing_field": field,
        "source_store": item.get("source_store") or batch.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "image_url": item.get("image_url"),
        "release_date": item.get("release_date"),
        "official_price_jpy": item.get("official_price_jpy"),
        "catalog_field_import_template": _with_blocker(template, field),
        "blocked_until": blocker.get("blocked_until"),
        "blocked_reason": blocker.get("blocked_reason"),
        "required_evidence": list(blocker.get("required_evidence") or []),
        "primary_review_url": primary_url,
        "primary_review_url_kind": primary_kind,
        "next_machine_step": batch.get("next_machine_step"),
        "recommended_action": batch.get("recommended_action"),
        "auto_apply_enabled": False,
    }


def build_report(
    review_batches: dict[str, Any],
    *,
    max_batches: int = 120,
    batch_size: int = 25,
    generated_at: str | None = None,
) -> dict[str, Any]:
    action_items: list[dict[str, Any]] = []
    barcode_template_rows = 0
    skipped_non_template_rows = 0

    for batch in review_batches.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            template = item.get("catalog_field_import_template")
            if not isinstance(template, dict):
                skipped_non_template_rows += 1
                continue
            field = str(template.get("field") or item.get("missing_field") or batch.get("missing_field") or "")
            if field == "barcode":
                barcode_template_rows += 1
                continue
            if field not in ACTIONABLE_FIELDS:
                continue
            action_items.append(_compact_action_item(batch, item))

    action_items.sort(
        key=lambda row: (
            FIELD_PRIORITY.get(str(row.get("missing_field") or ""), 99),
            int(row.get("catalog_index") or 999_999_999),
            str(row.get("topic_id") or ""),
            str(row.get("source_store") or ""),
        )
    )

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in action_items:
        key = (
            str(item.get("missing_field") or ""),
            str(item.get("topic_id") or ""),
            str(item.get("source_store") or "unknown"),
        )
        grouped.setdefault(key, []).append(item)

    action_batches: list[dict[str, Any]] = []
    for (field, topic_id, source_store), rows in sorted(
        grouped.items(),
        key=lambda pair: (
            FIELD_PRIORITY.get(pair[0][0], 99),
            -len(pair[1]),
            pair[0][1],
            pair[0][2],
        ),
    ):
        for offset in range(0, len(rows), batch_size):
            chunk = rows[offset : offset + batch_size]
            if len(action_batches) >= max_batches:
                break
            action_batches.append(
                {
                    "batch_id": f"requested-focus-action-{len(action_batches) + 1:03d}",
                    "priority": FIELD_PRIORITY.get(field, 99),
                    "topic_id": topic_id,
                    "missing_field": field,
                    "source_store": source_store,
                    "row_count": len(chunk),
                    "offset": offset,
                    "review_state": "manual_evidence_review_required",
                    "next_machine_step": chunk[0].get("next_machine_step") if chunk else "",
                    "recommended_action": chunk[0].get("recommended_action") if chunk else "",
                    "blocked_until": _blocker_for_field(field).get("blocked_until"),
                    "blocked_reason": _blocker_for_field(field).get("blocked_reason"),
                    "required_evidence": list(_blocker_for_field(field).get("required_evidence") or []),
                    "first_primary_review_url": next(
                        (str(item.get("primary_review_url")) for item in chunk if item.get("primary_review_url")),
                        "",
                    ),
                    "first_primary_review_url_kind": next(
                        (
                            str(item.get("primary_review_url_kind"))
                            for item in chunk
                            if item.get("primary_review_url")
                        ),
                        "manual_lookup_required",
                    ),
                    "category_counts": _count_pairs(chunk, "category"),
                    "blocked_reason_counts": _count_pairs(chunk, "blocked_reason"),
                    "blocked_until_counts": _count_pairs(chunk, "blocked_until"),
                    "items": chunk,
                    "auto_apply_enabled": False,
                }
            )
        if len(action_batches) >= max_batches:
            break

    queued_rows = sum(int(batch.get("row_count") or 0) for batch in action_batches)
    review_url_rows = sum(1 for item in action_items if item.get("primary_review_url"))
    primary_review_url_kind_counts = _count_pairs(action_items, "primary_review_url_kind")
    unqueued_actionable_rows = max(len(action_items) - queued_rows, 0)
    queue_coverage = round(queued_rows / len(action_items), 4) if action_items else 1.0
    non_barcode_template_rows = len(action_items)
    total_review_template_rows = non_barcode_template_rows + barcode_template_rows
    non_barcode_template_share = (
        round(non_barcode_template_rows / total_review_template_rows, 4) if total_review_template_rows else 1.0
    )
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "requested_focus_action_queue",
        "summary": {
            "actionable_template_rows": len(action_items),
            "queued_action_rows": queued_rows,
            "unqueued_actionable_rows": unqueued_actionable_rows,
            "queue_coverage": queue_coverage,
            "action_batch_count": len(action_batches),
            "batch_size": batch_size,
            "max_batches": max_batches,
            "barcode_template_rows_excluded": barcode_template_rows,
            "non_barcode_template_rows": non_barcode_template_rows,
            "total_review_template_rows": total_review_template_rows,
            "non_barcode_template_share": non_barcode_template_share,
            "skipped_non_template_rows": skipped_non_template_rows,
            "field_counts": _count_pairs(action_items, "missing_field"),
            "topic_counts": _count_pairs(action_items, "topic_id"),
            "blocked_reason_counts": _count_pairs(action_items, "blocked_reason"),
            "blocked_until_counts": _count_pairs(action_items, "blocked_until"),
            "review_url_rows": review_url_rows,
            "primary_review_url_kind_counts": primary_review_url_kind_counts,
            "barcode_template_rows_excluded_blocked_reason": BARCODE_EXCLUDED_BLOCKER["blocked_reason"],
            "barcode_template_rows_excluded_blocked_until": BARCODE_EXCLUDED_BLOCKER["blocked_until"],
            "barcode_template_rows_excluded_required_evidence": BARCODE_EXCLUDED_BLOCKER["required_evidence"],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue for user-requested focus rows that are actionable before barcode research.",
            "Each item still requires exact official or trusted evidence before any catalog patch is applied.",
            "Every queued item declares blocked_reason and required_evidence so manual reviewers know what proof is missing.",
            "Barcode-only rows are excluded here and remain in requested_focus_review_batches_public.json with barcode_research_deferred_from_requested_focus_action_queue.",
        ],
        "batches": action_batches,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
            "queued_rows_require": {
                field: {
                    "blocked_until": details["blocked_until"],
                    "blocked_reason": details["blocked_reason"],
                    "required_evidence": details["required_evidence"],
                }
                for field, details in FIELD_BLOCKERS.items()
            },
            "excluded_barcode_rows": BARCODE_EXCLUDED_BLOCKER,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-batches", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()

    report = build_report(_load(args.input), max_batches=args.max_batches, batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
