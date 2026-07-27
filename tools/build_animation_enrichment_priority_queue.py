from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_image_enrichment_queue import search_url
from catalog_quality_report import source_group

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_AUDIT = ROOT / "server" / "animation_goods_category_audit.json"
DEFAULT_JSON = ROOT / "server" / "animation_enrichment_priority_queue.json"
DEFAULT_CSV = ROOT / "server" / "animation_enrichment_priority_queue.csv"
DEFAULT_MD = ROOT / "server" / "animation_enrichment_priority_queue.md"
DEFAULT_HTML = ROOT / "server" / "animation_enrichment_priority_queue.html"
DEFAULT_IMAGE_UPDATE_TEMPLATE = ROOT / "server" / "animation_next_batch_image_update.template.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_rows(payload: Any, path: Path) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or public catalog object with items")


def _category_rank(items: list[dict[str, Any]], field: str = "category") -> dict[str, int]:
    return {
        str(item.get(field) or ""): index
        for index, item in enumerate(items)
        if isinstance(item, dict)
    }


def _missing(row: dict[str, Any], field: str) -> bool:
    return row.get(field) in (None, "")


def _workflow(row: dict[str, Any]) -> str:
    if _missing(row, "source_url"):
        return "find_exact_source_url"
    if _missing(row, "image_url"):
        return "attach_image_from_exact_source"
    return "metadata_backfill"


def _query(row: dict[str, Any]) -> str:
    return str(row.get("name_ja") or row.get("name_ko") or row.get("name_en") or "").strip()


def _links(row: dict[str, Any]) -> dict[str, str]:
    query = _query(row)
    encoded = urllib.parse.quote(query)
    links = {
        "web_search": f"https://www.google.com/search?q={encoded}",
        "image_search": f"https://www.google.com/search?tbm=isch&q={encoded}",
    }
    official_search = search_url(row)
    if official_search:
        links["official_search"] = official_search
    source_url = str(row.get("source_url") or "").strip()
    if source_url:
        links["current_source"] = source_url
    return links


def _top_affiliations(group: list[tuple[int, dict[str, Any]]], limit: int = 5) -> list[dict[str, Any]]:
    counter = Counter(str(row.get("affiliation") or "(blank)") for _, row in group)
    return [
        {"affiliation": affiliation, "rows": rows}
        for affiliation, rows in counter.most_common(limit)
    ]


def _priority(category: str, missing_image_rank: dict[str, int], missing_source_rank: dict[str, int], workflow: str) -> int:
    image_rank = missing_image_rank.get(category, 99)
    source_rank = missing_source_rank.get(category, 99)
    base = min(image_rank, source_rank) + 1
    if workflow == "find_exact_source_url":
        return base
    if workflow == "attach_image_from_exact_source":
        return base + 20
    return base + 40


def build(rows: list[dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    animation_rows = [
        (index, row)
        for index, row in enumerate(rows)
        if isinstance(row, dict) and source_group(row.get("source_store")) == "animation_goods"
    ]
    missing_image_rank = _category_rank(audit.get("missing_image_by_category") or [])
    missing_source_rank = _category_rank(audit.get("missing_source_url_by_category") or [])

    grouped: dict[tuple[str, str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for row_index, row in animation_rows:
        if not (_missing(row, "image_url") or _missing(row, "source_url")):
            continue
        workflow = _workflow(row)
        key = (workflow, str(row.get("category") or ""), str(row.get("source_store") or ""))
        grouped[key].append((row_index, row))

    items: list[dict[str, Any]] = []
    for (workflow, category, source_store), group in grouped.items():
        group.sort(key=lambda pair: (str(pair[1].get("affiliation") or ""), str(pair[1].get("name_ko") or "")))
        rows_count = len(group)
        missing_images = sum(1 for _, row in group if _missing(row, "image_url"))
        missing_sources = sum(1 for _, row in group if _missing(row, "source_url"))
        priority = _priority(category, missing_image_rank, missing_source_rank, workflow)
        items.append(
            {
                "priority": priority,
                "workflow": workflow,
                "category": category,
                "source_store": source_store,
                "rows": rows_count,
                "missing_image_url": missing_images,
                "missing_source_url": missing_sources,
                "top_affiliations": _top_affiliations(group),
                "sample_items": [
                    {
                        "row_index": row_index,
                        "catalog_index": row.get("catalog_index"),
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                        "affiliation": row.get("affiliation"),
                        "sub_series": row.get("sub_series"),
                        "source_url": row.get("source_url"),
                        "query": _query(row),
                        "links": _links(row),
                    }
                    for row_index, row in group[:12]
                ],
            }
        )

    items.sort(
        key=lambda item: (
            item["priority"],
            -int(item.get("rows") or 0),
            str(item.get("category") or ""),
            str(item.get("source_store") or ""),
        )
    )
    by_workflow = Counter(str(item.get("workflow") or "") for item in items for _ in range(int(item.get("rows") or 0)))
    return {
        "animation_rows": len(animation_rows),
        "queue_groups": len(items),
        "queue_rows": sum(int(item.get("rows") or 0) for item in items),
        "missing_image_rows": sum(1 for _, row in animation_rows if _missing(row, "image_url")),
        "missing_source_rows": sum(1 for _, row in animation_rows if _missing(row, "source_url")),
        "by_workflow": by_workflow.most_common(),
        "top_categories": {
            "missing_image": (audit.get("missing_image_by_category") or [])[:10],
            "missing_source_url": (audit.get("missing_source_url_by_category") or [])[:10],
        },
        "items": items,
    }


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    fields = [
        "priority",
        "workflow",
        "category",
        "source_store",
        "rows",
        "missing_image_url",
        "missing_source_url",
        "top_affiliations",
        "sample_name_ko",
        "sample_name_ja",
        "sample_official_search",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            sample = (item.get("sample_items") or [{}])[0]
            links = sample.get("links") or {}
            row = {field: item.get(field) for field in fields}
            row["top_affiliations"] = "; ".join(
                f"{entry.get('affiliation')}: {entry.get('rows')}"
                for entry in item.get("top_affiliations") or []
            )
            row["sample_name_ko"] = sample.get("name_ko")
            row["sample_name_ja"] = sample.get("name_ja")
            row["sample_official_search"] = links.get("official_search") or links.get("web_search")
            writer.writerow(row)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Animation Enrichment Priority Queue",
        "",
        f"- Animation rows: `{payload['animation_rows']}`",
        f"- Queue groups: `{payload['queue_groups']}`",
        f"- Queue rows: `{payload['queue_rows']}`",
        f"- Missing image rows: `{payload['missing_image_rows']}`",
        f"- Missing source rows: `{payload['missing_source_rows']}`",
        "",
        "## By Workflow",
    ]
    for workflow, count in payload["by_workflow"]:
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "## Top Groups"])
    for item in payload["items"][:60]:
        sample = (item.get("sample_items") or [{}])[0]
        links = sample.get("links") or {}
        link = links.get("official_search") or links.get("web_search") or ""
        top_affiliations = "; ".join(
            f"{entry.get('affiliation')}: {entry.get('rows')}"
            for entry in item.get("top_affiliations") or []
        )
        lines.append(
            f"- P{item['priority']} `{item['workflow']}` / `{item['category']}` / "
            f"`{item['source_store']}`: `{item['rows']}` rows"
            f" / top affiliations `{top_affiliations}`"
            f" / sample `{sample.get('name_ko') or sample.get('name_ja')}`"
            f" / [search]({link})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(path: Path, payload: dict[str, Any]) -> None:
    cards: list[str] = []
    for item in payload["items"]:
        sample_rows: list[str] = []
        top_affiliations = "; ".join(
            f"{entry.get('affiliation')}: {entry.get('rows')}"
            for entry in item.get("top_affiliations") or []
        )
        for sample in item.get("sample_items") or []:
            links = sample.get("links") or {}
            link_items = []
            for label, url in links.items():
                link_items.append(f'<a href="{html.escape(str(url), quote=True)}">{html.escape(str(label))}</a>')
            sample_rows.append(
                "<li>"
                f"<strong>{html.escape(str(sample.get('name_ko') or sample.get('name_ja') or ''))}</strong>"
                f"<small>{html.escape(str(sample.get('affiliation') or ''))} / {html.escape(str(sample.get('sub_series') or ''))}</small>"
                f"<div>{' '.join(link_items)}</div>"
                "</li>"
            )
        cards.append(
            "<article>"
            f"<h2>P{html.escape(str(item.get('priority')))} {html.escape(str(item.get('category') or ''))} / {html.escape(str(item.get('source_store') or ''))}</h2>"
            f"<p><strong>{html.escape(str(item.get('workflow') or ''))}</strong> - {html.escape(str(item.get('rows')))} rows - "
            f"images {html.escape(str(item.get('missing_image_url')))} - sources {html.escape(str(item.get('missing_source_url')))}</p>"
            f"<p class=\"affiliations\">{html.escape(top_affiliations)}</p>"
            f"<ol>{''.join(sample_rows)}</ol>"
            "</article>"
        )
    document = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Animation Enrichment Priority Queue</title>
<style>
body {{ margin: 24px; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f8fa; color: #15171c; }}
h1 {{ margin: 0 0 8px; }}
.summary {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 20px; }}
.pill {{ padding: 5px 10px; border: 1px solid #d9dee8; border-radius: 999px; background: #fff; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; }}
article {{ background: #fff; border: 1px solid #dfe3ea; border-radius: 8px; padding: 14px; }}
h2 {{ font-size: 16px; margin: 0 0 6px; }}
p {{ margin: 0 0 10px; color: #4b5563; }}
ol {{ padding-left: 20px; }}
li {{ margin: 10px 0; }}
small {{ display: block; color: #6b7280; }}
a {{ display: inline-block; margin: 4px 8px 0 0; color: #0b57d0; }}
</style>
</head>
<body>
<h1>Animation Enrichment Priority Queue</h1>
<section class="summary">
  <span class="pill">rows {html.escape(str(payload.get('animation_rows')))}</span>
  <span class="pill">queue groups {html.escape(str(payload.get('queue_groups')))}</span>
  <span class="pill">queue rows {html.escape(str(payload.get('queue_rows')))}</span>
  <span class="pill">missing images {html.escape(str(payload.get('missing_image_rows')))}</span>
  <span class="pill">missing sources {html.escape(str(payload.get('missing_source_rows')))}</span>
</section>
<main class="grid">{''.join(cards)}</main>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def _next_batch_samples(payload: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        for sample in item.get("sample_items") or []:
            if not isinstance(sample, dict):
                continue
            samples.append(
                {
                    **sample,
                    "category": item.get("category"),
                    "source_store": item.get("source_store"),
                    "workflow": item.get("workflow"),
                }
            )
            if len(samples) >= limit:
                return samples
    return samples


def build_image_update_template(
    payload: dict[str, Any],
    *,
    limit: int = 20,
    collected_at: str | None = None,
) -> dict[str, Any]:
    updates: list[dict[str, Any]] = []
    for sample in _next_batch_samples(payload, limit=limit):
        updates.append(
            {
                "catalog_index": sample.get("catalog_index", sample.get("row_index")),
                "image_url": "https://example.com/TODO_EXACT_IMAGE_URL",
                "source_url": "https://example.com/TODO_EXACT_PRODUCT_DETAIL_URL",
                "evidence": [
                    {
                        "url": "https://example.com/TODO_EXACT_PRODUCT_DETAIL_URL",
                        "type": "official",
                        "note": (
                            "Confirm the exact product/detail page, item identity, "
                            "and visible image before changing confidence to confirmed."
                        ),
                    }
                ],
                "confidence": "needs_review",
                "notes": (
                    f"{sample.get('workflow') or ''} / "
                    f"{sample.get('source_store') or ''} / "
                    f"{sample.get('category') or ''} / "
                    f"{sample.get('affiliation') or ''} / "
                    f"{sample.get('name_ko') or sample.get('name_ja') or ''}"
                ).strip(" /"),
            }
        )
    return {
        "schema_version": 1,
        "agent": {
            "name": "animation-enrichment-reviewer",
            "run_id": "animation-next-batch",
            "collected_at": collected_at
            or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "notes": "Fill exact source/image URLs from the animation enrichment priority queue, then set confirmed rows to confidence=confirmed.",
        },
        "updates": updates,
    }


def write_image_update_template(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    template = build_image_update_template(payload)
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--image-update-template", type=Path, default=DEFAULT_IMAGE_UPDATE_TEMPLATE)
    args = parser.parse_args()

    rows = _catalog_rows(_read_json(args.seed), args.seed)
    audit = _read_json(args.audit)
    if not isinstance(audit, dict):
        raise SystemExit(f"{args.audit} must contain a JSON object")
    payload = build(rows, audit)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(args.csv_output, payload["items"])
    write_markdown(args.markdown_output, payload)
    write_html(args.html_output, payload)
    write_image_update_template(args.image_update_template, payload)
    print(
        json.dumps(
            {
                "animation_rows": payload["animation_rows"],
                "queue_groups": payload["queue_groups"],
                "queue_rows": payload["queue_rows"],
                "missing_image_rows": payload["missing_image_rows"],
                "missing_source_rows": payload["missing_source_rows"],
                "json": str(args.json_output),
                "csv": str(args.csv_output),
                "markdown": str(args.markdown_output),
                "html": str(args.html_output),
                "image_update_template": str(args.image_update_template),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
