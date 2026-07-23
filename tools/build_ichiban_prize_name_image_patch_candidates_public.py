from __future__ import annotations

import argparse
import difflib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from import_ichiban_kuji_history import extract_campaign

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_REVIEW = DATA / "ichiban_kuji_prize_name_image_review_public.json"
DEFAULT_OUTPUT = DATA / "ichiban_kuji_prize_name_image_patch_candidates_public.json"


def _norm(value: Any) -> str:
    return "".join(str(value or "").split()).casefold()


def _similarity(left: Any, right: Any) -> float:
    return difflib.SequenceMatcher(None, _norm(left), _norm(right)).ratio()


def _expected_prize_display_name(prize_rank: str, name_ja: str) -> str:
    prize_rank = prize_rank.strip()
    name_ja = name_ja.strip()
    if not prize_rank:
        return name_ja
    if not name_ja:
        return prize_rank
    if name_ja.startswith(prize_rank):
        return name_ja
    return f"{prize_rank} {name_ja}"


def _expected_display_name(series_name: str, prize_rank: str, name_ja: str) -> str:
    prize_display_name = _expected_prize_display_name(prize_rank, name_ja)
    if series_name and prize_display_name:
        return f"{series_name} - {prize_display_name}"
    return series_name or prize_display_name


def _index_official_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    by_image: dict[str, dict[str, Any]] = {}
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name_ja = str(row.get("name_ja") or "").strip()
        image_url = str(row.get("image_url") or "").strip()
        if not name_ja or not image_url:
            continue
        official = {
            "name_ja": name_ja,
            "sub_series": row.get("sub_series"),
            "image_url": image_url,
        }
        cleaned.append(official)
        by_image.setdefault(image_url, official)
    return by_image, cleaned


def _best_name_match(prize_item_name: str, official_rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for row in official_rows:
        score = _similarity(prize_item_name, row.get("name_ja"))
        if score > best_score:
            best = row
            best_score = score
    return best, best_score


def _blocked_row(row: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "source_url": row.get("source_url"),
        "reason": reason,
        "review_reason": row.get("review_reason"),
        "series_name": row.get("series_name"),
        "current_prize_rank": row.get("prize_rank"),
        "current_name_ja": row.get("prize_item_name"),
        "current_display_name_ko": row.get("display_name_ko"),
        "expected_display_name_ko": row.get("expected_display_name_ko"),
        "current_image_url": row.get("image_url"),
        "manual_fix_template": row.get("manual_fix_template"),
        "manual_confirmed": False,
        "recommended_manual_action": "open_official_campaign_lineup_and_fill_manual_fix_template",
    }


def build_report(
    review_report: dict[str, Any],
    *,
    generated_at: str | None = None,
    sleep: float = 0.0,
    fetch_campaign: Callable[[str], list[dict[str, Any]]] = extract_campaign,
) -> dict[str, Any]:
    generated_at = generated_at or ""
    review_rows = [row for row in review_report.get("review_rows", []) if isinstance(row, dict)]
    source_urls = []
    for row in review_rows:
        source_url = str(row.get("source_url") or "")
        if not source_url or source_url == "https://1kuji.com/" or source_url in source_urls:
            continue
        source_urls.append(source_url)

    official_by_url: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    for index, source_url in enumerate(source_urls):
        if index and sleep:
            time.sleep(sleep)
        try:
            official_rows = fetch_campaign(source_url)
        except Exception as error:  # pragma: no cover - network failures are reported, not fatal
            failures.append({"source_url": source_url, "error": f"{type(error).__name__}: {error}"})
            continue
        by_image, rows = _index_official_rows(official_rows)
        official_by_url[source_url] = {
            "rows": rows,
            "by_image": by_image,
        }

    candidates: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    for row in review_rows:
        source_url = str(row.get("source_url") or "")
        official = official_by_url.get(source_url)
        if not official:
            blocked_rows.append(
                _blocked_row(
                    row,
                    reason="official_campaign_not_fetchable_or_root_url",
                )
            )
            continue

        current_image = str(row.get("image_url") or "")
        current_name = str(row.get("prize_item_name") or "")
        matched = official["by_image"].get(current_image)
        match_type = "exact_image_match" if matched else ""
        score = 1.0 if matched else 0.0
        if not matched:
            matched, score = _best_name_match(current_name, official["rows"])
            if matched and score >= 0.86:
                match_type = "strong_name_match"
            else:
                matched = None

        if not matched:
            blocked_rows.append(
                _blocked_row(
                    row,
                    reason="no_safe_official_name_or_image_match",
                )
            )
            continue

        suggested_name_ja = str(matched.get("name_ja") or "").strip()
        suggested_sub_series = str(matched.get("sub_series") or "").strip()
        suggested_image_url = str(matched.get("image_url") or "").strip()
        series_name = str(row.get("series_name") or "").strip()
        suggested_prize_display_name = _expected_prize_display_name(suggested_sub_series, suggested_name_ja)
        suggested_name_ko = _expected_display_name(series_name, suggested_sub_series, suggested_name_ja)
        current_sub_series = str(row.get("prize_rank") or "").strip()
        current_name_ko = str(row.get("display_name_ko") or "").strip()

        field_changes: dict[str, dict[str, Any]] = {}
        if suggested_name_ja and suggested_name_ja != current_name:
            field_changes["name_ja"] = {"from": current_name, "to": suggested_name_ja}
        if suggested_sub_series and suggested_sub_series != current_sub_series:
            field_changes["sub_series"] = {"from": current_sub_series, "to": suggested_sub_series}
        if suggested_name_ko and suggested_name_ko != current_name_ko:
            field_changes["name_ko"] = {"from": current_name_ko, "to": suggested_name_ko}
        if suggested_image_url and suggested_image_url != current_image:
            field_changes["image_url"] = {"from": current_image, "to": suggested_image_url}

        if not field_changes:
            blocked_rows.append(
                _blocked_row(
                    row,
                    reason="official_match_found_but_no_field_change",
                )
            )
            continue

        candidates.append(
            {
                "manual_review_status": "not_started",
                "manual_confirmed": False,
                "catalog_index": row.get("catalog_index"),
                "source_url": source_url,
                "match_type": match_type,
                "match_score": round(score, 4),
                "series_name": series_name,
                "current_prize_rank": current_sub_series,
                "current_name_ja": current_name,
                "current_display_name_ko": current_name_ko,
                "current_image_url": current_image,
                "official_prize_rank": suggested_sub_series,
                "official_name_ja": suggested_name_ja,
                "official_prize_display_name": suggested_prize_display_name,
                "suggested_display_name_ko": suggested_name_ko,
                "official_image_url": suggested_image_url,
                "field_changes": field_changes,
                "catalog_patch_template": {
                    "catalog_index": row.get("catalog_index"),
                    "name_ko": field_changes.get("name_ko", {}).get("to", ""),
                    "name_ja": field_changes.get("name_ja", {}).get("to", ""),
                    "sub_series": field_changes.get("sub_series", {}).get("to", ""),
                    "image_url": field_changes.get("image_url", {}).get("to", ""),
                    "evidence_url": source_url,
                    "manual_confirmed": False,
                },
                "auto_apply_enabled": False,
            }
        )

    candidates.sort(key=lambda row: (str(row.get("source_url") or ""), int(row.get("catalog_index") or 0)))
    blocked_rows.sort(key=lambda row: (str(row.get("source_url") or ""), int(row.get("catalog_index") or 0)))
    blocked_reason_counts = Counter(str(row.get("reason") or "unknown") for row in blocked_rows)
    blocked_review_reason_counts = Counter(str(row.get("review_reason") or "unknown") for row in blocked_rows)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "ichiban_kuji_prize_name_image_patch_candidates",
        "summary": {
            "review_rows": len(review_rows),
            "source_urls": len(source_urls),
            "fetched_source_urls": len(official_by_url),
            "fetch_failure_urls": len(failures),
            "candidate_rows": len(candidates),
            "exact_image_match_rows": sum(1 for row in candidates if row["match_type"] == "exact_image_match"),
            "strong_name_match_rows": sum(1 for row in candidates if row["match_type"] == "strong_name_match"),
            "blocked_rows": len(blocked_rows),
            "blocked_reason_counts": blocked_reason_counts.most_common(),
            "blocked_review_reason_counts": blocked_review_reason_counts.most_common(),
            "blocked_rows_with_manual_fix_template": sum(
                1 for row in blocked_rows if isinstance(row.get("manual_fix_template"), dict)
            ),
            "auto_apply_enabled": False,
            "recommended_next_action": "manual_confirm_exact_official_patch_candidates_or_fill_blocked_manual_templates",
        },
        "candidates": candidates,
        "blocked_rows": blocked_rows,
        "fetch_failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    review_report = json.loads(args.review.read_text(encoding="utf-8"))
    report = build_report(review_report, sleep=args.sleep)
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to update the public report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
