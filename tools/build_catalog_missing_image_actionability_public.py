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
DEFAULT_SOURCE_DETAIL_QUEUE = DATA / "source_detail_candidate_action_queue_public.json"
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


def summarize_source_stores(groups: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    by_store: dict[str, dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        source_store = str(group.get("source_store") or "").strip()
        if not source_store:
            continue
        workflow = str(group.get("workflow") or "manual_image_research")
        readiness = workflow_readiness(workflow)
        rows = int(group.get("missing_image_rows") or 0)
        bucket = by_store.setdefault(
            source_store,
            {
                "source_store": source_store,
                "missing_image_rows": 0,
                "priority": READINESS_ORDER.get(readiness, 99),
                "readiness_rows": Counter(),
                "workflow_rows": Counter(),
                "sample_items": [],
            },
        )
        bucket["missing_image_rows"] += rows
        bucket["priority"] = min(int(bucket["priority"]), READINESS_ORDER.get(readiness, 99))
        bucket["readiness_rows"][readiness] += rows
        bucket["workflow_rows"][workflow] += rows
        for item in group.get("sample_items") or []:
            if isinstance(item, dict) and len(bucket["sample_items"]) < 8:
                sample = compact_sample(group, item)
                sample["workflow"] = workflow
                sample["readiness"] = readiness
                bucket["sample_items"].append(sample)

    rows_out: list[dict[str, Any]] = []
    for bucket in by_store.values():
        primary_workflow = ""
        if bucket["workflow_rows"]:
            primary_workflow = bucket["workflow_rows"].most_common(1)[0][0]
        rows_out.append(
            {
                "source_store": bucket["source_store"],
                "priority": bucket["priority"],
                "missing_image_rows": bucket["missing_image_rows"],
                "primary_workflow": primary_workflow,
                "recommended_next_step": WORKFLOW_NEXT_STEPS.get(primary_workflow, "manual_review"),
                "readiness_rows": [
                    {"readiness": readiness, "rows": count}
                    for readiness, count in bucket["readiness_rows"].most_common()
                ],
                "workflow_rows": [
                    {
                        "workflow": workflow,
                        "label": WORKFLOW_LABELS.get(workflow, workflow),
                        "rows": count,
                        "next_step": WORKFLOW_NEXT_STEPS.get(workflow, "manual_review"),
                    }
                    for workflow, count in bucket["workflow_rows"].most_common()
                ],
                "sample_items": bucket["sample_items"],
                "auto_apply_enabled": False,
            }
        )
    return sorted(rows_out, key=lambda row: (int(row["priority"]), -int(row["missing_image_rows"]), str(row["source_store"])))[:limit]


def source_detail_items(source_detail_queue: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(source_detail_queue, dict):
        return []
    items: list[dict[str, Any]] = []
    for batch in source_detail_queue.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        for item in batch.get("items") or []:
            if isinstance(item, dict):
                items.append(item)
    return items


def source_detail_missing_items(source_detail_queue: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        item
        for item in source_detail_items(source_detail_queue)
        if item.get("current_catalog_state", {}).get("catalog_has_display_image") is False
    ]


def append_source_detail_readiness(
    readiness_rows: list[dict[str, Any]],
    source_detail_missing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ready_items = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") == "confirm_exact_identity_before_source_or_image_patch"
    ]
    recheck_items = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") == "recheck_candidate_identity_before_source_or_image_patch"
    ]
    if not ready_items and not recheck_items:
        return readiness_rows
    ready_samples = [
        {
            "catalog_index": item.get("catalog_index"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "source_store": item.get("source_store"),
            "candidate_source_url": item.get("candidate_source_url"),
            "candidate_image_url": item.get("candidate_image_url"),
            "review_risk": item.get("review_risk"),
            "candidate_identity_flags": item.get("candidate_identity_flags") or [],
            "workflow": "confirm_source_detail_candidate_then_attach_image",
        }
        for item in ready_items[:12]
    ]
    out = list(readiness_rows)
    if ready_items:
        out.append(
            {
                "readiness": "source_detail_candidate_review",
                "priority": READINESS_ORDER["image_url_candidate_review"] + 1,
                "rows": len(ready_items),
                "workflow_rows": [
                    {
                        "workflow": "confirm_source_detail_candidate_then_attach_image",
                        "label": "정확한 상품 상세 후보를 확인한 뒤 source_url/image_url 첨부",
                        "rows": len(ready_items),
                        "next_step": "manual_confirm_then_import_source_and_image_templates",
                    }
                ],
                "by_source_store": counter_rows(Counter(str(item.get("source_store") or "") for item in ready_items), "source_store"),
                "sample_items": ready_samples,
                "auto_apply_enabled": False,
            }
        )
    if recheck_items:
        out.append(
            {
                "readiness": "source_detail_candidate_recheck_required",
                "priority": READINESS_ORDER["source_url_discovery_required"] - 1,
                "rows": len(recheck_items),
                "workflow_rows": [
                    {
                        "workflow": "recheck_source_detail_candidate_identity",
                        "label": "후보 제목의 작품/캐릭터/변형 불일치 가능성 재확인",
                        "rows": len(recheck_items),
                        "next_step": "refresh_or_replace_candidate_before_import",
                    }
                ],
                "by_source_store": counter_rows(Counter(str(item.get("source_store") or "") for item in recheck_items), "source_store"),
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "source_store": item.get("source_store"),
                        "candidate_title": item.get("candidate_title"),
                        "candidate_source_url": item.get("candidate_source_url"),
                        "candidate_identity_flags": item.get("candidate_identity_flags") or [],
                        "workflow": "recheck_source_detail_candidate_identity",
                    }
                    for item in recheck_items[:12]
                ],
                "auto_apply_enabled": False,
            }
        )
    return sorted(out, key=lambda row: (int(row["priority"]), str(row["readiness"])))


def build_report(
    enrichment: dict[str, Any],
    action_queue: dict[str, Any],
    source_detail_queue: dict[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    summary = enrichment.get("summary") if isinstance(enrichment.get("summary"), dict) else {}
    action_summary = action_queue.get("summary") if isinstance(action_queue.get("summary"), dict) else {}
    groups = [group for group in enrichment.get("groups", []) if isinstance(group, dict)]
    source_detail_missing = source_detail_missing_items(source_detail_queue)
    source_detail_ready = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") == "confirm_exact_identity_before_source_or_image_patch"
    ]
    source_detail_recheck = [
        item
        for item in source_detail_missing
        if item.get("recommended_action") == "recheck_candidate_identity_before_source_or_image_patch"
    ]
    base_readiness_rows = summarize_groups(groups)
    readiness_rows = append_source_detail_readiness(base_readiness_rows, source_detail_missing)
    source_store_priority = summarize_source_stores(groups)
    readiness_total = sum(int(row.get("rows") or 0) for row in base_readiness_rows)
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
            "source_detail_candidate_review_rows": len(source_detail_ready),
            "source_detail_candidate_recheck_required_rows": len(source_detail_recheck),
            "source_detail_identity_warning_rows": sum(
                1 for item in source_detail_missing if item.get("candidate_identity_flags")
            ),
            "source_detail_unflagged_candidate_rows": len(source_detail_ready),
            "manual_image_research_rows": int(summary.get("manual_image_research_rows") or 0),
            "action_queue_rows": int(action_summary.get("queued_image_rows") or 0) + len(source_detail_ready),
            "direct_image_action_queue_rows": int(action_summary.get("queued_image_rows") or 0),
            "actionable_image_rows": int(action_summary.get("actionable_image_rows") or 0) + len(source_detail_ready),
            "auto_apply_enabled": False,
        },
        "readiness": readiness_rows,
        "source_store_priority": source_store_priority,
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
            "source_detail_candidate_review_rows are separate source_url/image_url candidate pairs and still require exact identity confirmation.",
            "source_detail_identity_warning_rows counts candidates with generic-only shared tokens, crossover titles, or missing variant hints.",
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
    parser.add_argument("--source-detail-queue", type=Path, default=DEFAULT_SOURCE_DETAIL_QUEUE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.enrichment), load_json(args.action_queue), load_json(args.source_detail_queue))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
