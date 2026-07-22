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
OUTPUT = DATA / "gotouchi_representative_image_attachment_public.json"

TARGET_STATUS = "attached_representative_official_image"


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
        "source_store": item.get("source_store") or "ご当地ちいかわ 公式(API)",
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
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    templates = [
        template_for(item)
        for item in items
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
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
