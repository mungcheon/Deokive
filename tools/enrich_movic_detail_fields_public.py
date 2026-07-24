from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "data" / "movic_detail_field_enrichment_public.json"
MOVIC_NETLOC = "www.movic.jp"
MOVIC_STORE = "Movic"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)


def _catalog_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    raise SystemExit("catalog must be a JSON list or an object with items")


def _plain(text: Any) -> str:
    value = html.unescape(str(text or ""))
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _squash(text: Any) -> str:
    return re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", _plain(text).lower())


def _product_code_from_url(url: str) -> str:
    path = urllib.parse.urlsplit(url).path
    match = re.search(r"/shop/g/g([^/?#]+)/?", path, re.I)
    return match.group(1) if match else ""


def _is_movic_detail_url(url: Any) -> bool:
    parsed = urllib.parse.urlsplit(str(url or ""))
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == MOVIC_NETLOC and bool(
        _product_code_from_url(str(url))
    )


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": "https://www.movic.jp/"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(exc.headers.get_content_charset() or "utf-8", errors="replace")
        if exc.code == 503 and ("商品コード" in body or "JANコード" in body or "発売日" in body):
            return body
        raise


def parse_movic_detail(html_text: str) -> dict[str, Any]:
    title = ""
    match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.I)
    if match:
        title = html.unescape(match.group(1)).strip()
    if not title:
        match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.I | re.S)
        title = _plain(match.group(1)) if match else ""
    text = _plain(html_text)

    release_date = None
    match = re.search(r"発売日\s*([0-9]{4})[/-]([0-9]{1,2})[/-]([0-9]{1,2})", text)
    if match:
        release_date = f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

    price_jpy = None
    match = re.search(r"([0-9][0-9,]*)円", text)
    if match:
        price_jpy = int(match.group(1).replace(",", ""))

    barcode = None
    match = re.search(r"JANコード[:：]?\s*([0-9]{8,14})", text)
    if match:
        barcode = match.group(1)

    product_code = None
    match = re.search(r"商品コード\s*([0-9A-Za-z-]+)", text)
    if match:
        product_code = match.group(1)

    image_url = None
    match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.I)
    if match:
        image_url = html.unescape(match.group(1)).strip()
    if image_url and image_url.startswith("//"):
        image_url = "https:" + image_url

    return {
        "title": title,
        "release_date": release_date,
        "official_price_jpy": price_jpy,
        "barcode": barcode,
        "product_code": product_code,
        "image_url": image_url,
    }


def _row_matches_page(row: dict[str, Any], page: dict[str, Any], url_code: str) -> tuple[bool, str | None]:
    page_code = str(page.get("product_code") or "")
    if page_code and page_code != url_code:
        return False, "product_code_mismatch"

    image_path = urllib.parse.urlsplit(str(row.get("image_url") or "")).path
    if url_code and url_code.lower() in image_path.lower():
        return True, None

    row_key = _squash(row.get("name_ja") or row.get("name_ko"))
    title_key = _squash(page.get("title"))
    if row_key and title_key and (row_key in title_key or title_key in row_key):
        return True, None

    tokens = [
        _squash(part)
        for part in re.split(r"[\s/／()（）・]+", str(row.get("name_ja") or row.get("name_ko") or ""))
        if len(_squash(part)) >= 2
    ]
    matched = [token for token in tokens if token in title_key]
    if len(matched) >= 2:
        return True, None
    return False, "title_or_image_identity_mismatch"


def enrich(rows: list[dict[str, Any]], *, limit: int | None = None, update_price_conflicts: bool = False) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    price_conflicts: list[dict[str, Any]] = []
    fetched = 0

    for index, row in enumerate(rows):
        if limit is not None and fetched >= limit:
            break
        url = str(row.get("source_url") or "").strip()
        if row.get("source_store") != MOVIC_STORE or not _is_movic_detail_url(url):
            continue
        if row.get("release_date") and row.get("barcode") and row.get("official_price_jpy") not in (None, ""):
            continue

        url_code = _product_code_from_url(url)
        try:
            page = parse_movic_detail(_fetch(url))
            fetched += 1
        except urllib.error.HTTPError as exc:
            reason = f"http_error_{exc.code}"
            if exc.code == 503:
                reason = "movic_http_503_blocked_or_waiting_room"
            rejected.append({"row_index": index, "catalog_index": row.get("catalog_index"), "source_url": url, "reason": reason})
            continue
        except Exception as exc:
            rejected.append({"row_index": index, "catalog_index": row.get("catalog_index"), "source_url": url, "reason": str(exc)})
            continue

        matched, reason = _row_matches_page(row, page, url_code)
        if not matched:
            rejected.append(
                {
                    "row_index": index,
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_url": url,
                    "page_title": page.get("title"),
                    "reason": reason,
                }
            )
            continue

        row_changes: dict[str, Any] = {}
        for field in ("release_date", "barcode"):
            value = page.get(field)
            if value and row.get(field) in (None, ""):
                row_changes[field] = value

        page_price = page.get("official_price_jpy")
        existing_price = row.get("official_price_jpy")
        if page_price is not None:
            if existing_price in (None, ""):
                row_changes["official_price_jpy"] = page_price
            elif int(existing_price) != int(page_price):
                price_conflicts.append(
                    {
                        "row_index": index,
                        "catalog_index": row.get("catalog_index"),
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                        "source_url": url,
                        "existing_official_price_jpy": existing_price,
                        "page_official_price_jpy": page_price,
                    }
                )
                if update_price_conflicts:
                    row_changes["official_price_jpy"] = page_price

        if row_changes:
            row.update(row_changes)
            changes.append(
                {
                    "row_index": index,
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_url": url,
                    "page_title": page.get("title"),
                    "fields": row_changes,
                }
            )

    return {
        "fetched_pages": fetched,
        "changes": changes,
        "rejected": rejected,
        "price_conflicts": price_conflicts,
    }


def _refresh_meta(payload: Any, rows: list[dict[str, Any]]) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("meta"), dict):
        return
    missing: dict[str, int] = {}
    for field in payload["meta"].get("fields") or []:
        missing[field] = sum(1 for row in rows if row.get(field) in (None, ""))
    payload["meta"]["missing"] = missing
    payload["meta"]["row_count"] = len(rows)
    payload["meta"]["total_items"] = len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--update-price-conflicts", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    rows = _catalog_rows(payload)
    result = enrich(rows, limit=args.limit, update_price_conflicts=args.update_price_conflicts)
    if args.write and result["changes"]:
        _refresh_meta(payload, rows)
        args.input.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    report = {
        "write": args.write,
        "updated_rows": len(result["changes"]) if args.write else 0,
        "change_candidates": len(result["changes"]),
        "fetched_pages": result["fetched_pages"],
        "price_conflict_rows": len(result["price_conflicts"]),
        "rejected_rows": len(result["rejected"]),
        "rejected_reason_counts": dict(Counter(item.get("reason") for item in result["rejected"])),
        "changes": result["changes"],
        "price_conflicts": result["price_conflicts"],
        "rejected": result["rejected"],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("write", "updated_rows", "change_candidates", "fetched_pages", "price_conflict_rows", "rejected_rows")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
