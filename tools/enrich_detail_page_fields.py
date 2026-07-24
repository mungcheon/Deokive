from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any

from enrich_catalog_images import _score
from image_enrichment_safety import is_product_specific_source_url

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "detail_page_field_enrichment_report.json"
ANIMATE_STORE = "\uc560\ub2c8\uba54\uc774\ud2b8"
ENSKY_STORE = "\uc5d4\uc2a4\uce74\uc774"
KOTOBUKIYA_STORE = "\ucf54\ud1a0\ubd80\ud0a4\uc57c"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _fetch_text(url: str) -> str | None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Referer": "https://www.kotobukiya.co.jp/" if "kotobukiya.co.jp/" in url else "",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                return None
            return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return None


def _plain(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value))).strip()


def _title(source: str) -> str:
    match = TITLE_RE.search(source)
    return _plain(match.group(1)) if match else ""


def _tokens(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return {
        token
        for token in re.split(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff\uac00-\ud7a3]+", text)
        if len(token) >= 2
    }


def _distinctive_tokens(value: Any) -> set[str]:
    generic = {
        "アニメ",
        "グッズ",
        "トレーディング",
        "ランダム",
        "再販",
        "セット",
        "ver",
        "vol",
        "the",
        "tv",
    }
    return {token for token in _tokens(value) if token not in generic and not token.isdigit()}


def _ascii_tokens(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return {token for token in re.split(r"[^0-9a-z]+", text) if len(token) >= 2}


def _safe_title_match(row: dict[str, Any], detail_title: str) -> bool:
    detail_tokens = _distinctive_tokens(detail_title)
    if not detail_tokens:
        return False
    name_ja = str(row.get("name_ja") or "").strip()
    if name_ja:
        query_tokens = _distinctive_tokens(name_ja)
        if len(query_tokens) >= 2:
            covered = {
                query_token
                for query_token in query_tokens
                if any(query_token == detail_token or query_token in detail_token or detail_token in query_token for detail_token in detail_tokens)
            }
            return query_tokens <= detail_tokens or covered == query_tokens
        if len(query_tokens) == 1:
            query_token = next(iter(query_tokens))
            return any(
                query_token == detail_token or query_token in detail_token or detail_token in query_token
                for detail_token in detail_tokens
            )

    query = str(row.get("name_ko") or "").strip()
    if not query or not detail_title:
        return False
    # Korean-only titles cannot be safely compared with Japanese detail pages.
    # Allow only shared ASCII/number identity such as SPY×FAMILY, Re:Zero, or V3.
    ascii_query = _ascii_tokens(query)
    if not ascii_query:
        return False
    ascii_title = _ascii_tokens(detail_title)
    if not (ascii_query & ascii_title):
        return False
    overlap, ratio = _score(query, detail_title)
    return (overlap >= 2 and ratio >= 0.72) or (overlap >= 4 and ratio >= 0.66)


def _animate_barcode(source: str) -> str | None:
    match = re.search(r"JAN\s*\u30b3\u30fc\u30c9\s*[:\uff1a]\s*(\d{13})", source)
    if not match:
        match = re.search(r"JAN[^0-9]{0,30}(\d{13})", source)
    if not match:
        return None
    barcode = match.group(1)
    return barcode if barcode.startswith(("45", "49")) else None


def _animate_release_date(source: str) -> str | None:
    plain = _plain(source)
    patterns = (
        r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\s*(?:発売|発売予定)",
        r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(?:発売|発売予定)",
    )
    for pattern in patterns:
        match = re.search(pattern, plain)
        if match:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    return None


def _animate_price_jpy(source: str) -> int | None:
    plain = _plain(source)
    match = re.search(r"(?:販売価格|価格)[^0-9]{0,80}([0-9,]{2,8})\s*円", plain)
    if not match:
        return None
    price = int(match.group(1).replace(",", ""))
    return price if 1 <= price <= 1_000_000 else None


def _ensky_barcode(source: str) -> str | None:
    match = re.search(r"\u5546\u54c1\u30b3\u30fc\u30c9[^0-9]{0,120}(\d{13})", source)
    if not match:
        match = re.search(r"product_code[\"']?\s*:\s*[\"'](\d{13})", source)
    if not match:
        return None
    barcode = match.group(1)
    return barcode if barcode.startswith(("45", "49")) else None


def _ensky_release_date(source: str) -> str | None:
    match = re.search(r"\u521d\u56de\u51fa\u8377\u958b\u59cb\u65e5[^0-9]{0,80}(20\d{2})\u5e74\s*(\d{1,2})\u6708", source)
    if not match:
        match = re.search(r"(20\d{2})\u5e74\s*(\d{1,2})\u6708", _title(source))
    if not match:
        return None
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"


def _kotobukiya_barcode(source_url: str) -> str | None:
    match = re.search(r"/p(\d{13})/?$", source_url)
    if not match:
        return None
    barcode = match.group(1)
    return barcode if barcode.startswith(("45", "49")) else None


def _kotobukiya_release_date(source: str) -> str | None:
    plain = _plain(source)
    for label in ("\u521d\u56de\u767a\u58f2\u6708", "\u767a\u58f2\u6708"):
        match = re.search(label + r"[^0-9]{0,80}(20\d{2})\u5e74\s*(\d{1,2})\u6708", plain)
        if match:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"
    return None


def _kotobukiya_price_jpy(source: str) -> int | None:
    plain = _plain(source)
    match = re.search(r"\u4fa1\u683c[^0-9]{0,80}([0-9,]{3,8})\s*\u5186\uff08\u7a0e\u8fbc\uff09", plain)
    if not match:
        return None
    price = int(match.group(1).replace(",", ""))
    return price if 1 <= price <= 1_000_000 else None


def _supported_store_source(store: str, source_url: str) -> bool:
    if store == ANIMATE_STORE:
        return "animate-onlineshop.jp/" in source_url
    if store == ENSKY_STORE:
        return "enskyshop.com/products/detail/" in source_url
    if store == KOTOBUKIYA_STORE:
        return "kotobukiya.co.jp/product/detail/p" in source_url
    return False


def _extract_fields(store: str, source: str, source_url: str = "") -> dict[str, Any]:
    if store == ANIMATE_STORE:
        return {
            "barcode": _animate_barcode(source),
            "release_date": _animate_release_date(source),
            "official_price_jpy": _animate_price_jpy(source),
        }
    if store == ENSKY_STORE:
        return {"barcode": _ensky_barcode(source), "release_date": _ensky_release_date(source)}
    if store == KOTOBUKIYA_STORE:
        return {
            "barcode": _kotobukiya_barcode(source_url),
            "release_date": _kotobukiya_release_date(source),
            "official_price_jpy": _kotobukiya_price_jpy(source),
        }
    return {}


def _row_contains(row: dict[str, Any], filters: list[str] | None = None) -> bool:
    filters = [item.lower() for item in (filters or []) if item]
    if not filters:
        return True
    haystack = " ".join(
        str(row.get(field) or "")
        for field in (
            "name_ko",
            "name_ja",
            "name_en",
            "category",
            "character_name",
            "affiliation",
            "series_name",
            "sub_series",
            "source_store",
        )
    ).lower()
    return any(item in haystack for item in filters)


def enrich(
    rows: list[dict[str, Any]],
    max_rows: int | None = None,
    filter_text: list[str] | None = None,
) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    updated = 0
    processed = 0
    changes: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    cache: dict[str, str | None] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _row_contains(row, filter_text):
            continue
        if row.get("barcode") and row.get("release_date") and row.get("official_price_jpy"):
            continue
        store = str(row.get("source_store") or "")
        source_url = str(row.get("source_url") or "").strip()
        if not _supported_store_source(store, source_url):
            continue
        if not is_product_specific_source_url(source_url):
            continue
        if max_rows is not None and processed >= max_rows:
            break
        processed += 1

        if source_url not in cache:
            cache[source_url] = _fetch_text(source_url)
            time.sleep(0.08)
        source = cache[source_url]
        if not source:
            rejected.append({"name_ko": row.get("name_ko"), "source_url": source_url, "reason": "fetch_failed"})
            continue
        detail_title = _title(source)
        if not _safe_title_match(row, detail_title):
            rejected.append(
                {
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_url": source_url,
                    "detail_title": detail_title,
                    "score": _score(str(row.get("name_ja") or row.get("name_ko") or ""), detail_title),
                }
            )
            continue
        fields = _extract_fields(store, source, source_url)
        changed_fields: list[str] = []
        barcode = fields.get("barcode")
        if barcode and not row.get("barcode"):
            row["barcode"] = barcode
            changed_fields.append("barcode")
        release_date = fields.get("release_date")
        if release_date and not row.get("release_date"):
            row["release_date"] = release_date
            changed_fields.append("release_date")
        price = fields.get("official_price_jpy")
        if price is not None and row.get("official_price_jpy") in (None, ""):
            row["official_price_jpy"] = price
            changed_fields.append("official_price_jpy")
        if not changed_fields:
            rejected.append({"name_ko": row.get("name_ko"), "source_url": source_url, "reason": "fields_not_found_or_already_filled"})
            continue

        updated += 1
        changes.append(
            {
                "name_ko": row.get("name_ko"),
                "source_store": store,
                "fields": changed_fields,
                "barcode": row.get("barcode"),
                "release_date": row.get("release_date"),
                "official_price_jpy": row.get("official_price_jpy"),
                "source_url": source_url,
                "detail_title": detail_title,
            }
        )
    return updated, changes, rejected


def load_catalog(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], None
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)], payload
    raise SystemExit(f"{path} must contain a JSON list or a catalog object with items")


def refresh_meta(payload: dict[str, Any] | None, rows: list[dict[str, Any]]) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("meta"), dict):
        return
    fields = payload["meta"].get("fields") or []
    payload["meta"]["missing"] = {
        field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields
    }
    payload["meta"]["row_count"] = len(rows)
    payload["meta"]["total_items"] = len(rows)
    payload["total_items"] = len(rows)


def write_catalog(path: Path, rows: list[dict[str, Any]], wrapper: dict[str, Any] | None) -> None:
    if wrapper is None:
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    wrapper["items"] = rows
    refresh_meta(wrapper, rows)
    path.write_text(json.dumps(wrapper, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument(
        "--filter-text",
        action="append",
        default=[],
        help="Only process rows whose text fields contain this value. Repeat for OR matching.",
    )
    args = parser.parse_args()

    rows, wrapper = load_catalog(args.input)
    updated, changes, rejected = enrich(rows, args.max_rows, args.filter_text)
    args.report.write_text(
        json.dumps(
            {
                "updated_rows": updated,
                "write": args.write,
                "filter_text": args.filter_text,
                "changes": changes,
                "rejected_sample": rejected[:200],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if args.write and changes:
        write_catalog(args.input, rows, wrapper)
    print(json.dumps({"updated_rows": updated, "report": str(args.report), "write": args.write}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to update the seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
