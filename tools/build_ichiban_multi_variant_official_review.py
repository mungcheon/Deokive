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
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_CANDIDATES = ROOT / "data" / "ichiban_kuji_multi_variant_review_public.json"
DEFAULT_OUTPUT = ROOT / "data" / "ichiban_kuji_multi_variant_official_public.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

ITEM_BLOCK_RE = re.compile(
    r'<div class="itemColList">(.*?)(?=<div class="itemColList">|</section>)',
    re.IGNORECASE | re.DOTALL,
)
NAME_RE = re.compile(r'<h4 class="name sp">(.*?)</h4>', re.IGNORECASE | re.DOTALL)
FANCYBOX_IMAGE_RE = re.compile(
    r'<a\s+[^>]*data-fancybox[^>]*href=["\']([^"\']+)["\']',
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
COUNT_RE = re.compile(r"全\s*([0-9０-９]+)\s*種")
TIER_RE = re.compile(r"^([A-ZＡ-Ｚ]\d*賞)|^(ラストワン賞)|^(ダブルチャンス)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit-urls", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    rows = catalog["items"]
    review = json.loads(args.candidates.read_text(encoding="utf-8"))
    candidates = review.get("candidates", [])

    candidate_urls = sorted(
        {
            item.get("source_url")
            for item in candidates
            if str(item.get("source_url") or "").startswith("https://1kuji.com/products/")
        }
    )
    if args.limit_urls:
        candidate_urls = candidate_urls[: args.limit_urls]

    existing_by_url_tier = _existing_tier_counts(rows)
    page_results: list[dict[str, Any]] = []
    split_ready: list[dict[str, Any]] = []
    additional_rows_if_numbered_split = 0
    failures: list[dict[str, str]] = []

    for index, url in enumerate(candidate_urls, start=1):
        try:
            blocks = extract_page_blocks(url)
        except Exception as exc:
            failures.append({"source_url": url, "error": str(exc)})
            continue

        campaign_results = []
        for block in blocks:
            tier = _extract_tier(block["name"])
            key = (url, tier)
            existing_count = existing_by_url_tier.get(key, 0)
            is_multi = (block.get("variant_count") or 0) > 1
            has_variant_images = len(block.get("images") or []) > 1
            if not tier or not is_multi or not has_variant_images:
                continue

            record = {
                "source_url": url,
                "tier": tier,
                "official_name": block["name"],
                "official_variant_count": block.get("variant_count"),
                "image_count": len(block["images"]),
                "existing_catalog_rows_for_tier": existing_count,
                "choice_text": block.get("choice_text"),
                "images": block["images"],
                "suggested_action": "split_single_catalog_row_into_numbered_variant_rows"
                if existing_count <= 1
                else "catalog_already_has_multiple_rows_for_tier_review_images_only",
            }
            if existing_count <= 1:
                record["suggested_variant_rows"] = _suggest_variant_rows(record)
                additional_rows_if_numbered_split += max(0, len(record["suggested_variant_rows"]) - existing_count)
            campaign_results.append(record)
            if existing_count <= 1:
                split_ready.append(record)

        if campaign_results:
            page_results.append({"source_url": url, "multi_variant_prizes": campaign_results})

        if args.delay_seconds and index < len(candidate_urls):
            time.sleep(args.delay_seconds)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output = {
        "generated_at": now,
        "scope": "public_catalog_ichiban_kuji",
        "source_candidate_count": len(candidates),
        "checked_source_urls": len(candidate_urls),
        "failed_source_urls": len(failures),
        "pages_with_multi_variant_prizes": len(page_results),
        "split_ready_count": len(split_ready),
        "additional_rows_if_numbered_split": additional_rows_if_numbered_split,
        "note": (
            "Official 1kuji pages were parsed for prize blocks with 全N種 and "
            "multiple gallery images. Rows marked split_single_catalog_row_into_numbered_variant_rows "
            "are grounded enough for a numbered variant expansion, but official variant names are "
            "not always published separately."
        ),
        "split_ready": split_ready,
        "pages": page_results,
        "failures": failures,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "checked_source_urls": len(candidate_urls),
                "failed_source_urls": len(failures),
                "pages_with_multi_variant_prizes": len(page_results),
                "split_ready_count": len(split_ready),
                "additional_rows_if_numbered_split": additional_rows_if_numbered_split,
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def extract_page_blocks(url: str) -> list[dict[str, Any]]:
    source = _fetch_text(url)
    blocks: list[dict[str, Any]] = []
    for match in ITEM_BLOCK_RE.finditer(source):
        block = match.group(1)
        name_match = NAME_RE.search(block)
        if not name_match:
            continue
        name = _plain(name_match.group(1))
        images = []
        for image_match in FANCYBOX_IMAGE_RE.finditer(block):
            image_url = urllib.parse.urljoin(url + "/", html.unescape(image_match.group(1).strip()))
            if image_url.startswith(("http://", "https://")) and image_url not in images:
                images.append(image_url)
        plain = _plain(block)
        variant_count = _extract_variant_count(plain)
        blocks.append(
            {
                "name": name,
                "variant_count": variant_count,
                "choice_text": _extract_choice_text(plain),
                "images": images,
            }
        )
    return blocks


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _plain(value: str) -> str:
    value = html.unescape(TAG_RE.sub(" ", value))
    return re.sub(r"\s+", " ", value).strip()


def _extract_tier(name: str) -> str:
    match = TIER_RE.search(name or "")
    if not match:
        return ""
    return next(group for group in match.groups() if group)


def _extract_variant_count(text: str) -> int | None:
    match = COUNT_RE.search(text or "")
    if not match:
        return None
    return int(match.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789")))


def _extract_choice_text(text: str) -> str | None:
    if "選べない" in text:
        return "選べない"
    if "選べる" in text:
        return "選べる"
    return None


def _existing_tier_counts(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        url = row.get("source_url")
        tier = row.get("sub_series")
        if not isinstance(url, str) or not isinstance(tier, str):
            continue
        if not url.startswith("https://1kuji.com/products/"):
            continue
        counts[(url, tier)] = counts.get((url, tier), 0) + 1
    return counts


def _suggest_variant_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    images = record.get("images") or []
    variant_count = int(record.get("official_variant_count") or 0)
    usable_count = min(len(images), variant_count) if variant_count else len(images)
    if usable_count <= 1:
        return []
    return [
        {
            "name_ja": f'{record["official_name"]}（{index}/{usable_count}）',
            "sub_series": record["tier"],
            "image_url": images[index - 1],
            "source_url": record["source_url"],
            "official_variant_label": f"{index}/{usable_count}",
            "official_variant_count": usable_count,
        }
        for index in range(1, usable_count + 1)
    ]


if __name__ == "__main__":
    main()
