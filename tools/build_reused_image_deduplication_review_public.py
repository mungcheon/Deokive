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
DATA = ROOT / "data"
DEFAULT_REUSED_IMAGE_REVIEW = DATA / "catalog_reused_image_review_public.json"
DEFAULT_OUTPUT = DATA / "catalog_reused_image_deduplication_review_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _present(value: Any) -> str:
    return str(value or "").strip()


def _unique(values: list[Any]) -> list[str]:
    return sorted({_present(value) for value in values if _present(value)})


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _is_online_kuji_row(row: dict[str, Any]) -> bool:
    source_url = _present(row.get("source_url"))
    source_store = _present(row.get("source_store"))
    return "online-kuji.chiikawamarket.jp/store/lottery/" in source_url or source_store == "치이카와 온라인 쿠지"


def _rank_token(row: dict[str, Any]) -> str:
    for value in (row.get("name_ja"), row.get("name_ko")):
        text = _present(value)
        if not text:
            continue
        for delimiter in ("賞", "상"):
            if delimiter in text:
                return text.split(delimiter, 1)[0][-1:].upper()
        if " - " in text:
            tail = text.rsplit(" - ", 1)[-1].strip()
            if tail:
                return tail.split(" ", 1)[0].upper()
    return ""


def _identity_score(row: dict[str, Any]) -> int:
    score = 0
    for field in ("name_ko", "name_ja", "source_url", "image_url", "local_image_path"):
        if _present(row.get(field)):
            score += 2
    for field in ("category", "character_name", "affiliation", "series_name", "sub_series"):
        if _present(row.get(field)):
            score += 1
    score += min(len(_present(row.get("name_ja"))), 80) // 20
    score += min(len(_present(row.get("name_ko"))), 80) // 20
    return score


def _manual_template(group: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(
        rows,
        key=lambda row: (_identity_score(row), int(row.get("catalog_index") or -1)),
        reverse=True,
    )
    suggested_keep = ranked[0].get("catalog_index") if ranked else None
    suggested_drop = [
        row.get("catalog_index")
        for row in ranked[1:]
        if isinstance(row.get("catalog_index"), int)
    ]
    return {
        "manual_confirmed": False,
        "decision": "",
        "allowed_decisions": [
            "same_sellable_product_keep_one",
            "campaign_or_variant_keep_separate",
            "wrong_shared_image_clear_or_replace",
            "needs_more_evidence",
        ],
        "suggested_keep_catalog_index": suggested_keep,
        "suggested_drop_catalog_indexes": suggested_drop,
        "manual_keep_catalog_index": None,
        "manual_drop_catalog_indexes": [],
        "evidence_urls": group.get("source_urls") or [],
        "manual_note": "",
        "required_checks": [
            "Confirm both rows point to the same official campaign URL.",
            "Confirm prize rank and item/variant name are the same sellable product.",
            "Keep separate if either row is a reissue, channel variant, or different campaign wave.",
            "Do not delete until manual_confirmed is true.",
        ],
    }


def build_report(
    reused_image_review: dict[str, Any],
    *,
    generated_at: str | None = None,
    max_groups: int = 80,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    skipped_reasons: Counter[str] = Counter()
    for group in _rows(reused_image_review.get("groups")):
        rows = _rows(group.get("rows"))
        if group.get("risk") != "medium":
            skipped_reasons["risk_not_medium"] += 1
            continue
        if group.get("recommended_action") != "review_possible_duplicate_or_reissue_before_keep":
            skipped_reasons["not_duplicate_or_reissue_lane"] += 1
            continue
        if len(rows) < 2:
            skipped_reasons["single_row_group"] += 1
            continue
        if not all(_is_online_kuji_row(row) for row in rows):
            skipped_reasons["not_all_online_kuji_rows"] += 1
            continue

        source_urls = _unique([row.get("source_url") for row in rows])
        image_urls = _unique([row.get("image_url") for row in rows])
        local_image_paths = _unique(
            [row.get("local_image_path") for row in rows] + [group.get("local_image_path")]
        )
        categories = _unique([row.get("category") for row in rows])
        characters = _unique([row.get("character_name") for row in rows])
        rank_tokens = _unique([_rank_token(row) for row in rows])
        source_url_same = len(source_urls) == 1
        image_same = len(image_urls) == 1 and len(local_image_paths) == 1
        category_same = len(categories) == 1
        character_same = len(characters) == 1
        rank_same = len(rank_tokens) <= 1
        confidence = (
            "strong_manual_duplicate_candidate"
            if source_url_same and image_same and category_same and character_same and rank_same
            else "manual_identity_review_candidate"
        )
        candidates.append(
            {
                "group_index": len(candidates) + 1,
                "local_image_path": group.get("local_image_path"),
                "row_count": len(rows),
                "confidence": confidence,
                "source_url_same": source_url_same,
                "image_same": image_same,
                "category_same": category_same,
                "character_same": character_same,
                "rank_same": rank_same,
                "source_urls": source_urls,
                "image_urls": image_urls,
                "local_image_paths": local_image_paths,
                "categories": categories,
                "characters": characters,
                "rank_tokens": rank_tokens,
                "reason": "online_kuji_same_image_same_character_distinct_names",
                "rows": rows,
                "decision_template": _manual_template(group, rows),
            }
        )

    confidence_counts = Counter(row["confidence"] for row in candidates)
    candidates.sort(
        key=lambda row: (
            0 if row["confidence"] == "strong_manual_duplicate_candidate" else 1,
            -int(row.get("row_count") or 0),
            str(row.get("local_image_path") or ""),
        )
    )
    selected = candidates[:max_groups]
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "catalog_reused_image_deduplication_review",
        "summary": {
            "candidate_groups": len(candidates),
            "queued_groups": len(selected),
            "max_groups": max_groups,
            "candidate_rows": sum(int(row.get("row_count") or 0) for row in candidates),
            "queued_rows": sum(int(row.get("row_count") or 0) for row in selected),
            "strong_manual_duplicate_candidate_groups": confidence_counts.get(
                "strong_manual_duplicate_candidate",
                0,
            ),
            "manual_identity_review_candidate_groups": confidence_counts.get(
                "manual_identity_review_candidate",
                0,
            ),
            "skipped_reasons": [[key, value] for key, value in skipped_reasons.most_common()],
            "auto_delete_enabled": False,
            "auto_merge_enabled": False,
        },
        "automation_policy": {
            "manual_review_required_before_mutation": True,
            "reason": "Shared image and source evidence can indicate a duplicate, but prize/campaign identity must be confirmed before deleting or merging.",
        },
        "items": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build manual dedupe candidates from reused public catalog images."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_REUSED_IMAGE_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-groups", type=int, default=80)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(_load_json(args.input), max_groups=args.max_groups)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
