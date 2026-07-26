from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_JSON_REPORT = ROOT / "server" / "ichiban_variant_completeness_audit.json"
DEFAULT_MD_REPORT = ROOT / "server" / "ichiban_variant_completeness_audit.md"

FRACTION_RE = re.compile(r"[(（](\d+)\s*/\s*(\d+)[)）]")
COUNT_RE = re.compile(r"(?:全\s*)?(\d+)\s*種")
ASSORT_RE = re.compile(r"(アソート|コレクション|ランダム|選べる|各種)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    args = parser.parse_args()

    rows = _read_catalog_items(args.catalog)
    ichiban_rows = [row for row in rows if _is_ichiban(row)]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in ichiban_rows:
        groups[(_text(row.get("source_url")), _text(row.get("sub_series")))].append(row)

    incomplete_fraction_groups: list[dict[str, Any]] = []
    count_marker_review_groups: list[dict[str, Any]] = []
    complete_fraction_groups = 0

    for (source_url, tier), group_rows in sorted(
        groups.items(), key=lambda item: min(_int(row.get("catalog_index")) for row in item[1])
    ):
        parsed = [_variant_fraction(row) for row in group_rows]
        parsed = [item for item in parsed if item is not None]
        if parsed:
            expected_total = max(total for _row, _current, total in parsed)
            present = sorted({current for _row, current, total in parsed if total == expected_total})
            missing = [number for number in range(1, expected_total + 1) if number not in present]
            if missing:
                incomplete_fraction_groups.append(
                    {
                        "source_url": source_url,
                        "series_name": group_rows[0].get("series_name"),
                        "sub_series": tier,
                        "expected_variant_count": expected_total,
                        "present_variant_numbers": present,
                        "missing_variant_numbers": missing,
                        "rows": [_row_summary(row) for row in group_rows],
                    }
                )
            else:
                complete_fraction_groups += 1
            continue

        expected_count = _expected_count_marker(group_rows)
        if expected_count and expected_count > len(group_rows):
            count_marker_review_groups.append(
                {
                    "source_url": source_url,
                    "series_name": group_rows[0].get("series_name"),
                    "sub_series": tier,
                    "expected_variant_count": expected_count,
                    "present_row_count": len(group_rows),
                    "reason": "count_or_assort_marker_without_fraction_rows",
                    "rows": [_row_summary(row) for row in group_rows],
                }
            )

    report = {
        "schema_version": 1,
        "catalog": str(args.catalog),
        "ichiban_rows": len(ichiban_rows),
        "ichiban_source_tier_groups": len(groups),
        "complete_fraction_groups": complete_fraction_groups,
        "incomplete_fraction_groups_count": len(incomplete_fraction_groups),
        "count_marker_review_groups_count": len(count_marker_review_groups),
        "incomplete_fraction_groups": incomplete_fraction_groups,
        "count_marker_review_groups": count_marker_review_groups,
    }
    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_report.write_text(_markdown_report(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "ichiban_rows": report["ichiban_rows"],
                "ichiban_source_tier_groups": report["ichiban_source_tier_groups"],
                "complete_fraction_groups": report["complete_fraction_groups"],
                "incomplete_fraction_groups_count": report["incomplete_fraction_groups_count"],
                "count_marker_review_groups_count": report["count_marker_review_groups_count"],
                "json": str(args.json_report),
                "markdown": str(args.md_report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _read_catalog_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        payload = payload.get("items")
    if not isinstance(payload, list):
        raise SystemExit(f"{path} must contain a JSON list or an object with items")
    return [row for row in payload if isinstance(row, dict)]


def _is_ichiban(row: dict[str, Any]) -> bool:
    return "1kuji.com/products/" in _text(row.get("source_url"))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 10**9


def _variant_fraction(row: dict[str, Any]) -> tuple[dict[str, Any], int, int] | None:
    text = " ".join(_text(row.get(key)) for key in ("name_ja", "name_ko"))
    match = FRACTION_RE.search(text)
    if not match:
        return None
    current, total = int(match.group(1)), int(match.group(2))
    if current < 1 or total < 2 or current > total:
        return None
    return row, current, total


def _expected_count_marker(rows: list[dict[str, Any]]) -> int | None:
    best: int | None = None
    for row in rows:
        text = " ".join(_text(row.get(key)) for key in ("name_ja", "name_ko"))
        if not ASSORT_RE.search(text):
            continue
        for match in COUNT_RE.finditer(text):
            value = int(match.group(1))
            if value > 1:
                best = max(best or 0, value)
    return best


def _row_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "character_name": row.get("character_name"),
        "image_url": row.get("image_url"),
        "local_image_path": row.get("local_image_path"),
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Ichiban Kuji Variant Completeness Audit",
        "",
        f"- Ichiban rows: {report['ichiban_rows']}",
        f"- Source/tier groups: {report['ichiban_source_tier_groups']}",
        f"- Complete numbered variant groups: {report['complete_fraction_groups']}",
        f"- Incomplete numbered variant groups: {report['incomplete_fraction_groups_count']}",
        f"- Count-marker review groups: {report['count_marker_review_groups_count']}",
        "",
        "## Incomplete Numbered Groups",
        "",
    ]
    for item in report["incomplete_fraction_groups"][:40]:
        lines.append(
            f"- {item['series_name']} / {item['sub_series']}: "
            f"expected {item['expected_variant_count']}, missing {item['missing_variant_numbers']}"
        )
    lines.extend(["", "## Count-Marker Review Groups", ""])
    for item in report["count_marker_review_groups"][:40]:
        lines.append(
            f"- {item['series_name']} / {item['sub_series']}: "
            f"marker says {item['expected_variant_count']}, rows {item['present_row_count']}"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
