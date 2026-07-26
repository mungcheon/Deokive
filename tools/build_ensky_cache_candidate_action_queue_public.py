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
DEFAULT_INPUT = DATA / "ensky_missing_image_cache_coverage_public.json"
DEFAULT_OUTPUT = DATA / "ensky_cache_candidate_action_queue_public.json"

ENSKY_STORE = "\uc5d4\uc2a4\uce74\uc774"

PRODUCT_TYPE_HINTS = {
    "acrylic_stand": {
        "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
        "\u30a2\u30af\u30b9\u30bf",
        "\u30b9\u30bf\u30f3\u30c9",
        "\u30b9\u30bf\u30f3\u30c7\u30a3",
        "acrylic stand",
    },
    "capsule_standy": {"\u30ab\u30d6\u30bb\u30eb\u30b9\u30bf\u30f3\u30c7\u30a3"},
    "rubber_strap": {"\u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7", "rubber strap"},
    "keyholder": {"\u30ad\u30fc\u30db\u30eb\u30c0\u30fc", "\u30ad\u30fc\u30c1\u30a7\u30fc\u30f3", "\u30ab\u30e9\u30d3\u30ca", "keyholder", "keychain"},
    "can_badge": {"\u7f36\u30d0\u30c3\u30b8", "\u30d0\u30c3\u30c1", "can badge"},
    "clear_file": {"\u30af\u30ea\u30a2\u30d5\u30a1\u30a4\u30eb", "clear file"},
    "mug": {"\u30de\u30b0\u30ab\u30c3\u30d7", "\u30de\u30b0", "mug"},
    "plush_mascot": {
        "\u3061\u3073\u3050\u308b\u307f",
        "\u306c\u3044\u3050\u308b\u307f",
        "\u30de\u30b9\u30b3\u30c3\u30c8",
        "\u307e\u3059\u3053\u3063\u3068",
        "\u304a\u307e\u3093\u3058\u3085\u3046",
        "\u3082\u3061\u3053\u308d\u308a\u3093",
        "mascot",
    },
    "towel": {"\u30bf\u30aa\u30eb", "towel"},
    "uchiwa": {"\u3046\u3061\u308f"},
    "ticket_file": {"\u30c1\u30b1\u30c3\u30c8\u30d5\u30a1\u30a4\u30eb"},
    "seal_gum": {"\u30b7\u30fc\u30eb\u30ac\u30e0"},
    "emoca": {"emoca"},
    "jigsaw_puzzle": {"\u30b8\u30b0\u30bd\u30fc\u30d1\u30ba\u30eb", "\u30d1\u30ba\u30eb", "puzzle"},
    "paper_theater": {"paper theater", "paper shadow art", "\u30da\u30fc\u30d1\u30fc\u30b7\u30a2\u30bf\u30fc"},
    "sticker": {"\u30b9\u30c6\u30c3\u30ab\u30fc", "\u30b7\u30fc\u30eb", "sticker"},
    "card": {"\u30ab\u30fc\u30c9", "card"},
}

AFFILIATION_TITLE_HINTS = {
    "\ub2e8\uac04\ub860\ud30c": {"\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1", "danganronpa"},
    "\uadc0\uba78\uc758 \uce7c\ub0a0": {"\u9b3c\u6ec5\u306e\u5203", "\u304d\u3081\u3064", "kimetsu"},
    "\ub098\uc758 \ud788\uc5b4\ub85c \uc544\uce74\ub370\ubbf8\uc544": {
        "\u50d5\u306e\u30d2\u30fc\u30ed\u30fc\u30a2\u30ab\u30c7\u30df\u30a2",
        "\u30d2\u30ed\u30a2\u30ab",
        "hero academia",
    },
    "\uccb4\uc778\uc18c \ub9e8": {"\u30c1\u30a7\u30f3\u30bd\u30fc\u30de\u30f3", "chainsaw man"},
    "\uc6d0\ud53c\uc2a4": {"\u30ef\u30f3\u30d4\u30fc\u30b9", "one piece"},
    "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c": {
        "\u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3",
        "\u30d5\u30ea\u30fc\u30ec\u30f3",
        "frieren",
    },
    "\ud5cc\ud130X\ud5cc\ud130": {"hunter", "\u30cf\u30f3\u30bf\u30fc"},
    "\uc8fc\uc220\ud68c\uc804": {"\u546a\u8853\u5efb\u6226", "\u3058\u3085\u3058\u3085\u3064", "jujutsu"},
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


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


def normalize_text(value: Any) -> str:
    return str(value or "").casefold()


def product_type_hints(value: Any) -> set[str]:
    text = normalize_text(value)
    matches: set[str] = set()
    for key, hints in PRODUCT_TYPE_HINTS.items():
        if any(normalize_text(hint) in text for hint in hints):
            matches.add(key)
    if "capsule_standy" in matches:
        matches.discard("acrylic_stand")
    return matches


def candidate_identity_flags(item: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    catalog_text = " ".join(str(item.get(field) or "") for field in ("name_ko", "name_ja", "category"))
    title = str(candidate.get("title") or candidate.get("candidate_title") or "")
    affiliation = str(item.get("affiliation") or "")
    affiliation_hints = AFFILIATION_TITLE_HINTS.get(affiliation)
    if affiliation_hints and not any(
        normalize_text(hint) in normalize_text(title) for hint in affiliation_hints
    ):
        flags.append("candidate_title_affiliation_mismatch")
    catalog_types = product_type_hints(catalog_text)
    candidate_types = product_type_hints(title)
    if catalog_types and candidate_types and not catalog_types.intersection(candidate_types):
        flags.append("candidate_title_product_type_mismatch")

    title_key = normalize_text(title)
    catalog_key = normalize_text(catalog_text)
    if re.search(r"1\s*box|box\u5165\u308a|\u30dc\u30c3\u30af\u30b9", title_key) and not re.search(
        r"1\s*box|box|\u30dc\u30c3\u30af\u30b9",
        catalog_key,
    ):
        flags.append("candidate_title_box_or_assortment")
    if "/" in title and "/" not in catalog_text:
        flags.append("candidate_title_multi_variant_or_lineup")
    return flags


def compact_candidate(candidate: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_title": candidate.get("title"),
        "candidate_source_url": candidate.get("source_url"),
        "candidate_image_url": candidate.get("image_url"),
        "safe_exact_match": candidate.get("safe_exact_match") is True,
        "score": candidate.get("score"),
        "matched_tokens": candidate.get("matched_tokens") or [],
        "candidate_identity_flags": candidate_identity_flags(item, candidate),
    }


def candidate_review_risk(flags: list[str]) -> str:
    flag_set = set(flags)
    if "candidate_title_affiliation_mismatch" in flag_set or "candidate_title_product_type_mismatch" in flag_set:
        return "high"
    if "candidate_title_box_or_assortment" in flag_set:
        return "medium"
    if flag_set == {"candidate_title_multi_variant_or_lineup"}:
        return "low"
    if flag_set:
        return "medium"
    return "low"


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        compact_candidate(candidate, item)
        for candidate in item.get("top_candidates", [])
        if isinstance(candidate, dict)
    ]
    top_candidate = candidates[0] if candidates else {}
    identity_flags = sorted(
        {
            flag
            for candidate in candidates
            for flag in candidate.get("candidate_identity_flags") or []
        }
    )
    review_risk = candidate_review_risk(identity_flags)
    return {
        "manual_confirmed": False,
        "catalog_index": item.get("catalog_index"),
        "row_index": item.get("catalog_index"),
        "source_store": item.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "affiliation": item.get("affiliation"),
        "category": item.get("category"),
        "candidate_status": item.get("status"),
        "candidate_count": item.get("candidate_count"),
        "candidate_identity_flags": identity_flags,
        "candidate_review_risk": review_risk,
        "top_candidate_has_source_url": bool(top_candidate.get("candidate_source_url")),
        "top_candidate_has_image_url": bool(top_candidate.get("candidate_image_url")),
        "top_candidate_safe_exact_match": top_candidate.get("safe_exact_match") is True,
        "import_readiness": {
            "status": "blocked_manual_identity_review",
            "candidate_source_url_ready": bool(top_candidate.get("candidate_source_url")),
            "candidate_image_url_ready": bool(top_candidate.get("candidate_image_url")),
            "candidate_identity_warning": bool(identity_flags),
            "candidate_review_risk": review_risk,
            "manual_confirmed_required": True,
            "can_import_now": False,
            "blocked_reason": "manual_confirmed_false"
            if not identity_flags
            else "candidate_identity_warning_requires_review",
        },
        "top_candidates": candidates[:5],
        "source_patch_template": {
            "manual_confirmed": False,
            "row_index": item.get("catalog_index"),
            "field": "source_url",
            "manual_value": top_candidate.get("candidate_source_url") or "",
            "evidence_url": top_candidate.get("candidate_source_url") or "",
            "candidate_source_url": top_candidate.get("candidate_source_url") or "",
            "source_store": item.get("source_store"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
        },
        "image_patch_template": {
            "manual_confirmed": False,
            "row_index": item.get("catalog_index"),
            "field": "image_url",
            "manual_value": top_candidate.get("candidate_image_url") or "",
            "evidence_url": top_candidate.get("candidate_source_url") or "",
            "candidate_source_url": top_candidate.get("candidate_source_url") or "",
            "source_store": item.get("source_store"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
        },
        "acceptance_criteria": [
            "Candidate title must match the exact product, character, and variant in the catalog row.",
            "Candidate source URL must be an Ensky product detail page, not search or category results.",
            "Candidate image must be the product image from the accepted Ensky product page.",
            "Leave manual_confirmed false for related goods, wrong characters, wrong goods type, or broad brand-only matches.",
        ],
        "recommended_action": "recheck_ensky_candidate_identity_before_source_or_image_patch"
        if identity_flags
        else "manual_review_ensky_cache_candidate_before_source_or_image_patch",
        "auto_apply_enabled": False,
    }


def build_report(cache_coverage: dict[str, Any], *, generated_at: str | None = None, batch_size: int = 10) -> dict[str, Any]:
    items = [
        compact_item(item)
        for item in cache_coverage.get("items", [])
        if isinstance(item, dict) and item.get("status") == "broad_cache_candidate"
    ]
    items.sort(
        key=lambda row: (
            {"low": 0, "medium": 1, "high": 2}.get(str(row.get("candidate_review_risk") or ""), 9),
            "candidate_title_affiliation_mismatch" in (row.get("candidate_identity_flags") or []),
            len(row.get("candidate_identity_flags") or []),
            "candidate_title_product_type_mismatch" in (row.get("candidate_identity_flags") or []),
            "candidate_title_box_or_assortment" in (row.get("candidate_identity_flags") or []),
            str(row.get("affiliation") or ""),
            str(row.get("category") or ""),
            -int(row.get("candidate_count") or 0),
            int(row.get("catalog_index") or 999_999_999),
        )
    )
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(items), batch_size):
        chunk = items[offset : offset + batch_size]
        batches.append(
            {
                "batch_id": f"ensky-cache-candidate-action-{len(batches) + 1:03d}",
                "row_count": len(chunk),
                "offset": offset,
                "review_state": "manual_identity_review_required",
                "source_store": "엔스카이",
                "next_machine_step": "manual_confirm_then_import_source_and_image_templates",
                "recommended_action": "Review broad Ensky cache candidates and confirm only exact product matches.",
                "by_affiliation": counter_rows(chunk, "affiliation"),
                "by_category": counter_rows(chunk, "category"),
                "by_candidate_review_risk": counter_rows(chunk, "candidate_review_risk"),
                "by_candidate_identity_flag": counter_list_values(chunk, "candidate_identity_flags"),
                "candidate_source_url_ready_rows": sum(
                    1 for item in chunk if item.get("top_candidate_has_source_url")
                ),
                "candidate_image_url_ready_rows": sum(
                    1 for item in chunk if item.get("top_candidate_has_image_url")
                ),
                "safe_exact_top_candidate_rows": sum(
                    1 for item in chunk if item.get("top_candidate_safe_exact_match")
                ),
                "identity_warning_rows": sum(
                    1 for item in chunk if item.get("candidate_identity_flags")
                ),
                "can_import_now_rows": sum(
                    1 for item in chunk if (item.get("import_readiness") or {}).get("can_import_now")
                ),
                "items": chunk,
                "auto_apply_enabled": False,
            }
        )
    import_readiness = {
        "candidate_rows": len(items),
        "candidate_source_url_ready_rows": sum(
            1 for item in items if item.get("top_candidate_has_source_url")
        ),
        "candidate_image_url_ready_rows": sum(
            1 for item in items if item.get("top_candidate_has_image_url")
        ),
        "safe_exact_top_candidate_rows": sum(
            1 for item in items if item.get("top_candidate_safe_exact_match")
        ),
        "identity_warning_rows": sum(1 for item in items if item.get("candidate_identity_flags")),
        "low_risk_review_rows": sum(1 for item in items if item.get("candidate_review_risk") == "low"),
        "medium_risk_review_rows": sum(1 for item in items if item.get("candidate_review_risk") == "medium"),
        "high_risk_review_rows": sum(1 for item in items if item.get("candidate_review_risk") == "high"),
        "can_import_now_rows": sum(
            1 for item in items if (item.get("import_readiness") or {}).get("can_import_now")
        ),
        "blocked_manual_review_rows": len(items),
        "manual_confirmation_required": True,
        "auto_apply_enabled": False,
    }

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "ensky_cache_candidate_action_queue",
        "summary": {
            "candidate_action_rows": len(items),
            "action_batch_count": len(batches),
            "batch_size": batch_size,
            "manual_confirmed_true": sum(1 for item in items if item.get("manual_confirmed") is True),
            "identity_warning_rows": sum(1 for item in items if item.get("candidate_identity_flags")),
            "candidate_source_url_ready_rows": import_readiness["candidate_source_url_ready_rows"],
            "candidate_image_url_ready_rows": import_readiness["candidate_image_url_ready_rows"],
            "safe_exact_top_candidate_rows": import_readiness["safe_exact_top_candidate_rows"],
            "low_risk_review_rows": import_readiness["low_risk_review_rows"],
            "medium_risk_review_rows": import_readiness["medium_risk_review_rows"],
            "high_risk_review_rows": import_readiness["high_risk_review_rows"],
            "can_import_now_rows": import_readiness["can_import_now_rows"],
            "blocked_manual_review_rows": import_readiness["blocked_manual_review_rows"],
            "by_affiliation": counter_rows(items, "affiliation"),
            "by_category": counter_rows(items, "category"),
            "by_candidate_review_risk": counter_rows(items, "candidate_review_risk"),
            "by_candidate_identity_flag": counter_list_values(items, "candidate_identity_flags"),
            "auto_apply_enabled": False,
        },
        "import_readiness": import_readiness,
        "instructions": [
            "These are broad Ensky sitemap cache candidates, not safe automatic matches.",
            "Only exact product, character, variant, and goods-type matches may be manually confirmed.",
            "Do not import source_url or image_url unless manual_confirmed is set true after review.",
        ],
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
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), batch_size=args.batch_size)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
