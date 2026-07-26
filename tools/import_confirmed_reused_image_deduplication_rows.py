from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from generate_seed_catalog_dart import generate
except ModuleNotFoundError:
    from tools.generate_seed_catalog_dart import generate

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_REVIEW = DATA / "catalog_reused_image_deduplication_review_public.json"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_REPORT = DATA / "catalog_reused_image_deduplication_import_dry_run_public.json"
DEFAULT_SEED_OUTPUT = ROOT / "lib" / "data" / "catalog" / "seed_catalog.dart"

VALID_DECISIONS = {
    "same_sellable_product_keep_one",
}


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool):
            result.append(item)
        elif str(item).strip().isdigit():
            result.append(int(str(item).strip()))
    return result


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _catalog_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    rows = catalog.get("items")
    if not isinstance(rows, list):
        raise SystemExit("catalog must contain an items list")
    return [row for row in rows if isinstance(row, dict)]


def _index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        catalog_index = row.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            result[catalog_index] = row
    return result


def _decision_template(item: dict[str, Any]) -> dict[str, Any]:
    template = item.get("decision_template")
    return template if isinstance(template, dict) else {}


def _same_flags_pass(item: dict[str, Any]) -> bool:
    return all(
        item.get(field) is True
        for field in (
            "source_url_same",
            "image_same",
            "category_same",
            "character_same",
            "rank_same",
        )
    )


def _choose_keep_drop(template: dict[str, Any]) -> tuple[int | None, list[int]]:
    keep = template.get("manual_keep_catalog_index")
    if not isinstance(keep, int) or isinstance(keep, bool):
        keep = template.get("suggested_keep_catalog_index")
    if not isinstance(keep, int) or isinstance(keep, bool):
        keep = None

    manual_drops = _int_list(template.get("manual_drop_catalog_indexes"))
    drops = manual_drops or _int_list(template.get("suggested_drop_catalog_indexes"))
    return keep, drops


def import_confirmed(
    review: dict[str, Any],
    catalog: dict[str, Any],
    *,
    write: bool = False,
) -> dict[str, Any]:
    rows = _catalog_rows(catalog)
    by_index = _index(rows)
    drop_indexes: set[int] = set()
    keep_indexes: set[int] = set()
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in _items(review):
        template = _decision_template(item)
        keep, drops = _choose_keep_drop(template)
        base = {
            "group_index": item.get("group_index"),
            "confidence": item.get("confidence"),
            "keep_catalog_index": keep,
            "drop_catalog_indexes": drops,
        }
        if not _confirmed(template.get("manual_confirmed")):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue
        if str(template.get("decision") or "").strip() not in VALID_DECISIONS:
            skipped.append({**base, "reason": "unsupported_decision"})
            continue
        if item.get("confidence") != "strong_manual_duplicate_candidate":
            skipped.append({**base, "reason": "confidence_not_strong"})
            continue
        if not _same_flags_pass(item):
            skipped.append({**base, "reason": "identity_flags_not_all_true"})
            continue
        if not template.get("evidence_urls"):
            skipped.append({**base, "reason": "evidence_urls_missing"})
            continue
        if keep is None:
            skipped.append({**base, "reason": "invalid_keep_catalog_index"})
            continue
        if not drops:
            skipped.append({**base, "reason": "drop_catalog_indexes_missing"})
            continue
        if keep in drops:
            skipped.append({**base, "reason": "keep_catalog_index_in_drop_indexes"})
            continue
        if keep in drop_indexes:
            skipped.append({**base, "reason": "keep_row_already_dropped_by_prior_decision"})
            continue
        if keep not in by_index:
            skipped.append({**base, "reason": "keep_catalog_index_not_found"})
            continue
        missing_drops = [index for index in drops if index not in by_index]
        if missing_drops:
            skipped.append({**base, "reason": "drop_catalog_index_not_found", "missing_drop_catalog_indexes": missing_drops})
            continue
        reused = [index for index in drops if index in keep_indexes or index in drop_indexes]
        if reused:
            skipped.append({**base, "reason": "catalog_index_used_by_prior_decision", "overlapping_catalog_indexes": reused})
            continue

        keep_indexes.add(keep)
        for drop in drops:
            drop_indexes.add(drop)
            updated.append(
                {
                    "action": "drop_reused_image_duplicate_row",
                    "group_index": item.get("group_index"),
                    "keep_catalog_index": keep,
                    "drop_catalog_index": drop,
                    "keep_name_ko": by_index[keep].get("name_ko"),
                    "drop_name_ko": by_index[drop].get("name_ko"),
                    "source_urls": item.get("source_urls") or [],
                    "manual_note": template.get("manual_note") or "",
                }
            )

    filtered_rows = [row for row in rows if row.get("catalog_index") not in drop_indexes]
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in skipped)
    summary = {
        "write": write,
        "template_groups": len(_items(review)),
        "manual_confirmed_groups": sum(
            1 for item in _items(review) if _confirmed(_decision_template(item).get("manual_confirmed"))
        ),
        "ready_groups": len({item["group_index"] for item in updated}),
        "updated_rows": len(updated),
        "skipped_groups": len(skipped),
        "skip_reason_counts": [[key, value] for key, value in skip_reasons.most_common()],
        "input_rows": len(rows),
        "output_rows": len(filtered_rows),
        "auto_delete_enabled": False,
        "auto_merge_enabled": False,
    }
    return {
        "summary": summary,
        "updated": updated,
        "skipped_sample": skipped[:100],
        "catalog": {**catalog, "items": filtered_rows},
    }


def _sync_seed(catalog: dict[str, Any], output: Path, source_label: str) -> None:
    rows = _catalog_rows(catalog)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate(rows, source_label=source_label), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply manually confirmed reused-image duplicate decisions to the public catalog."
    )
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--seed-output", type=Path, default=DEFAULT_SEED_OUTPUT)
    parser.add_argument("--skip-seed-sync", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    review = _load_json(args.review)
    catalog = _load_json(args.catalog)
    result = import_confirmed(review, catalog, write=args.write)
    report = {
        **result["summary"],
        "review": str(args.review),
        "catalog": str(args.catalog),
        "updated": result["updated"],
        "skipped_sample": result["skipped_sample"],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and result["updated"]:
        args.catalog.write_text(json.dumps(result["catalog"], ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        if not args.skip_seed_sync:
            try:
                source_label = args.catalog.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                source_label = args.catalog.resolve().as_posix()
            _sync_seed(result["catalog"], args.seed_output, source_label)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Set manual_confirmed=true and decision=same_sellable_product_keep_one before --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
