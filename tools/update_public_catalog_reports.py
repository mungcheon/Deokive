from __future__ import annotations

import argparse
import json
import urllib.parse
from collections import Counter
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
GOTOUCHI = DATA / "gotouchi_chiikawa_image_candidates_public.json"
REQUESTED = DATA / "requested_special_goods_public.json"
GENERIC_SOURCE = DATA / "generic_source_cleanup_public.json"
SOURCE_DETAIL = DATA / "source_detail_probe_public.json"
SOURCE_DISCOVERY = DATA / "source_discovery_queue_public.json"

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
    "image_url": 30,
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


def normalize_text_key(value: Any) -> str:
    return str(value or "").strip().lower()


def row_richness(item: dict[str, Any]) -> int:
    return sum(1 for field in PUBLIC_FIELDS if present(item.get(field)))


def dedupe_keys(item: dict[str, Any]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    name = normalize_text_key(item.get("name_ja") or item.get("name_ko"))
    barcode = normalize_text_key(item.get("barcode"))
    if barcode:
        keys.append(("barcode", barcode))
    source_url = normalize_text_key(item.get("source_url"))
    if source_url and len(name) >= 6:
        keys.append(("source_url", f"{source_url}|{name}"))
    image_url = normalize_text_key(item.get("image_url"))
    if image_url:
        if len(name) >= 6:
            keys.append(("image_url", f"{image_url}|{name}"))
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
        },
        "groups": groups[:sample_groups],
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
    deduplication = build_deduplication_public(items)

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
        target["deduplication_review"] = {
            "public_report": f"data/{DEDUPLICATION.name}",
            **deduplication["summary"],
        }

    public_files = [
        PUBLIC_CATALOG,
        PUBLIC_META,
        QUALITY,
        IMAGE_BACKLOG,
        IMAGE_CANDIDATES,
        DEDUPLICATION,
        GOTOUCHI,
        REQUESTED,
        GENERIC_SOURCE,
        SOURCE_DETAIL,
        SOURCE_DISCOVERY,
    ]
    findings = validate_public_files([path for path in public_files if path.exists()])
    if findings:
        raise ValueError("public safety validation failed: " + "; ".join(findings))

    if write:
        write_json(SOURCE_DISCOVERY, source_discovery)
        write_json(DEDUPLICATION, deduplication)
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
            str(DEDUPLICATION.relative_to(ROOT)),
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
