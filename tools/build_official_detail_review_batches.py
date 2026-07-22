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
DEFAULT_INPUTS = (
    ROOT / "server" / "official_detail_match_queue_animate_after_query_fix_merged_summary.json",
    ROOT / "server" / "official_detail_match_queue_ensky_merged_current.json",
)
DEFAULT_JSON = ROOT / "server" / "official_detail_review_batches.json"
DEFAULT_CSV = ROOT / "server" / "official_detail_review_batches.csv"
DEFAULT_MD = ROOT / "server" / "official_detail_review_batches.md"
DEFAULT_HTML = ROOT / "server" / "official_detail_review_batches.html"
DEFAULT_TEMPLATE = ROOT / "server" / "official_detail_match_confirmed_rows.current.template.json"
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"

REVIEWABLE_STATUSES = {"strong_review_candidate", "needs_manual_title_review", "weak_or_ambiguous"}


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        source_rows = payload.get("reviewable")
        if source_rows is None:
            source_rows = payload.get("rows") or []
        for row in source_rows:
            if not isinstance(row, dict):
                continue
            if row.get("review_status") not in REVIEWABLE_STATUSES:
                continue
            key = (
                row.get("source_store"),
                row.get("name_ko"),
                row.get("name_ja"),
                row.get("category"),
                row.get("candidate_source_url"),
                row.get("candidate_image_url"),
            )
            if key in seen:
                continue
            seen.add(key)
            item = dict(row)
            item["_source_file"] = _display_path(path)
            rows.append(item)
    return rows


def _row_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("source_store"),
        row.get("name_ko"),
        row.get("name_ja"),
        row.get("category"),
        row.get("affiliation"),
    )


def _seed_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("source_store"),
        row.get("name_ko"),
        row.get("name_ja"),
        row.get("category"),
        row.get("affiliation"),
    )


def _completed_seed_keys(seed_path: Path) -> set[tuple[Any, ...]]:
    if not seed_path.exists():
        return set()
    rows = json.loads(seed_path.read_text(encoding="utf-8-sig"))
    completed: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("source_url") and row.get("image_url"):
            completed.add(_seed_key(row))
    return completed


def _seed_index_by_key(seed_path: Path) -> dict[tuple[Any, ...], int]:
    if not seed_path.exists():
        return {}
    rows = json.loads(seed_path.read_text(encoding="utf-8-sig"))
    buckets: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        buckets[_seed_key(row)].append(index)
    return {key: indexes[0] for key, indexes in buckets.items() if len(indexes) == 1}


def _priority(candidate_count: int, status_counts: Counter[str], top_overlap: int, top_similarity: float) -> int:
    if status_counts.get("strong_review_candidate"):
        return 1
    if candidate_count <= 2 and top_overlap >= 3 and top_similarity >= 0.95:
        return 2
    if candidate_count <= 5 and top_overlap >= 3 and top_similarity >= 0.95:
        return 3
    if candidate_count <= 5:
        return 4
    if top_overlap >= 3 and top_similarity >= 0.95:
        return 5
    return 6


def _workflow(priority: int) -> str:
    return {
        1: "confirm_strong_exact_candidate",
        2: "quick_disambiguation_two_candidates",
        3: "quick_disambiguation_small_set",
        4: "manual_small_set_review",
        5: "title_variant_review",
        6: "broad_manual_review",
    }[priority]


def _counter_rows(counter: Counter[str]) -> list[list[Any]]:
    return [[key, value] for key, value in counter.most_common()]


def build_batches(
    rows: list[dict[str, Any]],
    completed_keys: set[tuple[Any, ...]] | None = None,
    seed_index_by_key: dict[tuple[Any, ...], int] | None = None,
) -> dict[str, Any]:
    completed_keys = completed_keys or set()
    seed_index_by_key = seed_index_by_key or {}
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _row_key(row) in completed_keys:
            continue
        grouped[_row_key(row)].append(row)

    items: list[dict[str, Any]] = []
    for key, candidates in grouped.items():
        candidates.sort(
            key=lambda row: (
                row.get("rank") or 999,
                -(row.get("token_overlap") or 0),
                -(row.get("similarity") or 0),
                row.get("candidate_title") or "",
            )
        )
        status_counts = Counter(str(row.get("review_status") or "") for row in candidates)
        top = candidates[0]
        top_overlap = int(top.get("token_overlap") or 0)
        top_similarity = float(top.get("similarity") or 0)
        priority = _priority(len(candidates), status_counts, top_overlap, top_similarity)
        source_store, name_ko, name_ja, category, affiliation = key
        items.append(
            {
                "row_index": seed_index_by_key.get(key),
                "priority": priority,
                "workflow": _workflow(priority),
                "source_store": source_store,
                "affiliation": affiliation,
                "category": category,
                "name_ko": name_ko,
                "name_ja": name_ja,
                "candidate_count": len(candidates),
                "status_counts": status_counts,
                "top_candidate_title": top.get("candidate_title"),
                "top_candidate_source_url": top.get("candidate_source_url"),
                "top_candidate_image_url": top.get("candidate_image_url"),
                "top_token_overlap": top_overlap,
                "top_similarity": top_similarity,
                "candidates": [
                    {
                        "rank": row.get("rank"),
                        "review_status": row.get("review_status"),
                        "candidate_title": row.get("candidate_title"),
                        "candidate_source_url": row.get("candidate_source_url"),
                        "candidate_image_url": row.get("candidate_image_url"),
                        "token_overlap": row.get("token_overlap"),
                        "similarity": row.get("similarity"),
                        "source_file": row.get("_source_file"),
                    }
                    for row in candidates[:8]
                ],
            }
        )

    items.sort(
        key=lambda item: (
            item["priority"],
            item["candidate_count"],
            -item["top_token_overlap"],
            -item["top_similarity"],
            item["source_store"] or "",
            item["name_ko"] or "",
        )
    )
    reviewable_candidate_rows = sum(int(item.get("candidate_count") or 0) for item in items)
    by_priority = Counter(str(item["priority"]) for item in items)
    by_workflow = Counter(item["workflow"] for item in items)
    by_store = Counter(str(item["source_store"] or "") for item in items)
    summary = {
        "reviewable_seed_rows": len(items),
        "reviewable_candidate_rows": reviewable_candidate_rows,
        "completed_seed_rows_excluded": len(completed_keys),
        "by_priority": _counter_rows(by_priority),
        "by_workflow": _counter_rows(by_workflow),
        "by_store": _counter_rows(by_store),
        "manual_confirmed_true": 0,
        "auto_apply_enabled": False,
    }
    return {
        "schema_version": 1,
        "source_files": [str(path.relative_to(ROOT)) for path in DEFAULT_INPUTS if path.exists()],
        "summary": summary,
        "completed_seed_rows_excluded": len(completed_keys),
        "reviewable_seed_rows": len(items),
        "reviewable_candidate_rows": reviewable_candidate_rows,
        "by_priority": by_priority,
        "by_workflow": by_workflow,
        "by_store": by_store,
        "manual_confirmed_true": 0,
        "auto_apply_enabled": False,
        "items": items,
    }


def _write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    fields = [
        "priority",
        "row_index",
        "workflow",
        "source_store",
        "affiliation",
        "category",
        "name_ko",
        "name_ja",
        "candidate_count",
        "top_token_overlap",
        "top_similarity",
        "top_candidate_title",
        "top_candidate_source_url",
        "top_candidate_image_url",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({field: item.get(field) for field in fields})


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Official Detail Review Batches",
        "",
        f"- Reviewable seed rows: `{payload['reviewable_seed_rows']}`",
        f"- Reviewable candidate rows: `{payload['reviewable_candidate_rows']}`",
        "",
        "## By Workflow",
    ]
    for workflow, count in payload["by_workflow"].most_common():
        lines.append(f"- `{workflow}`: `{count}`")
    lines.extend(["", "## Top Batches"])
    for item in payload["items"][:80]:
        lines.append(
            f"- P{item['priority']} row `{item.get('row_index')}` `{item['workflow']}` / `{item['source_store']}` / "
            f"`{item['name_ko']}`: `{item['candidate_count']}` candidates, "
            f"top `{item['top_candidate_title']}`"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_html(path: Path, payload: dict[str, Any]) -> None:
    cards = []
    for item in payload["items"]:
        candidates = []
        for candidate in item["candidates"]:
            title = html.escape(str(candidate.get("candidate_title") or ""))
            source_url = html.escape(str(candidate.get("candidate_source_url") or ""))
            image_url = html.escape(str(candidate.get("candidate_image_url") or ""))
            candidates.append(
                f"<li><a href=\"{source_url}\">{title}</a>"
                f"<small> overlap {candidate.get('token_overlap')} / sim {candidate.get('similarity')} / "
                f"{html.escape(str(candidate.get('review_status') or ''))}</small>"
                f"<img src=\"{image_url}\" loading=\"lazy\" alt=\"\"></li>"
            )
        cards.append(
            "<article>"
            f"<h2>P{item['priority']} row {html.escape(str(item.get('row_index')))} {html.escape(str(item['name_ko'] or ''))}</h2>"
            f"<p>{html.escape(str(item['source_store'] or ''))} · {html.escape(str(item['category'] or ''))} · "
            f"{html.escape(str(item['workflow']))} · {item['candidate_count']} candidates</p>"
            f"<p><strong>{html.escape(str(item.get('name_ja') or ''))}</strong></p>"
            f"<ol>{''.join(candidates)}</ol>"
            "</article>"
        )
    document = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Official Detail Review Batches</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f6f7f9; color: #17181c; }}
header {{ margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; }}
article {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
h1, h2, p {{ margin: 0 0 8px; }}
h2 {{ font-size: 16px; }}
ol {{ padding-left: 20px; }}
li {{ margin: 10px 0; }}
small {{ display: block; color: #667085; margin-top: 2px; }}
img {{ display: block; width: 72px; height: 72px; object-fit: cover; border-radius: 6px; margin-top: 6px; border: 1px solid #eee; }}
a {{ color: #1a5fb4; }}
</style>
</head>
<body>
<header>
<h1>Official Detail Review Batches</h1>
<p>{payload['reviewable_seed_rows']} seed rows · {payload['reviewable_candidate_rows']} candidates</p>
</header>
<main class="grid">{''.join(cards)}</main>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def _template_item(item: dict[str, Any]) -> dict[str, Any]:
    top = item.get("candidates", [{}])[0] if item.get("candidates") else {}
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "source_store": item.get("source_store"),
        "row_index": item.get("row_index"),
        "source_queue_index": None,
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "affiliation": item.get("affiliation"),
        "candidate_title": top.get("candidate_title") or item.get("top_candidate_title"),
        "candidate_source_url": top.get("candidate_source_url") or item.get("top_candidate_source_url"),
        "candidate_image_url": top.get("candidate_image_url") or item.get("top_candidate_image_url"),
        "manual_barcode": "",
        "manual_release_date": "",
        "manual_official_price_jpy": "",
        "review_status": top.get("review_status"),
        "manual_review_reason": "confirm_exact_variant_or_representative_before_write",
        "broad_seed_row": True,
        "candidate_count": item.get("candidate_count"),
        "candidate_extra_tokens": [],
        "token_overlap": top.get("token_overlap") or item.get("top_token_overlap"),
        "similarity": top.get("similarity") or item.get("top_similarity"),
    }


def _write_template(path: Path, payload: dict[str, Any]) -> None:
    items = [_template_item(item) for item in payload.get("items") or []]
    template = {
        "instructions": (
            "Copy to official_detail_match_confirmed_rows.json, set manual_confirmed=true only after "
            "checking the candidate is the exact product/variant/representative row, then run "
            "tools/import_confirmed_official_detail_matches.py --write."
        ),
        "reviewable_items": len(items),
        "manual_confirmed_true": 0,
        "items": items,
    }
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", default=None)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--include-completed", action="store_true")
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--template-output", type=Path, default=DEFAULT_TEMPLATE)
    args = parser.parse_args()

    input_paths = args.input or list(DEFAULT_INPUTS)
    rows = _load_rows(input_paths)
    completed_keys = set() if args.include_completed else _completed_seed_keys(args.seed)
    seed_indexes = _seed_index_by_key(args.seed)
    payload = build_batches(rows, completed_keys, seed_indexes)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_csv(args.csv_output, payload["items"])
    _write_markdown(args.markdown_output, payload)
    _write_html(args.html_output, payload)
    _write_template(args.template_output, payload)
    print(
        json.dumps(
            {
                "reviewable_seed_rows": payload["reviewable_seed_rows"],
                "reviewable_candidate_rows": payload["reviewable_candidate_rows"],
                "completed_seed_rows_excluded": payload["completed_seed_rows_excluded"],
                "by_workflow": payload["by_workflow"].most_common(),
                "json": str(args.json_output),
                "csv": str(args.csv_output),
                "markdown": str(args.markdown_output),
                "html": str(args.html_output),
                "template": str(args.template_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
