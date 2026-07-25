from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

from catalog_quality_report import load_catalog_rows
from enrich_catalog_images import _preferred_query_for_row

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_STALE_QUEUE = SERVER / "stale_source_cleanup_queue.json"
DEFAULT_JSON = SERVER / "catalog_source_discovery_queue.json"
DEFAULT_CSV = SERVER / "catalog_source_discovery_queue.csv"
DEFAULT_MD = SERVER / "catalog_source_discovery_queue.md"
DEFAULT_HTML = SERVER / "catalog_source_discovery_queue.html"

OFFICIAL_SEARCH_TEMPLATES = {
    "애니메이트": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    "엔스카이": "https://www.enskyshop.com/products/list?name={query}",
    "굿스마일컴퍼니": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "코토부키야": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "Movic": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "FuRyu": "https://furyuprize.com/search?keyword={query}",
    "Taito": "https://www.taito.co.jp/prize?keyword={query}",
    "AmiAmi": "https://www.amiami.jp/top/search/list?s_keywords={query}",
    "Cospa": "https://www.cospa.com/cospa/itemlist/keyword/{query}",
    "메가하우스": "https://www.megahobby.jp/?s={query}",
    "반다이": "https://p-bandai.jp/search/?q={query}",
    "점프 캐릭터즈 스토어": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "무기와라스토어": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "Banpresto": "https://bsp-prize.jp/search/?keyword={query}",
    "SEGA": "https://segaplaza.jp/search/?word={query}",
    "치이카와 마켓": "https://chiikawamarket.jp/search?q={query}",
    "치이카와 모구모구 혼포": "https://chiikawamogumogu.shop/search?q={query}",
    "치이카와 온라인 쿠지": "https://online-kuji.chiikawamarket.jp/search?q={query}",
    "Re-ment": "https://www.re-ment.co.jp/?s={query}",
    "Stellive Store": "https://stellive.fanding.kr/search?keyword={query}",
    "JYP SHOP": "https://en.thejypshop.com/product/search.html?keyword={query}",
    "산리오": "https://shop.sanrio.co.jp/search?keyword={query}",
    "디즈니 스토어": "https://store.disney.co.jp/search?q={query}",
    "가샤폰": "https://gashapon.jp/search/?q={query}",
    "MINISO": "https://www.miniso.com/search?keyword={query}",
    "MINISO 중국": "https://www.miniso.com/search?keyword={query}",
    "ALTER": "https://www.google.com/search?q=site%3Aalter-web.jp%20{query}",
    "Phat! Company": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "Bandai Premium": "https://p-bandai.jp/search/?q={query}",
    "Hololive Production Official Shop": "https://shop.hololivepro.com/en/search?q={query}",
    "SM STORE": "https://global.shop.smtown.com/search?q={query}",
    "YG SELECT": "https://en.ygselect.com/product/search.html?keyword={query}",
    "귀멸의 칼날 공식": "https://www.google.com/search?q=site%3Awebshop-global.ufotable.co.jp%20{query}",
    "카도카와": "https://www.amiami.com/eng/search/list/?s_keywords={query}%20KADOKAWA",
    "Algonavis": "https://bushiroad-store.com/search?q={query}",
    "Hobby Max International": "https://www.amiami.com/eng/search/list/?s_keywords={query}%20HOBBY%20MAX",
    "STARSHIP STORE": "https://www.starship-square.com/product/search.html?keyword={query}",
}

OFFICIAL_SEARCH_TEMPLATES.update(
    {
        "CUBE STORE": "https://www.google.com/search?q=site%3Acubee.co.kr%20{query}",
        "IST STORE": "https://www.google.com/search?q=site%3Ashop.weverse.io%20{query}",
        "KQ FELLAZ": "https://www.google.com/search?q=site%3Akqshop.kr%20{query}",
        "롯데웰푸드": "https://www.google.com/search?q=site%3Alottewellfood.com%20{query}",
        "점프 숍": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
        "이세계아이돌 공식 굿즈": "https://www.google.com/search?q=site%3Awithmuulive.com%20{query}",
        "이세계아이돌 팝업스토어": "https://www.google.com/search?q=site%3Awithmuulive.com%20{query}",
        "치이카와 중국 팝업스토어": "https://www.google.com/search?q=site%3Ax.com%2Fchiikawa_kouhou%20{query}",
        "치이카와샵 용산": "https://www.google.com/search?q=site%3Ax.com%2Fchiikawashop_kr%20{query}",
    }
)

CONTENT_SEARCH_TEMPLATES = [
    (
        ("SVC 공식",),
        ("쿠루미 노아", "胡桃のあ", "Kurumi Noah"),
        "https://store.vspo.jp/search?q={query}",
    ),
    (
        ("SVC 공식",),
        ("시라유키 히나", "Shirayuki Hina"),
        "https://www.google.com/search?q=site%3Astellive.fanding.kr%20{query}",
    ),
]

DISCOVERY_PRIORITY = {
    "official_search_url_available": 10,
    "licensed_retailer_search_review": 20,
    "manual_official_research": 40,
}

LICENSED_RETAILER_STORES = {"AmiAmi"}

FIELDS = [
    "priority",
    "workflow",
    "row_index",
    "source_store",
    "affiliation",
    "category",
    "name_ko",
    "name_ja",
    "query",
    "official_search_url",
    "web_search_url",
    "recommended_next_action",
]


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _stale_indexes(path: Path) -> set[int]:
    payload = _read_json(path, {"items": []})
    indexes: set[int] = set()
    if not isinstance(payload, dict):
        return indexes
    for item in payload.get("items") or []:
        try:
            indexes.add(int(item.get("row_index")))
        except (AttributeError, TypeError, ValueError):
            pass
    return indexes


def _query(row: dict[str, Any]) -> str:
    localized = _preferred_query_for_row(row)
    if localized:
        return localized
    for field in ("name_ja", "name_ko", "name_en"):
        value = str(row.get(field) or "").strip()
        if value:
            return value
    return ""


def _format_url(template: str | None, query: str) -> str | None:
    if not template or not query:
        return None
    return template.format(query=urllib.parse.quote(query))


def _official_template_for(row: dict[str, Any]) -> str | None:
    store = str(row.get("source_store") or "")
    haystack = " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "name_en", "affiliation", "character_name", "series_name")
    )
    for stores, tokens, template in CONTENT_SEARCH_TEMPLATES:
        if store in stores and any(token in haystack for token in tokens):
            return template
    return OFFICIAL_SEARCH_TEMPLATES.get(store)


def _workflow(row: dict[str, Any]) -> str:
    store = str(row.get("source_store") or "")
    if store in LICENSED_RETAILER_STORES:
        return "licensed_retailer_search_review"
    if _official_template_for(row):
        return "official_search_url_available"
    return "manual_official_research"


def build_queue(rows: list[dict[str, Any]], stale_indexes: set[int]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if row_index in stale_indexes or row.get("image_url") or row.get("source_url"):
            continue
        query = _query(row)
        workflow = _workflow(row)
        source_store = str(row.get("source_store") or "")
        official_search = _format_url(_official_template_for(row), query)
        web_query_parts = [query, source_store, "official", "公式 商品画像"]
        item = {
            "priority": DISCOVERY_PRIORITY[workflow],
            "workflow": workflow,
            "row_index": row_index,
            "source_store": row.get("source_store"),
            "affiliation": row.get("affiliation"),
            "category": row.get("category"),
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
            "query": query,
            "official_search_url": official_search,
            "web_search_url": "https://www.google.com/search?q=" + urllib.parse.quote(" ".join(part for part in web_query_parts if part)),
            "recommended_next_action": "find_exact_product_detail_url_then_import_image",
        }
        items.append(item)

    items.sort(
        key=lambda item: (
            item["priority"],
            str(item.get("source_store") or ""),
            str(item.get("affiliation") or ""),
            str(item.get("category") or ""),
            str(item.get("name_ja") or item.get("name_ko") or ""),
        )
    )
    by_workflow = Counter(str(item["workflow"]) for item in items)
    by_store = Counter(str(item.get("source_store") or "") for item in items)
    by_store_workflow = Counter((str(item.get("source_store") or ""), str(item.get("workflow") or "")) for item in items)
    by_store_category = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or ""))
        for item in items
    )
    by_official_store_category = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or ""))
        for item in items
        if item.get("workflow") == "official_search_url_available"
    )
    return {
        "summary": {
            "source_discovery_rows": len(items),
            "stale_excluded_rows": len(stale_indexes),
            "by_workflow": by_workflow.most_common(),
            "by_store": by_store.most_common(),
            "by_store_workflow": [
                {"source_store": store, "workflow": workflow, "rows": count}
                for (store, workflow), count in by_store_workflow.most_common()
            ],
            "top_store_categories": [
                {"source_store": store, "category": category, "rows": count}
                for (store, category), count in by_store_category.most_common(80)
            ],
            "top_official_search_store_categories": [
                {"source_store": store, "category": category, "rows": count}
                for (store, category), count in by_official_store_category.most_common(80)
            ],
        },
        "items": items,
        "instructions": [
            "Use this queue before image attachment when source_url is missing.",
            "Only write source_url after an exact product/detail page is found for the same item.",
            "After source_url is confirmed, use image safety/import tooling to attach image_url from that exact page.",
        ],
    }


def write_csv(payload: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(payload.get("items") or [])


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# Catalog Source Discovery Queue",
        "",
        f"- Source discovery rows: `{summary['source_discovery_rows']}`",
        f"- Stale rows excluded: `{summary['stale_excluded_rows']}`",
        "",
        "## Workflow Counts",
    ]
    for workflow, count in summary["by_workflow"]:
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "## Top Store Counts"])
    for store, count in summary["by_store"][:30]:
        lines.append(f"- `{store}`: `{count}`")
    lines.extend(["", "## Top Store Category Batches"])
    for item in summary.get("top_store_categories", [])[:30]:
        lines.append(f"- `{item['source_store']}` / `{item['category']}`: `{item['rows']}`")
    lines.extend(["", "## Top Official Search Store Category Batches"])
    for item in summary.get("top_official_search_store_categories", [])[:30]:
        lines.append(f"- `{item['source_store']}` / `{item['category']}`: `{item['rows']}`")
    lines.extend(["", "## First Rows"])
    for item in (payload.get("items") or [])[:80]:
        lines.append(
            f"- P{item.get('priority')} row `{item.get('row_index')}` "
            f"`{item.get('source_store')}` {item.get('name_ja') or item.get('name_ko')}"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def write_html(payload: dict[str, Any], path: Path) -> None:
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('priority')))}</td>"
        f"<td>{html.escape(str(item.get('workflow') or ''))}</td>"
        f"<td>{html.escape(str(item.get('row_index')))}</td>"
        f"<td>{html.escape(str(item.get('source_store') or ''))}</td>"
        f"<td>{html.escape(str(item.get('name_ja') or item.get('name_ko') or ''))}</td>"
        f"<td><a href=\"{html.escape(str(item.get('official_search_url') or item.get('web_search_url') or ''))}\">search</a></td>"
        "</tr>"
        for item in payload.get("items") or []
    )
    summary = payload["summary"]
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catalog Source Discovery Queue</title>
<style>
body {{ margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #17191f; }}
header {{ padding: 24px; background: #fff; border-bottom: 1px solid #dde2ea; }}
main {{ max-width: 1280px; margin: auto; padding: 20px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 16px; }}
article, table {{ background: #fff; border: 1px solid #dde2ea; border-radius: 10px; }}
article {{ padding: 14px; }}
article span {{ display: block; color: #667085; }}
article strong {{ display: block; font-size: 28px; }}
table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #edf0f4; text-align: left; vertical-align: top; }}
th {{ background: #f9fafb; position: sticky; top: 0; }}
a {{ color: #0b57d0; font-weight: 700; }}
</style>
</head>
<body>
<header>
  <h1>Catalog Source Discovery Queue</h1>
  <div>Missing-image rows that need exact product source URLs first.</div>
</header>
<main>
  <section class="summary">
    <article><span>Source discovery rows</span><strong>{html.escape(str(summary.get('source_discovery_rows')))}</strong></article>
    <article><span>Stale excluded rows</span><strong>{html.escape(str(summary.get('stale_excluded_rows')))}</strong></article>
  </section>
  <table>
    <thead><tr><th>Priority</th><th>Workflow</th><th>Row</th><th>Store</th><th>Name</th><th>Search</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</main>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--stale-queue", type=Path, default=DEFAULT_STALE_QUEUE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    rows = load_catalog_rows(args.seed)
    payload = build_queue(rows, _stale_indexes(args.stale_queue))
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(payload, args.csv_output)
    write_markdown(payload, args.markdown_output)
    write_html(payload, args.html_output)
    print(
        json.dumps(
            {
                "source_discovery_rows": payload["summary"]["source_discovery_rows"],
                "stale_excluded_rows": payload["summary"]["stale_excluded_rows"],
                "json": str(args.json_output),
                "csv": str(args.csv_output),
                "markdown": str(args.markdown_output),
                "html": str(args.html_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
