from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_JSON_REPORT = ROOT / "server" / "ichiban_kuji_metadata_audit.json"
DEFAULT_MD_REPORT = ROOT / "server" / "ichiban_kuji_metadata_audit.md"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

TEXT_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(?:script|style).*?</(?:script|style)>", re.DOTALL | re.IGNORECASE)
DATE_RE = re.compile(r"(20\d{2})\s*(?:\u5e74|[/-])\s*(\d{1,2})\s*(?:\u6708|[/-])\s*(\d{1,2})\s*(?:\u65e5)?")
MONTH_RE = re.compile(
    r"(20\d{2})\s*(?:\u5e74|[/-])\s*(\d{1,2})\s*(?:\u6708)?\s*(?:\u4e0a\u65ec|\u4e2d\u65ec|\u4e0b\u65ec)?\s*(?:\u767a\u58f2(?:\u4e88\u5b9a)?)?"
)
PRICE_RE = re.compile(r"(\d{2,3}(?:,\d{3})?)\s*\u5186")

RELEASE_LABELS = (
    "\u25a0\u767a\u58f2\u65e5",  # ■発売日
    "\u767a\u58f2\u65e5",  # 発売日
)
RELEASE_LABEL_RE = re.compile(r"(?:\u25a0\s*)?\u767a\u58f2\u65e5\s*[:\uff1a]\s*")
PRICE_LABELS = (
    "\u25a0\u30e1\u30fc\u30ab\u30fc\u5e0c\u671b\u5c0f\u58f2\u4fa1\u683c",  # ■メーカー希望小売価格
    "\u30e1\u30fc\u30ab\u30fc\u5e0c\u671b\u5c0f\u58f2\u4fa1\u683c",  # メーカー希望小売価格
    "\u25a0\u4fa1\u683c",  # ■価格
    "\u4fa1\u683c",  # 価格
)
DOUBLE_CHANCE = "\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9"
CAMPAIGN = "\u30ad\u30e3\u30f3\u30da\u30fc\u30f3"
UNDECIDED = "\u672a\u5b9a"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--max-urls", type=int, default=None)
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise SystemExit(f"{args.input} must contain a JSON list")

    grouped = _group_missing_1kuji_rows(rows)
    urls = sorted(grouped)
    if args.max_urls:
        urls = urls[: args.max_urls]

    pages: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for index, url in enumerate(urls):
        if index:
            time.sleep(args.sleep)
        try:
            source = _fetch_text(url)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            failures.append({"url": url, "error": f"{type(error).__name__}: {error}"})
            continue
        plain = _plain_text(source)
        release = _extract_safe_release_date(plain)
        price = _extract_safe_price(plain)
        all_dates = _all_dates(plain)
        double_dates = _dates_near(plain, DOUBLE_CHANCE, 220)
        pages.append(
            {
                "url": url,
                "title": grouped[url]["title"],
                "rows": grouped[url]["rows"],
                "missing_release_rows": grouped[url]["missing_release_rows"],
                "missing_price_rows": grouped[url]["missing_price_rows"],
                "safe_release_date": release.get("value"),
                "safe_release_reason": release.get("reason"),
                "safe_release_snippet": release.get("snippet"),
                "safe_price_jpy": price.get("value"),
                "safe_price_reason": price.get("reason"),
                "safe_price_snippet": price.get("snippet"),
                "all_dates": all_dates[:12],
                "double_chance_dates": double_dates[:12],
                "ambiguous": release.get("ambiguous", False) or price.get("ambiguous", False),
            }
        )

    report = {
        "input": str(args.input),
        "urls_with_missing_metadata": len(grouped),
        "audited_urls": len(pages),
        "failures": failures,
        "rows_missing_release_date": sum(v["missing_release_rows"] for v in grouped.values()),
        "rows_missing_official_price_jpy": sum(v["missing_price_rows"] for v in grouped.values()),
        "safe_release_url_count": sum(
            1 for p in pages if p["missing_release_rows"] and p["safe_release_date"]
        ),
        "safe_price_url_count": sum(
            1 for p in pages if p["missing_price_rows"] and p["safe_price_jpy"]
        ),
        "pages": pages,
    }
    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_report.write_text(_markdown_report(report), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "pages"}, ensure_ascii=False, indent=2))
    print(f"Wrote {args.json_report}")
    print(f"Wrote {args.md_report}")
    return 0


def _group_missing_1kuji_rows(rows: list[Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = str(row.get("source_url") or "")
        if "1kuji.com/products/" not in url:
            continue
        if _present(row.get("release_date")) and _present(row.get("official_price_jpy")):
            continue
        item = grouped.setdefault(
            url,
            {
                "title": row.get("series_name") or row.get("name_ko"),
                "rows": 0,
                "missing_release_rows": 0,
                "missing_price_rows": 0,
            },
        )
        item["rows"] += 1
        if not _present(row.get("release_date")):
            item["missing_release_rows"] += 1
        if not _present(row.get("official_price_jpy")):
            item["missing_price_rows"] += 1
    return grouped


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _plain_text(source: str) -> str:
    text = SCRIPT_STYLE_RE.sub(" ", source)
    text = TEXT_TAG_RE.sub(" ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _extract_safe_release_date(text: str) -> dict[str, Any]:
    for label_match in RELEASE_LABEL_RE.finditer(text):
        snippet = text[label_match.start() : label_match.start() + 180]
        if DOUBLE_CHANCE in snippet or CAMPAIGN in snippet:
            continue
        value_area = text[label_match.end() : label_match.end() + 100]
        if UNDECIDED in value_area[:20]:
            return {"value": None, "reason": "release label says undecided", "snippet": snippet, "ambiguous": True}
        match = DATE_RE.search(value_area)
        if match:
            return {
                "value": _format_date(match),
                "reason": "exact date after release-date label",
                "snippet": snippet,
                "ambiguous": False,
            }
        month_match = MONTH_RE.search(value_area)
        if month_match:
            return {
                "value": _format_month(month_match),
                "reason": "month after release-date label",
                "snippet": snippet,
                "ambiguous": False,
            }
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
            if DOUBLE_CHANCE in snippet:
                continue
            value_area = _after_colon(snippet)
            match = PRICE_RE.search(value_area[:90])
            if not match:
                continue
            value = int(match.group(1).replace(",", ""))
            if 100 <= value <= 2000:
                return {
                    "value": value,
                    "reason": f"yen amount after {label}",
                    "snippet": snippet,
                    "ambiguous": False,
                }
    return {
        "value": None,
        "reason": "no labeled yen price in expected product-info area",
        "snippet": _first_relevant_snippet(text, PRICE_LABELS),
        "ambiguous": bool(PRICE_RE.search(text)),
    }


def _after_colon(text: str) -> str:
    for separator in (":", "\uff1a"):
        if separator in text:
            return text.split(separator, 1)[1]
    return text


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


def _first_relevant_snippet(text: str, labels: tuple[str, ...]) -> str | None:
    indexes = [index for label in labels for index in _find_all(text, label)]
    if not indexes:
        return None
    index = min(indexes)
    return text[max(0, index - 80) : index + 180]


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Ichiban Kuji metadata audit",
        "",
        f"- URLs with missing metadata: {report['urls_with_missing_metadata']}",
        f"- Audited URLs: {report['audited_urls']}",
        f"- Rows missing release_date: {report['rows_missing_release_date']}",
        f"- Rows missing official_price_jpy: {report['rows_missing_official_price_jpy']}",
        f"- URLs with safe release_date candidate: {report['safe_release_url_count']}",
        f"- URLs with safe official_price_jpy candidate: {report['safe_price_url_count']}",
        "",
        "## Safe extraction rules",
        "",
        "- release_date is safe only from an exact date immediately following a product release label such as `発売日`.",
        "- Do not parse `発売時期` month-only values into `YYYY-MM-DD`.",
        "- Treat `発売日: 未定` as missing, even if the page has double-chance dates.",
        "- Ignore any date in text containing `ダブルチャンス` or `キャンペーン`, including campaign period and campaign end dates.",
        "- official_price_jpy is safe from a yen amount immediately following `メーカー希望小売価格`, `価格`, or `1回` in the product-info text.",
        "",
        "## Page samples",
        "",
    ]
    for page in report["pages"]:
        if page["safe_release_date"] or page["safe_price_jpy"] or page["double_chance_dates"]:
            lines.extend(
                [
                    f"### {page['url']}",
                    "",
                    f"- title: {page['title']}",
                    f"- missing rows: release_date={page['missing_release_rows']}, official_price_jpy={page['missing_price_rows']}",
                    f"- safe release_date: {page['safe_release_date']} ({page['safe_release_reason']})",
                    f"- safe official_price_jpy: {page['safe_price_jpy']} ({page['safe_price_reason']})",
                    f"- all dates sampled: {', '.join(page['all_dates']) or '(none)'}",
                    f"- double-chance dates: {', '.join(page['double_chance_dates']) or '(none)'}",
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
