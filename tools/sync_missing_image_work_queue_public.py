from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_QUEUE = DATA / "catalog_missing_image_work_queue_public.json"
DEFAULT_CSV = DATA / "catalog_missing_image_work_queue_public.csv"

OFFICIAL_SEARCH_STORES = {
    "FuRyu": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://furyuprize.com/search?keyword={query}"),
    "Taito": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://www.taito.co.jp/prize/search?keyword={query}"),
    "Banpresto": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://bsp-prize.jp/search/?q={query}"),
    "애니메이트": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}"),
    "엔스카이": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://www.enskyshop.com/products/list?name={query}"),
    "Movic": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}"),
    "코토부키야": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}"),
    "굿스마일컴퍼니": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}"),
    "굿스마일컴퍼니/Max Factory": ("official_search", "search_only", "candidate_provider_script_required", 10, "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}"),
    "점프 캐릭터즈 스토어": ("manual_official_search_review", "search_only_manual", "manual_confirmation_required", 20, "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}"),
    "반다이": ("manual_official_search_review", "search_only_manual", "manual_confirmation_required", 20, "https://p-bandai.jp/search/?q={query}"),
    "AmiAmi": ("manual_official_search_review", "search_only_manual", "manual_confirmation_required", 20, "https://www.amiami.jp/top/search/list?s_keywords={query}"),
    "Cospa": ("manual_official_search_review", "search_only_manual", "manual_confirmation_required", 20, "https://www.cospa.com/cospa/itemlist/id/00000/mode/title/page/1/series_index/{query}"),
    "SEGA": ("manual_official_search_review", "search_only_manual", "manual_confirmation_required", 20, "https://segaplaza.jp/search/?q={query}"),
    "Re-ment": ("manual_official_search_review", "search_only_manual", "manual_confirmation_required", 20, "https://www.re-ment.co.jp/?s={query}"),
}

FIELDNAMES = [
    "row_index",
    "name_ko",
    "name_ja",
    "name_en",
    "category",
    "affiliation",
    "source_store",
    "source_url",
    "source_url_is_generic",
    "source_url_is_product_detail",
    "strategy",
    "provider_status",
    "automation_safety",
    "priority",
    "query",
    "search_url",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    catalog = _load_json(args.catalog)
    queue = _load_json(args.queue)
    result = sync_queue(catalog, queue)
    if args.write:
        args.queue.write_text(json.dumps(result["queue"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(result["queue"]["items"], args.csv_output)
    print(
        json.dumps(
            {
                **result["summary"],
                "json": str(args.queue),
                "csv": str(args.csv_output),
                "write": args.write,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def sync_queue(catalog: dict[str, Any], queue: dict[str, Any]) -> dict[str, Any]:
    missing_rows = _missing_image_rows(catalog)
    existing_items = [item for item in queue.get("items", []) if isinstance(item, dict)]
    existing_by_index = {
        item.get("row_index"): dict(item)
        for item in existing_items
        if isinstance(item.get("row_index"), int) and not isinstance(item.get("row_index"), bool)
    }
    new_items: list[dict[str, Any]] = []
    added_items: list[dict[str, Any]] = []
    refreshed_items = 0

    for row in missing_rows:
        catalog_index = row.get("catalog_index")
        if not isinstance(catalog_index, int) or isinstance(catalog_index, bool):
            continue
        existing = existing_by_index.get(catalog_index)
        if existing:
            item = _refresh_existing_item(existing, row)
            if item != existing:
                refreshed_items += 1
        else:
            item = _new_queue_item(row)
            added_items.append(item)
        new_items.append(item)

    new_items.sort(key=lambda item: (int(item.get("priority") or 999), int(item.get("row_index") or 10**9)))
    summary_queue = _build_queue_payload(new_items, source_queue=queue)
    return {
        "summary": {
            "catalog_missing_image_rows": len(missing_rows),
            "previous_queue_rows": len(existing_items),
            "synced_queue_rows": len(new_items),
            "added_queue_rows": len(added_items),
            "refreshed_queue_rows": refreshed_items,
            "removed_non_missing_queue_rows": max(0, len(existing_items) - len(new_items) + len(added_items)),
            "coverage_matches_catalog_missing_images": len(new_items) == len(missing_rows),
        },
        "queue": summary_queue,
        "added_items": added_items,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _missing_image_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise SystemExit("catalog must contain items")
    return [
        item
        for item in items
        if isinstance(item, dict) and not (_present(item.get("image_url")) or _present(item.get("local_image_path")))
    ]


def _refresh_existing_item(item: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    refreshed = dict(item)
    for field in ("name_ko", "name_ja", "name_en", "category", "affiliation", "source_store", "source_url"):
        refreshed[field] = row.get(field)
    source_url = str(row.get("source_url") or "").strip()
    refreshed["source_url_is_generic"] = bool(refreshed.get("source_url_is_generic")) and bool(source_url)
    refreshed["source_url_is_product_detail"] = bool(refreshed.get("source_url_is_product_detail")) and bool(source_url)
    if not refreshed.get("query"):
        refreshed["query"] = _query(row)
    expected_search_url = _search_url(row, str(refreshed.get("query") or ""))
    if expected_search_url and refreshed.get("strategy") in {"official_search", "manual_official_search_review"}:
        refreshed["search_url"] = expected_search_url
    elif not refreshed.get("search_url"):
        refreshed["search_url"] = expected_search_url
    return refreshed


def _new_queue_item(row: dict[str, Any]) -> dict[str, Any]:
    source_url = str(row.get("source_url") or "").strip()
    strategy, provider_status, automation_safety, priority, _template = _strategy_for(row)
    query = _query(row)
    return {
        "row_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "name_en": row.get("name_en"),
        "category": row.get("category"),
        "affiliation": row.get("affiliation"),
        "source_store": row.get("source_store"),
        "source_url": source_url or None,
        "source_url_is_generic": False,
        "source_url_is_product_detail": False,
        "strategy": strategy,
        "provider_status": provider_status,
        "automation_safety": automation_safety,
        "priority": priority,
        "query": query,
        "search_url": _search_url(row, query),
    }


def _strategy_for(row: dict[str, Any]) -> tuple[str, str, str, int, str | None]:
    source_url = str(row.get("source_url") or "").strip()
    if source_url:
        return (
            "source_url_manual_review",
            "ambiguous_source",
            "manual_confirmation_required",
            30,
            None,
        )
    store = str(row.get("source_store") or "").strip()
    if store in OFFICIAL_SEARCH_STORES:
        return OFFICIAL_SEARCH_STORES[store]
    return (
        "manual_review",
        "manual_only",
        "manual_research_required",
        50,
        None,
    )


def _query(row: dict[str, Any]) -> str:
    return str(row.get("name_ja") or row.get("name_ko") or "").strip()


def _search_url(row: dict[str, Any], query: str) -> str | None:
    _strategy, _provider_status, _automation_safety, _priority, template = _strategy_for(row)
    if not query:
        return None
    encoded = urllib.parse.quote(query)
    if template:
        return template.format(query=encoded)
    return "https://www.google.com/search?q=" + encoded


def _build_queue_payload(items: list[dict[str, Any]], *, source_queue: dict[str, Any]) -> dict[str, Any]:
    by_strategy = Counter(str(item.get("strategy") or "") for item in items)
    by_provider_status = Counter(str(item.get("provider_status") or "") for item in items)
    by_automation_safety = Counter(str(item.get("automation_safety") or "") for item in items)
    by_store = Counter(str(item.get("source_store") or "") for item in items)
    by_category = Counter(str(item.get("category") or "") for item in items)
    top_store_categories = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or ""))
        for item in items
    )
    top_strategy_stores = Counter(
        (str(item.get("strategy") or ""), str(item.get("source_store") or ""))
        for item in items
    )
    queue = {
        **{key: value for key, value in source_queue.items() if key not in {"items", "queue"}},
        "generated_at": _now_utc(),
        "missing_images": len(items),
        "by_strategy": _counter_pairs(by_strategy),
        "by_provider_status": _counter_pairs(by_provider_status),
        "by_automation_safety": _counter_pairs(by_automation_safety),
        "by_store": _counter_pairs(by_store),
        "by_category": _counter_pairs(by_category),
        "top_store_categories": [
            [store, category, rows]
            for (store, category), rows in top_store_categories.most_common(40)
        ],
        "top_strategy_stores": [
            [strategy, store, rows]
            for (strategy, store), rows in top_strategy_stores.most_common(40)
        ],
        "queue": items,
        "items": items,
        "samples_by_strategy": _samples_by(items, "strategy"),
        "samples_by_store": _samples_by(items, "source_store"),
    }
    return queue


def _counter_pairs(counter: Counter[str], limit: int = 40) -> list[list[Any]]:
    return [[key, count] for key, count in counter.most_common(limit)]


def _samples_by(items: list[dict[str, Any]], field: str, limit: int = 5) -> dict[str, list[dict[str, Any]]]:
    samples: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = str(item.get(field) or "")
        bucket = samples.setdefault(key, [])
        if len(bucket) < limit:
            bucket.append({name: item.get(name) for name in FIELDNAMES})
    return samples


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_csv(items: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            writer.writerow(item)


if __name__ == "__main__":
    raise SystemExit(main())
