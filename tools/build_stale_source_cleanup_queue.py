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
DEFAULT_AUDIT = SERVER / "live_source_identity_audit.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_JSON = SERVER / "stale_source_cleanup_queue.json"
DEFAULT_CSV = SERVER / "stale_source_cleanup_queue.csv"
DEFAULT_MD = SERVER / "stale_source_cleanup_queue.md"
DEFAULT_HTML = SERVER / "stale_source_cleanup_queue.html"


FIELDS = [
    "row_index",
    "catalog_index",
    "match_method",
    "name_ko",
    "name_ja",
    "source_store",
    "current_source_url",
    "current_image_url",
    "live_title",
    "shared_tokens",
    "source_url_row_count",
    "risk",
    "identity_status",
    "recommended_action",
    "candidate_source_url",
    "manual_confirmed",
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_seed_rows(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        payload = payload["items"]
    if not isinstance(payload, list):
        raise SystemExit(f"{path} must contain a JSON list or public catalog object with items")
    return [row for row in payload if isinstance(row, dict)]


def _seed_row(seed_rows: list[dict[str, Any]], row_index: Any) -> dict[str, Any]:
    try:
        index = int(row_index)
    except (TypeError, ValueError):
        return {}
    if 0 <= index < len(seed_rows) and isinstance(seed_rows[index], dict):
        return seed_rows[index]
    return {}


def _audit_row_matches_current_seed(row: dict[str, Any], current: dict[str, Any]) -> bool:
    audit_ko = str(row.get("name_ko") or "").strip()
    audit_ja = str(row.get("name_ja") or "").strip()
    current_ko = str(current.get("name_ko") or "").strip()
    current_ja = str(current.get("name_ja") or "").strip()
    if not audit_ko and not audit_ja:
        return True
    return bool((audit_ko and audit_ko == current_ko) or (audit_ja and audit_ja == current_ja))


def _find_current_seed_row(
    seed_rows: list[dict[str, Any]],
    audit_row: dict[str, Any],
    source_url: Any,
) -> tuple[dict[str, Any], str]:
    indexed = _seed_row(seed_rows, audit_row.get("row_index"))
    if indexed and _audit_row_matches_current_seed(audit_row, indexed):
        return indexed, "row_index"

    audit_ko = str(audit_row.get("name_ko") or "").strip()
    audit_ja = str(audit_row.get("name_ja") or "").strip()
    source = str(source_url or "").strip()
    for current in seed_rows:
        if source and str(current.get("source_url") or "").strip() != source:
            continue
        current_ko = str(current.get("name_ko") or "").strip()
        current_ja = str(current.get("name_ja") or "").strip()
        if (audit_ko and audit_ko == current_ko) or (audit_ja and audit_ja == current_ja):
            return current, "name_source_url"

    return indexed, "unmatched"


def build_queue(audit: dict[str, Any], seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for result in audit.get("results") or []:
        if not isinstance(result, dict) or result.get("status") not in {
            "live_title_mismatch",
            "weak_title_overlap",
        }:
            continue
        for row in result.get("rows") or []:
            if not isinstance(row, dict) or row.get("status") not in {
                "live_title_mismatch",
                "weak_title_overlap",
            }:
                continue
            current, match_method = _find_current_seed_row(seed_rows, row, result.get("source_url"))
            if match_method == "unmatched" and current and not _audit_row_matches_current_seed(row, current):
                skipped.append(
                    {
                        "row_index": row.get("row_index"),
                        "reason": "audit_row_name_mismatch",
                        "audit_name_ko": row.get("name_ko"),
                        "audit_name_ja": row.get("name_ja"),
                        "current_name_ko": current.get("name_ko"),
                        "current_name_ja": current.get("name_ja"),
                        "source_url": result.get("source_url"),
                    }
                )
                continue
            current_image = current.get("image_url") or ""
            identity_status = str(row.get("status") or result.get("status") or "")
            is_mismatch = identity_status == "live_title_mismatch"
            item = {
                "row_index": row.get("row_index"),
                "catalog_index": current.get("catalog_index"),
                "match_method": match_method,
                "name_ko": current.get("name_ko") or row.get("name_ko"),
                "name_ja": current.get("name_ja") or row.get("name_ja"),
                "source_store": current.get("source_store") or result.get("source_store"),
                "current_source_url": current.get("source_url") or result.get("source_url"),
                "current_image_url": current_image,
                "live_title": result.get("live_title"),
                "shared_tokens": row.get("shared_tokens") or [],
                "source_url_row_count": result.get("row_count"),
                "risk": "stale_source_points_to_different_live_product"
                if is_mismatch
                else "weak_source_identity_overlap",
                "identity_status": identity_status,
                "recommended_action": "find_exact_source_url_before_image_use"
                if current_image and is_mismatch
                else "review_source_url_before_image_use"
                if current_image
                else "find_exact_source_url_before_image_import"
                if is_mismatch
                else "review_source_url_before_image_import",
                "candidate_source_url": "",
                "manual_confirmed": False,
            }
            items.append(item)

    by_store = Counter(str(item.get("source_store") or "") for item in items)
    by_action = Counter(str(item.get("recommended_action") or "") for item in items)
    by_risk = Counter(str(item.get("risk") or "") for item in items)
    by_identity_status = Counter(str(item.get("identity_status") or "") for item in items)
    mismatch_urls = len(
        {
            item.get("current_source_url")
            for item in items
            if item.get("current_source_url")
            and item.get("identity_status") == "live_title_mismatch"
        }
    )
    weak_urls = len(
        {
            item.get("current_source_url")
            for item in items
            if item.get("current_source_url")
            and item.get("identity_status") == "weak_title_overlap"
        }
    )
    return {
        "summary": {
            "review_rows": len(items),
            "mismatch_rows": by_identity_status.get("live_title_mismatch", 0),
            "weak_overlap_rows": by_identity_status.get("weak_title_overlap", 0),
            "mismatch_urls": mismatch_urls,
            "weak_overlap_urls": weak_urls,
            "skipped_rows": len(skipped),
            "skipped_by_reason": sorted(Counter(str(item.get("reason") or "") for item in skipped).items()),
            "by_source_store": sorted(by_store.items()),
            "by_recommended_action": sorted(by_action.items()),
            "by_risk": sorted(by_risk.items()),
            "by_identity_status": sorted(by_identity_status.items()),
        },
        "items": items,
        "skipped_sample": skipped[:100],
        "instructions": [
            "Do not propagate image_url values from these rows until the current_source_url has been replaced or confirmed.",
            "Rows marked weak_source_identity_overlap are not proven stale, but generic token overlap is too weak for automatic enrichment.",
            "Prefer an exact official product/detail URL. Use candidate_source_url and manual_confirmed=true only after review.",
            "If no exact replacement is found, clear or ignore the stale source/image evidence instead of reusing it for enrichment.",
        ],
    }


def write_csv(payload: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for item in payload.get("items") or []:
            row = dict(item)
            row["shared_tokens"] = ", ".join(str(token) for token in row.get("shared_tokens") or [])
            writer.writerow(row)


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# Stale Source Cleanup Queue",
        "",
        f"- Review rows: `{summary['review_rows']}`",
        f"- Mismatch rows: `{summary['mismatch_rows']}`",
        f"- Weak overlap rows: `{summary.get('weak_overlap_rows', 0)}`",
        f"- Mismatch URLs: `{summary['mismatch_urls']}`",
        f"- Weak overlap URLs: `{summary.get('weak_overlap_urls', 0)}`",
        "",
        "## Instructions",
    ]
    for instruction in payload.get("instructions") or []:
        lines.append(f"- {instruction}")
    lines.extend(["", "## Rows"])
    for item in (payload.get("items") or [])[:120]:
        lines.append(
            f"- Row `{item.get('row_index')}` {item.get('name_ko')}: "
            f"`{item.get('identity_status')}` / `{item.get('live_title')}` -> {item.get('current_source_url')}"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def write_html(payload: dict[str, Any], path: Path) -> None:
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('row_index')))}</td>"
        f"<td>{html.escape(str(item.get('name_ko') or ''))}<br><small>{html.escape(str(item.get('name_ja') or ''))}</small></td>"
        f"<td>{html.escape(str(item.get('source_store') or ''))}</td>"
        f"<td><a href=\"{html.escape(str(item.get('current_source_url') or ''))}\">source</a></td>"
        f"<td>{html.escape(str(item.get('live_title') or ''))}</td>"
        f"<td>{html.escape(str(item.get('identity_status') or ''))}</td>"
        f"<td>{html.escape(str(item.get('recommended_action') or ''))}</td>"
        "</tr>"
        for item in payload.get("items") or []
    )
    summary = payload["summary"]
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stale Source Cleanup Queue</title>
<style>
body {{ margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #17191f; background: #f6f7f9; }}
header {{ padding: 24px; background: #fff; border-bottom: 1px solid #dde2ea; }}
main {{ max-width: 1280px; margin: auto; padding: 20px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px; }}
article, table {{ background: #fff; border: 1px solid #dde2ea; border-radius: 10px; }}
article {{ padding: 14px; }}
article span {{ display: block; color: #667085; }}
article strong {{ display: block; font-size: 28px; }}
table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #edf0f4; vertical-align: top; text-align: left; }}
th {{ background: #f9fafb; position: sticky; top: 0; }}
small {{ color: #667085; }}
a {{ color: #0b57d0; font-weight: 700; }}
</style>
</head>
<body>
<header>
  <h1>Stale Source Cleanup Queue</h1>
  <div>Rows whose current source URL opens as a different live product.</div>
</header>
<main>
  <section class="summary">
    <article><span>Review rows</span><strong>{html.escape(str(summary.get('review_rows')))}</strong></article>
    <article><span>Mismatch rows</span><strong>{html.escape(str(summary.get('mismatch_rows')))}</strong></article>
    <article><span>Weak overlap rows</span><strong>{html.escape(str(summary.get('weak_overlap_rows')))}</strong></article>
    <article><span>Mismatch URLs</span><strong>{html.escape(str(summary.get('mismatch_urls')))}</strong></article>
    <article><span>Weak overlap URLs</span><strong>{html.escape(str(summary.get('weak_overlap_urls')))}</strong></article>
  </section>
  <table>
    <thead><tr><th>Row</th><th>Catalog item</th><th>Store</th><th>Current URL</th><th>Live title</th><th>Status</th><th>Action</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</main>
</body>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    audit = _read_json(args.audit)
    if not isinstance(audit, dict):
        raise SystemExit(f"{args.audit} must contain a JSON object")
    seed_rows = _load_seed_rows(args.seed)
    payload = build_queue(audit, seed_rows)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(payload, args.csv_output)
    write_markdown(payload, args.markdown_output)
    write_html(payload, args.html_output)
    print(
        json.dumps(
            {
                "mismatch_rows": payload["summary"]["mismatch_rows"],
                "weak_overlap_rows": payload["summary"]["weak_overlap_rows"],
                "mismatch_urls": payload["summary"]["mismatch_urls"],
                "weak_overlap_urls": payload["summary"]["weak_overlap_urls"],
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
