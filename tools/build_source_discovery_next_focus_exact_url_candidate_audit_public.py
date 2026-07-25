from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus, urljoin

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_next_focus_exact_url_review_queue_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_next_focus_exact_url_candidate_audit_public.json"
DEFAULT_ENSKY_CACHE_COVERAGE = DATA / "ensky_missing_image_cache_coverage_public.json"
BROAD_RESULT_LINK_THRESHOLD = 30

Fetcher = Callable[[str], str]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def fetch_html(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def target_title_tokens(value: Any) -> list[str]:
    text = str(value or "")
    tokens = [text]
    tokens.extend(re.findall(r"[（(]([^）)]+)[）)]", text))
    tokens.extend(re.split(r"[\s/・,、【】\[\]（）()]+", text))
    normalized: list[str] = []
    for token in tokens:
        token = normalize_text(token)
        if len(token) >= 3 and token not in normalized:
            normalized.append(token)
    return normalized


def title_match_status(target_title: str, page_title_value: str, page_h1_value: str) -> str:
    haystack = normalize_text(f"{page_title_value} {page_h1_value}")
    if not haystack:
        return "missing_title"
    target = normalize_text(target_title)
    if target and target in haystack:
        return "exact_target_title_in_page_title"
    tokens = target_title_tokens(target_title)
    matched = [token for token in tokens if token in haystack]
    if len(matched) >= 2:
        return "partial_title_token_match"
    return "title_mismatch"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def page_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return clean_text(match.group(1)) if match else ""


def page_h1(html: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    return clean_text(match.group(1)) if match else ""


def unique_detail_links(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    for match in re.finditer(r'href=["\']([^"\']*/products/detail/\d+)', html):
        link = urljoin(base_url, match.group(1))
        if link not in links:
            links.append(link)
    return links


def sample_detail_link_snapshots(
    links: list[str],
    target_title: str,
    fetcher: Fetcher,
    cache: dict[str, dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for link in links[:limit]:
        if link not in cache:
            try:
                html = fetcher(link)
            except Exception as exc:  # pragma: no cover - exercised through integration runs
                cache[link] = {
                    "url": link,
                    "fetch_status": "fetch_error",
                    "fetch_error": type(exc).__name__,
                    "title": "",
                    "h1": "",
                }
            else:
                cache[link] = {
                    "url": link,
                    "fetch_status": "ok",
                    "title": page_title(html),
                    "h1": page_h1(html),
                }
        snapshot = dict(cache[link])
        snapshot["title_match_status"] = title_match_status(
            target_title,
            str(snapshot.get("title") or ""),
            str(snapshot.get("h1") or ""),
        )
        snapshots.append(snapshot)
    return snapshots


def exact_title_detail_links(html: str, base_url: str, title: str) -> list[str]:
    needle = normalize_text(title)
    if not needle:
        return []
    links: list[str] = []
    for match in re.finditer(r'href=["\']([^"\']*/products/detail/\d+)', html):
        start = max(0, match.start() - 600)
        end = min(len(html), match.end() + 1000)
        context = normalize_text(re.sub(r"<[^>]+>", " ", html[start:end]))
        if needle not in context:
            continue
        link = urljoin(base_url, match.group(1))
        if link not in links:
            links.append(link)
    return links


def domain_limited_web_search_url(item: dict[str, Any]) -> str:
    title = str(item.get("name_ja") or item.get("name_ko") or "").strip()
    query = f'site:enskyshop.com/products/detail "{title}"' if title else "site:enskyshop.com/products/detail"
    return f"https://duckduckgo.com/?q={quote_plus(query)}"


def audit_item(
    item: dict[str, Any],
    fetcher: Fetcher,
    detail_snapshot_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    url = str(item.get("fallback_store_search_url") or "")
    title = str(item.get("name_ja") or item.get("name_ko") or "")
    primary_review_url = str(item.get("primary_review_url") or "")
    primary_review_url_kind = str(item.get("primary_review_url_kind") or "")
    base = "https://www.enskyshop.com/"
    result: dict[str, Any] = {
        "catalog_index": item.get("catalog_index"),
        "source_store": item.get("source_store"),
        "category": item.get("category"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "fallback_store_search_url": url,
        "store_search_fetch_status": "not_started",
        "http_detail_link_count": 0,
        "exact_title_detail_link_count": 0,
        "candidate_source_urls": [],
        "broad_result_page": False,
        "auto_apply_enabled": False,
        "manual_review_queue_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "primary_manual_review_url": primary_review_url,
        "primary_manual_review_url_kind": primary_review_url_kind,
        "domain_limited_web_search_url": domain_limited_web_search_url(item),
        "domain_limited_web_search_role": "secondary_search_hint",
        "manual_review_instruction": (
            "Open primary_manual_review_url first when present; use domain_limited_web_search_url only as a secondary "
            "search hint. Never copy broad store search sample links without exact product identity confirmation."
        ),
    }
    if not url:
        result.update(
            {
                "store_search_fetch_status": "missing_url",
                "recommended_next_action": "use_domain_limited_web_search_url",
            }
        )
        return result
    try:
        html = fetcher(url)
    except Exception as exc:  # pragma: no cover - exercised through integration runs
        result.update(
            {
                "store_search_fetch_status": "fetch_error",
                "fetch_error": type(exc).__name__,
                "recommended_next_action": "use_domain_limited_web_search_url",
            }
        )
        return result

    links = unique_detail_links(html, base)
    exact_links = exact_title_detail_links(html, base, title)
    broad = len(links) > BROAD_RESULT_LINK_THRESHOLD
    snapshots = sample_detail_link_snapshots(links, title, fetcher, detail_snapshot_cache)
    snapshot_match_counts = Counter(
        str(snapshot.get("title_match_status") or "unknown") for snapshot in snapshots
    )
    result.update(
        {
            "store_search_fetch_status": "ok",
            "http_detail_link_count": len(links),
            "exact_title_detail_link_count": len(exact_links),
            "candidate_source_urls": exact_links[:5],
            "sample_product_detail_links": links[:5],
            "sample_product_detail_link_count": min(len(links), 5),
            "sample_product_detail_link_snapshots": snapshots,
            "sample_product_detail_link_snapshot_rows": len(snapshots),
            "sample_product_detail_link_snapshot_ok_rows": sum(
                1 for snapshot in snapshots if snapshot.get("fetch_status") == "ok"
            ),
            "sample_product_detail_link_title_match_counts": snapshot_match_counts.most_common(),
            "sample_product_detail_link_title_mismatch_rows": snapshot_match_counts.get(
                "title_mismatch",
                0,
            ),
            "sample_product_detail_link_source": "broad_official_search_result",
            "sample_product_detail_link_warning": (
                "Sample detail links come from the official search result page and are only review starting points; "
                "confirm exact title, character, variant, and product type before using any link as source_url."
            )
            if links
            else "",
            "broad_result_page": broad,
            "recommended_next_action": (
                "review_exact_title_candidate_source_urls"
                if exact_links and not broad
                else "use_domain_limited_web_search_url"
                if broad
                else "manual_exact_source_url_search"
            ),
        }
    )
    return result


def cache_coverage_by_index(cache_coverage: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not isinstance(cache_coverage, dict):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for item in cache_coverage.get("items") or []:
        if not isinstance(item, dict):
            continue
        try:
            catalog_index = int(item.get("catalog_index"))
        except (TypeError, ValueError):
            continue
        out[catalog_index] = item
    return out


def attach_cache_coverage_evidence(
    audited: list[dict[str, Any]],
    cache_coverage: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    by_index = cache_coverage_by_index(cache_coverage)
    if not by_index:
        return audited
    enriched: list[dict[str, Any]] = []
    for item in audited:
        try:
            catalog_index = int(item.get("catalog_index"))
        except (TypeError, ValueError):
            enriched.append(item)
            continue
        cache_item = by_index.get(catalog_index)
        if not cache_item:
            enriched.append(item)
            continue
        candidates = [
            candidate
            for candidate in cache_item.get("candidates") or []
            if isinstance(candidate, dict)
        ]
        enriched.append(
            {
                **item,
                "ensky_cache_coverage": {
                    "status": cache_item.get("status"),
                    "candidate_count": int(cache_item.get("candidate_count") or 0),
                    "safe_exact_match": bool(cache_item.get("safe_exact_match")),
                    "top_candidate_title": (
                        (candidates[0] or {}).get("title") if candidates else None
                    ),
                    "top_candidate_source_url": (
                        (candidates[0] or {}).get("source_url") if candidates else None
                    ),
                    "top_candidate_image_url": (
                        (candidates[0] or {}).get("image_url") if candidates else None
                    ),
                    "evidence_role": "official_sitemap_cache_cross_check",
                },
            }
        )
    return enriched


def build_report(
    queue: dict[str, Any],
    *,
    generated_at: str | None = None,
    fetcher: Fetcher = fetch_html,
    cache_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = [item for item in queue.get("items") or [] if isinstance(item, dict)]
    detail_snapshot_cache: dict[str, dict[str, Any]] = {}
    audited = attach_cache_coverage_evidence(
        [audit_item(item, fetcher, detail_snapshot_cache) for item in items],
        cache_coverage,
    )
    exact_ready = [
        item
        for item in audited
        if item.get("candidate_source_urls") and not item.get("broad_result_page")
    ]
    broad_rows = sum(1 for item in audited if item.get("broad_result_page"))
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_next_focus_exact_url_candidate_audit",
        "source_report": str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "queue_rows": len(items),
            "audited_rows": len(audited),
            "store_search_ok_rows": sum(
                1 for item in audited if item.get("store_search_fetch_status") == "ok"
            ),
            "store_search_broad_result_rows": broad_rows,
            "exact_title_candidate_rows": sum(
                1 for item in audited if item.get("exact_title_detail_link_count")
            ),
            "auto_apply_ready_rows": 0,
            "manual_review_candidate_rows": len(exact_ready),
            "broad_result_link_threshold": BROAD_RESULT_LINK_THRESHOLD,
            "sample_product_detail_link_rows": sum(
                1 for item in audited if item.get("sample_product_detail_links")
            ),
            "sample_product_detail_links": sum(
                len(item.get("sample_product_detail_links") or []) for item in audited
            ),
            "sample_product_detail_link_snapshot_rows": sum(
                len(item.get("sample_product_detail_link_snapshots") or []) for item in audited
            ),
            "unique_sample_product_detail_link_snapshots": len(detail_snapshot_cache),
            "sample_product_detail_link_snapshot_ok_rows": sum(
                sum(
                    1
                    for snapshot in item.get("sample_product_detail_link_snapshots") or []
                    if snapshot.get("fetch_status") == "ok"
                )
                for item in audited
            ),
            "sample_product_detail_link_title_mismatch_rows": sum(
                int(item.get("sample_product_detail_link_title_mismatch_rows") or 0)
                for item in audited
            ),
            "sample_product_detail_link_title_match_counts": Counter(
                str(snapshot.get("title_match_status") or "unknown")
                for item in audited
                for snapshot in item.get("sample_product_detail_link_snapshots") or []
            ).most_common(),
            "broad_result_sample_detail_link_rows": sum(
                1
                for item in audited
                if item.get("broad_result_page") and item.get("sample_product_detail_links")
            ),
            "fallback_to_domain_limited_web_search_rows": sum(
                1
                for item in audited
                if item.get("recommended_next_action") == "use_domain_limited_web_search_url"
            ),
            "primary_manual_review_url_rows": sum(
                1 for item in audited if item.get("primary_manual_review_url")
            ),
            "primary_manual_review_url_kind_counts": Counter(
                str(item.get("primary_manual_review_url_kind") or "")
                for item in audited
                if item.get("primary_manual_review_url")
            ).most_common(),
            "domain_limited_web_search_role_counts": Counter(
                str(item.get("domain_limited_web_search_role") or "")
                for item in audited
                if item.get("domain_limited_web_search_url")
            ).most_common(),
            "ensky_cache_cross_checked_rows": sum(
                1 for item in audited if item.get("ensky_cache_coverage")
            ),
            "ensky_cache_safe_exact_match_rows": sum(
                1
                for item in audited
                if (item.get("ensky_cache_coverage") or {}).get("safe_exact_match")
            ),
            "ensky_cache_broad_candidate_rows": sum(
                1
                for item in audited
                if (item.get("ensky_cache_coverage") or {}).get("status")
                == "broad_cache_candidate"
            ),
            "ensky_cache_no_candidate_rows": sum(
                1
                for item in audited
                if (item.get("ensky_cache_coverage") or {}).get("status")
                == "no_cache_candidate"
            ),
            "ensky_cache_status_counts": Counter(
                str((item.get("ensky_cache_coverage") or {}).get("status") or "")
                for item in audited
                if item.get("ensky_cache_coverage")
            ).most_common(),
            "auto_apply_enabled": False,
            "recommended_next_action": "Use exact title candidates only after manual review; broad Ensky search result pages are not source_url evidence.",
        },
        "automation_policy": {
            "auto_apply_source_url": False,
            "requires_manual_review": True,
            "accepted_candidate_condition": "exact_title_detail_link_count > 0 and broad_result_page is false",
        },
        "items": audited,
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ensky-cache-coverage", type=Path, default=DEFAULT_ENSKY_CACHE_COVERAGE)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    cache_coverage = (
        load_json(args.ensky_cache_coverage)
        if args.ensky_cache_coverage.exists()
        else None
    )
    report = build_report(load_json(args.input), cache_coverage=cache_coverage)
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
