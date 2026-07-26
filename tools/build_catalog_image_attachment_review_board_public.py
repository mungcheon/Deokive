from __future__ import annotations

import argparse
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
DATA = ROOT / "data"
DEFAULT_TEMPLATE = DATA / "catalog_image_attachment_confirmed_template_public.json"
DEFAULT_JSON = DATA / "catalog_image_attachment_review_board_public.json"
DEFAULT_MD = DATA / "catalog_image_attachment_review_board_public.md"
DEFAULT_HTML = DATA / "catalog_image_attachment_review_board_public.html"


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def _items(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def _review_url(item: dict[str, Any]) -> str:
    for key in ("current_source_url", "candidate_source_url", "evidence_url", "official_search_url", "source_search_url"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _lane_rank(item: dict[str, Any]) -> tuple[int, str, int]:
    lane = str(item.get("review_lane") or "")
    if lane == "image_url_review_ready":
        rank = 0
    elif lane == "representative_image_candidate_review":
        rank = 1
    else:
        rank = 2
    return (rank, str(item.get("source_store") or ""), int(item.get("catalog_index") or item.get("row_index") or 0))


def build_board(template: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items = sorted(_items(template), key=_lane_rank)
    board_items: list[dict[str, Any]] = []
    blocker_counter: Counter[str] = Counter()
    lane_counter: Counter[str] = Counter()
    store_counter: Counter[str] = Counter()
    batch_counter: Counter[str] = Counter()
    for item in items:
        blockers = [str(value) for value in item.get("image_import_blockers") or []]
        blocker_counter.update(blockers)
        lane = str(item.get("review_lane") or "unknown")
        lane_counter[lane] += 1
        store_counter[str(item.get("source_store") or "unknown")] += 1
        batch_counter[str(item.get("batch_id") or "unbatched")] += 1
        board_items.append(
            {
                "catalog_index": item.get("catalog_index", item.get("row_index")),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "affiliation": item.get("affiliation"),
                "category": item.get("category"),
                "source_store": item.get("source_store"),
                "review_lane": lane,
                "workflow": item.get("workflow"),
                "batch_id": item.get("batch_id"),
                "blocked_until": item.get("blocked_until"),
                "image_import_blockers": blockers,
                "review_url": _review_url(item),
                "candidate_image_url": item.get("candidate_image_url") or "",
                "manual_value": item.get("manual_value") or "",
                "evidence_url": item.get("evidence_url") or "",
                "suggested_local_image_path": item.get("suggested_local_image_path"),
                "manual_confirmation_requirements": item.get("manual_confirmation_requirements") or [],
            }
        )

    ready_now = lane_counter.get("image_url_review_ready", 0)
    representative = lane_counter.get("representative_image_candidate_review", 0)
    return {
        "schema_version": 1,
        "generated_at": generated_at or template.get("generated_at"),
        "scope": "catalog_image_attachment_review_board",
        "source_template": "data/catalog_image_attachment_confirmed_template_public.json",
        "summary": {
            "review_rows": len(board_items),
            "image_url_review_ready_rows": ready_now,
            "representative_image_review_rows": representative,
            "manual_confirmed_rows": sum(1 for item in items if item.get("manual_confirmed") is True),
            "manual_value_rows": sum(1 for item in items if str(item.get("manual_value") or "").strip()),
            "batch_count": len(batch_counter),
            "by_review_lane": lane_counter.most_common(),
            "by_source_store": store_counter.most_common(),
            "by_blocker": blocker_counter.most_common(),
            "gate_status": "blocked_until_manual_image_confirmation" if board_items else "no_image_review_rows",
        },
        "instructions": [
            "Open review_url and verify the exact product identity.",
            "Copy only an exact product image URL into manual_value.",
            "Set manual_confirmed=true in server/catalog_image_attachment_confirmed_rows.json only after verification.",
            "Dry-run tools/import_confirmed_image_attachment_rows.py before --write.",
        ],
        "items": board_items,
    }


def write_markdown(board: dict[str, Any], path: Path) -> None:
    summary = board["summary"]
    lines = [
        "# Catalog Image Attachment Review Board",
        "",
        f"- Review rows: `{summary['review_rows']}`",
        f"- Exact image URL review rows: `{summary['image_url_review_ready_rows']}`",
        f"- Representative image review rows: `{summary['representative_image_review_rows']}`",
        f"- Gate: `{summary['gate_status']}`",
        "",
        "## Next Commands",
        "",
        "`python tools/import_confirmed_image_attachment_rows.py --queue server/catalog_image_attachment_confirmed_rows.json --report server/catalog_image_attachment_confirmed_import_report.json`",
        "",
        "`python tools/import_confirmed_image_attachment_rows.py --queue server/catalog_image_attachment_confirmed_rows.json --report server/catalog_image_attachment_confirmed_import_report.json --write`",
        "",
        "## Items",
        "",
    ]
    for item in board["items"]:
        lines.extend(
            [
                f"### {item.get('catalog_index')} {item.get('name_ko')}",
                "",
                f"- Lane: `{item.get('review_lane')}`",
                f"- Store: `{item.get('source_store')}`",
                f"- Category: `{item.get('category')}`",
                f"- Blockers: `{', '.join(item.get('image_import_blockers') or [])}`",
                f"- Review URL: {item.get('review_url') or '(missing)'}",
                f"- Suggested local path: `{item.get('suggested_local_image_path')}`",
                "",
            ]
        )
    path.write_text(_strip_trailing_whitespace("\n".join(lines)), encoding="utf-8")


def write_html(board: dict[str, Any], path: Path) -> None:
    summary = board["summary"]
    cards = []
    for item in board["items"]:
        url = item.get("review_url") or ""
        link = f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">Open evidence</a>' if url else "<span>No URL</span>"
        blockers = ", ".join(item.get("image_import_blockers") or [])
        cards.append(
            f"""
            <article>
              <header>
                <span>{html.escape(str(item.get('review_lane')))}</span>
                <strong>{html.escape(str(item.get('catalog_index')))}</strong>
              </header>
              <h2>{html.escape(str(item.get('name_ko') or ''))}</h2>
              <p>{html.escape(str(item.get('name_ja') or ''))}</p>
              <dl>
                <dt>Store</dt><dd>{html.escape(str(item.get('source_store') or ''))}</dd>
                <dt>Category</dt><dd>{html.escape(str(item.get('category') or ''))}</dd>
                <dt>Blockers</dt><dd>{html.escape(blockers)}</dd>
                <dt>Local path</dt><dd>{html.escape(str(item.get('suggested_local_image_path') or ''))}</dd>
              </dl>
              {link}
            </article>
            """
        )
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Catalog Image Attachment Review Board</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #161719; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px; }}
    h1 {{ margin: 0 0 16px; font-size: 28px; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }}
    .stats div, article {{ background: #fff; border: 1px solid #e1e4e8; border-radius: 10px; padding: 16px; }}
    .stats span, dt, header span {{ color: #69707a; font-size: 12px; }}
    .stats strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    section {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    article header {{ display: flex; justify-content: space-between; gap: 12px; padding: 0; border: 0; }}
    article h2 {{ font-size: 16px; line-height: 1.35; margin: 12px 0 8px; }}
    article p {{ min-height: 38px; color: #4f5660; font-size: 13px; line-height: 1.4; }}
    dl {{ display: grid; grid-template-columns: 76px 1fr; gap: 6px 10px; font-size: 13px; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    a {{ display: inline-flex; margin-top: 10px; color: #275efe; text-decoration: none; font-weight: 700; }}
  </style>
</head>
<body>
<main>
  <h1>Catalog Image Attachment Review Board</h1>
  <div class="stats">
    <div><span>Review rows</span><strong>{html.escape(str(summary['review_rows']))}</strong></div>
    <div><span>Exact URL review</span><strong>{html.escape(str(summary['image_url_review_ready_rows']))}</strong></div>
    <div><span>Representative review</span><strong>{html.escape(str(summary['representative_image_review_rows']))}</strong></div>
    <div><span>Gate</span><strong>{html.escape(str(summary['gate_status']))}</strong></div>
  </div>
  <section>
    {''.join(cards)}
  </section>
</main>
</body>
</html>
"""
    path.write_text(_strip_trailing_whitespace(html_text), encoding="utf-8")


def _strip_trailing_whitespace(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()
    board = build_board(_load(args.template))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(board, args.markdown_output)
    write_html(board, args.html_output)
    print(json.dumps({**board["summary"], "json": str(args.json_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
