from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "goodsmile_com_exact_candidate_report.json"
DEFAULT_CANDIDATES = ROOT / "server" / "goodsmile_com_exact_image_candidates.json"

GOODSMILE_STORE = "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8"
BASE_URL = "https://www.goodsmile.com"
SEARCH_LIST_URL = BASE_URL + "/ja/search/list"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

# goodsmile.com category ids observed from the public search page.
CATEGORY_IDS = {
    "pop_up_parade": 12,
    "nendoroid": 6,
}


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(str(value or ""))).lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _absolute(value: Any) -> str:
    return urllib.parse.urljoin(BASE_URL, html.unescape(str(value or "").strip()))


def _category_for_name(name: str) -> int | None:
    if name.startswith("POP UP PARADE "):
        return CATEGORY_IDS["pop_up_parade"]
    if name.startswith("\u306d\u3093\u3069\u308d\u3044\u3069 "):
        return CATEGORY_IDS["nendoroid"]
    return None


def _fetch_category_page(category_id: int, offset: int, *, limit: int = 60) -> str:
    search_filter = {
        "search_keyword": "",
        "search_over18": False,
        "search_category": [category_id],
        "search_maker": [],
        "search_title": [],
        "search_status": "",
        "release_date_from": "",
        "release_date_to": "",
        "search_bonus": False,
        "search_exclusive": False,
        "search_sale": False,
        "search_sales_origin": False,
        "tag": [],
    }
    params = {
        "filter": json.dumps(search_filter, ensure_ascii=False, separators=(",", ":")),
        "orderBy": "1",
        "limit": str(limit),
        "offset": str(offset),
        "couponId": "null",
        "searchIndex": "-1",
    }
    url = SEARCH_LIST_URL + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en-US;q=0.8,en;q=0.7",
            "Referer": BASE_URL + "/ja/search",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def _items_from_html(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    blocks = re.findall(
        r'<div class="p-product-list__item">(.*?)(?=<div class="p-product-list__item">'
        r'|<div style="display: none" id="search_result_total_count"|$)',
        text,
        re.S,
    )
    for block in blocks:
        title_match = re.search(r'<div class="b-product-item__title">\s*<h2[^>]*>(.*?)</h2>', block, re.S)
        href_match = re.search(r'<a class="p-product-list__link" href="([^"]+)"', block)
        image_match = re.search(r'<figure class="b-product-item__image">.*?<img src="([^"]+)"', block, re.S)
        price_match = re.search(r'<span class="c-price__main">([^<]+)</span>', block)
        if not title_match or not href_match or not image_match:
            continue
        title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title_match.group(1)))).strip()
        items.append(
            {
                "title": title,
                "source_url": _absolute(href_match.group(1)),
                "image_url": _absolute(image_match.group(1)),
                "price": html.unescape(price_match.group(1)).strip() if price_match else None,
            }
        )
    return items


def _total_count(text: str) -> int:
    match = re.search(r'id="search_result_total_count">([^<]+)', text)
    if not match:
        return 0
    try:
        return int(match.group(1))
    except ValueError:
        return 0


def fetch_category_catalog(category_id: int) -> dict[str, list[dict[str, Any]]]:
    by_title: dict[str, list[dict[str, Any]]] = {}
    total = None
    offset = 0
    limit = 60
    while True:
        text = _fetch_category_page(category_id, offset, limit=limit)
        if total is None:
            total = _total_count(text)
        for item in _items_from_html(text):
            by_title.setdefault(_norm(item["title"]), []).append(item)
        offset += limit
        if not total or offset >= total:
            break
        time.sleep(0.05)
    return by_title


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if (
            isinstance(row, dict)
            and row.get("source_store") == GOODSMILE_STORE
            and not row.get("image_url")
        ):
            name = str(row.get("name_ja") or row.get("name_ko") or "").strip()
            category_id = _category_for_name(name)
            if category_id is not None:
                targets.append({"row_index": index, "name": name, "category_id": category_id, "row": row})

    catalogs: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for category_id in sorted({target["category_id"] for target in targets}):
        catalogs[category_id] = fetch_category_catalog(category_id)

    exact_matches: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for target in targets:
        row = target["row"]
        matches = catalogs[target["category_id"]].get(_norm(target["name"]), [])
        if len(matches) == 1:
            match = matches[0]
            exact_matches.append(
                {
                    "row_index": target["row_index"],
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "category": row.get("category"),
                    "affiliation": row.get("affiliation"),
                    "candidate_title": match["title"],
                    "candidate_source_url": match["source_url"],
                    "candidate_image_url": match["image_url"],
                    "candidate_price": match.get("price"),
                }
            )
        elif len(matches) > 1:
            ambiguous.append(
                {
                    "row_index": target["row_index"],
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "match_count": len(matches),
                    "matches": matches[:5],
                }
            )
        else:
            missing.append({"row_index": target["row_index"], "name_ko": row.get("name_ko"), "name_ja": row.get("name_ja")})

    return {
        "source": SEARCH_LIST_URL,
        "target_rows": len(targets),
        "exact_match_rows": len(exact_matches),
        "ambiguous_rows": len(ambiguous),
        "missing_rows": len(missing),
        "exact_matches": exact_matches,
        "ambiguous": ambiguous,
        "missing_sample": missing[:100],
    }


def build_import_candidates(report: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for match in report.get("exact_matches") or []:
        if not isinstance(match, dict):
            skipped.append({"reason": "invalid_match"})
            continue
        source_url = str(match.get("candidate_source_url") or "").strip()
        image_url = str(match.get("candidate_image_url") or "").strip()
        if not source_url or not image_url:
            skipped.append(
                {
                    "row_index": match.get("row_index"),
                    "name_ko": match.get("name_ko"),
                    "reason": "missing_source_or_image_url",
                }
            )
            continue
        items.append(
            {
                "row_index": match.get("row_index"),
                "name_ko": match.get("name_ko"),
                "name_ja": match.get("name_ja"),
                "source_store": GOODSMILE_STORE,
                "source_kind": "official_manufacturer_page",
                "confidence": 0.94,
                "source_url": source_url,
                "image_url": image_url,
                "candidate_title": match.get("candidate_title") or match.get("name_ja") or match.get("name_ko"),
                "manual_confirmed": True,
                "evidence": "Exact title match from the official Good Smile category catalog.",
            }
        )

    return {
        "source_report": str(report.get("source") or ""),
        "items": items,
        "summary": {
            "exact_match_rows": len(report.get("exact_matches") or []),
            "candidate_items": len(items),
            "skipped_items": len(skipped),
        },
        "skipped_sample": skipped[:100],
    }


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{path} must contain a JSON list or a catalog object with items")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--candidates-output",
        type=Path,
        default=None,
        help="Write import_manual_image_candidates.py-compatible rows for exact matches.",
    )
    args = parser.parse_args()

    rows = _load_rows(args.input)
    report = build_report(rows)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    candidates_path = args.candidates_output
    if candidates_path is not None:
        candidates_path.write_text(
            json.dumps(build_import_candidates(report), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "target_rows": report["target_rows"],
                "exact_match_rows": report["exact_match_rows"],
                "ambiguous_rows": report["ambiguous_rows"],
                "missing_rows": report["missing_rows"],
                "report": str(args.report),
                "candidates_output": str(candidates_path) if candidates_path is not None else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
