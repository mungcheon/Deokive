from __future__ import annotations

import argparse
import json
import re
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
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_JSON_OUTPUT = DATA / "catalog_reused_image_review_public.json"
DEFAULT_MD_OUTPUT = DATA / "catalog_reused_image_review_public.md"

PLACEHOLDER_HINTS = (
    "ogp",
    "placeholder",
    "noimage",
    "no_image",
    "logo",
    "banner",
    "common",
)
LINEUP_HINTS = (
    "trading",
    "トレーディング",
    "랜덤",
    "라인업",
    "세트",
    "set",
    "vol.",
    "vol ",
    "collection",
    "컬렉션",
    "コレクション",
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a list or object with items")
    return [row for row in rows if isinstance(row, dict)]


def _present(value: Any) -> str:
    return str(value or "").strip()


def _unique(rows: list[dict[str, Any]], field: str) -> list[str]:
    return sorted({_present(row.get(field)) for row in rows if _present(row.get(field))})


def _normalized_name(value: Any) -> str:
    return re.sub(r"[\W_]+", "", _present(value).lower())


def _unique_names(rows: list[dict[str, Any]]) -> list[str]:
    names = set()
    for row in rows:
        name = row.get("name_ja") or row.get("name_ko") or row.get("name_en")
        normalized = _normalized_name(name)
        if normalized:
            names.add(normalized)
    return sorted(names)


def _haystack(rows: list[dict[str, Any]], local_image_path: str) -> str:
    parts = [local_image_path]
    for row in rows:
        parts.extend(
            _present(row.get(field))
            for field in (
                "name_ko",
                "name_ja",
                "name_en",
                "category",
                "character_name",
                "affiliation",
                "series_name",
                "sub_series",
                "image_url",
                "source_url",
            )
        )
    return " ".join(parts).lower()


def _risk_for_group(local_image_path: str, rows: list[dict[str, Any]]) -> tuple[str, list[str], str]:
    affiliations = _unique(rows, "affiliation")
    categories = _unique(rows, "category")
    characters = _unique(rows, "character_name")
    names = _unique_names(rows)
    source_urls = _unique(rows, "source_url")
    image_urls = _unique(rows, "image_url")
    text = _haystack(rows, local_image_path)
    reasons: list[str] = []

    if any(hint in text for hint in PLACEHOLDER_HINTS):
        reasons.append("placeholder_or_non_product_image_hint")
    if len(affiliations) > 1:
        reasons.append("shared_across_multiple_affiliations")
    if len(categories) > 1:
        reasons.append("shared_across_multiple_categories")
    if len(source_urls) > 1:
        reasons.append("shared_across_multiple_source_urls")
    if len(characters) > 1:
        reasons.append("shared_across_multiple_characters")
    if len(image_urls) > 1:
        reasons.append("different_image_urls_share_one_local_path")
    if len(names) > 1 and len(characters) <= 1:
        reasons.append("same_character_image_reused_for_distinct_names")
    if len(image_urls) == 1 and len(source_urls) > 1:
        reasons.append("same_image_url_used_for_distinct_source_urls")

    lineup_like = any(hint in text for hint in LINEUP_HINTS)
    if lineup_like:
        reasons.append("lineup_or_trading_image_possible")

    if (
        "placeholder_or_non_product_image_hint" in reasons
        or "different_image_urls_share_one_local_path" in reasons
        or len(affiliations) > 1
    ):
        return "high", reasons, "clear_or_replace_after_manual_identity_review"
    if len(categories) > 1:
        return "medium", reasons, "review_category_mismatch_before_keep"
    if "same_character_image_reused_for_distinct_names" in reasons:
        return "medium", reasons, "review_possible_duplicate_or_reissue_before_keep"
    if len(characters) > 1 and len(source_urls) > 1 and not lineup_like:
        return "medium", reasons, "review_shared_character_images_before_keep"
    return "low", reasons, "likely_lineup_or_set_image_review_later"


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "affiliation": row.get("affiliation"),
        "category": row.get("category"),
        "character_name": row.get("character_name"),
        "series_name": row.get("series_name"),
        "sub_series": row.get("sub_series"),
        "image_url": row.get("image_url"),
        "source_url": row.get("source_url"),
        "source_store": row.get("source_store"),
    }


def build_report(items: list[dict[str, Any]], generated_at: str | None = None) -> dict[str, Any]:
    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        local_image_path = _present(row.get("local_image_path"))
        image_url = _present(row.get("image_url"))
        if local_image_path and image_url:
            by_path[local_image_path].append(row)

    groups: list[dict[str, Any]] = []
    for local_image_path, rows in by_path.items():
        if len(rows) < 2:
            continue
        risk, reasons, recommended_action = _risk_for_group(local_image_path, rows)
        groups.append(
            {
                "local_image_path": local_image_path,
                "row_count": len(rows),
                "risk": risk,
                "reasons": reasons,
                "recommended_action": recommended_action,
                "affiliations": _unique(rows, "affiliation"),
                "categories": _unique(rows, "category"),
                "characters": _unique(rows, "character_name"),
                "source_urls": _unique(rows, "source_url"),
                "image_urls": _unique(rows, "image_url"),
                "rows": [_compact_row(row) for row in sorted(rows, key=lambda value: value.get("catalog_index") or 0)],
            }
        )

    risk_order = {"high": 0, "medium": 1, "low": 2}
    groups.sort(key=lambda group: (risk_order[group["risk"]], -group["row_count"], group["local_image_path"]))
    risk_counts = Counter(group["risk"] for group in groups)
    recommended_next_action = "archive_reused_image_review_clean"
    if risk_counts.get("high", 0):
        recommended_next_action = "review_high_risk_groups_first"
    elif risk_counts.get("medium", 0):
        recommended_next_action = "review_medium_risk_groups_before_next_image_import"
    elif risk_counts.get("low", 0):
        recommended_next_action = "review_low_risk_lineup_or_set_images_later"
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "catalog_reused_image_review",
        "summary": {
            "catalog_rows": len(items),
            "reused_image_groups": len(groups),
            "high_risk_groups": risk_counts.get("high", 0),
            "medium_risk_groups": risk_counts.get("medium", 0),
            "low_risk_groups": risk_counts.get("low", 0),
            "review_rows": sum(group["row_count"] for group in groups),
            "recommended_next_action": recommended_next_action,
        },
        "groups": groups,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# Catalog Reused Image Review",
        "",
        f"- Reused image groups: `{summary['reused_image_groups']}`",
        f"- High risk groups: `{summary['high_risk_groups']}`",
        f"- Medium risk groups: `{summary['medium_risk_groups']}`",
        f"- Low risk groups: `{summary['low_risk_groups']}`",
        f"- Review rows: `{summary['review_rows']}`",
        "",
        "## Groups",
        "",
    ]
    for group in report["groups"]:
        lines.append(
            f"### {group['risk'].upper()} - {group['local_image_path']} ({group['row_count']} rows)"
        )
        lines.append(f"- Action: `{group['recommended_action']}`")
        lines.append(f"- Reasons: `{', '.join(group['reasons'])}`")
        lines.append(f"- Affiliations: `{', '.join(group['affiliations'])}`")
        lines.append(f"- Categories: `{', '.join(group['categories'])}`")
        for row in group["rows"][:12]:
            lines.append(
                f"- `{row.get('catalog_index')}` {row.get('name_ko')} / {row.get('name_ja')} "
                f"({row.get('affiliation')}, {row.get('category')})"
            )
        if len(group["rows"]) > 12:
            lines.append(f"- ... {len(group['rows']) - 12} more rows")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a public review report for reused catalog images.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(_load_items(args.catalog))
    if args.write:
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_markdown(report, args.markdown_output)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.write:
        print(f"JSON: {args.json_output}")
        print(f"Markdown: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
