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

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DEFAULT_QUEUE = SERVER / "catalog_image_attachment_confirmed_rows.json"
FALLBACK_QUEUE = SERVER / "catalog_image_attachment_confirmed_rows.template.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_REPORT = SERVER / "catalog_image_attachment_confirmed_import_report.json"

GENERIC_SOURCE_HINTS = ("/search", "/shop", "/collections", "/category", "/categories")
GENERIC_IMAGE_RE = re.compile(r"(^|[/_.-])(?:ogp?|og-image|share|sns|logo|banner|cover|hero|noimage|placeholder|default)([/_.-]|$)", re.I)
PRODUCT_SOURCE_PATTERNS = (
    re.compile(r"^https://fanding\.kr/@[^/]+/shop/\d+/?$", re.I),
    re.compile(r"^https://shop\.weverse\.io/[a-z]{2}/shop/[A-Z]{3}/artists/\d+/sales/\d+/?$", re.I),
    re.compile(r"^https://www\.jp-api\.com/contents/[A-Z0-9]+/?$", re.I),
    re.compile(r"^https://www\.pokemoncenter-online\.com/\d{8,14}\.html$", re.I),
    re.compile(r"^https://chiikawamarket\.jp/(?:ko/)?products/[^/?#]+/?$", re.I),
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


def _same_url(left: Any, right: Any) -> bool:
    left_url = _http_url(left)
    right_url = _http_url(right)
    if not left_url or not right_url:
        return False
    return left_url.rstrip("/") == right_url.rstrip("/")


def _looks_generic_source_url(value: Any) -> bool:
    url = _http_url(value)
    if not url:
        return True
    if any(pattern.search(url.rstrip("/")) for pattern in PRODUCT_SOURCE_PATTERNS):
        return False
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/").lower()
    if not path or path == "/":
        return True
    return any(hint in path for hint in GENERIC_SOURCE_HINTS)


def _product_specific_source_url(value: Any) -> bool:
    url = _http_url(value)
    if not url:
        return False
    return any(pattern.search(url.rstrip("/")) for pattern in PRODUCT_SOURCE_PATTERNS)


def _looks_generic_image_url(value: Any) -> bool:
    url = _http_url(value)
    if not url:
        return True
    parsed = urlsplit(url)
    filename = parsed.path.rsplit("/", 1)[-1] or parsed.path
    return bool(GENERIC_IMAGE_RE.search(filename))


def _safe_image_pair(source_url: Any, image_url: Any, *, representative_image: bool = False) -> bool:
    source = _http_url(source_url)
    image = _http_url(image_url)
    if not source or not image:
        return False
    if representative_image and not _looks_generic_source_url(source):
        return True
    if not _product_specific_source_url(source):
        return False
    if _looks_generic_image_url(image):
        return False
    return True


def _iter_items(raw_queue: Any) -> list[dict[str, Any]]:
    if isinstance(raw_queue, list):
        return [item for item in raw_queue if isinstance(item, dict)]
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("items"), list):
            return [item for item in raw_queue["items"] if isinstance(item, dict)]
        if raw_queue.get("catalog_field_import_template"):
            template = raw_queue.get("catalog_field_import_template")
            return [template] if isinstance(template, dict) else []
        if raw_queue.get("field") == "image_url":
            return [raw_queue]
    raise SystemExit("queue must contain items, a list of items, or one image attachment object")


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


def import_rows(review_queue: dict[str, Any] | list[Any], seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_seed = [dict(row) for row in seed_rows if isinstance(row, dict)]
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in _iter_items(review_queue):
        base = {"row_index": item.get("row_index"), "catalog_index": item.get("catalog_index"), "name_ko": item.get("name_ko")}
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue
        if str(item.get("field") or "").strip() != "image_url":
            skipped.append({**base, "reason": "unsupported_field"})
            continue
        image_url = _http_url(item.get("manual_value"))
        if not image_url:
            skipped.append({**base, "reason": "invalid_image_url"})
            continue
        candidate_source_url = _http_url(item.get("candidate_source_url")) or _http_url(item.get("evidence_url"))
        if not candidate_source_url:
            skipped.append({**base, "reason": "candidate_source_url_required"})
            continue
        seed_index, match_error = _find_row(normalized_seed, item)
        if seed_index is None:
            skipped.append({**base, "reason": match_error})
            continue
        row = normalized_seed[seed_index]
        source_url = candidate_source_url or row.get("source_url")
        if not _safe_image_pair(source_url, image_url, representative_image=_confirmed(item.get("representative_image"))):
            skipped.append({**base, "reason": "unsafe_source_image_pair"})
            continue
        existing_image = row.get("image_url")
        if existing_image not in (None, "", image_url):
            skipped.append({**base, "reason": "existing_image_url_conflict", "existing": existing_image, "manual_value": image_url})
            continue
        changed: dict[str, Any] = {}
        existing_source = row.get("source_url")
        if candidate_source_url and not _same_url(existing_source, candidate_source_url):
            if existing_source not in (None, "") and not _looks_generic_source_url(existing_source):
                skipped.append({**base, "reason": "existing_source_url_conflict", "existing_source_url": existing_source})
                continue
            row["source_url"] = candidate_source_url
            changed["source_url"] = candidate_source_url
        if existing_image != image_url:
            row["image_url"] = image_url
            changed["image_url"] = image_url
        if not changed:
            skipped.append({**base, "reason": "no_change"})
            continue
        updated.append(
            {
                "row_index": seed_index,
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "updated": changed,
                "candidate_source_url": candidate_source_url,
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
    result = import_rows(review_queue, seed_rows)
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])
    report = {
        "write": args.write,
        "queue": str(args.queue),
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
        print("Dry run only. Confirm exact product source/image evidence, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
