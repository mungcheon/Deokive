from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue_current.json"
DEFAULT_JSON = ROOT / "server" / "catalog_image_review_batches.json"
DEFAULT_CSV = ROOT / "server" / "catalog_image_review_batches.csv"
DEFAULT_MD = ROOT / "server" / "catalog_image_review_batches.md"
DEFAULT_HTML = ROOT / "server" / "catalog_image_review_batches.html"
DEFAULT_CONFIRMED_TEMPLATE = ROOT / "server" / "catalog_image_confirmed_rows.template.json"
DEFAULT_PROVIDER_RECHECK = ROOT / "server" / "catalog_missing_images_report.json"


OFFICIAL_SEARCH_HOSTS = {
    "애니메이트": "animate-onlineshop.jp",
    "엔스카이": "enskyshop.com",
    "굿스마일컴퍼니": ("goodsmile.com", "goodsmile.info"),
    "FuRyu": "furyuprize.com",
    "Banpresto": "bsp-prize.jp",
    "Taito": "taito.co.jp",
    "코토부키야": "shop.kotobukiya.co.jp",
    "Movic": "movic.jp",
    "치이카와 마켓": "chiikawamarket.jp",
    "치이카와 모구모구 혼포": "chiikawamogumogu.shop",
    "나가노 마켓": "nagano-market.jp",
    "AmiAmi": "amiami.jp",
    "Cospa": "cospa.com",
    "Square Enix e-STORE": "store.jp.square-enix.com",
    "점프 캐릭터즈 스토어": "jumpcs.shueisha.co.jp",
    "무기와라스토어": "mugiwara-store.com",
    "Weverse Shop": "shop.weverse.io",
    "Stellive Store": "fanding.kr",
}
OFFICIAL_SEARCH_HOSTS.update(
    {
        "애니메이트": "animate-onlineshop.jp",
        "엔스카이": "enskyshop.com",
        "굿스마일컴퍼니": ("goodsmile.com", "goodsmile.info"),
        "코토부키야": "shop.kotobukiya.co.jp",
        "치이카와 마켓": "chiikawamarket.jp",
        "치이카와 모구모구 혼포": "chiikawamogumogu.shop",
        "나가노 마켓": "nagano-market.jp",
        "점프 캐릭터즈 스토어": "jumpcs.shueisha.co.jp",
        "무기와라스토어": "mugiwara-store.com",
    }
)


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("queue") or payload.get("items") or []
    return [item for item in items if isinstance(item, dict)]


def _load_provider_recheck(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {}
    unresolved = payload.get("unresolved") or []
    out: dict[int, dict[str, Any]] = {}
    for item in unresolved:
        if not isinstance(item, dict):
            continue
        row_index = item.get("row_index")
        if isinstance(row_index, bool) or not isinstance(row_index, int):
            continue
        out[row_index] = {
            "reason": item.get("reason"),
            "rejection_reason": item.get("rejection_reason"),
            "failed_checks": item.get("failed_checks") if isinstance(item.get("failed_checks"), list) else [],
            "candidate_count": item.get("candidate_count"),
            "best_score_overlap": item.get("best_score_overlap"),
            "best_score_similarity": item.get("best_score_similarity"),
        }
    return out


def _query(item: dict[str, Any]) -> str:
    return str(item.get("name_ja") or item.get("name_ko") or item.get("name_en") or "").strip()


def _contextual_query(item: dict[str, Any]) -> str:
    parts = [
        item.get("affiliation"),
        item.get("name_ja") or item.get("name_ko") or item.get("name_en"),
        item.get("category"),
    ]
    seen: set[str] = set()
    tokens: list[str] = []
    for part in parts:
        text = re.sub(r"\s+", " ", str(part or "").strip())
        if not text or text in seen:
            continue
        seen.add(text)
        tokens.append(text)
    return " ".join(tokens).strip() or _query(item)


def _search_links(item: dict[str, Any]) -> dict[str, str]:
    query = _query(item)
    contextual_query = _contextual_query(item)
    encoded = urllib.parse.quote(query)
    encoded_context = urllib.parse.quote(contextual_query)
    store = str(item.get("source_store") or "")
    host = OFFICIAL_SEARCH_HOSTS.get(store)
    links = {
        "web_search": f"https://www.google.com/search?q={encoded}",
        "image_search": f"https://www.google.com/search?tbm=isch&q={encoded}",
        "context_web_search": f"https://www.google.com/search?q={encoded_context}",
        "context_image_search": f"https://www.google.com/search?tbm=isch&q={encoded_context}",
    }
    if host:
        hosts = (host,) if isinstance(host, str) else tuple(host)
        for index, current_host in enumerate(hosts, start=1):
            suffix = "" if index == 1 else f"_{index}"
            links[f"official_site_search{suffix}"] = (
                f"https://www.google.com/search?q={urllib.parse.quote('site:' + current_host + ' ' + query)}"
            )
            links[f"official_context_search{suffix}"] = (
                f"https://www.google.com/search?q={urllib.parse.quote('site:' + current_host + ' ' + contextual_query)}"
            )
    source_url = str(item.get("source_url") or "").strip()
    if source_url:
        links["current_source"] = source_url
    return links


def _workflow(item: dict[str, Any]) -> str:
    safety = str(item.get("automation_safety") or "")
    strategy = str(item.get("strategy") or "")
    if safety == "candidate_provider_script_required":
        return "provider_script_recheck"
    if safety == "detail_page_validation_required":
        return "detail_page_image_validation"
    if safety == "blocked_until_exact_product_url":
        return "find_exact_product_page"
    if safety == "manual_confirmation_required":
        return "manual_official_image_confirmation"
    if strategy == "manual_review":
        return "manual_web_image_research"
    return strategy or safety or "image_review"


def _priority(item: dict[str, Any]) -> int:
    safety = str(item.get("automation_safety") or "")
    store = str(item.get("source_store") or "")
    base = {
        "candidate_provider_script_required": 10,
        "detail_page_validation_required": 20,
        "manual_confirmation_required": 30,
        "blocked_until_exact_product_url": 40,
        "manual_research_required": 50,
    }.get(safety, 70)
    if store in OFFICIAL_SEARCH_HOSTS:
        base -= 3
    if item.get("source_url"):
        base -= 2
    return max(base, 1)


def _batch_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _workflow(item),
        str(item.get("source_store") or ""),
        str(item.get("category") or ""),
        str(item.get("automation_safety") or ""),
    )


def build_batches(
    items: list[dict[str, Any]],
    provider_recheck: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    provider_recheck = provider_recheck or {}
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        row_index = item.get("row_index")
        if isinstance(row_index, int) and row_index in provider_recheck:
            item = {**item, "provider_recheck": provider_recheck[row_index]}
        grouped[_batch_key(item)].append(item)

    batches: list[dict[str, Any]] = []
    for key, group in grouped.items():
        group.sort(key=lambda item: (_priority(item), item.get("name_ja") or item.get("name_ko") or ""))
        workflow, source_store, category, automation_safety = key
        provider_reason_counts = Counter(
            str((item.get("provider_recheck") or {}).get("reason") or "")
            for item in group
            if item.get("provider_recheck")
        )
        provider_rejection_counts = Counter(
            str((item.get("provider_recheck") or {}).get("rejection_reason") or "")
            for item in group
            if (item.get("provider_recheck") or {}).get("rejection_reason")
        )
        provider_failed_checks = Counter(
            str(check)
            for item in group
            for check in ((item.get("provider_recheck") or {}).get("failed_checks") or [])
            if check
        )
        batches.append(
            {
                "priority": _priority(group[0]),
                "workflow": workflow,
                "source_store": source_store,
                "category": category,
                "automation_safety": automation_safety,
                "strategy": group[0].get("strategy"),
                "row_count": len(group),
                "official_search_host": OFFICIAL_SEARCH_HOSTS.get(source_store),
                "official_search_hosts": (
                    list(OFFICIAL_SEARCH_HOSTS.get(source_store))
                    if isinstance(OFFICIAL_SEARCH_HOSTS.get(source_store), tuple)
                    else ([OFFICIAL_SEARCH_HOSTS[source_store]] if source_store in OFFICIAL_SEARCH_HOSTS else [])
                ),
                "has_source_url_count": sum(1 for item in group if item.get("source_url")),
                "provider_recheck_count": sum(1 for item in group if item.get("provider_recheck")),
                "provider_recheck_by_reason": provider_reason_counts.most_common(),
                "provider_recheck_by_rejection_reason": provider_rejection_counts.most_common(),
                "provider_recheck_failed_checks": provider_failed_checks.most_common(),
                "sample_items": [
                    {
                        "row_index": item.get("row_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "affiliation": item.get("affiliation"),
                        "search_query": _query(item),
                        "contextual_search_query": _contextual_query(item),
                        "links": _search_links(item),
                        "provider_recheck": item.get("provider_recheck"),
                    }
                    for item in group[:16]
                ],
            }
        )

    batches.sort(
        key=lambda item: (
            item["priority"],
            -item["row_count"],
            item["source_store"],
            item["category"],
        )
    )
    return {
        "source": str(DEFAULT_QUEUE.relative_to(ROOT)),
        "missing_images": len(items),
        "batch_count": len(batches),
        "by_workflow": Counter(_workflow(item) for item in items),
        "by_source_store": Counter(str(item.get("source_store") or "") for item in items),
        "by_automation_safety": Counter(str(item.get("automation_safety") or "") for item in items),
        "provider_recheck_rows": len(provider_recheck),
        "batches": batches,
    }


def build_confirmed_template(items: list[dict[str, Any]], limit: int = 500) -> dict[str, Any]:
    sorted_items = sorted(
        items,
        key=lambda item: (
            _priority(item),
            str(item.get("source_store") or ""),
            str(item.get("category") or ""),
            str(item.get("name_ko") or ""),
        ),
    )
    template_items: list[dict[str, Any]] = []
    for item in sorted_items[:limit]:
        links = _search_links(item)
        template_items.append(
            {
                "manual_confirmed": False,
                "manual_note": "",
                "row_index": item.get("row_index"),
                "field": "image_url",
                "manual_value": "",
                "evidence_url": item.get("source_url") or "",
                "candidate_source_url": "",
                "candidate_image_url": "",
                "review_links": links,
                "source_store": item.get("source_store"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "category": item.get("category"),
                "affiliation": item.get("affiliation"),
                "acceptance_criteria": (
                    "Use an image URL from the exact official product/detail page. "
                    "Set evidence_url or candidate_source_url to that exact page before confirming."
                ),
                "automation_safety": item.get("automation_safety"),
                "strategy": item.get("strategy"),
            }
        )
    return {
        "instructions": [
            "Copy reviewed items into server/catalog_field_confirmed_rows.json or use this file as the queue with --queue.",
            "For each item, set manual_value to the final image URL and manual_confirmed to true.",
            "Set evidence_url or candidate_source_url to the exact product/detail page that proves the image.",
            "The importer rejects generic images, unsafe source/image pairs, identity mismatches, and existing conflicts.",
        ],
        "items": template_items,
    }


def _json_ready(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "by_workflow": payload["by_workflow"].most_common(),
        "by_source_store": payload["by_source_store"].most_common(),
        "by_automation_safety": payload["by_automation_safety"].most_common(),
    }


def _write_csv(path: Path, batches: list[dict[str, Any]]) -> None:
    fields = [
        "priority",
        "workflow",
        "source_store",
        "category",
        "automation_safety",
        "strategy",
        "row_count",
        "official_search_host",
        "has_source_url_count",
        "provider_recheck_count",
        "provider_recheck_by_reason",
        "provider_recheck_failed_checks",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for batch in batches:
            writer.writerow({field: batch.get(field) for field in fields})


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Catalog Image Review Batches",
        "",
        f"- Missing images: `{payload['missing_images']}`",
        f"- Batch count: `{payload['batch_count']}`",
        f"- Provider recheck rows: `{payload.get('provider_recheck_rows', 0)}`",
        "",
        "## By Workflow",
    ]
    for workflow, count in payload["by_workflow"].most_common():
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "## Top Batches"])
    for batch in payload["batches"][:120]:
        lines.append(
            f"- P{batch['priority']} `{batch['workflow']}` / `{batch['source_store']}` / "
            f"`{batch['category']}`: `{batch['row_count']}` rows"
        )
        if batch.get("provider_recheck_count"):
            lines.append(
                f"  - Provider recheck: `{batch.get('provider_recheck_count')}` rows, "
                f"reasons `{batch.get('provider_recheck_by_reason')}`, "
                f"failed checks `{batch.get('provider_recheck_failed_checks')}`"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_html(path: Path, payload: dict[str, Any]) -> None:
    cards: list[str] = []
    for batch in payload["batches"][:240]:
        samples: list[str] = []
        for item in batch["sample_items"]:
            links = item.get("links") or {}
            link_html = " ".join(
                f'<a href="{html.escape(url)}">{html.escape(label.replace("_", " "))}</a>'
                for label, url in links.items()
            )
            title = html.escape(str(item.get("name_ja") or item.get("name_ko") or ""))
            sub = html.escape(
                f"row {item.get('row_index')} · {item.get('affiliation') or item.get('name_ko') or ''}"
            )
            provider = item.get("provider_recheck") or {}
            provider_html = ""
            if provider:
                checks = ", ".join(str(check) for check in provider.get("failed_checks") or [])
                provider_html = (
                    '<small class="provider">'
                    f"provider: {html.escape(str(provider.get('reason') or ''))}"
                    f" / {html.escape(str(provider.get('rejection_reason') or ''))}"
                    f" / candidates {html.escape(str(provider.get('candidate_count') or 0))}"
                    f" / checks {html.escape(checks or '-')}"
                    "</small>"
                )
            samples.append(f"<li><strong>{title}</strong><small>{sub}</small>{provider_html}<nav>{link_html}</nav></li>")
        provider_summary = ""
        if batch.get("provider_recheck_count"):
            provider_summary = (
                '<p class="provider-summary">'
                f"provider recheck {batch.get('provider_recheck_count')} rows · "
                f"reasons {html.escape(str(batch.get('provider_recheck_by_reason')))} · "
                f"failed checks {html.escape(str(batch.get('provider_recheck_failed_checks')))}"
                "</p>"
            )
        cards.append(
            "<article>"
            f"<h2>P{batch['priority']} {html.escape(str(batch.get('source_store') or ''))}</h2>"
            f"<p>{html.escape(str(batch.get('category') or ''))} · {html.escape(str(batch.get('workflow') or ''))} · "
            f"{batch.get('row_count')} rows</p>"
            f"<p><strong>{html.escape(str(batch.get('automation_safety') or ''))}</strong> · "
            f"source URLs {batch.get('has_source_url_count')}</p>"
            f"{provider_summary}"
            f"<ol>{''.join(samples)}</ol>"
            "</article>"
        )
    document = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catalog Image Review Batches</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f6f7f9; color: #17181c; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; }}
article {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
h1, h2, p {{ margin: 0 0 8px; }}
h2 {{ font-size: 16px; }}
ol {{ padding-left: 20px; }}
li {{ margin: 12px 0; }}
small {{ display: block; color: #667085; margin-top: 2px; }}
.provider {{ color: #8a4b00; }}
.provider-summary {{ color: #8a4b00; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 8px; }}
nav {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }}
a {{ color: #0b57d0; font-weight: 700; }}
</style>
</head>
<body>
<h1>Catalog Image Review Batches</h1>
<p>{payload['missing_images']} missing images · {payload['batch_count']} batches</p>
<main class="grid">{''.join(cards)}</main>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--confirmed-template", type=Path, default=DEFAULT_CONFIRMED_TEMPLATE)
    parser.add_argument("--confirmed-template-limit", type=int, default=500)
    parser.add_argument("--provider-recheck", type=Path, default=DEFAULT_PROVIDER_RECHECK)
    args = parser.parse_args()

    items = _load_items(args.queue)
    provider_recheck = _load_provider_recheck(args.provider_recheck)
    payload = build_batches(items, provider_recheck=provider_recheck)
    json_payload = _json_ready(payload)
    confirmed_template = build_confirmed_template(items, limit=args.confirmed_template_limit)
    args.json.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.confirmed_template.write_text(
        json.dumps(confirmed_template, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(args.csv, payload["batches"])
    _write_markdown(args.markdown, payload)
    _write_html(args.html, payload)
    print(
        json.dumps(
            {
                "missing_images": payload["missing_images"],
                "batch_count": payload["batch_count"],
                "json": str(args.json),
                "html": str(args.html),
                "confirmed_template": str(args.confirmed_template),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
