from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from catalog_normalize import canonical_key, is_generic_source_url, normalize_row
from image_enrichment_safety import is_product_specific_source_url, is_safe_source_image_pair, looks_like_generic_image_url

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = ROOT / "server" / "catalog_field_confirmed_rows.json"
FALLBACK_QUEUE = ROOT / "server" / "catalog_field_confirmed_rows.template.json"
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "catalog_field_confirmed_import_report.json"
ALLOWED_FIELDS = {
    "source_url",
    "image_url",
    "release_date",
    "barcode",
    "official_price_jpy",
    "sub_series",
    "name_ja",
    "character_name",
}
STORE_ALLOWED_NETLOCS = {
    "치이카와 마켓": {"chiikawamarket.jp"},
    "나가노 마켓": {"nagano-market.jp"},
    "치이카와 모구모구 혼포": {"chiikawamogumogu.shop"},
    "치이카와 온라인 쿠지": {"online-kuji.chiikawamarket.jp"},
    "애니메이트": {"www.animate-onlineshop.jp"},
    "엔스카이": {"www.enskyshop.com"},
    "굿스마일컴퍼니": {"www.goodsmile.info", "www.goodsmile.com"},
    "Banpresto": {"bsp-prize.jp"},
    "FuRyu": {"furyuprize.com"},
    "Taito": {"www.taito.co.jp", "taito.co.jp"},
    "코토부키야": {"shop.kotobukiya.co.jp", "www.kotobukiya.co.jp"},
    "Movic": {"www.movic.jp"},
    "Stellive Store": {"fanding.kr"},
    "Weverse Shop": {"shop.weverse.io"},
    "포켓몬 센터": {"www.pokemoncenter-online.com", "pokemoncenter-online.com"},
    "SEGA": {"segaplaza.jp"},
    "이치방쿠지": {"1kuji.com"},
    "AnyMy": {"anymy.jp"},
}
CHARACTER_NAME_PLACEHOLDERS = {"기타", "その他", "unknown", "Unknown", "UNKNOWN"}


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


def _same_netloc(left: Any, right: Any) -> bool:
    left_url = _http_url(left)
    right_url = _http_url(right)
    if not left_url or not right_url:
        return False
    return urlsplit(left_url).netloc.lower() == urlsplit(right_url).netloc.lower()


def _same_url(left: Any, right: Any) -> bool:
    left_url = _http_url(left)
    right_url = _http_url(right)
    if not left_url or not right_url:
        return False
    return left_url.rstrip("/") == right_url.rstrip("/")


def _evidence_url(item: dict[str, Any]) -> str | None:
    return _http_url(item.get("evidence_url")) or _http_url(item.get("candidate_source_url"))


def _store_url_compatible(source_store: Any, url: Any) -> bool:
    parsed_url = _http_url(url)
    if not parsed_url:
        return False
    if str(source_store or "").strip() == "굿스마일컴퍼니" and urlsplit(parsed_url).netloc.lower() == "special.goodsmile.info":
        return True
    allowed = STORE_ALLOWED_NETLOCS.get(str(source_store or "").strip())
    if not allowed:
        return True
    return urlsplit(parsed_url).netloc.lower() in allowed


def _is_exact_evidence_url(value: Any) -> bool:
    url = _http_url(value)
    if not url or is_generic_source_url(url):
        return False
    if is_product_specific_source_url(url):
        return True
    parsed = urlsplit(url)
    return parsed.netloc.lower() == "1kuji.com" and parsed.path.startswith("/products/")


def _clean_value(field: str, value: Any, item: dict[str, Any] | None = None) -> tuple[Any, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, "manual_value_missing"
    if field == "barcode":
        digits = re.sub(r"\D", "", text)
        if not re.fullmatch(r"\d{8,14}", digits):
            return None, "invalid_barcode"
        return digits, None
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
    if field in {"source_url", "image_url"}:
        url = _http_url(text)
        if not url:
            return None, "invalid_url"
        if field == "source_url" and is_generic_source_url(url):
            return None, "generic_source_url"
        if field == "image_url" and looks_like_generic_image_url(url) and not _confirmed((item or {}).get("representative_image")):
            return None, "generic_image_url"
        return url, None
    if field == "sub_series":
        text = re.sub(r"\s+", " ", text)
        if _http_url(text):
            return None, "invalid_sub_series"
        if len(text) > 80:
            return None, "invalid_sub_series"
        return text, None
    if field == "name_ja":
        text = re.sub(r"\s+", " ", text)
        if _http_url(text):
            return None, "invalid_name_ja"
        if len(text) > 160:
            return None, "invalid_name_ja"
        return text, None
    if field == "character_name":
        text = re.sub(r"\s+", " ", text)
        if _http_url(text):
            return None, "invalid_character_name"
        if len(text) > 80:
            return None, "invalid_character_name"
        return text, None
    return None, "unsupported_field"


def _identity_matches(row: dict[str, Any], item: dict[str, Any]) -> bool:
    for field in ("source_store", "name_ko", "name_ja", "category", "affiliation"):
        expected = item.get(field)
        if expected not in (None, "") and row.get(field) != expected:
            return False
    return True


def _find_seed_index(seed_rows: list[dict[str, Any]], item: dict[str, Any]) -> tuple[int | None, str | None]:
    row_index = item.get("row_index")
    if isinstance(row_index, int) and 0 <= row_index < len(seed_rows):
        if _identity_matches(seed_rows[row_index], item):
            return row_index, None
        return None, "row_index_identity_mismatch"

    probe = normalize_row(
        {
            "source_store": item.get("source_store"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "category": item.get("category"),
            "affiliation": item.get("affiliation"),
        }
    )
    key = canonical_key(probe)
    matches = [index for index, row in enumerate(seed_rows) if canonical_key(row) == key]
    if len(matches) == 1:
        return matches[0], None
    return None, "seed_match_not_unique" if matches else "seed_match_missing"


def _safe_for_field(row: dict[str, Any], item: dict[str, Any], field: str, value: Any) -> str | None:
    evidence_url = _evidence_url(item)
    if field in {"barcode", "release_date", "official_price_jpy", "sub_series", "name_ja", "character_name"}:
        if not _is_exact_evidence_url(evidence_url):
            return "exact_evidence_url_required"
        if not _store_url_compatible(row.get("source_store"), evidence_url):
            return "evidence_store_mismatch"
        if field in {"sub_series", "name_ja", "character_name"} and row.get("source_url") and not _same_url(row.get("source_url"), evidence_url):
            return "evidence_source_mismatch"
        return None
    if field == "source_url":
        if not _is_exact_evidence_url(value):
            return "exact_source_url_required"
        if not _store_url_compatible(row.get("source_store"), value):
            return "source_store_mismatch"
        if evidence_url and not _same_netloc(evidence_url, value):
            return "evidence_source_mismatch"
        return None
    if field == "image_url":
        source_url = evidence_url or row.get("source_url")
        if not _store_url_compatible(row.get("source_store"), source_url):
            return "evidence_store_mismatch"
        if _confirmed(item.get("representative_image")) and source_url and _http_url(value):
            return None
        if not source_url or not is_safe_source_image_pair(source_url, value):
            return "unsafe_source_image_pair"
    return None


def import_rows(
    review_queue: dict[str, Any],
    seed_rows: list[dict[str, Any]],
    *,
    allow_existing_overwrite: bool = False,
) -> dict[str, Any]:
    normalized_seed = [normalize_row(row) for row in seed_rows if isinstance(row, dict)]
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in review_queue.get("items") or []:
        if not isinstance(item, dict):
            continue
        if not _confirmed(item.get("manual_confirmed")):
            skipped.append({"field": item.get("field"), "name_ko": item.get("name_ko"), "reason": "manual_confirmed_false"})
            continue
        field = str(item.get("field") or "").strip()
        if field not in ALLOWED_FIELDS:
            skipped.append({"field": field, "name_ko": item.get("name_ko"), "reason": "unsupported_field"})
            continue
        value, value_error = _clean_value(field, item.get("manual_value"), item)
        if value_error:
            skipped.append({"field": field, "name_ko": item.get("name_ko"), "reason": value_error})
            continue
        seed_index, match_error = _find_seed_index(normalized_seed, item)
        if match_error or seed_index is None:
            skipped.append({"field": field, "name_ko": item.get("name_ko"), "reason": match_error})
            continue
        row = normalized_seed[seed_index]
        safety_error = _safe_for_field(row, item, field, value)
        if safety_error:
            skipped.append({"field": field, "name_ko": item.get("name_ko"), "reason": safety_error})
            continue
        existing = row.get(field)
        if existing not in (None, "", value):
            if field == "source_url" and is_generic_source_url(existing):
                pass
            elif field == "character_name" and str(existing).strip() in CHARACTER_NAME_PLACEHOLDERS:
                pass
            elif allow_existing_overwrite:
                pass
            else:
                skipped.append(
                    {
                        "field": field,
                        "name_ko": item.get("name_ko"),
                        "reason": "existing_field_conflict",
                        "existing": existing,
                        "manual_value": value,
                    }
                )
                continue
        if row.get(field) == value:
            skipped.append({"field": field, "name_ko": item.get("name_ko"), "reason": "no_change"})
            continue
        row[field] = value
        updated.append(
            {
                "row_index": seed_index,
                "field": field,
                "value": value,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_store": row.get("source_store"),
                "evidence_url": item.get("evidence_url"),
                "candidate_source_url": item.get("candidate_source_url"),
            }
        )

    return {"seed_rows": normalized_seed, "updated": updated, "skipped": skipped}


def _normalize_review_queue(raw_queue: Any) -> dict[str, Any]:
    if isinstance(raw_queue, list):
        return {"items": raw_queue}
    if isinstance(raw_queue, dict):
        if isinstance(raw_queue.get("metadata_field_import_template"), list):
            return {"items": raw_queue["metadata_field_import_template"]}
        if isinstance(raw_queue.get("items"), list):
            return raw_queue
        if raw_queue.get("field") and raw_queue.get("row_index") is not None:
            return {"items": [raw_queue]}
    raise SystemExit(
        "review queue must be an object with items, metadata_field_import_template, "
        "a list of items, or one copied item object"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--allow-existing-overwrite",
        action="store_true",
        help="Allow confirmed exact-evidence rows to replace an existing non-empty field.",
    )
    args = parser.parse_args()

    queue_path = args.queue
    if not queue_path.exists():
        fallback_name = FALLBACK_QUEUE.name if queue_path.name == DEFAULT_QUEUE.name else queue_path.with_suffix(".template.json").name
        empty_report = {
            "write": args.write,
            "queue": str(queue_path),
            "updated_rows": 0,
            "skipped_rows": 0,
            "updated": [],
            "skipped_sample": [],
            "note": f"No confirmed queue found. Copy {fallback_name} to {queue_path.name} after manual review.",
        }
        args.report.write_text(json.dumps(empty_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: empty_report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
        return 0
    review_queue = _normalize_review_queue(json.loads(queue_path.read_text(encoding="utf-8-sig")))
    seed_rows = json.loads(args.seed.read_text(encoding="utf-8-sig"))
    if not isinstance(seed_rows, list):
        raise SystemExit(f"{args.seed} must contain a JSON list")

    result = import_rows(review_queue, seed_rows, allow_existing_overwrite=args.allow_existing_overwrite)
    report = {
        "write": args.write,
        "queue": str(queue_path),
        "allow_existing_overwrite": args.allow_existing_overwrite,
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and result["updated"]:
        args.seed.write_text(json.dumps(result["seed_rows"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("updated_rows", "skipped_rows", "queue", "write")}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Copy the template, fill confirmed values, review the report, then re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
