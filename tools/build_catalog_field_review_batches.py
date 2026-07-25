from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = ROOT / "server" / "catalog_field_enrichment_queue_current.json"
DEFAULT_JSON = ROOT / "server" / "catalog_field_review_batches_current.json"
DEFAULT_CSV = ROOT / "server" / "catalog_field_review_batches_current.csv"
DEFAULT_MD = ROOT / "server" / "catalog_field_review_batches_current.md"
DEFAULT_HTML = ROOT / "server" / "catalog_field_review_batches_current.html"


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("queue") or payload.get("items") or payload.get("rows") or []
    return [item for item in items if isinstance(item, dict)]


def _batch_key(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(item.get("workstream") or ""),
        str(item.get("source_store") or ""),
        str(item.get("category") or ""),
        str(item.get("field") or ""),
        str(item.get("applicability") or ""),
    )


def _workflow(item: dict[str, Any]) -> str:
    field = str(item.get("field") or "")
    source_group = str(item.get("source_group") or "")
    has_evidence_url = bool(item.get("search_url") or item.get("source_url"))
    if not has_evidence_url:
        return "manual_source_discovery"
    if item.get("automation_candidate") and field in {"source_url", "image_url"}:
        return "exact_url_or_image_lookup"
    if item.get("automation_candidate") and field in {"release_date", "official_price_jpy"}:
        return "official_metadata_lookup"
    if source_group == "kuji":
        return "campaign_metadata_review"
    if field == "barcode":
        return "manual_barcode_evidence"
    return "manual_evidence_review"


def _priority(item: dict[str, Any]) -> int:
    if not item.get("actionable_now"):
        return 90
    field = str(item.get("field") or "")
    source_group = str(item.get("source_group") or "")
    base = {
        "source_url": 10,
        "image_url": 20,
        "release_date": 30,
        "official_price_jpy": 40,
        "barcode": 50,
    }.get(field, 80)
    group_bonus = {
        "chiikawa_official": 0,
        "animation_goods": 5,
        "kuji": 10,
        "global_vtuber": 20,
        "korea_vtuber": 25,
        "kpop_official": 25,
    }.get(source_group, 30)
    if str(item.get("risk") or "") == "high":
        group_bonus += 10
    if not (item.get("search_url") or item.get("source_url")):
        group_bonus += 18
    return base + group_bonus


def build_batches(items: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[_batch_key(item)].append(item)

    batches: list[dict[str, Any]] = []
    for key, group in grouped.items():
        group.sort(
            key=lambda item: (
                _priority(item),
                item.get("row_index") or 999999,
                item.get("name_ko") or "",
            )
        )
        first = group[0]
        no_evidence_url_count = sum(1 for item in group if not (item.get("search_url") or item.get("source_url")))
        workstream, source_store, category, field, applicability = key
        priority = _priority(first)
        batches.append(
            {
                "priority": priority,
                "workflow": _workflow(first),
                "workstream": workstream,
                "source_group": first.get("source_group"),
                "source_store": source_store,
                "category": category,
                "field": field,
                "applicability": applicability,
                "risk": first.get("risk"),
                "actionable_now": bool(first.get("actionable_now")),
                "automation_candidate": bool(first.get("automation_candidate")),
                "no_evidence_url_count": no_evidence_url_count,
                "row_count": len(group),
                "batch_hint": first.get("batch_hint"),
                "acceptance_criteria": first.get("acceptance_criteria"),
                "sample_items": [
                    {
                        "row_index": item.get("row_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "evidence_url": item.get("search_url") or item.get("source_url"),
                        "note": item.get("note"),
                    }
                    for item in group[:12]
                ],
            }
        )

    batches.sort(
        key=lambda item: (
            item["priority"],
            not item["automation_candidate"],
            -item["row_count"],
            item["source_store"],
            item["category"],
            item["field"],
        )
    )
    actionable = [item for item in items if item.get("actionable_now")]
    return {
        "source": str(DEFAULT_QUEUE.relative_to(ROOT)),
        "queue_rows": len(items),
        "actionable_rows": len(actionable),
        "non_actionable_rows": len(items) - len(actionable),
        "batch_count": len(batches),
        "by_field": Counter(str(item.get("field") or "") for item in items),
        "by_workflow": Counter(item["workflow"] for item in batches),
        "by_applicability": Counter(str(item.get("applicability") or "") for item in items),
        "by_source_group": Counter(str(item.get("source_group") or "") for item in items),
        "batches": batches,
    }


def _write_csv(path: Path, batches: list[dict[str, Any]]) -> None:
    fields = [
        "priority",
        "workflow",
        "workstream",
        "source_group",
        "source_store",
        "category",
        "field",
        "applicability",
        "risk",
        "actionable_now",
        "automation_candidate",
        "no_evidence_url_count",
        "row_count",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for batch in batches:
            writer.writerow({field: batch.get(field) for field in fields})


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Catalog Field Review Batches",
        "",
        f"- Queue rows: `{payload['queue_rows']}`",
        f"- Actionable rows: `{payload['actionable_rows']}`",
        f"- Non-actionable rows: `{payload['non_actionable_rows']}`",
        f"- Batch count: `{payload['batch_count']}`",
        "",
        "## By Field",
    ]
    for field, count in payload["by_field"].most_common():
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(["", "## By Workflow"])
    for workflow, count in payload["by_workflow"].most_common():
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "## Top Batches"])
    for batch in payload["batches"][:100]:
        lines.append(
            f"- P{batch['priority']} `{batch['workflow']}` / `{batch['source_store']}` / "
            f"`{batch['category']}` / `{batch['field']}`: `{batch['row_count']}` rows"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_html(path: Path, payload: dict[str, Any]) -> None:
    cards: list[str] = []
    for batch in payload["batches"][:240]:
        samples = []
        for item in batch["sample_items"]:
            url = html.escape(str(item.get("evidence_url") or ""))
            title = html.escape(str(item.get("name_ja") or item.get("name_ko") or ""))
            note = html.escape(str(item.get("note") or ""))
            samples.append(
                f"<li><a href=\"{url}\">{title}</a><small>row {item.get('row_index')} {note}</small></li>"
            )
        cards.append(
            "<article>"
            f"<h2>P{batch['priority']} {html.escape(str(batch.get('source_store') or ''))}</h2>"
            f"<p>{html.escape(str(batch.get('category') or ''))} · {html.escape(str(batch.get('field') or ''))} · "
            f"{html.escape(str(batch.get('workflow') or ''))} · {batch.get('row_count')} rows</p>"
            f"<p><strong>{html.escape(str(batch.get('applicability') or ''))}</strong> · risk {html.escape(str(batch.get('risk') or ''))}</p>"
            f"<p>{html.escape(str(batch.get('acceptance_criteria') or ''))}</p>"
            f"<ol>{''.join(samples)}</ol>"
            "</article>"
        )
    document = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Catalog Field Review Batches</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f6f7f9; color: #17181c; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; }}
article {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
h1, h2, p {{ margin: 0 0 8px; }}
h2 {{ font-size: 16px; }}
ol {{ padding-left: 20px; }}
li {{ margin: 10px 0; }}
small {{ display: block; color: #667085; margin-top: 2px; }}
a {{ color: #1a5fb4; }}
</style>
</head>
<body>
<h1>Catalog Field Review Batches</h1>
<p>{payload['actionable_rows']} actionable rows · {payload['batch_count']} batches</p>
<main class="grid">{''.join(cards)}</main>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def _json_ready(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "by_field": payload["by_field"].most_common(),
        "by_workflow": payload["by_workflow"].most_common(),
        "by_applicability": payload["by_applicability"].most_common(),
        "by_source_group": payload["by_source_group"].most_common(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    payload = build_batches(_load_items(args.queue))
    json_payload = _json_ready(payload)
    args.json_output.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_csv(args.csv_output, payload["batches"])
    _write_markdown(args.markdown_output, payload)
    _write_html(args.html_output, payload)
    print(
        json.dumps(
            {
                "queue_rows": payload["queue_rows"],
                "actionable_rows": payload["actionable_rows"],
                "batch_count": payload["batch_count"],
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
