from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_LEDGER = ROOT / "server" / "boss_review" / "boss_review_ledger.json"
DEFAULT_APPROVED = ROOT / "server" / "boss_review" / "catalog_public_approved.json"
DEFAULT_REWORK = ROOT / "server" / "boss_review" / "boss_review_rework_queue.json"

ALLOWED_STATUSES = {
    "image_error",
    "content_error",
    "pass",
}
APPROVED_STATUSES = {"pass"}
BLOCKED_STATUSES = {"image_error", "content_error"}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_payload(path: Path) -> dict[str, Any]:
    payload = _read_json(path, {})
    if isinstance(payload, list):
        return {"meta": {}, "items": payload, "total_items": len(payload)}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object or list")
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain an items list")
    return payload


def _row_index(index: int, item: dict[str, Any]) -> int:
    value = item.get("catalog_index")
    if isinstance(value, bool):
        return index
    if isinstance(value, int):
        return value
    return index


def _normalize_decisions(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path, {})
    decisions = payload.get("decisions") if isinstance(payload, dict) else []
    if not isinstance(decisions, list):
        raise ValueError(f"{path} must contain a decisions list")
    normalized: list[dict[str, Any]] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        row_index = decision.get("row_index")
        raw_statuses = decision.get("statuses")
        if isinstance(raw_statuses, list):
            statuses = [str(status).strip() for status in raw_statuses if str(status).strip()]
        else:
            status = str(decision.get("status") or "").strip()
            statuses = [status] if status else []
        statuses = ["pass" if status == "fixed_pass" else status for status in statuses]
        if "pass" in statuses:
            statuses = ["pass"]
        else:
            statuses = sorted({status for status in statuses if status})
        status = "pass" if statuses == ["pass"] else ("image_error" if "image_error" in statuses else "content_error" if "content_error" in statuses else "")
        if isinstance(row_index, bool) or not isinstance(row_index, int):
            raise ValueError(f"decision has invalid row_index: {decision!r}")
        invalid = [item for item in statuses if item not in ALLOWED_STATUSES]
        if invalid or not statuses:
            raise ValueError(f"row {row_index} has invalid statuses: {statuses!r}")
        normalized.append(
            {
                "row_index": row_index,
                "catalog_index": decision.get("catalog_index", row_index),
                "display_name": decision.get("display_name"),
                "status": status,
                "statuses": statuses,
                "status_label": decision.get("status_label"),
                "note": decision.get("note") or "",
                "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            }
        )
    return normalized


def merge_ledger(ledger_path: Path, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    ledger = _read_json(ledger_path, {"meta": {}, "decisions": []})
    if not isinstance(ledger, dict):
        ledger = {"meta": {}, "decisions": []}
    existing = {
        int(item["row_index"]): item
        for item in ledger.get("decisions", [])
        if isinstance(item, dict)
        and isinstance(item.get("row_index"), int)
        and not isinstance(item.get("row_index"), bool)
    }
    for decision in decisions:
        existing[int(decision["row_index"])] = decision
    merged = [existing[key] for key in sorted(existing)]
    ledger["decisions"] = merged
    ledger["meta"] = {
        **(ledger.get("meta") if isinstance(ledger.get("meta"), dict) else {}),
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "reviewed_items": len(merged),
        "approved_items": sum(1 for item in merged if _is_approved(item)),
        "blocked_items": sum(1 for item in merged if not _is_approved(item)),
        "allowed_statuses": sorted(ALLOWED_STATUSES),
        "approved_statuses": sorted(APPROVED_STATUSES),
    }
    return ledger


def _decision_statuses(decision: dict[str, Any]) -> list[str]:
    raw = decision.get("statuses")
    if isinstance(raw, list):
        return [str(status) for status in raw if str(status)]
    status = str(decision.get("status") or "")
    if status == "fixed_pass":
        return ["pass"]
    return [status] if status else []


def _is_approved(decision: dict[str, Any]) -> bool:
    return _decision_statuses(decision) == ["pass"]


def build_approved_catalog(catalog_path: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    payload = _catalog_payload(catalog_path)
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    approved_indexes = {
        int(decision["row_index"]): decision
        for decision in ledger.get("decisions", [])
        if isinstance(decision, dict)
        and _is_approved(decision)
        and isinstance(decision.get("row_index"), int)
        and not isinstance(decision.get("row_index"), bool)
    }
    approved_items: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        row_index = _row_index(index, item)
        decision = approved_indexes.get(row_index)
        if not decision:
            continue
        approved_items.append(
            {
                **item,
                "boss_review": {
                    "status": decision.get("status"),
                    "status_label": decision.get("status_label"),
                    "reviewed_at": decision.get("reviewed_at"),
                },
            }
        )
    return {
        "meta": {
            **(payload.get("meta") if isinstance(payload.get("meta"), dict) else {}),
            "boss_review_generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source_catalog": str(catalog_path.relative_to(ROOT) if catalog_path.is_relative_to(ROOT) else catalog_path),
            "approved_items": len(approved_items),
            "reviewed_items": len(ledger.get("decisions", [])),
            "approval_policy": "Only rows with pass are included. Legacy fixed_pass decisions are read as pass.",
        },
        "items": approved_items,
        "total_items": len(approved_items),
    }


def _display_name(item: dict[str, Any]) -> str:
    return str(
        item.get("name_ko")
        or item.get("name_ja")
        or item.get("name_en")
        or item.get("name")
        or "이름 없음"
    )


def _rework_type(status: str) -> str:
    if status == "image_error":
        return "image_update"
    if status == "content_error":
        return "field_update"
    return "manual_review"


def build_rework_queue(catalog_path: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    payload = _catalog_payload(catalog_path)
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    catalog_by_index = {_row_index(index, item): item for index, item in enumerate(items)}
    blocked = [
        decision
        for decision in ledger.get("decisions", [])
        if isinstance(decision, dict) and not _is_approved(decision)
    ]
    queue: list[dict[str, Any]] = []
    for decision in blocked:
        row_index = decision.get("row_index")
        if isinstance(row_index, bool) or not isinstance(row_index, int):
            continue
        item = catalog_by_index.get(row_index, {})
        statuses = [status for status in _decision_statuses(decision) if status in BLOCKED_STATUSES]
        status = "image_error" if "image_error" in statuses else "content_error"
        queue.append(
            {
                "row_index": row_index,
                "catalog_index": item.get("catalog_index", row_index),
                "status": status,
                "statuses": statuses,
                "status_label": decision.get("status_label"),
                "rework_type": "image_and_field_update"
                if {"image_error", "content_error"}.issubset(set(statuses))
                else _rework_type(status),
                "display_name": decision.get("display_name") or _display_name(item),
                "note": decision.get("note") or "",
                "source_url": item.get("source_url"),
                "image_url": item.get("image_url"),
                "local_image_path": item.get("local_image_path"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "category": item.get("category"),
                "character_name": item.get("character_name"),
                "affiliation": item.get("affiliation"),
                "series_name": item.get("series_name"),
                "sub_series": item.get("sub_series"),
                "next_step": (
                    "Submit confirmed image and field fixes through the matching data/intake incoming folders."
                    if {"image_error", "content_error"}.issubset(set(statuses))
                    else "Submit a confirmed image fix through data/intake/image_updates/incoming/."
                    if "image_error" in statuses
                    else "Submit a confirmed field correction through data/intake/field_updates/incoming/."
                ),
            }
        )
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source_catalog": str(catalog_path.relative_to(ROOT) if catalog_path.is_relative_to(ROOT) else catalog_path),
            "blocked_items": len(queue),
            "image_error_items": sum(1 for item in queue if "image_error" in (item.get("statuses") or [])),
            "content_error_items": sum(1 for item in queue if "content_error" in (item.get("statuses") or [])),
            "purpose": "Rows blocked by boss review; route these back to image or field update intake before publishing.",
        },
        "items": queue,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import boss review decisions and build an approved-only catalog.")
    parser.add_argument("decisions", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--approved-out", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--rework-out", type=Path, default=DEFAULT_REWORK)
    args = parser.parse_args()

    decisions = _normalize_decisions(args.decisions)
    ledger = merge_ledger(args.ledger, decisions)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    approved = build_approved_catalog(args.catalog, ledger)
    args.approved_out.parent.mkdir(parents=True, exist_ok=True)
    args.approved_out.write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rework = build_rework_queue(args.catalog, ledger)
    args.rework_out.parent.mkdir(parents=True, exist_ok=True)
    args.rework_out.write_text(json.dumps(rework, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "imported_decisions": len(decisions),
                "reviewed_items": ledger["meta"]["reviewed_items"],
                "approved_items": ledger["meta"]["approved_items"],
                "blocked_items": ledger["meta"]["blocked_items"],
                "approved_out": str(args.approved_out),
                "rework_out": str(args.rework_out),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
