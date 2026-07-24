from __future__ import annotations

import argparse
import json
import sys
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
DEFAULT_INPUT = DATA / "catalog_deduplication_action_queue_public.json"
DEFAULT_OUTPUT = DATA / "ichiban_kuji_reissue_decision_template_public.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _copy_template(row: dict[str, Any]) -> dict[str, Any]:
    template = dict(row.get("decision_template") or {})
    template["manual_confirmed"] = False
    template["decision"] = ""
    template.setdefault("evidence_urls", row.get("source_urls") or [])
    template.setdefault("manual_note", "")
    return template


def _item_template(row: dict[str, Any]) -> dict[str, Any]:
    template = _copy_template(row)
    return {
        "work_order_id": row.get("work_order_id"),
        "campaign_work_order_id": row.get("campaign_work_order_id"),
        "priority": row.get("priority"),
        "normalized_name": row.get("normalized_name"),
        "catalog_indexes": row.get("catalog_indexes") or [],
        "source_urls": row.get("source_urls") or [],
        "campaign_slug_families": row.get("campaign_slug_families") or [],
        "campaign_url_comparison": row.get("campaign_url_comparison") or {},
        "reissue_signal_reasons": row.get("reissue_signal_reasons") or [],
        "manual_review_checklist": row.get("manual_review_checklist") or [],
        "sample_rows": row.get("sample_rows") or [],
        "decision_template": template,
        "manual_confirmed": False,
        "decision": template.get("decision") or "",
        "keep_catalog_index": template.get("keep_catalog_index"),
        "drop_catalog_indexes": template.get("drop_catalog_indexes") or [],
        "evidence_urls": template.get("evidence_urls") or [],
        "manual_note": template.get("manual_note") or "",
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def _campaign_template(row: dict[str, Any]) -> dict[str, Any]:
    template = _copy_template(row)
    return {
        "campaign_work_order_id": row.get("campaign_work_order_id"),
        "priority": row.get("priority"),
        "source_urls": row.get("source_urls") or [],
        "item_work_order_count": row.get("item_work_order_count") or 0,
        "affected_item_work_order_ids": template.get("affected_item_work_order_ids") or [],
        "catalog_indexes": row.get("catalog_indexes") or [],
        "prize_labels": row.get("prize_labels") or [],
        "campaign_url_comparison": row.get("campaign_url_comparison") or {},
        "manual_review_checklist": row.get("manual_review_checklist") or [],
        "sample_rows": row.get("sample_rows") or [],
        "decision_template": template,
        "manual_confirmed": False,
        "decision": template.get("decision") or "",
        "evidence_urls": template.get("evidence_urls") or [],
        "manual_note": template.get("manual_note") or "",
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }


def build_report(action_queue: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    item_templates = [_item_template(row) for row in _safe_list(action_queue.get("ichiban_reissue_work_order"))]
    campaign_templates = [
        _campaign_template(row) for row in _safe_list(action_queue.get("ichiban_reissue_campaign_work_order"))
    ]

    item_decisions = Counter(item["decision"] or "unconfirmed" for item in item_templates)
    campaign_decisions = Counter(item["decision"] or "unconfirmed" for item in campaign_templates)
    summary = {
        "item_template_rows": len(item_templates),
        "campaign_template_rows": len(campaign_templates),
        "manual_confirmed_item_rows": sum(1 for item in item_templates if item.get("manual_confirmed") is True),
        "manual_confirmed_campaign_rows": sum(
            1 for item in campaign_templates if item.get("manual_confirmed") is True
        ),
        "same_sellable_product_keep_drop_ready_rows": sum(
            1
            for item in item_templates
            if item.get("manual_confirmed") is True
            and item.get("decision") == "same_sellable_product_keep_drop_confirmed"
        ),
        "keep_separate_confirmed_rows": sum(
            1
            for item in item_templates
            if item.get("manual_confirmed") is True
            and item.get("decision") == "reissue_or_campaign_variant_keep_separate"
        ),
        "item_decision_counts": [[key, count] for key, count in sorted(item_decisions.items())],
        "campaign_decision_counts": [[key, count] for key, count in sorted(campaign_decisions.items())],
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
        "manual_review_required_before_mutation": True,
        "recommended_next_action": "fill_campaign_decisions_first_then_confirm_item_keep_drop_or_keep_separate",
    }

    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "ichiban_kuji_reissue_decision_template",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": summary,
        "instructions": [
            "Review campaign_templates first when one campaign URL pair covers many item work orders.",
            "Set manual_confirmed=true only after checking official campaign pages and evidence_urls.",
            "Use reissue_or_campaign_variant_keep_separate when rows are legitimate reissues or campaign waves.",
            "Use same_sellable_product_keep_drop_confirmed only for exact duplicates, with one keep_catalog_index and explicit drop_catalog_indexes.",
            "Do not import any merge/delete mutation from this file unless manual_confirmed=true and evidence_urls prove the decision.",
        ],
        "automation_policy": {
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
            "manual_review_required_before_mutation": True,
        },
        "campaign_templates": campaign_templates,
        "item_templates": item_templates,
    }


def write_report(report: dict[str, Any], path: Path = DEFAULT_OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(_load_json(args.input))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
