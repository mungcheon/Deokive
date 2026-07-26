from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_REVIEW = DATA / "ichiban_variant_lineup_review_public.json"
DEFAULT_JSON = DATA / "ichiban_variant_lineup_official_probe_public.json"
DEFAULT_MD = DATA / "ichiban_variant_lineup_official_probe_public.md"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
ITEM_BLOCK_RE = re.compile(
    r'<div class="itemColList">(.*?)(?=<div class="itemColList">|</section>)',
    re.IGNORECASE | re.DOTALL,
)
NAME_RE = re.compile(
    r'<h4[^>]+class=["\'][^"\']*\bname\b[^"\']*["\'][^>]*>(.*?)</h4>',
    re.IGNORECASE | re.DOTALL,
)
DETAIL_RE = re.compile(r'<p[^>]+class=["\'][^"\']*\bdetail\b[^"\']*["\'][^>]*>(.*?)</p>', re.IGNORECASE | re.DOTALL)
IMG_RE = re.compile(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
HREF_IMAGE_RE = re.compile(r'<a[^>]+href=["\']([^"\']+\.(?:webp|jpe?g|png)(?:\?[^"\']*)?)["\']', re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
COUNT_RE = re.compile(r"\u5168\s*(\d+)\s*\u7a2e")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _text(value: Any) -> str:
    return str(value or "").strip()


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _plain(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = TAG_RE.sub(" ", text)
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def _first_group(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return _plain(match.group(1)) if match else ""


def _campaign_title(source: str) -> str:
    title = _first_group(TITLE_RE, source)
    return title.split("\uff5c", 1)[0].strip() or title


def _absolute_url(value: str, page_url: str) -> str:
    return urllib.parse.urljoin(page_url if page_url.endswith("/") else f"{page_url}/", html.unescape(value).strip())


def extract_item_blocks(source: str, page_url: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block_match in ITEM_BLOCK_RE.finditer(source):
        block = block_match.group(1)
        name = _first_group(NAME_RE, block)
        detail = _first_group(DETAIL_RE, block)
        images: list[str] = []
        for pattern in (HREF_IMAGE_RE, IMG_RE):
            for match in pattern.finditer(block):
                image_url = _absolute_url(match.group(1), page_url)
                if image_url.startswith(("http://", "https://")) and image_url not in images:
                    images.append(image_url)
        items.append(
            {
                "official_name": name,
                "official_detail": detail,
                "official_images": images,
                "expected_variant_count": _expected_variant_count(detail),
                "choice_policy": _choice_policy(detail),
            }
        )
    return items


def _expected_variant_count(detail: str) -> int | None:
    match = COUNT_RE.search(detail)
    if not match:
        return None
    return int(match.group(1))


def _choice_policy(detail: str) -> str:
    if "\u9078\u3079\u307e\u305b\u3093" in detail:
        return "blind"
    if "\u9078\u3079\u307e\u3059" in detail:
        return "selectable"
    return "unknown"


def _rank_from_official_name(name: str) -> str:
    match = re.match(r"^([^\s\u3000]{1,40}\u8cde)", name)
    return match.group(1) if match else ""


def _strip_rank(name: str) -> str:
    rank = _rank_from_official_name(name)
    return name[len(rank) :].strip() if rank else name.strip()


def _find_official_item(row: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any] | None:
    image_url = _text(row.get("image_url"))
    if image_url:
        for item in items:
            if image_url in item.get("official_images", []):
                return item
    prize_rank = _text(row.get("prize_rank"))
    product_name = _text(row.get("product_name"))
    for item in items:
        official_name = _text(item.get("official_name"))
        if prize_rank and official_name.startswith(prize_rank) and product_name and product_name in official_name:
            return item
    return None


def _candidate(row: dict[str, Any], official_item: dict[str, Any] | None, campaign_title: str, error: str = "") -> dict[str, Any]:
    if official_item is None:
        return {
            "catalog_index": row.get("catalog_index"),
            "status": "official_item_not_matched" if not error else "fetch_failed",
            "error": error,
            "source_url": row.get("source_url"),
            "current_name": row.get("campaign_name"),
            "current_prize_rank": row.get("prize_rank"),
            "current_product_name": row.get("product_name"),
            "current_character_name": row.get("character_name"),
        }

    official_name = _text(official_item.get("official_name"))
    official_rank = _rank_from_official_name(official_name) or _text(row.get("prize_rank"))
    official_product = _strip_rank(official_name)
    expected_count = official_item.get("expected_variant_count")
    choice_policy = _text(official_item.get("choice_policy"))
    action = "keep_single_lineup_row"
    if expected_count and expected_count > 1:
        action = "review_before_variant_split"

    return {
        "catalog_index": row.get("catalog_index"),
        "status": "matched",
        "source_url": row.get("source_url"),
        "campaign_title": campaign_title,
        "official_name": official_name,
        "official_prize_rank": official_rank,
        "official_product_name": official_product,
        "official_detail": official_item.get("official_detail"),
        "official_images": official_item.get("official_images"),
        "expected_variant_count": expected_count,
        "choice_policy": choice_policy,
        "current_prize_rank": row.get("prize_rank"),
        "current_product_name": row.get("product_name"),
        "current_character_name": row.get("character_name"),
        "recommended_action": action,
        "proposed_display_name_ko": f"{campaign_title} / {official_rank} / {official_product} / \uae30\ud0c0",
    }


def build_probe(review: dict[str, Any], *, sleep: float = 0.2) -> dict[str, Any]:
    rows = [row for row in review.get("review_rows") or [] if isinstance(row, dict)]
    by_url: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        url = _text(row.get("source_url"))
        if url:
            by_url.setdefault(url, []).append(row)

    candidates: list[dict[str, Any]] = []
    page_cache: dict[str, dict[str, Any]] = {}
    for index, (url, url_rows) in enumerate(sorted(by_url.items())):
        if index:
            time.sleep(sleep)
        try:
            source = fetch_text(url)
            campaign_title = _campaign_title(source)
            items = extract_item_blocks(source, url)
            page_cache[url] = {"campaign_title": campaign_title, "item_count": len(items)}
            for row in url_rows:
                candidates.append(_candidate(row, _find_official_item(row, items), campaign_title))
        except Exception as error:  # noqa: BLE001 - report network/parser failures without mutating DB.
            page_cache[url] = {"error": f"{type(error).__name__}: {error}"}
            for row in url_rows:
                candidates.append(_candidate(row, None, "", error=f"{type(error).__name__}: {error}"))

    status_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    expected_count_rows = 0
    blind_rows = 0
    for row in candidates:
        status = _text(row.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1
        action = _text(row.get("recommended_action"))
        if action:
            action_counts[action] = action_counts.get(action, 0) + 1
        if row.get("expected_variant_count"):
            expected_count_rows += 1
        if row.get("choice_policy") == "blind":
            blind_rows += 1

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "ichiban_variant_lineup_official_probe",
        "review_rows": len(rows),
        "source_urls": len(by_url),
        "summary": {
            "candidate_rows": len(candidates),
            "status_counts": sorted(status_counts.items(), key=lambda item: (-item[1], item[0])),
            "recommended_action_counts": sorted(action_counts.items(), key=lambda item: (-item[1], item[0])),
            "rows_with_official_expected_variant_count": expected_count_rows,
            "blind_choice_rows": blind_rows,
            "safe_auto_apply_rows": 0,
            "policy": "Official details are evidence for review; variant rows are not created automatically.",
        },
        "pages": page_cache,
        "candidates": sorted(candidates, key=lambda item: int(item.get("catalog_index") or 10**9)),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Ichiban Variant Lineup Official Probe",
        "",
        f"- Candidate rows: `{report['summary']['candidate_rows']}`",
        f"- Rows with official expected variant count: `{report['summary']['rows_with_official_expected_variant_count']}`",
        f"- Blind choice rows: `{report['summary']['blind_choice_rows']}`",
        f"- Safe auto-apply rows: `{report['summary']['safe_auto_apply_rows']}`",
        "",
        "## Status",
        "",
    ]
    for status, count in report["summary"]["status_counts"]:
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Candidates", ""])
    for row in report["candidates"]:
        lines.append(f"### #{row.get('catalog_index')} {row.get('status')}")
        if row.get("official_name"):
            lines.append(f"- Official: {row.get('campaign_title')} / {row.get('official_name')}")
            lines.append(f"- Expected variants: {row.get('expected_variant_count')}")
            lines.append(f"- Choice: {row.get('choice_policy')}")
            lines.append(f"- Action: {row.get('recommended_action')}")
            lines.append(f"- Proposed display: {row.get('proposed_display_name_ko')}")
        else:
            lines.append(f"- Error: {row.get('error')}")
            lines.append(f"- Source: {row.get('source_url')}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    review = load_json(args.review)
    if not isinstance(review, dict):
        raise SystemExit(f"{args.review} must contain a JSON object")
    report = build_probe(review, sleep=args.sleep)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.markdown_output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
