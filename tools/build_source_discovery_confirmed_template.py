from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "source_discovery_review_batches_public.json"
DEFAULT_OUTPUT = ROOT / "server" / "source_discovery_confirmed_rows.template.json"
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _template_items(
    payload: dict[str, Any],
    seed_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    stale_excluded: list[dict[str, Any]] = []
    seen: set[tuple[Any, str]] = set()
    for batch in payload.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        batch_id = str(batch.get("batch_id") or "")
        workflow = str(batch.get("workflow") or "")
        for row in batch.get("items") or []:
            if not isinstance(row, dict):
                continue
            template = row.get("catalog_field_import_template")
            if not isinstance(template, dict):
                continue
            row_index = template.get("row_index")
            key = (row_index, str(template.get("field") or ""))
            if key in seen:
                continue
            seen.add(key)
            if isinstance(seed_rows, list) and isinstance(row_index, int) and 0 <= row_index < len(seed_rows):
                seed_row = seed_rows[row_index]
                if seed_row.get("source_url"):
                    stale_excluded.append(
                        {
                            "row_index": row_index,
                            "catalog_index": seed_row.get("catalog_index"),
                            "name_ko": seed_row.get("name_ko"),
                            "source_store": seed_row.get("source_store"),
                            "source_discovery_batch_id": batch_id,
                            "reason": "seed_source_url_already_present",
                        }
                    )
                    continue
            output = dict(template)
            output["source_discovery_batch_id"] = batch_id
            output["source_discovery_workflow"] = workflow
            output["review_state"] = batch.get("review_state")
            output["manual_confirmed"] = False
            output["manual_value"] = ""
            output["candidate_source_url"] = ""
            items.append(output)
    return items, stale_excluded


def build_template(
    payload: dict[str, Any],
    seed_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items, stale_excluded = _template_items(payload, seed_rows)
    by_workflow = Counter(str(item.get("source_discovery_workflow") or "") for item in items)
    by_store = Counter(str(item.get("source_store") or "") for item in items)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "source_discovery_confirmed_source_url_template",
        "summary": {
            "template_items": len(items),
            "manual_confirmed_true": 0,
            "by_workflow": by_workflow.most_common(),
            "by_source_store": by_store.most_common(40),
            "stale_excluded_source_url_rows": len(stale_excluded),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Copy this template to source_discovery_confirmed_rows.json before importing reviewed rows.",
            "For each exact match, set manual_confirmed=true and manual_value to the exact product/detail source_url.",
            "Do not confirm search, storefront, tag, collection, or unrelated variant pages.",
            "Run tools/import_confirmed_source_discovery_rows.py with this confirmed file before using --write.",
        ],
        "stale_excluded_sample": stale_excluded[:50],
        "items": items,
        "automation_policy": {
            "auto_apply_enabled": False,
            "requires_manual_review": True,
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
            "confirmed_file": "server/source_discovery_confirmed_rows.json",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    args = parser.parse_args()

    payload = _load_json(args.input)
    if not isinstance(payload, dict):
        raise SystemExit(f"{args.input} must contain a JSON object")
    seed_rows = _load_json(args.seed) if args.seed.exists() else None
    if seed_rows is not None and not isinstance(seed_rows, list):
        raise SystemExit(f"{args.seed} must contain a JSON list")
    template = build_template(payload, seed_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    print(f"Template: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
