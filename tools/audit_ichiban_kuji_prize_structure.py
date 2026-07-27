from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from import_ichiban_kuji_history import _extract_tier

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_CAMPAIGNS = ROOT / "data" / "intake" / "sources" / "ichiban_kuji_campaigns.json"
DEFAULT_JSON_REPORT = ROOT / "server" / "ichiban_kuji_prize_structure_audit.json"
DEFAULT_MD_REPORT = ROOT / "server" / "ichiban_kuji_prize_structure_audit.md"
DEFAULT_ARCHIVE = ROOT / "server" / "ichiban_non_prize_archived_rows.json"

GENERIC_MULTI_VARIANT_ITEM_TOKENS = (
    "\u30a2\u30bd\u30fc\u30c8",
    "\u5168",
    "\u30c8\u30ec\u30fc\u30c7\u30a3\u30f3\u30b0",
    "\u30e9\u30f3\u30c0\u30e0",
    "\u30b3\u30ec\u30af\u30b7\u30e7\u30f3",
)

LIKELY_CHARACTER_SPLIT_ITEM_TOKENS = (
    "\u7f36\u30d0\u30c3\u30b8",
    "\u30d0\u30c3\u30b8",
    "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
    "\u30a2\u30af\u30b9\u30bf",
    "\u30a2\u30af\u30ea\u30eb\u30c1\u30e3\u30fc\u30e0",
    "\u30e9\u30d0\u30fc\u30c1\u30e3\u30fc\u30e0",
    "\u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
    "\u30af\u30ea\u30a2\u30d5\u30a1\u30a4\u30eb",
    "\u30b9\u30c6\u30c3\u30ab\u30fc",
    "\u30bf\u30aa\u30eb",
    "\u30dd\u30b9\u30bf\u30fc",
)

UNREVIEWED_CHARACTER_LABELS = {"", "\uae30\ud0c0"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", "--seed", dest="catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--campaigns", type=Path, default=DEFAULT_CAMPAIGNS)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    args = parser.parse_args()

    rows = _read_catalog_rows(args.catalog)
    campaigns = _read_json_list(args.campaigns)

    prize_rows = [
        row
        for row in rows
        if isinstance(row, dict) and "1kuji.com/products/" in str(row.get("source_url") or "")
    ]
    campaign_urls = {
        _normalize_url(str(item.get("url") or ""))
        for item in campaigns
        if isinstance(item, dict) and item.get("url")
    }
    seeded_urls = {
        _normalize_url(str(row.get("source_url") or ""))
        for row in prize_rows
        if row.get("source_url")
    } | archived_campaign_urls(args.archive)

    missing_sub_series: list[dict[str, Any]] = []
    fillable_sub_series: list[dict[str, Any]] = []
    under_split_prize_review_candidates: list[dict[str, Any]] = []
    tier_counter: Counter[str] = Counter()
    rows_by_url: dict[str, int] = defaultdict(int)
    rows_by_url_tier: dict[tuple[str, str], int] = defaultdict(int)
    missing_sub_series_by_url: dict[str, int] = defaultdict(int)

    for row in prize_rows:
        source_url = str(row.get("source_url") or "")
        rows_by_url[source_url] += 1
        sub_series = str(row.get("sub_series") or "").strip()
        rows_by_url_tier[(source_url, sub_series)] += 1
        if sub_series:
            tier_counter[sub_series] += 1
            continue

        name_ja = str(row.get("name_ja") or "").strip()
        inferred = _extract_tier(name_ja) if name_ja else None
        item = {
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
            "source_url": source_url,
            "inferred_sub_series": inferred,
        }
        missing_sub_series.append(item)
        missing_sub_series_by_url[source_url] += 1
        if inferred:
            fillable_sub_series.append(item)

    for row in prize_rows:
        source_url = str(row.get("source_url") or "")
        sub_series = str(row.get("sub_series") or "").strip()
        if not sub_series or rows_by_url_tier[(source_url, sub_series)] != 1:
            continue
        product_name = _product_name_from_display(str(row.get("name_ko") or ""), sub_series)
        name_ja = str(row.get("name_ja") or "")
        review_text = f"{product_name} {name_ja}"
        character_name = str(row.get("character_name") or "").strip()
        if character_name not in UNREVIEWED_CHARACTER_LABELS:
            continue
        if _looks_like_under_split_character_prize(review_text):
            under_split_prize_review_candidates.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "source_url": source_url,
                    "sub_series": sub_series,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "product_name": product_name,
                    "character_name": row.get("character_name"),
                    "reason": "single_generic_variant_row_may_need_one_row_per_character",
                }
            )

    campaign_without_seed_rows = sorted(campaign_urls - seeded_urls)
    report = {
        "catalog": str(args.catalog),
        "campaigns": str(args.campaigns),
        "archive": str(args.archive),
        "campaign_count": len(campaign_urls),
        "seeded_campaign_url_count": len(seeded_urls),
        "campaign_without_seed_rows_count": len(campaign_without_seed_rows),
        "prize_rows": len(prize_rows),
        "missing_sub_series_rows": len(missing_sub_series),
        "fillable_sub_series_rows": len(fillable_sub_series),
        "under_split_prize_review_candidate_rows": len(under_split_prize_review_candidates),
        "tier_counts": tier_counter.most_common(),
        "campaign_without_seed_rows": campaign_without_seed_rows,
        "missing_sub_series_by_url": sorted(
            (
                {"source_url": url, "rows": rows_by_url[url], "missing_sub_series_rows": missing}
                for url, missing in missing_sub_series_by_url.items()
            ),
            key=lambda item: (item["missing_sub_series_rows"], item["source_url"]),
            reverse=True,
        ),
        "fillable_sub_series": fillable_sub_series,
        "fillable_sub_series_sample": fillable_sub_series[:100],
        "manual_sub_series_sample": [item for item in missing_sub_series if not item["inferred_sub_series"]][:100],
        "under_split_prize_review_candidates": under_split_prize_review_candidates[:250],
    }

    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_report.write_text(_markdown_report(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "campaign_count": report["campaign_count"],
                "seeded_campaign_url_count": report["seeded_campaign_url_count"],
                "campaign_without_seed_rows_count": report["campaign_without_seed_rows_count"],
                "prize_rows": report["prize_rows"],
                "missing_sub_series_rows": report["missing_sub_series_rows"],
                "fillable_sub_series_rows": report["fillable_sub_series_rows"],
                "under_split_prize_review_candidate_rows": report["under_split_prize_review_candidate_rows"],
                "json": str(args.json_report),
                "markdown": str(args.md_report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _read_json_list(path: Path) -> list[Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise SystemExit(f"{path} must contain a JSON list")
    return payload


def _read_catalog_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{path} must contain a JSON list or an object with items")
    return [row for row in rows if isinstance(row, dict)]


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def archived_campaign_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        return set()
    urls: set[str] = set()
    for item in payload:
        row = item.get("row") if isinstance(item, dict) else None
        if not isinstance(row, dict):
            continue
        source_url = str(row.get("source_url") or "")
        if "1kuji.com/products/" in source_url:
            urls.add(_normalize_url(source_url))
    return urls


def _product_name_from_display(name_ko: str, sub_series: str) -> str:
    parts = [part.strip() for part in name_ko.split(" / ")]
    if len(parts) >= 4:
        prize_index = 1
        if sub_series:
            for index, part in enumerate(parts[1:-1], start=1):
                if part == sub_series:
                    prize_index = index
                    break
        return " / ".join(parts[prize_index + 1 : -1]).strip()

    marker = f" - {sub_series} "
    if sub_series and marker in name_ko:
        return name_ko.split(marker, 1)[1].strip()
    return ""


def _looks_like_under_split_character_prize(value: str) -> bool:
    if not value:
        return False
    has_generic_variant_marker = any(token in value for token in GENERIC_MULTI_VARIANT_ITEM_TOKENS)
    has_character_split_item = any(token in value for token in LIKELY_CHARACTER_SPLIT_ITEM_TOKENS)
    return has_generic_variant_marker and has_character_split_item


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Ichiban Kuji prize structure audit",
        "",
        f"- Campaigns discovered: {report['campaign_count']}",
        f"- Campaign URLs represented in catalog: {report['seeded_campaign_url_count']}",
        f"- Archive file: {report['archive']}",
        f"- Campaign URLs without catalog rows: {report['campaign_without_seed_rows_count']}",
        f"- Prize rows: {report['prize_rows']}",
        f"- Rows missing sub_series: {report['missing_sub_series_rows']}",
        f"- Rows with safely inferred sub_series candidate: {report['fillable_sub_series_rows']}",
        f"- Single generic prize rows needing character split review: {report['under_split_prize_review_candidate_rows']}",
        "",
        "## Tier Counts",
        "",
    ]
    for tier, count in report["tier_counts"][:30]:
        lines.append(f"- {tier}: {count}")
    lines.extend(["", "## Next Safe Actions", ""])
    lines.append("- Apply only `fillable_sub_series_sample` rows after reviewing exact name_ja tier extraction.")
    lines.append("- Split rows in `under_split_prize_review_candidates` only after confirming character variants on the official campaign page.")
    lines.append("- Keep `manual_sub_series_sample` out of automatic writes until product-page structure is confirmed.")
    lines.append("- Treat campaign URLs without catalog rows as an extraction/404 review queue, not as generated rows.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
