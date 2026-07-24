from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_next_focus_live_source_probe_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_next_focus_variant_metadata_backfill_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _risk_flags(candidate: dict[str, Any]) -> list[str]:
    risk = candidate.get("variant_risk") or {}
    flags = risk.get("flags") or []
    return [str(flag) for flag in flags if str(flag).strip()]


def _candidate_digest(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_url": candidate.get("source_url"),
        "page_title": candidate.get("page_title"),
        "title_match": candidate.get("title_match") or {},
        "variant_risk": candidate.get("variant_risk") or {},
    }


def _recommended_metadata_fields(flags: set[str]) -> list[str]:
    fields = ["name_ja", "sub_series"]
    if {
        "letter_or_version_variant",
        "named_theme_variant",
        "collection_or_trading_variant",
        "mini_or_junior_variant",
        "oversized_variant",
    } & flags:
        fields.append("name_ko")
    if "calendar_product_type" in flags:
        fields.append("category")
    return fields


def build_report(live_probe: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    out_items: list[dict[str, Any]] = []
    flag_counts: Counter[str] = Counter()
    for item in live_probe.get("items") or []:
        if not isinstance(item, dict):
            continue
        strong_candidates = item.get("strong_title_match_candidates") or []
        risky = [
            candidate
            for candidate in strong_candidates
            if isinstance(candidate, dict) and _risk_flags(candidate)
        ]
        if not risky:
            continue
        flags = {flag for candidate in risky for flag in _risk_flags(candidate)}
        flag_counts.update(flags)
        out_items.append(
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "search_term": item.get("search_term"),
                "category": item.get("category"),
                "source_store": item.get("source_store"),
                "review_url": item.get("review_url"),
                "strong_title_match_candidate_count": item.get("strong_title_match_candidate_count") or 0,
                "risky_strong_candidate_count": len(risky),
                "variant_risk_flags": sorted(flags),
                "recommended_metadata_fields": _recommended_metadata_fields(flags),
                "manual_backfill_required": True,
                "auto_apply_enabled": False,
                "blocked_until": "exact_variant_metadata_backfilled_or_candidate_rejected",
                "metadata_backfill_template": {
                    "catalog_index": item.get("catalog_index"),
                    "manual_confirmed": False,
                    "manual_confirmed_name_ja": "",
                    "manual_confirmed_name_ko": "",
                    "manual_confirmed_sub_series": "",
                    "manual_confirmed_category": "",
                    "manual_evidence_url": "",
                    "manual_note": "",
                },
                "candidate_samples": [_candidate_digest(candidate) for candidate in risky[:10]],
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_next_focus_variant_metadata_backfill",
        "source_reports": [str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/")],
        "summary": {
            "queue_rows": len(out_items),
            "risky_strong_candidate_rows": len(out_items),
            "risky_strong_candidate_total": sum(
                int(item.get("risky_strong_candidate_count") or 0) for item in out_items
            ),
            "variant_risk_flag_counts": flag_counts.most_common(),
            "auto_apply_enabled": False,
            "recommended_next_action": (
                "review candidate_samples and backfill exact name/sub_series/category metadata "
                "before confirming source_url or image_url"
            ),
        },
        "automation_policy": {
            "auto_apply_metadata": False,
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "requires_manual_exact_variant_review": True,
        },
        "items": out_items,
    }


def write_report(report: dict[str, Any], path: Path = DEFAULT_OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to save the public variant metadata backfill queue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
