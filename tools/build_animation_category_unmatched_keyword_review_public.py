from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_animation_category_split_review_public as split_review


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPLIT_REVIEW = ROOT / "data" / "animation_category_split_review_public.json"
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "animation_category_unmatched_keyword_review_public.json"

STOPWORDS = {
    "goods",
    "グッズ",
    "굿즈",
    "一番くじ",
    "the",
    "and",
    "with",
    "ver",
    "vol",
    "cm",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _catalog_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("items", [])
    return [row for row in rows if isinstance(row, dict)]


def _text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "series_name", "sub_series", "source_store")
        if str(row.get(field) or "").strip()
    )


def _tokens(text: str) -> list[str]:
    found = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[가-힣]{2,}|[ァ-ヴー]{2,}|[一-龯々]{2,}", text)
    return [token for token in found if token.casefold() not in STOPWORDS]


def _sample(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "category": row.get("category"),
        "affiliation": row.get("affiliation"),
        "series_name": row.get("series_name"),
        "sub_series": row.get("sub_series"),
        "source_store": row.get("source_store"),
    }


def _source_rules(split_payload: dict[str, Any]) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {}
    for item in split_payload.get("review_items", []):
        if not isinstance(item, dict):
            continue
        keywords: list[str] = []
        for candidate in item.get("split_candidates", []):
            if isinstance(candidate, dict):
                keywords.extend(str(keyword) for keyword in candidate.get("match_keywords", []) if str(keyword))
        rules[str(item.get("source_category") or "")] = keywords
    return rules


def _is_unmatched(row: dict[str, Any], keywords: list[str]) -> bool:
    value = _text(row).casefold()
    return not any(keyword.casefold() in value for keyword in keywords)


def _ranked_groups(rows: list[dict[str, Any]], field: str, *, limit: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = str(row.get(field) or "").strip() or "(blank)"
        grouped[value].append(row)
    ranked = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:limit]
    return [
        {
            field: value,
            "row_count": len(group_rows),
            "sample_rows": [_sample(row) for row in group_rows[:6]],
        }
        for value, group_rows in ranked
    ]


def _token_candidates(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    token_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seen: set[str] = set()
        for token in _tokens(_text(row)):
            if token in seen:
                continue
            seen.add(token)
            token_rows[token].append(row)
    ranked = sorted(token_rows.items(), key=lambda item: (-len(item[1]), item[0]))[:limit]
    return [
        {
            "token": token,
            "row_count": len(group_rows),
            "sample_rows": [_sample(row) for row in group_rows[:6]],
            "manual_confirmed": False,
            "suggested_use": "review_as_keyword_candidate",
        }
        for token, group_rows in ranked
    ]


def build_report(split_payload: dict[str, Any], catalog_payload: dict[str, Any], *, limit: int = 20) -> dict[str, Any]:
    rows = _catalog_rows(catalog_payload)
    rules = _source_rules(split_payload)
    review_items: list[dict[str, Any]] = []
    for source_category, keywords in sorted(rules.items()):
        source_rows = [row for row in rows if str(row.get("category") or "").strip() == source_category]
        unmatched = [row for row in source_rows if _is_unmatched(row, keywords)]
        review_items.append(
            {
                "source_category": source_category,
                "source_category_rows": len(source_rows),
                "unmatched_rows": len(unmatched),
                "current_keyword_count": len(keywords),
                "top_token_candidates": _token_candidates(unmatched, limit=limit),
                "top_series": _ranked_groups(unmatched, "series_name", limit=10),
                "top_sub_series": _ranked_groups(unmatched, "sub_series", limit=10),
                "top_source_stores": _ranked_groups(unmatched, "source_store", limit=10),
                "sample_unmatched_rows": [_sample(row) for row in unmatched[:12]],
                "automation_policy": {
                    "auto_apply_keywords": False,
                    "requires_manual_review": True,
                    "reason": "Unmatched broad categories can mix product types, series names, and store labels.",
                },
            }
        )

    token_candidate_count = sum(len(item["top_token_candidates"]) for item in review_items)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "animation_category_unmatched_keyword_review",
        "summary": {
            "source_categories": len(review_items),
            "source_category_rows": sum(int(item["source_category_rows"]) for item in review_items),
            "unmatched_rows": sum(int(item["unmatched_rows"]) for item in review_items),
            "token_candidate_count": token_candidate_count,
            "manual_confirmed_rows": 0,
            "auto_apply_enabled": False,
        },
        "review_items": review_items,
        "instructions": [
            "Use top_token_candidates only as review hints, not as automatic category changes.",
            "Prefer product-type keywords over series, character, or store-only words.",
            "Add a split rule only when sample rows consistently share the same goods type.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-review", type=Path, default=DEFAULT_SPLIT_REVIEW)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    report = build_report(_load(args.split_review), _load(args.catalog), limit=args.limit)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
