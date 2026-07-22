from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
WORK_QUEUE = DATA / "catalog_missing_image_work_queue_public.json"
REPORT = DATA / "catalog_missing_image_report_coverage_public.json"

ANIMATE_STORE = "\uc560\ub2c8\uba54\uc774\ud2b8"
ENSKY_STORE = "\uc5d4\uc2a4\uce74\uc774"
GOODSMILE_STORE = "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8"
STELLIVE_STORE = "Stellive Store"
KOTOBUKIYA_STORE = "\ucf54\ud1a0\ubd80\ud0a4\uc57c"
JUMP_STORE = "\uc810\ud504 \uce90\ub9ad\ud130\uc988 \uc2a4\ud1a0\uc5b4"
GOTOUCHI_STORE = "\u3054\u5f53\u5730\u3061\u3044\u304b\u308f \uacf5\uc2dd(API)"


REPORT_RULES = [
    ("animate_missing_image_search", "data/animate_missing_image_search_public.json", {ANIMATE_STORE}, None),
    ("ensky_cache_coverage", "data/ensky_missing_image_cache_coverage_public.json", {ENSKY_STORE}, None),
    ("goodsmile_missing_image_search", "data/goodsmile_missing_image_search_public.json", {GOODSMILE_STORE}, None),
    ("stellive_fanding_candidates", "data/stellive_fanding_candidates_public.json", {STELLIVE_STORE}, None),
    (
        "kotobukiya_movic_missing_image_search",
        "data/kotobukiya_movic_missing_image_search_public.json",
        {KOTOBUKIYA_STORE, "Movic"},
        None,
    ),
    (
        "jump_furyu_taito_missing_image_search",
        "data/jump_furyu_taito_missing_image_search_public.json",
        {JUMP_STORE, "FuRyu", "Taito"},
        None,
    ),
    (
        "secondary_official_missing_image_search",
        "data/secondary_official_missing_image_search_public.json",
        {"AmiAmi", "Cospa", "\ubc18\ub2e4\uc774", "\uba54\uac00\ud558\uc6b0\uc2a4", "Re-ment", "SEGA"},
        None,
    ),
    ("gotouchi_chiikawa_image_candidates", "data/gotouchi_chiikawa_image_candidates_public.json", {GOTOUCHI_STORE}, None),
    (
        "manual_missing_image_source_discovery",
        "data/manual_missing_image_source_discovery_public.json",
        None,
        ("manual_review", "manual_research_required"),
    ),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def catalog_items(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def queue_items(queue: dict[str, Any]) -> list[dict[str, Any]]:
    items = queue.get("items")
    if not isinstance(items, list):
        raise ValueError("catalog_missing_image_work_queue_public.json must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def missing_catalog_items(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in catalog_items(catalog) if not present(item.get("image_url"))]


def queue_by_index(queue: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in queue_items(queue):
        row_index = item.get("row_index")
        if isinstance(row_index, int):
            result[row_index] = item
    return result


def rule_matches(
    row: dict[str, Any],
    queue_row: dict[str, Any] | None,
    stores: set[str] | None,
    strategy_safety: tuple[str, str] | None,
) -> bool:
    if stores is not None and row.get("source_store") in stores:
        return True
    if strategy_safety and queue_row:
        strategy, safety = strategy_safety
        return queue_row.get("strategy") == strategy and queue_row.get("automation_safety") == safety
    return False


def counter_rows(counter: Counter[str], field: str, limit: int = 40) -> list[dict[str, Any]]:
    return [{field: key, "rows": count} for key, count in counter.most_common(limit)]


def build_report(
    catalog: dict[str, Any],
    queue: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows = missing_catalog_items(catalog)
    qlookup = queue_by_index(queue)
    assignments: dict[int, str] = {}
    assignment_rows: dict[str, list[dict[str, Any]]] = {rule[0]: [] for rule in REPORT_RULES}

    for row in rows:
        catalog_index = row.get("catalog_index")
        queue_row = qlookup.get(catalog_index) if isinstance(catalog_index, int) else None
        if not isinstance(catalog_index, int):
            continue
        for report_key, _public_report, stores, strategy_safety in REPORT_RULES:
            if rule_matches(row, queue_row, stores, strategy_safety):
                assignments[catalog_index] = report_key
                assignment_rows[report_key].append(row)
                break

    unassigned = [row for row in rows if row.get("catalog_index") not in assignments]
    by_unassigned_store = Counter(str(row.get("source_store") or "") for row in unassigned)
    by_unassigned_strategy = Counter(
        str(qlookup.get(row.get("catalog_index"), {}).get("strategy") or "not_in_queue")
        for row in unassigned
        if isinstance(row.get("catalog_index"), int)
    )

    report_rows = []
    for report_key, public_report, _stores, _strategy_safety in REPORT_RULES:
        assigned = assignment_rows[report_key]
        report_rows.append(
            {
                "report_key": report_key,
                "public_report": public_report,
                "assigned_missing_image_rows": len(assigned),
                "report_exists": (ROOT / public_report).exists(),
                "auto_apply_enabled": False,
                "by_source_store": counter_rows(Counter(str(row.get("source_store") or "") for row in assigned), "source_store"),
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_missing_image_report_coverage",
        "summary": {
            "missing_image_rows": len(rows),
            "assigned_report_rows": len(assignments),
            "unassigned_missing_image_rows": len(unassigned),
            "report_count": len(report_rows),
            "auto_apply_enabled": False,
        },
        "reports": report_rows,
        "unassigned_breakdowns": {
            "by_source_store": counter_rows(by_unassigned_store, "source_store"),
            "by_strategy": counter_rows(by_unassigned_strategy, "strategy"),
        },
        "unassigned_samples": [
            {
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_store": row.get("source_store"),
                "affiliation": row.get("affiliation"),
                "category": row.get("category"),
                "strategy": qlookup.get(row.get("catalog_index"), {}).get("strategy"),
                "automation_safety": qlookup.get(row.get("catalog_index"), {}).get("automation_safety"),
            }
            for row in unassigned[:50]
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "report_is_coverage_only": True,
            "requires_exact_product_identity_before_image_attachment": True,
        },
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CATALOG)
    parser.add_argument("--queue", type=Path, default=WORK_QUEUE)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input), load_json(args.queue))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
