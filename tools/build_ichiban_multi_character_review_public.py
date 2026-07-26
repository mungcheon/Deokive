from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_POLICY = ROOT / "data" / "catalog_character_name_policy_public.json"
DEFAULT_JSON = ROOT / "data" / "ichiban_multi_character_review_public.json"
DEFAULT_CSV = ROOT / "data" / "ichiban_multi_character_review_public.csv"
DEFAULT_MD = ROOT / "data" / "ichiban_multi_character_review_public.md"
DEFAULT_HTML = ROOT / "data" / "ichiban_multi_character_review_public.html"

ICHIBAN_PREFIX = "\u4e00\u756a\u304f\u3058"
MIXED_CHARACTER_NAMES = {"\ud63c\ud569", "\uae30\ud0c0", ""}
COMBINED_MARKERS = ("&", "\uff06", "\u00d7", "VS", "vs", "\u30fb", "\u30fb")
COUNT_MARKERS = ("\u5168", "\u7a2e", "\u30a2\u30bd\u30fc\u30c8", "\u30e9\u30a4\u30f3\u30ca\u30c3\u30d7")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON list or an object with items")
    return [row for row in rows if isinstance(row, dict)]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _parts(name_ko: Any) -> list[str]:
    return [part.strip() for part in _text(name_ko).split(" / ")]


def _catalog_index(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_ichiban(row: dict[str, Any]) -> bool:
    return _text(row.get("series_name")).startswith(ICHIBAN_PREFIX) or ICHIBAN_PREFIX in _text(row.get("name_ko"))


def _same_prize_key(row: dict[str, Any]) -> tuple[str, str]:
    return (_text(row.get("source_url")), _text(row.get("sub_series")))


def _row_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "character_name": row.get("character_name"),
        "category": row.get("category"),
        "image_url": row.get("image_url"),
        "local_image_path": row.get("local_image_path"),
    }


def _classification(candidate: dict[str, Any], sibling_rows: list[dict[str, Any]]) -> tuple[int, str, str]:
    product_name = _text(candidate.get("product_name"))
    character_name = _text(candidate.get("character_name"))
    matched = candidate.get("matched_characters") or []
    sibling_characters = {
        _text(row.get("character_name"))
        for row in sibling_rows
        if _text(row.get("character_name")) not in MIXED_CHARACTER_NAMES
    }

    has_combined_marker = any(marker in product_name for marker in COMBINED_MARKERS)
    has_count_marker = any(marker in product_name for marker in COUNT_MARKERS)
    has_individual_siblings = bool(set(map(str, matched)) & sibling_characters)

    if has_individual_siblings:
        return (
            1,
            "split_context_review",
            "Same prize already has individual character rows; verify whether this mixed row is duplicate or should be split.",
        )
    if character_name not in MIXED_CHARACTER_NAMES:
        return (
            2,
            "character_field_mismatch_review",
            "Product name contains multiple characters but character_name is not mixed; verify the exact character assignment.",
        )
    if has_count_marker and not has_combined_marker:
        return (
            3,
            "variant_split_review",
            "Product name looks like a multi-variant lineup; split only after official source confirms each character variant.",
        )
    if has_combined_marker:
        return (
            4,
            "likely_combined_goods",
            "Product name uses a pair/team marker; keep as one mixed row unless official source lists separate prizes.",
        )
    return (
        5,
        "manual_multi_character_review",
        "Multiple character tokens were detected; inspect official source before changing row count.",
    )


def build_review(
    catalog_rows: list[dict[str, Any]],
    policy_report: dict[str, Any],
    *,
    catalog_path: Path | str = DEFAULT_CATALOG,
    policy_path: Path | str = DEFAULT_POLICY,
) -> dict[str, Any]:
    by_index: dict[int, dict[str, Any]] = {}
    by_prize_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in catalog_rows:
        index = _catalog_index(row.get("catalog_index"))
        if index is not None:
            by_index[index] = row
        if _is_ichiban(row):
            by_prize_key.setdefault(_same_prize_key(row), []).append(row)

    review_rows: list[dict[str, Any]] = []
    for candidate in policy_report.get("ichiban_multi_character_product_review_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        index = _catalog_index(candidate.get("catalog_index"))
        catalog_row = by_index.get(index) if index is not None else None
        if catalog_row is None:
            review_rows.append(
                {
                    "priority": 99,
                    "classification": "catalog_index_not_found",
                    "catalog_index": candidate.get("catalog_index"),
                    "recommended_action": "Rebuild character policy report because the catalog index is stale.",
                    "candidate": candidate,
                }
            )
            continue

        parts = _parts(catalog_row.get("name_ko"))
        campaign_name = parts[0] if len(parts) > 0 else _text(catalog_row.get("series_name"))
        prize_rank = parts[1] if len(parts) > 1 else _text(catalog_row.get("sub_series"))
        product_name = parts[2] if len(parts) > 2 else _text(candidate.get("product_name"))
        display_character_name = parts[3] if len(parts) > 3 else _text(catalog_row.get("character_name"))
        sibling_rows = by_prize_key.get(_same_prize_key(catalog_row), [])
        priority, classification, action = _classification(candidate, sibling_rows)
        matched_characters = [str(value) for value in candidate.get("matched_characters") or []]
        split_name_templates = [
            f"{campaign_name} / {prize_rank} / {product_name} / {character}"
            for character in matched_characters
        ]

        review_rows.append(
            {
                "priority": priority,
                "classification": classification,
                "catalog_index": index,
                "campaign_name": campaign_name,
                "prize_rank": prize_rank,
                "product_name": product_name,
                "display_character_name": display_character_name,
                "character_name": catalog_row.get("character_name"),
                "matched_characters": matched_characters,
                "matched_tokens": candidate.get("matched_tokens") or [],
                "source_url": catalog_row.get("source_url"),
                "source_store": catalog_row.get("source_store"),
                "image_url": catalog_row.get("image_url"),
                "local_image_path": catalog_row.get("local_image_path"),
                "same_prize_row_count": len(sibling_rows),
                "same_prize_rows": [_row_summary(row) for row in sibling_rows[:24]],
                "split_name_templates": split_name_templates,
                "recommended_action": action,
            }
        )

    review_rows.sort(key=lambda row: (int(row.get("priority") or 99), int(row.get("catalog_index") or 10**9)))
    by_classification: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for row in review_rows:
        key = _text(row.get("classification"))
        by_classification[key] = by_classification.get(key, 0) + 1
        priority_key = str(row.get("priority"))
        by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "ichiban_multi_character_split_review",
        "catalog": str(catalog_path),
        "policy_report": str(policy_path),
        "summary": {
            "review_rows": len(review_rows),
            "by_classification": sorted(by_classification.items(), key=lambda item: (-item[1], item[0])),
            "by_priority": sorted(by_priority.items(), key=lambda item: (int(item[0]), item[0])),
            "safe_auto_split_rows": 0,
            "requires_official_source_review_rows": len(review_rows),
            "policy": "Never auto-split multi-character Ichiban rows without official source evidence.",
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
        "matched_characters",
        "same_prize_row_count",
        "source_url",
        "image_url",
        "recommended_action",
        "split_name_templates",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["review_rows"]:
            out = dict(row)
            out["matched_characters"] = " | ".join(row.get("matched_characters") or [])
            out["split_name_templates"] = "\n".join(row.get("split_name_templates") or [])
            writer.writerow({field: out.get(field) for field in fields})


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Ichiban Multi-Character Review",
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
    lines.extend(["", "## Priority Rows", ""])
    for row in report["review_rows"]:
        lines.append(f"### P{row['priority']} {row['classification']} - #{row['catalog_index']}")
        lines.append(f"- Name: {row.get('campaign_name')} / {row.get('prize_rank')} / {row.get('product_name')} / {row.get('display_character_name')}")
        lines.append(f"- Characters: {', '.join(row.get('matched_characters') or [])}")
        lines.append(f"- Same prize rows: {row.get('same_prize_row_count')}")
        lines.append(f"- Source: {row.get('source_url')}")
        lines.append(f"- Action: {row.get('recommended_action')}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _image(row: dict[str, Any]) -> str:
    url = _text(row.get("image_url"))
    if not url:
        return '<div class="image empty">No image</div>'
    return f'<img class="image" src="{_escape(url)}" alt="">'


def _card(row: dict[str, Any]) -> str:
    templates = "".join(f"<li>{_escape(item)}</li>" for item in row.get("split_name_templates") or [])
    siblings = "".join(
        f"<li>#{_escape(item.get('catalog_index'))} {_escape(item.get('name_ko'))}</li>"
        for item in row.get("same_prize_rows") or []
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
          {_image(row)}
          <div>
            <div class="meta"><span>P{_escape(row.get('priority'))}</span><span>{_escape(row.get('classification'))}</span><span>#{_escape(row.get('catalog_index'))}</span></div>
            <h2>{_escape(row.get('campaign_name'))}</h2>
            <p>{_escape(row.get('prize_rank'))} / {_escape(row.get('product_name'))} / {_escape(row.get('display_character_name'))}</p>
          </div>
        </div>
        <dl>
          <dt>matched</dt><dd>{_escape(', '.join(row.get('matched_characters') or []))}</dd>
          <dt>field</dt><dd>{_escape(row.get('character_name'))}</dd>
          <dt>same prize</dt><dd>{_escape(row.get('same_prize_row_count'))} rows</dd>
          <dt>action</dt><dd>{_escape(row.get('recommended_action'))}</dd>
        </dl>
        <details>
          <summary>Split name templates</summary>
          <ul>{templates}</ul>
        </details>
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
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ichiban Multi-Character Review</title>
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
    dl {{ display: grid; grid-template-columns: 84px 1fr; gap: 2px 8px; margin: 10px 0; }}
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
    <h1>Ichiban Multi-Character Review</h1>
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
"""
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    catalog_rows = load_catalog(args.catalog)
    policy_report = load_json(args.policy)
    if not isinstance(policy_report, dict):
        raise SystemExit(f"{args.policy} must contain a JSON object")

    report = build_review(catalog_rows, policy_report, catalog_path=args.catalog, policy_path=args.policy)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(report, args.csv_output)
    write_markdown(report, args.markdown_output)
    write_html(report, args.html_output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
