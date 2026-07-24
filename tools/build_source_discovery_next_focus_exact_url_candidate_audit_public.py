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


def unique_detail_links(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    for match in re.finditer(r'href=["\']([^"\']*/products/detail/\d+)', html):
        link = urljoin(base_url, match.group(1))
        if link not in links:
            links.append(link)
    return links


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


def audit_item(item: dict[str, Any], fetcher: Fetcher) -> dict[str, Any]:
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
    result.update(
        {
            "store_search_fetch_status": "ok",
            "http_detail_link_count": len(links),
            "exact_title_detail_link_count": len(exact_links),
            "candidate_source_urls": exact_links[:5],
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


def build_report(
    queue: dict[str, Any],
    *,
    generated_at: str | None = None,
    fetcher: Fetcher = fetch_html,
) -> dict[str, Any]:
    items = [item for item in queue.get("items") or [] if isinstance(item, dict)]
    audited = [audit_item(item, fetcher) for item in items]
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
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json(args.input))
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
