from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue.json"
DEFAULT_JSON = ROOT / "server" / "catalog_image_enrichment_batch_plan.json"
DEFAULT_CSV = ROOT / "server" / "catalog_image_enrichment_batch_plan.csv"
DEFAULT_MD = ROOT / "server" / "catalog_image_enrichment_batch_plan.md"

BLOCKED_STRATEGIES = {
    "source_url_generic_storefront",
    "source_url_search_portal",
    "source_url_manual_review",
}
PROVIDER_STRATEGIES = {"official_search"}
PRIZE_STRATEGIES = {"prize_detail_validation", "prize_maker_search"}
MANUAL_SEARCH_STRATEGIES = {"manual_official_search_review"}

REPRESENTATIVE_HINTS = (
    "trading",
    "トレーディング",
    "collection",
    "コレクション",
    "box",
    "BOX",
    "랜덤",
    "블라인드",
    "세트",
    "セット",
)
INDIVIDUAL_HINTS = (
    "フィギュア",
    "ぬい",
    "인형",
    "마스코트",
    "아크릴 스탠드",
    "피규어",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _line_key(item: dict[str, Any], seed_row: dict[str, Any]) -> str:
    name = _compact_text(item.get("name_ja") or item.get("name_ko"))
    if not name:
        return "unknown"
    name = re.sub(r"[（(][^）)]{1,40}[）)]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    character = _compact_text(seed_row.get("character_name"))
    if character:
        for token in re.split(r"[\s/・,、]+", character):
            if len(token) >= 2:
                name = name.replace(token, "").strip()
    return name or _compact_text(item.get("category")) or "unknown"


def _batch_type(strategy: str) -> str:
    if strategy in PROVIDER_STRATEGIES:
        return "official_provider_matcher"
    if strategy in PRIZE_STRATEGIES:
        return "prize_detail_validation"
    if strategy in MANUAL_SEARCH_STRATEGIES:
        return "manual_official_search_review"
    if strategy in BLOCKED_STRATEGIES:
        return "exact_product_url_required"
    if strategy == "source_url_product_detail_lookup":
        return "exact_detail_image_extraction"
    return "manual_research_required"


def _image_granularity(item: dict[str, Any], seed_row: dict[str, Any]) -> str:
    text = " ".join(
        _compact_text(value)
        for value in (
            item.get("name_ko"),
            item.get("name_ja"),
            item.get("category"),
            seed_row.get("sub_series"),
        )
    )
    if any(hint in text for hint in REPRESENTATIVE_HINTS):
        return "representative_box_or_trading_image_ok"
    if _compact_text(seed_row.get("character_name")):
        return "individual_character_image_required"
    if re.search(r"[（(][^）)]{1,40}[）)]\s*$", _compact_text(item.get("name_ja") or item.get("name_ko"))):
        return "individual_character_image_required"
    if any(hint in text for hint in INDIVIDUAL_HINTS):
        return "individual_item_image_required"
    return "item_or_series_image_review"


def _next_action(batch_type: str, granularity: str) -> str:
    if batch_type == "official_provider_matcher":
        return "Run or improve a strict provider matcher, then import only title-verified detail-page images."
    if batch_type == "prize_detail_validation":
        return "Find exact prize detail pages first; broad search images should stay in review."
    if batch_type == "manual_official_search_review":
        return "Use the generated search URLs for human confirmation or add a provider parser."
    if batch_type == "exact_product_url_required":
        return "Replace storefront/search/campaign URLs with exact product URLs before image import."
    if batch_type == "exact_detail_image_extraction":
        return "Extract image from the same product page via JSON-LD, OG image, or product media."
    if granularity == "representative_box_or_trading_image_ok":
        return "One confirmed trading/box product image can cover the grouped row when the source URL is exact."
    return "Research manually and capture source_url plus image_url as a confirmed candidate."


def _review_artifacts(batch_type: str) -> dict[str, str]:
    if batch_type in {
        "exact_product_url_required",
        "official_provider_matcher",
        "manual_official_search_review",
        "manual_research_required",
    }:
        return {
            "manual_confirmation_template": "server/source_discovery_confirmed_rows.template.json",
            "confirmed_queue": "server/source_discovery_confirmed_rows.json",
            "import_tool": "tools/import_confirmed_source_discovery_rows.py",
            "unblocks_when": "exact_product_source_url_confirmed",
        }
    if batch_type == "exact_detail_image_extraction":
        return {
            "manual_confirmation_template": "server/catalog_image_candidate_import_queue.template.json",
            "confirmed_queue": "server/catalog_image_candidate_import_queue.json",
            "import_tool": "tools/import_manual_image_candidates.py",
            "unblocks_when": "same_product_page_image_url_confirmed",
        }
    if batch_type == "prize_detail_validation":
        return {
            "manual_confirmation_template": "server/official_detail_match_review.template.json",
            "confirmed_queue": "server/official_detail_match_review.json",
            "import_tool": "tools/import_confirmed_official_detail_matches.py",
            "unblocks_when": "exact_prize_detail_page_confirmed",
        }
    return {
        "manual_confirmation_template": "server/catalog_field_enrichment_queue.template.json",
        "confirmed_queue": "server/catalog_field_enrichment_queue.json",
        "import_tool": "tools/import_confirmed_catalog_field_rows.py",
        "unblocks_when": "manual_field_evidence_confirmed",
    }


def build(seed_path: Path, queue_path: Path) -> dict[str, Any]:
    seed_rows = _read_json(seed_path)
    queue_payload = _read_json(queue_path)
    queue = queue_payload.get("queue") or queue_payload.get("items") or []
    if not isinstance(seed_rows, list):
        raise ValueError(f"{seed_path} must contain a JSON list")
    if not isinstance(queue, list):
        raise ValueError(f"{queue_path} must contain queue/items list")

    grouped: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    enriched_items: list[dict[str, Any]] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        row_index = item.get("row_index")
        if not isinstance(row_index, int) or row_index < 0 or row_index >= len(seed_rows):
            continue
        seed_row = seed_rows[row_index] if isinstance(seed_rows[row_index], dict) else {}
        strategy = _compact_text(item.get("strategy"))
        batch_type = _batch_type(strategy)
        granularity = _image_granularity(item, seed_row)
        line_key = _line_key(item, seed_row)
        enriched = {
            **item,
            "batch_type": batch_type,
            "image_granularity": granularity,
            "line_key": line_key,
            "character_name": seed_row.get("character_name"),
            "sub_series": seed_row.get("sub_series"),
            "recommended_next_action": _next_action(batch_type, granularity),
            **_review_artifacts(batch_type),
        }
        enriched_items.append(enriched)
        grouped[
            (
                batch_type,
                _compact_text(item.get("source_store")),
                _compact_text(item.get("affiliation")),
                _compact_text(item.get("category")),
                granularity,
                line_key,
            )
        ].append(enriched)

    batches: list[dict[str, Any]] = []
    for index, (key, items) in enumerate(grouped.items(), start=1):
        batch_type, source_store, affiliation, category, granularity, line_key = key
        batches.append(
            {
                "batch_id": f"img-{index:04d}",
                "batch_type": batch_type,
                "source_store": source_store,
                "affiliation": affiliation,
                "category": category,
                "image_granularity": granularity,
                "line_key": line_key,
                "missing_images": len(items),
                "row_indexes": [item["row_index"] for item in items],
                "recommended_next_action": _next_action(batch_type, granularity),
                **_review_artifacts(batch_type),
                "samples": [
                    {
                        "row_index": item.get("row_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "character_name": item.get("character_name"),
                        "source_url": item.get("source_url"),
                        "search_url": item.get("search_url"),
                    }
                    for item in items[:8]
                ],
            }
        )

    priority = {
        "exact_detail_image_extraction": 0,
        "official_provider_matcher": 1,
        "prize_detail_validation": 2,
        "manual_official_search_review": 3,
        "exact_product_url_required": 4,
        "manual_research_required": 5,
    }
    batches.sort(
        key=lambda item: (
            priority.get(str(item.get("batch_type")), 99),
            -int(item.get("missing_images") or 0),
            str(item.get("source_store") or ""),
            str(item.get("affiliation") or ""),
        )
    )
    for index, batch in enumerate(batches, start=1):
        batch["rank"] = index

    by_batch_type = Counter(item["batch_type"] for item in enriched_items)
    by_granularity = Counter(item["image_granularity"] for item in enriched_items)
    by_store_batch_type = Counter(
        (item["source_store"], item["batch_type"]) for item in enriched_items
    )
    workstream_groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in enriched_items:
        workstream_groups[
            (
                item["batch_type"],
                _compact_text(item.get("source_store")),
                _compact_text(item.get("affiliation")),
                _compact_text(item.get("category")),
                item["image_granularity"],
            )
        ].append(item)

    workstreams: list[dict[str, Any]] = []
    for index, (key, items) in enumerate(workstream_groups.items(), start=1):
        batch_type, source_store, affiliation, category, granularity = key
        line_counter = Counter(_compact_text(item.get("line_key")) for item in items)
        workstreams.append(
            {
                "workstream_id": f"img-ws-{index:03d}",
                "batch_type": batch_type,
                "source_store": source_store,
                "affiliation": affiliation,
                "category": category,
                "image_granularity": granularity,
                "missing_images": len(items),
                "line_count": len(line_counter),
                "top_lines": [
                    {"line_key": line_key, "missing_images": count}
                    for line_key, count in line_counter.most_common(10)
                ],
                "recommended_next_action": _next_action(batch_type, granularity),
                **_review_artifacts(batch_type),
                "sample_row_indexes": [item["row_index"] for item in items[:20]],
                "samples": [
                    {
                        "row_index": item.get("row_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "search_url": item.get("search_url"),
                    }
                    for item in items[:8]
                ],
            }
        )
    workstreams.sort(
        key=lambda item: (
            priority.get(str(item.get("batch_type")), 99),
            -int(item.get("missing_images") or 0),
            str(item.get("source_store") or ""),
            str(item.get("affiliation") or ""),
        )
    )
    for index, workstream in enumerate(workstreams, start=1):
        workstream["rank"] = index

    return {
        "missing_images": len(enriched_items),
        "batch_count": len(batches),
        "workstream_count": len(workstreams),
        "by_batch_type": by_batch_type.most_common(),
        "by_image_granularity": by_granularity.most_common(),
        "top_store_batch_types": [
            {"source_store": store, "batch_type": batch_type, "missing_images": count}
            for (store, batch_type), count in by_store_batch_type.most_common(60)
        ],
        "workstreams": workstreams,
        "batches": batches,
        "items": enriched_items,
    }


def write_csv(payload: dict[str, Any], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "rank",
                "batch_id",
                "batch_type",
                "source_store",
                "affiliation",
                "category",
                "image_granularity",
                "line_key",
                "missing_images",
                "recommended_next_action",
                "row_indexes",
            ],
        )
        writer.writeheader()
        for batch in payload["batches"]:
            row = {key: batch.get(key) for key in writer.fieldnames}
            row["row_indexes"] = " ".join(str(item) for item in batch.get("row_indexes") or [])
            writer.writerow(row)


def write_workstream_csv(payload: dict[str, Any], path: Path) -> None:
    workstream_path = path.with_name(path.stem + "_workstreams" + path.suffix)
    with workstream_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "rank",
                "workstream_id",
                "batch_type",
                "source_store",
                "affiliation",
                "category",
                "image_granularity",
                "missing_images",
                "line_count",
                "recommended_next_action",
                "sample_row_indexes",
            ],
        )
        writer.writeheader()
        for workstream in payload["workstreams"]:
            row = {key: workstream.get(key) for key in writer.fieldnames}
            row["sample_row_indexes"] = " ".join(
                str(item) for item in workstream.get("sample_row_indexes") or []
            )
            writer.writerow(row)


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Catalog Image Enrichment Batch Plan",
        "",
        f"- Missing images: `{payload['missing_images']}`",
        f"- Workstreams: `{payload['workstream_count']}`",
        f"- Batches: `{payload['batch_count']}`",
        "",
        "## Batch Types",
        "",
    ]
    for label, count in payload["by_batch_type"]:
        lines.append(f"- `{label}`: `{count}`")
    lines.extend(["", "## Image Granularity", ""])
    for label, count in payload["by_image_granularity"]:
        lines.append(f"- `{label}`: `{count}`")
    lines.extend(["", "## Top Workstreams", ""])
    for workstream in payload["workstreams"][:30]:
        lines.append(
            f"- `{workstream['workstream_id']}` `{workstream['batch_type']}` "
            f"`{workstream['source_store']}` `{workstream['affiliation']}` "
            f"`{workstream['category']}` `{workstream['missing_images']}` rows, "
            f"`{workstream['line_count']}` lines"
        )
    lines.extend(["", "## Top Work Batches", ""])
    for batch in payload["batches"][:30]:
        samples = ", ".join(
            str(sample.get("name_ko") or sample.get("name_ja"))
            for sample in batch.get("samples", [])[:3]
        )
        lines.append(
            f"- `{batch['batch_id']}` `{batch['batch_type']}` "
            f"`{batch['source_store']}` `{batch['affiliation']}` "
            f"`{batch['category']}` `{batch['missing_images']}` rows - {samples}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build(args.seed, args.queue)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(payload, args.csv_output)
    write_workstream_csv(payload, args.csv_output)
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                "missing_images": payload["missing_images"],
                "workstream_count": payload["workstream_count"],
                "batch_count": payload["batch_count"],
                "by_batch_type": payload["by_batch_type"],
                "json": str(args.json_output),
                "csv": str(args.csv_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
