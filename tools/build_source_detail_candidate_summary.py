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
SERVER = ROOT / "server"
DEFAULT_PATTERN = "catalog_source_detail_candidates*.json"
DEFAULT_JSON = SERVER / "catalog_source_detail_candidate_summary.json"
DEFAULT_MD = SERVER / "catalog_source_detail_candidate_summary.md"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _summary_count(summary: dict[str, Any], key: str, fallback: int = 0) -> int:
    value = summary.get(key)
    return value if isinstance(value, int) else fallback


def _status_of(result: dict[str, Any]) -> str:
    status = result.get("status")
    return str(status) if status else "unknown"


def _store_of(item: dict[str, Any]) -> str:
    value = item.get("source_store") or item.get("store") or item.get("provider")
    return str(value).strip() if value else "unknown"


def _row_key(item: dict[str, Any]) -> tuple[str, str] | None:
    row_index = item.get("row_index")
    if row_index is None:
        seed_id = item.get("seed_id") or item.get("id")
        if seed_id is None:
            return None
        row_index = seed_id
    return (_store_of(item), str(row_index))


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _report_stores(results: list[Any], failures: list[Any]) -> list[str]:
    stores = set()
    for item in [*results, *failures]:
        if isinstance(item, dict):
            stores.add(_store_of(item))
    return sorted(stores)


def _counter_items(counter: Counter[str], limit: int | None = None) -> list[list[Any]]:
    items = [[key, value] for key, value in counter.most_common(limit)]
    return items


def build_summary(paths: list[Path]) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    skipped_files: list[str] = []
    by_store: dict[str, Counter[str]] = defaultdict(Counter)
    status_counts: Counter[str] = Counter()
    skipped_rate_limits: Counter[str] = Counter()
    provider_temporary_unavailable: Counter[str] = Counter()
    unsupported_stores: Counter[str] = Counter()
    unique_processed: set[tuple[str, str]] = set()
    unique_exact: set[tuple[str, str]] = set()
    unique_review: set[tuple[str, str]] = set()

    totals = Counter()

    for path in sorted(paths):
        if path.name in {DEFAULT_JSON.name, DEFAULT_MD.name}:
            continue
        payload = _read_json(path)
        if payload is None:
            skipped_files.append(_relative(path))
            continue

        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        results = [item for item in _as_list(payload.get("results")) if isinstance(item, dict)]
        failures = [item for item in _as_list(payload.get("failures")) if isinstance(item, dict)]
        stores = _report_stores(results, failures)
        inferred_processed = len(results) + len(failures)
        processed_rows = _summary_count(summary, "processed_rows", inferred_processed)
        if not processed_rows:
            processed_rows = inferred_processed

        exact_rows = _summary_count(summary, "exact_candidate_rows", 0)
        review_rows = _summary_count(summary, "candidate_review_rows", 0)
        failure_count = _summary_count(summary, "failure_count", len(failures))
        result_rows = _summary_count(summary, "result_rows", len(results))
        scanned_rows = _summary_count(summary, "scanned_rows", result_rows + failure_count)
        no_relevant_rows = 0

        per_report_status = Counter()
        for result in results:
            status = _status_of(result)
            store = _store_of(result)
            key = _row_key(result)
            per_report_status[status] += 1
            status_counts[status] += 1
            by_store[store]["result_rows"] += 1
            by_store[store][f"status:{status}"] += 1
            if status in {"exact_candidate", "exact_candidate_available"}:
                by_store[store]["exact_candidate_rows"] += 1
                if key:
                    unique_exact.add(key)
            elif status in {"candidate_review", "candidate_review_needed"}:
                by_store[store]["candidate_review_rows"] += 1
                if key:
                    unique_review.add(key)
            elif status in {
                "no_relevant_candidate",
                "no_relevant_candidates",
                "no_candidate",
                "no_candidates",
                "no_candidates_found",
            }:
                no_relevant_rows += 1
                by_store[store]["no_candidate_rows"] += 1
            if key:
                unique_processed.add(key)

        for failure in failures:
            store = _store_of(failure)
            key = _row_key(failure)
            by_store[store]["failure_count"] += 1
            if failure.get("provider_temporary_unavailable"):
                by_store[store]["provider_temporary_unavailable_failures"] += 1
                provider_temporary_unavailable[store] += 1
            if key:
                unique_processed.add(key)

        for store in _as_list(summary.get("rate_limit_skipped_stores")):
            skipped_rate_limits[str(store)] += 1

        unsupported_items = (
            summary.get("unsupported_provider_top_stores")
            or summary.get("top_unsupported_provider_stores")
        )
        for item in _as_list(unsupported_items):
            if isinstance(item, list) and len(item) >= 2:
                unsupported_stores[str(item[0])] += int(item[1])
            elif isinstance(item, dict):
                store = item.get("store") or item.get("source_store")
                count = item.get("count") or item.get("rows") or 0
                if store:
                    unsupported_stores[str(store)] += int(count)

        time_budget_exhausted = bool(summary.get("time_budget_exhausted"))

        for store in stores or ["unknown"]:
            by_store[store]["report_count"] += 1
            by_store[store]["processed_rows"] += processed_rows if len(stores) <= 1 else 0
            by_store[store]["scanned_rows"] += scanned_rows if len(stores) <= 1 else 0
            if time_budget_exhausted:
                by_store[store]["time_budget_exhausted_reports"] += 1

        totals["processed_rows_reported"] += processed_rows
        totals["scanned_rows_reported"] += scanned_rows
        totals["result_rows"] += result_rows
        totals["failure_count"] += failure_count
        totals["exact_candidate_rows_reported"] += exact_rows
        totals["candidate_review_rows_reported"] += review_rows
        totals["time_budget_exhausted_reports"] += 1 if time_budget_exhausted else 0

        reports.append(
            {
                "path": _relative(path),
                "stores": stores,
                "processed_rows": processed_rows,
                "scanned_rows": scanned_rows,
                "result_rows": result_rows,
                "failure_count": failure_count,
                "exact_candidate_rows": exact_rows,
                "candidate_review_rows": review_rows,
                "no_candidate_rows": no_relevant_rows,
                "status_counts": dict(sorted(per_report_status.items())),
                "time_budget_exhausted": time_budget_exhausted,
                "rate_limit_skipped_stores": _as_list(summary.get("rate_limit_skipped_stores")),
            }
        )

    by_store_rows = []
    for store, counts in by_store.items():
        by_store_rows.append(
            {
                "store": store,
                "report_count": counts.get("report_count", 0),
                "processed_rows_reported_single_store_only": counts.get("processed_rows", 0),
                "scanned_rows_reported_single_store_only": counts.get("scanned_rows", 0),
                "result_rows": counts.get("result_rows", 0),
                "failure_count": counts.get("failure_count", 0),
                "provider_temporary_unavailable_failures": counts.get(
                    "provider_temporary_unavailable_failures", 0
                ),
                "exact_candidate_rows": counts.get("exact_candidate_rows", 0),
                "candidate_review_rows": counts.get("candidate_review_rows", 0),
                "no_candidate_rows": counts.get("no_candidate_rows", 0),
                "time_budget_exhausted_reports": counts.get("time_budget_exhausted_reports", 0),
            }
        )
    by_store_rows.sort(
        key=lambda row: (
            row["exact_candidate_rows"] + row["candidate_review_rows"],
            row["result_rows"] + row["failure_count"],
        ),
        reverse=True,
    )

    actionable_reports = [
        report
        for report in reports
        if report["exact_candidate_rows"] or report["candidate_review_rows"]
    ]
    zero_match_reports = [
        report
        for report in reports
        if not report["exact_candidate_rows"] and not report["candidate_review_rows"]
    ]

    return {
        "summary": {
            "report_count": len(reports),
            "skipped_file_count": len(skipped_files),
            "processed_rows_reported": totals["processed_rows_reported"],
            "scanned_rows_reported": totals["scanned_rows_reported"],
            "unique_processed_store_row_pairs": len(unique_processed),
            "unique_exact_candidate_store_row_pairs": len(unique_exact),
            "unique_review_candidate_store_row_pairs": len(unique_review),
            "result_rows": totals["result_rows"],
            "failure_count": totals["failure_count"],
            "exact_candidate_rows_reported": totals["exact_candidate_rows_reported"],
            "candidate_review_rows_reported": totals["candidate_review_rows_reported"],
            "time_budget_exhausted_reports": totals["time_budget_exhausted_reports"],
            "actionable_report_count": len(actionable_reports),
            "zero_match_report_count": len(zero_match_reports),
            "status_counts": _counter_items(status_counts),
            "rate_limit_skipped_stores": _counter_items(skipped_rate_limits),
            "provider_temporary_unavailable_stores": _counter_items(provider_temporary_unavailable),
            "unsupported_provider_top_stores": _counter_items(unsupported_stores, 20),
            "note": "Reported totals may include overlapping batch attempts; unique counts are keyed by source_store and row_index/id.",
        },
        "by_store": by_store_rows,
        "actionable_reports": actionable_reports,
        "zero_match_reports": zero_match_reports,
        "reports": reports,
        "skipped_files": skipped_files,
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload.get("summary", {})
    lines = [
        "# Source Detail Candidate Summary",
        "",
        "Source detail scans are operational attempts. Reported totals can overlap across full scans and smaller batches, so unique counts are keyed by `source_store` and `row_index`/`id`.",
        "",
        "## Totals",
        "",
        f"- Reports scanned: {summary.get('report_count', 0)}",
        f"- Reported processed rows: {summary.get('processed_rows_reported', 0)}",
        f"- Unique processed store/row pairs: {summary.get('unique_processed_store_row_pairs', 0)}",
        f"- Exact candidates: {summary.get('unique_exact_candidate_store_row_pairs', 0)} unique / {summary.get('exact_candidate_rows_reported', 0)} reported",
        f"- Review candidates: {summary.get('unique_review_candidate_store_row_pairs', 0)} unique / {summary.get('candidate_review_rows_reported', 0)} reported",
        f"- Failures: {summary.get('failure_count', 0)}",
        f"- Actionable reports: {summary.get('actionable_report_count', 0)}",
        "",
        "## By Store",
        "",
        "| Store | Reports | Results | Failures | Exact | Review | No candidate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload.get("by_store", [])[:20]:
        lines.append(
            "| {store} | {report_count} | {result_rows} | {failure_count} | {exact_candidate_rows} | {candidate_review_rows} | {no_candidate_rows} |".format(
                **row
            )
        )

    lines.extend(["", "## Actionable Reports", ""])
    actionable = payload.get("actionable_reports", [])
    if actionable:
        for report in actionable:
            lines.append(
                f"- `{report['path']}`: exact {report['exact_candidate_rows']}, review {report['candidate_review_rows']}, stores {', '.join(report.get('stores') or ['unknown'])}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Rate Limits", ""])
    rate_limits = summary.get("rate_limit_skipped_stores") or []
    if rate_limits:
        for store, count in rate_limits:
            lines.append(f"- {store}: {count} report(s)")
    else:
        lines.append("- None")

    lines.extend(["", "## Unsupported Provider Stores", ""])
    unsupported = summary.get("unsupported_provider_top_stores") or []
    if unsupported:
        for store, count in unsupported[:10]:
            lines.append(f"- {store}: {count}")
    else:
        lines.append("- None")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-dir", type=Path, default=SERVER)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)

    paths = sorted(args.server_dir.glob(args.pattern))
    payload = build_summary(paths)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.output_md)
    print(
        json.dumps(
            {
                "reports": payload["summary"]["report_count"],
                "unique_processed": payload["summary"]["unique_processed_store_row_pairs"],
                "unique_exact": payload["summary"]["unique_exact_candidate_store_row_pairs"],
                "unique_review": payload["summary"]["unique_review_candidate_store_row_pairs"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
