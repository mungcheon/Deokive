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
DEFAULT_INPUT = DATA / "source_detail_probe_public.json"
DEFAULT_OUTPUT = DATA / "source_detail_candidate_action_queue_public.json"
DEFAULT_CATALOG = DATA / "catalog_public.json"

GENERIC_SHARED_TOKENS = {
    "pop",
    "up",
    "parade",
    "acrylic",
    "badge",
    "can",
    "stand",
    "keychain",
    "clear",
    "file",
    "tshirt",
    "shirt",
    "pouch",
    "mug",
    "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
    "\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
    "\u30af\u30ea\u30a2\u30d5\u30a1\u30a4\u30eb",
    "\u30c8\u30ec\u30fc\u30c7\u30a3\u30f3\u30b0\u7f36\u30d0\u30c3\u30b8",
    "\u7f36\u30d0\u30c3\u30b8",
    "\u30de\u30b0\u30ab\u30c3\u30d7",
    "\u30dd\u30fc\u30c1",
    "t\u30b7\u30e3\u30c4",
}

PRODUCT_TYPE_HINTS = {
    "nendoroid": {
        "nendoroid",
        "\u306d\u3093\u3069\u308d\u3044\u3069",
    },
    "nendoroid_plus": {
        "nendoroid plus",
        "nendoroid+",
        "\u306d\u3093\u3069\u308d\u3044\u3069\u3077\u3089\u3059",
    },
    "acrylic_keychain": {
        "acrylic keychain",
        "acrylic key ring",
        "\u30a2\u30af\u30ea\u30eb\u30ad\u30fc\u30c1\u30a7\u30fc\u30f3",
        "\u30a2\u30af\u30ea\u30eb\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
    },
    "acrylic_stand": {
        "acrylic stand",
        "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
        "\u30b9\u30bf\u30f3\u30c9\u30dd\u30c3\u30d7",
    },
    "clear_file": {
        "clear file",
        "\u30af\u30ea\u30a2\u30d5\u30a1\u30a4\u30eb",
    },
    "can_badge": {
        "can badge",
        "\u7f36\u30d0\u30c3\u30b8",
        "\u30d0\u30c3\u30c1",
    },
    "tshirt": {
        "tshirt",
        "t-shirt",
        "t\u30b7\u30e3\u30c4",
    },
    "pouch": {
        "pouch",
        "\u30dd\u30fc\u30c1",
    },
    "mug": {
        "mug",
        "\u30de\u30b0\u30ab\u30c3\u30d7",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def load_catalog_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("items")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    raise ValueError(f"{path} must contain a catalog row list or an object with items")


def counter_rows(rows: list[dict[str, Any]], field: str) -> list[list[Any]]:
    counts = Counter(str(row.get(field) or "") for row in rows)
    counts.pop("", None)
    return [[key, value] for key, value in counts.most_common()]


def counter_list_values(rows: list[dict[str, Any]], field: str) -> list[list[Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        for value in row.get(field) or []:
            if value:
                counts[str(value)] += 1
    return [[key, value] for key, value in counts.most_common()]


def candidate_count_bucket(row: dict[str, Any]) -> str:
    candidate_count = int(row.get("candidate_count") or 0)
    if candidate_count <= 0:
        return "no_candidate_count"
    if candidate_count == 1:
        return "single_candidate"
    if candidate_count <= 3:
        return "near_single_candidate"
    if candidate_count <= 10:
        return "small_candidate_set"
    return "large_candidate_set"


def candidate_risk(row: dict[str, Any]) -> str:
    score = row.get("score")
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        numeric_score = 0.0
    candidate_count = int(row.get("candidate_count") or 0)
    if row.get("status") == "exact_candidate_available" and numeric_score >= 0.8 and candidate_count == 1:
        return "strong_single_candidate_review"
    if numeric_score >= 0.75 and candidate_count <= 2:
        return "near_single_candidate_review"
    if numeric_score >= 0.5:
        return "ambiguous_candidate_review"
    return "weak_candidate_review"


def catalog_index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for position, row in enumerate(rows):
        raw_index = row.get("catalog_index", position)
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        indexed[index] = row
    return indexed


def text_matches(left: Any, right: Any) -> bool:
    return str(left or "").strip() == str(right or "").strip()


def normalize_token(value: Any) -> str:
    return str(value or "").strip().casefold()


def is_generic_token(value: Any) -> bool:
    token = normalize_token(value)
    return token in {normalize_token(item) for item in GENERIC_SHARED_TOKENS}


def parenthetical_terms(*values: Any) -> list[str]:
    terms: list[str] = []
    for value in values:
        text = str(value or "")
        for match in re.findall(r"[\(\uff08]([^\)\uff09]{2,})[\)\uff09]", text):
            term = match.strip()
            if term:
                terms.append(term)
    return terms


def product_type_hints(value: Any) -> set[str]:
    text = normalize_token(value)
    matches: set[str] = set()
    for key, hints in PRODUCT_TYPE_HINTS.items():
        if any(normalize_token(hint) in text for hint in hints):
            matches.add(key)
    if "nendoroid_plus" in matches:
        matches.discard("nendoroid")
    return matches


def candidate_identity_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    shared_tokens = [token for token in row.get("shared_tokens") or [] if str(token or "").strip()]
    if shared_tokens and all(is_generic_token(token) for token in shared_tokens):
        flags.append("only_generic_shared_tokens")

    name_text_raw = " ".join(str(row.get(field) or "") for field in ("name_ko", "name_ja"))
    name_text = name_text_raw.casefold()
    title_text = str(row.get("candidate_title") or "").casefold()
    if ("\u00d7" in title_text or "|" in title_text) and "\u00d7" not in name_text and "|" not in name_text:
        flags.append("candidate_title_mentions_crossover")
    if ("/" in title_text or "\u5168" in title_text) and "/" not in name_text and "\u5168" not in name_text:
        flags.append("candidate_title_multi_variant_or_bundle")

    catalog_types = product_type_hints(name_text_raw)
    candidate_types = product_type_hints(row.get("candidate_title"))
    if catalog_types and candidate_types and not catalog_types.intersection(candidate_types):
        flags.append("candidate_title_product_type_mismatch")
    elif "nendoroid" in catalog_types and "nendoroid_plus" in candidate_types:
        flags.append("candidate_title_product_type_mismatch")

    missing_terms = [
        term
        for term in parenthetical_terms(row.get("name_ko"), row.get("name_ja"))
        if normalize_token(term) not in title_text and not is_generic_token(term)
    ]
    if missing_terms:
        flags.append("candidate_title_missing_catalog_variant_hint")

    return flags


def review_priority(risk: str, flags: list[str]) -> int:
    base_priority = {
        "strong_single_candidate_review": 10,
        "near_single_candidate_review": 20,
        "ambiguous_candidate_review": 30,
        "weak_candidate_review": 40,
    }.get(risk, 99)
    if flags and base_priority < 35:
        return 35
    return base_priority


def manual_confirmation_shortlist(item: dict[str, Any]) -> bool:
    catalog_state = item.get("current_catalog_state") or {}
    candidate_count = int(item.get("candidate_count") or 0)
    return bool(
        item.get("safe_source_image_pair") is True
        and catalog_state.get("catalog_identity_matches") is True
        and catalog_state.get("catalog_has_display_image") is False
        and not item.get("candidate_identity_flags")
        and item.get("review_risk") in {"strong_single_candidate_review", "near_single_candidate_review"}
        and 0 < candidate_count <= 2
    )


def priority_manual_review_candidate(item: dict[str, Any]) -> bool:
    catalog_state = item.get("current_catalog_state") or {}
    return bool(
        item.get("safe_source_image_pair") is True
        and catalog_state.get("catalog_identity_matches") is True
        and catalog_state.get("catalog_has_display_image") is False
        and not item.get("candidate_identity_flags")
    )


def current_catalog_state(row: dict[str, Any], catalog_by_index: dict[int, dict[str, Any]]) -> dict[str, Any]:
    try:
        index = int(row.get("catalog_index"))
    except (TypeError, ValueError):
        index = -1
    catalog_row = catalog_by_index.get(index)
    if not catalog_row:
        return {
            "catalog_match_found": False,
            "catalog_has_display_image": False,
            "catalog_identity_matches": False,
            "stale_candidate": True,
        }
    name_matches = text_matches(row.get("name_ko"), catalog_row.get("name_ko")) and text_matches(
        row.get("name_ja"), catalog_row.get("name_ja")
    )
    store_matches = text_matches(row.get("source_store"), catalog_row.get("source_store"))
    return {
        "catalog_match_found": True,
        "catalog_has_display_image": bool(catalog_row.get("local_image_path") or catalog_row.get("image_url")),
        "catalog_identity_matches": name_matches and store_matches,
        "stale_candidate": not (name_matches and store_matches),
        "catalog_current_name_ko": catalog_row.get("name_ko"),
        "catalog_current_name_ja": catalog_row.get("name_ja"),
        "catalog_current_source_store": catalog_row.get("source_store"),
        "catalog_current_source_url": catalog_row.get("source_url"),
    }


def compact_item(row: dict[str, Any], catalog_by_index: dict[int, dict[str, Any]] | None = None) -> dict[str, Any]:
    risk = candidate_risk(row)
    catalog_state = current_catalog_state(row, catalog_by_index or {})
    identity_flags = candidate_identity_flags(row)
    item = {
        "manual_confirmed": False,
        "catalog_index": row.get("catalog_index"),
        "row_index": row.get("catalog_index"),
        "source_store": row.get("source_store"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "query": row.get("query"),
        "candidate_status": row.get("status"),
        "candidate_count": row.get("candidate_count"),
        "candidate_count_bucket": candidate_count_bucket(row),
        "candidate_source_url": row.get("candidate_source_url"),
        "candidate_title": row.get("candidate_title"),
        "candidate_image_url": row.get("candidate_image_url"),
        "score": row.get("score"),
        "candidate_score": row.get("score"),
        "shared_tokens": row.get("shared_tokens") or [],
        "candidate_identity_flags": identity_flags,
        "safe_source_image_pair": row.get("safe_source_image_pair"),
        "source_report": row.get("source_report"),
        "review_risk": risk,
        "review_priority": review_priority(risk, identity_flags),
        "recommended_action": "confirm_exact_identity_before_source_or_image_patch",
        "current_catalog_state": catalog_state,
        "source_patch_template": {
            "manual_confirmed": False,
            "row_index": row.get("catalog_index"),
            "field": "source_url",
            "manual_value": row.get("candidate_source_url") or "",
            "evidence_url": row.get("candidate_source_url") or "",
            "candidate_source_url": row.get("candidate_source_url") or "",
            "source_store": row.get("source_store"),
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
        },
        "image_patch_template": {
            "manual_confirmed": False,
            "row_index": row.get("catalog_index"),
            "field": "image_url",
            "manual_value": row.get("candidate_image_url") or "",
            "evidence_url": row.get("candidate_source_url") or "",
            "candidate_source_url": row.get("candidate_source_url") or "",
            "source_store": row.get("source_store"),
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
        },
        "acceptance_criteria": [
            "Candidate title must describe the same product, character, and variant as the catalog row.",
            "Candidate source URL must be an exact product/detail page.",
            "Candidate image must be the product image from the accepted source page or trusted official CDN.",
            "Leave manual_confirmed false when the candidate is a related product, bundle, or wrong variant.",
        ],
        "auto_apply_enabled": False,
    }
    item["manual_confirmation_shortlist"] = manual_confirmation_shortlist(item)
    item["priority_manual_review_candidate"] = priority_manual_review_candidate(item)
    if catalog_state.get("catalog_has_display_image"):
        item["recommended_action"] = "skip_current_catalog_row_already_has_display_image"
    elif catalog_state.get("stale_candidate"):
        item["recommended_action"] = "refresh_candidate_before_manual_review"
    elif item["manual_confirmation_shortlist"]:
        item["recommended_action"] = "priority_manual_confirm_source_and_image_patch"
    elif item["priority_manual_review_candidate"]:
        item["recommended_action"] = "priority_manual_review_safe_source_image_candidate"
    elif identity_flags:
        item["recommended_action"] = "recheck_candidate_identity_before_source_or_image_patch"
    return item


def build_report(
    source_detail_probe: dict[str, Any],
    catalog_rows: list[dict[str, Any]] | None = None,
    *,
    generated_at: str | None = None,
    batch_size: int = 10,
) -> dict[str, Any]:
    by_index = catalog_index(catalog_rows or [])
    items = [
        compact_item(row, by_index)
        for row in source_detail_probe.get("review_candidates") or []
        if isinstance(row, dict)
    ]
    items.sort(
        key=lambda row: (
            int(row.get("review_priority") or 99),
            str(row.get("source_store") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(items), batch_size):
        chunk = items[offset : offset + batch_size]
        batches.append(
            {
                "batch_id": f"source-detail-candidate-action-{len(batches) + 1:03d}",
                "row_count": len(chunk),
                "offset": offset,
                "review_state": "manual_identity_review_required",
                "next_machine_step": "manual_confirm_then_import_source_and_image_templates",
                "recommended_action": "Review candidate identity and set manual_confirmed only for exact product matches.",
                "by_source_store": counter_rows(chunk, "source_store"),
                "by_review_risk": counter_rows(chunk, "review_risk"),
                "by_candidate_count_bucket": counter_rows(chunk, "candidate_count_bucket"),
                "safe_source_image_pair_rows": sum(1 for item in chunk if item.get("safe_source_image_pair") is True),
                "manual_confirmation_shortlist_rows": sum(
                    1 for item in chunk if item.get("manual_confirmation_shortlist") is True
                ),
                "priority_manual_review_candidate_rows": sum(
                    1 for item in chunk if item.get("priority_manual_review_candidate") is True
                ),
                "items": chunk,
                "auto_apply_enabled": False,
            }
        )
    priority_review_candidates = [
        {
            "catalog_index": item.get("catalog_index"),
            "source_store": item.get("source_store"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "candidate_title": item.get("candidate_title"),
            "candidate_source_url": item.get("candidate_source_url"),
            "candidate_image_url": item.get("candidate_image_url"),
            "review_risk": item.get("review_risk"),
            "candidate_count_bucket": item.get("candidate_count_bucket"),
            "recommended_action": item.get("recommended_action"),
            "source_patch_template": item.get("source_patch_template"),
            "image_patch_template": item.get("image_patch_template"),
            "auto_apply_enabled": False,
        }
        for item in items
        if item.get("priority_manual_review_candidate") is True
    ]

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_detail_candidate_action_queue",
        "summary": {
            "candidate_action_rows": len(items),
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "manual_confirmed_true": sum(1 for item in items if item.get("manual_confirmed") is True),
            "safe_source_image_pair_rows": sum(1 for item in items if item.get("safe_source_image_pair") is True),
            "manual_confirmation_shortlist_rows": sum(
                1 for item in items if item.get("manual_confirmation_shortlist") is True
            ),
            "priority_manual_review_candidate_rows": len(priority_review_candidates),
            "identity_warning_rows": sum(1 for item in items if item.get("candidate_identity_flags")),
            "identity_warning_missing_display_image_rows": sum(
                1
                for item in items
                if item.get("candidate_identity_flags")
                and item.get("current_catalog_state", {}).get("catalog_has_display_image") is False
            ),
            "unflagged_missing_display_image_candidate_rows": sum(
                1
                for item in items
                if not item.get("candidate_identity_flags")
                and item.get("current_catalog_state", {}).get("catalog_has_display_image") is False
            ),
            "current_catalog_matched_rows": sum(
                1 for item in items if item.get("current_catalog_state", {}).get("catalog_match_found") is True
            ),
            "current_catalog_missing_display_image_rows": sum(
                1 for item in items if item.get("current_catalog_state", {}).get("catalog_has_display_image") is False
            ),
            "current_catalog_already_has_display_image_rows": sum(
                1 for item in items if item.get("current_catalog_state", {}).get("catalog_has_display_image") is True
            ),
            "stale_candidate_rows": sum(
                1 for item in items if item.get("current_catalog_state", {}).get("stale_candidate") is True
            ),
            "identity_matched_candidate_rows": sum(
                1 for item in items if item.get("current_catalog_state", {}).get("catalog_identity_matches") is True
            ),
            "near_or_better_candidate_rows": sum(
                1
                for item in items
                if item.get("review_risk")
                in {"strong_single_candidate_review", "near_single_candidate_review"}
            ),
            "by_manual_confirmation_shortlist": [
                ["ready_for_priority_manual_confirmation", sum(1 for item in items if item.get("manual_confirmation_shortlist") is True)],
                ["requires_deeper_identity_review", sum(1 for item in items if item.get("manual_confirmation_shortlist") is not True)],
            ],
            "by_priority_manual_review_candidate": [
                ["safe_unflagged_missing_display_candidate", len(priority_review_candidates)],
                [
                    "not_priority_manual_review_candidate",
                    sum(1 for item in items if item.get("priority_manual_review_candidate") is not True),
                ],
            ],
            "ambiguous_or_weaker_candidate_rows": sum(
                1
                for item in items
                if item.get("review_risk")
                not in {"strong_single_candidate_review", "near_single_candidate_review"}
            ),
            "by_source_store": counter_rows(items, "source_store"),
            "by_review_risk": counter_rows(items, "review_risk"),
            "by_candidate_count_bucket": counter_rows(items, "candidate_count_bucket"),
            "by_candidate_identity_flag": counter_list_values(items, "candidate_identity_flags"),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use this queue only after reviewing source_detail_probe_public review candidates.",
            "Do not import candidate source_url or image_url unless manual_confirmed is set true after exact identity review.",
            "Rows may contain related products; wrong character or variant candidates must remain unconfirmed.",
            "current_catalog_state flags candidates that no longer match the public catalog row or already have a display image.",
            "candidate_identity_flags highlight high-risk title matches such as generic-only shared tokens, crossovers, or missing variant hints.",
        ],
        "priority_manual_review_candidates": priority_review_candidates,
        "batches": batches,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), load_catalog_rows(args.catalog), batch_size=args.batch_size)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
