from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_JSON = DATA / "ichiban_variant_lineup_review_public.json"
DEFAULT_CSV = DATA / "ichiban_variant_lineup_review_public.csv"
DEFAULT_MD = DATA / "ichiban_variant_lineup_review_public.md"
DEFAULT_HTML = DATA / "ichiban_variant_lineup_review_public.html"

ICHIBAN_PREFIX = "\u4e00\u756a\u304f\u3058"
GENERIC_CHARACTERS = {"\uae30\ud0c0", "\ud63c\ud569", ""}
LINEUP_MARKERS = (
    "\u30a2\u30bd\u30fc\u30c8",
    "\u30e9\u30a4\u30f3\u30ca\u30c3\u30d7",
    "\u30e9\u30f3\u30c0\u30e0",
    "\u9078\u3079\u308b",
    "\u9078\u3079\u306a\u3044",
)
COUNT_PATTERNS = (
    re.compile(r"\u5168\s*(\d+)\s*\u7a2e"),
    re.compile(r"(\d+)\s*\u7a2e"),
    re.compile(r"\((\d+)\s*/\s*(\d+)\)"),
    re.compile(r"\uff08(\d+)\s*/\s*(\d+)\uff09"),
)
FRACTION_PATTERNS = (
    re.compile(r"\((\d+)\s*/\s*(\d+)\)"),
    re.compile(r"\uff08(\d+)\s*/\s*(\d+)\uff09"),
)


def load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON list or an object with items")
    return [row for row in rows if isinstance(row, dict)]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _catalog_index(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 10**9


def _is_ichiban(row: dict[str, Any]) -> bool:
    return (
        _text(row.get("series_name")).startswith(ICHIBAN_PREFIX)
        or ICHIBAN_PREFIX in _text(row.get("name_ko"))
        or "1kuji.com/products/" in _text(row.get("source_url"))
    )


def _parts(row: dict[str, Any]) -> tuple[str, str, str, str]:
    name_parts = [part.strip() for part in _text(row.get("name_ko")).split(" / ")]
    campaign = name_parts[0] if len(name_parts) > 0 else _text(row.get("series_name"))
    prize = name_parts[1] if len(name_parts) > 1 else _text(row.get("sub_series"))
    product = name_parts[2] if len(name_parts) > 2 else _text(row.get("name_ja"))
    character = name_parts[3] if len(name_parts) > 3 else _text(row.get("character_name"))
    return campaign, prize, product, character


def _same_prize_key(row: dict[str, Any]) -> tuple[str, str]:
    return (_text(row.get("source_url")), _text(row.get("sub_series")))


def _expected_variant_count(text: str) -> int | None:
    best: int | None = None
    for pattern in COUNT_PATTERNS:
        for match in pattern.finditer(text):
            groups = [int(value) for value in match.groups() if value and value.isdigit()]
            if not groups:
                continue
            value = max(groups)
            if value > 1:
                best = max(best or 0, value)
    return best


def _variant_fraction(text: str) -> tuple[int, int] | None:
    for pattern in FRACTION_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        current, total = int(match.group(1)), int(match.group(2))
        if 1 <= current <= total and total > 1:
            return current, total
    return None


def _complete_numbered_fraction_group(siblings: list[dict[str, Any]], expected_count: int | None) -> bool:
    if expected_count is None:
        return False
    present: set[int] = set()
    for sibling in siblings:
        text = " ".join(_text(sibling.get(key)) for key in ("name_ko", "name_ja"))
        fraction = _variant_fraction(text)
        if fraction is None:
            continue
        current, total = fraction
        if total == expected_count:
            present.add(current)
    return len(present) == expected_count


def _lineup_markers(text: str) -> list[str]:
    markers = [marker for marker in LINEUP_MARKERS if marker in text]
    if "\u5168" in text and "\u7a2e" in text:
        markers.append("\u5168n\u7a2e")
    return markers


def _row_summary(row: dict[str, Any]) -> dict[str, Any]:
    campaign, prize, product, character = _parts(row)
    return {
        "catalog_index": row.get("catalog_index"),
        "campaign_name": campaign,
        "prize_rank": prize,
        "product_name": product,
        "display_character_name": character,
        "character_name": row.get("character_name"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "image_url": row.get("image_url"),
        "local_image_path": row.get("local_image_path"),
    }


def _classify(row: dict[str, Any], siblings: list[dict[str, Any]], expected_count: int | None) -> tuple[int, str, str]:
    non_generic_sibling_count = sum(
        1 for sibling in siblings if _text(sibling.get("character_name")) not in GENERIC_CHARACTERS
    )
    if expected_count and len(siblings) < expected_count:
        return (
            1,
            "expected_count_exceeds_rows",
            "Official-looking count marker exceeds current row count; verify variants and split into one row per item when confirmed.",
        )
    if _text(row.get("character_name")) in GENERIC_CHARACTERS:
        return (
            3,
            "generic_character_lineup_marker",
            "Lineup marker is attached to a generic character row; inspect official source for separate character/design variants.",
        )
    return (
        4,
        "lineup_marker_manual_review",
        "Lineup marker detected; no automatic DB change without source-confirmed variant names.",
    )


def build_review(rows: list[dict[str, Any]], *, catalog_path: Path | str = DEFAULT_CATALOG) -> dict[str, Any]:
    ichiban_rows = [row for row in rows if _is_ichiban(row)]
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in ichiban_rows:
        by_key[_same_prize_key(row)].append(row)

    review_rows: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()
    for row in ichiban_rows:
        full_text = " ".join(_text(row.get(key)) for key in ("name_ko", "name_ja"))
        markers = _lineup_markers(full_text)
        expected_count = _expected_variant_count(full_text)
        if not markers and expected_count is None:
            continue

        index = _catalog_index(row.get("catalog_index"))
        if index in seen_indexes:
            continue

        siblings = sorted(by_key.get(_same_prize_key(row), []), key=lambda item: _catalog_index(item.get("catalog_index")))
        if _complete_numbered_fraction_group(siblings, expected_count):
            continue
        seen_indexes.add(index)

        campaign, prize, product, character = _parts(row)
        priority, classification, action = _classify(row, siblings, expected_count)
        review_rows.append(
            {
                "priority": priority,
                "classification": classification,
                "catalog_index": row.get("catalog_index"),
                "campaign_name": campaign,
                "prize_rank": prize,
                "product_name": product,
                "display_character_name": character,
                "character_name": row.get("character_name"),
                "lineup_markers": markers,
                "expected_variant_count": expected_count,
                "same_prize_row_count": len(siblings),
                "named_variant_row_count": sum(
                    1 for sibling in siblings if _text(sibling.get("character_name")) not in GENERIC_CHARACTERS
                ),
                "same_prize_rows": [_row_summary(sibling) for sibling in siblings[:40]],
                "source_url": row.get("source_url"),
                "source_store": row.get("source_store"),
                "image_url": row.get("image_url"),
                "local_image_path": row.get("local_image_path"),
                "recommended_action": action,
            }
        )

    review_rows.sort(key=lambda item: (int(item.get("priority") or 99), _catalog_index(item.get("catalog_index"))))
    by_classification: dict[str, int] = {}
    for row in review_rows:
        key = _text(row.get("classification"))
        by_classification[key] = by_classification.get(key, 0) + 1

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "ichiban_variant_lineup_review",
        "catalog": str(catalog_path),
        "summary": {
            "ichiban_rows": len(ichiban_rows),
            "review_rows": len(review_rows),
            "by_classification": sorted(by_classification.items(), key=lambda item: (-item[1], item[0])),
            "safe_auto_split_rows": 0,
            "requires_official_source_review_rows": len(review_rows),
            "policy": "Lineup/count-marker rows require official source confirmation before creating variant rows.",
        },
        "review_rows": review_rows,
    }


def write_csv(report: dict[str, Any], path: Path) -> None:
    fields = [
        "priority",
        "classification",
        "catalog_index",
        "campaign_name",
        "prize_rank",
        "product_name",
        "display_character_name",
        "character_name",
        "lineup_markers",
        "expected_variant_count",
        "same_prize_row_count",
        "named_variant_row_count",
        "source_url",
        "recommended_action",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["review_rows"]:
            out = dict(row)
            out["lineup_markers"] = " | ".join(row.get("lineup_markers") or [])
            writer.writerow({field: out.get(field) for field in fields})


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Ichiban Variant Lineup Review",
        "",
        f"- Review rows: `{report['summary']['review_rows']}`",
        f"- Safe auto-split rows: `{report['summary']['safe_auto_split_rows']}`",
        f"- Requires official source review: `{report['summary']['requires_official_source_review_rows']}`",
        "",
        "## By Classification",
        "",
    ]
    for classification, count in report["summary"]["by_classification"]:
        lines.append(f"- `{classification}`: `{count}`")
    lines.extend(["", "## Review Rows", ""])
    for row in report["review_rows"]:
        lines.append(f"### P{row['priority']} {row['classification']} - #{row['catalog_index']}")
        lines.append(
            f"- Name: {row.get('campaign_name')} / {row.get('prize_rank')} / "
            f"{row.get('product_name')} / {row.get('display_character_name')}"
        )
        lines.append(f"- Markers: {', '.join(row.get('lineup_markers') or [])}")
        lines.append(f"- Expected variants: {row.get('expected_variant_count')}")
        lines.append(f"- Same prize rows: {row.get('same_prize_row_count')}")
        lines.append(f"- Named variant rows: {row.get('named_variant_row_count')}")
        lines.append(f"- Source: {row.get('source_url')}")
        lines.append(f"- Action: {row.get('recommended_action')}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _card(row: dict[str, Any]) -> str:
    siblings = "".join(
        f"<li>#{_escape(item.get('catalog_index'))} {_escape(item.get('name_ko'))}</li>"
        for item in row.get("same_prize_rows") or []
    )
    markers = ", ".join(row.get("lineup_markers") or [])
    image_url = _text(row.get("image_url"))
    image = (
        f'<img class="image" src="{_escape(image_url)}" alt="">'
        if image_url
        else '<div class="image empty">No image</div>'
    )
    haystack = " ".join(
        _text(row.get(key))
        for key in (
            "classification",
            "campaign_name",
            "prize_rank",
            "product_name",
            "display_character_name",
            "character_name",
            "source_url",
            "recommended_action",
        )
    ).lower()
    return f"""
      <article class="card" data-classification="{_escape(row.get('classification'))}" data-haystack="{_escape(haystack)}">
        <div class="top">
          {image}
          <div>
            <div class="meta"><span>P{_escape(row.get('priority'))}</span><span>{_escape(row.get('classification'))}</span><span>#{_escape(row.get('catalog_index'))}</span></div>
            <h2>{_escape(row.get('campaign_name'))}</h2>
            <p>{_escape(row.get('prize_rank'))} / {_escape(row.get('product_name'))} / {_escape(row.get('display_character_name'))}</p>
          </div>
        </div>
        <dl>
          <dt>markers</dt><dd>{_escape(markers)}</dd>
          <dt>expected</dt><dd>{_escape(row.get('expected_variant_count'))}</dd>
          <dt>same prize</dt><dd>{_escape(row.get('same_prize_row_count'))}</dd>
          <dt>named rows</dt><dd>{_escape(row.get('named_variant_row_count'))}</dd>
          <dt>action</dt><dd>{_escape(row.get('recommended_action'))}</dd>
        </dl>
        <details>
          <summary>Same prize rows</summary>
          <ul>{siblings}</ul>
        </details>
        <div class="actions"><a href="{_escape(row.get('source_url'))}" target="_blank" rel="noreferrer">Open source</a></div>
      </article>
    """


def write_html(report: dict[str, Any], path: Path) -> None:
    classifications = sorted(
        {str(row.get("classification") or "") for row in report.get("review_rows") or [] if row.get("classification")}
    )
    options = "\n".join(f'<option value="{_escape(value)}">{_escape(value)}</option>' for value in classifications)
    cards = "\n".join(_card(row) for row in report.get("review_rows") or [])
    path.write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ichiban Variant Lineup Review</title>
  <style>
    body {{ margin: 0; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f8fa; color: #171a20; }}
    header {{ position: sticky; top: 0; z-index: 2; padding: 18px 24px; background: rgba(255,255,255,.94); border-bottom: 1px solid #dde2ea; backdrop-filter: blur(12px); }}
    h1 {{ margin: 0 0 8px; font-size: 22px; }}
    .pills, .toolbar, .meta, .actions {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .pill, .meta span {{ padding: 4px 9px; border: 1px solid #d8dde5; border-radius: 999px; background: #fff; color: #596273; }}
    main {{ max-width: 1180px; margin: auto; padding: 22px; }}
    .toolbar {{ margin-bottom: 18px; }}
    input, select {{ font: inherit; border: 1px solid #d8dde5; border-radius: 8px; background: #fff; color: #15171c; padding: 9px 10px; }}
    .toolbar input {{ min-width: min(420px, 100%); flex: 1; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; }}
    .card {{ padding: 14px; background: #fff; border: 1px solid #dfe3ea; border-radius: 10px; box-shadow: 0 4px 18px rgba(20,28,40,.05); }}
    .top {{ display: grid; grid-template-columns: 96px 1fr; gap: 12px; }}
    .image {{ width: 96px; height: 96px; object-fit: contain; border-radius: 8px; background: #f0f2f5; border: 1px solid #eceff4; }}
    .empty {{ display: grid; place-items: center; color: #7b8494; text-align: center; }}
    h2 {{ margin: 8px 0 4px; font-size: 16px; }}
    p {{ margin: 5px 0; color: #454c59; }}
    dl {{ display: grid; grid-template-columns: 92px 1fr; gap: 2px 8px; margin: 10px 0; }}
    dt {{ color: #6b7280; }}
    dd {{ margin: 0; }}
    details {{ border-top: 1px solid #eef1f5; padding-top: 8px; margin-top: 8px; }}
    summary {{ cursor: pointer; font-weight: 650; }}
    li {{ margin: 4px 0; word-break: break-word; }}
    a {{ color: #0b57d0; word-break: break-all; }}
  </style>
</head>
<body>
  <header>
    <h1>Ichiban Variant Lineup Review</h1>
    <div class="pills">
      <span class="pill">review rows: {_escape(report['summary']['review_rows'])}</span>
      <span class="pill">safe auto split: {_escape(report['summary']['safe_auto_split_rows'])}</span>
      <span class="pill">source review required: {_escape(report['summary']['requires_official_source_review_rows'])}</span>
    </div>
  </header>
  <main>
    <div class="toolbar">
      <input id="search" placeholder="Search campaign, prize, product, character">
      <select id="classificationFilter">
        <option value="">All classifications</option>
        {options}
      </select>
    </div>
    <div class="grid">{cards}</div>
  </main>
  <script>
    const search = document.querySelector('#search');
    const classificationFilter = document.querySelector('#classificationFilter');
    const cards = [...document.querySelectorAll('.card')];
    function applyFilters() {{
      const q = (search.value || '').trim().toLowerCase();
      const classification = classificationFilter.value;
      for (const card of cards) {{
        const classificationOk = !classification || card.dataset.classification === classification;
        const queryOk = !q || (card.dataset.haystack || '').includes(q);
        card.style.display = classificationOk && queryOk ? '' : 'none';
      }}
    }}
    search.addEventListener('input', applyFilters);
    classificationFilter.addEventListener('change', applyFilters);
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    report = build_review(load_catalog(args.catalog), catalog_path=args.catalog)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(report, args.csv_output)
    write_markdown(report, args.markdown_output)
    write_html(report, args.html_output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
