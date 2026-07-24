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
DEFAULT_INPUT = DATA / "source_discovery_next_focus_identity_backfill_queue_public.json"
REPORT = DATA / "source_discovery_next_focus_identity_candidate_review_queue_public.json"


IDENTITY_CANDIDATE_HINTS: dict[int, list[dict[str, Any]]] = {
    1082: [
        {
            "candidate_identity": "ジョナサン・ジョースター / バストアップアクリルスタンド【PB】①",
            "candidate_source_url": "https://www.animate-onlineshop.jp/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%82%A2%E3%83%8B%E3%83%A1%E3%80%8E%E3%82%B8%E3%83%A7%E3%82%B8%E3%83%A7%E3%81%AE%E5%A5%87%E5%A6%99%E3%81%AA%E5%86%92%E9%99%BA%2B%E3%83%95%E3%82%A1%E3%83%B3%E3%83%88%E3%83%A0%E3%83%96%E3%83%A9%E3%83%83%E3%83%89%E3%80%8F%2B%E3%83%90%E3%82%B9%E3%83%88%E3%82%A2%E3%83%83%E3%83%97%E3%82%A2%E3%82%AF%E3%83%AA%E3%83%AB%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%80%90PB%E3%80%91%E2%91%A0%E3%82%B8%E3%83%A7%E3%83%8A%E3%82%B5%E3%83%B3%E3%83%BB%E3%82%B8%E3%83%A7%E3%83%BC%E3%82%B9%E3%82%BF%E3%83%BC/pd/3516685/",
            "evidence_search_query": 'site:www.animate-onlineshop.jp/pn/ "ジョジョの奇妙な冒険" "アクリルスタンド" "ジョナサン"',
            "candidate_note": "Search result title matches JoJo Phantom Blood, acrylic stand, and Jonathan; row identity is still too generic to auto-confirm.",
        },
        {
            "candidate_identity": "ジョナサン・ジョースター / 描き下ろしBIGアクリルスタンドLL【AM2026】①【再販】",
            "candidate_source_url": "https://www.animate-onlineshop.jp/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%82%A2%E3%83%8B%E3%83%A1%E3%80%8E%E3%82%B8%E3%83%A7%E3%82%B8%E3%83%A7%E3%81%AE%E5%A5%87%E5%A6%99%E3%81%AA%E5%86%92%E9%99%BA%2B%E3%83%95%E3%82%A1%E3%83%B3%E3%83%88%E3%83%A0%E3%83%96%E3%83%A9%E3%83%83%E3%83%89%E3%80%8F%2B%E6%8F%8F%E3%81%8D%E4%B8%8B%E3%82%8D%E3%81%97BIG%E3%82%A2%E3%82%AF%E3%83%AA%E3%83%AB%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89LL%E3%80%90AM2026%E3%80%91%E2%91%A0%E3%82%B8%E3%83%A7%E3%83%8A%E3%82%B5%E3%83%B3%E3%83%BB%E3%82%B8%E3%83%A7%E3%83%BC%E3%82%B9%E3%82%BF%E3%83%BC%E3%80%90%E5%86%8D%E8%B2%A9%E3%80%91/pd/3480572/",
            "evidence_search_query": 'site:www.animate-onlineshop.jp/pn/ "ジョジョの奇妙な冒険" "アクリルスタンド" "再販"',
            "candidate_note": "Search result is an Animate product page but represents a specific AM2026 resale variant.",
        },
        {
            "candidate_identity": "ジョナサン・ジョースター / 描き下ろしオーロラアクリルスタンド【AM2026】①【再販】",
            "candidate_source_url": "https://www.animate-onlineshop.jp/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%82%A2%E3%83%8B%E3%83%A1%E3%80%8E%E3%82%B8%E3%83%A7%E3%82%B8%E3%83%A7%E3%81%AE%E5%A5%87%E5%A6%99%E3%81%AA%E5%86%92%E9%99%BA%2B%E3%83%95%E3%82%A1%E3%83%B3%E3%83%88%E3%83%A0%E3%83%96%E3%83%A9%E3%83%83%E3%83%89%E3%80%8F%2B%E6%8F%8F%E3%81%8D%E4%B8%8B%E3%82%8D%E3%81%97%E3%82%AA%E3%83%BC%E3%83%AD%E3%83%A9%E3%82%A2%E3%82%AF%E3%83%AA%E3%83%AB%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%80%90AM2026%E3%80%91%E2%91%A0%E3%82%B8%E3%83%A7%E3%83%8A%E3%82%B5%E3%83%B3%E3%83%BB%E3%82%B8%E3%83%A7%E3%83%BC%E3%82%B9%E3%82%BF%E3%83%BC%E3%80%90%E5%86%8D%E8%B2%A9%E3%80%91/pd/3480568/",
            "evidence_search_query": 'site:www.animate-onlineshop.jp/pn/ "ジョジョの奇妙な冒険" "アクリルスタンド" "再販"',
            "candidate_note": "Search result is an Animate product page but represents a different acrylic-stand variant.",
        },
    ],
    1123: [
        {
            "candidate_identity": "碇シンジ / おやすみシリーズ ゆらゆらアクリルスタンド",
            "candidate_source_url": "https://www.animate-onlineshop.jp/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%80%8E%E3%82%A8%E3%83%B4%E3%82%A1%E3%83%B3%E3%82%B2%E3%83%AA%E3%82%AA%E3%83%B3%E3%80%8F%E3%82%B7%E3%83%AA%E3%83%BC%E3%82%BA%2B%E3%81%8A%E3%82%84%E3%81%99%E3%81%BF%E3%82%B7%E3%83%AA%E3%83%BC%E3%82%BA%2B%E3%82%86%E3%82%89%E3%82%86%E3%82%89%E3%82%A2%E3%82%AF%E3%83%AA%E3%83%AB%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%2B%E7%A2%87%E3%82%B7%E3%83%B3%E3%82%B8/pd/3489435/",
            "evidence_search_query": 'site:www.animate-onlineshop.jp/pn/ "エヴァンゲリオン" "アクリルスタンド" "シンジ"',
            "candidate_note": "Search result title matches Evangelion series, acrylic stand, and Shinji; row identity is still generic.",
        },
        {
            "candidate_identity": "カヲル / カスタマニア",
            "candidate_source_url": "https://www.animate-onlineshop.jp/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%82%A8%E3%83%B4%E3%82%A1%E3%83%B3%E3%82%B2%E3%83%AA%E3%82%AA%E3%83%B3%2B%E3%82%AB%E3%82%B9%E3%82%BF%E3%83%9E%E3%83%8B%E3%82%A2%EF%BC%8F%E3%82%AB%E3%83%B2%E3%83%AB/pd/3133108/",
            "evidence_search_query": 'site:www.animate-onlineshop.jp/pn/ "エヴァンゲリオン" "アクリルスタンド"',
            "candidate_note": "Search result is an Animate stand-pop product but points to Kaworu, not a generic Evangelion acrylic stand.",
        },
    ],
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def build_report(payload: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row in payload.get("items") or []:
        if not isinstance(row, dict):
            continue
        catalog_index = row.get("catalog_index")
        candidates = IDENTITY_CANDIDATE_HINTS.get(catalog_index, [])
        items.append(
            {
                "catalog_index": catalog_index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_store": row.get("source_store"),
                "category": row.get("category"),
                "search_term": row.get("search_term"),
                "identity_blockers": row.get("identity_blockers") or [],
                "manual_confirmed": False,
                "manual_confirmed_identity": "",
                "manual_confirmed_source_url": "",
                "manual_note": "",
                "candidate_count": len(candidates),
                "candidates": candidates,
                "next_action": "pick_exact_identity_or_keep_unconfirmed_before_source_url_import",
                "auto_apply_enabled": False,
            }
        )

    with_candidates = sum(1 for item in items if int(item.get("candidate_count") or 0) > 0)
    candidate_total = sum(int(item.get("candidate_count") or 0) for item in items)
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "source_discovery_next_focus_identity_candidate_review_queue",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "queue_rows": len(items),
            "items_with_candidates": with_candidates,
            "candidate_rows": candidate_total,
            "manual_confirmed_rows": 0,
            "auto_apply_enabled": False,
            "recommended_next_action": "review candidate identities and only confirm exact matches",
        },
        "automation_policy": {
            "auto_apply_metadata": False,
            "auto_apply_source_url": False,
            "requires_manual_review": True,
        },
        "items": items,
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(_load_json(args.input))
    if args.write:
        write_report(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
