from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "gotouchi_chiikawa_image_candidates_public.json"
CATALOG = DATA / "catalog_public.json"
OUTPUT = DATA / "gotouchi_representative_image_attachment_public.json"

TARGET_STATUS = "attached_representative_official_image"
GOTOUCHI_STORE = "ご当地ちいかわ 공식(API)"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def first_candidate(item: dict[str, Any]) -> dict[str, Any]:
    candidates = item.get("top_candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate
    return {}


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def catalog_image_lookup(catalog: dict[str, Any] | None) -> dict[int, bool]:
    if not catalog:
        return {}
    items = catalog.get("items")
    if not isinstance(items, list):
        return {}
    lookup: dict[int, bool] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        catalog_index = item.get("catalog_index")
        if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
            lookup[catalog_index] = present(item.get("local_image_path")) or present(item.get("image_url"))
    return lookup


def template_for(item: dict[str, Any]) -> dict[str, Any]:
    candidate = first_candidate(item)
    image_url = str(candidate.get("image_url") or "").strip()
    evidence_url = str(candidate.get("page") or item.get("source_url") or "").strip()
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "catalog_index": item.get("catalog_index"),
        "field": "image_url",
        "manual_value": image_url,
        "evidence_url": evidence_url,
        "candidate_source_url": evidence_url,
        "representative_image": True,
        "source_store": item.get("source_store") or GOTOUCHI_STORE,
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "character_name": item.get("character_name"),
        "candidate_status": item.get("candidate_status"),
        "candidate_alt": candidate.get("alt"),
        "candidate_type": candidate.get("type"),
        "row_type": item.get("row_type"),
        "matched_motifs": candidate.get("matched_motifs") or [],
        "blocked_until": "manual_confirmed_true_after_visual_identity_review",
    }


def build_report(payload: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    return build_report_for_catalog(payload, None, generated_at=generated_at)


def build_report_for_catalog(
    payload: dict[str, Any],
    catalog: dict[str, Any] | None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    has_image_by_index = catalog_image_lookup(catalog)
    skipped_already_has_image = 0
    eligible_items: list[dict[str, Any]] = []
    for item in items:
        catalog_index = item.get("catalog_index")
        if isinstance(catalog_index, int) and has_image_by_index.get(catalog_index):
            skipped_already_has_image += 1
            continue
        eligible_items.append(item)
    templates = [
        template_for(item)
        for item in eligible_items
        if item.get("candidate_status") == TARGET_STATUS and first_candidate(item).get("image_url")
    ]
    by_category = Counter(str(item.get("category") or "") for item in templates)
    by_character = Counter(str(item.get("character_name") or "") for item in templates)

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "gotouchi_representative_image_attachment",
        "summary": {
            "representative_attachment_rows": len(templates),
            "skipped_already_has_image_rows": skipped_already_has_image,
            "manual_confirmed_true": sum(1 for item in templates if item.get("manual_confirmed") is True),
            "auto_apply_enabled": False,
        },
        "breakdowns": {
            "by_category": [{"category": key, "rows": value} for key, value in by_category.most_common()],
            "by_character_name": [
                {"character_name": key, "rows": value} for key, value in by_character.most_common()
            ],
        },
        "items": templates,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_confirmed_true": True,
            "requires_visual_identity_review": True,
            "safe_import_command": (
                "python tools/import_confirmed_image_attachment_rows.py "
                "--queue data/gotouchi_representative_image_attachment_public.json"
            ),
        },
    }


def write_report(report: dict[str, Any], path: Path = OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report_for_catalog(load_json(args.input), load_json(args.catalog) if args.catalog.exists() else None)
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
