from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit
from urllib.parse import unquote

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_INPUT = DATA / "source_discovery_next_focus_exact_url_review_queue_public.json"
DEFAULT_OUTPUT = DATA / "source_discovery_next_focus_live_source_probe_public.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

PRODUCT_LINK_RE = re.compile(
    r"""<a[^>]+href=["']([^"']*(?:/pn/[^"']*/pd/\d+/?|products/detail\.php\?product_id=\d+)[^"']*)["'][^>]*>(.*?)</a>""",
    re.I | re.S,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _plain(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value))).strip()


def _title_from_source_url(value: str) -> str:
    parsed = urlsplit(value)
    match = re.search(r"/pn/([^/]+)/pd/\d+/?", parsed.path)
    if not match:
        return ""
    return unquote(match.group(1)).strip()


def _key(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", html.unescape(str(value or "")).lower())


def _tokens(value: Any) -> list[str]:
    return [
        token
        for token in (_key(part) for part in re.split(r"[\s()（）・/【】\\[\\]「」『』:：_-]+", str(value or "")))
        if len(token) >= 2
    ]


def _match_score(row: dict[str, Any], title: str) -> dict[str, Any]:
    title_key = _key(title)
    source_tokens: list[str] = []
    for field in ("name_ja", "name_ko", "category"):
        for token in _tokens(row.get(field)):
            if token not in source_tokens:
                source_tokens.append(token)
    matched = [token for token in source_tokens if token in title_key]
    return {
        "matched_tokens": matched,
        "required_token_count": len(source_tokens),
        "matched_token_count": len(matched),
        "score": round(len(matched) / len(source_tokens), 4) if source_tokens else 0,
    }


def _product_source_url(value: str) -> bool:
    parsed = urlsplit(value)
    if not parsed.scheme.startswith("http") or not parsed.netloc:
        return False
    target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return bool(re.search(r"(?:/pn/.+/pd/\d+/?|products/detail\.php\?product_id=\d+)", target))


def extract_candidates(
    page_html: str,
    *,
    base_url: str,
    row: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for href, body in PRODUCT_LINK_RE.findall(page_html):
        source_url = urljoin(base_url, html.unescape(href))
        if not _product_source_url(source_url) or source_url in seen:
            continue
        seen.add(source_url)
        title = _plain(body) or _title_from_source_url(source_url)
        candidate: dict[str, Any] = {
            "source_url": source_url,
            "page_title": title,
        }
        if row is not None:
            candidate["title_match"] = _match_score(row, title)
        candidates.append(candidate)
    return candidates


def _fetch(url: str, *, session: requests.Session) -> tuple[int | None, str, str]:
    response = session.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://www.animate-onlineshop.jp/",
        },
        timeout=25,
    )
    response.raise_for_status()
    return response.status_code, response.url, response.text


def build_report(
    queue: dict[str, Any],
    *,
    fetcher: Callable[[str], tuple[int | None, str, str]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    items = queue.get("items") or []
    out_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        review_url = str(item.get("fallback_store_search_url") or item.get("primary_review_url") or "").strip()
        base = {
            "catalog_index": item.get("catalog_index"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "source_store": item.get("source_store"),
            "category": item.get("category"),
            "review_url": review_url,
            "manual_confirmed": False,
            "auto_apply_enabled": False,
            "source_url_review_guidance": item.get("source_url_review_guidance") or {},
        }
        if not review_url:
            out_items.append({**base, "probe_status": "missing_review_url", "candidates": []})
            continue
        try:
            status, final_url, page = fetcher(review_url)
        except Exception as exc:
            out_items.append(
                {
                    **base,
                    "probe_status": "fetch_failed",
                    "http_status": None,
                    "final_url": "",
                    "error": str(exc),
                    "candidates": [],
                }
            )
            continue
        candidates = extract_candidates(page, base_url=final_url, row=item)
        strong_candidates = [
            candidate
            for candidate in candidates
            if float((candidate.get("title_match") or {}).get("score") or 0) >= 0.75
        ]
        out_items.append(
            {
                **base,
                "probe_status": "detail_candidates_found" if candidates else "no_detail_candidates_on_search_page",
                "http_status": status,
                "final_url": final_url,
                "candidate_count": len(candidates),
                "strong_title_match_candidate_count": len(strong_candidates),
                "candidates": candidates[:10],
                "blocked_until": (
                    "manual_exact_product_identity_confirmation"
                    if candidates
                    else "alternate_exact_source_url_research_required"
                ),
            }
        )

    candidate_rows = [item for item in out_items if item.get("candidate_count")]
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_next_focus_live_source_probe",
        "source_reports": [str(DEFAULT_INPUT.relative_to(ROOT)).replace("\\", "/")],
        "summary": {
            "probed_rows": len(out_items),
            "detail_candidate_rows": len(candidate_rows),
            "detail_candidate_total": sum(int(item.get("candidate_count") or 0) for item in out_items),
            "no_detail_candidate_rows": sum(
                1 for item in out_items if item.get("probe_status") == "no_detail_candidates_on_search_page"
            ),
            "fetch_failed_rows": sum(1 for item in out_items if item.get("probe_status") == "fetch_failed"),
            "auto_apply_enabled": False,
            "recommended_next_action": (
                "manually confirm exact product identity for detail candidate rows; "
                "research alternate exact source URLs for rows with no search-page candidates"
            ),
        },
        "automation_policy": {
            "auto_apply_source_url": False,
            "auto_apply_image_url": False,
            "accepted_source_url_required": True,
            "search_result_urls_are_not_importable": True,
        },
        "items": out_items,
    }


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def write_report(report: dict[str, Any], path: Path = DEFAULT_OUTPUT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    session = requests.Session()

    def fetcher(url: str) -> tuple[int | None, str, str]:
        return _fetch(url, session=session)

    report = build_report(load_json(args.input), fetcher=fetcher)
    if args.write:
        write_report(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to save the public probe report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
