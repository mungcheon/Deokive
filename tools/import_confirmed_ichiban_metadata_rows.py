from __future__ import annotations

import argparse
import datetime as dt
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

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DEFAULT_QUEUE = SERVER / "ichiban_kuji_metadata_confirmed_rows.json"
FALLBACK_QUEUE = SERVER / "ichiban_kuji_metadata_confirmed_rows.template.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_REPORT = SERVER / "ichiban_kuji_metadata_confirmed_import_report.json"
ALLOWED_FIELDS = {"release_date", "official_price_jpy"}


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _official_1kuji_url(value: Any) -> str | None:
    url = str(value or "").strip()
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc.lower() != "1kuji.com":
        return None
    if not parsed.path.startswith("/products/"):
        return None
    return url.rstrip("/")


def _clean_value(field: str, value: Any) -> tuple[Any, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, "manual_value_missing"
    if field == "release_date":
        if not re.fullmatch(r"20\d{2}-\d{2}(?:-\d{2})?", text):
            return None, "invalid_release_date"
        try:
            dt.datetime.strptime(text, "%Y-%m-%d" if text.count("-") == 2 else "%Y-%m")
        except ValueError:
            return None, "invalid_release_date"
        return text, None
    if field == "official_price_jpy":
        try:
            price = int(text.replace(",", ""))
        except ValueError:
            return None, "invalid_official_price_jpy"
        if not 100 <= price <= 2000:
            return None, "invalid_official_price_jpy"
        return price, None
    return None, "unsupported_field"


def _iter_items(raw_queue: Any) -> list[dict[str, Any]]:
    if isinstance(raw_queue, list):
        return [item for item in raw_queue if isinstance(item, dict)]
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("items"), list):
            return [item for item in raw_queue["items"] if isinstance(item, dict)]
        if raw_queue.get("field") and raw_queue.get("evidence_url"):
            return [raw_queue]
    raise SystemExit("queue must contain items, a list of items, or one campaign field patch object")


def import_rows(
    review_queue: dict[str, Any] | list[Any],
    seed_rows: list[dict[str, Any]],
    *,
    allow_existing_overwrite: bool = False,
) -> dict[str, Any]:
    normalized_seed = [dict(row) for row in seed_rows if isinstance(row, dict)]
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in _iter_items(review_queue):
        field = str(item.get("field") or "").strip()
        evidence_url = _official_1kuji_url(item.get("evidence_url"))
        base = {
            "field": field,
            "campaign_slug": item.get("campaign_slug"),
            "campaign_title": item.get("campaign_title"),
            "evidence_url": item.get("evidence_url"),
        }
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue
        if not _confirmed(item.get("official_evidence_confirmed")):
            skipped.append({**base, "reason": "official_evidence_not_confirmed"})
            continue
        if field not in ALLOWED_FIELDS:
            skipped.append({**base, "reason": "unsupported_field"})
            continue
        if not evidence_url:
            skipped.append({**base, "reason": "official_1kuji_evidence_url_required"})
            continue
        value, value_error = _clean_value(field, item.get("manual_value"))
        if value_error:
            skipped.append({**base, "reason": value_error})
            continue

        matching_indexes = [
            index
            for index, row in enumerate(normalized_seed)
            if str(row.get("source_url") or "").strip().rstrip("/") == evidence_url
        ]
        expected_rows = item.get("target_catalog_item_rows")
        if isinstance(expected_rows, int) and expected_rows >= 0 and expected_rows != len(matching_indexes):
            skipped.append(
                {
                    **base,
                    "reason": "target_catalog_item_rows_mismatch",
                    "expected_rows": expected_rows,
                    "matched_rows": len(matching_indexes),
                }
            )
            continue
        if not matching_indexes:
            skipped.append({**base, "reason": "campaign_source_url_not_found"})
            continue

        for index in matching_indexes:
            row = normalized_seed[index]
            existing = row.get(field)
            if existing not in (None, "", value) and not allow_existing_overwrite:
                skipped.append(
                    {
                        **base,
                        "catalog_index": row.get("catalog_index"),
                        "name_ko": row.get("name_ko"),
                        "reason": "existing_field_conflict",
                        "existing": existing,
                        "manual_value": value,
                    }
                )
                continue
            if existing == value:
                skipped.append({**base, "catalog_index": row.get("catalog_index"), "reason": "no_change"})
                continue
            row[field] = value
            updated.append(
                {
                    "row_index": index,
                    "catalog_index": row.get("catalog_index"),
                    "field": field,
                    "value": value,
                    "source_url": evidence_url,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "campaign_slug": item.get("campaign_slug"),
                }
            )

    return {"seed_rows": normalized_seed, "updated": updated, "skipped": skipped}


def _load_seed_payload(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload, [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return payload, [row for row in payload if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or an object with items")


def _missing_by_field(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    return {field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields}


def _write_seed_payload(path: Path, payload: Any, rows: list[dict[str, Any]]) -> None:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        payload = dict(payload)
        meta = dict(payload.get("meta") or {})
        fields = meta.get("fields")
        payload["items"] = rows
        meta["generated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        meta["row_count"] = len(rows)
        meta["total_items"] = len(rows)
        if isinstance(fields, list):
            meta["missing"] = _missing_by_field(rows, [str(field) for field in fields])
        payload["meta"] = meta
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        return
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--allow-existing-overwrite", action="store_true")
    args = parser.parse_args()

    if not args.queue.exists():
        empty_report = {
            "write": args.write,
            "queue": str(args.queue),
            "updated_rows": 0,
            "skipped_rows": 0,
            "updated": [],
            "skipped_sample": [],
            "note": f"No confirmed queue found. Copy {FALLBACK_QUEUE.name} to {args.queue.name} after manual review.",
        }
        args.report.write_text(json.dumps(empty_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: empty_report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
        return 0

    review_queue = json.loads(args.queue.read_text(encoding="utf-8-sig"))
    seed_payload, seed_rows = _load_seed_payload(args.seed)
    result = import_rows(review_queue, seed_rows, allow_existing_overwrite=args.allow_existing_overwrite)
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])
    report = {
        "write": args.write,
        "queue": str(args.queue),
        "allow_existing_overwrite": args.allow_existing_overwrite,
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and result["updated"]:
        _write_seed_payload(args.seed, seed_payload, result["seed_rows"])
    print(json.dumps({k: report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Confirm official 1kuji evidence, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
