from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

try:
    from catalog_quality_report import build_report, load_catalog_rows
except ImportError:
    from tools.catalog_quality_report import build_report, load_catalog_rows


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_JSON = ROOT / "server" / "ichiban_public_quality_queue.json"
DEFAULT_CSV = ROOT / "server" / "ichiban_public_quality_queue.csv"
DEFAULT_HTML = ROOT / "server" / "ichiban_public_quality_queue.html"


def build_queue(quality_report: dict[str, Any]) -> dict[str, Any]:
    ichiban = quality_report.get("ichiban_kuji") or {}
    campaign_gap_urls = ichiban.get("campaign_gap_urls")
    if not isinstance(campaign_gap_urls, list):
        campaign_gap_urls = ichiban.get("campaign_gap_sample", [])
    gap_items = [
        {
            "workflow": "campaign_gap_research",
            "priority": 10,
            "status": "needs_official_or_archive_evidence",
            "source_url": url,
            "research_links": _campaign_research_links(url),
            "decision_options": [
                "add_missing_campaign_rows_only_after_official_or_archive_evidence",
                "mark_campaign_seed_as_unusable_if_no_evidence_exists",
            ],
            "acceptance_criteria": [
                "Campaign URL must resolve through an official 1kuji page, official cache, or trusted archive.",
                "Do not create prize rows from title-only search results.",
                "Imported prize rows must follow release / rank / prize / character naming.",
            ],
            "recommended_action": (
                "Find replacement official/archive evidence before creating or importing prize rows."
            ),
            "auto_apply_enabled": False,
        }
        for url in campaign_gap_urls
        if isinstance(url, str) and url.strip()
    ]

    duplicate_items: list[dict[str, Any]] = []
    duplicate_review_groups = ichiban.get("exact_display_duplicate_review")
    if not isinstance(duplicate_review_groups, list):
        duplicate_review_groups = ichiban.get("exact_display_duplicate_review_sample", [])
    for group in duplicate_review_groups:
        if not isinstance(group, dict):
            continue
        source_urls = group.get("source_urls") or []
        if not isinstance(source_urls, list):
            source_urls = []
        catalog_indexes = group.get("catalog_indexes") or []
        if not isinstance(catalog_indexes, list):
            catalog_indexes = []
        source_families = sorted({_campaign_family(str(url)) for url in source_urls if url})
        duplicate_kind = _duplicate_review_kind(source_urls, catalog_indexes)
        duplicate_items.append(
            {
                "workflow": "exact_display_duplicate_reissue_review",
                "priority": 20,
                "status": "needs_reissue_or_duplicate_decision",
                "display_name": group.get("display_name"),
                "row_count": group.get("rows"),
                "source_urls": source_urls,
                "source_url_count": len(source_urls),
                "source_families": source_families,
                "catalog_indexes": catalog_indexes,
                "duplicate_review_kind": duplicate_kind,
                "decision_options": _duplicate_decision_options(duplicate_kind),
                "acceptance_criteria": [
                    "Keep both rows only when source URLs prove separate campaigns, reissues, or release dates.",
                    "Merge only when product identity, campaign, rank, prize, character, and source evidence are the same.",
                    "If kept as reissues, add distinguishing release metadata or source-specific note before clearing this queue.",
                ],
                "recommended_action": (
                    "Confirm whether rows are separate reissues/campaigns or true duplicates before merging."
                ),
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
            }
        )

    zero_price_items = [
        {
            "workflow": "zero_price_policy_review",
            "priority": 5,
            "status": "unexpected_zero_price",
            "catalog_index": row.get("catalog_index"),
            "display_name": row.get("name_ko"),
            "source_url": row.get("source_url"),
            "recommended_action": (
                "Set normal prize price or confirm this is a last-one/double-chance exception."
            ),
            "decision_options": [
                "set_official_price_jpy_from_campaign_price",
                "mark_as_last_one_or_double_chance_exception",
            ],
            "acceptance_criteria": [
                "Normal prize rows must not keep official_price_jpy at 0.",
                "Last One and Double Chance exceptions may keep official_price_jpy at 0.",
            ],
            "auto_apply_enabled": False,
        }
        for row in ichiban.get("zero_price_non_exception_sample", [])
        if isinstance(row, dict)
    ]

    naming_items: list[dict[str, Any]] = []
    for row in ichiban.get("naming_convention_review_sample", []):
        if not isinstance(row, dict):
            continue
        reason = row.get("reason")
        if reason == "non_prize_or_related_item_needs_classification":
            workflow = "non_prize_related_item_classification"
            recommended_action = (
                "Classify as related/campaign/non-prize goods or find exact prize-rank evidence."
            )
            priority = 30
        else:
            workflow = "display_name_convention_review"
            recommended_action = (
                "Rewrite display_name as release name / prize rank / prize name / character name."
            )
            priority = 25
        naming_items.append(
            {
                "workflow": workflow,
                "priority": priority,
                "status": "needs_display_or_classification_review",
                "catalog_index": row.get("catalog_index"),
                "display_name": row.get("name_ko"),
                "source_url": row.get("source_url"),
                "reason": reason,
                "display_parts": row.get("display_parts") or [],
                "expected_display_format": (
                    "Ichiban Kuji release name / prize rank / prize name / character name"
                ),
                "decision_options": _naming_decision_options(reason),
                "acceptance_criteria": [
                    "Prize rows must have four display parts separated by ' / '.",
                    "The second part must be a prize rank such as A賞, B賞, ラストワン賞, or ダブルチャンス.",
                    "Related or campaign goods must be classified separately instead of pretending to be a prize rank.",
                    "Character-specific variants should be one row per character.",
                ],
                "recommended_action": recommended_action,
                "auto_apply_enabled": False,
            }
        )

    items = zero_price_items + gap_items + duplicate_items + naming_items
    items.sort(
        key=lambda item: (
            int(item.get("priority") or 99),
            str(item.get("source_url") or ""),
            str(item.get("display_name") or ""),
        )
    )
    work_packs = _build_work_packs(items)
    return {
        "source": "data/catalog_public.json",
        "quality_report_source": "server/catalog_quality_report.json",
        "summary": {
            "ichiban_rows": ichiban.get("rows", 0),
            "campaign_count": ichiban.get("campaign_count", 0),
            "seeded_campaign_url_count": ichiban.get("seeded_campaign_url_count", 0),
            "campaign_gap_count": ichiban.get("campaign_gap_count", 0),
            "campaign_gap_queue_rows": len(gap_items),
            "exact_display_duplicate_review_groups": ichiban.get(
                "exact_display_duplicate_review_groups", 0
            ),
            "exact_display_duplicate_review_rows": ichiban.get(
                "exact_display_duplicate_review_rows", 0
            ),
            "exact_display_duplicate_queue_rows": len(duplicate_items),
            "zero_price_exception_rows": ichiban.get("zero_price_exception_rows", 0),
            "zero_price_non_exception_rows": ichiban.get("zero_price_non_exception_rows", 0),
            "zero_price_policy_queue_rows": len(zero_price_items),
            "naming_convention_review_rows": ichiban.get("naming_convention_review_rows", 0),
            "naming_convention_queue_rows": len(naming_items),
            "queue_rows": len(items),
            "work_pack_rows": len(work_packs),
        },
        "items": items,
        "work_packs": work_packs,
        "automation_policy": {
            "auto_merge_duplicates": False,
            "auto_delete_duplicates": False,
            "auto_create_campaign_rows": False,
            "requires_human_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def _build_work_packs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in items:
        workflow = str(item.get("workflow") or "")
        group_key = _pack_group_key(item)
        grouped.setdefault((workflow, group_key), []).append(item)

    packs: list[dict[str, Any]] = []
    for (workflow, group_key), rows in grouped.items():
        first = rows[0]
        packs.append(
            {
                "workflow": workflow,
                "group_key": group_key,
                "priority": first.get("priority"),
                "status": first.get("status"),
                "rows": len(rows),
                "next_action": first.get("recommended_action"),
                "decision_options": first.get("decision_options") or [],
                "acceptance_criteria": first.get("acceptance_criteria") or [],
                "auto_apply_enabled": False,
                "sample_rows": rows[:10],
            }
        )
    packs.sort(
        key=lambda item: (
            int(item.get("priority") or 99),
            str(item.get("workflow") or ""),
            -int(item.get("rows") or 0),
            str(item.get("group_key") or ""),
        )
    )
    return packs


def _pack_group_key(item: dict[str, Any]) -> str:
    workflow = str(item.get("workflow") or "")
    if workflow == "campaign_gap_research":
        source_url = str(item.get("source_url") or "")
        return _campaign_family(source_url)
    if workflow == "exact_display_duplicate_reissue_review":
        source_urls = item.get("source_urls") or []
        if isinstance(source_urls, list) and source_urls:
            families = sorted({_campaign_family(str(url)) for url in source_urls})
            return " + ".join(families)
        return _display_release_name(str(item.get("display_name") or ""))
    if workflow in {"non_prize_related_item_classification", "display_name_convention_review"}:
        parts = item.get("display_parts") or []
        if isinstance(parts, list) and len(parts) >= 2:
            return f"{parts[0]} / {parts[1]}"
        return _display_release_name(str(item.get("display_name") or ""))
    return workflow


def _campaign_family(source_url: str) -> str:
    slug = source_url.rstrip("/").split("/")[-1]
    if not slug:
        return "unknown_campaign"
    return slug.split("_")[0]


def _campaign_research_links(source_url: str) -> dict[str, str]:
    stripped = source_url.strip().rstrip("/")
    encoded_url = urllib.parse.quote(stripped, safe="")
    encoded_query = urllib.parse.quote(stripped)
    return {
        "source_url": stripped,
        "wayback_calendar": f"https://web.archive.org/web/*/{encoded_url}",
        "domain_search": f"https://www.google.com/search?q={encoded_query}",
    }


def _duplicate_review_kind(source_urls: list[Any], catalog_indexes: list[Any]) -> str:
    clean_urls = {str(url).strip().rstrip("/") for url in source_urls if str(url).strip()}
    clean_indexes = {index for index in catalog_indexes if isinstance(index, int) and not isinstance(index, bool)}
    if len(clean_urls) > 1:
        return "possible_reissue_or_separate_campaign"
    if len(clean_indexes) > 1:
        return "possible_true_duplicate_same_campaign"
    return "needs_more_duplicate_evidence"


def _duplicate_decision_options(kind: str) -> list[str]:
    if kind == "possible_reissue_or_separate_campaign":
        return [
            "keep_rows_as_separate_reissues_with_distinguishing_metadata",
            "merge_only_if_sources_are_same_campaign_aliases",
        ]
    if kind == "possible_true_duplicate_same_campaign":
        return [
            "merge_duplicate_rows_after_confirming_same_prize_variant",
            "split_rows_if_hidden_character_or_variant_difference_exists",
        ]
    return [
        "collect_more_campaign_source_evidence",
        "defer_until_exact_campaign_identity_is_known",
    ]


def _naming_decision_options(reason: Any) -> list[str]:
    if reason == "non_prize_or_related_item_needs_classification":
        return [
            "classify_as_related_or_campaign_goods",
            "replace_second_display_part_with_exact_prize_rank_if_evidence_exists",
        ]
    return [
        "rewrite_display_name_to_release_rank_prize_character",
        "split_multi_character_prize_into_one_row_per_character",
    ]


def _display_release_name(display_name: str) -> str:
    return display_name.split(" / ", 1)[0] if display_name else "unknown_display"


def write_csv(queue: dict[str, Any], path: Path) -> None:
    fields = [
        "workflow",
        "priority",
        "status",
        "catalog_index",
        "source_url",
        "display_name",
        "row_count",
        "reason",
        "display_parts",
        "catalog_indexes",
        "source_urls",
        "recommended_action",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in queue.get("items", []):
            row = {field: item.get(field, "") for field in fields}
            for field in ("catalog_indexes", "source_urls", "display_parts"):
                if isinstance(row[field], list):
                    row[field] = " | ".join(str(value) for value in row[field])
            writer.writerow(row)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _html(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _link(url: Any, label: str | None = None) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    return f'<a href="{_html(value)}" target="_blank" rel="noreferrer">{_html(label or value)}</a>'


def _list(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return "".join(f"<li>{_html(value)}</li>" for value in values)


def write_html(queue: dict[str, Any], path: Path = DEFAULT_HTML) -> None:
    summary = queue.get("summary") or {}
    cards: list[str] = []
    for item in queue.get("items", [])[:80]:
        if not isinstance(item, dict):
            continue
        source_links = ""
        if item.get("source_url"):
            links = item.get("research_links") if isinstance(item.get("research_links"), dict) else {}
            source_links = " ".join(
                part
                for part in [
                    _link(item.get("source_url"), "Source"),
                    _link(links.get("wayback_calendar"), "Wayback"),
                    _link(links.get("domain_search"), "Search"),
                ]
                if part
            )
        elif isinstance(item.get("source_urls"), list):
            source_links = " ".join(
                _link(url, f"Source {index + 1}")
                for index, url in enumerate(item.get("source_urls") or [])
            )
        cards.append(
            f"""
      <article class="card">
        <div class="meta">
          <span>P{_html(item.get('priority'))}</span>
          <span>{_html(item.get('workflow'))}</span>
        </div>
        <h3>{_html(item.get('display_name') or item.get('source_url') or item.get('workflow'))}</h3>
        <dl>
          <dt>Status</dt><dd>{_html(item.get('status'))}</dd>
          <dt>Kind</dt><dd>{_html(item.get('duplicate_review_kind') or item.get('reason'))}</dd>
          <dt>Rows</dt><dd>{_html(item.get('row_count') or len(item.get('catalog_indexes') or []))}</dd>
          <dt>Catalog</dt><dd>{_html(' | '.join(str(value) for value in item.get('catalog_indexes', [])) or item.get('catalog_index'))}</dd>
          <dt>Action</dt><dd>{_html(item.get('recommended_action'))}</dd>
        </dl>
        <div class="links">{source_links}</div>
        <h4>Decision Options</h4>
        <ul>{_list(item.get('decision_options'))}</ul>
        <h4>Acceptance Criteria</h4>
        <ul>{_list(item.get('acceptance_criteria'))}</ul>
      </article>
            """
        )
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Deokive Ichiban Kuji Quality Queue</title>
  <style>
    body {{ margin: 0; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #15171c; background: #f7f8fa; }}
    header {{ position: sticky; top: 0; z-index: 1; background: rgba(255,255,255,.94); backdrop-filter: blur(14px); border-bottom: 1px solid #dde2ea; padding: 18px 22px; }}
    h1 {{ margin: 0 0 6px; font-size: 22px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 22px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-bottom: 18px; }}
    .summary article, .card {{ background: #fff; border: 1px solid #dde2ea; border-radius: 10px; box-shadow: 0 6px 20px rgba(20,28,40,.05); }}
    .summary article {{ padding: 12px; }}
    .summary span, dt, .meta {{ color: #667085; }}
    .summary strong {{ font-size: 22px; }}
    .queue {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }}
    .card {{ padding: 14px; }}
    .meta {{ display: flex; justify-content: space-between; gap: 8px; font-size: 12px; }}
    h2 {{ font-size: 18px; margin: 22px 0 12px; }}
    h3 {{ margin: 10px 0; font-size: 16px; overflow-wrap: anywhere; }}
    h4 {{ margin: 12px 0 6px; font-size: 13px; }}
    dl {{ display: grid; grid-template-columns: 70px 1fr; gap: 6px 10px; margin: 0; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    ul {{ margin: 0; padding-left: 18px; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    a {{ color: #0b57d0; text-decoration: none; border: 1px solid #c8d7f4; background: #f5f8ff; border-radius: 999px; padding: 7px 10px; }}
  </style>
</head>
<body>
  <header>
    <h1>Ichiban Kuji Quality Queue</h1>
    <div>Review campaign gaps, reissue duplicates, and naming convention rows before changing the public catalog.</div>
  </header>
  <main>
    <section class="summary">
      <article><span>Ichiban rows</span><strong>{_html(summary.get('ichiban_rows'))}</strong></article>
      <article><span>Campaign gaps</span><strong>{_html(summary.get('campaign_gap_queue_rows'))}</strong></article>
      <article><span>Duplicate review</span><strong>{_html(summary.get('exact_display_duplicate_queue_rows'))}</strong></article>
      <article><span>Naming review</span><strong>{_html(summary.get('naming_convention_queue_rows'))}</strong></article>
      <article><span>Total queue</span><strong>{_html(summary.get('queue_rows'))}</strong></article>
      <article><span>Work packs</span><strong>{_html(summary.get('work_pack_rows'))}</strong></article>
    </section>
    <h2>Review Cards</h2>
    <section class="queue">{''.join(cards)}</section>
  </main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a public-catalog Ichiban Kuji quality work queue."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    quality_report = build_report(load_catalog_rows(args.catalog))
    queue = build_queue(quality_report)
    write_json(args.json_output, queue)
    write_csv(queue, args.csv_output)
    write_html(queue, args.html_output)
    print(json.dumps(queue["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
