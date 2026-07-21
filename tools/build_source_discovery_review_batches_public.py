from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import update_public_catalog_reports as reports


DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "source_discovery_review_batches_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path} must contain a JSON object with an items list")
    return [item for item in payload["items"] if isinstance(item, dict)]


def _compact_item(item: dict[str, Any]) -> dict[str, Any]:
    catalog_index = item.get("row_index")
    import_template = {
        "manual_confirmed": False,
        "manual_note": "",
        "row_index": catalog_index,
        "field": "source_url",
        "manual_value": "",
        "evidence_url": item.get("official_search_url") or item.get("web_search_url") or "",
        "candidate_source_url": "",
        "source_store": item.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "affiliation": item.get("affiliation"),
        "acceptance_criteria": item.get("acceptance_rule"),
        "blocked_until": "exact_product_detail_source_url_confirmed",
    }
    return {
        "catalog_index": catalog_index,
        "source_store": item.get("source_store"),
        "category": item.get("category"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "official_search_url": item.get("official_search_url"),
        "web_search_url": item.get("web_search_url"),
        "allowed_source_domains": item.get("allowed_source_domains") or [],
        "acceptance_rule": item.get("acceptance_rule"),
        "source_patch_template": {
            "catalog_index": catalog_index,
            "source_url": "<exact_product_detail_url>",
            "image_url": "<official_product_image_url_optional_after_source_verification>",
            "source_store": item.get("source_store"),
            "evidence_url": "<official_or_trusted_evidence_url>",
            "manual_confirmed": False,
            "requires_exact_identity_match": True,
        },
        "catalog_field_import_template": import_template,
        "blocked_until": "exact_product_detail_source_url_confirmed",
        "auto_apply_enabled": False,
    }


def _review_state(workflow: str) -> str:
    if workflow == "official_search_url_available":
        return "official_search_review_required"
    if workflow == "licensed_retailer_search_review":
        return "licensed_retailer_review_required"
    return "manual_official_research_required"


def _next_step(workflow: str) -> str:
    if workflow == "official_search_url_available":
        return "open_official_search_and_verify_exact_product_detail"
    if workflow == "licensed_retailer_search_review":
        return "verify_retailer_page_when_official_source_is_unavailable"
    return "record_manual_official_source_evidence"


def build_report(items: list[dict[str, Any]], *, batch_size: int = 25) -> dict[str, Any]:
    source_discovery = reports.build_source_discovery_public(items, sample_rows=len(items))
    queue = [item for item in source_discovery.get("items", []) if isinstance(item, dict)]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in queue:
        grouped[(str(item.get("workflow") or ""), str(item.get("source_store") or "unknown"))].append(item)

    batches: list[dict[str, Any]] = []
    for (workflow, store), rows in sorted(
        grouped.items(),
        key=lambda pair: (
            reports.DISCOVERY_PRIORITY.get(pair[0][0], 99),
            -len(pair[1]),
            pair[0][1],
        ),
    ):
        policy = reports.source_discovery_policy(workflow)
        for offset in range(0, len(rows), batch_size):
            batch_rows = rows[offset : offset + batch_size]
            categories = Counter(str(row.get("category") or "") for row in batch_rows)
            allowed_domains = sorted(
                {
                    domain
                    for row in batch_rows
                    for domain in (row.get("allowed_source_domains") or [])
                    if isinstance(domain, str) and domain
                }
            )
            batch_id = f"source-discovery-{len(batches) + 1:03d}"
            batches.append(
                {
                    "batch_id": batch_id,
                    "priority": reports.DISCOVERY_PRIORITY.get(workflow, 99),
                    "workflow": workflow,
                    "source_store": store,
                    "row_count": len(batch_rows),
                    "offset": offset,
                    "review_state": _review_state(workflow),
                    "next_machine_step": _next_step(workflow),
                    "confidence": policy["confidence"],
                    "evidence_required": policy["evidence_required"],
                    "acceptance_rule": policy["acceptance_rule"],
                    "allowed_source_domains": allowed_domains,
                    "category_counts": categories.most_common(),
                    "source_patch_template_fields": [
                        "catalog_index",
                        "source_url",
                        "image_url",
                        "evidence_url",
                        "manual_confirmed",
                    ],
                    "catalog_field_import_template_fields": [
                        "manual_confirmed",
                        "row_index",
                        "field",
                        "manual_value",
                        "evidence_url",
                        "candidate_source_url",
                    ],
                    "blocked_until": "exact_product_detail_source_url_confirmed",
                    "recommended_action": "Find exact product/detail source URLs before any image_url import.",
                    "items": [_compact_item(row) for row in batch_rows],
                    "auto_apply_enabled": False,
                }
            )

    by_workflow = Counter(str(row.get("workflow") or "") for row in queue)
    by_store = Counter(str(row.get("source_store") or "") for row in queue)
    by_review_state = Counter(str(batch.get("review_state") or "") for batch in batches)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "source_discovery_full_review_batches",
        "summary": {
            "source_discovery_rows": len(queue),
            "batch_count": len(batches),
            "batch_size": batch_size,
            "by_workflow": by_workflow.most_common(),
            "by_source_store": by_store.most_common(40),
            "by_review_state": by_review_state.most_common(),
            "auto_apply_enabled": False,
        },
        "workflow_policies": source_discovery.get("workflow_policies", {}),
        "instructions": [
            "Review batches in priority order, starting with official_search_url_available.",
            "Accepted source_url values must be exact product/detail pages, not search or storefront pages.",
            "After source_url is confirmed, image_url can be extracted only from that exact trusted page.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "reason": "Search results can contain related but non-identical goods, variants, and expired listings.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()

    report = build_report(_load_items(args.input), batch_size=args.batch_size)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
