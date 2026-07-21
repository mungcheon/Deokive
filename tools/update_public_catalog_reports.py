from __future__ import annotations

import argparse
import json
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PUBLIC_CATALOG = DATA / "catalog_public.json"
PUBLIC_META = DATA / "catalog_public_meta.json"
QUALITY = DATA / "catalog_quality_public.json"
IMAGE_BACKLOG = DATA / "catalog_image_backlog_public.json"
IMAGE_CANDIDATES = DATA / "catalog_image_candidate_review_public.json"
DEDUPLICATION = DATA / "catalog_deduplication_public.json"
ANIMATION_CATEGORIES = DATA / "animation_goods_categories_public.json"
ICHIIBAN_KUJI_HISTORY = DATA / "ichiban_kuji_history_public.json"
ICHIIBAN_KUJI_CAMPAIGNS = DATA / "ichiban_kuji_campaigns.json"
GOTOUCHI = DATA / "gotouchi_chiikawa_image_candidates_public.json"
REQUESTED = DATA / "requested_special_goods_public.json"
GENERIC_SOURCE = DATA / "generic_source_cleanup_public.json"
GENERIC_SOURCE_PATCH_CANDIDATES = DATA / "generic_source_patch_candidates_public.json"
SOURCE_DETAIL = DATA / "source_detail_probe_public.json"
SOURCE_DISCOVERY = DATA / "source_discovery_queue_public.json"
METADATA_BACKLOG = DATA / "catalog_metadata_backlog_public.json"
IMAGE_ENRICHMENT_BATCHES = DATA / "catalog_image_enrichment_batches_public.json"
OPERATIONS_REPORT = DATA / "catalog_operations_public.json"
AGENT_WORK_QUEUE = DATA / "catalog_agent_work_queue_public.json"

OFFICIAL_SEARCH_TEMPLATES = {
    "애니메이트": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    "엔스카이": "https://www.enskyshop.com/products/list?name={query}",
    "굿스마일컴퍼니": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "코토부키야": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "Movic": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "FuRyu": "https://furyuprize.com/search?keyword={query}",
    "Taito": "https://www.taito.co.jp/prize?keyword={query}",
    "AmiAmi": "https://www.amiami.jp/top/search/list?s_keywords={query}",
    "Cospa": "https://www.cospa.com/cospa/itemlist/keyword/{query}",
    "메가하우스": "https://www.megahobby.jp/?s={query}",
    "반다이": "https://p-bandai.jp/search/?q={query}",
    "점프 캐릭터즈 스토어": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "무기와라스토어": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "Banpresto": "https://bsp-prize.jp/search/?keyword={query}",
    "SEGA": "https://segaplaza.jp/search/?word={query}",
    "치이카와 마켓": "https://chiikawamarket.jp/search?q={query}",
    "치이카와 모구모구 혼포": "https://chiikawamogumogu.shop/search?q={query}",
    "치이카와 온라인 쿠지": "https://online-kuji.chiikawamarket.jp/search?q={query}",
    "Re-ment": "https://www.re-ment.co.jp/?s={query}",
    "Stellive Store": "https://stellive.fanding.kr/search?keyword={query}",
    "JYP SHOP": "https://en.thejypshop.com/product/search.html?keyword={query}",
    "산리오": "https://shop.sanrio.co.jp/search?keyword={query}",
    "디즈니 스토어": "https://store.disney.co.jp/search?q={query}",
    "가샤폰": "https://gashapon.jp/search/?q={query}",
    "MINISO": "https://www.miniso.com/search?keyword={query}",
    "MINISO 중국": "https://www.miniso.com/search?keyword={query}",
    "ALTER": "https://www.google.com/search?q=site%3Aalter-web.jp%20{query}",
    "Phat! Company": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "Bandai Premium": "https://p-bandai.jp/search/?q={query}",
    "Hololive Production Official Shop": "https://shop.hololivepro.com/en/search?q={query}",
    "SM STORE": "https://global.shop.smtown.com/search?q={query}",
    "YG SELECT": "https://en.ygselect.com/product/search.html?keyword={query}",
    "귀멸의 칼날 공식": "https://www.google.com/search?q=site%3Awebshop-global.ufotable.co.jp%20{query}",
    "카도카와": "https://www.amiami.com/eng/search/list/?s_keywords={query}%20KADOKAWA",
    "Algonavis": "https://bushiroad-store.com/search?q={query}",
    "Hobby Max International": "https://www.amiami.com/eng/search/list/?s_keywords={query}%20HOBBY%20MAX",
    "STARSHIP STORE": "https://www.starship-square.com/product/search.html?keyword={query}",
    "CUBE STORE": "https://www.google.com/search?q=site%3Acubee.co.kr%20{query}",
    "IST STORE": "https://www.google.com/search?q=site%3Ashop.weverse.io%20{query}",
    "KQ FELLAZ": "https://www.google.com/search?q=site%3Akqshop.kr%20{query}",
    "롯데웰푸드": "https://www.google.com/search?q=site%3Alottewellfood.com%20{query}",
    "점프 숍": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "이세계아이돌 공식 굿즈": "https://www.google.com/search?q=site%3Awithmuulive.com%20{query}",
    "이세계아이돌 팝업스토어": "https://www.google.com/search?q=site%3Awithmuulive.com%20{query}",
    "치이카와 중국 팝업스토어": "https://www.google.com/search?q=site%3Ax.com%2Fchiikawa_kouhou%20{query}",
    "치이카와샵 용산": "https://www.google.com/search?q=site%3Ax.com%2Fchiikawashop_kr%20{query}",
}

LICENSED_RETAILER_STORES = {"AmiAmi"}
GENERIC_STOREFRONT_URLS = {
    "https://fanding.kr/@stellive/shop",
    "https://shop.weverse.io/home",
    "https://www.pokemoncenter-online.com",
    "https://www.pokemoncenter-online.com/",
}
DISCOVERY_PRIORITY = {
    "official_search_url_available": 10,
    "licensed_retailer_search_review": 20,
    "manual_official_research": 40,
}
DEDUPLICATION_KEY_PRIORITY = {
    "barcode": 10,
    "source_url": 20,
    "source_url_normalized_name": 25,
    "image_url": 30,
    "image_url_normalized_name": 35,
}

ANIMATION_STORES = {
    "AmiAmi",
    "Cospa",
    "FuRyu",
    "Movic",
    "Re-ment",
    "Taito",
    "굿스마일컴퍼니",
    "귀멸의 칼날 공식",
    "메가하우스",
    "무기와라스토어",
    "반다이",
    "애니메이트",
    "엔스카이",
    "점프 캐릭터즈 스토어",
    "점프 숍",
    "카도카와",
    "코토부키야",
}

CATEGORY_FAMILIES = {
    "figure": {"피규어", "미니어처", "리플리카"},
    "plush": {"인형", "마스코트"},
    "badge": {"캔뱃지"},
    "acrylic": {"아크릴 스탠드"},
    "keyring": {"키링"},
    "stationery": {"문구", "클리어파일", "카드", "트레이딩 카드", "스티커"},
    "daily_goods": {"머그컵", "타월", "가방", "생활잡화", "액세서리", "클리어 보틀", "파우치"},
    "display_goods": {"태피스트리"},
    "apparel": {"의류"},
    "fan_goods": {"응원용품", "응원봉"},
}

FAMILY_VISUALS = {
    "figure": {"icon_key": "toys", "color_hint": "mint", "color_hex": "0xFF28D6C8"},
    "plush": {"icon_key": "face", "color_hint": "pink", "color_hex": "0xFFFF8FC3"},
    "badge": {"icon_key": "badge", "color_hint": "red", "color_hex": "0xFFD64562"},
    "acrylic": {"icon_key": "view_carousel", "color_hint": "blue", "color_hex": "0xFF5BA7F7"},
    "keyring": {"icon_key": "local_offer", "color_hint": "yellow", "color_hex": "0xFFFFD84D"},
    "stationery": {"icon_key": "sticky_note", "color_hint": "purple", "color_hex": "0xFFA78BFA"},
    "daily_goods": {"icon_key": "inventory", "color_hint": "green", "color_hex": "0xFF42A866"},
    "display_goods": {"icon_key": "photo", "color_hint": "indigo", "color_hex": "0xFF4F46E5"},
    "apparel": {"icon_key": "style", "color_hint": "neutral", "color_hex": "0xFF6B7280"},
    "fan_goods": {"icon_key": "celebration", "color_hint": "orange", "color_hex": "0xFFFF9F43"},
    "other": {"icon_key": "category", "color_hint": "neutral", "color_hex": "0xFF9CA3AF"},
}

FOLDER_COLOR_PALETTE = [
    {"color_hint": "red", "color_hex": "0xFFD64562", "sort_order": 10},
    {"color_hint": "coral", "color_hex": "0xFFFF6B6B", "sort_order": 20},
    {"color_hint": "orange", "color_hex": "0xFFFF9F43", "sort_order": 30},
    {"color_hint": "yellow", "color_hex": "0xFFFFD84D", "sort_order": 40},
    {"color_hint": "lime", "color_hex": "0xFFA3E635", "sort_order": 50},
    {"color_hint": "green", "color_hex": "0xFF42A866", "sort_order": 60},
    {"color_hint": "mint", "color_hex": "0xFF28D6C8", "sort_order": 70},
    {"color_hint": "cyan", "color_hex": "0xFF22D3EE", "sort_order": 80},
    {"color_hint": "blue", "color_hex": "0xFF5BA7F7", "sort_order": 90},
    {"color_hint": "indigo", "color_hex": "0xFF4F46E5", "sort_order": 100},
    {"color_hint": "purple", "color_hex": "0xFFA78BFA", "sort_order": 110},
    {"color_hint": "pink", "color_hex": "0xFFFF8FC3", "sort_order": 120},
    {"color_hint": "neutral", "color_hex": "0xFF9CA3AF", "sort_order": 130},
]

FAMILY_ICON_OPTIONS = {
    "figure": ["toys", "view_in_ar", "emoji_objects"],
    "plush": ["face", "sentiment_satisfied", "favorite"],
    "badge": ["badge", "stars", "workspace_premium"],
    "acrylic": ["view_carousel", "layers", "photo_library"],
    "keyring": ["local_offer", "vpn_key", "sell"],
    "stationery": ["sticky_note", "edit_note", "article"],
    "daily_goods": ["inventory", "shopping_bag", "widgets"],
    "display_goods": ["photo", "collections", "wallpaper"],
    "apparel": ["style", "checkroom", "dry_cleaning"],
    "fan_goods": ["celebration", "campaign", "favorite"],
    "other": ["category", "folder", "apps"],
}

CANONICAL_CATEGORY_SUGGESTIONS = {
    "클리어파일": "문구",
    "카드": "문구",
    "미니어처": "피규어",
    "트레이딩 카드": "문구",
    "스티커": "문구",
    "클리어 보틀": "생활잡화",
    "파우치": "가방",
    "기타 굿즈": "액세서리",
}

UNKNOWN_CATEGORY_REVIEW_SUGGESTIONS = {
    "굿즈": {
        "suggested_family": "other",
        "suggested_category": "기타 굿즈",
        "color_hint": "neutral",
        "primary_icon_key": "category",
        "review_priority": 70,
        "reason": "Broad catch-all category; inspect names before moving to a specific folder family.",
    },
    "아크릴": {
        "suggested_family": "acrylic",
        "suggested_category": "아크릴 스탠드",
        "color_hint": "blue",
        "primary_icon_key": "view_carousel",
        "review_priority": 20,
        "reason": "Most acrylic goods should be split into acrylic stand/keyholder/card after name review.",
    },
    "참": {
        "suggested_family": "keyring",
        "suggested_category": "키링",
        "color_hint": "yellow",
        "primary_icon_key": "local_offer",
        "review_priority": 30,
        "reason": "Charm items usually behave like keyrings in the app folder model.",
    },
    "포스터": {
        "suggested_family": "display_goods",
        "suggested_category": "포스터",
        "color_hint": "indigo",
        "primary_icon_key": "photo",
        "review_priority": 25,
        "reason": "Poster is a display goods folder, but should remain distinct from bromide/photo cards.",
    },
    "컵": {
        "suggested_family": "daily_goods",
        "suggested_category": "머그컵",
        "color_hint": "green",
        "primary_icon_key": "inventory",
        "review_priority": 40,
        "reason": "Cup items fit daily goods; verify whether they are mugs, tumblers, or glassware.",
    },
    "캡슐토이": {
        "suggested_family": "figure",
        "suggested_category": "캡슐토이",
        "color_hint": "mint",
        "primary_icon_key": "toys",
        "review_priority": 35,
        "reason": "Capsule toy is usually a small figure/miniature product family.",
    },
    "기타 굿즈": {
        "suggested_family": "other",
        "suggested_category": "기타 굿즈",
        "color_hint": "neutral",
        "primary_icon_key": "category",
        "review_priority": 80,
        "reason": "Already a catch-all category; keep broad unless names clearly identify a better folder.",
    },
    "식품": {
        "suggested_family": "daily_goods",
        "suggested_category": "식품",
        "color_hint": "green",
        "primary_icon_key": "inventory",
        "review_priority": 50,
        "reason": "Food items should stay separate from character goods but use daily goods visual treatment.",
    },
}

PUBLIC_FIELDS = [
    "catalog_index",
    "name_ko",
    "name_ja",
    "name_en",
    "category",
    "character_name",
    "affiliation",
    "series_name",
    "sub_series",
    "official_price_jpy",
    "official_price_krw",
    "barcode",
    "image_url",
    "source_url",
    "source_store",
    "release_date",
]

PRIVACY_NEEDLES = [
    "C:\\Users",
    "/Users/",
    "localhost",
    "127.0.0.1",
    "deokive_dev.db",
    "password=",
    "secret=",
    "api_key=",
    "ghp_",
    "github_pat_",
    "sk-",
]


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def present(value: Any) -> bool:
    return value not in (None, "", [], {})


def missing_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {field: sum(1 for item in items if not present(item.get(field))) for field in PUBLIC_FIELDS}


def coverage(missing: dict[str, int], rows: int, fields: list[str]) -> dict[str, float]:
    if rows <= 0:
        return {field: 0.0 for field in fields}
    return {field: round((rows - missing.get(field, 0)) / rows, 4) for field in fields}


def copy_report_summary(path: Path, key: str) -> dict[str, Any]:
    data = load_json(path, {})
    summary = data.get("summary") if isinstance(data, dict) else None
    if not isinstance(summary, dict):
        summary = {}
    return {"public_report": f"data/{path.name}", **summary}


def discovery_query(item: dict[str, Any]) -> str:
    for field in ("name_ja", "name_ko", "name_en"):
        value = str(item.get(field) or "").strip()
        if value:
            return value
    return ""


def discovery_workflow(item: dict[str, Any]) -> str:
    store = str(item.get("source_store") or "")
    if store in LICENSED_RETAILER_STORES:
        return "licensed_retailer_search_review"
    if store in OFFICIAL_SEARCH_TEMPLATES:
        return "official_search_url_available"
    return "manual_official_research"


def discovery_search_url(item: dict[str, Any], query: str) -> str | None:
    template = OFFICIAL_SEARCH_TEMPLATES.get(str(item.get("source_store") or ""))
    if not template or not query:
        return None
    return template.format(query=urllib.parse.quote(query))


def build_source_discovery_public(items: list[dict[str, Any]], sample_rows: int = 120) -> dict[str, Any]:
    queue: list[dict[str, Any]] = []
    for row_number, item in enumerate(items):
        if present(item.get("source_url")):
            continue
        query = discovery_query(item)
        workflow = discovery_workflow(item)
        source_store = str(item.get("source_store") or "")
        web_query = " ".join(part for part in (query, source_store, "official", "公式 商品画像") if part)
        queue.append(
            {
                "priority": DISCOVERY_PRIORITY[workflow],
                "workflow": workflow,
                "row_index": item.get("catalog_index", row_number),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "official_search_url": discovery_search_url(item, query),
                "web_search_url": "https://www.google.com/search?q=" + urllib.parse.quote(web_query),
                "recommended_next_action": "find_exact_product_detail_url_then_import_image",
            }
        )

    queue.sort(
        key=lambda row: (
            row["priority"],
            str(row.get("source_store") or ""),
            str(row.get("affiliation") or ""),
            str(row.get("category") or ""),
            str(row.get("name_ja") or row.get("name_ko") or ""),
        )
    )
    by_workflow = Counter(str(item.get("workflow") or "") for item in queue)
    by_store = Counter(str(item.get("source_store") or "") for item in queue)
    return {
        "schema_version": 1,
        "summary": {
            "source_discovery_rows": len(queue),
            "published_sample_rows": min(sample_rows, len(queue)),
            "stale_excluded_rows": 0,
            "by_workflow": by_workflow.most_common(),
            "top_source_stores": by_store.most_common(30),
        },
        "instructions": [
            "Public work queue for catalog rows that need exact source URLs or image enrichment.",
            "Open official_search_url or web_search_url, verify an exact product detail page, then review source_url/image_url updates.",
            "Do not auto-apply uncertain matches; use manual review before changing the catalog database.",
        ],
        "items": queue[:sample_rows],
    }


def metadata_action(field: str) -> str:
    if field in {"source_url", "image_url"}:
        return "find exact official product page and attach source_url/image_url together"
    if field in {"release_date", "official_price_jpy"}:
        return "verify official detail page metadata before importing"
    if field == "barcode":
        return "fill only when barcode is shown by official or trusted retailer data"
    if field == "name_ja":
        return "verify original Japanese product title from official listing"
    return "manual review required"


def build_metadata_backlog_public(items: list[dict[str, Any]], sample_groups: int = 120) -> dict[str, Any]:
    tracked_fields = [
        "source_url",
        "image_url",
        "release_date",
        "official_price_jpy",
        "barcode",
        "name_ja",
    ]
    by_field_store: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    field_totals: Counter[str] = Counter()
    store_totals: Counter[str] = Counter()

    for item in items:
        store = str(item.get("source_store") or "unknown")
        missing_fields = [field for field in tracked_fields if not present(item.get(field))]
        for field in missing_fields:
            field_totals[field] += 1
            by_field_store[(field, store)].append(item)
        if missing_fields:
            store_totals[store] += 1

    groups: list[dict[str, Any]] = []
    for (field, store), group_items in sorted(
        by_field_store.items(),
        key=lambda pair: (-len(pair[1]), pair[0][0], pair[0][1]),
    )[:sample_groups]:
        samples = group_items[:8]
        groups.append(
            {
                "field": field,
                "source_store": store,
                "missing_rows": len(group_items),
                "priority_score": len(group_items),
                "recommended_action": metadata_action(field),
                "sample_catalog_indexes": [item.get("catalog_index") for item in samples],
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "series_name": item.get("series_name"),
                        "category": item.get("category"),
                        "source_url": item.get("source_url"),
                        "image_url": item.get("image_url"),
                    }
                    for item in samples
                ],
            }
        )

    return {
        "schema_version": 1,
        "summary": {
            "tracked_fields": tracked_fields,
            "field_missing_totals": dict(field_totals),
            "store_rows_with_any_missing_metadata": store_totals.most_common(40),
            "published_group_rows": len(groups),
        },
        "instructions": [
            "Public backlog grouped by missing field and source store.",
            "Use this before source/image crawling so agents work on the largest safe gaps first.",
            "Do not infer dates, prices, barcodes, or names without official or trusted source evidence.",
        ],
        "groups": groups,
    }


def image_workflow(item: dict[str, Any]) -> str:
    if str(item.get("source_store") or "") == "ご当地ちいかわ 공식(API)":
        return "review_gotouchi_official_candidates"
    if present(item.get("source_url")):
        if normalize_url_key(item.get("source_url")) in {normalize_url_key(url) for url in GENERIC_STOREFRONT_URLS}:
            return "replace_generic_source_then_extract_image"
        return "extract_from_existing_source_url"
    if str(item.get("source_store") or "") in OFFICIAL_SEARCH_TEMPLATES:
        return "find_source_then_extract_image"
    return "manual_image_research"


def build_image_enrichment_batches_public(
    items: list[dict[str, Any]], sample_groups: int = 80, sample_items: int = 10
) -> dict[str, Any]:
    missing = [item for item in items if not present(item.get("image_url"))]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in missing:
        grouped[(image_workflow(item), str(item.get("source_store") or "unknown"))].append(item)

    workflow_priority = {
        "extract_from_existing_source_url": 10,
        "replace_generic_source_then_extract_image": 15,
        "review_gotouchi_official_candidates": 18,
        "find_source_then_extract_image": 20,
        "manual_image_research": 40,
    }
    groups: list[dict[str, Any]] = []
    for (workflow, store), group_items in sorted(
        grouped.items(),
        key=lambda pair: (workflow_priority.get(pair[0][0], 99), -len(pair[1]), pair[0][1]),
    )[:sample_groups]:
        samples = group_items[:sample_items]
        groups.append(
            {
                "workflow": workflow,
                "source_store": store,
                "missing_image_rows": len(group_items),
                "priority": workflow_priority.get(workflow, 99),
                "recommended_action": {
                    "extract_from_existing_source_url": "crawl verified source_url and review extracted product image",
                    "replace_generic_source_then_extract_image": "replace generic storefront URL with exact product URL before image import",
                    "review_gotouchi_official_candidates": "review gotouchi official motif candidates; do not import motif-only type mismatches",
                    "find_source_then_extract_image": "find exact official product page, then attach source_url and image_url",
                    "manual_image_research": "manual web research with source verification required",
                }.get(workflow, "manual review required"),
                "official_search_available": store in OFFICIAL_SEARCH_TEMPLATES,
                "candidate_review_report": f"data/{GOTOUCHI.name}"
                if workflow == "review_gotouchi_official_candidates" and GOTOUCHI.exists()
                else None,
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "series_name": item.get("series_name"),
                        "category": item.get("category"),
                        "source_url": item.get("source_url"),
                        "official_search_url": discovery_search_url(item, discovery_query(item)),
                    }
                    for item in samples
                ],
            }
        )

    by_workflow = Counter(image_workflow(item) for item in missing)
    by_store = Counter(str(item.get("source_store") or "unknown") for item in missing)
    return {
        "schema_version": 1,
        "summary": {
            "missing_image_rows": len(missing),
            "source_url_ready_rows": by_workflow.get("extract_from_existing_source_url", 0),
            "generic_source_url_rows": by_workflow.get("replace_generic_source_then_extract_image", 0),
            "gotouchi_official_review_rows": by_workflow.get("review_gotouchi_official_candidates", 0),
            "needs_source_discovery_rows": by_workflow.get("find_source_then_extract_image", 0),
            "manual_image_research_rows": by_workflow.get("manual_image_research", 0),
            "published_group_rows": len(groups),
            "top_source_stores": by_store.most_common(30),
            "by_workflow": by_workflow.most_common(),
        },
        "instructions": [
            "Public image enrichment batches grouped by readiness and source store.",
            "Rows with source_url should be attempted first because identity evidence already exists.",
            "Generic storefront source_url rows must be replaced with exact product URLs before image import.",
            "Gotouchi rows use the separate official motif candidate report before any image import.",
            "Rows without source_url must attach an exact source URL before image_url is imported.",
        ],
        "groups": groups,
    }


def build_operations_public(
    generated_at: str,
    items: list[dict[str, Any]],
    rows: int,
    missing: dict[str, int],
    cov: dict[str, float],
    source_discovery: dict[str, Any],
    metadata_backlog: dict[str, Any],
    image_enrichment_batches: dict[str, Any],
    deduplication: dict[str, Any],
    animation_categories: dict[str, Any],
    ichiban_kuji_history: dict[str, Any],
    generic_source_patch_candidates: dict[str, Any],
) -> dict[str, Any]:
    source_summary = source_discovery["summary"]
    image_summary = image_enrichment_batches["summary"]
    dedupe_summary = deduplication["summary"]
    animation_summary = animation_categories["summary"]
    kuji_summary = ichiban_kuji_history["summary"]
    metadata_summary = metadata_backlog["summary"]
    generic_patch_summary = generic_source_patch_candidates["summary"]

    priority_fields = ["source_url", "image_url", "release_date", "official_price_jpy", "barcode"]
    store_totals: dict[str, dict[str, Any]] = defaultdict(lambda: {"rows": 0, **{field: 0 for field in priority_fields}})
    for item in items:
        store = str(item.get("source_store") or "unknown")
        store_totals[store]["rows"] += 1
        for field in priority_fields:
            if not present(item.get(field)):
                store_totals[store][field] += 1

    def store_first_action(row: dict[str, Any]) -> str:
        if row["missing_source_url"] or row["missing_image_url"]:
            return "source_and_image_enrichment"
        if row["missing_release_date"]:
            return "release_date_enrichment"
        if row["missing_price_jpy"]:
            return "price_enrichment"
        if row["missing_barcode"]:
            return "barcode_review"
        return "monitor"

    store_priority_matrix = []
    for store, totals in store_totals.items():
        score = (
            totals["source_url"] * 5
            + totals["image_url"] * 4
            + totals["release_date"] * 2
            + totals["official_price_jpy"]
            + min(totals["barcode"], 200) * 0.5
        )
        if score <= 0:
            continue
        row = {
            "source_store": store,
            "priority_score": round(score, 1),
            "rows": totals["rows"],
            "missing_source_url": totals["source_url"],
            "missing_image_url": totals["image_url"],
            "missing_release_date": totals["release_date"],
            "missing_price_jpy": totals["official_price_jpy"],
            "missing_barcode": totals["barcode"],
        }
        row["recommended_first_action"] = store_first_action(row)
        store_priority_matrix.append(row)
    store_priority_matrix.sort(key=lambda row: (-row["priority_score"], str(row["source_store"])))

    quality_gates = [
        {
            "key": "source_url_coverage",
            "status": "pass" if cov.get("source_url", 0) >= 0.95 else "warn",
            "value": cov.get("source_url", 0),
            "target": 0.95,
        },
        {
            "key": "image_url_coverage",
            "status": "pass" if cov.get("image_url", 0) >= 0.95 else "warn",
            "value": cov.get("image_url", 0),
            "target": 0.95,
        },
        {
            "key": "release_date_coverage",
            "status": "pass" if cov.get("release_date", 0) >= 0.9 else "warn",
            "value": cov.get("release_date", 0),
            "target": 0.9,
        },
        {
            "key": "source_discovery_backlog",
            "status": "warn" if source_summary.get("source_discovery_rows", 0) else "pass",
            "value": source_summary.get("source_discovery_rows", 0),
            "target": 0,
        },
        {
            "key": "manual_dedupe_backlog",
            "status": "warn" if dedupe_summary.get("duplicate_groups", 0) else "pass",
            "value": dedupe_summary.get("duplicate_groups", 0),
            "target": 0,
        },
    ]

    next_actions = [
        {
            "priority": 5,
            "workstream": "agent_work_queue",
            "public_report": f"data/{AGENT_WORK_QUEUE.name}",
            "recommended_next_action": "Open top_next_batches and assign the first image/source batches before broad metadata work.",
        },
        {
            "priority": 10,
            "workstream": "image_url_attachment",
            "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
            "ready_rows": image_summary.get("source_url_ready_rows", 0),
            "generic_source_url_rows": image_summary.get("generic_source_url_rows", 0),
            "gotouchi_official_review_rows": image_summary.get("gotouchi_official_review_rows", 0),
            "blocked_rows": image_summary.get("needs_source_discovery_rows", 0),
            "recommended_next_action": "Process exact source_url-ready image rows first; review gotouchi motif candidates and replace generic storefront URLs before image import.",
        },
        {
            "priority": 12,
            "workstream": "generic_source_patch_candidates",
            "public_report": f"data/{GENERIC_SOURCE_PATCH_CANDIDATES.name}",
            "candidate_rows": generic_patch_summary.get("candidate_rows", 0),
            "manual_confirmed_rows": generic_patch_summary.get("manual_confirmed_rows", 0),
            "auto_apply_enabled": generic_patch_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Review weak generic storefront candidates before preparing any catalog patch.",
        },
        {
            "priority": 20,
            "workstream": "source_discovery",
            "public_report": f"data/{SOURCE_DISCOVERY.name}",
            "ready_rows": source_summary.get("source_discovery_rows", 0),
            "recommended_next_action": "Find exact official detail pages for rows missing source_url.",
        },
        {
            "priority": 30,
            "workstream": "metadata_backlog",
            "public_report": f"data/{METADATA_BACKLOG.name}",
            "tracked_fields": metadata_summary.get("tracked_fields", []),
            "recommended_next_action": "Use store/field groups to fill release dates, prices, barcodes, and names with evidence.",
        },
        {
            "priority": 40,
            "workstream": "deduplication_review",
            "public_report": f"data/{DEDUPLICATION.name}",
            "review_groups": dedupe_summary.get("duplicate_groups", 0),
            "recommended_next_action": "Review duplicates manually; automatic deletion remains disabled.",
        },
        {
            "priority": 50,
            "workstream": "ichiban_kuji_history",
            "public_report": f"data/{ICHIIBAN_KUJI_HISTORY.name}",
            "campaign_metadata_review_queue_rows": kuji_summary.get("campaign_metadata_review_queue_rows", 0),
            "missing_release_date_campaign_groups": kuji_summary.get("missing_release_date_campaign_groups", 0),
            "missing_price_campaign_groups": kuji_summary.get("missing_official_price_jpy_campaign_groups", 0),
            "recommended_next_action": "Use campaign_metadata_review_queue to verify official pages before applying dates or prices.",
        },
        {
            "priority": 60,
            "workstream": "animation_folder_visuals",
            "public_report": f"data/{ANIMATION_CATEGORIES.name}",
            "category_count": animation_summary.get("category_count", 0),
            "unknown_category_rows": animation_summary.get("unknown_category_rows", 0),
            "recommended_next_action": "Use taxonomy_review_queue and folder_visual_tokens for app folder colors, icons, and category cleanup.",
        },
    ]

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "summary": {
            "catalog_rows": rows,
            "coverage": cov,
            "missing": {
                "source_url": missing.get("source_url", 0),
                "image_url": missing.get("image_url", 0),
                "release_date": missing.get("release_date", 0),
                "official_price_jpy": missing.get("official_price_jpy", 0),
                "barcode": missing.get("barcode", 0),
                "name_ja": missing.get("name_ja", 0),
            },
            "open_review_queues": {
                "source_discovery_rows": source_summary.get("source_discovery_rows", 0),
                "image_missing_rows": image_summary.get("missing_image_rows", 0),
                "dedupe_groups": dedupe_summary.get("duplicate_groups", 0),
                "animation_unknown_categories": animation_summary.get("unknown_category_count", 0),
                "ichiban_missing_release_date_rows": kuji_summary.get("missing_release_date_rows", 0),
                "ichiban_missing_price_rows": kuji_summary.get("missing_official_price_jpy_rows", 0),
                "generic_source_patch_candidate_rows": generic_patch_summary.get("candidate_rows", 0),
            },
            "top_store_priority_score": store_priority_matrix[0]["priority_score"] if store_priority_matrix else 0,
        },
        "quality_gates": quality_gates,
        "store_priority_matrix": store_priority_matrix[:40],
        "reports": [
            {"key": "quality", "public_report": f"data/{QUALITY.name}"},
            {"key": "image_backlog", "public_report": f"data/{IMAGE_BACKLOG.name}"},
            {"key": "generic_source_patch_candidates", "public_report": f"data/{GENERIC_SOURCE_PATCH_CANDIDATES.name}"},
            {"key": "image_enrichment_batches", "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}"},
            {"key": "source_discovery", "public_report": f"data/{SOURCE_DISCOVERY.name}"},
            {"key": "metadata_backlog", "public_report": f"data/{METADATA_BACKLOG.name}"},
            {"key": "deduplication", "public_report": f"data/{DEDUPLICATION.name}"},
            {"key": "animation_categories", "public_report": f"data/{ANIMATION_CATEGORIES.name}"},
            {"key": "ichiban_kuji_history", "public_report": f"data/{ICHIIBAN_KUJI_HISTORY.name}"},
            {"key": "agent_work_queue", "public_report": f"data/{AGENT_WORK_QUEUE.name}"},
        ],
        "next_actions": next_actions,
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "requires_manual_review_for_imports": True,
            "scheduled_refresh": "Daily at 04:20 KST via GitHub Actions plus manual workflow_dispatch.",
            "reason": "This report coordinates public queues; it does not mutate catalog data by itself.",
        },
    }


def compact_sample(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("catalog_index") or item.get("row_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_store": item.get("source_store"),
        "source_url": item.get("source_url"),
        "official_search_url": item.get("official_search_url"),
    }


def build_agent_work_queue_public(
    generated_at: str,
    source_discovery: dict[str, Any],
    metadata_backlog: dict[str, Any],
    image_enrichment_batches: dict[str, Any],
    deduplication: dict[str, Any],
    animation_categories: dict[str, Any],
    ichiban_kuji_history: dict[str, Any],
    operations: dict[str, Any],
) -> dict[str, Any]:
    batches: list[dict[str, Any]] = []
    generic_source_report = load_json(GENERIC_SOURCE, {}) if GENERIC_SOURCE.exists() else {}
    gotouchi_report = load_json(GOTOUCHI, {}) if GOTOUCHI.exists() else {}

    def generic_source_review_summary(source_store: str) -> dict[str, int]:
        items = [
            item
            for item in generic_source_report.get("items", [])
            if isinstance(item, dict) and str(item.get("source_store") or "") == source_store
        ]
        candidate_statuses = Counter(str(item.get("candidate_status") or "no_candidate_report") for item in items)
        return {
            "review_rows": len(items),
            "candidate_rows": sum(1 for item in items if item.get("candidate_source_url")),
            "manual_confirmed_rows": sum(1 for item in items if item.get("manual_confirmed") is True),
            "weak_or_low_confidence_rows": sum(
                1
                for item in items
                if item.get("candidate_status") in {"weak_manual_review_candidate", "low_confidence_candidate"}
            ),
            "no_candidate_rows": candidate_statuses.get("no_candidate_report", 0),
        }

    def gotouchi_review_summary() -> dict[str, int]:
        summary = gotouchi_report.get("summary", {}) if isinstance(gotouchi_report, dict) else {}
        keys = (
            "rows_checked",
            "exact_type_candidate_rows",
            "motif_only_type_mismatch_rows",
            "no_official_candidate_rows",
            "attached_representative_rows",
            "visual_mismatch_rows",
        )
        return {key: int(summary.get(key) or 0) for key in keys}

    def review_state_for_batch(workstream: str, review_summary: dict[str, int] | None = None) -> str:
        if workstream == "generic_source_url_cleanup":
            if review_summary and review_summary.get("manual_confirmed_rows", 0) > 0:
                return "manual_confirmed_candidates_ready"
            if review_summary and review_summary.get("candidate_rows", 0) > 0:
                return "candidate_review_required"
            return "exact_source_discovery_required"
        if workstream == "gotouchi_official_candidate_review":
            if review_summary and review_summary.get("exact_type_candidate_rows", 0) > 0:
                return "official_exact_candidate_review_required"
            return "official_candidate_mismatch_review_required"
        if workstream == "image_url_attachment":
            return "source_discovery_then_image_attachment"
        if workstream == "source_url_discovery":
            return "exact_source_discovery_required"
        if workstream == "metadata_backlog":
            return "metadata_evidence_required"
        if workstream == "deduplication_review":
            return "manual_dedupe_review_required"
        if workstream.startswith("ichiban_kuji"):
            return "official_campaign_evidence_required"
        if workstream == "animation_category_review":
            return "taxonomy_mapping_required"
        return "manual_review_required"

    def next_machine_step_for_state(review_state: str) -> str:
        return {
            "manual_confirmed_candidates_ready": "prepare_reviewed_catalog_patch",
            "candidate_review_required": "open_candidate_report_and_verify_exact_product_identity",
            "exact_source_discovery_required": "find_exact_official_product_source_url",
            "official_exact_candidate_review_required": "verify_official_candidate_image_matches_row_type",
            "official_candidate_mismatch_review_required": "review_official_candidates_before_import",
            "source_discovery_then_image_attachment": "find_source_url_before_image_import",
            "metadata_evidence_required": "collect_official_metadata_evidence",
            "manual_dedupe_review_required": "compare_duplicate_group_evidence",
            "official_campaign_evidence_required": "verify_ichiban_campaign_page",
            "taxonomy_mapping_required": "map_category_to_folder_color_and_icon",
        }.get(review_state, "manual_review")

    def add_batch(
        *,
        agent_id: str,
        workstream: str,
        priority: int,
        title: str,
        public_report: Path,
        rows: int,
        recommended_action: str,
        acceptance_criteria: list[str],
        samples: list[dict[str, Any]],
        review_summary: dict[str, int] | None = None,
    ) -> None:
        if rows <= 0:
            return
        batch = {
            "batch_id": f"{priority:03d}-{agent_id}-{len(batches) + 1:02d}",
            "agent_id": agent_id,
            "workstream": workstream,
            "priority": priority,
            "title": title,
            "public_report": f"data/{public_report.name}",
            "rows": rows,
            "recommended_action": recommended_action,
            "acceptance_criteria": acceptance_criteria,
            "sample_items": samples[:8],
        }
        if review_summary is not None:
            batch["review_summary"] = review_summary
        review_state = review_state_for_batch(workstream, review_summary)
        batch["review_state"] = review_state
        batch["next_machine_step"] = next_machine_step_for_state(review_state)
        batches.append(batch)

    for group in image_enrichment_batches.get("groups", [])[:12]:
        workflow = str(group.get("workflow") or "")
        if workflow == "extract_from_existing_source_url":
            agent_id = "agent-image-existing-source"
            workstream = "image_url_attachment"
            batch_report = IMAGE_ENRICHMENT_BATCHES
        elif workflow == "replace_generic_source_then_extract_image":
            agent_id = "agent-generic-source-cleanup"
            workstream = "generic_source_url_cleanup"
            batch_report = GENERIC_SOURCE if GENERIC_SOURCE.exists() else IMAGE_ENRICHMENT_BATCHES
        elif workflow == "review_gotouchi_official_candidates":
            agent_id = "agent-gotouchi-review"
            workstream = "gotouchi_official_candidate_review"
            batch_report = GOTOUCHI if GOTOUCHI.exists() else IMAGE_ENRICHMENT_BATCHES
        else:
            agent_id = "agent-source-image"
            workstream = "image_url_attachment"
            batch_report = IMAGE_ENRICHMENT_BATCHES
        add_batch(
            agent_id=agent_id,
            workstream=workstream,
            priority=int(group.get("priority") or 99),
            title=f"{group.get('source_store')} 이미지 보강 ({workflow})",
            public_report=batch_report,
            rows=int(group.get("missing_image_rows") or 0),
            recommended_action=str(group.get("recommended_action") or "review image candidates"),
            acceptance_criteria=[
                "Exact product identity is verified before importing image_url.",
                "Rows without source_url must receive an exact source_url before image_url is accepted.",
                "No marketplace or unrelated stock image is imported without matching product evidence.",
            ],
            samples=[compact_sample(item) for item in group.get("sample_items", []) if isinstance(item, dict)],
            review_summary=(
                generic_source_review_summary(str(group.get("source_store") or ""))
                if workflow == "replace_generic_source_then_extract_image"
                else gotouchi_review_summary()
                if workflow == "review_gotouchi_official_candidates"
                else None
            ),
        )

    source_items = [item for item in source_discovery.get("items", []) if isinstance(item, dict)]
    source_grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in source_items:
        source_grouped[(str(item.get("workflow") or ""), str(item.get("source_store") or "unknown"))].append(item)
    for (workflow, store), items in sorted(
        source_grouped.items(),
        key=lambda pair: (DISCOVERY_PRIORITY.get(pair[0][0], 99), -len(pair[1]), pair[0][1]),
    )[:10]:
        add_batch(
            agent_id="agent-source-discovery",
            workstream="source_url_discovery",
            priority=20 + DISCOVERY_PRIORITY.get(workflow, 99),
            title=f"{store} 출처 URL 탐색 ({workflow})",
            public_report=SOURCE_DISCOVERY,
            rows=len(items),
            recommended_action="Find exact official product detail URLs and prepare source_url updates.",
            acceptance_criteria=[
                "Candidate URL is an exact official or trusted licensed product/detail page.",
                "Product title and image/metadata match the catalog row.",
                "Generic search/listing pages stay in review and are not imported as final source_url.",
            ],
            samples=[compact_sample(item) for item in items],
        )

    for group in metadata_backlog.get("groups", [])[:10]:
        add_batch(
            agent_id="agent-metadata",
            workstream="metadata_backlog",
            priority=60,
            title=f"{group.get('source_store')} {group.get('field')} 누락 보강",
            public_report=METADATA_BACKLOG,
            rows=int(group.get("missing_rows") or 0),
            recommended_action=str(group.get("recommended_action") or "verify missing metadata"),
            acceptance_criteria=[
                "Dates, prices, names, and barcodes are copied only from official or trusted evidence.",
                "Every proposed update includes catalog_index and source evidence.",
                "Unverified inferred metadata remains in the review queue.",
            ],
            samples=[compact_sample(item) for item in group.get("sample_items", []) if isinstance(item, dict)],
        )

    for group in deduplication.get("groups", [])[:10]:
        add_batch(
            agent_id="agent-dedupe",
            workstream="deduplication_review",
            priority=80 + DEDUPLICATION_KEY_PRIORITY.get(str(group.get("key_type")), 99),
            title=f"중복 후보 검토: {group.get('key_type')}",
            public_report=DEDUPLICATION,
            rows=len(group.get("rows") or []),
            recommended_action="Review keep/drop suggestions and prepare a manual-only dedupe decision.",
            acceptance_criteria=[
                "Variants, alternate prizes, and campaign-specific rows are preserved.",
                "Only evidence-backed exact duplicates are proposed for merge/delete.",
                "Auto-delete remains disabled.",
            ],
            samples=[compact_sample(item) for item in group.get("rows", []) if isinstance(item, dict)],
        )

    for group in ichiban_kuji_history.get("missing_release_date_campaigns", [])[:6]:
        add_batch(
            agent_id="agent-ichiban-kuji",
            workstream="ichiban_kuji_release_date",
            priority=110,
            title=f"이치방쿠지 발매일 확인: {group.get('slug') or group.get('title')}",
            public_report=ICHIIBAN_KUJI_HISTORY,
            rows=int(group.get("catalog_item_rows") or 0),
            recommended_action="Verify official campaign date before applying release_date to linked rows.",
            acceptance_criteria=[
                "Official 1kuji campaign page or captured official campaign data confirms the date.",
                "All updated catalog rows belong to the same campaign group.",
            ],
            samples=[
                {
                    "catalog_index": index,
                    "name_ko": name,
                    "source_url": group.get("url"),
                }
                for index, name in zip(group.get("sample_catalog_indexes", []), group.get("sample_names", []))
            ],
        )

    for group in ichiban_kuji_history.get("missing_official_price_jpy_campaigns", [])[:8]:
        add_batch(
            agent_id="agent-ichiban-kuji",
            workstream="ichiban_kuji_price",
            priority=120,
            title=f"이치방쿠지 가격 확인: {group.get('slug') or group.get('title')}",
            public_report=ICHIIBAN_KUJI_HISTORY,
            rows=int(group.get("catalog_item_rows") or 0),
            recommended_action="Verify official campaign price before applying official_price_jpy.",
            acceptance_criteria=[
                "Price is confirmed from official 1kuji campaign data.",
                "Non-prize collateral and campaign rows are not assigned a price unless evidence applies.",
            ],
            samples=[
                {
                    "catalog_index": index,
                    "name_ko": name,
                    "source_url": group.get("url"),
                }
                for index, name in zip(group.get("sample_catalog_indexes", []), group.get("sample_names", []))
            ],
        )

    unknown_categories = animation_categories.get("unknown_categories", [])
    if unknown_categories:
        add_batch(
            agent_id="agent-animation-taxonomy",
            workstream="animation_category_review",
            priority=140,
            title="애니메이션 굿즈 미분류 카테고리 정리",
            public_report=ANIMATION_CATEGORIES,
            rows=int(animation_categories.get("summary", {}).get("unknown_category_count") or 0),
            recommended_action="Map unknown categories to app folder families and visual tokens.",
            acceptance_criteria=[
                "Folder color hints follow folder_color_palette sort order.",
                "Icon choices use existing icon keys from folder_visual_tokens.",
                "Category changes remain review-only until app navigation impact is checked.",
            ],
            samples=[row for row in unknown_categories if isinstance(row, dict)],
        )

    batches.sort(key=lambda row: (row["priority"], -row["rows"], row["batch_id"]))
    by_workstream = Counter(str(batch["workstream"]) for batch in batches)
    by_agent = Counter(str(batch["agent_id"]) for batch in batches)
    top_next_batches = [
        {
            "batch_id": batch["batch_id"],
            "agent_id": batch["agent_id"],
            "workstream": batch["workstream"],
            "priority": batch["priority"],
            "rows": batch["rows"],
            "title": batch["title"],
            "public_report": batch["public_report"],
            "review_state": batch["review_state"],
            "next_machine_step": batch["next_machine_step"],
            **({"review_summary": batch["review_summary"]} if "review_summary" in batch else {}),
        }
        for batch in batches[:10]
    ]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "summary": {
            "batch_count": len(batches),
            "summed_batch_rows": sum(int(batch.get("rows") or 0) for batch in batches),
            "top_next_batch_count": len(top_next_batches),
            "by_workstream": by_workstream.most_common(),
            "by_agent": by_agent.most_common(),
            "open_review_queues": operations["summary"]["open_review_queues"],
        },
        "top_next_batches": top_next_batches,
        "instructions": [
            "Agent-ready public work queue generated from the public catalog reports.",
            "Use this file to split DB cleanup across agents without exposing private local data.",
            "Every proposed catalog mutation still needs exact source evidence and review before import.",
        ],
        "batches": batches[:80],
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "safe_for_github_pages": True,
            "reason": "This queue coordinates work; it does not contain credentials or private ownership data.",
        },
    }


def build_generic_source_patch_candidates_public(generated_at: str) -> dict[str, Any]:
    generic_source_report = load_json(GENERIC_SOURCE, {}) if GENERIC_SOURCE.exists() else {}
    items: list[dict[str, Any]] = []
    for item in generic_source_report.get("items", []):
        if not isinstance(item, dict) or not item.get("candidate_source_url"):
            continue
        candidate_status = str(item.get("candidate_status") or "candidate_review_required")
        confidence = (
            "manual_confirmed"
            if item.get("manual_confirmed") is True
            else "weak"
            if candidate_status == "weak_manual_review_candidate"
            else "low"
        )
        items.append(
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "current_source_url": item.get("current_source_url"),
                "candidate_source_url": item.get("candidate_source_url"),
                "candidate_image_url": item.get("candidate_image_url"),
                "candidate_title": item.get("candidate_title"),
                "candidate_score": item.get("candidate_score"),
                "candidate_status": candidate_status,
                "confidence": confidence,
                "proposed_fields": {
                    "source_url": item.get("candidate_source_url"),
                    "image_url": item.get("candidate_image_url"),
                },
                "review_required": True,
                "review_checks": [
                    "Candidate title must describe the exact same goods item or set.",
                    "Candidate image must visually match the catalog item, not only the same brand/store.",
                    "Generic storefront source_url must be replaced only after exact product identity is confirmed.",
                ],
            }
        )

    by_status = Counter(str(item.get("candidate_status") or "") for item in items)
    by_confidence = Counter(str(item.get("confidence") or "") for item in items)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "generic_source_review_patch_candidates",
        "summary": {
            "candidate_rows": len(items),
            "manual_confirmed_rows": by_confidence.get("manual_confirmed", 0),
            "weak_candidate_rows": by_confidence.get("weak", 0),
            "low_confidence_candidate_rows": by_confidence.get("low", 0),
            "auto_apply_enabled": False,
            "source_report": f"data/{GENERIC_SOURCE.name}",
            "by_candidate_status": by_status.most_common(),
            "by_confidence": by_confidence.most_common(),
        },
        "items": items,
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "reason": "These candidates came from generic storefront cleanup and may be related but not exact.",
        },
    }


def normalize_text_key(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_dedupe_name(value: Any) -> str:
    text = normalize_text_key(value)
    drop_chars = " \t\r\n-_/\\.,，、・:：;；'\"`´[](){}<>【】「」『』（）［］〈〉《》"
    return "".join(char for char in text if char not in drop_chars)


def normalize_url_key(value: Any) -> str:
    return normalize_text_key(value).rstrip("/")


def row_richness(item: dict[str, Any]) -> int:
    return sum(1 for field in PUBLIC_FIELDS if present(item.get(field)))


def dedupe_keys(item: dict[str, Any]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    name = normalize_text_key(item.get("name_ja") or item.get("name_ko"))
    normalized_name = normalize_dedupe_name(item.get("name_ja") or item.get("name_ko"))
    barcode = normalize_text_key(item.get("barcode"))
    if barcode:
        keys.append(("barcode", barcode))
    source_url = normalize_url_key(item.get("source_url"))
    if source_url and len(name) >= 6:
        keys.append(("source_url", f"{source_url}|{name}"))
    if source_url and len(normalized_name) >= 6 and normalized_name != name:
        keys.append(("source_url_normalized_name", f"{source_url}|{normalized_name}"))
    image_url = normalize_url_key(item.get("image_url"))
    if image_url:
        if len(name) >= 6:
            keys.append(("image_url", f"{image_url}|{name}"))
        if len(normalized_name) >= 6 and normalized_name != name:
            keys.append(("image_url_normalized_name", f"{image_url}|{normalized_name}"))
    return keys


def build_deduplication_public(items: list[dict[str, Any]], sample_groups: int = 80) -> dict[str, Any]:
    key_to_indices: dict[tuple[str, str], list[int]] = {}
    for index, item in enumerate(items):
        for key in dedupe_keys(item):
            key_to_indices.setdefault(key, []).append(index)

    def dedupe_review_metadata(key_type: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        categories = {str(row.get("category") or "") for row in rows if row.get("category")}
        stores = {str(row.get("source_store") or "") for row in rows if row.get("source_store")}
        image_urls = {str(row.get("image_url") or "") for row in rows if row.get("image_url")}
        source_urls = {str(row.get("source_url") or "") for row in rows if row.get("source_url")}
        barcodes = {str(row.get("barcode") or "") for row in rows if row.get("barcode")}
        evidence: list[str] = [key_type]
        if len(barcodes) == 1 and barcodes:
            evidence.append("same_barcode")
        if len(source_urls) == 1 and source_urls:
            evidence.append("same_source_url")
        if len(image_urls) == 1 and image_urls:
            evidence.append("same_image_url")
        if len(categories) > 1:
            evidence.append("category_mismatch")
        if len(stores) > 1:
            evidence.append("multi_store")

        if "category_mismatch" in evidence:
            review_risk = "variant_risk_review"
            recommended_action = "Compare product type/category before any merge; preserve variants if category is truly different."
            review_priority = 40
        elif key_type == "barcode" and "same_barcode" in evidence:
            review_risk = "strong_identity_review"
            recommended_action = "Verify names/images match the same product, then prefer the richer official row as keep."
            review_priority = 10
        elif key_type.startswith("source_url") and "same_source_url" in evidence:
            review_risk = "source_identity_review"
            recommended_action = "Verify rows point to the same product detail page before merge."
            review_priority = 20
        elif key_type.startswith("image_url") and "same_image_url" in evidence:
            review_risk = "image_identity_review"
            recommended_action = "Check that the shared image is not a reused lineup/placeholder image before merge."
            review_priority = 30
        else:
            review_risk = "manual_identity_review"
            recommended_action = "Review all evidence manually before proposing keep/drop."
            review_priority = 50

        return {
            "review_priority": review_priority,
            "review_risk": review_risk,
            "evidence": evidence,
            "recommended_action": recommended_action,
        }

    seen_groups: set[tuple[int, ...]] = set()
    groups: list[dict[str, Any]] = []
    duplicate_rows: set[int] = set()
    for key, indices in sorted(
        key_to_indices.items(),
        key=lambda pair: (DEDUPLICATION_KEY_PRIORITY.get(pair[0][0], 99), pair[0][1]),
    ):
        unique_indices = sorted(set(indices))
        if len(unique_indices) < 2:
            continue
        signature = tuple(unique_indices)
        if signature in seen_groups:
            continue
        seen_groups.add(signature)
        keep = max(unique_indices, key=lambda idx: (row_richness(items[idx]), -idx))
        drops = [idx for idx in unique_indices if idx != keep]
        duplicate_rows.update(drops)
        group_rows = [
            {
                "catalog_index": item.get("catalog_index", idx),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "category": item.get("category"),
                "barcode": item.get("barcode"),
                "source_url": item.get("source_url"),
                "image_url": item.get("image_url"),
                "richness": row_richness(item),
            }
            for idx in unique_indices
            for item in [items[idx]]
        ]
        review_metadata = dedupe_review_metadata(key[0], group_rows)
        groups.append(
            {
                "key_type": key[0],
                "key": key[1],
                "keep_catalog_index": items[keep].get("catalog_index", keep),
                "drop_catalog_indexes": [items[idx].get("catalog_index", idx) for idx in drops],
                **review_metadata,
                "rows": group_rows,
            }
        )

    by_key_type = Counter(group["key_type"] for group in groups)
    by_review_risk = Counter(group["review_risk"] for group in groups)
    groups.sort(
        key=lambda group: (
            int(group.get("review_priority") or 99),
            DEDUPLICATION_KEY_PRIORITY.get(str(group.get("key_type")), 99),
            -len(group.get("rows") or []),
            str(group.get("key") or ""),
        )
    )
    return {
        "schema_version": 1,
        "summary": {
            "rows": len(items),
            "duplicate_groups": len(groups),
            "duplicate_rows": len(duplicate_rows),
            "published_groups": min(sample_groups, len(groups)),
            "by_key_type": by_key_type.most_common(),
            "by_review_risk": by_review_risk.most_common(),
            "top_review_risk": groups[0]["review_risk"] if groups else None,
        },
        "automation_policy": {
            "auto_delete": False,
            "requires_manual_review": True,
            "reason": "Shared barcode/source/image evidence can still represent variants; public report is a review queue only.",
            "normalization": "Names are normalized only when barcode/source_url/image_url evidence is shared.",
            "excluded": "Broad same-name matches across different campaign URLs are excluded because they often represent legitimate variants.",
        },
        "groups": groups[:sample_groups],
    }


def category_family(category: str) -> str:
    for family, values in CATEGORY_FAMILIES.items():
        if category in values:
            return family
    return "other"


def color_sort_order(color_hint: str) -> int:
    for row in FOLDER_COLOR_PALETTE:
        if row["color_hint"] == color_hint:
            return int(row["sort_order"])
    return 999


def folder_visual_token(category: str, family: str, rows: int) -> dict[str, Any]:
    visual = FAMILY_VISUALS.get(family, FAMILY_VISUALS["other"])
    return {
        "category": category,
        "family": family,
        "rows": rows,
        "color_hint": visual["color_hint"],
        "color_hex": visual["color_hex"],
        "color_sort_order": color_sort_order(visual["color_hint"]),
        "primary_icon_key": visual["icon_key"],
        "icon_options": FAMILY_ICON_OPTIONS.get(family, FAMILY_ICON_OPTIONS["other"]),
    }


def counter_rows(counter: Counter[Any], keys: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for values, count in counter.most_common(limit):
        if not isinstance(values, tuple):
            values = (values,)
        item = {key: value for key, value in zip(keys, values)}
        item["rows"] = count
        rows.append(item)
    return rows


def is_animation_goods(item: dict[str, Any]) -> bool:
    if str(item.get("source_store") or "") in ANIMATION_STORES:
        return True
    affiliation = str(item.get("affiliation") or "")
    series = str(item.get("series_name") or "")
    return any(token in affiliation or token in series for token in ("단간론파", "주술회전", "헌터헌터", "프리렌", "최애의아이", "나의 히어로"))


def build_animation_categories_public(items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [item for item in items if is_animation_goods(item)]
    by_category = Counter(str(item.get("category") or "미분류") for item in rows)
    by_family = Counter(category_family(str(item.get("category") or "")) for item in rows)
    by_store_category = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or "미분류")) for item in rows
    )
    missing_image_by_category = Counter(
        str(item.get("category") or "미분류") for item in rows if not present(item.get("image_url"))
    )
    missing_source_by_category = Counter(
        str(item.get("category") or "미분류") for item in rows if not present(item.get("source_url"))
    )
    by_sub_series = Counter(str(item.get("sub_series") or "") for item in rows if present(item.get("sub_series")))

    category_visuals = []
    folder_visual_tokens = []
    for category, count in by_category.most_common(120):
        family = category_family(category)
        visual = FAMILY_VISUALS.get(family, FAMILY_VISUALS["other"])
        category_visuals.append(
            {
                "category": category,
                "family": family,
                "rows": count,
                "recommended_icon_key": visual["icon_key"],
                "recommended_color_hint": visual["color_hint"],
                "recommended_color_hex": visual["color_hex"],
            }
        )
        folder_visual_tokens.append(folder_visual_token(category, family, count))

    folder_visual_tokens.sort(
        key=lambda row: (
            row["color_sort_order"],
            str(row.get("family") or ""),
            str(row.get("category") or ""),
        )
    )

    suggestions = []
    for category, canonical in CANONICAL_CATEGORY_SUGGESTIONS.items():
        affected = [item for item in rows if item.get("category") == category]
        if not affected:
            continue
        suggestions.append(
            {
                "category": category,
                "suggested_category": canonical,
                "rows": len(affected),
                "risk": "medium",
                "reason": "Subtype-like category may work better as sub_series while using a broader app category.",
                "sample_names": [item.get("name_ko") for item in affected[:8]],
            }
        )

    unknown_categories = []
    for category, count in by_category.most_common():
        if category_family(category) != "other":
            continue
        suggestion = UNKNOWN_CATEGORY_REVIEW_SUGGESTIONS.get(
            category,
            {
                "suggested_family": "other",
                "suggested_category": category,
                "color_hint": "neutral",
                "primary_icon_key": "category",
                "review_priority": 90,
                "reason": "No exact mapping exists yet; keep in manual taxonomy review.",
            },
        )
        color_hint = str(suggestion["color_hint"])
        affected = [item for item in rows if str(item.get("category") or "") == category]
        unknown_categories.append(
            {
                "category": category,
                "rows": count,
                "review_priority": suggestion["review_priority"],
                "suggested_family": suggestion["suggested_family"],
                "suggested_category": suggestion["suggested_category"],
                "suggested_color_hint": color_hint,
                "suggested_color_hex": next(
                    (row["color_hex"] for row in FOLDER_COLOR_PALETTE if row["color_hint"] == color_hint),
                    FAMILY_VISUALS["other"]["color_hex"],
                ),
                "suggested_color_sort_order": color_sort_order(color_hint),
                "suggested_primary_icon_key": suggestion["primary_icon_key"],
                "suggested_icon_options": FAMILY_ICON_OPTIONS.get(
                    str(suggestion["suggested_family"]), FAMILY_ICON_OPTIONS["other"]
                ),
                "review_reason": suggestion["reason"],
                "sample_names": [item.get("name_ko") for item in affected[:8]],
            }
        )
    unknown_categories.sort(
        key=lambda row: (
            int(row.get("review_priority") or 99),
            int(row.get("suggested_color_sort_order") or 999),
            str(row.get("category") or ""),
        )
    )

    return {
        "schema_version": 1,
        "summary": {
            "animation_goods_rows": len(rows),
            "category_count": len(by_category),
            "unknown_category_count": len(unknown_categories),
            "unknown_category_rows": sum(int(row.get("rows") or 0) for row in unknown_categories),
            "normalization_suggestion_count": len(suggestions),
            "missing_image_rows": sum(1 for item in rows if not present(item.get("image_url"))),
            "missing_source_url_rows": sum(1 for item in rows if not present(item.get("source_url"))),
        },
        "category_families": counter_rows(by_family, ("family",), 40),
        "categories": counter_rows(by_category, ("category",), 120),
        "category_visuals": category_visuals,
        "folder_color_palette": FOLDER_COLOR_PALETTE,
        "folder_visual_tokens": folder_visual_tokens,
        "top_store_categories": counter_rows(by_store_category, ("source_store", "category"), 120),
        "missing_image_by_category": counter_rows(missing_image_by_category, ("category",), 60),
        "missing_source_url_by_category": counter_rows(missing_source_by_category, ("category",), 60),
        "top_sub_series": counter_rows(by_sub_series, ("sub_series",), 80),
        "normalization_suggestions": suggestions,
        "unknown_categories": unknown_categories[:80],
        "taxonomy_review_queue": unknown_categories[:80],
        "automation_policy": {
            "auto_apply_category_changes": False,
            "requires_manual_review": True,
            "reason": "Category changes affect app navigation and folder semantics; this public report is a review queue.",
        },
    }


def year_of(value: Any) -> str:
    text = str(value or "").strip()
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else "unknown"


def is_ichiban_kuji_item(item: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(item.get(field) or "")
        for field in ("source_url", "source_store", "series_name", "sub_series", "name_ko", "name_ja")
    )
    return "1kuji.com" in haystack or "一番くじ" in haystack or "이치방쿠지" in haystack


def campaign_slug(url: Any) -> str:
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    return text.split("/")[-1]


def build_ichiban_kuji_history_public(items: list[dict[str, Any]]) -> dict[str, Any]:
    campaigns = load_json(ICHIIBAN_KUJI_CAMPAIGNS, [])
    if not isinstance(campaigns, list):
        campaigns = []
    campaign_rows = [row for row in campaigns if isinstance(row, dict)]
    kuji_items = [item for item in items if is_ichiban_kuji_item(item)]

    campaign_by_url = {str(row.get("url") or "").rstrip("/"): row for row in campaign_rows}
    campaign_urls_in_catalog = {
        str(item.get("source_url") or "").rstrip("/")
        for item in kuji_items
        if "1kuji.com/products/" in str(item.get("source_url") or "")
    }
    campaign_with_catalog_rows = sorted(url for url in campaign_by_url if url in campaign_urls_in_catalog)
    missing_catalog_campaigns = sorted(url for url in campaign_by_url if url not in campaign_urls_in_catalog)

    by_campaign: Counter[str] = Counter()
    for item in kuji_items:
        url = str(item.get("source_url") or "").rstrip("/")
        if "1kuji.com/products/" in url:
            by_campaign[url] += 1

    by_campaign_year = Counter(year_of(row.get("release_date")) for row in campaign_rows)
    by_item_year = Counter(year_of(item.get("release_date")) for item in kuji_items)
    by_category = Counter(str(item.get("category") or "미분류") for item in kuji_items)
    by_sub_series = Counter(str(item.get("sub_series") or "미분류") for item in kuji_items)
    missing_release = [item for item in kuji_items if not present(item.get("release_date"))]
    missing_price = [item for item in kuji_items if not present(item.get("official_price_jpy"))]

    def item_group_key(item: dict[str, Any]) -> str:
        url = str(item.get("source_url") or "").strip().rstrip("/")
        if "1kuji.com/products/" in url:
            return url
        series = str(item.get("series_name") or "").strip()
        if series:
            return f"series:{series}"
        return "unknown"

    def grouped_item_backlog(backlog_items: list[dict[str, Any]], max_groups: int = 80) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in backlog_items:
            grouped[item_group_key(item)].append(item)

        rows: list[dict[str, Any]] = []
        for key, group_items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:max_groups]:
            url = key if key.startswith("http") else ""
            campaign = campaign_by_url.get(url, {})
            sample_items = group_items[:8]
            rows.append(
                {
                    "group_key": key,
                    "url": url or None,
                    "slug": campaign_slug(url),
                    "title": campaign.get("title") or sample_items[0].get("series_name"),
                    "release_date": campaign.get("release_date"),
                    "catalog_item_rows": len(group_items),
                    "sample_catalog_indexes": [item.get("catalog_index") for item in sample_items],
                    "sample_names": [
                        item.get("name_ko") or item.get("name_ja") or item.get("name_en")
                        for item in sample_items
                    ],
                    "review_action": "verify campaign detail page before applying inferred metadata",
                }
            )
        return rows

    missing_release_groups = grouped_item_backlog(missing_release)
    missing_price_groups = grouped_item_backlog(missing_price)
    campaign_metadata_review_by_key: dict[str, dict[str, Any]] = {}

    def merge_campaign_metadata_review(groups: list[dict[str, Any]], field: str, priority: int) -> None:
        for group in groups:
            key = str(group.get("group_key") or "")
            if key not in campaign_metadata_review_by_key:
                campaign_metadata_review_by_key[key] = {
                    "group_key": key,
                    "url": group.get("url"),
                    "slug": group.get("slug"),
                    "title": group.get("title"),
                    "release_date": group.get("release_date"),
                    "catalog_item_rows": group.get("catalog_item_rows", 0),
                    "missing_fields": [],
                    "review_priority": priority,
                    "sample_catalog_indexes": group.get("sample_catalog_indexes", []),
                    "sample_names": group.get("sample_names", []),
                    "source_evidence_required": "official_1kuji_campaign_page",
                    "recommended_action": "Verify official campaign page before applying missing campaign metadata.",
                }
            row = campaign_metadata_review_by_key[key]
            if field not in row["missing_fields"]:
                row["missing_fields"].append(field)
            row["review_priority"] = min(int(row.get("review_priority") or priority), priority)

    merge_campaign_metadata_review(missing_release_groups, "release_date", 10)
    merge_campaign_metadata_review(missing_price_groups, "official_price_jpy", 20)
    campaign_metadata_review_queue = sorted(
        campaign_metadata_review_by_key.values(),
        key=lambda row: (
            int(row.get("review_priority") or 99),
            -len(row.get("missing_fields") or []),
            -int(row.get("catalog_item_rows") or 0),
            str(row.get("slug") or row.get("group_key") or ""),
        ),
    )

    latest_campaigns = sorted(
        campaign_rows,
        key=lambda row: str(row.get("release_date") or ""),
        reverse=True,
    )[:20]

    return {
        "schema_version": 1,
        "summary": {
            "campaign_rows": len(campaign_rows),
            "catalog_kuji_item_rows": len(kuji_items),
            "campaigns_with_catalog_items": len(campaign_with_catalog_rows),
            "campaigns_without_catalog_items": len(missing_catalog_campaigns),
            "missing_release_date_rows": len(missing_release),
            "missing_release_date_campaign_groups": len(missing_release_groups),
            "missing_official_price_jpy_rows": len(missing_price),
            "missing_official_price_jpy_campaign_groups": len(missing_price_groups),
            "campaign_metadata_review_queue_rows": len(campaign_metadata_review_queue),
            "image_coverage": round(
                (len(kuji_items) - sum(1 for item in kuji_items if not present(item.get("image_url")))) / len(kuji_items),
                4,
            )
            if kuji_items
            else 0.0,
            "source_url_coverage": round(
                (len(kuji_items) - sum(1 for item in kuji_items if not present(item.get("source_url")))) / len(kuji_items),
                4,
            )
            if kuji_items
            else 0.0,
        },
        "campaigns_by_year": counter_rows(by_campaign_year, ("year",), 40),
        "catalog_items_by_year": counter_rows(by_item_year, ("year",), 40),
        "top_categories": counter_rows(by_category, ("category",), 40),
        "top_prize_labels": counter_rows(by_sub_series, ("sub_series",), 80),
        "top_campaigns_by_item_count": [
            {
                "url": url,
                "slug": campaign_slug(url),
                "title": campaign_by_url.get(url, {}).get("title"),
                "release_date": campaign_by_url.get(url, {}).get("release_date"),
                "catalog_item_rows": count,
            }
            for url, count in by_campaign.most_common(80)
        ],
        "latest_campaigns": latest_campaigns,
        "missing_catalog_campaign_samples": [
            {
                "url": url,
                "slug": campaign_slug(url),
                "title": campaign_by_url.get(url, {}).get("title"),
                "release_date": campaign_by_url.get(url, {}).get("release_date"),
            }
            for url in missing_catalog_campaigns[:80]
        ],
        "missing_release_date_samples": [
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "series_name": item.get("series_name"),
                "sub_series": item.get("sub_series"),
                "source_url": item.get("source_url"),
            }
            for item in missing_release[:80]
        ],
        "missing_release_date_campaigns": missing_release_groups,
        "missing_official_price_jpy_campaigns": missing_price_groups,
        "campaign_metadata_review_queue": campaign_metadata_review_queue[:120],
        "automation_policy": {
            "auto_import_campaigns": False,
            "requires_manual_review": True,
            "reason": "Campaign-level pages and prize rows are tracked separately; missing catalog links should be reviewed before import.",
        },
    }


def validate_public_files(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.exists():
            findings.append(f"missing:{path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            json.loads(text)
        for needle in PRIVACY_NEEDLES:
            if needle.lower() in text.lower():
                findings.append(f"{path.as_posix()} contains {needle}")
        if "???" in text:
            findings.append(f"{path.as_posix()} contains replacement placeholder ???")
    return findings


def validate_report_consistency(
    rows: int,
    missing: dict[str, int],
    source_discovery: dict[str, Any],
    metadata_backlog: dict[str, Any],
    image_enrichment_batches: dict[str, Any],
    deduplication: dict[str, Any],
    animation_categories: dict[str, Any],
    ichiban_kuji_history: dict[str, Any],
    generic_source_patch_candidates: dict[str, Any],
    operations: dict[str, Any],
    agent_work_queue: dict[str, Any],
) -> list[str]:
    findings: list[str] = []
    source_summary = source_discovery["summary"]
    metadata_summary = metadata_backlog["summary"]
    image_summary = image_enrichment_batches["summary"]
    dedupe_summary = deduplication["summary"]
    animation_summary = animation_categories["summary"]
    kuji_summary = ichiban_kuji_history["summary"]
    generic_patch_summary = generic_source_patch_candidates["summary"]
    operations_summary = operations["summary"]
    open_queues = operations_summary["open_review_queues"]
    agent_summary = agent_work_queue["summary"]
    batches = agent_work_queue.get("batches", [])
    top_next_batches = agent_work_queue.get("top_next_batches", [])

    expected_missing = {
        "source_url": missing["source_url"],
        "image_url": missing["image_url"],
        "release_date": missing["release_date"],
        "official_price_jpy": missing["official_price_jpy"],
        "barcode": missing["barcode"],
        "name_ja": missing["name_ja"],
    }
    if operations_summary.get("catalog_rows") != rows:
        findings.append("operations.catalog_rows does not match public catalog row count")
    if operations_summary.get("missing") != expected_missing:
        findings.append("operations.missing does not match generated missing counts")

    field_totals = metadata_summary.get("field_missing_totals", {})
    for field, expected in expected_missing.items():
        if field_totals.get(field) != expected:
            findings.append(f"metadata_backlog.field_missing_totals.{field} does not match missing counts")

    if source_summary.get("source_discovery_rows") != missing["source_url"]:
        findings.append("source_discovery_rows does not match missing source_url count")
    if image_summary.get("missing_image_rows") != missing["image_url"]:
        findings.append("image_enrichment missing_image_rows does not match missing image_url count")
    image_workflow_total = sum(
        int(image_summary.get(key, 0))
        for key in (
            "source_url_ready_rows",
            "generic_source_url_rows",
            "gotouchi_official_review_rows",
            "needs_source_discovery_rows",
            "manual_image_research_rows",
        )
    )
    if image_workflow_total != image_summary.get("missing_image_rows"):
        findings.append("image_enrichment workflow totals do not sum to missing_image_rows")

    expected_open_queues = {
        "source_discovery_rows": source_summary.get("source_discovery_rows", 0),
        "image_missing_rows": image_summary.get("missing_image_rows", 0),
        "dedupe_groups": dedupe_summary.get("duplicate_groups", 0),
        "animation_unknown_categories": animation_summary.get("unknown_category_count", 0),
        "ichiban_missing_release_date_rows": kuji_summary.get("missing_release_date_rows", 0),
        "ichiban_missing_price_rows": kuji_summary.get("missing_official_price_jpy_rows", 0),
        "generic_source_patch_candidate_rows": generic_patch_summary.get("candidate_rows", 0),
    }
    if open_queues != expected_open_queues:
        findings.append("operations.open_review_queues does not match source report summaries")
    taxonomy_review_queue = animation_categories.get("taxonomy_review_queue", [])
    unknown_categories = animation_categories.get("unknown_categories", [])
    if taxonomy_review_queue != unknown_categories:
        findings.append("animation_categories.taxonomy_review_queue does not match unknown_categories")
    if animation_summary.get("unknown_category_rows") != sum(
        int(row.get("rows") or 0) for row in taxonomy_review_queue if isinstance(row, dict)
    ):
        findings.append("animation_categories.unknown_category_rows does not match taxonomy review queue")
    for row in taxonomy_review_queue:
        if not isinstance(row, dict):
            findings.append("animation_categories.taxonomy_review_queue contains non-object row")
            continue
        required_taxonomy_fields = {
            "category",
            "rows",
            "review_priority",
            "suggested_family",
            "suggested_category",
            "suggested_color_hint",
            "suggested_color_hex",
            "suggested_primary_icon_key",
            "suggested_icon_options",
            "review_reason",
        }
        missing_taxonomy_fields = required_taxonomy_fields - set(row)
        if missing_taxonomy_fields:
            findings.append(f"animation taxonomy row missing fields: {sorted(missing_taxonomy_fields)}")

    campaign_metadata_review_queue = ichiban_kuji_history.get("campaign_metadata_review_queue", [])
    if kuji_summary.get("campaign_metadata_review_queue_rows") != len(campaign_metadata_review_queue):
        findings.append("ichiban_kuji_history.campaign_metadata_review_queue_rows does not match queue")
    for row in campaign_metadata_review_queue:
        if not isinstance(row, dict):
            findings.append("ichiban_kuji_history.campaign_metadata_review_queue contains non-object row")
            continue
        required_campaign_fields = {
            "group_key",
            "slug",
            "title",
            "catalog_item_rows",
            "missing_fields",
            "review_priority",
            "source_evidence_required",
            "recommended_action",
        }
        missing_campaign_fields = required_campaign_fields - set(row)
        if missing_campaign_fields:
            findings.append(f"ichiban metadata review row missing fields: {sorted(missing_campaign_fields)}")
        if not isinstance(row.get("missing_fields"), list) or not row.get("missing_fields"):
            findings.append("ichiban metadata review row has no missing_fields")

    store_matrix = operations.get("store_priority_matrix", [])
    if store_matrix:
        scores = [row.get("priority_score", 0) for row in store_matrix]
        if scores != sorted(scores, reverse=True):
            findings.append("operations.store_priority_matrix is not sorted by descending priority_score")
        if operations_summary.get("top_store_priority_score") != store_matrix[0].get("priority_score"):
            findings.append("operations.top_store_priority_score does not match first store priority")

    if agent_summary.get("open_review_queues") != expected_open_queues:
        findings.append("agent_work_queue.open_review_queues does not match source report summaries")
    if agent_summary.get("batch_count") != len(batches):
        findings.append("agent_work_queue.batch_count does not match published batches")
    if agent_summary.get("top_next_batch_count") != len(top_next_batches):
        findings.append("agent_work_queue.top_next_batch_count does not match top_next_batches")
    if agent_summary.get("summed_batch_rows") != sum(int(batch.get("rows", 0)) for batch in batches):
        findings.append("agent_work_queue.summed_batch_rows does not match published batches")
    if agent_summary.get("by_workstream") != Counter(str(batch.get("workstream") or "") for batch in batches).most_common():
        findings.append("agent_work_queue.by_workstream does not match published batches")
    if agent_summary.get("by_agent") != Counter(str(batch.get("agent_id") or "") for batch in batches).most_common():
        findings.append("agent_work_queue.by_agent does not match published batches")
    batch_priorities = [int(batch.get("priority", 999)) for batch in batches]
    if batch_priorities != sorted(batch_priorities):
        findings.append("agent_work_queue.batches are not sorted by ascending priority")
    expected_top_next_batches = [
        {
            "batch_id": batch["batch_id"],
            "agent_id": batch["agent_id"],
            "workstream": batch["workstream"],
            "priority": batch["priority"],
            "rows": batch["rows"],
            "title": batch["title"],
            "public_report": batch["public_report"],
            "review_state": batch["review_state"],
            "next_machine_step": batch["next_machine_step"],
            **({"review_summary": batch["review_summary"]} if "review_summary" in batch else {}),
        }
        for batch in batches[:10]
    ]
    if top_next_batches != expected_top_next_batches:
        findings.append("agent_work_queue.top_next_batches does not match first published batches")
    seen_batch_ids: set[str] = set()
    allowed_reports = {
        f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
        f"data/{SOURCE_DISCOVERY.name}",
        f"data/{METADATA_BACKLOG.name}",
        f"data/{DEDUPLICATION.name}",
        f"data/{ANIMATION_CATEGORIES.name}",
        f"data/{ICHIIBAN_KUJI_HISTORY.name}",
        f"data/{GENERIC_SOURCE.name}",
        f"data/{GOTOUCHI.name}",
    }
    required_batch_fields = {
        "batch_id",
        "agent_id",
        "workstream",
        "priority",
        "title",
        "public_report",
        "rows",
        "recommended_action",
        "acceptance_criteria",
        "sample_items",
        "review_state",
        "next_machine_step",
    }
    allowed_review_states = {
        "manual_confirmed_candidates_ready",
        "candidate_review_required",
        "exact_source_discovery_required",
        "official_exact_candidate_review_required",
        "official_candidate_mismatch_review_required",
        "source_discovery_then_image_attachment",
        "metadata_evidence_required",
        "manual_dedupe_review_required",
        "official_campaign_evidence_required",
        "taxonomy_mapping_required",
        "manual_review_required",
    }
    allowed_next_machine_steps = {
        "prepare_reviewed_catalog_patch",
        "open_candidate_report_and_verify_exact_product_identity",
        "find_exact_official_product_source_url",
        "verify_official_candidate_image_matches_row_type",
        "review_official_candidates_before_import",
        "find_source_url_before_image_import",
        "collect_official_metadata_evidence",
        "compare_duplicate_group_evidence",
        "verify_ichiban_campaign_page",
        "map_category_to_folder_color_and_icon",
        "manual_review",
    }
    for batch in batches:
        missing_fields = required_batch_fields - set(batch)
        if missing_fields:
            findings.append(f"agent_work_queue batch missing fields: {sorted(missing_fields)}")
            continue
        batch_id = str(batch.get("batch_id") or "")
        if batch_id in seen_batch_ids:
            findings.append(f"agent_work_queue duplicate batch_id: {batch_id}")
        seen_batch_ids.add(batch_id)
        if batch.get("public_report") not in allowed_reports:
            findings.append(f"agent_work_queue has unsupported public_report: {batch.get('public_report')}")
        if int(batch.get("rows") or 0) <= 0:
            findings.append(f"agent_work_queue batch has non-positive rows: {batch_id}")
        if not isinstance(batch.get("acceptance_criteria"), list) or not batch.get("acceptance_criteria"):
            findings.append(f"agent_work_queue batch missing acceptance criteria: {batch_id}")
        if not isinstance(batch.get("sample_items"), list):
            findings.append(f"agent_work_queue batch sample_items is not a list: {batch_id}")
        if batch.get("review_state") not in allowed_review_states:
            findings.append(f"agent_work_queue batch has unsupported review_state: {batch_id}")
        if batch.get("next_machine_step") not in allowed_next_machine_steps:
            findings.append(f"agent_work_queue batch has unsupported next_machine_step: {batch_id}")
        if batch.get("workstream") in {"generic_source_url_cleanup", "gotouchi_official_candidate_review"}:
            review_summary = batch.get("review_summary")
            if not isinstance(review_summary, dict) or not review_summary:
                findings.append(f"agent_work_queue batch missing review_summary: {batch_id}")
            elif any(not isinstance(value, int) or value < 0 for value in review_summary.values()):
                findings.append(f"agent_work_queue batch review_summary has invalid counts: {batch_id}")

    return findings


def update_reports(write: bool) -> dict[str, Any]:
    catalog = load_json(PUBLIC_CATALOG)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("items"), list):
        raise ValueError("data/catalog_public.json must have an items list")

    items: list[dict[str, Any]] = catalog["items"]
    rows = len(items)
    missing = missing_counts(items)
    cov = coverage(missing, rows, ["source_url", "image_url", "release_date"])
    generated_at = now_utc()
    source_discovery = build_source_discovery_public(items)
    metadata_backlog = build_metadata_backlog_public(items)
    image_enrichment_batches = build_image_enrichment_batches_public(items)
    deduplication = build_deduplication_public(items)
    animation_categories = build_animation_categories_public(items)
    ichiban_kuji_history = build_ichiban_kuji_history_public(items)
    generic_source_patch_candidates = build_generic_source_patch_candidates_public(generated_at)
    patch_candidate_items = generic_source_patch_candidates.get("items", [])
    patch_candidate_summary = generic_source_patch_candidates.get("summary", {})
    if patch_candidate_summary.get("candidate_rows") != len(patch_candidate_items):
        raise ValueError("generic source patch candidate count does not match item count")
    if patch_candidate_summary.get("auto_apply_enabled") is not False:
        raise ValueError("generic source patch candidates must stay manual-review only")
    operations = build_operations_public(
        generated_at,
        items,
        rows,
        missing,
        cov,
        source_discovery,
        metadata_backlog,
        image_enrichment_batches,
        deduplication,
        animation_categories,
        ichiban_kuji_history,
        generic_source_patch_candidates,
    )
    agent_work_queue = build_agent_work_queue_public(
        generated_at,
        source_discovery,
        metadata_backlog,
        image_enrichment_batches,
        deduplication,
        animation_categories,
        ichiban_kuji_history,
        operations,
    )

    public_meta = load_json(PUBLIC_META, {})
    public_meta.update(
        {
            "schema_version": public_meta.get("schema_version", 1),
            "generated_at": public_meta.get("generated_at") or catalog.get("meta", {}).get("generated_at"),
            "row_count": rows,
            "fields": PUBLIC_FIELDS,
            "missing": missing,
            "privacy": {
                "contains_user_accounts": False,
                "contains_local_folders": False,
                "contains_private_memos": False,
                "contains_device_profiles": False,
                "contains_server_tokens": False,
            },
        }
    )

    quality = load_json(QUALITY, {})
    quality_missing = {
        "source_url": missing["source_url"],
        "image_url": missing["image_url"],
        "release_date": missing["release_date"],
        "barcode": missing["barcode"],
        "series_name": missing["series_name"],
        "sub_series": missing["sub_series"],
        "official_price_jpy": missing["official_price_jpy"],
    }
    quality_changed = (
        quality.get("row_count") != rows
        or quality.get("missing") != quality_missing
        or quality.get("coverage") != cov
    )
    quality.update(
        {
            "schema_version": quality.get("schema_version", 1),
            "row_count": rows,
            "missing": quality_missing,
            "coverage": cov,
        }
    )
    if quality_changed:
        quality["generated_at"] = generated_at

    image_backlog = load_json(IMAGE_BACKLOG, {})
    summary = image_backlog.setdefault("summary", {})
    summary.update(
        {
            "rows": rows,
            "missing_images": missing["image_url"],
            "missing_with_source_url": sum(
                1 for item in items if present(item.get("source_url")) and not present(item.get("image_url"))
            ),
            "missing_with_exact_source_url": 0,
            "missing_with_generic_source_url": sum(
                1 for item in items if present(item.get("source_url")) and not present(item.get("image_url"))
            ),
        }
    )

    image_candidates = load_json(IMAGE_CANDIDATES, {})
    image_candidates.setdefault("summary", {})

    for target in (quality, image_backlog, image_candidates):
        if GOTOUCHI.exists():
            target["gotouchi_chiikawa_image_candidates"] = copy_report_summary(GOTOUCHI, "gotouchi")
        if REQUESTED.exists():
            target["requested_special_goods_review"] = copy_report_summary(REQUESTED, "requested")
        if GENERIC_SOURCE.exists():
            target["generic_source_cleanup_queue"] = copy_report_summary(GENERIC_SOURCE, "generic_source")
        target["generic_source_patch_candidates"] = {
            "public_report": f"data/{GENERIC_SOURCE_PATCH_CANDIDATES.name}",
            **generic_source_patch_candidates["summary"],
        }
        if SOURCE_DETAIL.exists():
            target["source_detail_candidate_probe"] = copy_report_summary(SOURCE_DETAIL, "source_detail")
        target["source_discovery_queue"] = {
            "public_report": f"data/{SOURCE_DISCOVERY.name}",
            **source_discovery["summary"],
        }
        target["metadata_backlog"] = {
            "public_report": f"data/{METADATA_BACKLOG.name}",
            **metadata_backlog["summary"],
        }
        target["image_enrichment_batches"] = {
            "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
            **image_enrichment_batches["summary"],
        }
        target["deduplication_review"] = {
            "public_report": f"data/{DEDUPLICATION.name}",
            **deduplication["summary"],
        }
        target["animation_category_review"] = {
            "public_report": f"data/{ANIMATION_CATEGORIES.name}",
            **animation_categories["summary"],
        }
        target["ichiban_kuji_history"] = {
            "public_report": f"data/{ICHIIBAN_KUJI_HISTORY.name}",
            **ichiban_kuji_history["summary"],
        }
        target["operations"] = {
            "public_report": f"data/{OPERATIONS_REPORT.name}",
            **operations["summary"]["open_review_queues"],
        }
        target["agent_work_queue"] = {
            "public_report": f"data/{AGENT_WORK_QUEUE.name}",
            **agent_work_queue["summary"],
        }

    consistency_findings = validate_report_consistency(
        rows,
        missing,
        source_discovery,
        metadata_backlog,
        image_enrichment_batches,
        deduplication,
        animation_categories,
        ichiban_kuji_history,
        generic_source_patch_candidates,
        operations,
        agent_work_queue,
    )
    if consistency_findings:
        raise ValueError("public report consistency validation failed: " + "; ".join(consistency_findings))

    public_files = [
        PUBLIC_CATALOG,
        PUBLIC_META,
        QUALITY,
        IMAGE_BACKLOG,
        IMAGE_CANDIDATES,
        DEDUPLICATION,
        ANIMATION_CATEGORIES,
        ICHIIBAN_KUJI_HISTORY,
        GOTOUCHI,
        REQUESTED,
        GENERIC_SOURCE,
        GENERIC_SOURCE_PATCH_CANDIDATES,
        SOURCE_DETAIL,
        SOURCE_DISCOVERY,
        METADATA_BACKLOG,
        IMAGE_ENRICHMENT_BATCHES,
        OPERATIONS_REPORT,
        AGENT_WORK_QUEUE,
    ]
    findings = validate_public_files([path for path in public_files if path.exists()])
    if findings:
        raise ValueError("public safety validation failed: " + "; ".join(findings))

    if write:
        write_json(SOURCE_DISCOVERY, source_discovery)
        write_json(METADATA_BACKLOG, metadata_backlog)
        write_json(IMAGE_ENRICHMENT_BATCHES, image_enrichment_batches)
        write_json(DEDUPLICATION, deduplication)
        write_json(ANIMATION_CATEGORIES, animation_categories)
        write_json(ICHIIBAN_KUJI_HISTORY, ichiban_kuji_history)
        write_json(OPERATIONS_REPORT, operations)
        write_json(AGENT_WORK_QUEUE, agent_work_queue)
        write_json(PUBLIC_META, public_meta)
        write_json(QUALITY, quality)
        write_json(IMAGE_BACKLOG, image_backlog)
        write_json(IMAGE_CANDIDATES, image_candidates)
        write_json(GENERIC_SOURCE_PATCH_CANDIDATES, generic_source_patch_candidates)

    return {
        "write": write,
        "rows": rows,
        "missing": missing,
        "coverage": cov,
        "updated_files": [
            str(PUBLIC_META.relative_to(ROOT)),
            str(QUALITY.relative_to(ROOT)),
            str(IMAGE_BACKLOG.relative_to(ROOT)),
            str(IMAGE_CANDIDATES.relative_to(ROOT)),
            str(GENERIC_SOURCE_PATCH_CANDIDATES.relative_to(ROOT)),
            str(SOURCE_DISCOVERY.relative_to(ROOT)),
            str(METADATA_BACKLOG.relative_to(ROOT)),
            str(IMAGE_ENRICHMENT_BATCHES.relative_to(ROOT)),
            str(DEDUPLICATION.relative_to(ROOT)),
            str(ANIMATION_CATEGORIES.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_HISTORY.relative_to(ROOT)),
            str(OPERATIONS_REPORT.relative_to(ROOT)),
            str(AGENT_WORK_QUEUE.relative_to(ROOT)),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(update_reports(write=args.write), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
