from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "fanding_stellive_store_enrichment_report.json"
DEFAULT_CANDIDATE_REPORT = ROOT / "server" / "fanding_stellive_match_queue.json"
DEFAULT_CANDIDATE_CSV = ROOT / "server" / "fanding_stellive_match_queue.csv"
FANDING_LIST_API = "https://fanding.kr/rest/product/list"
FANDING_PRODUCT_API = "https://fanding.kr/rest/product"
FANDING_SHOP_URL = "https://fanding.kr/@stellive/shop"
FANDING_PRODUCT_URL = "https://fanding.kr/@stellive/shop/{product_no}"
STELLIVE_CREATOR_NO = 3142
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
STELLIVE_MEMBER_TOKENS = {
    "강지",
    "칸나",
    "아이리",
    "유니",
    "히나",
    "시라유키",
    "리제",
    "아카네",
    "타비",
    "마시로",
    "네네코",
    "노아",
    "쿠루미",
    "코코나",
    "하나코",
    "린",
    "마유",
    "비비",
    "후야",
}
PRODUCT_TYPE_REQUIREMENTS = (
    (("머그컵",), ("머그컵", "mug")),
    (("아크릴", "스탠드"), ("아크릴 스탠드", "디오라마")),
    (("키링",), ("키링",)),
    (("클리어", "파일"), ("클리어 파일",)),
    (("마스코트", "인형"), ("마스코트", "인형", "봉제")),
    (("봉제", "인형"), ("인형", "봉제", "마스코트")),
    (("토트백",), ("토트백", "백")),
    (("뱃지",), ("뱃지", "배지")),
)

STELLIVE_MEMBER_TOKENS = {
    "강지",
    "칸나",
    "아이리",
    "유니",
    "히나",
    "시라유키",
    "리제",
    "아카네",
    "타비",
    "마시로",
    "네네코",
    "시온",
    "쿠루미",
    "노아",
    "코코나",
    "하나코",
    "린",
    "마유",
    "비비",
    "후야",
    "메로코",
}
PRODUCT_TYPE_REQUIREMENTS = (
    (("머그컵",), ("머그컵", "머그", "mug")),
    (("아크릴", "스탠드"), ("아크릴 스탠드", "아크릴스탠드")),
    (("아크릴", "키링"), ("아크릴 키링", "아크릴키링")),
    (("클리어", "파일"), ("클리어 파일", "클리어파일")),
    (("키링",), ("키링", "키홀더")),
    (("마스코트",), ("마스코트", "인형", "봉제")),
    (("인형",), ("인형", "봉제", "마스코트")),
    (("응원봉",), ("응원봉", "라이트스틱")),
    (("뱃지",), ("뱃지", "배지", "badge")),
    (("토트백",), ("토트백", "백", "가방", "bag")),
    (("굿즈", "박스"), ("굿즈", "박스", "번들", "세트")),
    (("굿즈", "세트"), ("굿즈", "박스", "번들", "세트")),
)


STELLIVE_MEMBER_TOKENS.update(
    {
        "강지",
        "칸나",
        "아이리",
        "아카네",
        "리제",
        "시라유키",
        "히나",
        "네네코",
        "마시로",
        "아라하시",
        "타비",
        "아야츠노",
        "유니",
        "쿠루미",
        "노아",
        "하나코",
        "코코나",
        "비비",
        "린",
        "마유",
        "후야",
        "멜로코",
    }
)

PRODUCT_TYPE_REQUIREMENTS = (
    *PRODUCT_TYPE_REQUIREMENTS,
    (("머그컵",), ("머그컵", "머그", "mug")),
    (("아크릴", "스탠드"), ("아크릴 스탠드", "아크릴스탠드", "디오라마")),
    (("아크릴", "키링"), ("아크릴 키링", "아크릴키링", "키링", "키홀더")),
    (("키링",), ("키링", "키홀더", "keyring")),
    (("클리어", "파일"), ("클리어 파일", "클리어파일")),
    (("마스코트",), ("마스코트", "인형", "봉제")),
    (("봉제", "인형"), ("인형", "봉제", "마스코트")),
    (("응원봉",), ("응원봉", "라이트스틱")),
    (("뱃지",), ("뱃지", "배지", "badge")),
    (("토트백",), ("토트백", "백", "가방", "bag")),
    (("굿즈", "박스"), ("굿즈", "박스", "번들", "세트")),
    (("굿즈", "세트"), ("굿즈", "박스", "번들", "세트")),
)


STELLIVE_MEMBER_TOKENS.update(
    {
        "\uac15\uc9c0",
        "\uc544\uc774\ub9ac",
        "\uce78\ub098",
        "\uc544\uce74\ub124",
        "\ub9ac\uc81c",
        "\uc2dc\ub77c\uc720\ud0a4",
        "\ud788\ub098",
        "\ub124\ub124\ucf54",
        "\ub9c8\uc2dc\ub85c",
        "\uc544\ub77c\ud558\uc2dc",
        "\ud0c0\ube44",
        "\uc544\uc57c\uce20\ub178",
        "\uc720\ub2c8",
        "\ucfe0\ub8e8\ubbf8",
        "\ub178\uc544",
        "\ud558\ub098\ucf54",
        "\ucf54\ucf54\ub098",
        "\ube44\ube44",
        "\ub9b0",
        "\ub9c8\uc720",
        "\ud6c4\uc57c",
        "\uba54\ub85c\ucf54",
    }
)

PRODUCT_TYPE_REQUIREMENTS = (
    *PRODUCT_TYPE_REQUIREMENTS,
    (("\uba38\uadf8\ucef5",), ("\uba38\uadf8\ucef5", "\uba38\uadf8", "mug")),
    (("\uc544\ud06c\ub9b4", "\uc2a4\ud0e0\ub4dc"), ("\uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc", "\uc544\ud06c\ub9b4\uc2a4\ud0e0\ub4dc", "\ub514\uc624\ub77c\ub9c8")),
    (("\uc544\ud06c\ub9b4", "\ud0a4\ub9c1"), ("\uc544\ud06c\ub9b4 \ud0a4\ub9c1", "\uc544\ud06c\ub9b4\ud0a4\ub9c1", "\ud0a4\ub9c1", "keyring")),
    (("\ud0a4\ub9c1",), ("\ud0a4\ub9c1", "keyring")),
    (("\ud074\ub9ac\uc5b4", "\ud30c\uc77c"), ("\ud074\ub9ac\uc5b4 \ud30c\uc77c", "\ud074\ub9ac\uc5b4\ud30c\uc77c")),
    (("\ub9c8\uc2a4\ucf54\ud2b8",), ("\ub9c8\uc2a4\ucf54\ud2b8", "\uc778\ud615", "\ubd09\uc81c")),
    (("\ubd09\uc81c", "\uc778\ud615"), ("\uc778\ud615", "\ubd09\uc81c", "\ub9c8\uc2a4\ucf54\ud2b8")),
    (("\uc778\ud615",), ("\uc778\ud615", "\ubd09\uc81c", "\ub9c8\uc2a4\ucf54\ud2b8")),
    (("\uc751\uc6d0\ubd09",), ("\uc751\uc6d0\ubd09", "\ub77c\uc774\ud2b8\uc2a4\ud2f1")),
    (("\ubc43\uc9c0",), ("\ubc43\uc9c0", "\ubc30\uc9c0", "badge")),
    (("\ubc30\uc9c0",), ("\ubc43\uc9c0", "\ubc30\uc9c0", "badge")),
    (("\ud1a0\ud2b8\ubc31",), ("\ud1a0\ud2b8\ubc31", "\uac00\ubc29", "bag")),
    (("\uad7f\uc988", "\ubc15\uc2a4"), ("\uad7f\uc988", "\ubc15\uc2a4", "\uc138\ud2b8", "\ubc88\ub4e4", "\uc2a4\ud398\uc15c \ubc88\ub4e4")),
    (("\uad7f\uc988", "\uc138\ud2b8"), ("\uad7f\uc988", "\ubc15\uc2a4", "\uc138\ud2b8", "\ubc88\ub4e4", "\uc2a4\ud398\uc15c \ubc88\ub4e4")),
)


EVENT_TOKEN_GROUPS = (
    ("\ub370\ubdd4",),
    ("\uc0dd\uc77c",),
    ("1\uc8fc\ub144", "\uc77c\uc8fc\ub144"),
    ("2\uc8fc\ub144", "\uc774\uc8fc\ub144"),
)


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"\[[^\]]+\]|\([^)]*\)", " ", text)
    text = re.sub(r"[^0-9a-z\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: Any) -> set[str]:
    return {token for token in _norm(value).split() if len(token) > 1 or token.isdigit()}


def _member_tokens(value: Any) -> set[str]:
    normalized = _norm(value)
    return {member for member in STELLIVE_MEMBER_TOKENS if member in normalized}


def _event_tokens(value: Any) -> set[str]:
    normalized = _norm(value)
    return {group[0] for group in EVENT_TOKEN_GROUPS if any(token in normalized for token in group)}


def _event_tokens_compatible(query: Any, title: Any) -> bool:
    query_events = _event_tokens(query)
    title_events = _event_tokens(title)
    if not query_events or not title_events:
        return True
    return query_events <= title_events


def _has_required_product_type(query: Any, title: Any) -> bool:
    query_norm = _norm(query)
    title_norm = _norm(title)
    for query_terms, title_terms in PRODUCT_TYPE_REQUIREMENTS:
        if all(term in query_norm for term in query_terms):
            return any(term in title_norm for term in title_terms)
    return True


def _title(product: dict[str, Any], locale: str = "ko") -> str:
    titles = product.get("aTitle")
    if not isinstance(titles, dict):
        return ""
    return str(titles.get(locale) or titles.get("ko") or titles.get("ja") or titles.get("en") or "").strip()


def _sale_date(product: dict[str, Any]) -> str | None:
    raw = str(product.get("sSaleStartDatetime") or "")
    return raw[:10] if re.match(r"\d{4}-\d{2}-\d{2}", raw) else None


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": FANDING_SHOP_URL,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _fetch_product_detail(product_no: Any) -> dict[str, Any] | None:
    if not product_no:
        return None
    payload = _request_json(FANDING_PRODUCT_API, {"iProductNo": product_no})
    if not payload or payload.get("bIsResult") is not True:
        return None
    data = payload.get("aData")
    return data if isinstance(data, dict) else None


def _image_url(product: dict[str, Any], detail: dict[str, Any] | None) -> str:
    detail_product = detail.get("aProductData") if isinstance(detail, dict) else None
    if isinstance(detail_product, dict):
        images = detail_product.get("aImageList")
        if isinstance(images, list):
            for item in images:
                if isinstance(item, dict) and item.get("sImageUrl"):
                    return str(item.get("sImageUrl") or "").strip()
        if detail_product.get("sThumbnailUrl"):
            return str(detail_product.get("sThumbnailUrl") or "").strip()
    return str(product.get("sThumbnailUrl") or "").strip()


def _product_preview(product: dict[str, Any]) -> dict[str, Any]:
    product_no = product.get("iProductNo")
    return {
        "product_no": product_no,
        "title": _title(product),
        "source_url": FANDING_PRODUCT_URL.format(product_no=product_no) if product_no else None,
        "image_url": str(product.get("sThumbnailUrl") or "").strip() or None,
        "release_date": _sale_date(product),
    }


def _rank_product_candidate(query: str, product: dict[str, Any]) -> dict[str, Any] | None:
    query_tokens = _tokens(query)
    title = _title(product)
    title_tokens = _tokens(title)
    if not query_tokens or not title_tokens:
        return None

    query_members = _member_tokens(query)
    title_members = _member_tokens(title)
    if query_members and title_members and not (query_members & title_members):
        return None
    if query_members and not title_members:
        return None
    if not _event_tokens_compatible(query, title):
        return None
    if not _has_required_product_type(query, title):
        return None

    shared = sorted(query_tokens & title_tokens)
    shared_members = sorted(query_members & title_members)
    for member in shared_members:
        if member not in shared:
            shared.append(member)
    if not shared:
        return None

    query_norm = _norm(query)
    title_norm = _norm(title)
    query_overlap = len(shared) / max(len(query_tokens | query_members), 1)
    title_overlap = len(shared) / max(len(title_tokens | title_members), 1)
    score = query_overlap * 0.72 + title_overlap * 0.28
    if query_norm and title_norm and (query_norm in title_norm or title_norm in query_norm):
        score += 0.18
    if len(shared) >= 3:
        score += 0.06
    preview = _product_preview(product)
    preview.update(
        {
            "score": round(min(score, 1.0), 4),
            "shared_tokens": shared,
            "query_overlap": round(query_overlap, 4),
            "title_overlap": round(title_overlap, 4),
        }
    )
    return preview


def _top_product_candidates(query: str, products: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    ranked = [candidate for product in products if (candidate := _rank_product_candidate(query, product))]
    ranked.sort(key=lambda item: (-float(item["score"]), str(item.get("title") or "")))
    return ranked[:limit]


def _candidate_status(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "no_candidate"
    top_score = float(candidates[0].get("score") or 0)
    runner_up = float(candidates[1].get("score") or 0) if len(candidates) > 1 else 0
    shared_count = len(candidates[0].get("shared_tokens") or [])
    if top_score >= 0.78 and top_score - runner_up >= 0.14 and shared_count >= 2:
        return "strong_manual_review_candidate"
    if top_score >= 0.5:
        return "weak_manual_review_candidate"
    return "low_confidence_candidate"


def _candidate_review_lane(candidate_status: str, top_candidates: list[dict[str, Any]]) -> str:
    if candidate_status == "no_candidate":
        return "manual_search_required"
    if candidate_status == "low_confidence_candidate":
        return "low_confidence_candidate_review"
    if candidate_status == "weak_manual_review_candidate":
        return "weak_candidate_review"
    if candidate_status == "strong_manual_review_candidate":
        return "strong_candidate_manual_confirmation"
    return "manual_review_required"


def _match_diagnostics(query: Any, top_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    query_tokens = sorted(_tokens(query))
    query_members = sorted(_member_tokens(query))
    query_events = sorted(_event_tokens(query))
    top = top_candidates[0] if top_candidates else {}
    return {
        "query_tokens": query_tokens,
        "query_members": query_members,
        "query_events": query_events,
        "top_candidate_title": top.get("title"),
        "top_candidate_score": top.get("score"),
        "top_candidate_shared_tokens": top.get("shared_tokens") or [],
        "top_candidate_query_overlap": top.get("query_overlap"),
        "top_candidate_title_overlap": top.get("title_overlap"),
        "diagnosis": _candidate_diagnosis(query, top_candidates),
    }


def _candidate_diagnosis(query: Any, top_candidates: list[dict[str, Any]]) -> str:
    if not top_candidates:
        members = sorted(_member_tokens(query))
        events = sorted(_event_tokens(query))
        if members and events:
            return "no_product_matched_member_event_and_product_type_filters"
        if members:
            return "no_product_matched_member_and_product_type_filters"
        return "no_product_matched_product_type_filters"
    top = top_candidates[0]
    score = float(top.get("score") or 0)
    shared = top.get("shared_tokens") or []
    if score < 0.5:
        return "candidate_exists_but_score_below_manual_review_threshold"
    if len(shared) < 2:
        return "candidate_has_too_few_shared_identity_tokens"
    return "candidate_requires_exact_identity_confirmation"


def _fallback_search_queries(row: dict[str, Any], name: str) -> list[str]:
    normalized_name = name.strip()
    category = str(row.get("category") or "").strip()
    affiliation = str(row.get("affiliation") or "").strip()
    members = sorted(_member_tokens(normalized_name))
    events = sorted(_event_tokens(normalized_name))
    base_parts = [part for part in [normalized_name, category] if part]
    queries = [
        " ".join(base_parts),
        " ".join(part for part in ["site:fanding.kr/@stellive/shop", normalized_name] if part),
    ]
    if members:
        queries.append(" ".join(part for part in [members[0], category, affiliation] if part))
    if events:
        queries.append(" ".join(part for part in [members[0] if members else "", events[0], category] if part))
    compact: list[str] = []
    seen: set[str] = set()
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        if query and query not in seen:
            compact.append(query)
            seen.add(query)
    return compact[:5]


def _image_basename(value: Any) -> str:
    path = urllib.parse.urlsplit(str(value or "")).path
    return path.rsplit("/", 1)[-1].strip().lower()


def _can_auto_update_existing_image_row(row: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if row.get("source_url") != FANDING_SHOP_URL:
        return False
    if not row.get("image_url"):
        return False
    if not candidate.get("source_url") or not candidate.get("image_url"):
        return False
    if _image_basename(row.get("image_url")) != _image_basename(candidate.get("image_url")):
        return False
    return float(candidate.get("score") or 0) >= 0.9 and len(candidate.get("shared_tokens") or []) >= 3


def _candidate_sort_key(item: dict[str, Any]) -> tuple[int, float, str]:
    priority = {
        "strong_manual_review_candidate": 0,
        "weak_manual_review_candidate": 1,
        "low_confidence_candidate": 2,
        "no_candidate": 3,
    }.get(str(item.get("candidate_status") or ""), 9)
    top_candidates = item.get("top_candidates") if isinstance(item.get("top_candidates"), list) else []
    top_score = float(top_candidates[0].get("score") or 0) if top_candidates else 0.0
    return (priority, -top_score, str(item.get("name_ko") or ""))


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    statuses = sorted({str(item.get("candidate_status") or "") for item in items})
    return {
        status: sum(1 for item in items if item.get("candidate_status") == status)
        for status in statuses
    }


def fetch_products(creator_no: int = STELLIVE_CREATOR_NO) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    products: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    last_product_no: int | None = None
    total: int | None = None

    while True:
        params: dict[str, Any] = {
            "iCreatorNo": creator_no,
            "iLimit": 20,
            "sSortOrder": "recent",
        }
        if last_product_no is not None:
            params["iLastProductNo"] = last_product_no

        payload = _request_json(FANDING_LIST_API, params)
        if not payload or payload.get("bIsResult") is not True:
            errors.append({"params": params, "reason": "api_request_failed", "payload": payload})
            break
        data = payload.get("aData")
        if not isinstance(data, dict):
            errors.append({"params": params, "reason": "api_data_missing"})
            break
        batch = data.get("aProductList")
        if not isinstance(batch, list):
            errors.append({"params": params, "reason": "product_list_missing"})
            break

        total = int(data.get("iTotalCount") or len(products) + len(batch))
        products.extend([item for item in batch if isinstance(item, dict)])
        if len(products) >= total or not batch:
            break
        next_last = batch[-1].get("iProductNo") if isinstance(batch[-1], dict) else None
        try:
            last_product_no = int(next_last)
        except (TypeError, ValueError):
            errors.append({"params": params, "reason": "last_product_no_missing"})
            break
        time.sleep(0.08)

    return products, errors


def enrich(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    products, errors = fetch_products()
    detail_cache: dict[str, dict[str, Any] | None] = {}
    by_title: dict[str, list[dict[str, Any]]] = {}
    for product in products:
        title = _title(product)
        if title:
            by_title.setdefault(_norm(title), []).append(product)

    updated = 0
    changes: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    candidate_queue: list[dict[str, Any]] = []

    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if row.get("source_url") != FANDING_SHOP_URL:
            continue

        name = str(row.get("name_ko") or row.get("name_ja") or "").strip()
        key = _norm(name)
        matches = by_title.get(key, [])
        if len(matches) != 1:
            contains: list[dict[str, Any]] = []
            for product in products:
                product_key = _norm(_title(product))
                if key and product_key and (key in product_key or product_key in key):
                    contains.append({"product_no": product.get("iProductNo"), "title": _title(product)})
            top_candidates = _top_product_candidates(name, products)
            candidate_status = _candidate_status(top_candidates)
            top_candidate = top_candidates[0] if top_candidates else {}
            if candidate_status == "strong_manual_review_candidate" and _can_auto_update_existing_image_row(row, top_candidate):
                changed_fields: list[str] = []
                source_url = str(top_candidate.get("source_url") or "")
                release_date = str(top_candidate.get("release_date") or "")
                if source_url and row.get("source_url") == FANDING_SHOP_URL:
                    row["source_url"] = source_url
                    changed_fields.append("source_url")
                if release_date and not row.get("release_date"):
                    row["release_date"] = release_date
                    changed_fields.append("release_date")
                if changed_fields:
                    updated += 1
                    changes.append(
                        {
                            "catalog_index": row.get("catalog_index"),
                            "row_index": row_index,
                            "name_ko": row.get("name_ko"),
                            "fields": changed_fields,
                            "source_url": row.get("source_url"),
                            "image_url": row.get("image_url"),
                            "release_date": row.get("release_date"),
                            "product_title": top_candidate.get("title"),
                            "automation": "strong_candidate_existing_image_same_file",
                        }
                    )
                    continue
            candidate_item = {
                "row_index": row_index,
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "name_en": row.get("name_en"),
                "category": row.get("category"),
                "affiliation": row.get("affiliation"),
                "source_store": row.get("source_store"),
                "source_url": row.get("source_url"),
                "missing_image_url": not bool(row.get("image_url")),
                "missing_release_date": not bool(row.get("release_date")),
                "reason": "exact_title_match_not_unique",
                "exact_match_count": len(matches),
                "candidate_status": candidate_status,
                "candidate_review_lane": _candidate_review_lane(candidate_status, top_candidates),
                "match_diagnostics": _match_diagnostics(name, top_candidates),
                "fallback_search_queries": _fallback_search_queries(row, name),
                "top_candidates": top_candidates,
            }
            candidate_queue.append(candidate_item)
            rejected.append(
                {
                    "name_ko": row.get("name_ko"),
                    "reason": "exact_title_match_not_unique",
                    "exact_match_count": len(matches),
                    "contains_sample": contains[:5],
                    "candidate_status": candidate_status,
                    "candidate_review_lane": candidate_item["candidate_review_lane"],
                    "match_diagnostics": candidate_item["match_diagnostics"],
                    "fallback_search_queries": candidate_item["fallback_search_queries"],
                    "top_candidates": top_candidates,
                }
            )
            continue

        product = matches[0]
        product_no = product.get("iProductNo")
        detail_key = str(product_no)
        if detail_key not in detail_cache:
            detail_cache[detail_key] = _fetch_product_detail(product_no)
            time.sleep(0.08)
        image_url = _image_url(product, detail_cache[detail_key])
        release_date = _sale_date(product)
        source_url = FANDING_PRODUCT_URL.format(product_no=product_no)
        changed_fields: list[str] = []
        if product_no and row.get("source_url") == FANDING_SHOP_URL:
            row["source_url"] = source_url
            changed_fields.append("source_url")
        if image_url and not row.get("image_url"):
            row["image_url"] = image_url
            changed_fields.append("image_url")
        if release_date and not row.get("release_date"):
            row["release_date"] = release_date
            changed_fields.append("release_date")

        if changed_fields:
            updated += 1
            changes.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "fields": changed_fields,
                    "source_url": row.get("source_url"),
                    "image_url": row.get("image_url"),
                    "release_date": row.get("release_date"),
                    "product_title": _title(product),
                }
            )

    missing_image_candidates = [item for item in candidate_queue if item.get("missing_image_url")]
    review_candidates = [
        item
        for item in candidate_queue
        if item.get("candidate_status") in {"strong_manual_review_candidate", "weak_manual_review_candidate"}
    ]
    missing_image_review_candidates = [
        item for item in review_candidates if item.get("missing_image_url")
    ]
    summary = {
        "api": FANDING_LIST_API,
        "detail_api": FANDING_PRODUCT_API,
        "creator_no": STELLIVE_CREATOR_NO,
        "products_fetched": len(products),
        "api_errors": errors[:10],
        "candidate_rows": len(candidate_queue),
        "review_candidate_rows": len(review_candidates),
        "missing_image_candidate_rows": len(missing_image_candidates),
        "missing_image_review_candidate_rows": len(missing_image_review_candidates),
        "candidate_status_counts": _status_counts(candidate_queue),
        "missing_image_candidate_status_counts": _status_counts(missing_image_candidates),
    }
    candidate_queue.sort(key=_candidate_sort_key)
    return updated, changes, rejected[:200], summary, candidate_queue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--candidate-report", type=Path, default=DEFAULT_CANDIDATE_REPORT)
    parser.add_argument("--candidate-csv", type=Path, default=DEFAULT_CANDIDATE_CSV)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise SystemExit(f"{args.input} must contain a JSON list")

    updated, changes, rejected, summary, candidate_queue = enrich(rows)
    args.report.write_text(
        json.dumps(
            {
                "updated_rows": updated,
                "write": args.write,
                "summary": summary,
                "changes": changes,
                "rejected_sample": rejected,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    args.candidate_report.write_text(
        json.dumps(
            {
                "rows": len(candidate_queue),
                "summary": summary,
                "automation_policy": (
                    "Fuzzy Fanding matches are review-only. Write only exact unique title matches, "
                    "or manually confirm one candidate before attaching source_url/image_url."
                ),
                "queue": candidate_queue,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with args.candidate_csv.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "candidate_status",
                "name_ko",
                "name_ja",
                "category",
                "affiliation",
                "missing_image_url",
                "missing_release_date",
                "top_score",
                "top_title",
                "top_source_url",
                "top_image_url",
                "top_release_date",
                "shared_tokens",
            ],
        )
        writer.writeheader()
        for item in candidate_queue:
            top_candidates = item.get("top_candidates") if isinstance(item.get("top_candidates"), list) else []
            top = top_candidates[0] if top_candidates else {}
            writer.writerow(
                {
                    "candidate_status": item.get("candidate_status"),
                    "name_ko": item.get("name_ko"),
                    "name_ja": item.get("name_ja"),
                    "category": item.get("category"),
                    "affiliation": item.get("affiliation"),
                    "missing_image_url": item.get("missing_image_url"),
                    "missing_release_date": item.get("missing_release_date"),
                    "top_score": top.get("score"),
                    "top_title": top.get("title"),
                    "top_source_url": top.get("source_url"),
                    "top_image_url": top.get("image_url"),
                    "top_release_date": top.get("release_date"),
                    "shared_tokens": " ".join(str(token) for token in top.get("shared_tokens") or []),
                }
            )
    if args.write and changes:
        args.input.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "updated_rows": updated,
                "report": str(args.report),
                "candidate_report": str(args.candidate_report),
                "candidate_csv": str(args.candidate_csv),
                "candidate_rows": len(candidate_queue),
                "write": args.write,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.write:
        print("Dry run only. Re-run with --write to update the seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
