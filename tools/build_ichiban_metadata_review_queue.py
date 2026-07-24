from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DEFAULT_AUDIT = SERVER / "ichiban_kuji_metadata_audit.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_JSON = SERVER / "ichiban_kuji_metadata_review_queue.json"
DEFAULT_CSV = SERVER / "ichiban_kuji_metadata_review_queue.csv"
DEFAULT_MD = SERVER / "ichiban_kuji_metadata_review_queue.md"
DEFAULT_HTML = SERVER / "ichiban_kuji_metadata_review_queue.html"


def _read_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _read_seed_rows(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _rows_by_url(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        url = str(row.get("source_url") or "")
        if "1kuji.com/products/" not in url:
            continue
        if _present(row.get("release_date")) and _present(row.get("official_price_jpy")):
            continue
        grouped.setdefault(url, []).append(
            {
                "row_index": index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "category": row.get("category"),
                "character_name": row.get("character_name"),
                "series_name": row.get("series_name"),
                "sub_series": row.get("sub_series"),
                "release_date": row.get("release_date"),
                "official_price_jpy": row.get("official_price_jpy"),
                "missing_release_date": not _present(row.get("release_date")),
                "missing_official_price_jpy": not _present(row.get("official_price_jpy")),
            }
        )
    return grouped


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _workflow(page: dict[str, Any]) -> str:
    missing_release = int(page.get("missing_release_rows") or 0)
    missing_price = int(page.get("missing_price_rows") or 0)
    if missing_release and missing_price:
        return "manual_release_and_price_review"
    if missing_release:
        return "manual_release_review"
    return "manual_price_review"


def _date_candidates(page: dict[str, Any]) -> list[str]:
    dates = [str(item) for item in page.get("all_dates") or [] if item]
    double_chance = {str(item) for item in page.get("double_chance_dates") or [] if item}
    return [f"{date} (double chance)" if date in double_chance else date for date in dates]


def build_queue(
    payload: dict[str, Any],
    source_audit: Path | None = None,
    seed_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows_by_url = _rows_by_url(seed_rows or [])
    items: list[dict[str, Any]] = []
    for page in payload.get("pages") or []:
        if not isinstance(page, dict):
            continue
        missing_release = int(page.get("missing_release_rows") or 0)
        missing_price = int(page.get("missing_price_rows") or 0)
        if not missing_release and not missing_price:
            continue
        safe_release = page.get("safe_release_date")
        safe_price = page.get("safe_price_jpy")
        if (not missing_release or safe_release) and (not missing_price or safe_price):
            continue
        row_samples = rows_by_url.get(str(page.get("url") or ""), [])[:12]
        items.append(
            {
                "url": page.get("url"),
                "title": page.get("title"),
                "rows": page.get("rows"),
                "missing_release_rows": missing_release,
                "missing_price_rows": missing_price,
                "workflow": _workflow(page),
                "date_candidates": _date_candidates(page),
                "release_blocker": page.get("safe_release_reason"),
                "price_blocker": page.get("safe_price_reason"),
                "ambiguous": bool(page.get("ambiguous")),
                "row_samples": row_samples,
                "row_sample_count": len(row_samples),
                "needs_evidence": _needed_evidence(page),
            }
        )

    workflow_counts = Counter(str(item.get("workflow") or "") for item in items)
    return {
        "summary": {
            "source_audit": str(source_audit or DEFAULT_AUDIT),
            "review_items": len(items),
            "missing_release_rows": sum(int(item.get("missing_release_rows") or 0) for item in items),
            "missing_price_rows": sum(int(item.get("missing_price_rows") or 0) for item in items),
            "by_workflow": workflow_counts.most_common(),
            "instructions": [
                "Review official pages manually before filling release_date or official_price_jpy.",
                "Dates marked double chance are not release dates.",
                "Do not import month-only or unlabeled dates unless another official source confirms the release date.",
                "Use row_samples to confirm which seed rows would be affected before preparing a metadata import.",
            ],
        },
        "items": items,
    }


def _needed_evidence(page: dict[str, Any]) -> list[str]:
    evidence = []
    if int(page.get("missing_release_rows") or 0) and not page.get("safe_release_date"):
        evidence.append("labeled_official_release_date")
    if int(page.get("missing_price_rows") or 0) and not page.get("safe_price_jpy"):
        evidence.append("labeled_official_price_jpy")
    return evidence


def write_csv(payload: dict[str, Any], path: Path) -> None:
    fields = [
        "url",
        "title",
        "rows",
        "missing_release_rows",
        "missing_price_rows",
        "workflow",
        "date_candidates",
        "release_blocker",
        "price_blocker",
        "ambiguous",
        "row_sample_count",
        "row_samples",
        "needs_evidence",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for item in payload.get("items") or []:
            samples = item.get("row_samples") or []
            sample_text = "; ".join(
                f"{sample.get('row_index')}:{sample.get('name_ko') or sample.get('name_ja')}"
                for sample in samples
            )
            writer.writerow(
                {
                    **item,
                    "date_candidates": "; ".join(item.get("date_candidates") or []),
                    "row_samples": sample_text,
                    "needs_evidence": "; ".join(item.get("needs_evidence") or []),
                }
            )


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# Ichiban Kuji Metadata Review Queue",
        "",
        f"- Review items: `{summary['review_items']}`",
        f"- Missing release_date rows: `{summary['missing_release_rows']}`",
        f"- Missing official_price_jpy rows: `{summary['missing_price_rows']}`",
        "",
        "## Workflow Counts",
        "",
    ]
    for workflow, count in summary.get("by_workflow") or []:
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "## Items", ""])
    for item in payload.get("items") or []:
        dates = ", ".join(item.get("date_candidates") or []) or "none"
        lines.append(
            f"- `{item.get('url')}` {item.get('title')}: "
            f"release `{item.get('missing_release_rows')}`, price `{item.get('missing_price_rows')}`, "
            f"rows sampled `{item.get('row_sample_count')}`, needs `{', '.join(item.get('needs_evidence') or [])}`, "
            f"dates `{dates}`"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    rows = "\n".join(
        "<tr>"
        f"<td><a href=\"{html.escape(str(item.get('url') or ''))}\">{html.escape(str(item.get('url') or ''))}</a></td>"
        f"<td>{html.escape(str(item.get('title') or ''))}</td>"
        f"<td>{html.escape(str(item.get('workflow') or ''))}</td>"
        f"<td>{html.escape(str(item.get('missing_release_rows') or 0))}</td>"
        f"<td>{html.escape(str(item.get('missing_price_rows') or 0))}</td>"
        f"<td>{html.escape(', '.join(item.get('date_candidates') or []))}</td>"
        f"<td>{html.escape(str(item.get('row_sample_count') or 0))}</td>"
        f"<td>{html.escape(', '.join(item.get('needs_evidence') or []))}</td>"
        f"<td>{html.escape(str(item.get('release_blocker') or ''))}<br>{html.escape(str(item.get('price_blocker') or ''))}</td>"
        "</tr>"
        for item in payload.get("items") or []
    )
    path.write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ichiban Kuji Metadata Review Queue</title>
<style>
body {{ margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #17191f; background: #f6f7f9; }}
header {{ padding: 24px; background: #fff; border-bottom: 1px solid #dde2ea; }}
main {{ max-width: 1400px; margin: auto; padding: 20px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px; }}
article, table {{ background: #fff; border: 1px solid #dde2ea; border-radius: 10px; }}
article {{ padding: 14px; }}
article span {{ display: block; color: #667085; }}
article strong {{ display: block; font-size: 28px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #edf0f4; text-align: left; vertical-align: top; }}
th {{ background: #f9fafb; }}
a {{ color: #2454d6; }}
</style>
</head>
<body>
<header><h1>Ichiban Kuji Metadata Review Queue</h1><div>Official pages that still need manual release/price metadata review.</div></header>
<main>
<section class="summary">
  <article><span>Review items</span><strong>{html.escape(str(summary['review_items']))}</strong></article>
  <article><span>Missing release rows</span><strong>{html.escape(str(summary['missing_release_rows']))}</strong></article>
  <article><span>Missing price rows</span><strong>{html.escape(str(summary['missing_price_rows']))}</strong></article>
</section>
<table><thead><tr><th>URL</th><th>Title</th><th>Workflow</th><th>Release</th><th>Price</th><th>Date candidates</th><th>Rows</th><th>Needs</th><th>Blockers</th></tr></thead><tbody>{rows}</tbody></table>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    payload = build_queue(_read_payload(args.audit), source_audit=args.audit, seed_rows=_read_seed_rows(args.seed))
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(payload, args.csv_output)
    write_markdown(payload, args.markdown_output)
    write_html(payload, args.html_output)
    print(
        json.dumps(
            {
                **payload["summary"],
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
