from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_source_detail_candidate_summary import build_summary


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
DATA = ROOT / "data"
DEFAULT_PATTERN = "catalog_source_detail_candidates*.json"
DEFAULT_OUTPUT = DATA / "source_detail_probe_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def compact_candidate(result: dict[str, Any], source_report: Path) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in result.get("top_candidates") or []
        if isinstance(candidate, dict)
    ]
    top = candidates[0] if candidates else {}
    return {
        "catalog_index": result.get("row_index"),
        "source_store": result.get("source_store"),
        "name_ko": result.get("name_ko"),
        "name_ja": result.get("name_ja"),
        "query": result.get("query"),
        "status": result.get("status"),
        "candidate_count": result.get("candidate_count"),
        "candidate_source_url": top.get("candidate_source_url"),
        "candidate_title": top.get("candidate_title"),
        "candidate_image_url": top.get("candidate_image_url"),
        "score": top.get("score"),
        "shared_tokens": top.get("shared_tokens") or [],
        "safe_source_image_pair": top.get("safe_source_image_pair"),
        "source_report": rel(source_report),
        "recommended_action": "manual_review_candidate_before_source_or_image_patch",
        "auto_apply_enabled": False,
    }


def candidate_rows(paths: list[Path], *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for path in sorted(paths):
        try:
            payload = load_json(path)
        except Exception:
            continue
        for result in payload.get("results") or []:
            if not isinstance(result, dict):
                continue
            if result.get("status") not in {"exact_candidate_available", "candidate_review_needed"}:
                continue
            top = (result.get("top_candidates") or [{}])[0]
            if not isinstance(top, dict):
                top = {}
            key = (
                str(result.get("source_store") or ""),
                str(result.get("row_index") or ""),
                str(top.get("candidate_source_url") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(compact_candidate(result, path))

    rows.sort(
        key=lambda row: (
            0 if row.get("status") == "exact_candidate_available" else 1,
            str(row.get("source_store") or ""),
            int(row.get("catalog_index") or 999_999_999),
        )
    )
    return rows[:limit]


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _scan_bottleneck(row: dict[str, Any]) -> str:
    failures = _safe_int(row.get("failure_count"))
    result_rows = _safe_int(row.get("result_rows"))
    candidate_rows = _safe_int(row.get("candidate_review_rows")) + _safe_int(row.get("exact_candidate_rows"))
    if failures and not candidate_rows:
        return "fetch_or_rate_limit_failures"
    if result_rows and not candidate_rows:
        return "searched_but_no_candidates"
    if candidate_rows:
        return "candidate_review_available"
    return "not_scanned_or_empty"


def _candidate_yield(row: dict[str, Any]) -> float:
    result_rows = _safe_int(row.get("result_rows"))
    if not result_rows:
        return 0.0
    candidate_rows = _safe_int(row.get("candidate_review_rows")) + _safe_int(row.get("exact_candidate_rows"))
    return round(candidate_rows / result_rows, 4)


def _bottleneck_rows(scans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in scans:
        enriched = dict(row)
        enriched["candidate_rows"] = _safe_int(row.get("candidate_review_rows")) + _safe_int(
            row.get("exact_candidate_rows")
        )
        enriched["candidate_yield"] = _candidate_yield(row)
        enriched["bottleneck"] = _scan_bottleneck(row)
        if enriched["bottleneck"] == "candidate_review_available":
            enriched["next_step"] = "review_candidate_identity_then_fill_source_image_templates"
        elif enriched["bottleneck"] == "fetch_or_rate_limit_failures":
            enriched["next_step"] = "rerun_scan_with_store_specific_backoff_or_cache"
        elif enriched["bottleneck"] == "searched_but_no_candidates":
            enriched["next_step"] = "improve_store_search_query_or_parser"
        else:
            enriched["next_step"] = "schedule_store_scan"
        rows.append(enriched)
    return sorted(
        rows,
        key=lambda item: (
            {
                "fetch_or_rate_limit_failures": 10,
                "searched_but_no_candidates": 20,
                "not_scanned_or_empty": 30,
                "candidate_review_available": 40,
            }.get(str(item.get("bottleneck") or ""), 99),
            -_safe_int(item.get("failure_count")),
            -_safe_int(item.get("no_candidate_rows")),
            str(item.get("source_store") or ""),
        ),
    )


def build_report(paths: list[Path], *, generated_at: str | None = None, candidate_limit: int = 80) -> dict[str, Any]:
    summary_payload = build_summary(paths)
    summary = summary_payload.get("summary", {})
    candidates = candidate_rows(paths, limit=candidate_limit)
    scans = [
        {
            "source_store": row.get("store"),
            "report_count": row.get("report_count"),
            "processed_rows": row.get("processed_rows_reported_single_store_only"),
            "result_rows": row.get("result_rows"),
            "failure_count": row.get("failure_count"),
            "provider_temporary_unavailable_failures": row.get("provider_temporary_unavailable_failures"),
            "exact_candidate_rows": row.get("exact_candidate_rows"),
            "candidate_review_rows": row.get("candidate_review_rows"),
            "no_candidate_rows": row.get("no_candidate_rows"),
        }
        for row in summary_payload.get("by_store", [])
        if isinstance(row, dict)
    ]
    candidate_store_counts = Counter(str(row.get("source_store") or "") for row in candidates)
    bottlenecks = _bottleneck_rows(scans)
    bottleneck_counts = Counter(str(row.get("bottleneck") or "") for row in bottlenecks)

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_detail_probe_public",
        "summary": {
            "source_queue_rows": summary.get("unique_processed_store_row_pairs", 0),
            "report_count": summary.get("report_count", 0),
            "stores_scanned": len(scans),
            "scanned_rows": summary.get("scanned_rows_reported", 0),
            "processed_rows": summary.get("processed_rows_reported", 0),
            "unique_processed_store_row_pairs": summary.get("unique_processed_store_row_pairs", 0),
            "exact_candidate_rows": summary.get("unique_exact_candidate_store_row_pairs", 0),
            "candidate_review_rows": summary.get("candidate_review_rows_reported", 0),
            "unique_review_candidate_rows": summary.get("unique_review_candidate_store_row_pairs", 0),
            "failure_count": summary.get("failure_count", 0),
            "provider_temporary_unavailable_stores": summary.get(
                "provider_temporary_unavailable_stores", []
            ),
            "time_budget_exhausted_reports": summary.get("time_budget_exhausted_reports", 0),
            "rate_limit_skipped_stores": summary.get("rate_limit_skipped_stores", []),
            "published_candidate_rows": len(candidates),
            "candidate_yield": round(
                (summary.get("unique_review_candidate_store_row_pairs", 0) or 0)
                / (summary.get("unique_processed_store_row_pairs", 0) or 1),
                4,
            ),
            "store_bottleneck_counts": [[key, value] for key, value in bottleneck_counts.most_common()],
            "auto_apply_enabled": False,
        },
        "scans": scans,
        "store_bottlenecks": bottlenecks,
        "candidate_rows_by_store": [
            {"source_store": store, "rows": count}
            for store, count in candidate_store_counts.most_common()
        ],
        "review_candidates": candidates,
        "instructions": [
            "This public report summarizes already-run source detail scans; it does not fetch external pages.",
            "candidate_review_needed rows require manual identity review before source_url or image_url patches.",
            "exact_candidate_rows remain manual-review only; no catalog mutation is auto-applied.",
        ],
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=SERVER)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    paths = sorted(args.input_dir.glob(args.pattern)) if args.input_dir.exists() else []
    report = build_report(paths, candidate_limit=args.candidate_limit)
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
