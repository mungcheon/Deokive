from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from catalog_normalize import is_generic_source_url
from enrich_catalog_images import _preferred_query_for_row
from image_enrichment_safety import is_product_specific_source_url

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_JSON = ROOT / "server" / "catalog_image_enrichment_queue_current.json"
DEFAULT_CSV = ROOT / "server" / "catalog_image_enrichment_queue_current.csv"

SEARCH_TEMPLATES = {
    "애니메이트": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    "Animate": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    "엔스카이": "https://www.enskyshop.com/products/list?name={query}",
    "굿스마일컴퍼니": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "FuRyu": "https://furyuprize.com/search?keyword={query}",
    "Taito": "https://www.taito.co.jp/prize?keyword={query}",
    "코토부키야": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "Movic": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "AmiAmi": "https://www.amiami.jp/top/search/list?s_keywords={query}",
    "Re-ment": "https://www.re-ment.co.jp/?s={query}",
    "Cospa": "https://www.cospa.com/cospa/itemlist/keyword/{query}",
    "메가하우스": "https://www.megahobby.jp/?s={query}",
    "반다이": "https://p-bandai.jp/search/?q={query}",
    "Square Enix e-STORE": "https://store.jp.square-enix.com/item_list.html?keyword={query}",
    "점프 캐릭터즈 스토어": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
}

ANIMATE_STORE = "\uc560\ub2c8\uba54\uc774\ud2b8"
ENSKY_STORE = "\uc5d4\uc2a4\uce74\uc774"
GOODSMILE_STORE = "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8"
KOTOBUKIYA_STORE = "\ucf54\ud1a0\ubd80\ud0a4\uc57c"
CHIIKAWA_MARKET_STORE = "\uce58\uc774\uce74\uc640 \ub9c8\ucf13"
CHIIKAWA_MOGUMOGU_STORE = "\uce58\uc774\uce74\uc640 \ubaa8\uad6c\ubaa8\uad6c \ud63c\ud3ec"
JUMP_CHARACTER_STORE = "\uc810\ud504 \uce90\ub9ad\ud130\uc988 \uc2a4\ud1a0\uc5b4"
MEGAHOUSE_STORE = "\uba54\uac00\ud558\uc6b0\uc2a4"
BANDAI_STORE = "\ubc18\ub2e4\uc774"

SEARCH_TEMPLATES.update(
    {
        ANIMATE_STORE: "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
        ENSKY_STORE: "https://www.enskyshop.com/products/list?name={query}",
        GOODSMILE_STORE: "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
        KOTOBUKIYA_STORE: "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
        CHIIKAWA_MARKET_STORE: "https://chiikawamarket.jp/ko/search?q={query}&type=product",
        CHIIKAWA_MOGUMOGU_STORE: "https://chiikawamogumogu.shop/search?q={query}&type=product",
        JUMP_CHARACTER_STORE: "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
        MEGAHOUSE_STORE: "https://www.megahobby.jp/?s={query}",
        BANDAI_STORE: "https://p-bandai.jp/search/?q={query}",
    }
)

PRIZE_SEARCH_TEMPLATES = {
    "Banpresto": "https://bsp-prize.jp/search/?keyword={query}",
    "반프레스토": "https://bsp-prize.jp/search/?keyword={query}",
    "SEGA": "https://segaplaza.jp/search/?word={query}",
}

PRIZE_STORES = set(PRIZE_SEARCH_TEMPLATES)
REVIEW_ONLY_SEARCH_STORES = {
    "AmiAmi",
    "Cospa",
    "메가하우스",
    "반다이",
    "Square Enix e-STORE",
    "점프 캐릭터즈 스토어",
}

STRATEGY_PRIORITY = {
    "official_search": 10,
    "manual_official_search_review": 20,
    "prize_detail_validation": 25,
    "prize_maker_search": 25,
    "manual_review": 30,
    "source_url_product_detail_lookup": 40,
    "source_url_generic_storefront": 60,
    "source_url_search_portal": 65,
    "source_url_manual_review": 70,
}

STRATEGY_NOTES = {
    "official_search": "Verified or partially verified provider path exists; strict matchers should still be run in small batches.",
    "manual_official_search_review": "Official search URL is useful, but no stable automatic detail/image parser is verified or the provider blocks scripted access.",
    "prize_detail_validation": "Prize search can return broad results; require detail-page validation before attaching images.",
    "manual_review": "No stable official search/provider path is configured.",
    "source_url_product_detail_lookup": "Use existing product-specific official source_url metadata/JSON-LD image lookup only.",
    "source_url_generic_storefront": "Existing source_url points to a store home/shop page, not a product; find exact product pages before attaching images.",
    "source_url_search_portal": "Existing source_url points to a search/portal page; require a product detail URL or exact official ID first.",
    "source_url_manual_review": "Existing source_url is generic or ambiguous; do not attach homepage, campaign, or OG images automatically.",
}

PROVIDER_STATUS_BY_STRATEGY = {
    "official_search": "search_only",
    "manual_official_search_review": "search_only_manual",
    "prize_detail_validation": "search_only_requires_detail_validation",
    "prize_maker_search": "search_only_requires_detail_validation",
    "manual_review": "manual_only",
    "source_url_product_detail_lookup": "product_detail_available",
    "source_url_generic_storefront": "generic_source",
    "source_url_search_portal": "search_portal",
    "source_url_manual_review": "ambiguous_source",
}

AUTOMATION_SAFETY_BY_STATUS = {
    "product_detail_available": "safe_if_exact_image_or_jsonld",
    "search_only": "candidate_provider_script_required",
    "search_only_manual": "manual_confirmation_required",
    "search_only_requires_detail_validation": "detail_page_validation_required",
    "generic_source": "blocked_until_exact_product_url",
    "search_portal": "blocked_until_exact_product_url",
    "ambiguous_source": "manual_confirmation_required",
    "manual_only": "manual_research_required",
}

GENERIC_STOREFRONT_DOMAINS = {
    "fanding.kr",
    "shop.weverse.io",
    "www.pokemoncenter-online.com",
    "pokemoncenter-online.com",
}

SEARCH_PORTAL_HINTS = (
    "/search",
    "mode=search",
    "keyword=",
    "smt=",
    "q=",
)


def _top_counter(counter: Counter[tuple[Any, ...]], keys: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for values, count in counter.most_common(limit):
        row = {key: value for key, value in zip(keys, values)}
        row["missing_images"] = count
        rows.append(row)
    return rows


def classify(row: dict[str, Any]) -> str:
    store = str(row.get("source_store") or "")
    source_url = str(row.get("source_url") or "")
    if source_url:
        if is_product_specific_source_url(source_url):
            return "source_url_product_detail_lookup"
        parsed = urllib.parse.urlparse(source_url)
        domain = parsed.netloc.lower()
        url_lower = source_url.lower()
        if domain in GENERIC_STOREFRONT_DOMAINS:
            return "source_url_generic_storefront"
        if any(hint in url_lower for hint in SEARCH_PORTAL_HINTS):
            return "source_url_search_portal"
        return "source_url_manual_review"
    if store in REVIEW_ONLY_SEARCH_STORES:
        return "manual_official_search_review"
    if store in SEARCH_TEMPLATES:
        return "official_search"
    if store in PRIZE_STORES:
        return "prize_detail_validation"
    return "manual_review"


def provider_status(strategy: str) -> str:
    return PROVIDER_STATUS_BY_STRATEGY.get(strategy, "manual_only")


def automation_safety(strategy: str) -> str:
    return AUTOMATION_SAFETY_BY_STATUS.get(provider_status(strategy), "manual_research_required")


def preferred_query(row: dict[str, Any]) -> str:
    localized = _preferred_query_for_row(row)
    if localized:
        return localized
    store = str(row.get("source_store") or "")
    fields = ("name_ja", "name_en", "name_ko")
    if store not in SEARCH_TEMPLATES and store not in PRIZE_SEARCH_TEMPLATES:
        fields = ("name_ko", "name_ja", "name_en")
    for field in fields:
        value = str(row.get(field) or "").strip()
        if value:
            return value
    return ""


def search_url(row: dict[str, Any]) -> str | None:
    store = str(row.get("source_store") or "")
    template = SEARCH_TEMPLATES.get(store) or PRIZE_SEARCH_TEMPLATES.get(store)
    if not template:
        return None
    query = urllib.parse.quote(preferred_query(row))
    return template.format(query=query)


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or a catalog object with items")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    rows = load_rows(args.input)

    queue: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("image_url"):
            continue
        strategy = classify(row)
        item = {
            "row_index": row_index,
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
            "name_en": row.get("name_en"),
            "category": row.get("category"),
            "affiliation": row.get("affiliation"),
            "source_store": row.get("source_store"),
            "source_url": row.get("source_url"),
            "source_url_is_generic": is_generic_source_url(row.get("source_url")),
            "source_url_is_product_detail": is_product_specific_source_url(row.get("source_url")),
            "strategy": strategy,
            "provider_status": provider_status(strategy),
            "automation_safety": automation_safety(strategy),
            "priority": STRATEGY_PRIORITY.get(strategy, 99),
            "query": preferred_query(row),
            "search_url": search_url(row),
        }
        queue.append(item)

    queue.sort(
        key=lambda item: (
            item["priority"],
            str(item.get("source_store") or ""),
            str(item.get("affiliation") or ""),
            str(item.get("category") or ""),
            str(item.get("name_ko") or ""),
        )
    )

    by_strategy = Counter(item["strategy"] for item in queue)
    by_provider_status = Counter(item["provider_status"] for item in queue)
    by_automation_safety = Counter(item["automation_safety"] for item in queue)
    by_store = Counter(item["source_store"] for item in queue)
    by_category = Counter(item["category"] for item in queue)
    by_store_category: Counter[tuple[str, str]] = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or "")) for item in queue
    )
    by_strategy_store: Counter[tuple[str, str]] = Counter(
        (str(item.get("strategy") or ""), str(item.get("source_store") or "")) for item in queue
    )
    by_status_store: Counter[tuple[str, str]] = Counter(
        (str(item.get("provider_status") or ""), str(item.get("source_store") or "")) for item in queue
    )
    by_strategy_store_category: Counter[tuple[str, str, str]] = Counter(
        (
            str(item.get("strategy") or ""),
            str(item.get("source_store") or ""),
            str(item.get("category") or ""),
        )
        for item in queue
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_by_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in queue:
        grouped[str(item["strategy"])].append(item)
        grouped_by_store[str(item.get("source_store") or "")].append(item)

    payload = {
        "missing_images": len(queue),
        "by_strategy": by_strategy.most_common(),
        "by_provider_status": by_provider_status.most_common(),
        "by_automation_safety": by_automation_safety.most_common(),
        "by_store": by_store.most_common(),
        "by_category": by_category.most_common(),
        "top_store_categories": _top_counter(by_store_category, ("source_store", "category"), 80),
        "top_strategy_stores": _top_counter(by_strategy_store, ("strategy", "source_store"), 80),
        "top_provider_status_stores": _top_counter(by_status_store, ("provider_status", "source_store"), 80),
        "top_strategy_store_categories": _top_counter(
            by_strategy_store_category,
            ("strategy", "source_store", "category"),
            120,
        ),
        "strategy_notes": STRATEGY_NOTES,
        "provider_status_notes": {
            "product_detail_available": "A product-specific source_url exists; attach image only from same-page JSON-LD/OG/product media.",
            "search_only": "An official search path exists, but exact detail-page matching must happen before image attachment.",
            "search_only_manual": "Search is useful for humans, but scripted exact matching is not currently verified.",
            "search_only_requires_detail_validation": "Prize/search results are broad; require exact detail-page evidence.",
            "generic_source": "Current source_url is a home/shop page and cannot prove an image.",
            "search_portal": "Current source_url is a search/portal page and cannot prove an image.",
            "ambiguous_source": "Current source_url is not specific enough for automatic image attachment.",
            "manual_only": "No provider-specific official path is configured yet.",
        },
        "automation_safety_notes": {
            "safe_if_exact_image_or_jsonld": "Automation can run if the image is extracted from the exact product page and passes host safety rules.",
            "candidate_provider_script_required": "Build or run a provider-specific matcher before writing image_url.",
            "manual_confirmation_required": "Use human review or add a stricter provider before writing.",
            "detail_page_validation_required": "Search result must resolve to an exact detail page for the same item.",
            "blocked_until_exact_product_url": "Do not attach images from storefront/search pages.",
            "manual_research_required": "No safe automation path yet.",
        },
        "queue": queue,
        "items": queue,
        "samples_by_strategy": {key: value[:30] for key, value in grouped.items()},
        "samples_by_store": {key: value[:10] for key, value in grouped_by_store.items()},
    }
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with args.csv_output.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "strategy",
                "provider_status",
                "automation_safety",
                "priority",
                "row_index",
                "source_store",
                "affiliation",
                "category",
                "name_ko",
                "name_ja",
                "name_en",
                "source_url",
                "source_url_is_generic",
                "source_url_is_product_detail",
                "query",
                "search_url",
            ],
        )
        writer.writeheader()
        writer.writerows(queue)

    print(
        json.dumps(
            {
                "missing_images": len(queue),
                "by_strategy": by_strategy.most_common(),
                "by_provider_status": by_provider_status.most_common(),
                "by_automation_safety": by_automation_safety.most_common(),
                "json": str(args.json_output),
                "csv": str(args.csv_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
