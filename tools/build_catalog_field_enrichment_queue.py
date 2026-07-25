from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from catalog_quality_report import ENRICHMENT_FIELDS, load_catalog_rows, source_group

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_JSON = ROOT / "server" / "catalog_field_enrichment_queue_current.json"
DEFAULT_CSV = ROOT / "server" / "catalog_field_enrichment_queue_current.csv"
DEFAULT_MD = ROOT / "server" / "catalog_field_enrichment_queue_current.md"
DEFAULT_HTML = ROOT / "server" / "catalog_field_enrichment_review_current.html"
DEFAULT_CONFIRMED_TEMPLATE = ROOT / "server" / "catalog_field_confirmed_rows_current.template.json"

FIELD_PRIORITY = {
    "source_url": 10,
    "image_url": 20,
    "release_date": 30,
    "barcode": 40,
    "official_price_jpy": 50,
}

FIELD_GUIDANCE = {
    "source_url": {
        "field_action": "attach_exact_official_detail_url",
        "acceptance_criteria": "Use an official product, campaign, maker, or retailer detail page that uniquely identifies the row.",
        "risk": "medium",
    },
    "image_url": {
        "field_action": "attach_official_product_image",
        "acceptance_criteria": "Use an image from the exact official detail page or a verified official CDN URL for the same item.",
        "risk": "medium",
    },
    "release_date": {
        "field_action": "copy_exact_release_or_sale_date",
        "acceptance_criteria": "Use the release, sale, shipping, or campaign start date shown on the exact official page.",
        "risk": "medium",
    },
    "barcode": {
        "field_action": "copy_official_jan_or_barcode",
        "acceptance_criteria": "Use only a JAN/barcode printed on the exact official detail page; leave blank for lottery prizes if none is published.",
        "risk": "high",
    },
    "official_price_jpy": {
        "field_action": "copy_official_jpy_price",
        "acceptance_criteria": "Use only a listed JPY tax-included or tax-excluded official price; do not convert from KRW or resale prices.",
        "risk": "high",
    },
}

SEARCH_URLS = {
    "애니메이트": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    "엔스카이": "https://www.enskyshop.com/products/list?name={query}",
    "굿스마일컴퍼니": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "Banpresto": "https://bsp-prize.jp/search/?keyword={query}",
    "FuRyu": "https://furyuprize.com/search?keyword={query}",
    "Taito": "https://www.taito.co.jp/prize/search?keyword={query}",
    "코토부키야": "https://www.kotobukiya.co.jp/search/?keyword={query}",
    "Movic": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "치이카와 마켓": "https://chiikawamarket.jp/ko/search?q={query}",
    "나가노 마켓": "https://nagano-market.jp/ko/search?q={query}",
    "치이카와 모구모구 혼포": "https://chiikawamogumogu.shop/search?q={query}",
    "이치방쿠지": "https://1kuji.com/search?word={query}",
}


def missing(row: dict[str, Any], field: str) -> bool:
    return row.get(field) in (None, "")


def display_name(row: dict[str, Any]) -> str:
    return str(row.get("name_ja") or row.get("name_ko") or row.get("name_en") or "").strip()


def search_url(row: dict[str, Any]) -> str:
    store = str(row.get("source_store") or "").strip()
    template = SEARCH_URLS.get(store)
    if not template:
        return ""
    query = display_name(row) or str(row.get("name_ko") or "").strip()
    return template.format(query=quote_plus(query))


def strategy_for(row: dict[str, Any], field: str) -> str:
    store = str(row.get("source_store") or "")
    group = source_group(store)
    if field == "source_url" and store in {"치이카와 마켓", "나가노 마켓", "치이카와 모구모구 혼포", "치이카와 파크"}:
        return "official_shop_product_lookup"
    if field in {"release_date", "barcode", "official_price_jpy"} and group == "kuji":
        return "campaign_metadata_or_official_page"
    if group == "animation_goods":
        return "official_maker_or_retailer_lookup"
    if group == "chiikawa_official":
        return "official_shop_json_or_product_lookup"
    if group == "korea_vtuber":
        return "manual_store_archive_review"
    return "manual_review"


def note_for(row: dict[str, Any], field: str) -> str:
    store = str(row.get("source_store") or "")
    source_url = str(row.get("source_url") or "")
    if store == "치이카와 온라인 쿠지" and field in {"release_date", "official_price_jpy"}:
        if source_url.rstrip("/") == "https://online-kuji.chiikawamarket.jp":
            return "Only the site root is known; remap to the exact lottery URL before filling campaign metadata."
        if source_url.rstrip("/").endswith("/mochifuwa"):
            return "Official public API currently returns no campaign payload for this archived slug; keep for manual/archive review."
    if store == "굿스마일컴퍼니":
        return "Use exact title/detail matches only; broad Goodsmile search can return different variants."
    if store in {"Banpresto", "Taito"}:
        return "Search pages are broad; verify detail page identity before writing."
    if store == "엔스카이":
        return "Prefer sitemap/detail-page matches in small batches."
    if store == "이치방쿠지":
        return "Use listed campaign page and campaign metadata; do not infer per-prize barcode."
    if field == "barcode":
        return "Fill only from official JAN/barcode fields or exact product detail pages."
    if field == "release_date":
        return "Fill only from official release/sale date on exact product or campaign page."
    return ""


def action_context(row: dict[str, Any], field: str) -> dict[str, Any]:
    store = str(row.get("source_store") or "")
    category = str(row.get("category") or "")
    group = source_group(store)
    strategy = strategy_for(row, field)
    guidance = FIELD_GUIDANCE.get(field, {})

    if group == "animation_goods":
        workstream = "animation_goods_official_detail_backfill"
        automation_candidate = strategy == "official_maker_or_retailer_lookup"
        batch_hint = "Group by maker/store and category; run exact-title checks in small batches."
    elif group == "kuji":
        workstream = "kuji_campaign_metadata_review"
        automation_candidate = field in {"source_url", "release_date", "image_url"}
        batch_hint = "Group by campaign URL; prizes commonly lack public JAN/barcode data."
    elif group == "chiikawa_official":
        workstream = "chiikawa_official_shop_lookup"
        automation_candidate = field in {"source_url", "image_url", "release_date", "official_price_jpy"}
        batch_hint = "Group by official shop and category; prefer product JSON/detail pages."
    elif group in {"korea_vtuber", "global_vtuber", "kpop_official"}:
        workstream = "official_store_archive_manual_review"
        automation_candidate = False
        batch_hint = "Store pages may be hidden, expired, or region gated; keep manual evidence notes."
    else:
        workstream = "misc_official_source_review"
        automation_candidate = False
        batch_hint = "Find a stable official source before filling values."

    if field == "barcode":
        automation_candidate = False

    applicability = "actionable"
    actionable_now = True
    if store == "치이카와 온라인 쿠지" and field in {"release_date", "official_price_jpy"}:
        source_url = str(row.get("source_url") or "").rstrip("/")
        if source_url == "https://online-kuji.chiikawamarket.jp":
            applicability = "needs_source_url_remap"
            actionable_now = False
            automation_candidate = False
        elif source_url.endswith("/mochifuwa"):
            applicability = "unavailable_archived"
            actionable_now = False
            automation_candidate = False
    if group == "kuji" and field == "barcode":
        applicability = "not_publicly_available"
        actionable_now = False
    elif group in {"korea_vtuber", "kpop_official"} and field == "official_price_jpy":
        applicability = "not_applicable_currency"
        actionable_now = False
    elif field == "barcode" and group in {"korea_vtuber", "kpop_official", "global_vtuber", "retail_misc"}:
        applicability = "manual_only_or_not_public"
        actionable_now = False

    return {
        "field_action": guidance.get("field_action", "manual_review"),
        "acceptance_criteria": guidance.get("acceptance_criteria", ""),
        "risk": guidance.get("risk", "medium"),
        "workstream": workstream,
        "batch_key": f"{group}|{store}|{category}|{field}",
        "batch_hint": batch_hint,
        "automation_candidate": automation_candidate,
        "applicability": applicability,
        "actionable_now": actionable_now,
    }


def row_priority(row: dict[str, Any], field: str) -> int:
    store = str(row.get("source_store") or "")
    group = source_group(store)
    group_bonus = {
        "chiikawa_official": 0,
        "kuji": 5,
        "animation_goods": 10,
        "korea_vtuber": 25,
    }.get(group, 35)
    has_lookup = 0 if search_url(row) or row.get("source_url") else 8
    return FIELD_PRIORITY[field] + group_bonus + has_lookup


def _top_counter(counter: Counter[tuple[Any, ...]], keys: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for values, count in counter.most_common(limit):
        row = {key: value for key, value in zip(keys, values)}
        row["missing"] = count
        rows.append(row)
    return rows


def build_queue(rows: list[dict[str, Any]]) -> dict[str, Any]:
    queue: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        for field in ENRICHMENT_FIELDS:
            if not missing(row, field):
                continue
            context = action_context(row, field)
            item = {
                "priority": row_priority(row, field),
                "row_index": index,
                "field": field,
                "strategy": strategy_for(row, field),
                "source_group": source_group(row.get("source_store")),
                "source_store": row.get("source_store") or "",
                "affiliation": row.get("affiliation") or "",
                "category": row.get("category") or "",
                "name_ko": row.get("name_ko") or "",
                "name_ja": row.get("name_ja") or "",
                "source_url": row.get("source_url") or "",
                "search_url": search_url(row),
                "note": note_for(row, field),
                **context,
            }
            queue.append(item)

    queue.sort(
        key=lambda item: (
            item["priority"],
            item["field"],
            item["source_store"],
            item["affiliation"],
            item["name_ko"],
        )
    )

    by_field = Counter(item["field"] for item in queue)
    by_strategy = Counter(item["strategy"] for item in queue)
    by_store_field: Counter[tuple[str, str]] = Counter((item["source_store"], item["field"]) for item in queue)
    by_group_field: Counter[tuple[str, str]] = Counter((item["source_group"], item["field"]) for item in queue)
    by_strategy_store_field: Counter[tuple[str, str, str]] = Counter(
        (item["strategy"], item["source_store"], item["field"]) for item in queue
    )
    by_store_category_field: Counter[tuple[str, str, str]] = Counter(
        (item["source_store"], item["category"], item["field"]) for item in queue
    )
    by_workstream_field: Counter[tuple[str, str]] = Counter((item["workstream"], item["field"]) for item in queue)
    by_action_field: Counter[tuple[str, str]] = Counter((item["field_action"], item["field"]) for item in queue)
    by_risk_field: Counter[tuple[str, str]] = Counter((item["risk"], item["field"]) for item in queue)
    by_applicability_field: Counter[tuple[str, str]] = Counter((item["applicability"], item["field"]) for item in queue)
    by_batch_key = Counter(str(item["batch_key"]) for item in queue)
    actionable_queue = [item for item in queue if item.get("actionable_now")]
    animation_items = [item for item in queue if item["source_group"] == "animation_goods"]
    animation_category_field: Counter[tuple[str, str]] = Counter(
        (item["category"], item["field"]) for item in animation_items
    )
    animation_store_category_field: Counter[tuple[str, str, str]] = Counter(
        (item["source_store"], item["category"], item["field"]) for item in animation_items
    )

    return {
        "rows": len(rows),
        "missing_total": len(queue),
        "actionable_missing_total": len(actionable_queue),
        "non_actionable_missing_total": len(queue) - len(actionable_queue),
        "by_field": by_field.most_common(),
        "by_strategy": by_strategy.most_common(),
        "by_workstream_field": _top_counter(by_workstream_field, ("workstream", "field"), 80),
        "by_action_field": _top_counter(by_action_field, ("field_action", "field"), 80),
        "by_risk_field": _top_counter(by_risk_field, ("risk", "field"), 80),
        "by_applicability_field": _top_counter(by_applicability_field, ("applicability", "field"), 80),
        "by_source_group_field": _top_counter(by_group_field, ("source_group", "field"), 80),
        "top_store_fields": [
            {"source_store": store, "field": field, "missing": count}
            for (store, field), count in by_store_field.most_common(80)
        ],
        "top_strategy_store_fields": _top_counter(
            by_strategy_store_field,
            ("strategy", "source_store", "field"),
            100,
        ),
        "top_store_category_fields": _top_counter(
            by_store_category_field,
            ("source_store", "category", "field"),
            100,
        ),
        "top_batch_keys": [{"batch_key": key, "missing": count} for key, count in by_batch_key.most_common(100)],
        "animation_goods_category_fields": _top_counter(
            animation_category_field,
            ("category", "field"),
            80,
        ),
        "animation_goods_store_category_fields": _top_counter(
            animation_store_category_field,
            ("source_store", "category", "field"),
            100,
        ),
        "queue": queue,
    }


def write_csv(payload: dict[str, Any], path: Path) -> None:
    fields = [
        "priority",
        "row_index",
        "field",
        "strategy",
        "source_group",
        "source_store",
        "affiliation",
        "category",
        "name_ko",
        "name_ja",
        "source_url",
        "search_url",
        "note",
        "field_action",
        "acceptance_criteria",
        "risk",
        "workstream",
        "batch_key",
        "batch_hint",
        "automation_candidate",
        "applicability",
        "actionable_now",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for item in payload["queue"]:
            writer.writerow({field: item.get(field, "") for field in fields})


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog Field Enrichment Queue",
        "",
        f"- Rows: `{payload['rows']}`",
        f"- Missing field cells: `{payload['missing_total']}`",
        f"- Actionable missing field cells: `{payload['actionable_missing_total']}`",
        f"- Non-actionable/manual-only field cells: `{payload['non_actionable_missing_total']}`",
        "",
        "## By Field",
        "",
    ]
    for field, count in payload["by_field"]:
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(["", "## By Strategy", ""])
    for strategy, count in payload["by_strategy"]:
        lines.append(f"- `{strategy}`: `{count}`")
    lines.extend(["", "## Workstream Fields", ""])
    for item in payload["by_workstream_field"][:30]:
        lines.append(
            f"- `{item['workstream']}` / `{item['field']}`: `{item['missing']}`"
        )
    lines.extend(["", "## Action Fields", ""])
    for item in payload["by_action_field"][:30]:
        lines.append(
            f"- `{item['field_action']}` / `{item['field']}`: `{item['missing']}`"
        )
    lines.extend(["", "## Applicability Fields", ""])
    for item in payload["by_applicability_field"][:30]:
        lines.append(
            f"- `{item['applicability']}` / `{item['field']}`: `{item['missing']}`"
        )
    lines.extend(["", "## Source Group Fields", ""])
    for item in payload["by_source_group_field"][:30]:
        lines.append(
            f"- `{item['source_group']}` / `{item['field']}`: `{item['missing']}`"
        )
    lines.extend(["", "## Top Store Fields", ""])
    for item in payload["top_store_fields"][:30]:
        lines.append(f"- `{item['source_store']}` / `{item['field']}`: `{item['missing']}`")
    lines.extend(["", "## Top Strategy Store Fields", ""])
    for item in payload["top_strategy_store_fields"][:30]:
        lines.append(
            f"- `{item['strategy']}` / `{item['source_store']}` / "
            f"`{item['field']}`: `{item['missing']}`"
        )
    lines.extend(["", "## Top Store Category Fields", ""])
    for item in payload["top_store_category_fields"][:30]:
        lines.append(
            f"- `{item['source_store']}` / `{item['category']}` / "
            f"`{item['field']}`: `{item['missing']}`"
        )
    lines.extend(["", "## Animation Goods Category Fields", ""])
    for item in payload["animation_goods_category_fields"][:30]:
        lines.append(f"- `{item['category']}` / `{item['field']}`: `{item['missing']}`")
    lines.extend(["", "## Animation Goods Store Category Fields", ""])
    for item in payload["animation_goods_store_category_fields"][:30]:
        lines.append(
            f"- `{item['source_store']}` / `{item['category']}` / "
            f"`{item['field']}`: `{item['missing']}`"
        )
    lines.extend(["", "## Top Batch Keys", ""])
    for item in payload["top_batch_keys"][:30]:
        lines.append(f"- `{item['batch_key']}`: `{item['missing']}`")
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Work by `batch_key` when updating fields so one verified source pattern can clear many similar rows.",
            "- Fill barcodes only from official JAN/barcode fields or exact product detail pages.",
            "- Fill release dates only from exact product/campaign pages.",
            "- Fill JPY prices only from official Japanese price fields; do not convert currency or use resale listings.",
            "- Treat lottery prize barcodes as not publicly available unless a campaign explicitly publishes JAN/barcode values.",
            "- Treat Korea/K-pop store JPY prices as not applicable unless the official source lists a JPY price.",
            "- Treat generic official shop URLs as source pointers, not product identity keys.",
            "- Keep broad search result rows in manual review until a strict detail matcher is verified.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _group_card(item: dict[str, Any], fields: list[str]) -> str:
    title = " / ".join(str(item.get(field) or "") for field in fields if item.get(field))
    haystack = " ".join(str(item.get(field) or "") for field in fields + ["missing"]).lower()
    chips = "\n".join(
        f"<span>{_escape(field)}: <strong>{_escape(item.get(field))}</strong></span>"
        for field in fields
        if item.get(field)
    )
    return f"""
      <article class="group-card" data-haystack="{_escape(haystack)}">
        <h3>{_escape(title)}</h3>
        <div class="count">{_escape(item.get('missing'))}</div>
        <div class="chips">{chips}</div>
      </article>"""


def _template_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "row_index": item.get("row_index"),
        "field": item.get("field"),
        "manual_value": "",
        "evidence_url": item.get("source_url") or item.get("search_url") or "",
        "source_store": item.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "affiliation": item.get("affiliation"),
        "acceptance_criteria": item.get("acceptance_criteria"),
        "risk": item.get("risk"),
        "applicability": item.get("applicability"),
    }


def write_html(payload: dict[str, Any], path: Path) -> None:
    field_cards = "\n".join(
        f"<article class=\"metric\"><span>{_escape(field)}</span><strong>{_escape(count)}</strong></article>"
        for field, count in payload["by_field"]
    )
    workstream_cards = "\n".join(
        _group_card(item, ["workstream", "field"])
        for item in payload["by_workstream_field"][:30]
    )
    store_cards = "\n".join(
        _group_card(item, ["source_store", "field"])
        for item in payload["top_store_fields"][:40]
    )
    category_cards = "\n".join(
        _group_card(item, ["source_store", "category", "field"])
        for item in payload["top_store_category_fields"][:50]
    )
    animation_cards = "\n".join(
        _group_card(item, ["source_store", "category", "field"])
        for item in payload["animation_goods_store_category_fields"][:50]
    )
    sample_rows = "\n".join(
        (
            lambda template_json: f"""
        <tr data-field="{_escape(item.get('field'))}" data-actionable="{_escape(item.get('actionable_now'))}">
          <td>{_escape(item.get('priority'))}</td>
          <td>{_escape(item.get('field'))}</td>
          <td>{_escape(item.get('source_store'))}</td>
          <td>{_escape(item.get('category'))}</td>
          <td>{_escape(item.get('name_ko') or item.get('name_ja'))}</td>
          <td>{_escape(item.get('applicability'))}</td>
          <td>{_escape(item.get('note'))}</td>
          <td><a href="{_escape(item.get('search_url') or item.get('source_url'))}" target="_blank" rel="noreferrer">open</a></td>
          <td><button type="button" data-copy="{_escape(template_json)}">copy</button></td>
        </tr>"""
        )(json.dumps(_template_item(item), ensure_ascii=False, indent=2))
        for item in payload["queue"][:500]
    )
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Catalog Field Enrichment Review</title>
  <style>
    body {{ margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f8fa; color: #15171c; }}
    header {{ position: sticky; top: 0; z-index: 2; padding: 18px 24px; background: rgba(255,255,255,.95); border-bottom: 1px solid #dde2ea; backdrop-filter: blur(12px); }}
    main {{ max-width: 1240px; margin: auto; padding: 22px; }}
    h1 {{ margin: 0 0 8px; font-size: 22px; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; }}
    .pills, .toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .pill {{ padding: 4px 9px; border: 1px solid #d8dde5; border-radius: 999px; background: #fff; color: #596273; }}
    input, select, button {{ font: inherit; padding: 9px 10px; border: 1px solid #d8dde5; border-radius: 8px; background: #fff; color: #15171c; }}
    button {{ cursor: pointer; }}
    input {{ min-width: min(420px, 100%); flex: 1; }}
    .metrics, .groups {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }}
    article, table {{ background: #fff; border: 1px solid #dfe3ea; border-radius: 10px; box-shadow: 0 4px 18px rgba(20,28,40,.05); }}
    .metric, .group-card {{ padding: 14px; }}
    .metric span {{ display: block; color: #657082; }}
    .metric strong, .count {{ font-size: 24px; font-weight: 750; }}
    .group-card h3 {{ margin: 0 0 8px; font-size: 15px; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
    .chips span {{ font-size: 12px; padding: 3px 7px; border-radius: 999px; background: #f0f3f7; color: #596273; }}
    table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid #edf0f4; vertical-align: top; text-align: left; }}
    th {{ background: #f9fafb; }}
    a {{ color: #0b57d0; }}
  </style>
</head>
<body>
  <header>
    <h1>Catalog Field Enrichment Review</h1>
    <div class="pills">
      <span class="pill">missing cells: {_escape(payload.get('missing_total'))}</span>
      <span class="pill">actionable: {_escape(payload.get('actionable_missing_total'))}</span>
      <span class="pill">manual/non-actionable: {_escape(payload.get('non_actionable_missing_total'))}</span>
    </div>
  </header>
  <main>
    <div class="toolbar">
      <input id="search" placeholder="Search groups and sample rows">
      <select id="fieldFilter">
        <option value="">All sample fields</option>
        <option value="source_url">source_url</option>
        <option value="image_url">image_url</option>
        <option value="release_date">release_date</option>
        <option value="barcode">barcode</option>
        <option value="official_price_jpy">official_price_jpy</option>
      </select>
    </div>
    <h2>Missing Fields</h2>
    <section class="metrics">{field_cards}</section>
    <h2>Workstreams</h2>
    <section class="groups">{workstream_cards}</section>
    <h2>Top Store Fields</h2>
    <section class="groups">{store_cards}</section>
    <h2>Top Store / Category / Field Batches</h2>
    <section class="groups">{category_cards}</section>
    <h2>Animation Goods Batches</h2>
    <section class="groups">{animation_cards}</section>
    <h2>Queue Sample</h2>
    <table id="sample"><thead><tr><th>P</th><th>Field</th><th>Store</th><th>Category</th><th>Name</th><th>Applicability</th><th>Note</th><th>Link</th><th>JSON</th></tr></thead><tbody>{sample_rows}</tbody></table>
  </main>
  <script>
    const search = document.querySelector('#search');
    const fieldFilter = document.querySelector('#fieldFilter');
    const cards = [...document.querySelectorAll('.group-card')];
    const rows = [...document.querySelectorAll('#sample tbody tr')];
    function applyFilters() {{
      const q = (search.value || '').trim().toLowerCase();
      const field = fieldFilter.value;
      for (const card of cards) {{
        card.style.display = !q || (card.dataset.haystack || '').includes(q) ? '' : 'none';
      }}
      for (const row of rows) {{
        const fieldOk = !field || row.dataset.field === field;
        const queryOk = !q || row.textContent.toLowerCase().includes(q);
        row.style.display = fieldOk && queryOk ? '' : 'none';
      }}
    }}
    search.addEventListener('input', applyFilters);
    fieldFilter.addEventListener('change', applyFilters);
    document.addEventListener('click', async (event) => {{
      const button = event.target.closest('button[data-copy]');
      if (!button) return;
      const text = button.dataset.copy || '';
      if (navigator.clipboard && window.isSecureContext) {{
        await navigator.clipboard.writeText(text);
      }} else {{
        const area = document.createElement('textarea');
        area.value = text;
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        area.remove();
      }}
      const before = button.textContent;
      button.textContent = 'copied';
      setTimeout(() => button.textContent = before, 1000);
    }});
  </script>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def write_confirmed_template(payload: dict[str, Any], path: Path) -> None:
    items = [_template_item(item) for item in payload["queue"] if item.get("actionable_now")][:500]
    path.write_text(
        json.dumps(
            {
                "instructions": (
                    "Copy this file to catalog_field_confirmed_rows.json. Fill manual_value and set "
                    "manual_confirmed=true only after checking the evidence URL against the exact seed row."
                ),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--confirmed-template-output", type=Path, default=DEFAULT_CONFIRMED_TEMPLATE)
    args = parser.parse_args()

    rows = load_catalog_rows(args.input)
    payload = build_queue(rows)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(payload, args.csv_output)
    write_markdown(payload, args.markdown_output)
    write_html(payload, args.html_output)
    write_confirmed_template(payload, args.confirmed_template_output)
    print(
        json.dumps(
            {
                "missing_total": payload["missing_total"],
                "actionable_missing_total": payload["actionable_missing_total"],
                "non_actionable_missing_total": payload["non_actionable_missing_total"],
                "by_field": payload["by_field"],
                "json": str(args.json_output),
                "csv": str(args.csv_output),
                "markdown": str(args.markdown_output),
                "html": str(args.html_output),
                "confirmed_template": str(args.confirmed_template_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
