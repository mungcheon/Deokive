from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_QUEUE = DATA / "source_discovery_next_focus_variant_metadata_confirmed_rows.template.json"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_REPORT = DATA / "source_discovery_next_focus_variant_metadata_import_dry_run_public.json"

CONFIRMED_FIELD_MAP = {
    "manual_confirmed_name_ja": "name_ja",
    "manual_confirmed_name_ko": "name_ko",
    "manual_confirmed_sub_series": "sub_series",
    "manual_confirmed_category": "category",
}

PRODUCT_SOURCE_RE = re.compile(
    r"("
    r"/products?/[^/?#]+|"
    r"/product/\d+|"
    r"/item/[^/?#]+|"
    r"/items?/[^/?#]+|"
    r"/detail(?:\.php)?(?:/|\?)|"
    r"/pd/\d+|"
    r"/shop/g/g[^/?#]+|"
    r"/prize/(?:item/)?[^/?#]+|"
    r"/goods/goods\d+\.php|"
    r"/\d{8,14}\.html"
    r")",
    re.I,
)


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _http_url(value: Any) -> str | None:
    url = str(value or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url


def _is_exact_evidence_url(value: Any) -> bool:
    url = _http_url(value)
    if not url:
        return False
    parsed = urlsplit(url)
    path_with_query = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    if parsed.netloc.lower() == "1kuji.com" and parsed.path.startswith("/products/"):
        return True
    return bool(PRODUCT_SOURCE_RE.search(path_with_query))


def _clean_text(field: str, value: Any) -> tuple[str | None, str | None]:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return None, "manual_value_missing"
    if _http_url(text):
        return None, f"invalid_{field}"
    limits = {
        "name_ja": 180,
        "name_ko": 180,
        "sub_series": 100,
        "category": 60,
    }
    if len(text) > limits[field]:
        return None, f"invalid_{field}"
    return text, None


def _catalog_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    raise SystemExit("catalog must be a JSON list or an object with items")


def _iter_templates(payload: Any) -> list[dict[str, Any]]:
    raw_items: list[Any]
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            raw_items = payload["items"]
        elif isinstance(payload.get("metadata_backfill_template"), dict):
            raw_items = [payload]
        else:
            raw_items = []
    else:
        raw_items = []

    templates: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        template = raw.get("metadata_backfill_template")
        if isinstance(template, dict):
            merged = {
                "catalog_index": raw.get("catalog_index"),
                "name_ko": raw.get("name_ko"),
                "source_store": raw.get("source_store"),
            }
            merged.update(template)
            templates.append(merged)
        else:
            templates.append(dict(raw))
    return templates


def _find_catalog_index(rows: list[dict[str, Any]], item: dict[str, Any]) -> tuple[int | None, str | None]:
    catalog_index = item.get("catalog_index")
    if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
        matches = [index for index, row in enumerate(rows) if row.get("catalog_index") == catalog_index]
        if len(matches) == 1:
            return matches[0], None
        return None, "catalog_index_not_unique" if matches else "catalog_index_missing"
    return None, "catalog_index_missing"


def import_rows(queue_payload: Any, catalog_payload: Any, *, write: bool = False) -> dict[str, Any]:
    rows = [dict(row) for row in _catalog_rows(catalog_payload)]
    templates = _iter_templates(queue_payload)
    skipped: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    field_counts: Counter[str] = Counter()

    for item in templates:
        base = {
            "catalog_index": item.get("catalog_index"),
            "name_ko": item.get("name_ko"),
            "source_store": item.get("source_store"),
        }
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue

        candidate_values: dict[str, str] = {}
        for source_key, field in CONFIRMED_FIELD_MAP.items():
            value, value_error = _clean_text(field, item.get(source_key))
            if value_error == "manual_value_missing":
                continue
            if value_error:
                blocked.append({**base, "field": field, "reason": value_error})
                continue
            candidate_values[field] = value or ""

        if not candidate_values:
            skipped.append({**base, "reason": "no_confirmed_metadata_values"})
            continue

        evidence_url = _http_url(item.get("manual_evidence_url") or item.get("evidence_url"))
        if not _is_exact_evidence_url(evidence_url):
            blocked.append({**base, "reason": "exact_evidence_url_required", "fields": sorted(candidate_values)})
            continue

        row_index, match_error = _find_catalog_index(rows, item)
        if row_index is None:
            blocked.append({**base, "reason": match_error})
            continue

        row = rows[row_index]
        changes: dict[str, str] = {}
        conflicts: list[dict[str, Any]] = []
        for field, value in candidate_values.items():
            existing = row.get(field)
            if existing in (None, ""):
                changes[field] = value
            elif str(existing).strip() == value:
                continue
            else:
                conflicts.append({"field": field, "existing": existing, "manual_value": value})

        if conflicts:
            blocked.append({**base, "reason": "existing_field_conflict", "conflicts": conflicts})
            continue
        if not changes:
            skipped.append({**base, "reason": "no_change"})
            continue

        if write:
            row.update(changes)
        field_counts.update(changes.keys())
        updated.append(
            {
                "catalog_index": row.get("catalog_index"),
                "row_index": row_index,
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "evidence_url": evidence_url,
                "fields": changes,
            }
        )

    skip_counts = Counter(str(item.get("reason")) for item in skipped)
    block_counts = Counter(str(item.get("reason")) for item in blocked)
    return {
        "catalog_rows": rows,
        "summary": {
            "template_items": len(templates),
            "manual_confirmed_rows": sum(1 for item in templates if _confirmed(item.get("manual_confirmed"))),
            "ready_update_rows": len(updated),
            "updated_rows": len(updated) if write else 0,
            "would_update_rows": len(updated) if not write else 0,
            "skipped_rows": len(skipped),
            "blocked_rows": len(blocked),
            "field_update_counts": field_counts.most_common(),
            "skip_reason_counts": skip_counts.most_common(),
            "blocked_reason_counts": block_counts.most_common(),
        },
        "updated": updated,
        "skipped_sample": skipped[:100],
        "blocked_sample": blocked[:100],
    }


def _display_path(path: Path) -> str:
    try:
        path = path.relative_to(ROOT)
    except ValueError:
        pass
    return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    queue_payload = json.loads(args.queue.read_text(encoding="utf-8-sig"))
    catalog_payload = json.loads(args.catalog.read_text(encoding="utf-8-sig"))
    result = import_rows(queue_payload, catalog_payload, write=args.write)
    report = {
        "write": args.write,
        "queue": _display_path(args.queue),
        "catalog": _display_path(args.catalog),
        **{key: result[key] for key in ("summary", "updated", "skipped_sample", "blocked_sample")},
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and result["updated"]:
        payload_to_write: Any
        if isinstance(catalog_payload, dict) and isinstance(catalog_payload.get("items"), list):
            payload_to_write = dict(catalog_payload)
            payload_to_write["items"] = result["catalog_rows"]
        else:
            payload_to_write = result["catalog_rows"]
        args.catalog.write_text(json.dumps(payload_to_write, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Fill metadata_backfill_template values and re-run with --write after reviewing this report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
