from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_animation_category_split_review_public as split_review


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPLIT_REVIEW = ROOT / "data" / "animation_category_split_review_public.json"
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "animation_category_unmatched_keyword_review_public.json"

STOPWORDS = {
    "goods",
    "グッズ",
    "굿즈",
    "一番くじ",
    "the",
    "and",
    "with",
    "ver",
    "vol",
    "cm",
}

PRODUCT_TYPE_MARKERS = {
    "アクリル",
    "アクリルチャーム",
    "アクリルコレクション",
    "アクリルキーホルダー",
    "アクリルスタンド",
    "アクリルセレクション",
    "アクキー",
    "アクスタ",
    "キーホルダー",
    "色紙",
    "ステッカー",
    "シール",
    "カード",
    "ブロマイド",
    "クリアファイル",
    "食器",
    "プレート",
    "グラス",
    "カップ",
    "スタンド",
    "ツインアクリルチャーム",
    "スクールアイコンボタン",
    "チャーム",
    "ピックリルスタンド",
    "フィギュア",
    "マスコット",
    "ラバーコレクション",
    "ラバーアソート",
    "ラバーチャーム",
    "アソート",
    "雑貨",
    "ボタン",
    "カメラ",
    "ケース",
    "ソックス",
    "シュシュ",
    "러버",
    "마스코트",
    "스탠드",
    "아크릴",
    "봉제인형",
    "키링",
    "카메라",
    "케이스",
    "피규어",
    "피크릴",
    "색지",
    "스티커",
    "카드",
    "브로마이드",
    "클리어파일",
    "식기",
    "컵",
    "머그",
}

PRODUCT_TYPE_ALIASES: dict[str, tuple[str, str]] = {
    "アクリル": ("아크릴", "acrylic"),
    "アクリルセレクション": ("아크릴", "acrylic"),
    "アクリルスタンド": ("아크릴 스탠드", "acrylic"),
    "アクスタ": ("아크릴 스탠드", "acrylic"),
    "スタンド": ("아크릴 스탠드", "acrylic"),
    "스탠드": ("아크릴 스탠드", "acrylic"),
    "ピックリルスタンド": ("아크릴 스탠드", "acrylic"),
    "피크릴": ("아크릴 스탠드", "acrylic"),
    "アクリルキーホルダー": ("아크릴 키링", "keyring"),
    "アクキー": ("아크릴 키링", "keyring"),
    "キーホルダー": ("키링", "keyring"),
    "キーリング": ("키링", "keyring"),
    "키링": ("키링", "keyring"),
    "チャーム": ("키링", "keyring"),
    "ラバーチャーム": ("액세서리", "accessory"),
    "러버": ("액세서리", "accessory"),
    "フィギュア": ("피규어", "figure"),
    "피규어": ("피규어", "figure"),
    "マスコット": ("마스코트", "plush"),
    "마스코트": ("마스코트", "plush"),
    "色紙": ("색지", "stationery"),
    "색지": ("색지", "stationery"),
    "ステッカー": ("스티커", "stationery"),
    "シール": ("스티커", "stationery"),
    "스티커": ("스티커", "stationery"),
    "カード": ("카드/브로마이드", "stationery"),
    "ブロマイド": ("카드/브로마이드", "stationery"),
    "카드": ("카드/브로마이드", "stationery"),
    "브로마이드": ("카드/브로마이드", "stationery"),
    "クリアファイル": ("클리어 파일", "stationery"),
    "클리어파일": ("클리어 파일", "stationery"),
    "食器": ("생활잡화", "daily_goods"),
    "プレート": ("생활잡화", "daily_goods"),
    "グラス": ("생활잡화", "daily_goods"),
    "カップ": ("생활잡화", "daily_goods"),
    "식기": ("생활잡화", "daily_goods"),
    "컵": ("생활잡화", "daily_goods"),
    "머그": ("생활잡화", "daily_goods"),
}

NOISE_MARKERS = {
    "이치방쿠지",
    "一番",
    "一番くじ",
    "치이카와",
    "공식",
    "마켓",
    "사용자",
    "요청",
    "추가",
    "ワンピース",
    "ドラゴンボール",
    "ハイキュー",
    "ガンダム",
    "機動戦士",
    "ラストワン",
    "ジョジョ",
    "ヒーローアカデミア",
    "ハチワレ",
    "하치와레",
    "Fate",
    "UNIVERSAL",
    "CENTURY",
    "SAGA",
}

GENERIC_PRODUCT_WORDS = {"コレクション", "collection", "アソート", "assort"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _catalog_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("items", [])
    return [row for row in rows if isinstance(row, dict)]


def _text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "series_name", "sub_series", "source_store")
        if str(row.get(field) or "").strip()
    )


def _tokens(text: str) -> list[str]:
    found = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[가-힣]{2,}|[ァ-ヴー]{2,}|[一-龯々]{2,}", text)
    return [token for token in found if token.casefold() not in STOPWORDS]


def _split_rule_hint(token: str) -> dict[str, str] | None:
    normalized_token = token.casefold()
    if token in GENERIC_PRODUCT_WORDS or normalized_token in GENERIC_PRODUCT_WORDS:
        return None
    for alias, (target_category, target_family) in PRODUCT_TYPE_ALIASES.items():
        normalized_alias = alias.casefold()
        if normalized_alias in normalized_token or normalized_token in normalized_alias:
            return {
                "suggested_target_category": target_category,
                "suggested_target_family": target_family,
                "suggested_rule_id": "manual_alias_review",
            }
    for rule in split_review.SPLIT_RULES:
        for keyword in rule.get("match_keywords", []):
            normalized_keyword = str(keyword).casefold()
            if not normalized_keyword:
                continue
            if normalized_keyword in normalized_token or normalized_token in normalized_keyword:
                return {
                    "suggested_target_category": str(rule.get("target_category") or ""),
                    "suggested_target_family": str(rule.get("target_family") or ""),
                    "suggested_rule_id": str(rule.get("rule_id") or ""),
                }
    return None


def _candidate_review(token: str) -> dict[str, Any]:
    rule_hint = _split_rule_hint(token)
    if rule_hint:
        return {
            "review_kind": "product_type_like",
            "review_reason": "Matches a known goods type keyword or an existing split-rule target.",
            **rule_hint,
        }
    if token in PRODUCT_TYPE_MARKERS or any(marker in token for marker in PRODUCT_TYPE_MARKERS):
        return {
            "review_kind": "product_type_like",
            "review_reason": "Looks like a goods shape, material, or product format.",
            "suggested_target_category": "",
            "suggested_target_family": "",
            "suggested_rule_id": "marker_review",
        }
    if token in NOISE_MARKERS:
        return {
            "review_kind": "series_or_source_noise",
            "review_reason": "Looks like a series, character, store, campaign, or request-source label.",
        }
    return {
        "review_kind": "ambiguous_review",
        "review_reason": "Needs sample review before it can become a category keyword.",
    }


def _review_score(review: dict[str, Any], row_count: int) -> int:
    kind = str(review.get("review_kind") or "")
    base = {
        "product_type_like": 80,
        "ambiguous_review": 35,
        "series_or_source_noise": 5,
    }.get(kind, 20)
    volume_bonus = min(row_count, 25)
    rule_bonus = 15 if review.get("suggested_rule_id") not in {None, "", "marker_review"} else 0
    return base + volume_bonus + rule_bonus


def _recommended_manual_action(review: dict[str, Any]) -> str:
    kind = str(review.get("review_kind") or "")
    if kind == "product_type_like":
        return "review_samples_then_add_name_level_split_rule_if_consistent"
    if kind == "series_or_source_noise":
        return "keep_as_noise_do_not_promote_to_category_rule"
    return "inspect_samples_before_deciding_product_type_or_noise"


def _review_kind_counts(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(candidate.get("review_kind") or "unknown") for candidate in candidates)
    return [{"review_kind": key, "candidates": value} for key, value in counts.most_common()]


def _sample(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "category": row.get("category"),
        "affiliation": row.get("affiliation"),
        "series_name": row.get("series_name"),
        "sub_series": row.get("sub_series"),
        "source_store": row.get("source_store"),
    }


def _source_rules(split_payload: dict[str, Any]) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {}
    for item in split_payload.get("review_items", []):
        if not isinstance(item, dict):
            continue
        keywords: list[str] = []
        for candidate in item.get("split_candidates", []):
            if isinstance(candidate, dict):
                keywords.extend(str(keyword) for keyword in candidate.get("match_keywords", []) if str(keyword))
        rules[str(item.get("source_category") or "")] = keywords
    return rules


def _is_unmatched(row: dict[str, Any], keywords: list[str]) -> bool:
    value = _text(row).casefold()
    return not any(keyword.casefold() in value for keyword in keywords)


def _ranked_groups(rows: list[dict[str, Any]], field: str, *, limit: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = str(row.get(field) or "").strip() or "(blank)"
        grouped[value].append(row)
    ranked = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:limit]
    return [
        {
            field: value,
            "row_count": len(group_rows),
            "sample_rows": [_sample(row) for row in group_rows[:6]],
        }
        for value, group_rows in ranked
    ]


def _token_candidates(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    token_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seen: set[str] = set()
        for token in _tokens(_text(row)):
            if token in seen:
                continue
            seen.add(token)
            token_rows[token].append(row)
    ranked = sorted(token_rows.items(), key=lambda item: (-len(item[1]), item[0]))[:limit]
    candidates: list[dict[str, Any]] = []
    for token, group_rows in ranked:
        review = _candidate_review(token)
        review_kind = str(review["review_kind"])
        review_score = _review_score(review, len(group_rows))
        candidates.append(
            {
                "token": token,
                "row_count": len(group_rows),
                "review_score": review_score,
                "sample_rows": [_sample(row) for row in group_rows[:6]],
                **review,
                "product_type_hint": review_kind == "product_type_like",
                "manual_confirmed": False,
                "recommended_manual_action": _recommended_manual_action(review),
                "suggested_use": (
                    "review_as_keyword_candidate"
                    if review_kind != "series_or_source_noise"
                    else "do_not_promote_without_stronger_product_type_evidence"
                ),
            }
        )
    candidates.sort(
        key=lambda candidate: (
            -int(candidate.get("review_score") or 0),
            -int(candidate.get("row_count") or 0),
            str(candidate.get("token") or ""),
        )
    )
    return candidates


def build_report(split_payload: dict[str, Any], catalog_payload: dict[str, Any], *, limit: int = 20) -> dict[str, Any]:
    rows = _catalog_rows(catalog_payload)
    rules = _source_rules(split_payload)
    review_items: list[dict[str, Any]] = []
    for source_category, keywords in sorted(rules.items()):
        source_rows = [row for row in rows if str(row.get("category") or "").strip() == source_category]
        unmatched = [row for row in source_rows if _is_unmatched(row, keywords)]
        token_candidates = _token_candidates(unmatched, limit=limit)
        promotable = [
            candidate for candidate in token_candidates if candidate.get("review_kind") == "product_type_like"
        ][:10]
        review_items.append(
            {
                "source_category": source_category,
                "source_category_rows": len(source_rows),
                "unmatched_rows": len(unmatched),
                "current_keyword_count": len(keywords),
                "review_kind_counts": _review_kind_counts(token_candidates),
                "highest_review_score": max(
                    (int(candidate.get("review_score") or 0) for candidate in token_candidates),
                    default=0,
                ),
                "top_token_candidates": token_candidates,
                "promotable_token_candidates": promotable,
                "next_review_action": (
                    "review_promotable_product_type_candidates"
                    if promotable
                    else "collect_more_samples_or_leave_unmatched"
                ),
                "top_series": _ranked_groups(unmatched, "series_name", limit=10),
                "top_sub_series": _ranked_groups(unmatched, "sub_series", limit=10),
                "top_source_stores": _ranked_groups(unmatched, "source_store", limit=10),
                "sample_unmatched_rows": [_sample(row) for row in unmatched[:12]],
                "automation_policy": {
                    "auto_apply_keywords": False,
                    "requires_manual_review": True,
                    "reason": "Unmatched broad categories can mix product types, series names, and store labels.",
                },
            }
        )

    top_product_type_candidates = [
        {
            "source_category": item["source_category"],
            **candidate,
        }
        for item in review_items
        for candidate in item["promotable_token_candidates"]
    ]
    top_product_type_candidates.sort(
        key=lambda candidate: (
            -int(candidate.get("review_score") or 0),
            -int(candidate.get("row_count") or 0),
            str(candidate.get("source_category") or ""),
            str(candidate.get("token") or ""),
        )
    )

    token_candidate_count = sum(len(item["top_token_candidates"]) for item in review_items)
    product_type_candidate_count = len(top_product_type_candidates)
    noise_candidate_count = sum(
        1
        for item in review_items
        for candidate in item["top_token_candidates"]
        if candidate.get("review_kind") == "series_or_source_noise"
    )
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "animation_category_unmatched_keyword_review",
        "summary": {
            "source_categories": len(review_items),
            "source_category_rows": sum(int(item["source_category_rows"]) for item in review_items),
            "unmatched_rows": sum(int(item["unmatched_rows"]) for item in review_items),
            "token_candidate_count": token_candidate_count,
            "product_type_candidate_count": product_type_candidate_count,
            "noise_candidate_count": noise_candidate_count,
            "manual_confirmed_rows": 0,
            "top_product_type_candidate_count": len(top_product_type_candidates[:20]),
            "auto_apply_enabled": False,
        },
        "review_items": review_items,
        "top_product_type_candidates": top_product_type_candidates[:20],
        "instructions": [
            "Use top_token_candidates only as review hints, not as automatic category changes.",
            "Review top_product_type_candidates first; they are the shortest path to reducing broad-category unmatched rows.",
            "Prefer product-type keywords over series, character, or store-only words.",
            "Add a split rule only when sample rows consistently share the same goods type.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-review", type=Path, default=DEFAULT_SPLIT_REVIEW)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    report = build_report(_load(args.split_review), _load(args.catalog), limit=args.limit)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
