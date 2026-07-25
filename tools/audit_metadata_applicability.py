from __future__ import annotations

import argparse
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
DEFAULT_QUEUE = SERVER / "catalog_field_enrichment_queue_current.json"
DEFAULT_JSON = SERVER / "catalog_metadata_applicability_audit_current.json"
DEFAULT_MD = SERVER / "catalog_metadata_applicability_audit_current.md"
METADATA_FIELDS = ("release_date", "official_price_jpy")


def _load_queue(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("queue") or payload.get("items") or payload.get("rows") or []
    if not isinstance(items, list):
        raise SystemExit(f"{path} must contain a queue/items/rows list")
    return [item for item in items if isinstance(item, dict)]


def _top(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"value": value, "rows": count} for value, count in counter.most_common(limit)]


def _top_pair(counter: Counter[tuple[str, str]], first: str, second: str, limit: int) -> list[dict[str, Any]]:
    return [{first: a, second: b, "rows": count} for (a, b), count in counter.most_common(limit)]


def _field_summary(items: list[dict[str, Any]], field: str) -> dict[str, Any]:
    field_items = [item for item in items if item.get("field") == field]
    actionable = [item for item in field_items if item.get("actionable_now")]
    non_actionable = [item for item in field_items if not item.get("actionable_now")]
    automation = [item for item in field_items if item.get("automation_candidate")]
    by_applicability = Counter(str(item.get("applicability") or "") for item in field_items)
    by_source_group = Counter(str(item.get("source_group") or "") for item in field_items)
    by_workstream = Counter(str(item.get("workstream") or "") for item in field_items)
    by_store = Counter(str(item.get("source_store") or "") for item in field_items)
    actionable_by_store = Counter(str(item.get("source_store") or "") for item in actionable)
    automation_by_store = Counter(str(item.get("source_store") or "") for item in automation)
    automation_store_category = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or "")) for item in automation
    )
    blocked_remap = [item for item in field_items if item.get("applicability") == "needs_source_url_remap"]
    archived = [item for item in field_items if item.get("applicability") == "unavailable_archived"]
    currency_na = [item for item in field_items if item.get("applicability") == "not_applicable_currency"]
    return {
        "field": field,
        "missing_rows": len(field_items),
        "actionable_rows": len(actionable),
        "non_actionable_rows": len(non_actionable),
        "automation_candidate_rows": len(automation),
        "needs_source_url_remap_rows": len(blocked_remap),
        "unavailable_archived_rows": len(archived),
        "not_applicable_currency_rows": len(currency_na),
        "by_applicability": _top(by_applicability, 40),
        "by_source_group": _top(by_source_group, 40),
        "by_workstream": _top(by_workstream, 40),
        "top_source_stores": _top(by_store, 40),
        "actionable_top_source_stores": _top(actionable_by_store, 40),
        "automation_top_source_stores": _top(automation_by_store, 40),
        "automation_top_store_categories": _top_pair(automation_store_category, "source_store", "category", 80),
    }


def build_audit(items: list[dict[str, Any]], source: Path | None = None) -> dict[str, Any]:
    fields = {field: _field_summary(items, field) for field in METADATA_FIELDS}
    return {
        "source": str(source or DEFAULT_QUEUE),
        "fields": fields,
        "metadata_missing_rows": sum(summary["missing_rows"] for summary in fields.values()),
        "metadata_actionable_rows": sum(summary["actionable_rows"] for summary in fields.values()),
        "metadata_automation_candidate_rows": sum(summary["automation_candidate_rows"] for summary in fields.values()),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog Metadata Applicability Audit",
        "",
        f"- Source: `{payload['source']}`",
        f"- Metadata missing rows: `{payload['metadata_missing_rows']}`",
        f"- Metadata actionable rows: `{payload['metadata_actionable_rows']}`",
        f"- Metadata automation candidate rows: `{payload['metadata_automation_candidate_rows']}`",
    ]
    for field, summary in payload["fields"].items():
        lines.extend(
            [
                "",
                f"## {field}",
                "",
                f"- Missing rows: `{summary['missing_rows']}`",
                f"- Actionable rows: `{summary['actionable_rows']}`",
                f"- Non-actionable rows: `{summary['non_actionable_rows']}`",
                f"- Automation candidate rows: `{summary['automation_candidate_rows']}`",
                f"- Needs source URL remap rows: `{summary['needs_source_url_remap_rows']}`",
                f"- Unavailable archived rows: `{summary['unavailable_archived_rows']}`",
                f"- Not applicable currency rows: `{summary['not_applicable_currency_rows']}`",
                "",
                "### By Applicability",
            ]
        )
        for item in summary["by_applicability"]:
            lines.append(f"- `{item['value']}`: `{item['rows']}`")
        lines.extend(["", "### Automation Candidate Stores"])
        for item in summary["automation_top_source_stores"][:30]:
            lines.append(f"- `{item['value']}`: `{item['rows']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_audit(_load_queue(args.queue), source=args.queue)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                "release_date": payload["fields"]["release_date"],
                "official_price_jpy": payload["fields"]["official_price_jpy"],
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
