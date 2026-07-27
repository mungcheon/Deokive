from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from catalog_normalize import CATALOG_FIELDS, canonical_key, normalize_row

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "server" / "catalog_quality_report.json"
CORE_FIELDS = ("name_ko", "category", "character_name", "affiliation", "source_store")
ENRICHMENT_FIELDS = ("image_url", "source_url", "release_date", "barcode", "official_price_jpy")
SERVER_UNSUPPORTED_FIELDS = ("official_price_krw",)
GROUP_FIELDS = ("source_store", "category", "affiliation", "series_name", "sub_series")

SOURCE_GROUPS = {
    "chiikawa_official": (
        "치이카와 마켓",
        "나가노 마켓",
        "치이카와 파크",
        "치이카와 모구모구 혼포",
        "치이카와샵",
        "치이카와 포켓",
        "치이카와 중국 팝업스토어",
    ),
    "animation_goods": (
        "애니메이트",
        "Animate",
        "엔스카이",
        "Ensky",
        "굿스마일컴퍼니",
        "Good Smile",
        "Banpresto",
        "FuRyu",
        "코토부키야",
        "Kotobukiya",
        "Movic",
        "Taito",
        "프라이즈",
        "점프 캐릭터즈 스토어",
        "점프 숍",
        "메가하우스",
        "Cospa",
        "무기와라스토어",
        "밀짚모자 스토어",
        "귀멸의 칼날 공식",
        "Re-ment",
        "AmiAmi",
        "반다이",
        "Bandai Premium",
        "반다이 캔디",
        "Square Enix e-STORE",
        "SEGA",
        "Algonavis",
        "Hobby Max",
        "카도카와",
        "Phat! Company",
        "ALTER",
        "ufotable",
        "TOHO animation STORE",
        "하이큐!!",
    ),
    "kuji": ("이치방쿠지", "AnyMy", "치이카와 온라인 쿠지"),
    "korea_vtuber": ("Stellive", "이세계아이돌", "SVC", "아이돌 공식", "릴파 카페", "이세계 페스티벌"),
    "global_vtuber": (
        "Hololive",
        "Nijisanji",
        "Geek Jack",
    ),
    "kpop_official": (
        "Weverse",
        "JYP SHOP",
        "YG SELECT",
        "SM STORE",
        "Withmuu",
        "STARSHIP STORE",
        "CUBE STORE",
        "KQ FELLAZ",
        "IST STORE",
    ),
    "game_character_official": (
        "닌텐도 스토어",
        "포켓몬 센터",
        "산리오",
        "HoYoLAB Shop",
        "Cygames Store",
        "CAPCOM STORE",
        "ATLUS STORE",
        "Spike Chunsoft",
        "커비 카페",
    ),
    "retail_misc": ("MINISO", "팝업스토어", "DAISO", "롯데웰푸드", "두찜", "가챠", "가샤폰", "디즈니 스토어"),
}


def source_group(source_store: Any) -> str:
    store = str(source_store or "")
    for group, tokens in SOURCE_GROUPS.items():
        if any(token.lower() in store.lower() for token in tokens):
            return group
    return "other"


def _is_missing(row: dict[str, Any], field: str) -> bool:
    return row.get(field) in (None, "")


def _counter_rows(rows: list[dict[str, Any]], field: str, group_field: str, limit: int) -> list[dict[str, Any]]:
    counts = Counter(row.get(group_field) or "" for row in rows if _is_missing(row, field))
    return [{"value": value, "missing": count} for value, count in counts.most_common(limit)]


def _store_category_pairs(rows: list[dict[str, Any]], field: str, limit: int) -> list[dict[str, Any]]:
    counts = Counter(
        (
            row.get("source_store") or "",
            row.get("category") or "",
        )
        for row in rows
        if _is_missing(row, field)
    )
    return [
        {"source_store": store, "category": category, "missing": count}
        for (store, category), count in counts.most_common(limit)
    ]


def build_missing_breakdowns(rows: list[dict[str, Any]]) -> dict[str, Any]:
    breakdowns: dict[str, Any] = {}
    for field in ENRICHMENT_FIELDS:
        missing_rows = [row for row in rows if _is_missing(row, field)]
        breakdowns[field] = {
            "missing": len(missing_rows),
            "by_source_group": _counter_rows(rows, field, "_source_group", 20),
            "by_source_store": _counter_rows(rows, field, "source_store", 25),
            "by_category": _counter_rows(rows, field, "category", 25),
            "by_affiliation": _counter_rows(rows, field, "affiliation", 20),
            "by_series_name": _counter_rows(rows, field, "series_name", 20),
            "top_store_category_pairs": _store_category_pairs(rows, field, 40),
        }
    return breakdowns


def build_source_store_profiles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = []
    by_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_store[row.get("source_store") or ""].append(row)

    for store, store_rows in by_store.items():
        missing_counts = {field: sum(1 for row in store_rows if _is_missing(row, field)) for field in ENRICHMENT_FIELDS}
        profiles.append(
            {
                "source_store": store,
                "source_group": source_group(store),
                "rows": len(store_rows),
                "missing": missing_counts,
                "top_missing_categories": {
                    field: _counter_rows(store_rows, field, "category", 10)
                    for field in ENRICHMENT_FIELDS
                    if missing_counts[field]
                },
            }
        )

    profiles.sort(
        key=lambda profile: (
            -sum(profile["missing"].values()),
            -profile["rows"],
            profile["source_store"],
        )
    )
    return profiles


def build_multi_field_gaps(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, ...]] = Counter()
    examples: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        missing_fields = tuple(field for field in ENRICHMENT_FIELDS if _is_missing(row, field))
        if not missing_fields:
            continue
        counts[missing_fields] += 1
        examples.setdefault(
            missing_fields,
            {
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "category": row.get("category"),
            },
        )

    return [
        {
            "missing_fields": list(fields),
            "rows": count,
            "example": examples[fields],
        }
        for fields, count in counts.most_common(30)
    ]


def build_update_passes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = build_source_store_profiles(rows)
    passes = []
    for profile in profiles:
        missing = profile["missing"]
        relevant = {
            field: count
            for field, count in missing.items()
            if field in {"image_url", "source_url", "release_date", "barcode"} and count
        }
        if not relevant:
            continue
        if profile["source_group"] == "animation_goods":
            pass_type = "maker_or_retailer_scrape"
        elif profile["source_group"] == "chiikawa_official":
            pass_type = "official_shop_json_or_product_lookup"
        elif profile["source_group"] == "kuji":
            pass_type = "kuji_campaign_lookup"
        elif profile["source_group"] in {"kpop_official", "global_vtuber", "korea_vtuber"}:
            pass_type = "official_store_archive_or_manual_review"
        elif profile["source_group"] == "game_character_official":
            pass_type = "official_store_or_brand_lookup"
        else:
            pass_type = "manual_or_search_queue"
        passes.append(
            {
                "source_store": profile["source_store"],
                "source_group": profile["source_group"],
                "pass_type": pass_type,
                "rows": profile["rows"],
                "missing": relevant,
                "top_missing_categories": profile["top_missing_categories"],
            }
        )
    return passes[:50]


def load_catalog_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise SystemExit(f"{path} must contain a JSON list or an object with items")


GROUP_LIMIT = 40


def grouped_missing(
    rows: list[dict[str, Any]], field: str, group_field: str, limit: int = GROUP_LIMIT
) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get(field) not in (None, ""):
            continue
        group = str(row.get(group_field) or "(blank)")
        counter[group] += 1
        if len(examples[group]) < 5:
            examples[group].append(str(row.get("name_ko") or row.get("name_ja") or row.get("name_en") or ""))
    return [
        {"value": value, "missing": count, "sample_names": examples[value]}
        for value, count in counter.most_common(limit)
    ]


def grouped_missing_matrix(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        field: {
            "by_source_store": grouped_missing(rows, field, "source_store"),
            "by_category": grouped_missing(rows, field, "category"),
            "by_affiliation": grouped_missing(rows, field, "affiliation"),
        }
        for field in ENRICHMENT_FIELDS
    }


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [normalize_row(row) for row in rows if isinstance(row, dict)]
    for row in normalized:
        row["_source_group"] = source_group(row.get("source_store"))

    missing = {
        field: sum(1 for row in normalized if row.get(field) in (None, ""))
        for field in CATALOG_FIELDS
    }
    missing_examples = {
        field: [
            {
                "name_ko": row.get("name_ko"),
                "source_store": row.get("source_store"),
                "source_url": row.get("source_url"),
            }
            for row in normalized
            if row.get(field) in (None, "")
        ][:30]
        for field in ENRICHMENT_FIELDS
    }

    keys: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(normalized):
        keys[canonical_key(row)].append(index)

    duplicate_groups = [
        {
            "key_type": key[0],
            "key": key[1],
            "count": len(indices),
            "sample_names": [normalized[idx].get("name_ko") for idx in indices[:5]],
        }
        for key, indices in keys.items()
        if key[1] and len(indices) > 1
    ]
    duplicate_groups.sort(key=lambda group: (-group["count"], group["key"]))

    return {
        "rows": len(normalized),
        "core_fields": list(CORE_FIELDS),
        "enrichment_fields": list(ENRICHMENT_FIELDS),
        "server_unsupported_fields": list(SERVER_UNSUPPORTED_FIELDS),
        "group_fields": list(GROUP_FIELDS),
        "source_groups": {group: list(tokens) for group, tokens in SOURCE_GROUPS.items()},
        "missing": missing,
        "missing_core": {field: missing[field] for field in CORE_FIELDS},
        "missing_enrichment": {field: missing[field] for field in ENRICHMENT_FIELDS},
        "missing_breakdowns": build_missing_breakdowns(normalized),
        "multi_field_gaps": build_multi_field_gaps(normalized),
        "source_store_profiles": build_source_store_profiles(normalized),
        "recommended_update_passes": build_update_passes(normalized),
        "missing_examples": missing_examples,
        "duplicate_groups": len(duplicate_groups),
        "duplicate_rows": sum(group["count"] - 1 for group in duplicate_groups),
        "top_source_stores": Counter(row.get("source_store") or "" for row in normalized).most_common(25),
        "top_categories": Counter(row.get("category") or "" for row in normalized).most_common(40),
        "top_affiliations": Counter(row.get("affiliation") or "" for row in normalized).most_common(30),
        "missing_enrichment_groups": grouped_missing_matrix(normalized),
        "duplicates": duplicate_groups[:200],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = load_catalog_rows(args.input)
    report = build_report(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Rows: {report['rows']}")
    print(f"Duplicate groups: {report['duplicate_groups']}")
    print(f"Duplicate rows: {report['duplicate_rows']}")
    print("Missing:")
    for field, count in report["missing_core"].items():
        if count:
            print(f"  CORE {field}: {count}")
    for field, count in report["missing_enrichment"].items():
        if count:
            print(f"  enrich {field}: {count}")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
