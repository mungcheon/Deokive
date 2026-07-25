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
DEFAULT_JSON = SERVER / "catalog_barcode_applicability_audit_current.json"
DEFAULT_MD = SERVER / "catalog_barcode_applicability_audit_current.md"


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


def build_audit(items: list[dict[str, Any]], source: Path | None = None) -> dict[str, Any]:
    barcode_items = [item for item in items if item.get("field") == "barcode"]
    actionable = [item for item in barcode_items if item.get("actionable_now")]
    non_actionable = [item for item in barcode_items if not item.get("actionable_now")]
    kuji_not_public = [
        item
        for item in barcode_items
        if item.get("source_group") == "kuji" and item.get("applicability") == "not_publicly_available"
    ]
    manual_only = [item for item in barcode_items if item.get("applicability") == "manual_only_or_not_public"]

    by_applicability = Counter(str(item.get("applicability") or "") for item in barcode_items)
    by_source_group = Counter(str(item.get("source_group") or "") for item in barcode_items)
    by_store = Counter(str(item.get("source_store") or "") for item in barcode_items)
    actionable_by_store = Counter(str(item.get("source_store") or "") for item in actionable)
    actionable_by_group = Counter(str(item.get("source_group") or "") for item in actionable)
    actionable_store_category = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or "")) for item in actionable
    )

    return {
        "source": str(source or DEFAULT_QUEUE),
        "barcode_missing_rows": len(barcode_items),
        "actionable_barcode_rows": len(actionable),
        "non_actionable_barcode_rows": len(non_actionable),
        "kuji_not_public_barcode_rows": len(kuji_not_public),
        "manual_only_or_not_public_rows": len(manual_only),
        "by_applicability": _top(by_applicability, 40),
        "by_source_group": _top(by_source_group, 40),
        "top_source_stores": _top(by_store, 40),
        "actionable_by_source_group": _top(actionable_by_group, 40),
        "actionable_top_source_stores": _top(actionable_by_store, 40),
        "actionable_top_store_categories": _top_pair(actionable_store_category, "source_store", "category", 80),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog Barcode Applicability Audit",
        "",
        f"- Source: `{payload['source']}`",
        f"- Barcode missing rows: `{payload['barcode_missing_rows']}`",
        f"- Actionable barcode rows: `{payload['actionable_barcode_rows']}`",
        f"- Non-actionable barcode rows: `{payload['non_actionable_barcode_rows']}`",
        f"- Kuji prize rows without public JAN expectation: `{payload['kuji_not_public_barcode_rows']}`",
        f"- Manual-only or not-public rows: `{payload['manual_only_or_not_public_rows']}`",
        "",
        "## By Applicability",
    ]
    for item in payload["by_applicability"]:
        lines.append(f"- `{item['value']}`: `{item['rows']}`")
    lines.extend(["", "## Actionable Stores"])
    for item in payload["actionable_top_source_stores"][:30]:
        lines.append(f"- `{item['value']}`: `{item['rows']}`")
    lines.extend(["", "## Actionable Store Categories"])
    for item in payload["actionable_top_store_categories"][:50]:
        lines.append(f"- `{item['source_store']}` / `{item['category']}`: `{item['rows']}`")
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
                "barcode_missing_rows": payload["barcode_missing_rows"],
                "actionable_barcode_rows": payload["actionable_barcode_rows"],
                "kuji_not_public_barcode_rows": payload["kuji_not_public_barcode_rows"],
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
