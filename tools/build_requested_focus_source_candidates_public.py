from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "requested_focus_next_work_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "requested_focus_source_candidates_public.json"
ANIMATE_STORE = "\uc560\ub2c8\uba54\uc774\ud2b8"
ANIMATE_SEARCH_URL = "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}"
WEB_SEARCH_URL = "https://www.google.com/search?q={query}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _plain(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value))).strip()


def _squash(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", html.unescape(str(value or "")).lower())


def _tokens(value: Any) -> list[str]:
    raw = html.unescape(str(value or ""))
    out: list[str] = []
    for token in re.split(r"[\s()（）・:：/／\\-]+", raw):
        key = _squash(token)
        if len(key) >= 2:
            out.append(key)
    return out


def _search_url(query: str) -> str:
    return ANIMATE_SEARCH_URL.format(query=urllib.parse.quote(query))


def _web_search_url(query: str) -> str:
    return WEB_SEARCH_URL.format(query=urllib.parse.quote(query))


def _fallback_query(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in [
        item.get("name_ja"),
        item.get("name_ko"),
        item.get("category"),
    ]:
        for token in _tokens(value):
            if token not in parts:
                parts.append(token)
            if len(parts) >= 5:
                break
        if len(parts) >= 5:
            break
    return " ".join(parts) or str(item.get("name_ja") or item.get("name_ko") or "").strip()


def _fallback_review_urls(item: dict[str, Any], *, include_secondary: bool = True) -> list[dict[str, Any]]:
    exact_query = str(item.get("name_ja") or item.get("name_ko") or "").strip()
    broad_query = _fallback_query(item)
    urls: list[dict[str, Any]] = []
    if broad_query:
        urls.append(
            {
                "kind": "animate_broad_search",
                "url": _search_url(broad_query),
                "acceptable_for_source_url": False,
                "review_use": "Official Animate search fallback; open matching product pages and use only exact /pn/.../pd/<id>/ product URLs.",
            }
        )
        urls.append(
            {
                "kind": "domain_limited_web_search",
                "url": _web_search_url(f'site:www.animate-onlineshop.jp/pn/ "{broad_query}"'),
                "acceptable_for_source_url": False,
                "review_use": "Find cached/indexed official Animate product pages; only the final official product page can be imported.",
            }
        )
    if exact_query:
        urls.append(
            {
                "kind": "trusted_web_search",
                "url": _web_search_url(f'"{exact_query}" 공식 グッズ'),
                "acceptable_for_source_url": False,
                "review_use": "Look for official manufacturer, licensor, or store product pages when Animate no longer lists the item.",
            }
        )
        if include_secondary:
            urls.append(
                {
                    "kind": "secondary_identity_reference",
                    "url": _web_search_url(f'"{exact_query}" 駿河屋 OR mercari OR らしんばん'),
                    "acceptable_for_source_url": False,
                    "review_use": "Secondary marketplace/reference identity check only; do not import as source_url without official/trusted confirmation.",
                }
            )
    return urls


def _fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://www.animate-onlineshop.jp/",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def parse_animate_search_results(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", text, re.S):
        match = re.search(
            r'<h3>\s*<a[^>]+href=["\']([^"\']*/pn/[^"\']*/pd/\d+/[^"\']*)["\'][^>]*title=["\']([^"\']+)["\']',
            li,
            re.S,
        )
        if not match:
            continue
        href = html.unescape(match.group(1))
        title = _plain(match.group(2))
        source_url = urllib.parse.urljoin("https://www.animate-onlineshop.jp/", href)
        if source_url in seen:
            continue
        seen.add(source_url)
        image_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', li)
        price_match = re.search(r'<p class="price"><font class="notranslate">([^<]+)</font>円', li)
        release_match = re.search(r'<p class="release">発売日：([^<]+)</p>', li)
        media_match = re.search(r'<p class="media">カテゴリ：.*?>([^<]+)</a>', li, re.S)
        candidates.append(
            {
                "source_url": source_url,
                "title": title,
                "image_url": html.unescape(image_match.group(1)) if image_match else "",
                "price_jpy": int(str(price_match.group(1)).replace(",", "")) if price_match else None,
                "release_label": _plain(release_match.group(1)) if release_match else "",
                "animate_category": _plain(media_match.group(1)) if media_match else "",
            }
        )
    return candidates


def _score_candidate(item: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    title_key = _squash(candidate.get("title"))
    required = _tokens(item.get("name_ja") or item.get("name_ko"))
    hits = [token for token in required if token in title_key]
    missing = [token for token in required if token not in title_key]
    score = round(len(hits) / len(required), 4) if required else 0.0
    confidence = "none"
    if required and score == 1:
        confidence = "exact_title_tokens"
    elif len(hits) >= 2 and score >= 0.5:
        confidence = "partial_title_tokens"
    elif hits:
        confidence = "weak_title_tokens"
    return {
        **candidate,
        "match_score": score,
        "matched_tokens": hits,
        "missing_tokens": missing,
        "candidate_confidence": confidence,
    }


def build_report(
    next_work: dict[str, Any],
    *,
    generated_at: str | None = None,
    fetch_live: bool = True,
) -> dict[str, Any]:
    batch = next_work.get("next_batch") if isinstance(next_work.get("next_batch"), dict) else {}
    items = [item for item in batch.get("items") or [] if isinstance(item, dict)]
    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()
    fallback_kind_counts: Counter[str] = Counter()

    for item in items:
        query = str(item.get("name_ja") or item.get("name_ko") or "").strip()
        url = _search_url(query) if query else ""
        candidates: list[dict[str, Any]] = []
        fetch_error = ""
        if fetch_live and url:
            try:
                candidates = [_score_candidate(item, candidate) for candidate in parse_animate_search_results(_fetch(url))]
            except Exception as exc:
                fetch_error = str(exc)
        candidates.sort(key=lambda row: (-float(row.get("match_score") or 0), str(row.get("title") or "")))
        strong = [row for row in candidates if row.get("candidate_confidence") == "exact_title_tokens"]
        status = "exact_candidate_review_required" if len(strong) == 1 else "manual_search_required"
        if fetch_error:
            status = "fetch_error"
        elif not candidates:
            status = "no_official_search_candidates"
        elif len(strong) > 1:
            status = "multiple_exact_candidate_review_required"
        status_counts[status] += 1
        for candidate in candidates:
            candidate_counts[str(candidate.get("candidate_confidence") or "none")] += 1
        fallback_urls = (
            _fallback_review_urls(item)
            if status in {"manual_search_required", "no_official_search_candidates", "fetch_error"}
            else []
        )
        for fallback_url in fallback_urls:
            fallback_kind_counts[str(fallback_url.get("kind") or "unknown")] += 1
        rows.append(
            {
                "catalog_index": item.get("catalog_index"),
                "review_batch_id": item.get("review_batch_id"),
                "source_store": item.get("source_store"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "category": item.get("category"),
                "search_query": query,
                "official_search_url": url,
                "candidate_status": status,
                "fetch_error": fetch_error,
                "candidate_count": len(candidates),
                "exact_title_candidate_count": len(strong),
                "top_candidates": candidates[:5],
                "fallback_review_urls": fallback_urls,
                "fallback_review_policy": {
                    "acceptable_source_url_kinds": [
                        "Official Animate product detail page whose title, character, variant, and goods type exactly match.",
                        "Official manufacturer, licensor, or event/store product detail page when Animate detail is unavailable.",
                    ],
                    "not_acceptable_as_source_url_without_confirmation": [
                        "Search result pages",
                        "Marketplace listings",
                        "Image-only pages",
                        "Pages with matching series but different character, variant, or goods type",
                    ],
                    "manual_confirmation_required": True,
                },
                "confirmed_rows_template_patch": {
                    "manual_confirmed": False,
                    "field": item.get("missing_field"),
                    "row_index": item.get("catalog_index"),
                    "source_store": item.get("source_store"),
                    "name_ko": item.get("name_ko"),
                    "name_ja": item.get("name_ja"),
                    "category": item.get("category"),
                    "manual_value": strong[0]["source_url"] if len(strong) == 1 else "",
                    "evidence_url": strong[0]["source_url"] if len(strong) == 1 else "",
                    "candidate_source_url": strong[0]["source_url"] if len(strong) == 1 else "",
                    "manual_note": "Candidate still requires human exact-product confirmation.",
                    "candidate_status": status,
                    "manual_confirmed_blocked_until": "human_exact_product_confirmation",
                },
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at or _now_utc(),
        "scope": "requested_focus_source_candidates",
        "summary": {
            "source_report": "data/requested_focus_next_work_public.json",
            "review_batch_id": batch.get("batch_id"),
            "source_store": batch.get("source_store"),
            "target_rows": len(items),
            "candidate_rows": len(rows),
            "rows_with_candidates": sum(1 for row in rows if int(row.get("candidate_count") or 0) > 0),
            "single_exact_candidate_rows": sum(
                1 for row in rows if row.get("candidate_status") == "exact_candidate_review_required"
            ),
            "manual_search_required_rows": sum(
                1 for row in rows if row.get("candidate_status") in {"manual_search_required", "no_official_search_candidates"}
            ),
            "fetch_error_rows": sum(1 for row in rows if row.get("candidate_status") == "fetch_error"),
            "fallback_review_rows": sum(1 for row in rows if row.get("fallback_review_urls")),
            "fallback_review_url_rows": sum(len(row.get("fallback_review_urls") or []) for row in rows),
            "status_counts": [[key, value] for key, value in status_counts.most_common()],
            "candidate_confidence_counts": [[key, value] for key, value in candidate_counts.most_common()],
            "fallback_kind_counts": [[key, value] for key, value in fallback_kind_counts.most_common()],
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Use only official animate-onlineshop product pages whose title, character, variant, and goods type match the catalog row.",
            "Do not set manual_confirmed=true from this report automatically; top candidates are review hints.",
            "If candidate_status is no_official_search_candidates, use the official_search_url plus broader trusted sources manually.",
            "fallback_review_urls are review aids only; never paste search-result or marketplace URLs into source_url.",
        ],
        "items": rows,
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_human_exact_product_confirmation": True,
            "allowed_source_store": ANIMATE_STORE,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args()

    report = build_report(_load(args.input), fetch_live=not args.no_fetch)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
