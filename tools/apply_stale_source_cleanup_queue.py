from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_QUEUE = ROOT / "server" / "stale_source_cleanup_queue.json"
DEFAULT_REPORT = ROOT / "server" / "stale_source_cleanup_apply_report.json"

CLEAR_FIELDS = ("source_url", "image_url", "local_image_path")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_catalog(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    payload = _read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)], payload
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], None
    raise SystemExit(f"{path} must contain a JSON list or public catalog object with items")


def write_catalog(path: Path, rows: list[dict[str, Any]], wrapper: dict[str, Any] | None) -> None:
    if wrapper is None:
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    wrapper["items"] = rows
    meta = wrapper.get("meta")
    if isinstance(meta, dict):
        fields = meta.get("fields") or []
        meta["missing"] = {field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields}
        meta["row_count"] = len(rows)
        meta["total_items"] = len(rows)
    wrapper["total_items"] = len(rows)
    path.write_text(json.dumps(wrapper, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def load_queue(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise SystemExit(f"{path} must contain a JSON list or object with items")
    return [item for item in items if isinstance(item, dict)]


def _row_by_catalog_index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for row in rows:
        try:
            lookup[int(row.get("catalog_index"))] = row
        except (TypeError, ValueError):
            continue
    return lookup


def _fallback_row(rows: list[dict[str, Any]], item: dict[str, Any]) -> dict[str, Any] | None:
    name_ko = str(item.get("name_ko") or "").strip()
    name_ja = str(item.get("name_ja") or "").strip()
    source_url = str(item.get("current_source_url") or "").strip()
    for row in rows:
        if source_url and str(row.get("source_url") or "").strip() != source_url:
            continue
        if name_ko and str(row.get("name_ko") or "").strip() == name_ko:
            return row
        if name_ja and str(row.get("name_ja") or "").strip() == name_ja:
            return row
    return None


def _target_row(
    rows: list[dict[str, Any]],
    index_lookup: dict[int, dict[str, Any]],
    item: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    try:
        catalog_index = int(item.get("catalog_index"))
    except (TypeError, ValueError):
        catalog_index = None
    if catalog_index is not None and catalog_index in index_lookup:
        return index_lookup[catalog_index], "catalog_index"
    row = _fallback_row(rows, item)
    return row, "name_source_url" if row else "not_found"


def _safe_to_clear(row: dict[str, Any], item: dict[str, Any]) -> tuple[bool, str]:
    if item.get("identity_status") != "live_title_mismatch":
        return False, "identity_status_not_mismatch"
    if item.get("recommended_action") != "find_exact_source_url_before_image_use":
        return False, "recommended_action_not_clearable"

    current_source = str(item.get("current_source_url") or "").strip()
    row_source = str(row.get("source_url") or "").strip()
    if not current_source or row_source != current_source:
        return False, "source_url_changed"

    current_image = str(item.get("current_image_url") or "").strip()
    row_image = str(row.get("image_url") or "").strip()
    if current_image and row_image != current_image:
        return False, "image_url_changed"
    if not row_image:
        return False, "no_image_url_to_clear"
    return True, "clear_stale_source_and_image"


def apply_cleanup(
    rows: list[dict[str, Any]],
    queue_items: list[dict[str, Any]],
) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    index_lookup = _row_by_catalog_index(rows)
    updated = 0
    changes: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in queue_items:
        row, match_method = _target_row(rows, index_lookup, item)
        if row is None:
            skipped.append({"name_ko": item.get("name_ko"), "reason": "target_row_not_found"})
            continue
        ok, reason = _safe_to_clear(row, item)
        if not ok:
            skipped.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": row.get("name_ko"),
                    "reason": reason,
                    "match_method": match_method,
                }
            )
            continue

        before = {field: row.get(field) for field in CLEAR_FIELDS}
        for field in CLEAR_FIELDS:
            row.pop(field, None)
        updated += 1
        changes.append(
            {
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "match_method": match_method,
                "cleared_fields": [field for field, value in before.items() if value not in (None, "")],
                "before": before,
                "live_title": item.get("live_title"),
            }
        )

    return updated, changes, skipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    rows, wrapper = load_catalog(args.catalog)
    updated, changes, skipped = apply_cleanup(rows, load_queue(args.queue))
    report = {
        "write": args.write,
        "updated_rows": updated,
        "changes": changes,
        "skipped_rows": len(skipped),
        "skipped_sample": skipped[:200],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and updated:
        write_catalog(args.catalog, rows, wrapper)
    print(json.dumps({"updated_rows": updated, "skipped_rows": len(skipped), "report": str(args.report), "write": args.write}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to update the catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
