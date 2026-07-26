from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from import_chiikawa_online_kuji_history import extract_campaign

DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "data" / "chiikawa_online_kuji_public_image_repair_report.json"

CHARACTER_TOKENS = (
    "ちいかわ",
    "ハチワレ",
    "うさぎ",
    "モモンガ",
    "くりまんじゅう",
    "シーサー",
    "ラッコ",
    "古本屋",
)

MANUAL_EXACT_MATCHES = {
    674: {
        "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/chiikawa",
        "candidate_name_ja": "A ピース",
        "note": "ちいかわだらけくじ A賞 BIGぬいぐるみ ピース",
    },
    675: {
        "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/chiikawa",
        "candidate_name_ja": "A ヤダッ",
        "note": "ちいかわだらけくじ A賞 BIGぬいぐるみ ヤダ",
    },
    676: {
        "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/chiikawa",
        "candidate_name_ja": "B 磁石でぴたっと！なかよしぬいぐるみ （ちいかわとカブトムシ）",
        "note": "ちいかわだらけくじ B賞 マグネット付きおとも人形",
    },
    678: {
        "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/hachiware",
        "candidate_name_ja": "A 撮るよーッ!!!",
        "note": "ハチワレだらけくじ A賞 BIGぬいぐるみ 撮るよーッ!!!",
    },
    679: {
        "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/hachiware",
        "candidate_name_ja": "A ピース",
        "note": "ハチワレだらけくじ A賞 BIGぬいぐるみ 照れピース",
    },
    680: {
        "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/hachiware",
        "candidate_name_ja": "B 下剋上",
        "note": "ハチワレだらけくじ B賞 フェイスクッション 下剋上",
    },
    681: {
        "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/hachiware",
        "candidate_name_ja": "B …ってコト！？",
        "note": "ハチワレだらけくじ B賞 フェイスクッション …ってコト!?",
    },
}


def load_catalog(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON list or an object with items")
    return payload, [row for row in rows if isinstance(row, dict)]


def write_catalog(path: Path, payload: Any, rows: list[dict[str, Any]]) -> None:
    if isinstance(payload, dict):
        payload["items"] = rows
        meta = payload.get("meta")
        if isinstance(meta, dict):
            missing = dict(meta.get("missing") or {})
            missing["image_url"] = sum(1 for row in rows if not row.get("image_url"))
            missing["local_image_path"] = sum(1 for row in rows if not row.get("local_image_path"))
            meta["missing"] = missing
            meta["row_count"] = len(rows)
            meta["total_items"] = len(rows)
        output = payload
    else:
        output = rows
    path.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def missing_online_rows(rows: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    result: list[tuple[int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        source_url = str(row.get("source_url") or "")
        if "online-kuji.chiikawamarket.jp" not in source_url:
            continue
        if row.get("image_url") or row.get("local_image_path"):
            continue
        result.append((index, row))
    return result


def prize_tier(text: str) -> str:
    match = re.match(r"\s*([A-Z])(?:賞|\s)", text)
    return match.group(1) if match else ""


def candidate_key(row: dict[str, Any]) -> tuple[str, str]:
    name = str(row.get("name_ja") or "")
    tier = prize_tier(name)
    detail = re.sub(r"^\s*[A-Z]\s*", "", name).strip()
    return tier, detail


def row_matches_candidate(row: dict[str, Any], candidate: dict[str, Any]) -> bool:
    row_name = str(row.get("name_ja") or "")
    tier, detail = candidate_key(candidate)
    if not tier or prize_tier(row_name) != tier:
        return False
    if not detail:
        return False
    if detail in row_name:
        return True
    return any(token == detail and token in row_name for token in CHARACTER_TOKENS)


def build_candidate_lookup(urls: list[str]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    by_url: dict[str, list[dict[str, Any]]] = {}
    failures: list[dict[str, Any]] = []
    for url in urls:
        if not url.rstrip("/").endswith("/store/lottery") and "/store/lottery/" not in url:
            failures.append({"source_url": url, "reason": "not_campaign_detail_url"})
            continue
        try:
            by_url[url] = extract_campaign(url)
        except Exception as error:
            failures.append({"source_url": url, "reason": type(error).__name__, "message": str(error)})
    return by_url, failures


def _manual_exact_candidate(
    index: int,
    row: dict[str, Any],
    by_url: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    catalog_index = row.get("catalog_index", index)
    if not isinstance(catalog_index, int):
        return None, None
    rule = MANUAL_EXACT_MATCHES.get(catalog_index)
    if not rule:
        return None, None
    source_url = str(rule["source_url"])
    expected = str(rule["candidate_name_ja"])
    for candidate in by_url.get(source_url, []):
        if candidate.get("name_ja") == expected and candidate.get("image_url"):
            return candidate, rule
    return None, rule


def repair(rows: list[dict[str, Any]], *, write: bool) -> dict[str, Any]:
    targets = missing_online_rows(rows)
    urls = {
        str(row.get("source_url") or "")
        for _, row in targets
        if str(row.get("source_url") or "").rstrip("/") != "https://online-kuji.chiikawamarket.jp"
    }
    urls.update(str(rule["source_url"]) for rule in MANUAL_EXACT_MATCHES.values())
    urls = sorted(urls)
    by_url, failures = build_candidate_lookup(urls)
    used_by_url: dict[str, set[int]] = defaultdict(set)
    repaired: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for index, row in targets:
        manual_candidate, manual_rule = _manual_exact_candidate(index, row, by_url)
        if manual_candidate and manual_rule:
            if write:
                row["source_url"] = manual_rule["source_url"]
                row["image_url"] = manual_candidate["image_url"]
            repaired.append(
                {
                    "catalog_index": row.get("catalog_index", index),
                    "row_index": index,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_url": manual_rule["source_url"],
                    "previous_source_url": row.get("source_url"),
                    "matched_candidate_name_ja": manual_candidate.get("name_ja"),
                    "image_url": manual_candidate.get("image_url"),
                    "match_method": "manual_exact_campaign_mapping",
                    "manual_note": manual_rule.get("note"),
                }
            )
            continue
        if manual_rule:
            skipped.append(
                {
                    "catalog_index": row.get("catalog_index", index),
                    "row_index": index,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_url": manual_rule["source_url"],
                    "previous_source_url": row.get("source_url"),
                    "reason": "manual_exact_candidate_not_found",
                    "expected_candidate_name_ja": manual_rule["candidate_name_ja"],
                }
            )
            continue
        source_url = str(row.get("source_url") or "")
        candidates = by_url.get(source_url) or []
        matches = [
            (candidate_index, candidate)
            for candidate_index, candidate in enumerate(candidates)
            if candidate_index not in used_by_url[source_url] and row_matches_candidate(row, candidate)
        ]
        if len(matches) == 1 and matches[0][1].get("image_url"):
            candidate_index, candidate = matches[0]
            used_by_url[source_url].add(candidate_index)
            if write:
                row["image_url"] = candidate["image_url"]
            repaired.append(
                {
                    "catalog_index": row.get("catalog_index", index),
                    "row_index": index,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "source_url": source_url,
                    "matched_candidate_name_ja": candidate.get("name_ja"),
                    "image_url": candidate.get("image_url"),
                }
            )
            continue
        skipped.append(
            {
                "catalog_index": row.get("catalog_index", index),
                "row_index": index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_url": source_url,
                "reason": "no_unique_safe_candidate",
                "candidate_count": len(matches),
            }
        )

    return {
        "schema_version": 1,
        "scope": "chiikawa_online_kuji_public_image_repair",
        "summary": {
            "target_rows": len(targets),
            "repaired_rows": len(repaired),
            "skipped_rows": len(skipped),
            "fetch_failed_campaigns": len(failures),
            "write": write,
            "by_source_url": [
                {"source_url": url, "target_rows": count}
                for url, count in Counter(str(row.get("source_url") or "") for _, row in targets).most_common()
            ],
        },
        "repaired": repaired,
        "skipped": skipped,
        "fetch_failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    payload, rows = load_catalog(args.catalog)
    report = repair(rows, write=args.write)
    if args.write:
        write_catalog(args.catalog, payload, rows)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
