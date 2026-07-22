from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_ENRICHMENT = DATA / "catalog_image_enrichment_batches_public.json"
DEFAULT_ACTION_QUEUE = DATA / "catalog_image_attachment_action_queue_public.json"
DEFAULT_OUTPUT = DATA / "catalog_missing_image_actionability_public.json"


WORKFLOW_LABELS = {
    "extract_from_existing_source_url": "이미 확인된 상세 source_url에서 image_url 추출",
    "replace_generic_source_then_extract_image": "일반 상점/목록 URL을 상품 상세 URL로 교체 후 이미지 첨부",
    "review_gotouchi_official_candidates": "고토치 공식 후보가 상품 종류까지 맞는지 검토 후 이미지 첨부",
    "find_source_then_extract_image": "정확한 공식 상품 source_url을 먼저 찾은 뒤 이미지 첨부",
    "manual_image_research": "공식/제조사 경로를 수동 조사",
}

WORKFLOW_NEXT_STEPS = {
    "extract_from_existing_source_url": "extract_product_image_from_existing_exact_source_url",
    "replace_generic_source_then_extract_image": "replace_generic_source_url_then_extract_image",
    "review_gotouchi_official_candidates": "confirm_exact_product_type_then_attach_image",
    "find_source_then_extract_image": "find_exact_official_source_url_then_extract_image",
    "manual_image_research": "manual_official_source_and_image_research",
}

READINESS_ORDER = {
    "image_url_candidate_review": 10,
    "source_url_replacement_required": 20,
    "source_url_discovery_required": 30,
    "manual_research_required": 40,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def counter_rows(counter: Counter[str], field: str, limit: int = 30) -> list[dict[str, Any]]:
    return [{field: key, "rows": value} for key, value in counter.most_common(limit) if key]


def workflow_readiness(workflow: str) -> str:
    if workflow == "extract_from_existing_source_url":
        return "image_url_candidate_review"
    if workflow in {"replace_generic_source_then_extract_image", "review_gotouchi_official_candidates"}:
        return "source_url_replacement_required"
    if workflow == "find_source_then_extract_image":
        return "source_url_discovery_required"
    return "manual_research_required"


def compact_sample(group: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("catalog_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "source_store": item.get("source_store") or group.get("source_store"),
        "affiliation": item.get("affiliation"),
        "category": item.get("category"),
        "source_url": item.get("source_url"),
        "official_search_url": item.get("official_search_url"),
    }


def summarize_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_readiness: dict[str, dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        workflow = str(group.get("workflow") or "manual_image_research")
        readiness = workflow_readiness(workflow)
        rows = int(group.get("missing_image_rows") or 0)
        bucket = by_readiness.setdefault(
            readiness,
            {
                "readiness": readiness,
                "rows": 0,
                "workflow_rows": Counter(),
                "source_store_rows": Counter(),
                "sample_items": [],
            },
        )
        bucket["rows"] += rows
        bucket["workflow_rows"][workflow] += rows
        source_store = str(group.get("source_store") or "")
        if source_store:
            bucket["source_store_rows"][source_store] += rows
        for item in group.get("sample_items") or []:
            if isinstance(item, dict) and len(bucket["sample_items"]) < 12:
                sample = compact_sample(group, item)
                sample["workflow"] = workflow
                bucket["sample_items"].append(sample)

    rows_out: list[dict[str, Any]] = []
    for readiness, bucket in by_readiness.items():
        workflow_rows = [
            {
                "workflow": workflow,
                "label": WORKFLOW_LABELS.get(workflow, workflow),
                "rows": count,
                "next_step": WORKFLOW_NEXT_STEPS.get(workflow, "manual_review"),
            }
            for workflow, count in bucket["workflow_rows"].most_common()
        ]
        rows_out.append(
            {
                "readiness": readiness,
                "priority": READINESS_ORDER.get(readiness, 99),
                "rows": bucket["rows"],
                "workflow_rows": workflow_rows,
                "by_source_store": counter_rows(bucket["source_store_rows"], "source_store"),
                "sample_items": bucket["sample_items"],
                "auto_apply_enabled": False,
            }
        )
    return sorted(rows_out, key=lambda row: (int(row["priority"]), str(row["readiness"])))


def build_report(
    enrichment: dict[str, Any],
    action_queue: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    summary = enrichment.get("summary") if isinstance(enrichment.get("summary"), dict) else {}
    action_summary = action_queue.get("summary") if isinstance(action_queue.get("summary"), dict) else {}
    groups = [group for group in enrichment.get("groups", []) if isinstance(group, dict)]
    readiness_rows = summarize_groups(groups)
    readiness_total = sum(int(row.get("rows") or 0) for row in readiness_rows)
    missing_image_rows = int(summary.get("missing_image_rows") or readiness_total)

    immediate_rows = sum(
        count
        for workflow, count in summary.get("by_workflow", [])
        if workflow == "extract_from_existing_source_url"
    )
    source_first_rows = sum(
        count
        for workflow, count in summary.get("by_workflow", [])
        if workflow in {"find_source_then_extract_image", "replace_generic_source_then_extract_image"}
    )
    review_before_attach_rows = sum(
        count
        for workflow, count in summary.get("by_workflow", [])
        if workflow == "review_gotouchi_official_candidates"
    )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "catalog_missing_image_actionability",
        "summary": {
            "missing_image_rows": missing_image_rows,
            "readiness_classified_rows": readiness_total,
            "unclassified_rows": max(missing_image_rows - readiness_total, 0),
            "exact_source_ready_rows": immediate_rows,
            "source_first_rows": source_first_rows,
            "review_before_attach_rows": review_before_attach_rows,
            "manual_image_research_rows": int(summary.get("manual_image_research_rows") or 0),
            "action_queue_rows": int(action_summary.get("queued_image_rows") or 0),
            "actionable_image_rows": int(action_summary.get("actionable_image_rows") or 0),
            "auto_apply_enabled": False,
        },
        "readiness": readiness_rows,
        "recommended_order": [
            "source_url_replacement_required",
            "source_url_discovery_required",
            "manual_research_required",
            "image_url_candidate_review",
        ],
        "notes": [
            "exact_source_ready_rows means image_url can be reviewed from an already exact product source_url.",
            "source_first_rows must receive or replace source_url before any image_url import.",
            "action_queue_rows is a review sample queue, not permission for automatic catalog mutation.",
            "All image changes remain manual-review only until exact product identity is confirmed.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_exact_product_identity": True,
            "requires_exact_source_url_before_image_url": True,
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enrichment", type=Path, default=DEFAULT_ENRICHMENT)
    parser.add_argument("--action-queue", type=Path, default=DEFAULT_ACTION_QUEUE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.enrichment), load_json(args.action_queue))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
