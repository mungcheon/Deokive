from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import requests

from image_enrichment_safety import is_safe_source_image_pair

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DEFAULT_QUEUE = SERVER / "catalog_source_discovery_queue.json"
DEFAULT_JSON = SERVER / "catalog_source_detail_candidates.json"
DEFAULT_MD = SERVER / "catalog_source_detail_candidates.md"
ENSKY_STORE = "\uc5d4\uc2a4\uce74\uc774"
ANIMATE_STORE = "\uc560\ub2c8\uba54\uc774\ud2b8"
GOODSMILE_STORE = "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8"
FURYU_STORE = "FuRyu"
TAITO_STORE = "Taito"
REMENT_STORE = "Re-ment"
AMIAMI_STORE = "AmiAmi"
MOVIC_STORE = "Movic"
KOTOBUKIYA_STORE = "\ucf54\ud1a0\ubd80\ud0a4\uc57c"
SUPPORTED_PROVIDER_STORES = {
    "Cospa",
    ENSKY_STORE,
    ANIMATE_STORE,
    GOODSMILE_STORE,
    FURYU_STORE,
    TAITO_STORE,
    REMENT_STORE,
    AMIAMI_STORE,
    MOVIC_STORE,
    KOTOBUKIYA_STORE,
}
API_PROVIDER_STORES = {FURYU_STORE, TAITO_STORE, REMENT_STORE}
REMENT_CATALOG_URL = "https://www.re-ment.co.jp/product/search.php?s="
_REMENT_CATALOG_CACHE: list[dict[str, Any]] | None = None
_TAITO_SESSION: requests.Session | None = None
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
GENERIC_GOODS_TOKENS = {
    "acrylic",
    "stand",
    "badge",
    "can",
    "pop",
    "up",
    "parade",
    "keyholder",
    "mascot",
    "strap",
    "rubber",
    "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
    "\u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
    "\u30e1\u30bf\u30ea\u30c3\u30af\u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
    "\u30b9\u30bf\u30f3\u30c9\u30dd\u30c3\u30d7",
    "\u30a2\u30af\u30ea\u30eb\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
    "\u30a2\u30af\u30ea\u30eb\u30ad\u30fc\u30c1\u30a7\u30fc\u30f3",
    "\u30d0\u30c3\u30c1",
    "\u304a\u307e\u3093\u3058\u3085\u3046\u306b\u304e\u306b\u304e\u30de\u30b9\u30b3\u30c3\u30c8",
    "\u30de\u30b9\u30b3\u30c3\u30c8",
    "\u306c\u3044\u3050\u308b\u307f",
    "\u30d5\u30a3\u30ae\u30e5\u30a2",
    "\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
    "\u7f36\u30d0\u30c3\u30b8",
    "\uc544\ud06c\ub9b4",
    "\uc2a4\ud0e0\ub4dc",
    "\ub7ec\ubc84",
    "\uc2a4\ud2b8\ub7a9",
    "\ub9c8\uc2a4\ucf54\ud2b8",
    "\uce94\ubc43\uc9c0",
    "\ubc43\uc9c0",
    "\ubc30\uc9c0",
    "\ud0a4\ud640\ub354",
}


class RateLimitError(RuntimeError):
    pass


class ProviderTemporaryUnavailable(RuntimeError):
    pass


WAITING_ROOM_MARKERS = {
    "ただいま大変混みあっております",
    "ただいま大変混みあっており接続しづらい状況",
    "待ち人数",
    "想定待ち時間",
}


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimitError("HTTP Error 429: Too Many Requests") from exc
        raise


def _raise_if_provider_waiting_room(source_store: str, source_html: str) -> None:
    if source_store == MOVIC_STORE and any(marker in source_html for marker in WAITING_ROOM_MARKERS):
        raise ProviderTemporaryUnavailable("provider waiting room or temporary traffic block")


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimitError("HTTP Error 429: Too Many Requests") from exc
        raise


def _fetch_taito_json(url: str) -> Any:
    global _TAITO_SESSION
    if _TAITO_SESSION is None:
        _TAITO_SESSION = requests.Session()
        _TAITO_SESSION.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
            }
        )
        _TAITO_SESSION.get("https://www.taito.co.jp/prize", timeout=25)
    response = _TAITO_SESSION.get(
        url,
        timeout=25,
        headers={
            "Referer": "https://www.taito.co.jp/prize",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    if response.status_code == 429:
        raise RateLimitError("HTTP Error 429: Too Many Requests")
    response.raise_for_status()
    return response.json()


def _plain(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value))).strip()


def _tokens(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return {
        token
        for token in re.split(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff\uac00-\ud7a3]+", text)
        if len(token) >= 2
    }


def _distinctive_tokens(value: Any) -> set[str]:
    return {token for token in _tokens(value) if token not in GENERIC_GOODS_TOKENS}


def _goods_type_tokens(value: Any) -> set[str]:
    return _tokens(value) & GENERIC_GOODS_TOKENS


def _goods_type_compatible(query: str, title: str) -> bool:
    query_goods = _goods_type_tokens(query)
    if not query_goods:
        return True
    return bool(query_goods & _goods_type_tokens(title))


def _token_score(query: str, title: str) -> tuple[float, list[str]]:
    query_tokens = _distinctive_tokens(query)
    title_tokens = _distinctive_tokens(title)
    if not query_tokens or not title_tokens:
        return 0.0, []
    shared = sorted(query_tokens & title_tokens)
    return len(shared) / len(query_tokens), shared


def _item_query(item: dict[str, Any]) -> str:
    return str(item.get("query") or item.get("search_query") or item.get("name_ja") or item.get("name_ko") or "")


def _cospa_candidates(source_html: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    pattern = re.compile(
        r'<a[^>]+href="([^"]*/cospa/detail/id/\d+)"[^>]+title="([^"]+)"[^>]*>\s*'
        r'<img[^>]+src="([^"]+)"[^>]+class="item-tn"',
        re.S,
    )
    seen: set[str] = set()
    for link, title_raw, image_raw in pattern.findall(source_html):
        source_url = html.unescape(link)
        if source_url in seen:
            continue
        seen.add(source_url)
        title = _plain(title_raw)
        image_url = html.unescape(image_raw)
        candidates.append({"candidate_source_url": source_url, "candidate_title": title, "candidate_image_url": image_url})
    return candidates


def _ensky_candidates(source_html: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    pattern = re.compile(
        r'<div class="tabBox_item[^"]*"[^>]*>.*?'
        r'<a href="(https://www\.enskyshop\.com/products/detail/\d+)">\s*'
        r'<picture>\s*<source srcset="([^"]+)"[^>]*>.*?'
        r'<a href="https://www\.enskyshop\.com/products/detail/\d+"><span>(.*?)</span></a>',
        re.S,
    )
    seen: set[str] = set()
    for link, image_raw, title_raw in pattern.findall(source_html):
        source_url = html.unescape(link)
        if source_url in seen:
            continue
        seen.add(source_url)
        image_url = urllib.parse.urljoin(source_url, html.unescape(image_raw))
        title = _plain(title_raw)
        candidates.append({"candidate_source_url": source_url, "candidate_title": title, "candidate_image_url": image_url})
    return candidates


def _attr_value(attrs: str, name: str) -> str:
    match = re.search(rf"""{name}\s*=\s*(["'])(.*?)\1""", attrs, re.I | re.S)
    return html.unescape(match.group(2)).strip() if match else ""


def _animate_candidates(source_html: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    pattern = re.compile(
        r'<div class="item_list_thumb">\s*'
        r'<a href="(?P<thumb_link>[^"]+)">\s*'
        r'<img(?P<img_attrs>[^>]+src="(?P<image>[^"]+)"[^>]*)>\s*</a>\s*</div>\s*'
        r'<h3>\s*<a href="(?P<title_link>[^"]+)"(?P<a_attrs>[^>]*)>(?P<title_html>.*?)</a>\s*</h3>',
        re.S,
    )
    seen: set[str] = set()
    for match in pattern.finditer(source_html):
        link = match.group("title_link") or match.group("thumb_link")
        source_url = urllib.parse.urljoin("https://www.animate-onlineshop.jp/", html.unescape(link))
        if not re.search(r"animate-onlineshop\.jp/(?:products/detail\.php\?product_id=\d+|(?:sphone/)?pn/.*/pd/\d+/?)", source_url):
            continue
        if source_url in seen:
            continue
        seen.add(source_url)
        image_url = urllib.parse.urljoin("https://www.animate-onlineshop.jp/", html.unescape(match.group("image")))
        title = _attr_value(match.group("a_attrs"), "title") or _attr_value(match.group("img_attrs"), "title")
        if not title:
            title = _plain(match.group("title_html"))
        candidates.append({"candidate_source_url": source_url, "candidate_title": title, "candidate_image_url": image_url})
    return candidates


def _goodsmile_info_candidates(source_html: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    blocks = re.findall(
        r'<div\s+class=["\'][^"\']*\bhitItem\b[^"\']*["\']>\s*'
        r'<div\s+class=["\'][^"\']*\bhitBox\b[^"\']*["\']>(.*?)</div>\s*</div>',
        source_html,
        re.I | re.S,
    )
    seen: set[str] = set()
    for block in blocks:
        href_match = re.search(r'<a[^>]+href=["\']([^"\']*/ja/product/\d+[^"\']*)["\']', block, re.I)
        image_match = re.search(r'<img[^>]+data-original=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*\bitemImg\b', block, re.I | re.S)
        if image_match is None:
            image_match = re.search(r'<img[^>]+class=["\'][^"\']*\bitemImg\b[^>]+data-original=["\']([^"\']+)["\']', block, re.I | re.S)
        title_match = re.search(r'<span class="hitTtl">\s*<span>(.*?)</span>\s*</span>', block, re.I | re.S)
        if href_match is None or image_match is None or title_match is None:
            continue
        source_url = urllib.parse.urljoin("https://www.goodsmile.info", html.unescape(href_match.group(1)))
        if source_url in seen:
            continue
        seen.add(source_url)
        image_url = urllib.parse.urljoin("https://www.goodsmile.info", html.unescape(image_match.group(1)))
        title = _plain(title_match.group(1))
        candidates.append({"candidate_source_url": source_url, "candidate_title": title, "candidate_image_url": image_url})
    return candidates


def _furyu_candidates(query: str) -> list[dict[str, Any]]:
    url = "https://furyuprize.com/api/search?keyword={query}&page=1".format(query=urllib.parse.quote(query))
    payload = _fetch_json(url)
    items = payload.get("items") if isinstance(payload, dict) else []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not isinstance(items, list):
        return candidates
    for item in items:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        title = str(item.get("name_item") or "").strip()
        image_url = str(item.get("img_item_main") or "").strip()
        if image_url.startswith("/"):
            image_url = "https://furyuprize.com/files/images/" + image_url.lstrip("/")
        if not code or not title or not image_url:
            continue
        source_url = f"https://furyuprize.com/item/{code}"
        if source_url in seen:
            continue
        seen.add(source_url)
        candidates.append({"candidate_source_url": source_url, "candidate_title": title, "candidate_image_url": image_url})
    return candidates


def _taito_candidates(query: str) -> list[dict[str, Any]]:
    url = (
        "https://www.taito.co.jp/api/Prize/?keyword={query}&storeID=&offset=0&limit=30"
        "&sortName=TaitoPrizeRank&isDesc=true"
    ).format(query=urllib.parse.quote(query))
    payload = _fetch_taito_json(url)
    raw_items: Any = payload
    if isinstance(payload, dict):
        raw_items = payload.get("data") or payload.get("items") or payload.get("Products") or payload
    if isinstance(raw_items, dict):
        for key in ("ProductList", "list", "results"):
            if isinstance(raw_items.get(key), list):
                raw_items = raw_items[key]
                break
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not isinstance(raw_items, list):
        return candidates
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        base_data = item.get("BaseShoppingProductData")
        if not isinstance(base_data, dict):
            base_data = {}
        title = str(
            item.get("ProductName")
            or base_data.get("ProductName")
            or item.get("Name")
            or item.get("name")
            or item.get("Title")
            or ""
        ).strip()
        product_id = str(
            item.get("ProductID") or base_data.get("ProductID") or item.get("Id") or item.get("id") or ""
        ).strip()
        image_path = str(item.get("ImagePath") or base_data.get("ImagePath") or item.get("imagePath") or "").strip()
        image_name = str(
            item.get("ImageName01") or base_data.get("ImageName01") or item.get("ImageName") or item.get("image") or ""
        ).strip()
        if image_path and not image_path.startswith(("http://", "https://", "//", "/")):
            image_path = f"https://{image_path}"
        image_url = urllib.parse.urljoin("https://www.taito.co.jp", image_path + image_name) if image_path or image_name else ""
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        if not title or not product_id or not image_url:
            continue
        source_url = f"https://www.taito.co.jp/prize/item/{product_id}"
        if source_url in seen:
            continue
        seen.add(source_url)
        candidates.append({"candidate_source_url": source_url, "candidate_title": title, "candidate_image_url": image_url})
    return candidates


def _rement_candidates(source_html: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for href, body in re.findall(r'<a\s+href=["\']([^"\']*r\d+[^"\']*)["\'][^>]*>(.*?)</a>', source_html, re.I | re.S):
        title_match = re.search(r'<p\s+class=["\']name["\']>(.*?)</p>', body, re.I | re.S)
        image_match = re.search(r'data-original=["\']([^"\']+)["\']', body, re.I)
        if not title_match or not image_match:
            continue
        source_url = urllib.parse.urljoin("https://www.re-ment.co.jp/product/search.php", html.unescape(href))
        if source_url in seen:
            continue
        seen.add(source_url)
        image_url = urllib.parse.urljoin(source_url, html.unescape(image_match.group(1)))
        candidates.append(
            {
                "candidate_source_url": source_url,
                "candidate_title": _plain(title_match.group(1)),
                "candidate_image_url": image_url,
            }
        )
    return candidates


def _rement_catalog_candidates() -> list[dict[str, Any]]:
    global _REMENT_CATALOG_CACHE
    if _REMENT_CATALOG_CACHE is None:
        _REMENT_CATALOG_CACHE = _rement_candidates(_fetch_text(REMENT_CATALOG_URL))
    return list(_REMENT_CATALOG_CACHE)


def _amiami_candidates(source_html: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    starts = [match.start() for match in re.finditer(r'<div class="product_box">', source_html)]
    starts.append(len(source_html))
    seen: set[str] = set()
    for offset, end in zip(starts, starts[1:]):
        block = source_html[offset:end]
        href_match = re.search(r'href="([^"]*top/detail/detail\?gcode=[^"]+)"', block)
        title_match = re.search(r'<div class="product_name_inner">(.*?)</div>', block, re.S)
        image_match = re.search(r'data-src="([^"]+)"', block)
        if not href_match or not title_match or not image_match:
            continue
        source_url = html.unescape(href_match.group(1))
        if source_url.startswith("/"):
            source_url = urllib.parse.urljoin("https://www.amiami.jp", source_url)
        if source_url in seen:
            continue
        seen.add(source_url)
        title_text = re.sub(r"<!--.*?-->", "", title_match.group(1), flags=re.S)
        image_url = html.unescape(image_match.group(1)).replace("/thumb80/", "/thumb300/")
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        candidates.append(
            {
                "candidate_source_url": source_url,
                "candidate_title": _plain(title_text),
                "candidate_image_url": image_url,
            }
        )
    return candidates


def _goods_search_candidates(source_html: str, base_url: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    blocks = re.findall(
        r'<(?:li|div)[^>]+class=["\'][^"\']*(?:block-goods|goods|item)[^"\']*["\'][^>]*>(.*?)</(?:li|div)>',
        source_html,
        re.I | re.S,
    )
    if not blocks:
        blocks = re.findall(r'<a[^>]+href=["\'][^"\']*/shop/g/g[^"\']+["\'][^>]*>.*?</a>', source_html, re.I | re.S)
    for block in blocks:
        href_match = re.search(r'href=["\']([^"\']*/shop/g/g[^"\']+)["\']', block, re.I)
        if not href_match:
            continue
        source_url = urllib.parse.urljoin(base_url, html.unescape(href_match.group(1)))
        if source_url in seen:
            continue
        title_match = re.search(r'(?:alt|title)=["\']([^"\']+)["\']', block, re.I)
        if title_match:
            title = _plain(title_match.group(1))
        else:
            title = _plain(block)
        image_match = re.search(r'(?:data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)(?:\?[^"\']*)?)["\']', block, re.I)
        if not title or not image_match:
            continue
        image_url = urllib.parse.urljoin(source_url, html.unescape(image_match.group(1)))
        seen.add(source_url)
        candidates.append(
            {
                "candidate_source_url": source_url,
                "candidate_title": title,
                "candidate_image_url": image_url,
            }
        )
    return candidates


def provider_candidates(item: dict[str, Any], html_text: str) -> list[dict[str, Any]]:
    if item.get("source_store") == "Cospa":
        return _cospa_candidates(html_text)
    if item.get("source_store") == ENSKY_STORE:
        return _ensky_candidates(html_text)
    if item.get("source_store") == ANIMATE_STORE:
        return _animate_candidates(html_text)
    if item.get("source_store") == GOODSMILE_STORE:
        return _goodsmile_info_candidates(html_text)
    if item.get("source_store") == FURYU_STORE:
        return _furyu_candidates(str(item.get("query") or ""))
    if item.get("source_store") == TAITO_STORE:
        return _taito_candidates(str(item.get("query") or ""))
    if item.get("source_store") == REMENT_STORE:
        return _rement_catalog_candidates()
    if item.get("source_store") == AMIAMI_STORE:
        return _amiami_candidates(html_text)
    if item.get("source_store") == MOVIC_STORE:
        return _goods_search_candidates(html_text, "https://www.movic.jp")
    if item.get("source_store") == KOTOBUKIYA_STORE:
        return _goods_search_candidates(html_text, "https://shop.kotobukiya.co.jp")
    return []


def build_candidates(
    queue_payload: dict[str, Any],
    *,
    source_store: str | None = None,
    start_index: int = 0,
    max_rows: int | None = None,
    sleep_seconds: float = 0.15,
    max_consecutive_rate_limits: int = 3,
    time_budget_seconds: float | None = None,
) -> dict[str, Any]:
    queue_items = [item for item in queue_payload.get("items") or [] if isinstance(item, dict)]
    supported_queue_items = [item for item in queue_items if item.get("source_store") in SUPPORTED_PROVIDER_STORES]
    unsupported_queue_items = [item for item in queue_items if item.get("source_store") not in SUPPORTED_PROVIDER_STORES]
    items = list(queue_items)
    if source_store:
        items = [item for item in items if item.get("source_store") == source_store]
    else:
        items = supported_queue_items
    if start_index > 0:
        items = items[start_index:]
    if max_rows is not None:
        items = items[:max_rows]

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    consecutive_rate_limits_by_store: Counter[str] = Counter()
    skipped_rate_limited_stores: set[str] = set()
    rate_limit_stopped = False
    time_budget_exhausted = False
    started_at = time.monotonic()
    for item in items:
        if time_budget_seconds is not None and time.monotonic() - started_at >= time_budget_seconds:
            time_budget_exhausted = True
            break
        item_store = str(item.get("source_store") or "")
        if item_store in skipped_rate_limited_stores:
            continue
        official_search_url = item.get("official_search_url")
        if not official_search_url and item.get("source_store") not in API_PROVIDER_STORES:
            continue
        try:
            source_html = "" if item.get("source_store") in API_PROVIDER_STORES else _fetch_text(str(official_search_url))
            _raise_if_provider_waiting_room(item_store, source_html)
        except RateLimitError as exc:
            consecutive_rate_limits_by_store[item_store] += 1
            failures.append(
                {
                    "row_index": item.get("row_index"),
                    "source_store": item.get("source_store"),
                    "official_search_url": official_search_url,
                    "error": str(exc),
                    "rate_limited": True,
                }
            )
            if consecutive_rate_limits_by_store[item_store] >= max_consecutive_rate_limits:
                if source_store:
                    rate_limit_stopped = True
                    break
                skipped_rate_limited_stores.add(item_store)
                consecutive_rate_limits_by_store[item_store] = 0
                continue
            continue
        except ProviderTemporaryUnavailable as exc:
            consecutive_rate_limits_by_store[item_store] += 1
            failures.append(
                {
                    "row_index": item.get("row_index"),
                    "source_store": item.get("source_store"),
                    "official_search_url": official_search_url,
                    "error": str(exc),
                    "provider_temporary_unavailable": True,
                }
            )
            if consecutive_rate_limits_by_store[item_store] >= max_consecutive_rate_limits:
                if source_store:
                    rate_limit_stopped = True
                    break
                skipped_rate_limited_stores.add(item_store)
                consecutive_rate_limits_by_store[item_store] = 0
                continue
            continue
        except Exception as exc:
            failures.append({"row_index": item.get("row_index"), "source_store": item.get("source_store"), "error": str(exc)})
            continue
        consecutive_rate_limits_by_store[item_store] = 0
        parsed = provider_candidates(item, source_html)
        scored: list[dict[str, Any]] = []
        for candidate in parsed:
            query = _item_query(item)
            candidate_title = str(candidate.get("candidate_title") or "")
            score, shared = _token_score(query, candidate_title)
            goods_type_compatible = _goods_type_compatible(query, candidate_title)
            safe_pair = is_safe_source_image_pair(candidate.get("candidate_source_url"), candidate.get("candidate_image_url"))
            scored.append(
                {
                    **candidate,
                    "score": round(score, 4),
                    "shared_tokens": shared,
                    "goods_type_compatible": goods_type_compatible,
                    "safe_source_image_pair": safe_pair,
                }
            )
        scored.sort(key=lambda candidate: (-float(candidate["score"]), str(candidate.get("candidate_title") or "")))
        status = "no_candidates" if item.get("source_store") in SUPPORTED_PROVIDER_STORES else "no_provider_parser"
        if (
            len(scored) == 1
            and scored[0]["score"] >= 0.8
            and scored[0]["goods_type_compatible"]
            and scored[0]["safe_source_image_pair"]
        ):
            status = "exact_candidate_available"
        elif scored and (scored[0]["score"] < 0.5 or not scored[0]["goods_type_compatible"]):
            status = "no_relevant_candidates"
        elif scored:
            status = "candidate_review_needed"
        results.append(
            {
                "row_index": item.get("row_index"),
                "source_store": item.get("source_store"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "query": _item_query(item),
                "official_search_url": official_search_url,
                "status": status,
                "candidate_count": len(scored),
                "top_candidates": scored[:5],
            }
        )
        if sleep_seconds:
            time.sleep(sleep_seconds)

    status_counts = Counter(str(result.get("status") or "") for result in results)
    unsupported_by_store = Counter(str(item.get("source_store") or "") for item in unsupported_queue_items)
    return {
        "summary": {
            "source_queue_rows": len(queue_items),
            "supported_provider_rows": len(supported_queue_items),
            "unsupported_provider_rows": len(unsupported_queue_items),
            "supported_provider_stores": sorted(SUPPORTED_PROVIDER_STORES),
            "top_unsupported_provider_stores": [
                {"source_store": store, "rows": count}
                for store, count in unsupported_by_store.most_common(20)
            ],
            "scanned_rows": len(items),
            "processed_rows": len(results) + len(failures),
            "result_rows": len(results),
            "failure_count": len(failures),
            "rate_limit_stopped": rate_limit_stopped,
            "time_budget_seconds": time_budget_seconds,
            "time_budget_exhausted": time_budget_exhausted,
            "start_index": max(start_index, 0),
            "rate_limit_skipped_stores": sorted(skipped_rate_limited_stores),
            "rate_limit_failures": sum(1 for failure in failures if failure.get("rate_limited")),
            "provider_temporary_unavailable_failures": sum(
                1 for failure in failures if failure.get("provider_temporary_unavailable")
            ),
            "status_counts": status_counts.most_common(),
            "exact_candidate_rows": status_counts.get("exact_candidate_available", 0),
            "candidate_review_rows": status_counts.get("candidate_review_needed", 0),
            "no_relevant_candidate_rows": status_counts.get("no_relevant_candidates", 0),
            "auto_apply_enabled": False,
        },
        "results": results,
        "failures": failures,
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# Catalog Source Detail Candidates",
        "",
        f"- Source queue rows: `{summary['source_queue_rows']}`",
        f"- Supported provider rows: `{summary['supported_provider_rows']}`",
        f"- Unsupported provider rows: `{summary['unsupported_provider_rows']}`",
        f"- Scanned rows: `{summary['scanned_rows']}`",
        f"- Processed rows: `{summary.get('processed_rows', summary.get('result_rows'))}`",
        f"- Exact candidate rows: `{summary['exact_candidate_rows']}`",
        f"- Candidate review rows: `{summary['candidate_review_rows']}`",
        f"- Failures: `{summary['failure_count']}`",
        f"- Time budget exhausted: `{summary.get('time_budget_exhausted', False)}`",
        "",
        "## Status Counts",
    ]
    for status, count in summary["status_counts"]:
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Top Unsupported Provider Stores"])
    for item in summary.get("top_unsupported_provider_stores", []):
        lines.append(f"- `{item['source_store']}`: `{item['rows']}`")
    lines.extend(["", "## Exact Candidates"])
    for result in payload.get("results") or []:
        if result.get("status") != "exact_candidate_available":
            continue
        top = (result.get("top_candidates") or [{}])[0]
        lines.append(
            f"- Row `{result.get('row_index')}` {result.get('name_ja') or result.get('name_ko')}: "
            f"`{top.get('candidate_title')}` -> {top.get('candidate_source_url')}"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument(
        "--source-store",
        default=None,
        help="Source store to scan. Omit or pass all-supported to scan every supported parser.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Skip this many filtered queue rows before scanning, useful for resuming a slow store.",
    )
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--max-consecutive-rate-limits", type=int, default=3)
    parser.add_argument(
        "--time-budget-seconds",
        type=float,
        default=None,
        help="Stop cleanly after this many seconds and write a partial report.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.15,
        help="Delay between successful provider requests to avoid store rate limits.",
    )
    args = parser.parse_args()

    queue_payload = json.loads(args.queue.read_text(encoding="utf-8-sig"))
    if not isinstance(queue_payload, dict):
        raise SystemExit(f"{args.queue} must contain a JSON object")
    payload = build_candidates(
        queue_payload,
        source_store=None if args.source_store in (None, "", "all-supported") else args.source_store,
        start_index=max(args.start_index, 0),
        max_rows=args.max_rows,
        sleep_seconds=args.sleep_seconds,
        max_consecutive_rate_limits=args.max_consecutive_rate_limits,
        time_budget_seconds=args.time_budget_seconds,
    )
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                "scanned_rows": payload["summary"]["scanned_rows"],
                "processed_rows": payload["summary"].get("processed_rows"),
                "exact_candidate_rows": payload["summary"]["exact_candidate_rows"],
                "candidate_review_rows": payload["summary"]["candidate_review_rows"],
                "failures": payload["summary"]["failure_count"],
                "time_budget_exhausted": payload["summary"].get("time_budget_exhausted"),
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
