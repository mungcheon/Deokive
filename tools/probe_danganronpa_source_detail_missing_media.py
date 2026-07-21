from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_detail_candidates as detail_candidates
import build_source_discovery_queue as source_discovery


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = ROOT / "data" / "danganronpa_missing_media_public.json"
DEFAULT_REPORT = ROOT / "data" / "danganronpa_source_detail_probe_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def _to_source_detail_queue(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for item in items:
        query = source_discovery._query(item)
        official_search_url = source_discovery._format_url(
            source_discovery._official_template_for(item),
            query,
        )
        queue.append(
            {
                **item,
                "row_index": item.get("catalog_index"),
                "query": query,
                "official_search_url": official_search_url,
            }
        )
    return queue


def _source_kind(item: dict[str, Any]) -> str:
    value = str(item.get("source_kind") or "").strip()
    if value:
        return value
    store = str(item.get("source_store") or "").strip()
    if store in {"AmiAmi", "\uc560\ub2c8\uba54\uc774\ud2b8"}:
        return "licensed_retailer"
    if store in {"Taito", "FuRyu"}:
        return "official_prize"
    return "official_manufacturer"


def build_report(
    missing_media_items: list[dict[str, Any]],
    *,
    source_store: str | None = None,
    max_rows: int | None = None,
    sleep_seconds: float = 0.0,
    time_budget_seconds: float | None = None,
) -> dict[str, Any]:
    queue_items = _to_source_detail_queue(missing_media_items)
    scan_payload = detail_candidates.build_candidates(
        {"items": queue_items},
        source_store=source_store,
        max_rows=max_rows,
        sleep_seconds=sleep_seconds,
        max_consecutive_rate_limits=1,
        time_budget_seconds=time_budget_seconds,
    )

    result_by_index = {result.get("row_index"): result for result in scan_payload.get("results") or []}
    failure_by_index = {failure.get("row_index"): failure for failure in scan_payload.get("failures") or []}

    rows: list[dict[str, Any]] = []
    for item in queue_items:
        if source_store and item.get("source_store") != source_store:
            continue
        if max_rows is not None and len(rows) >= max_rows:
            break
        row_index = item.get("row_index")
        result = result_by_index.get(row_index)
        failure = failure_by_index.get(row_index)
        status = result.get("status") if result else None
        if not status:
            status = "fetch_failed" if failure else "not_scanned"
        top_candidates = (result or {}).get("top_candidates") or []
        rows.append(
            {
                "catalog_index": item.get("catalog_index"),
                "row_index": row_index,
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "source_kind": _source_kind(item),
                "query": item.get("query"),
                "official_search_url": item.get("official_search_url"),
                "status": status,
                "candidate_count": (result or {}).get("candidate_count", 0),
                "top_candidates": top_candidates[:5],
                "failure": failure,
                "auto_apply_enabled": False,
                "recommended_action": "manual_review_exact_candidate_before_patch"
                if status == "exact_candidate_available"
                else "continue_manual_official_source_review",
            }
        )

    status_counts = Counter(str(row["status"]) for row in rows)
    by_store = Counter(str(row.get("source_store") or "") for row in rows)
    by_source_kind = Counter(str(row.get("source_kind") or "") for row in rows)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "danganronpa_missing_media_source_detail_probe",
        "summary": {
            "target_rows": len(rows),
            "source_store_filter": source_store,
            "official_search_url_rows": sum(1 for row in rows if row.get("official_search_url")),
            "exact_candidate_rows": status_counts.get("exact_candidate_available", 0),
            "candidate_review_rows": status_counts.get("candidate_review_needed", 0),
            "no_candidate_rows": status_counts.get("no_candidates", 0),
            "no_relevant_candidate_rows": status_counts.get("no_relevant_candidates", 0),
            "fetch_failed_rows": status_counts.get("fetch_failed", 0),
            "not_scanned_rows": status_counts.get("not_scanned", 0),
            "by_status": status_counts.most_common(),
            "by_source_store": by_store.most_common(),
            "by_source_kind": by_source_kind.most_common(),
            "scan_summary": scan_payload.get("summary", {}),
            "auto_apply_enabled": False,
        },
        "items": rows,
        "instructions": [
            "This report converts Danganronpa missing-media rows into official source search probes.",
            "Candidate rows are evidence only; catalog source_url/image_url patches require manual product identity review.",
            "Licensed retailer candidates are kept separate from official manufacturer/prize candidates.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-store")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--time-budget-seconds", type=float)
    args = parser.parse_args()

    report = build_report(
        _load_items(args.queue),
        source_store=args.source_store,
        max_rows=args.max_rows,
        sleep_seconds=args.sleep_seconds,
        time_budget_seconds=args.time_budget_seconds,
    )
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
