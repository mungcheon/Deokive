from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "chiikawa_gotouchi_jp_api_image_report.json"
DEFAULT_SOURCE_URL = "https://www.jp-api.com/contents/NOD62/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

CHIIKAWA_MARKET = "치이카와 마켓"
GOTOCHI = "ご当地"


@dataclass(frozen=True)
class OfficialImage:
    alt: str
    image_url: str


THEME_ALIASES: dict[str, tuple[str, ...]] = {
    "東京タワー": ("도쿄타워", "도쿄 타워", "東京タワー"),
    "スカイツリー": ("스카이트리", "スカイツリー"),
    "鹿": ("나라 사슴", "사슴", "鹿"),
    "富士山": ("후지산", "시즈오카 후지산", "富士山"),
    "伏見稲荷": ("후시미이나리", "伏見稲荷"),
    "舞妓はん": ("마이코", "舞妓"),
    "ラベンダー": ("라벤더", "ラベンダー"),
    "忍者": ("닌자", "忍者"),
    "大阪": ("오사카", "大阪"),
    "たこ焼き": ("타코야키", "たこ焼き"),
    "雷門": ("카미나리몬", "雷門"),
}

TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "ぬいぐるみキーチェーン": ("마스코트", "봉제", "인형", "ぬいぐるみ", "マスコット"),
    "ダイカットキーホルダー": (
        "아크릴 키홀더",
        "아크릴 키링",
        "아크릴키홀더",
        "키홀더",
        "키링",
        "アクリルキーホルダー",
    ),
    "ソックス": ("양말", "삭스", "ソックス"),
    "ポーチ": ("파우치", "ポーチ"),
    "巾着": ("파우치", "긴착", "巾着"),
    "ティッシュケース": ("티슈 케이스", "ティッシュケース"),
}

OFFICIAL_GOODS_TYPES = (
    "\u306c\u3044\u3050\u308b\u307f\u30ad\u30fc\u30c1\u30a7\u30fc\u30f3",
    "\u30c0\u30a4\u30ab\u30c3\u30c8\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
    "\u30ad\u30e3\u30e9\u30c3\u30c8\u30bd\u30c3\u30af\u30b9",
    "\u63a8\u3057\u30ad\u30e3\u30e9\u30bd\u30c3\u30af\u30b9",
    "\u8a18\u5ff5\u30e1\u30c0\u30eb",
    "\u30c6\u30a3\u30c3\u30b7\u30e5\u30b1\u30fc\u30b9",
    "\u30dd\u30fc\u30c1",
    "\u304b\u307e\u53e3",
    "\u304c\u307e\u53e3",
    "\u5dfe\u7740",
    "\u30bd\u30c3\u30af\u30b9",
)

OFFICIAL_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "\u306c\u3044\u3050\u308b\u307f\u30ad\u30fc\u30c1\u30a7\u30fc\u30f3": (
        "\u30de\u30b9\u30b3\u30c3\u30c8",
        "\u306c\u3044\u3050\u308b\u307f",
        "\uc778\ud615",
        "\ub9c8\uc2a4\ucf54\ud2b8",
    ),
    "\u30c0\u30a4\u30ab\u30c3\u30c8\u30ad\u30fc\u30db\u30eb\u30c0\u30fc": (
        "\u30a2\u30af\u30ea\u30eb\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
        "\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
        "\u30a2\u30af\u30ea\u30eb",
        "\uc544\ud06c\ub9b4 \ud0a4\ud640\ub354",
        "\uc544\ud06c\ub9b4 \ud0a4\ub9c1",
        "\ud0a4\ub9c1",
    ),
    "\u30ad\u30e3\u30e9\u30c3\u30c8\u30bd\u30c3\u30af\u30b9": ("\u30bd\u30c3\u30af\u30b9", "\uc591\ub9d0"),
    "\u63a8\u3057\u30ad\u30e3\u30e9\u30bd\u30c3\u30af\u30b9": ("\u30bd\u30c3\u30af\u30b9", "\uc591\ub9d0"),
    "\u5dfe\u7740": ("\u5dfe\u7740", "\ud30c\uc6b0\uce58"),
    "\u30dd\u30fc\u30c1": ("\u30dd\u30fc\u30c1", "\ud30c\uc6b0\uce58"),
    "\u304b\u307e\u53e3": ("\u304c\u307e\u53e3", "\u304b\u307e\u53e3"),
    "\u304c\u307e\u53e3": ("\u304c\u307e\u53e3", "\u304b\u307e\u53e3"),
}

THEME_ALIASES_EXTRA: dict[str, tuple[str, ...]] = {
    "\u305f\u3053\u713c": ("\u305f\u3053\u713c", "\u305f\u3053\u713c\u304d", "\ud0c0\ucf54\uc57c\ud0a4"),
    "\u96f7\u9580": ("\u96f7\u9580", "\uce74\ubbf8\ub098\ub9ac\ubb38"),
    "\u901a\u5929\u95a3": ("\u901a\u5929\u95a3", "\ud1b5\ucc9c\uac01"),
    "\u821e\u5993": ("\u821e\u5993", "\u821e\u5993\u306f\u3093", "\ub9c8\uc774\ucf54"),
    "\u660e\u592a\u5b50": ("\u660e\u592a\u5b50", "\uba58\ud0c0\uc774\ucf54"),
    "\u3055\u3064\u307e\u3044\u3082": ("\u3055\u3064\u307e\u3044\u3082", "\uace0\uad6c\ub9c8"),
    "\u3082\u307f\u3058\u9945\u982d": ("\u3082\u307f\u3058\u9945\u982d", "\ubaa8\ubbf8\uc9c0\ub9cc\uc8fc"),
    "\u4e2d\u83ef\u8857": ("\u4e2d\u83ef\u8857", "\ucc28\uc774\ub098\ud0c0\uc6b4"),
    "\u30dd\u30fc\u30c8\u30bf\u30ef\u30fc": ("\u30dd\u30fc\u30c8\u30bf\u30ef\u30fc", "\ud3ec\ud2b8\ud0c0\uc6cc"),
    "\u30b7\u30fc\u30b5\u30fc": ("\u30b7\u30fc\u30b5\u30fc", "\uc2dc\uc0ac"),
}
AUTO_EXCLUDED_BROAD_THEMES = {"\u5317\u6d77\u9053"}


def _fetch_text(source_url: str) -> str:
    req = urllib.request.Request(source_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
    return raw.decode("cp932", errors="replace")


def _pagination_urls(source_url: str, text: str) -> list[str]:
    urls = [source_url]
    for match in re.finditer(r"href=[\"']([^\"']*/contents/NOD62/PGE\d+/?)", text, re.IGNORECASE):
        url = urllib.parse.urljoin(source_url, html.unescape(match.group(1)))
        if url not in urls:
            urls.append(url)
    return urls


def fetch_official_images(source_url: str) -> list[OfficialImage]:
    first_text = _fetch_text(source_url)
    images: list[OfficialImage] = []
    seen: set[tuple[str, str]] = set()
    for page_url in _pagination_urls(source_url, first_text):
        text = first_text if page_url == source_url else _fetch_text(page_url)
        for tag in re.findall(r"<img\b[^>]*>", text, re.IGNORECASE):
            src_match = re.search(r"src=[\"']([^\"']+)", tag, re.IGNORECASE)
            alt_match = re.search(r"alt=[\"']([^\"']*)", tag, re.IGNORECASE)
            if not src_match or not alt_match:
                continue
            src = urllib.parse.urljoin(page_url, html.unescape(src_match.group(1)))
            alt = html.unescape(alt_match.group(1)).replace("\u3000", " ").strip()
            if "/images/tphoto_" not in src:
                continue
            if alt in {"X", "Instagram", "\u3054\u5f53\u5730 \u3061\u3044\u304b\u308f"}:
                continue
            key = (alt, src)
            if key in seen:
                continue
            seen.add(key)
            images.append(OfficialImage(alt=alt, image_url=src))
    return images


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _official_parts(alt: str) -> tuple[str | None, str | None]:
    normalized = re.sub(r"\s+", " ", alt.replace("\u3000", " ")).strip()
    for goods_type in sorted((*OFFICIAL_GOODS_TYPES, *TYPE_ALIASES), key=len, reverse=True):
        if normalized.endswith(goods_type):
            return normalized[: -len(goods_type)].strip(), goods_type
    for theme in THEME_ALIASES:
        if theme in alt:
            goods_type = next((candidate for candidate in TYPE_ALIASES if candidate in alt), None)
            return theme, goods_type
    return None, None


def _aliases_for_theme(theme: str) -> tuple[str, ...]:
    if theme in AUTO_EXCLUDED_BROAD_THEMES:
        return ()
    return tuple(dict.fromkeys((theme, *THEME_ALIASES.get(theme, ()), *THEME_ALIASES_EXTRA.get(theme, ()))))


def _aliases_for_type(goods_type: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((goods_type, *TYPE_ALIASES.get(goods_type, ()), *OFFICIAL_TYPE_ALIASES.get(goods_type, ()))))


def find_candidate(row: dict[str, Any], official_images: list[OfficialImage]) -> tuple[OfficialImage | None, str]:
    name = str(row.get("name_ko") or "")
    category = str(row.get("category") or "")
    source_store = str(row.get("source_store") or "")
    haystack = " ".join(
        str(row.get(key) or "")
        for key in ("name_ko", "name_ja", "category", "sub_series")
    )
    if row.get("image_url"):
        return None, "image_exists"
    if row.get("source_store") != CHIIKAWA_MARKET and "ご当地ちいかわ" not in source_store:
        return None, "source_store_not_chiikawa_market_or_gotouchi_api"
    if GOTOCHI not in name:
        return None, "not_gotouchi"

    matches: list[OfficialImage] = []
    reasons: list[str] = []
    for image in official_images:
        theme, official_type = _official_parts(image.alt)
        if not theme or not official_type:
            continue
        if not _contains_any(haystack, _aliases_for_theme(theme)):
            continue
        if not _contains_any(haystack, _aliases_for_type(official_type)):
            reasons.append(f"theme_match_type_mismatch:{image.alt}")
            continue
        matches.append(image)

    if len(matches) == 1:
        return matches[0], "matched_official_theme_and_type"
    if len(matches) > 1:
        return None, "multiple_official_matches"
    return None, ";".join(reasons) if reasons else "no_official_theme_type_match"


def load_seed(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)], payload
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], None
    raise SystemExit(f"{path} must contain a JSON list or a public catalog object with an items list")


def enrich(seed_rows: list[dict[str, Any]], official_images: list[OfficialImage], source_url: str) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for index, row in enumerate(seed_rows):
        candidate, reason = find_candidate(row, official_images)
        if candidate is None:
            source_store = str(row.get("source_store") or "")
            if (
                (row.get("source_store") == CHIIKAWA_MARKET or "ご当地ちいかわ" in source_store)
                and GOTOCHI in str(row.get("name_ko") or "")
                and not row.get("image_url")
            ):
                skipped.append(
                    {
                        "row_index": index,
                        "catalog_index": row.get("catalog_index"),
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                        "source_store": row.get("source_store"),
                        "source_url": row.get("source_url"),
                        "reason": reason,
                    }
                )
            continue
        row["image_url"] = candidate.image_url
        if not row.get("source_url"):
            row["source_url"] = source_url
        updated.append(
            {
                "row_index": index,
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_store": row.get("source_store"),
                "category": row.get("category"),
                "image_url": candidate.image_url,
                "source_url": row.get("source_url"),
                "official_alt": candidate.alt,
                "reason": reason,
                "evidence": "multi_character_official_image",
            }
        )
    return {"updated": updated, "skipped": skipped}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_seed(path: Path, rows: list[dict[str, Any]], wrapper: dict[str, Any] | None) -> None:
    if wrapper is not None:
        wrapper["items"] = rows
        write_json(path, wrapper)
        return
    write_json(path, rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    seed_rows, seed_wrapper = load_seed(args.seed)
    official_images = fetch_official_images(args.source_url)
    result = enrich(seed_rows, official_images, args.source_url)
    report = {
        "source_url": args.source_url,
        "official_image_count": len(official_images),
        "updated_count": len(result["updated"]),
        "skipped_count": len(result["skipped"]),
        "write": args.write,
        "updated": result["updated"],
        "skipped": result["skipped"],
    }
    write_json(args.report, report)
    if args.write and result["updated"]:
        write_seed(args.seed, seed_rows, seed_wrapper)

    print(json.dumps({k: report[k] for k in ("source_url", "official_image_count", "updated_count", "skipped_count", "write")}, ensure_ascii=False, indent=2))
    print(f"Report: {args.report}")
    if not args.write:
        print("Dry run only. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
