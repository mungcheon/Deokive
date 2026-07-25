from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue_current.json"
DEFAULT_SMOKE_MATRIX = ROOT / "server" / "catalog_image_provider_smoke_matrix_now.json"
DEFAULT_JSON = ROOT / "server" / "catalog_remaining_image_enrichment_audit_current.json"
DEFAULT_MD = ROOT / "server" / "catalog_remaining_image_enrichment_audit_current.md"
DEFAULT_CANDIDATE_REVIEW_FILES = [
    ROOT / "server" / "agent_image_candidates_import_queue_current.json",
    ROOT / "server" / "agent_image_candidates_import_queue_broad.json",
    ROOT / "server" / "agent_image_candidates_import_queue_all_current.json",
    ROOT / "server" / "agent_image_candidates_import_queue_targeted_current.json",
    ROOT / "server" / "catalog_image_existing_candidate_consolidated.json",
    ROOT / "server" / "catalog_image_query_exact_review_queue_current.json",
    ROOT / "server" / "web_image_search_candidates_top_missing_current.json",
    ROOT / "server" / "prize_provider_fallback_image_candidates_current.json",
]

PROBE_FILES = [
    ROOT / "server" / "image_probe_animate_40.json",
    ROOT / "server" / "image_probe_goodsmile_40.json",
    ROOT / "server" / "image_probe_banpresto_50.json",
    ROOT / "server" / "image_probe_furyu_50.json",
    ROOT / "server" / "image_probe_taito_30.json",
    ROOT / "server" / "image_probe_movic_30.json",
    ROOT / "server" / "image_probe_movic_42_current.json",
    ROOT / "server" / "catalog_image_ensky_search_parser_dryrun.json",
    ROOT / "server" / "catalog_image_movic_search_current_dryrun.json",
    ROOT / "server" / "catalog_image_kotobukiya_search_current_dryrun.json",
    ROOT / "server" / "catalog_image_sega_missing_current_dryrun.json",
    ROOT / "server" / "catalog_image_taito_search_current_dryrun.json",
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise ValueError("catalog source must be a JSON list or an object with items")


def _top(counter: Counter[Any], limit: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, count in counter.most_common(limit):
        if isinstance(key, tuple):
            row = {f"key_{index + 1}": value for index, value in enumerate(key)}
        else:
            row = {"key": key}
        row["count"] = count
        rows.append(row)
    return rows


def _sample(items: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    return [
        {
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "source_store": item.get("source_store"),
            "category": item.get("category"),
            "affiliation": item.get("affiliation"),
            "source_url": item.get("source_url"),
            "query": item.get("query"),
            "search_url": item.get("search_url"),
        }
        for item in items[:limit]
    ]


def _probe_summary() -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path in PROBE_FILES:
        if not path.exists():
            summaries.append({"file": str(path.relative_to(ROOT)), "status": "missing"})
            continue
        payload = _read_json(path)
        unresolved = payload.get("unresolved") if isinstance(payload, dict) else None
        summaries.append(
            {
                "file": str(path.relative_to(ROOT)),
                "status": "read",
                "filled": payload.get("filled") if isinstance(payload, dict) else None,
                "filled_changes": len(payload.get("filled_changes") or []) if isinstance(payload, dict) else None,
                "unresolved": len(unresolved or []) if isinstance(unresolved, list) else None,
            }
        )
    return summaries


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _mapping_to_counter(value: Any) -> Counter[str]:
    counter: Counter[str] = Counter()
    if isinstance(value, dict):
        for key, count in value.items():
            counter[str(key)] += int(count or 0)
        return counter
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                counter[str(item[0])] += int(item[1] or 0)
    return counter


def _candidate_review_summary(paths: list[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    rejected_reasons: Counter[str] = Counter()
    totals = Counter()
    for path in paths:
        if not path.exists():
            files.append({"file": _display_path(path), "status": "missing"})
            continue
        try:
            payload = _read_json(path)
        except Exception as exc:
            files.append({"file": _display_path(path), "status": "unreadable", "error": str(exc)})
            continue
        summary = payload.get("summary") if isinstance(payload, dict) else {}
        if not isinstance(summary, dict):
            summary = {}
        reason_counts = (
            summary.get("rejected_reasons")
            or payload.get("rejected_reason_counts")
            or payload.get("skipped_by_reason")
            or payload.get("skipped_reasons")
        )
        reasons = _mapping_to_counter(reason_counts)
        rejected_reasons.update(reasons)
        file_summary = {
            "file": _display_path(path),
            "status": "read",
            "candidate_files": summary.get("candidate_files"),
            "input_items": summary.get("input_items"),
            "preflight_passed_items": summary.get("preflight_passed_items"),
            "ready_items": summary.get("ready_items"),
            "review_items": summary.get("review_items"),
            "candidate_items": summary.get("candidate_items"),
            "candidate_rows": payload.get("candidate_rows") if isinstance(payload, dict) else None,
            "fallback_candidate_rows": summary.get("fallback_candidate_rows"),
            "rejected_items": summary.get("rejected_items"),
            "rejected_rows": payload.get("rejected_rows") if isinstance(payload, dict) else None,
            "rejected_reasons": reasons.most_common(12),
        }
        files.append(file_summary)
        for key in (
            "candidate_files",
            "input_items",
            "preflight_passed_items",
            "ready_items",
            "review_items",
            "candidate_items",
            "candidate_rows",
            "fallback_candidate_rows",
            "rejected_items",
            "rejected_rows",
        ):
            value = file_summary.get(key)
            if isinstance(value, int):
                totals[key] += value
    return {
        "files": files,
        "totals": dict(totals),
        "rejected_reasons": rejected_reasons.most_common(30),
        "ready_items": totals.get("ready_items", 0),
        "review_items": totals.get("review_items", 0),
        "preflight_passed_items": totals.get("preflight_passed_items", 0),
        "candidate_items": (
            totals.get("candidate_items", 0)
            + totals.get("candidate_rows", 0)
            + totals.get("review_items", 0)
            + totals.get("fallback_candidate_rows", 0)
        ),
    }


def _smoke_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = _read_json(path)
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("source_store") or ""): row
        for row in rows
        if isinstance(row, dict) and row.get("source_store")
    }


def _provider_blockers(
    by_store: Counter[str],
    by_store_strategy: Counter[tuple[str, str]],
    smoke_by_store: dict[str, dict[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    manual_strategies = {
        "manual_review",
        "manual_official_search_review",
        "source_url_generic_storefront",
        "source_url_search_portal",
        "source_url_manual_review",
    }
    for store, count in by_store.most_common():
        provider_count = sum(
            strategy_count
            for (strategy_store, strategy), strategy_count in by_store_strategy.items()
            if strategy_store == store and strategy not in manual_strategies
        )
        if provider_count <= 0:
            continue
        smoke = smoke_by_store.get(store, {})
        blockers.append(
            {
                "source_store": store,
                "provider_candidate_items": provider_count,
                "queue_items": count,
                "latest_processed_rows": smoke.get("latest_processed_rows"),
                "latest_image_filled": smoke.get("latest_image_filled"),
                "latest_current_image_filled": smoke.get("latest_current_image_filled"),
                "latest_image_fill_rate": smoke.get("latest_image_fill_rate"),
                "recommendation": smoke.get("recommendation") or "No current smoke-matrix recommendation.",
            }
        )
    blockers.sort(
        key=lambda item: (
            -(int(item.get("provider_candidate_items") or 0)),
            int(item.get("latest_current_image_filled") or 0),
            str(item.get("source_store") or ""),
        )
    )
    return blockers[:limit]


def build(
    seed_path: Path,
    queue_path: Path,
    smoke_matrix_path: Path = DEFAULT_SMOKE_MATRIX,
    candidate_review_files: list[Path] | None = None,
) -> dict[str, Any]:
    rows = _catalog_rows(_read_json(seed_path))
    queue_payload = _read_json(queue_path)
    queue = [item for item in queue_payload.get("queue", []) if isinstance(item, dict)]
    missing_rows_with_index = [
        (index, row)
        for index, row in enumerate(rows)
        if isinstance(row, dict) and not row.get("image_url")
    ]
    missing_rows = [row for _index, row in missing_rows_with_index]
    queue_row_indexes = {
        item.get("row_index")
        for item in queue
        if isinstance(item.get("row_index"), int) and not isinstance(item.get("row_index"), bool)
    }
    queue_catalog_indexes = {
        item.get("catalog_index")
        for item in queue
        if isinstance(item.get("catalog_index"), int) and not isinstance(item.get("catalog_index"), bool)
    }
    unqueued_missing_rows = [
        row
        for index, row in missing_rows_with_index
        if index not in queue_row_indexes
        and (
            not isinstance(row.get("catalog_index"), int)
            or isinstance(row.get("catalog_index"), bool)
            or row.get("catalog_index") not in queue_catalog_indexes
        )
    ]

    by_strategy = Counter(str(item.get("strategy") or "") for item in queue)
    by_store = Counter(str(item.get("source_store") or "") for item in queue)
    by_store_strategy = Counter(
        (str(item.get("source_store") or ""), str(item.get("strategy") or "")) for item in queue
    )
    by_category = Counter(str(item.get("category") or "") for item in queue)
    by_affiliation = Counter(str(item.get("affiliation") or "") for item in queue)
    missing_with_source = [
        row
        for row in missing_rows
        if str(row.get("source_url") or "").strip()
    ]
    missing_with_exact_source = [
        row
        for row in missing_with_source
        if _looks_product_specific(str(row.get("source_url") or ""))
    ]
    missing_with_generic_source = [
        row
        for row in missing_with_source
        if not _looks_product_specific(str(row.get("source_url") or ""))
    ]

    grouped_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_by_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in queue:
        grouped_by_strategy[str(item.get("strategy") or "")].append(item)
        grouped_by_store[str(item.get("source_store") or "")].append(item)

    blocked_or_manual = sum(
        count
        for strategy, count in by_strategy.items()
        if strategy
        in {
            "manual_review",
            "manual_official_search_review",
            "source_url_generic_storefront",
            "source_url_search_portal",
            "source_url_manual_review",
        }
    )
    provider_candidates = len(queue) - blocked_or_manual
    smoke_by_store = _smoke_rows(smoke_matrix_path)
    candidate_reviews = _candidate_review_summary(candidate_review_files or DEFAULT_CANDIDATE_REVIEW_FILES)

    return {
        "rows": len(rows),
        "catalog_source": str(seed_path),
        "missing_images": len(missing_rows),
        "queue_items": len(queue),
        "queued_missing_image_rows": len(queue),
        "unqueued_missing_image_rows": max(0, len(missing_rows) - len(queue)),
        "unqueued_missing_image_samples": _sample_rows(unqueued_missing_rows, 20),
        "provider_candidate_items": provider_candidates,
        "manual_or_blocked_items": blocked_or_manual,
        "missing_with_source_url": len(missing_with_source),
        "missing_with_exact_source_url": len(missing_with_exact_source),
        "missing_with_generic_source_url": len(missing_with_generic_source),
        "missing_with_generic_source_by_store": Counter(
            str(row.get("source_store") or "") for row in missing_with_generic_source
        ).most_common(30),
        "missing_with_generic_source_samples": _sample_rows(missing_with_generic_source, 20),
        "by_strategy": by_strategy.most_common(),
        "by_store": by_store.most_common(40),
        "by_store_strategy": _top(by_store_strategy, 60),
        "by_category": by_category.most_common(40),
        "by_affiliation": by_affiliation.most_common(40),
        "samples_by_strategy": {
            strategy: _sample(items)
            for strategy, items in sorted(grouped_by_strategy.items())
        },
        "samples_by_store": {
            store: _sample(items)
            for store, items in sorted(grouped_by_store.items())
        },
        "provider_blockers": _provider_blockers(by_store, by_store_strategy, smoke_by_store),
        "candidate_reviews": candidate_reviews,
        "probe_summary": _probe_summary(),
        "recommendations": [
            "Do not attach images from generic storefront URLs; collect exact product detail URLs first.",
            "Rows counted in missing_with_generic_source_url have a URL, but it is a storefront/home page, not item evidence.",
            "Keep official provider runs small and dry-run first; recent probes filled zero safe image matches.",
            "Use candidate_reviews.rejected_reasons to avoid re-importing stale or mismatched image candidates.",
            "Use product-specific source_url extraction before broad official search whenever possible.",
            "For animation goods, prioritize exact Japanese title and maker pages; generic Korean names are too ambiguous for safe image matching.",
        ],
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Remaining Image Enrichment Audit",
        "",
        f"- Catalog source: `{payload.get('catalog_source')}`",
        f"- Rows: `{payload['rows']}`",
        f"- Missing images: `{payload['missing_images']}`",
        f"- Queued missing image rows: `{payload.get('queued_missing_image_rows')}`",
        f"- Unqueued missing image rows: `{payload.get('unqueued_missing_image_rows')}`",
        f"- Provider candidate items: `{payload['provider_candidate_items']}`",
        f"- Manual or blocked items: `{payload['manual_or_blocked_items']}`",
        f"- Missing images with source URL: `{payload['missing_with_source_url']}`",
        f"- Exact source URL but no image: `{payload['missing_with_exact_source_url']}`",
        f"- Generic source URL but no image: `{payload['missing_with_generic_source_url']}`",
        "",
        "## Strategy Counts",
        "",
    ]
    for strategy, count in payload["by_strategy"]:
        lines.append(f"- `{strategy}`: `{count}`")
    lines.extend(["", "## Store Counts", ""])
    for store, count in payload["by_store"][:25]:
        lines.append(f"- `{store}`: `{count}`")
    lines.extend(["", "## Generic Source URL Blockers", ""])
    for store, count in payload["missing_with_generic_source_by_store"][:20]:
        lines.append(f"- `{store}`: `{count}`")
    lines.extend(["", "### Samples", ""])
    for item in payload["missing_with_generic_source_samples"][:12]:
        lines.append(
            f"- `{item.get('source_store')}` `{item.get('name_ko')}` -> {item.get('source_url')}"
        )
    lines.extend(["", "## Unqueued Missing Image Samples", ""])
    for item in payload.get("unqueued_missing_image_samples", [])[:12]:
        lines.append(
            f"- `{item.get('source_store')}` `{item.get('name_ko')}` -> {item.get('source_url')}"
        )
    lines.extend(["", "## Provider Blockers", ""])
    for item in payload.get("provider_blockers", [])[:20]:
        lines.append(
            f"- `{item['source_store']}`: provider candidates `{item['provider_candidate_items']}`, "
            f"latest image fills `{item.get('latest_image_filled')}`, "
            f"current fills `{item.get('latest_current_image_filled')}`"
        )
        lines.append(f"  - {item.get('recommendation')}")
    lines.extend(["", "## Candidate Review Outcomes", ""])
    review = payload.get("candidate_reviews") or {}
    totals = review.get("totals") or {}
    lines.append(f"- Ready items: `{review.get('ready_items')}`")
    lines.append(f"- Preflight passed items: `{review.get('preflight_passed_items')}`")
    lines.append(f"- Candidate items/rows: `{review.get('candidate_items')}`")
    lines.append(f"- Totals: `{json.dumps(totals, ensure_ascii=False)}`")
    lines.extend(["", "### Rejected Reasons", ""])
    for reason, count in (review.get("rejected_reasons") or [])[:20]:
        lines.append(f"- `{reason}`: `{count}`")
    lines.extend(["", "### Candidate Review Files", ""])
    for item in (review.get("files") or [])[:20]:
        lines.append(
            f"- `{item['file']}`: `{item['status']}`, ready `{item.get('ready_items')}`, "
            f"preflight `{item.get('preflight_passed_items')}`, rejected `{item.get('rejected_items') or item.get('rejected_rows')}`"
        )
    lines.extend(["", "## Probe Summary", ""])
    for item in payload["probe_summary"]:
        lines.append(
            f"- `{item['file']}`: `{item['status']}`, filled `{item.get('filled')}`, "
            f"unresolved `{item.get('unresolved')}`"
        )
    lines.extend(["", "## Recommendations", ""])
    for item in payload["recommendations"]:
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def _looks_product_specific(url: str) -> bool:
    lowered = url.strip().lower().rstrip("/")
    if not lowered.startswith(("http://", "https://")):
        return False
    generic_suffixes = {
        "pokemoncenter-online.com",
        "www.pokemoncenter-online.com",
        "fanding.kr/@stellive/shop",
        "shop.weverse.io/home",
    }
    if lowered.removeprefix("https://").removeprefix("http://") in generic_suffixes:
        return False
    product_markers = (
        "/products/",
        "/product/",
        "/item/",
        "/goods/",
        "/shop/",
        "/products/detail/",
        "iProductNo=",
    )
    return any(marker in lowered for marker in product_markers)


def _sample_rows(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    return [
        {
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
            "source_store": row.get("source_store"),
            "category": row.get("category"),
            "affiliation": row.get("affiliation"),
            "source_url": row.get("source_url"),
        }
        for row in rows[:limit]
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--smoke-matrix", type=Path, default=DEFAULT_SMOKE_MATRIX)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build(args.seed, args.queue, args.smoke_matrix)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                "missing_images": payload["missing_images"],
                "provider_candidate_items": payload["provider_candidate_items"],
                "manual_or_blocked_items": payload["manual_or_blocked_items"],
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
