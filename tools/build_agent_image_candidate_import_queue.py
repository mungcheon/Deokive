from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from enrich_catalog_images import (
    _has_all_distinctive_token_matches,
    _has_goods_type_compatibility,
    _parenthetical_terms_match,
)
from image_enrichment_safety import is_safe_source_image_pair
from import_manual_image_candidates import _candidate_title_matches_row, import_candidates

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_OUTPUT = ROOT / "server" / "agent_image_candidates_import_queue.json"
DEFAULT_MARKDOWN = ROOT / "server" / "agent_image_candidates_import_queue.md"
DEFAULT_HTML = ROOT / "server" / "agent_image_candidates_import_queue.html"

GENERATED_REPORT_NAME_PARTS = (
    "_import_",
    "import_queue",
    "_dryrun",
    "_write",
    "_review",
    "_recheck",
)


def discover_candidate_files(globs: list[str], *, root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            if _is_generated_report(path):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def _is_generated_report(path: Path) -> bool:
    name = path.name.lower()
    return any(part in name for part in GENERATED_REPORT_NAME_PARTS)


def _items(payload: Any) -> list[dict[str, Any]]:
    raw_items = None
    if isinstance(payload, dict):
        raw_items = payload.get("items")
        if raw_items is None:
            raw_items = payload.get("candidates")
    else:
        raw_items = payload
    if not isinstance(raw_items, list):
        raise ValueError("candidate file must contain a JSON list or an object with items/candidates")
    return [item for item in raw_items if isinstance(item, dict)]


def _current_identity(item: dict[str, Any]) -> dict[str, Any]:
    current = item.get("current")
    if isinstance(current, dict):
        return current
    return item


def _confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().lower()
    if text == "high":
        return 0.95
    if text == "medium":
        return 0.8
    if text == "low":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _same_non_empty(left: Any, right: Any) -> bool:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    return bool(left_text and right_text and left_text == right_text)


def _clean_expected_text(value: Any) -> Any:
    text = str(value or "").strip()
    if not text:
        return None
    if "?" in text or "\ufffd" in text:
        return None
    return text


def normalize_candidate(item: dict[str, Any], *, source_file: str) -> dict[str, Any]:
    identity = _current_identity(item)
    return {
        "row_index": item.get("row_index"),
        "name_ko": identity.get("name_ko"),
        "name_ja": identity.get("name_ja"),
        "source_store": _clean_expected_text(identity.get("source_store")),
        "affiliation": _clean_expected_text(identity.get("affiliation")),
        "category": _clean_expected_text(identity.get("category")),
        "source_kind": item.get("source_kind") or "licensed_retailer_exact",
        "confidence": _confidence(item.get("confidence")),
        "source_url": item.get("source_url") or item.get("candidate_source_url"),
        "image_url": item.get("image_url") or item.get("candidate_image_url"),
        "candidate_title": item.get("candidate_title") or item.get("title") or "",
        "evidence_notes": item.get("evidence_notes"),
        "manual_confirmed": item.get("manual_confirmed"),
        "remap_reason": item.get("remap_reason"),
        "old_row_index": item.get("old_row_index"),
        "from_file": source_file,
    }


def _preflight(candidate: dict[str, Any], seed_rows: list[dict[str, Any]]) -> str | None:
    row_index = candidate.get("row_index")
    if isinstance(row_index, bool) or not isinstance(row_index, int):
        return "invalid_row_index"
    if row_index < 0 or row_index >= len(seed_rows):
        return "invalid_row_index"
    row = seed_rows[row_index]
    if row.get("image_url"):
        return "image_already_present"
    if not _same_non_empty(candidate.get("name_ko"), row.get("name_ko")) and not _same_non_empty(
        candidate.get("name_ja"), row.get("name_ja")
    ):
        return "current_name_mismatch"
    for field in ("source_store", "affiliation", "category"):
        expected = candidate.get(field)
        if expected not in (None, "") and row.get(field) != expected:
            return f"current_{field}_mismatch"
    if not candidate.get("source_url") or not candidate.get("image_url"):
        return "missing_source_or_image_url"
    if not is_safe_source_image_pair(candidate.get("source_url"), candidate.get("image_url")):
        return "unsafe_source_image_pair"
    if _requires_manual_confirmation(candidate):
        return "remapped_candidate_requires_manual_confirmation"
    if not _candidate_title_passes_strict_match(candidate, row):
        return "strict_candidate_title_mismatch"
    return None


def _requires_manual_confirmation(candidate: dict[str, Any]) -> bool:
    remap_reason = str(candidate.get("remap_reason") or "").strip()
    if not remap_reason:
        return False
    if candidate.get("manual_confirmed") is True:
        return False
    # Remapped candidate titles can be copied from the target row, so they are
    # not independent evidence that the source URL is the exact same product.
    return True


def _candidate_title_passes_strict_match(candidate: dict[str, Any], row: dict[str, Any]) -> bool:
    title = str(candidate.get("candidate_title") or "").strip()
    if not title:
        return False
    queries = [
        str(row.get(field) or "").strip()
        for field in ("name_ja", "name_ko")
        if str(row.get(field) or "").strip()
    ]
    if not queries:
        return False
    return _candidate_title_matches_row(candidate, row) and any(
        _has_goods_type_compatibility(query, title)
        and _has_all_distinctive_token_matches(query, title)
        and _parenthetical_terms_match(query, title)
        for query in queries
    )


def build_queue(
    seed_rows: list[dict[str, Any]],
    candidate_files: list[Path],
    *,
    min_confidence: float = 0.75,
    trust_manual_confirmed_title: bool = False,
    allow_existing_overwrite: bool = False,
    validate_live_title: bool = False,
    require_live_title_exact: bool = False,
) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for path in candidate_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            raw_items = _items(payload)
        except Exception as exc:
            rejected.append(
                {
                    "from_file": str(path),
                    "reason": "candidate_file_unreadable",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        for item in raw_items:
            candidate = normalize_candidate(item, source_file=str(path))
            reason = _preflight(candidate, seed_rows)
            if reason:
                rejected.append({**candidate, "reason": reason})
                continue
            normalized.append(candidate)

    result = import_candidates(
        [dict(row) for row in seed_rows],
        normalized,
        min_confidence=min_confidence,
        allow_existing_overwrite=allow_existing_overwrite,
        allow_source_store_change=False,
        validate_live_title=validate_live_title,
        require_live_title_exact=require_live_title_exact,
        trust_manual_confirmed_title=trust_manual_confirmed_title,
    )
    normalized_by_index: dict[int, dict[str, Any]] = {
        int(item["row_index"]): item
        for item in normalized
        if isinstance(item.get("row_index"), int) and not isinstance(item.get("row_index"), bool)
    }
    import_rejected = []
    for item in result["skipped"]:
        row_index = item.get("row_index")
        original = normalized_by_index.get(row_index) if isinstance(row_index, int) else None
        import_rejected.append(
            {
                **(original or {}),
                **item,
                "reason": item.get("reason") or "import_rejected",
            }
        )
    ready_indexes = {item["row_index"] for item in result["updated"]}
    ready = [item for item in normalized if item.get("row_index") in ready_indexes]
    all_rejected = rejected + import_rejected
    ready, duplicate_row_rejected = _reject_duplicate_ready_rows(ready)
    all_rejected.extend(duplicate_row_rejected)
    ready, duplicate_ready_rejected = _reject_duplicate_ready_sources(ready)
    all_rejected.extend(duplicate_ready_rejected)

    return {
        "instructions": [
            "Generated by tools/build_agent_image_candidate_import_queue.py.",
            "Import ready items with tools/import_manual_image_candidates.py after reviewing this report.",
            "Candidates rejected here should stay in review until the source/store/title mismatch is resolved.",
        ],
        "summary": {
            "candidate_files": len(candidate_files),
            "input_items": len(normalized) + len(rejected),
            "preflight_passed_items": len(normalized),
            "ready_items": len(ready),
            "rejected_items": len(all_rejected),
            "rejected_reasons": Counter(str(item.get("reason") or "") for item in all_rejected).most_common(),
            "allow_existing_overwrite": allow_existing_overwrite,
            "validate_live_title": validate_live_title,
            "require_live_title_exact": require_live_title_exact,
        },
        "items": ready,
        "rejected": all_rejected,
        "rejected_sample": all_rejected[:200],
    }


def _reject_duplicate_ready_rows(
    ready: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_rows: set[int] = set()
    for item in ready:
        row_index = item.get("row_index")
        if isinstance(row_index, int) and not isinstance(row_index, bool):
            if row_index in seen_rows:
                rejected.append({**item, "reason": "duplicate_ready_row_index"})
                continue
            seen_rows.add(row_index)
        kept.append(item)
    return kept, rejected


def _reject_duplicate_ready_sources(
    ready: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in ready:
        key = (str(item.get("source_url") or ""), str(item.get("image_url") or ""))
        by_key.setdefault(key, []).append(item)

    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in ready:
        key = (str(item.get("source_url") or ""), str(item.get("image_url") or ""))
        peers = by_key.get(key) or []
        peer_names = {
            str(peer.get("name_ko") or peer.get("name_ja") or "")
            for peer in peers
        }
        if len(peers) > 1 and len(peer_names) > 1:
            rejected.append(
                {
                    **item,
                    "reason": "duplicate_ready_source_image_pair",
                    "duplicate_ready_rows": [peer.get("row_index") for peer in peers],
                    "duplicate_ready_names": sorted(peer_names),
                }
            )
            continue
        kept.append(item)
    return kept, rejected


def _short(value: Any, limit: int = 96) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _md_link(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    return f"[{_short(text, 48)}]({text})"


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Agent Image Candidate Import Queue",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in ("candidate_files", "input_items", "preflight_passed_items", "ready_items", "rejected_items"):
        lines.append(f"| {key} | {summary.get(key, 0)} |")
    lines.extend(["", "## Rejected Reasons", "", "| Reason | Rows |", "| --- | ---: |"])
    for reason, rows in summary.get("rejected_reasons") or []:
        lines.append(f"| {reason} | {rows} |")
    if not summary.get("rejected_reasons"):
        lines.append("| none | 0 |")

    lines.extend(["", "## Ready Items", "", "| Row | Name | Store | Source | Image | Title |", "| ---: | --- | --- | --- | --- | --- |"])
    for item in report.get("items") or []:
        lines.append(
            "| {row} | {name} | {store} | {source} | {image} | {title} |".format(
                row=item.get("row_index"),
                name=_short(item.get("name_ko") or item.get("name_ja")),
                store=_short(item.get("source_store"), 32),
                source=_md_link(item.get("source_url")),
                image=_md_link(item.get("image_url")),
                title=_short(item.get("candidate_title")),
            )
        )
    if not report.get("items"):
        lines.append("| - | No ready import items | - | - | - | - |")

    lines.extend(["", "## Rejected Sample", "", "| Row | Reason | Name | Store | Source | File |", "| ---: | --- | --- | --- | --- | --- |"])
    for item in report.get("rejected_sample") or []:
        lines.append(
            "| {row} | {reason} | {name} | {store} | {source} | {file} |".format(
                row=item.get("row_index", ""),
                reason=_short(item.get("reason"), 48),
                name=_short(item.get("name_ko") or item.get("name_ja")),
                store=_short(item.get("source_store"), 32),
                source=_md_link(item.get("source_url")),
                file=_short(item.get("from_file"), 48),
            )
        )
    if not report.get("rejected_sample"):
        lines.append("| - | none | - | - | - | - |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary") or {}

    def esc(value: Any) -> str:
        return html.escape("" if value is None else str(value))

    def link(url: Any) -> str:
        text = str(url or "").strip()
        if not text:
            return ""
        safe = esc(text)
        return f'<a href="{safe}">{esc(_short(text, 48))}</a>'

    reason_rows = "".join(
        f"<tr><td>{esc(reason)}</td><td>{int(rows)}</td></tr>"
        for reason, rows in (summary.get("rejected_reasons") or [])
    ) or "<tr><td>none</td><td>0</td></tr>"
    ready_rows = "".join(
        "<tr>"
        f"<td>{esc(item.get('row_index'))}</td>"
        f"<td>{esc(_short(item.get('name_ko') or item.get('name_ja')))}</td>"
        f"<td>{esc(_short(item.get('source_store'), 32))}</td>"
        f"<td>{link(item.get('source_url'))}</td>"
        f"<td>{link(item.get('image_url'))}</td>"
        f"<td>{esc(_short(item.get('candidate_title')))}</td>"
        "</tr>"
        for item in (report.get("items") or [])
    ) or '<tr><td colspan="6">No ready import items</td></tr>'
    rejected_rows = "".join(
        "<tr>"
        f"<td>{esc(item.get('row_index', ''))}</td>"
        f"<td>{esc(_short(item.get('reason'), 48))}</td>"
        f"<td>{esc(_short(item.get('name_ko') or item.get('name_ja')))}</td>"
        f"<td>{esc(_short(item.get('source_store'), 32))}</td>"
        f"<td>{link(item.get('source_url'))}</td>"
        f"<td>{esc(_short(item.get('from_file'), 48))}</td>"
        "</tr>"
        for item in (report.get("rejected_sample") or [])
    ) or '<tr><td colspan="6">No rejected sample</td></tr>'
    cards = "".join(
        f"<article><span>{esc(key)}</span><strong>{esc(summary.get(key, 0))}</strong></article>"
        for key in ("candidate_files", "input_items", "preflight_passed_items", "ready_items", "rejected_items")
    )
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Image Candidate Import Queue</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #17181a; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ margin: 0 0 18px; font-size: 28px; }}
    h2 {{ margin-top: 28px; font-size: 18px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }}
    article {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
    article span {{ display: block; color: #69707a; font-size: 12px; }}
    article strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid #edf0f3; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #f0f2f5; color: #343840; }}
    a {{ color: #1558d6; text-decoration: none; }}
  </style>
</head>
<body>
<main>
  <h1>Agent Image Candidate Import Queue</h1>
  <section class="cards">{cards}</section>
  <h2>Rejected Reasons</h2>
  <table><thead><tr><th>Reason</th><th>Rows</th></tr></thead><tbody>{reason_rows}</tbody></table>
  <h2>Ready Items</h2>
  <table><thead><tr><th>Row</th><th>Name</th><th>Store</th><th>Source</th><th>Image</th><th>Title</th></tr></thead><tbody>{ready_rows}</tbody></table>
  <h2>Rejected Sample</h2>
  <table><thead><tr><th>Row</th><th>Reason</th><th>Name</th><th>Store</th><th>Source</th><th>File</th></tr></thead><tbody>{rejected_rows}</tbody></table>
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--candidate-file", type=Path, action="append", default=[])
    parser.add_argument(
        "--candidate-glob",
        action="append",
        default=[],
        help="Candidate file glob relative to the repository root. Can be repeated.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--trust-manual-confirmed-title", action="store_true")
    parser.add_argument("--allow-existing-overwrite", action="store_true")
    parser.add_argument("--validate-live-title", action="store_true")
    parser.add_argument("--require-live-title-exact", action="store_true")
    args = parser.parse_args()

    seed_rows = json.loads(args.seed.read_text(encoding="utf-8-sig"))
    if not isinstance(seed_rows, list):
        raise SystemExit(f"{args.seed} must contain a JSON list")
    candidate_files = [*args.candidate_file, *discover_candidate_files(args.candidate_glob)]
    if not candidate_files:
        raise SystemExit("At least one --candidate-file or --candidate-glob is required")
    report = build_queue(
        [row for row in seed_rows if isinstance(row, dict)],
        candidate_files,
        min_confidence=args.min_confidence,
        trust_manual_confirmed_title=args.trust_manual_confirmed_title,
        allow_existing_overwrite=args.allow_existing_overwrite,
        validate_live_title=args.validate_live_title,
        require_live_title_exact=args.require_live_title_exact,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.markdown_output)
    write_html(report, args.html_output)
    print(
        json.dumps(
            {
                **report["summary"],
                "output": str(args.output),
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
