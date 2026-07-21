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
DEFAULT_QUEUE = SERVER / "requested_focus_confirmed_rows.json"
FALLBACK_QUEUE = SERVER / "requested_focus_confirmed_rows.template.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_REPORT = SERVER / "requested_focus_confirmed_import_report.json"
ALLOWED_FIELDS = {"source_url", "image_url", "release_date", "official_price_jpy", "name_ja"}
GENERIC_IMAGE_RE = re.compile(r"(^|[/_.-])(?:ogp?|og-image|share|sns|logo|banner|cover|hero|noimage|placeholder|default)([/_.-]|$)", re.I)


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
    return url.rstrip("/")


def _looks_generic_url(value: Any) -> bool:
    url = _http_url(value)
    if not url:
        return True
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/").lower()
    return path in {"", "/"} or any(token in path for token in ("/search", "/category", "/collections"))


def _looks_generic_image_url(value: Any) -> bool:
    url = _http_url(value)
    if not url:
        return True
    filename = urlsplit(url).path.rsplit("/", 1)[-1] or urlsplit(url).path
    return bool(GENERIC_IMAGE_RE.search(filename))


def _clean_value(field: str, value: Any) -> tuple[Any, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, "manual_value_missing"
    if field == "source_url":
        url = _http_url(text)
        if not url:
            return None, "invalid_source_url"
        if _looks_generic_url(url):
            return None, "generic_source_url"
        return url, None
    if field == "image_url":
        url = _http_url(text)
        if not url:
            return None, "invalid_image_url"
        if _looks_generic_image_url(url):
            return None, "generic_image_url"
        return url, None
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
        if not 1 <= price <= 1_000_000:
            return None, "invalid_official_price_jpy"
        return price, None
    if field == "name_ja":
        if _http_url(text) or len(text) > 160:
            return None, "invalid_name_ja"
        return re.sub(r"\s+", " ", text), None
    return None, "unsupported_field"


def _iter_items(raw_queue: Any) -> list[dict[str, Any]]:
    if isinstance(raw_queue, list):
        return [item for item in raw_queue if isinstance(item, dict)]
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("items"), list):
            return [item for item in raw_queue["items"] if isinstance(item, dict)]
        if isinstance(raw_queue.get("catalog_field_import_template"), dict):
            item = dict(raw_queue["catalog_field_import_template"])
            for key in ("topic_id", "topic_label", "source_store", "name_ko", "name_ja", "category"):
                item.setdefault(key, raw_queue.get(key))
            return [item]
        if raw_queue.get("field"):
            return [raw_queue]
    raise SystemExit("queue must contain items, a list of items, or one requested-focus patch object")


def _find_row(seed_rows: list[dict[str, Any]], item: dict[str, Any]) -> tuple[int | None, str | None]:
    row_index = item.get("row_index")
    if isinstance(row_index, int) and not isinstance(row_index, bool) and 0 <= row_index < len(seed_rows):
        row = seed_rows[row_index]
        if item.get("name_ko") in (None, "", row.get("name_ko")) and item.get("source_store") in (None, "", row.get("source_store")):
            return row_index, None
        return None, "row_index_identity_mismatch"
    catalog_index = item.get("catalog_index")
    if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
        matches = [index for index, row in enumerate(seed_rows) if row.get("catalog_index") == catalog_index]
        if len(matches) == 1:
            return matches[0], None
    return None, "seed_match_missing"


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
        base = {"row_index": item.get("row_index"), "catalog_index": item.get("catalog_index"), "field": field, "name_ko": item.get("name_ko")}
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue
        if field not in ALLOWED_FIELDS:
            skipped.append({**base, "reason": "unsupported_field"})
            continue
        value, value_error = _clean_value(field, item.get("manual_value"))
        if value_error:
            skipped.append({**base, "reason": value_error})
            continue
        if field in {"source_url", "image_url", "release_date", "official_price_jpy"}:
            evidence_url = _http_url(item.get("evidence_url")) or _http_url(item.get("candidate_source_url"))
            if not evidence_url:
                skipped.append({**base, "reason": "evidence_url_required"})
                continue
            if field != "image_url" and _looks_generic_url(evidence_url):
                skipped.append({**base, "reason": "exact_evidence_url_required"})
                continue
        seed_index, match_error = _find_row(normalized_seed, item)
        if seed_index is None:
            skipped.append({**base, "reason": match_error})
            continue
        row = normalized_seed[seed_index]
        existing = row.get(field)
        if existing not in (None, "", value) and not allow_existing_overwrite:
            skipped.append({**base, "reason": "existing_field_conflict", "existing": existing, "manual_value": value})
            continue
        if existing == value:
            skipped.append({**base, "reason": "no_change"})
            continue
        row[field] = value
        updated.append(
            {
                "row_index": seed_index,
                "catalog_index": row.get("catalog_index"),
                "field": field,
                "value": value,
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "topic_id": item.get("topic_id"),
            }
        )

    return {"seed_rows": normalized_seed, "updated": updated, "skipped": skipped}


def _load_seed(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or an object with items")


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
    seed_rows = _load_seed(args.seed)
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
        args.seed.write_text(json.dumps(result["seed_rows"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Confirm requested focus evidence, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
