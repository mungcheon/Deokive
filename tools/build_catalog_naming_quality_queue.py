from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

try:
    from catalog_quality_report import build_report, load_catalog_rows
except ImportError:
    from tools.catalog_quality_report import build_report, load_catalog_rows


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_JSON = ROOT / "server" / "catalog_naming_quality_queue.json"
DEFAULT_CSV = ROOT / "server" / "catalog_naming_quality_queue.csv"


def _sample_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _base_item(workflow: str, priority: int, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow": workflow,
        "priority": priority,
        "status": "needs_review",
        "catalog_index": row.get("catalog_index"),
        "display_name": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "character_name": row.get("character_name"),
        "expected_character_name": row.get("expected_character_name"),
        "affiliation": row.get("affiliation"),
        "source_store": row.get("source_store"),
        "source_url": row.get("source_url"),
        "reason": row.get("reason"),
        "display_parts": row.get("display_parts") or [],
    }


def build_queue(quality_report: dict[str, Any]) -> dict[str, Any]:
    character_quality = quality_report.get("character_name_quality") or {}
    character_samples = character_quality.get("samples") or {}
    if not isinstance(character_samples, dict):
        character_samples = {}
    ichiban = quality_report.get("ichiban_kuji") or {}

    items: list[dict[str, Any]] = []
    for row in _sample_items(character_samples.get("known_alias_rows")):
        item = _base_item("character_alias_normalization", 10, row)
        item["recommended_action"] = "Normalize character_name to expected_character_name."
        items.append(item)
    for row in _sample_items(character_samples.get("ja_token_mismatch_rows")):
        item = _base_item("character_ja_token_mismatch", 15, row)
        item["recommended_action"] = (
            "Compare name_ja with character_name and set the official Korean display character."
        )
        items.append(item)
    for row in _sample_items(ichiban.get("naming_convention_review_sample")):
        if row.get("reason") == "non_prize_or_related_item_needs_classification":
            item = _base_item("ichiban_non_prize_related_item_review", 25, row)
            item["recommended_action"] = (
                "Classify as related/campaign/non-prize goods or replace with exact prize-rank evidence."
            )
        else:
            item = _base_item("ichiban_display_name_convention", 20, row)
            item["recommended_action"] = (
                "Rewrite display_name as release name / prize rank / prize name / character name."
            )
        items.append(item)
    for row in _sample_items(character_samples.get("single_character_name_review_rows")):
        item = _base_item("single_character_name_review", 40, row)
        item["recommended_action"] = "Confirm the one-character name is intentional, not truncated."
        items.append(item)

    items.sort(
        key=lambda item: (
            int(item.get("priority") or 99),
            str(item.get("source_store") or ""),
            str(item.get("display_name") or ""),
        )
    )
    return {
        "source": "data/catalog_public.json",
        "quality_report_source": "server/catalog_quality_report.json",
        "summary": {
            "known_alias_rows": character_quality.get("known_alias_rows", 0),
            "ja_token_mismatch_rows": character_quality.get("ja_token_mismatch_rows", 0),
            "single_character_name_review_rows": character_quality.get(
                "single_character_name_review_rows", 0
            ),
            "ichiban_naming_convention_review_rows": ichiban.get(
                "naming_convention_review_rows", 0
            ),
            "queue_rows": len(items),
        },
        "items": items,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(queue: dict[str, Any], path: Path) -> None:
    fields = [
        "workflow",
        "priority",
        "status",
        "catalog_index",
        "display_name",
        "name_ja",
        "character_name",
        "expected_character_name",
        "affiliation",
        "source_store",
        "source_url",
        "reason",
        "display_parts",
        "recommended_action",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in queue.get("items", []):
            row = {field: item.get(field, "") for field in fields}
            if isinstance(row["display_parts"], list):
                row["display_parts"] = " | ".join(str(value) for value in row["display_parts"])
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a public-catalog character and Ichiban naming quality queue."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    quality_report = build_report(load_catalog_rows(args.catalog))
    queue = build_queue(quality_report)
    write_json(args.json_output, queue)
    write_csv(queue, args.csv_output)
    print(json.dumps(queue["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
