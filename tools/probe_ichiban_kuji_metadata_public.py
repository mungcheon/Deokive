from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
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
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "data" / "ichiban_kuji_metadata_probe_public.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

TEXT_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(?:script|style).*?</(?:script|style)>", re.DOTALL | re.IGNORECASE)
DATE_RE = re.compile(r"(20\d{2})\s*(?:年|[/-])\s*(\d{1,2})\s*(?:月|[/-])\s*(\d{1,2})\s*(?:日)?")
MONTH_RE = re.compile(r"(20\d{2})\s*(?:年|[/-])\s*(\d{1,2})\s*(?:月)?\s*(?:上旬|中旬|下旬)?\s*(?:発売(?:予定)?)?")
PRICE_RE = re.compile(r"(\d{2,3}(?:,\d{3})?)\s*円")
RELEASE_LABEL_RE = re.compile(r"(?:■\s*)?発売日\s*[:：]\s*")
RELEASE_LABELS = ("■発売日", "発売日")
PRICE_LABELS = ("■メーカー希望小売価格", "メーカー希望小売価格", "■価格", "価格")
DOUBLE_CHANCE = "ダブルチャンス"
CAMPAIGN = "キャンペーン"
UNDECIDED = "未定"
NOISY_YEN_CONTEXT = ("円谷プロ", "円玉")


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain an items list")
    return [item for item in items if isinstance(item, dict)]


def _present(value: Any) -> bool:
    return value not in (None, "")


def _group_missing_1kuji_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        url = str(row.get("source_url") or "").strip().rstrip("/")
        if "1kuji.com/products/" not in url:
            continue
        if _present(row.get("release_date")) and _present(row.get("official_price_jpy")):
            continue
        item = grouped.setdefault(
            url,
            {
                "title": row.get("series_name") or row.get("name_ko") or row.get("name_ja"),
                "rows": 0,
                "missing_release_rows": 0,
                "missing_price_rows": 0,
                "sample_catalog_indexes": [],
                "sample_names": [],
            },
        )
        item["rows"] += 1
        if not _present(row.get("release_date")):
            item["missing_release_rows"] += 1
        if not _present(row.get("official_price_jpy")):
            item["missing_price_rows"] += 1
        if len(item["sample_catalog_indexes"]) < 8:
            item["sample_catalog_indexes"].append(row.get("catalog_index"))
            item["sample_names"].append(row.get("name_ko") or row.get("name_ja") or row.get("name_en"))
    return grouped


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _plain_text(source: str) -> str:
    text = SCRIPT_STYLE_RE.sub(" ", source)
    text = TEXT_TAG_RE.sub(" ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _format_date(match: re.Match[str]) -> str:
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def _format_month(match: re.Match[str]) -> str:
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"


def _find_all(text: str, needle: str) -> list[int]:
    indexes: list[int] = []
    start = 0
    while True:
        index = text.find(needle, start)
        if index < 0:
            return indexes
        indexes.append(index)
        start = index + len(needle)


def _all_dates(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in DATE_RE.finditer(text):
        value = _format_date(match)
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _dates_near(text: str, needle: str, radius: int) -> list[str]:
    out: list[str] = []
    for index in _find_all(text, needle):
        out.extend(_all_dates(text[max(0, index - radius) : index + radius]))
    return list(dict.fromkeys(out))


def _first_relevant_snippet(text: str, labels: tuple[str, ...]) -> str | None:
    indexes = [index for label in labels for index in _find_all(text, label)]
    if not indexes:
        return None
    index = min(indexes)
    return text[max(0, index - 80) : index + 180]


def _after_colon(text: str) -> str:
    for separator in (":", "："):
        if separator in text:
            return text.split(separator, 1)[1]
    return text


def _field_value_area(text: str, label_end: int, radius: int = 120) -> str:
    value = text[label_end : label_end + radius]
    if "■" in value:
        value = value.split("■", 1)[0]
    return value.strip()


def _nearby_previous_field_name(text: str, label_start: int, radius: int = 60) -> str:
    before = text[max(0, label_start - radius) : label_start]
    if "■" in before:
        before = before.rsplit("■", 1)[-1]
    return before


def _extract_safe_release_date(text: str) -> dict[str, Any]:
    for label_match in RELEASE_LABEL_RE.finditer(text):
        snippet = text[label_match.start() : label_match.start() + 180]
        previous_field_name = _nearby_previous_field_name(text, label_match.start())
        if DOUBLE_CHANCE in previous_field_name or CAMPAIGN in previous_field_name:
            continue
        value_area = _field_value_area(text, label_match.end())
        if UNDECIDED in value_area[:20]:
            return {"value": None, "reason": "release label says undecided", "snippet": snippet, "ambiguous": True}
        match = DATE_RE.search(value_area)
        if match:
            return {"value": _format_date(match), "reason": "exact date after release-date label", "snippet": snippet, "ambiguous": False}
        month_match = MONTH_RE.search(value_area)
        if month_match:
            return {"value": _format_month(month_match), "reason": "month after release-date label", "snippet": snippet, "ambiguous": False}
    dates = _all_dates(text)
    double_dates = set(_dates_near(text, DOUBLE_CHANCE, 220))
    non_double = [date for date in dates if date not in double_dates]
    return {
        "value": None,
        "reason": "no exact release-date label; unlabeled/double-chance dates are unsafe",
        "snippet": _first_relevant_snippet(text, RELEASE_LABELS + (DOUBLE_CHANCE,)),
        "ambiguous": bool(non_double or double_dates),
    }


def _extract_safe_price(text: str) -> dict[str, Any]:
    for label in PRICE_LABELS:
        for index in _find_all(text, label):
            snippet = text[index : index + 180]
            previous_field_name = _nearby_previous_field_name(text, index)
            if DOUBLE_CHANCE in previous_field_name or CAMPAIGN in previous_field_name:
                continue
            value_area = _field_value_area(_after_colon(snippet), 0)
            if DOUBLE_CHANCE in value_area or CAMPAIGN in value_area:
                value_area = value_area.split(DOUBLE_CHANCE, 1)[0].split(CAMPAIGN, 1)[0]
            match = PRICE_RE.search(value_area)
            if not match:
                continue
            value = int(match.group(1).replace(",", ""))
            if 100 <= value <= 2000:
                return {"value": value, "reason": f"yen amount after {label}", "snippet": snippet, "ambiguous": False}
    return {
        "value": None,
        "reason": "no labeled yen price in expected product-info area",
        "snippet": _first_relevant_snippet(text, PRICE_LABELS),
        "ambiguous": bool(PRICE_RE.search(text)),
    }


def _unsafe_yen_amount_candidates(text: str, limit: int = 5) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for match in PRICE_RE.finditer(text):
        value = int(match.group(1).replace(",", ""))
        if not 100 <= value <= 2000:
            continue
        snippet = text[max(0, match.start() - 90) : match.start() + 140]
        reason = "unlabeled_yen_amount_requires_manual_review"
        if any(noise in snippet for noise in NOISY_YEN_CONTEXT):
            reason = "likely_copyright_or_non_price_yen_noise"
        key = (value, reason)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "value": value,
                "reason": reason,
                "snippet": snippet,
                "manual_review_required": True,
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def build_report(
    rows: list[dict[str, Any]],
    *,
    fetch_text: Any = _fetch_text,
    max_urls: int | None = None,
    sleep_seconds: float = 0.05,
) -> dict[str, Any]:
    grouped = _group_missing_1kuji_rows(rows)
    urls = sorted(grouped)
    if max_urls is not None:
        urls = urls[:max_urls]

    pages: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for index, url in enumerate(urls):
        if index and sleep_seconds:
            time.sleep(sleep_seconds)
        try:
            plain = _plain_text(fetch_text(url))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            failures.append({"url": url, "error": f"{type(error).__name__}: {error}"})
            continue
        release = _extract_safe_release_date(plain)
        price = _extract_safe_price(plain)
        unsafe_price_candidates = _unsafe_yen_amount_candidates(plain)
        all_dates = _all_dates(plain)
        double_dates = _dates_near(plain, DOUBLE_CHANCE, 220)
        group = grouped[url]
        pages.append(
            {
                "url": url,
                "slug": url.rsplit("/", 1)[-1],
                "title": group["title"],
                "rows": group["rows"],
                "missing_release_rows": group["missing_release_rows"],
                "missing_price_rows": group["missing_price_rows"],
                "sample_catalog_indexes": group["sample_catalog_indexes"],
                "sample_names": group["sample_names"],
                "safe_release_date": release.get("value"),
                "safe_release_reason": release.get("reason"),
                "safe_release_snippet": release.get("snippet"),
                "safe_price_jpy": price.get("value"),
                "safe_price_reason": price.get("reason"),
                "safe_price_snippet": price.get("snippet"),
                "unsafe_price_candidates": unsafe_price_candidates,
                "unsafe_price_candidate_count": len(unsafe_price_candidates),
                "all_dates": all_dates[:12],
                "double_chance_dates": double_dates[:12],
                "ambiguous": release.get("ambiguous", False) or price.get("ambiguous", False),
                "auto_apply_enabled": False,
            }
        )

    blocked_reasons = Counter()
    unsafe_price_candidate_reasons = Counter()
    for page in pages:
        if page["missing_release_rows"] and not page["safe_release_date"]:
            blocked_reasons[str(page["safe_release_reason"])] += page["missing_release_rows"]
        if page["missing_price_rows"] and not page["safe_price_jpy"]:
            blocked_reasons[str(page["safe_price_reason"])] += page["missing_price_rows"]
        if page["missing_price_rows"]:
            for candidate in page.get("unsafe_price_candidates") or []:
                unsafe_price_candidate_reasons[str(candidate.get("reason") or "")] += 1

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "ichiban_kuji_missing_metadata_official_page_probe",
        "summary": {
            "urls_with_missing_metadata": len(grouped),
            "audited_urls": len(pages),
            "failure_count": len(failures),
            "rows_missing_release_date": sum(v["missing_release_rows"] for v in grouped.values()),
            "rows_missing_official_price_jpy": sum(v["missing_price_rows"] for v in grouped.values()),
            "safe_release_url_count": sum(1 for p in pages if p["missing_release_rows"] and p["safe_release_date"]),
            "safe_price_url_count": sum(1 for p in pages if p["missing_price_rows"] and p["safe_price_jpy"]),
            "safe_release_row_count": sum(p["missing_release_rows"] for p in pages if p["safe_release_date"]),
            "safe_price_row_count": sum(p["missing_price_rows"] for p in pages if p["safe_price_jpy"]),
            "unsafe_price_candidate_url_count": sum(
                1
                for p in pages
                if p["missing_price_rows"] and p["unsafe_price_candidate_count"]
            ),
            "unsafe_price_candidate_row_count": sum(
                p["missing_price_rows"]
                for p in pages
                if p["unsafe_price_candidate_count"]
            ),
            "ambiguous_page_count": sum(1 for p in pages if p["ambiguous"]),
            "blocked_reasons": blocked_reasons.most_common(),
            "unsafe_price_candidate_reasons": unsafe_price_candidate_reasons.most_common(),
            "auto_apply_enabled": False,
        },
        "pages": pages,
        "failures": failures,
        "instructions": [
            "Only official 1kuji.com campaign pages are probed.",
            "release_date is safe only from a date or month immediately following a product release label such as 発売日.",
            "official_price_jpy is safe only from a labeled yen price in the product-info area.",
            "Unlabeled yen amounts are listed only as unsafe candidates for manual review.",
            "Double-chance and campaign-period dates are explicitly ignored.",
            "This public report never applies catalog changes automatically.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-urls", type=int)
    parser.add_argument("--sleep", type=float, default=0.05)
    args = parser.parse_args()

    report = build_report(_read_catalog(args.catalog), max_urls=args.max_urls, sleep_seconds=args.sleep)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
