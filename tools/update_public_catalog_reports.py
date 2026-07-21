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
SOURCE_DETAIL = DATA / "source_detail_probe_public.json"
SOURCE_DISCOVERY = DATA / "source_discovery_queue_public.json"
METADATA_BACKLOG = DATA / "catalog_metadata_backlog_public.json"

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
        groups.append(
            {
                "key_type": key[0],
                "key": key[1],
                "keep_catalog_index": items[keep].get("catalog_index", keep),
                "drop_catalog_indexes": [items[idx].get("catalog_index", idx) for idx in drops],
                "rows": [
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
                ],
            }
        )

    by_key_type = Counter(group["key_type"] for group in groups)
    groups.sort(
        key=lambda group: (
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

    unknown_categories = [
        {"category": category, "rows": count}
        for category, count in by_category.most_common()
        if category_family(category) == "other"
    ]

    return {
        "schema_version": 1,
        "summary": {
            "animation_goods_rows": len(rows),
            "category_count": len(by_category),
            "unknown_category_count": len(unknown_categories),
            "normalization_suggestion_count": len(suggestions),
            "missing_image_rows": sum(1 for item in rows if not present(item.get("image_url"))),
            "missing_source_url_rows": sum(1 for item in rows if not present(item.get("source_url"))),
        },
        "category_families": counter_rows(by_family, ("family",), 40),
        "categories": counter_rows(by_category, ("category",), 120),
        "category_visuals": category_visuals,
        "top_store_categories": counter_rows(by_store_category, ("source_store", "category"), 120),
        "missing_image_by_category": counter_rows(missing_image_by_category, ("category",), 60),
        "missing_source_url_by_category": counter_rows(missing_source_by_category, ("category",), 60),
        "top_sub_series": counter_rows(by_sub_series, ("sub_series",), 80),
        "normalization_suggestions": suggestions,
        "unknown_categories": unknown_categories[:80],
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
    deduplication = build_deduplication_public(items)
    animation_categories = build_animation_categories_public(items)
    ichiban_kuji_history = build_ichiban_kuji_history_public(items)

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
        SOURCE_DETAIL,
        SOURCE_DISCOVERY,
        METADATA_BACKLOG,
    ]
    findings = validate_public_files([path for path in public_files if path.exists()])
    if findings:
        raise ValueError("public safety validation failed: " + "; ".join(findings))

    if write:
        write_json(SOURCE_DISCOVERY, source_discovery)
        write_json(METADATA_BACKLOG, metadata_backlog)
        write_json(DEDUPLICATION, deduplication)
        write_json(ANIMATION_CATEGORIES, animation_categories)
        write_json(ICHIIBAN_KUJI_HISTORY, ichiban_kuji_history)
        write_json(PUBLIC_META, public_meta)
        write_json(QUALITY, quality)
        write_json(IMAGE_BACKLOG, image_backlog)
        write_json(IMAGE_CANDIDATES, image_candidates)

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
            str(SOURCE_DISCOVERY.relative_to(ROOT)),
            str(METADATA_BACKLOG.relative_to(ROOT)),
            str(DEDUPLICATION.relative_to(ROOT)),
            str(ANIMATION_CATEGORIES.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_HISTORY.relative_to(ROOT)),
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
