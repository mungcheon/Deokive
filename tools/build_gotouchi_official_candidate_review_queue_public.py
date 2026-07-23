from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_ACTION_QUEUE = DATA / "catalog_image_attachment_action_queue_public.json"
DEFAULT_CANDIDATES = DATA / "gotouchi_chiikawa_image_candidates_public.json"
DEFAULT_OUTPUT = DATA / "gotouchi_official_candidate_review_queue_public.json"
GOTOUCHI_WORKFLOW = "review_gotouchi_official_candidates"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _counter_pairs(rows: list[dict[str, Any]], key: str) -> list[list[Any]]:
    counts = Counter(_compact_text(row.get(key)) for row in rows)
    counts.pop("", None)
    return [[name, count] for name, count in counts.most_common()]


def _action_items(action_queue: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for batch in action_queue.get("batches") or []:
        if not isinstance(batch, dict) or batch.get("workflow") != GOTOUCHI_WORKFLOW:
            continue
        for item in batch.get("items") or []:
            if isinstance(item, dict):
                out.append({**item, "batch_id": batch.get("batch_id")})
    return out


def _candidate_lookup(candidate_report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for item in candidate_report.get("items") or []:
        if not isinstance(item, dict):
            continue
        catalog_index = item.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            out[catalog_index] = item
    return out


def _candidate_options(candidate_row: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(candidate_row, dict):
        return []
    candidates = candidate_row.get("top_candidates")
    if not isinstance(candidates, list):
        return []
    out: list[dict[str, Any]] = []
    for candidate in candidates[:8]:
        if not isinstance(candidate, dict):
            continue
        out.append(
            {
                "page": candidate.get("page"),
                "image_url": candidate.get("image_url"),
                "alt": candidate.get("alt"),
                "type": candidate.get("type"),
                "row_type": candidate.get("row_type"),
                "type_match": candidate.get("type_match"),
                "matched_motifs": candidate.get("matched_motifs") or [],
                "score": candidate.get("score"),
            }
        )
    return out


def _manual_image_template(action_item: dict[str, Any], candidate_row: dict[str, Any] | None) -> dict[str, Any]:
    candidate = _candidate_options(candidate_row)
    top = candidate[0] if candidate else {}
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "row_index": action_item.get("catalog_index"),
        "catalog_index": action_item.get("catalog_index"),
        "field": "image_url",
        "manual_value": "",
        "evidence_url": top.get("page") or action_item.get("source_url") or "",
        "candidate_source_url": top.get("page") or action_item.get("source_url") or "",
        "candidate_image_url": top.get("image_url") or "",
        "representative_image": True,
        "blocked_until": "manual_confirmed_true_after_visual_identity_review",
    }


def _review_item(action_item: dict[str, Any], candidate_row: dict[str, Any] | None) -> dict[str, Any]:
    candidate_status = (
        candidate_row.get("candidate_status") if isinstance(candidate_row, dict) else "missing_candidate_report"
    )
    candidates = _candidate_options(candidate_row)
    return {
        "row_index": action_item.get("catalog_index"),
        "catalog_index": action_item.get("catalog_index"),
        "source_store": action_item.get("source_store"),
        "name_ko": action_item.get("name_ko"),
        "name_ja": action_item.get("name_ja"),
        "category": action_item.get("category"),
        "character_name": action_item.get("character_name"),
        "source_url": action_item.get("source_url"),
        "review_lane": action_item.get("review_lane"),
        "candidate_status": candidate_status,
        "row_type": candidate_row.get("row_type") if isinstance(candidate_row, dict) else None,
        "motifs": candidate_row.get("motifs") if isinstance(candidate_row, dict) else [],
        "candidate_count": len(candidates),
        "candidate_options": candidates,
        "top_candidate": candidates[0] if candidates else {},
        "image_url_import_template": _manual_image_template(action_item, candidate_row),
        "review_blockers": _review_blockers(str(candidate_status or "")),
        "manual_confirmation_requirements": [
            "Open candidate page and image when candidates exist.",
            "Confirm character, place/motif, product type, and variant visually.",
            "Representative images are allowed only when the product type mismatch is acceptable for catalog display.",
            "If no exact or acceptable representative image exists, leave manual_confirmed=false.",
        ],
        "batch_id": action_item.get("batch_id"),
        "auto_apply_enabled": False,
    }


def _review_blockers(status: str) -> list[str]:
    if status == "no_official_candidate":
        return ["no_official_candidate_image", "manual_external_official_search_required"]
    if status == "motif_only_type_mismatch":
        return ["motif_match_only", "product_type_mismatch", "visual_identity_review_required"]
    if "visual_mismatch" in status:
        return ["visual_mismatch", "do_not_import_without_stronger_evidence"]
    if status == "attached_representative_official_image":
        return ["representative_image_requires_manual_confirmation"]
    return ["candidate_status_unresolved", "manual_review_required"]


def _build_status_workstreams(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_status: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_status.setdefault(_compact_text(item.get("candidate_status")) or "unknown", []).append(item)

    workstreams: list[dict[str, Any]] = []
    for status, rows in by_status.items():
        rows = sorted(rows, key=lambda row: (int(row.get("candidate_count") or 0), int(row.get("catalog_index") or 0)))
        workstreams.append(
            {
                "candidate_status": status,
                "row_count": len(rows),
                "by_category": _counter_pairs(rows, "category"),
                "by_character_name": _counter_pairs(rows, "character_name"),
                "candidate_rows": sum(1 for row in rows if row.get("candidate_options")),
                "rows": rows,
                "recommended_review_order": [
                    "Review motif-only/type-mismatch rows before rows with no candidates.",
                    "Do not import image_url unless manual visual identity review passes.",
                    "Use representative_image=true only for acceptable representative display images.",
                ],
                "auto_apply_enabled": False,
            }
        )
    workstreams.sort(key=lambda row: (-int(row["row_count"]), str(row["candidate_status"])))
    return workstreams


def build_queue(
    action_queue: dict[str, Any],
    candidate_report: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    candidate_by_index = _candidate_lookup(candidate_report)
    items = [
        _review_item(item, candidate_by_index.get(int(item.get("catalog_index"))))
        for item in _action_items(action_queue)
        if isinstance(item.get("catalog_index"), int) and not isinstance(item.get("catalog_index"), bool)
    ]
    workstreams = _build_status_workstreams(items)
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "gotouchi_official_candidate_review_queue",
        "summary": {
            "review_rows": len(items),
            "workstream_count": len(workstreams),
            "by_candidate_status": _counter_pairs(items, "candidate_status"),
            "by_category": _counter_pairs(items, "category"),
            "by_character_name": _counter_pairs(items, "character_name"),
            "with_candidate_options": sum(1 for item in items if item.get("candidate_options")),
            "without_candidate_options": sum(1 for item in items if not item.get("candidate_options")),
            "manual_confirmed_true": 0,
            "auto_apply_enabled": False,
        },
        "instructions": [
            "This queue covers Gotouchi rows that require official candidate visual review.",
            "Candidate images are review hints only and must not be imported automatically.",
            "Set image_url_import_template.manual_confirmed=true only after visual identity review.",
            "Use tools/import_confirmed_image_attachment_rows.py as a dry-run before write imports.",
        ],
        "workstreams": workstreams,
        "items": items,
        "automation_policy": {
            "auto_apply_image_url": False,
            "requires_manual_review": True,
            "requires_representative_image_flag": True,
            "import_tool": "tools/import_confirmed_image_attachment_rows.py",
            "private_collection_storage": "local_device_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-queue", type=Path, default=DEFAULT_ACTION_QUEUE)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_queue(load_json(args.action_queue), load_json(args.candidates))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
