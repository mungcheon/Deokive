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
DEFAULT_QUEUE = SERVER / "source_discovery_confirmed_rows.json"
FALLBACK_QUEUE = SERVER / "source_discovery_confirmed_rows.template.json"
DEFAULT_SEED = SERVER / "catalog_seed_from_local.json"
DEFAULT_REPORT = SERVER / "source_discovery_confirmed_import_report.json"

GENERIC_SOURCE_HINTS = ("/search", "/shop$", "/category", "/categories", "/collections", "/goods/?$")
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
GENERIC_IMAGE_RE = re.compile(r"(^|[/_.-])(?:ogp?|og-image|share|sns|logo|banner|cover|hero|noimage|placeholder|default)([/_.-]|$)", re.I)


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _item_confirmed(item: dict[str, Any]) -> bool:
    if _confirmed(item.get("manual_confirmed")):
        return True
    return str(item.get("manual_review_status") or "").strip().lower() in {
        "source_confirmed",
        "source_and_image_confirmed",
        "confirmed",
    }


def _http_url(value: Any) -> str | None:
    url = str(value or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url.rstrip("/")


def _same_url(left: Any, right: Any) -> bool:
    left_url = _http_url(left)
    right_url = _http_url(right)
    return bool(left_url and right_url and left_url == right_url)


def _is_generic_source_url(value: Any) -> bool:
    url = _http_url(value)
    if not url:
        return True
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/").lower()
    if not path or path == "/":
        return True
    return any(re.search(pattern, path, flags=re.I) for pattern in GENERIC_SOURCE_HINTS)


def _is_product_source_url(value: Any) -> bool:
    url = _http_url(value)
    return bool(url and not _is_generic_source_url(url) and PRODUCT_SOURCE_RE.search(urlsplit(url).path + ("?" + urlsplit(url).query if urlsplit(url).query else "")))


def _allowed_domain(item: dict[str, Any], source_url: str) -> bool:
    allowed = item.get("allowed_source_domains")
    if not isinstance(allowed, list) or not allowed:
        return True
    netloc = urlsplit(source_url).netloc.lower()
    return netloc in {str(domain).lower() for domain in allowed}


def _safe_image_url(value: Any) -> str | None:
    url = _http_url(value)
    if not url:
        return None
    filename = urlsplit(url).path.rsplit("/", 1)[-1] or urlsplit(url).path
    if GENERIC_IMAGE_RE.search(filename):
        return None
    return url


def _iter_items(raw_queue: Any) -> list[dict[str, Any]]:
    if isinstance(raw_queue, list):
        return [item for item in raw_queue if isinstance(item, dict)]
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("items"), list):
            return [item for item in raw_queue["items"] if isinstance(item, dict)]
        if isinstance(raw_queue.get("packs"), list):
            items: list[dict[str, Any]] = []
            for pack in raw_queue["packs"]:
                if not isinstance(pack, dict):
                    continue
                for item in pack.get("items") or []:
                    if not isinstance(item, dict):
                        continue
                    merged = dict(item)
                    merged.setdefault("focus_pack_id", pack.get("focus_pack_id"))
                    merged.setdefault("source_store", pack.get("source_store"))
                    if isinstance(pack.get("allowed_source_domains"), list) and not merged.get("allowed_source_domains"):
                        merged["allowed_source_domains"] = [
                            domain.get("domain") if isinstance(domain, dict) else domain
                            for domain in pack["allowed_source_domains"]
                        ]
                    items.append(merged)
            return items
        if isinstance(raw_queue.get("catalog_field_import_template"), dict):
            item = dict(raw_queue["catalog_field_import_template"])
            if isinstance(raw_queue.get("allowed_source_domains"), list):
                item["allowed_source_domains"] = raw_queue["allowed_source_domains"]
            return [item]
        if raw_queue.get("field") == "source_url" or raw_queue.get("source_url"):
            return [raw_queue]
    raise SystemExit("queue must contain items, a list of items, or one source discovery object")


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
        if not _item_confirmed(item):
            skipped.append({**base, "reason": "manual_confirmed_false"})
            continue
        source_url = _http_url(
            item.get("manual_confirmed_source_url")
            or item.get("manual_value")
            or item.get("source_url")
            or item.get("candidate_source_url")
        )
        if not source_url:
            skipped.append({**base, "reason": "source_url_missing"})
            continue
        if not _is_product_source_url(source_url):
            skipped.append({**base, "reason": "exact_product_source_url_required", "source_url": source_url})
            continue
        if not _allowed_domain(item, source_url):
            skipped.append({**base, "reason": "source_domain_not_allowed", "source_url": source_url})
            continue
        seed_index, match_error = _find_row(normalized_seed, item)
        if seed_index is None:
            skipped.append({**base, "reason": match_error})
            continue
        row = normalized_seed[seed_index]
        existing_source = row.get("source_url")
        if existing_source not in (None, "", source_url):
            skipped.append({**base, "reason": "existing_source_url_conflict", "existing": existing_source, "source_url": source_url})
            continue

        changed: dict[str, Any] = {}
        if not _same_url(existing_source, source_url):
            row["source_url"] = source_url
            changed["source_url"] = source_url
        image_url = _safe_image_url(
            item.get("manual_confirmed_image_url")
            or item.get("image_url")
            or item.get("manual_image_url")
        )
        if image_url:
            existing_image = row.get("image_url")
            if existing_image not in (None, "", image_url):
                skipped.append({**base, "reason": "existing_image_url_conflict", "existing": existing_image, "image_url": image_url})
                continue
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


def _dump_seed_payload(original_payload: Any, seed_rows: list[dict[str, Any]]) -> Any:
    if isinstance(original_payload, dict) and isinstance(original_payload.get("items"), list):
        updated_payload = dict(original_payload)
        updated_payload["items"] = seed_rows
        meta = updated_payload.get("meta")
        if isinstance(meta, dict):
            meta = dict(meta)
            meta["row_count"] = len(seed_rows)
            meta["total_items"] = len(seed_rows)
            updated_payload["meta"] = meta
        return updated_payload
    return seed_rows


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
    seed_payload, seed_rows = _load_seed_payload(args.seed)
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
        updated_seed_payload = _dump_seed_payload(seed_payload, result["seed_rows"])
        args.seed.write_text(json.dumps(updated_seed_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Confirm exact product source evidence, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
