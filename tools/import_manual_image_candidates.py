from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
import unicodedata
import urllib.request
from urllib.parse import urlsplit

from image_enrichment_safety import is_safe_source_image_pair, normalized_url

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"

ALLOWED_SOURCE_KINDS = {
    "official_anime",
    "official_manufacturer",
    "official_manufacturer_news",
    "official_manufacturer_page",
    "official_licensed",
    "official_prize_listing",
    "official_prize_page",
    "licensed_retailer",
    "licensed_retailer_exact",
}
CONFIDENCE_LABELS = {"high": 0.9, "medium": 0.75, "low": 0.0}
GENERIC_TITLE_MATCH_TOKENS = {
    "acrylic",
    "badge",
    "collection",
    "figure",
    "goods",
    "keychain",
    "mascot",
    "chibi",
    "nui",
    "plush",
    "premium",
    "stand",
    "trading",
    "ver",
    "vol",
    "volume",
    "\u30a2\u30af\u30ea\u30eb",
    "\u30ad\u30fc\u30db\u30eb\u30c0\u30fc",
    "\u30b0\u30c3\u30ba",
    "\u30b3\u30ec\u30af\u30b7\u30e7\u30f3",
    "\u30b9\u30bf\u30f3\u30c9",
    "\u30c8\u30ec\u30fc\u30c7\u30a3\u30f3\u30b0",
    "\u30d5\u30a3\u30ae\u30e5\u30a2",
    "\u30d7\u30ec\u30df\u30a2\u30e0",
    "\u30de\u30b9\u30b3\u30c3\u30c8",
    "\u3061\u3073\u306c\u3044",
    "\u3061\u3073\u306c\u3044\u307e\u3059\u3053\u3063\u3068",
    "\u306c\u3044\u3050\u308b\u307f",
    "\u30a2\u30af\ub9b4",
    "\uac1c\ubcc4",
    "\uad7f\uc988",
    "\ub2e8\ud488",
    "\ub370\ube44",
    "\ub9c8\uc2a4\ucf54\ud2b8",
    "\uae30\ub150",
    "\ud0a4\ub9c1",
    "\uc0dd\uc77c",
    "\uc8fc\ub144",
    "\ubc84\uc804",
    "\ubc43\uc9c0",
    "\ubd09\uc81c",
    "\uc544\ud06c\ub9b4",
    "\uc2a4\ud0e0\ub4dc",
    "\uc778\ud615",
    "\ud53c\uaddc\uc5b4",
}
STORE_ALLOWED_NETLOCS = {
    "AmiAmi": {"www.amiami.jp"},
    "Banpresto": {"bsp-prize.jp"},
    "Cospa": {"www.cospa.com"},
    "FuRyu": {"furyuprize.com", "www.furyu.jp", "file-origin.charahiroba.com"},
    "Hobby Search": {"www.1999.co.jp"},
    "Movic": {"www.movic.jp"},
    "Re-ment": {"www.re-ment.co.jp"},
    "Stellive Store": {"fanding.kr"},
    "Taito": {"www.taito.co.jp", "taito.co.jp"},
    "\uc560\ub2c8\uba54\uc774\ud2b8": {"www.animate-onlineshop.jp"},
    "\uc5d4\uc2a4\uce74\uc774": {"www.enskyshop.com"},
    "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8": {"www.goodsmile.info", "www.goodsmile.com"},
    "\ub514\uc988\ub2c8 \uc2a4\ud1a0\uc5b4": {"store.disney.co.jp", "shopdisney.disney.co.jp"},
    "\ucf54\ud1a0\ubd80\ud0a4\uc57c": {"shop.kotobukiya.co.jp", "www.kotobukiya.co.jp"},
    "\uce58\uc774\uce74\uc640 \ub9c8\ucf13": {"chiikawamarket.jp"},
    "\uce58\uc774\uce74\uc640 \ubaa8\uad6c\ubaa8\uad6c \ud63c\ud3ec": {"chiikawamogumogu.shop"},
    "\ud3ec\ucf13\ubaac\uc13c\ud130": {"www.pokemoncenter-online.com"},
}


def _is_generic_title_token(token: str) -> bool:
    return token in GENERIC_TITLE_MATCH_TOKENS or bool(
        re.fullmatch(r"(?:20\d{2}|\d+|[\d０-９]+주년|[\d０-９]+周年)", token)
    )


def _tokens(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    # Fold katakana to hiragana so official JP titles and local seed names compare consistently.
    text = "".join(chr(ord(char) - 0x60) if "\u30a1" <= char <= "\u30f6" else char for char in text)
    text = re.sub(r"[\[\]{}()（）<>〈〉《》【】「」『』]", " ", text)
    return {
        token
        for token in re.split(r"[^0-9a-z\u3040-\u309f\u3400-\u9fff\uac00-\ud7a3]+", text)
        if len(token) >= 2
    }


def _candidate_title_matches_row(candidate: dict[str, Any], row: dict[str, Any]) -> bool:
    title = str(candidate.get("candidate_title") or "").strip()
    if not title:
        return True
    title_tokens = _tokens(title)
    row_name_tokens = _tokens(row.get("name_ja")) | _tokens(row.get("name_ko"))
    row_tokens = row_name_tokens | _tokens(row.get("affiliation"))
    if not title_tokens or not row_tokens:
        return True
    row_anniversary_tokens = {
        token for token in row_name_tokens if re.fullmatch(r"[\d０-９]+주년|[\d０-９]+周年", token)
    }
    if row_anniversary_tokens and not row_anniversary_tokens <= title_tokens:
        return False
    shared = title_tokens & row_name_tokens
    distinctive_shared = {
        token
        for token in shared
        if not _is_generic_title_token(token)
    }
    if distinctive_shared:
        return True
    title_text = "".join(title_tokens)
    return any(
        token in title_text
        for token in row_name_tokens
        if len(token) >= 2 and not _is_generic_title_token(token)
    )


def _candidate_row_name_matches_current_seed(candidate: dict[str, Any], row: dict[str, Any]) -> bool:
    candidate_ko = str(candidate.get("name_ko") or "").strip()
    candidate_ja = str(candidate.get("name_ja") or "").strip()
    if not candidate_ko and not candidate_ja:
        return True
    row_ko = str(row.get("name_ko") or "").strip()
    row_ja = str(row.get("name_ja") or "").strip()
    return bool((candidate_ko and candidate_ko == row_ko) or (candidate_ja and candidate_ja == row_ja))


def _live_title_matches_current_seed(live_title: str, row: dict[str, Any]) -> bool:
    title = str(live_title or "").strip()
    if not title:
        return False
    row_ja = str(row.get("name_ja") or "").strip()
    row_ko = str(row.get("name_ko") or "").strip()
    return bool((row_ja and row_ja in title) or (row_ko and row_ko in title))


def _page_title(source_url: str) -> str:
    request = urllib.request.Request(source_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', text, re.I)
    if match:
        return match.group(1).strip()
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if match:
        title = re.sub(r"<[^>]+>", " ", match.group(1))
        return re.sub(r"\s+", " ", title).strip()
    return ""


def _load_items(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    items = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise SystemExit(f"{path} must contain a JSON list or an object with items")
    return [item for item in items if isinstance(item, dict)]


def _confidence_score(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().lower()
    if text in CONFIDENCE_LABELS:
        return CONFIDENCE_LABELS[text]
    try:
        return float(text)
    except ValueError:
        return 0.0


def _valid_row_index(value: Any, row_count: int) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        index = int(value)
    except (TypeError, ValueError):
        return None
    return index if 0 <= index < row_count else None


def _source_netloc_allowed_for_store(row: dict[str, Any], source_url: str, source_kind: str, source_store: str | None = None) -> bool:
    if source_kind in {"official_anime", "official_manufacturer_news", "official_licensed"}:
        return True
    store = str(source_store or row.get("source_store") or "").strip()
    allowed = STORE_ALLOWED_NETLOCS.get(store)
    if not allowed:
        return True
    return urlsplit(source_url).netloc.lower() in allowed


def import_candidates(
    seed_rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    min_confidence: float = 0.75,
    allow_existing_overwrite: bool = False,
    allow_source_store_change: bool = False,
    validate_live_title: bool = False,
    require_live_title_exact: bool = False,
    trust_manual_confirmed_title: bool = False,
    require_manual_confirmed: bool = False,
) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    seen_indexes: set[int] = set()
    for candidate in candidates:
        if require_manual_confirmed and candidate.get("manual_confirmed") is not True:
            skipped.append({"row_index": candidate.get("row_index"), "reason": "manual_confirmed_false"})
            continue
        row_index = _valid_row_index(candidate.get("row_index"), len(seed_rows))
        if row_index is None:
            skipped.append({"row_index": candidate.get("row_index"), "reason": "invalid_row_index"})
            continue
        if row_index in seen_indexes:
            skipped.append({"row_index": row_index, "reason": "duplicate_row_index"})
            continue

        source_kind = str(candidate.get("source_kind") or "").strip()
        if source_kind not in ALLOWED_SOURCE_KINDS:
            skipped.append({"row_index": row_index, "reason": "unsupported_source_kind", "source_kind": source_kind})
            continue
        confidence = _confidence_score(candidate.get("confidence"))
        if confidence < min_confidence:
            skipped.append({"row_index": row_index, "reason": "confidence_below_threshold", "confidence": confidence})
            continue

        source_url = normalized_url(candidate.get("source_url"))
        image_url = normalized_url(candidate.get("image_url"))
        if not is_safe_source_image_pair(source_url, image_url):
            skipped.append(
                {
                    "row_index": row_index,
                    "reason": "unsafe_source_image_pair",
                    "source_url": source_url,
                    "image_url": image_url,
                }
            )
            continue

        row = seed_rows[row_index]
        if not _candidate_row_name_matches_current_seed(candidate, row):
            skipped.append(
                {
                    "row_index": row_index,
                    "reason": "candidate_row_name_mismatch",
                    "candidate_name_ko": candidate.get("name_ko"),
                    "candidate_name_ja": candidate.get("name_ja"),
                    "current_name_ko": row.get("name_ko"),
                    "current_name_ja": row.get("name_ja"),
                }
            )
            continue
        candidate_store = str(candidate.get("source_store") or candidate.get("candidate_source_store") or "").strip()
        if not _source_netloc_allowed_for_store(row, source_url, source_kind, candidate_store or None):
            skipped.append(
                {
                    "row_index": row_index,
                    "reason": "source_netloc_mismatch",
                    "name_ko": row.get("name_ko"),
                    "source_store": candidate_store or row.get("source_store"),
                    "row_source_store": row.get("source_store"),
                    "source_url": source_url,
                }
            )
            continue
        if validate_live_title or require_live_title_exact:
            try:
                live_title = _page_title(source_url)
            except Exception as exc:
                skipped.append(
                    {
                        "row_index": row_index,
                        "reason": "live_title_fetch_failed",
                        "source_url": source_url,
                        "error": str(exc),
                    }
                )
                continue
            if require_live_title_exact and not _live_title_matches_current_seed(live_title, row):
                skipped.append(
                    {
                        "row_index": row_index,
                        "reason": "live_title_exact_mismatch",
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                        "live_title": live_title,
                        "source_url": source_url,
                    }
                )
                continue
            candidate = {**candidate, "candidate_title": candidate.get("candidate_title") or live_title}
        if not (
            trust_manual_confirmed_title
            and candidate.get("manual_confirmed") is True
        ) and not _candidate_title_matches_row(candidate, row):
            skipped.append(
                {
                    "row_index": row_index,
                    "reason": "candidate_title_mismatch",
                    "name_ko": row.get("name_ko"),
                    "candidate_title": candidate.get("candidate_title"),
                }
            )
            continue
        changed_fields: list[str] = []
        if candidate_store and candidate_store != row.get("source_store") and not allow_source_store_change:
            skipped.append({"row_index": row_index, "reason": "source_store_change_not_enabled", "name_ko": row.get("name_ko")})
            continue

        if row.get("image_url") not in (None, "", image_url):
            if not allow_existing_overwrite:
                skipped.append({"row_index": row_index, "reason": "existing_image_url_conflict", "name_ko": row.get("name_ko")})
                continue
        if row.get("source_url") not in (None, "", source_url):
            if not allow_existing_overwrite:
                skipped.append({"row_index": row_index, "reason": "existing_source_url_conflict", "name_ko": row.get("name_ko")})
                continue

        if row.get("image_url") != image_url:
            row["image_url"] = image_url
            changed_fields.append("image_url")
        if row.get("source_url") != source_url:
            row["source_url"] = source_url
            changed_fields.append("source_url")

        if candidate_store and candidate_store != row.get("source_store"):
            row["source_store"] = candidate_store
            changed_fields.append("source_store")

        if not changed_fields:
            seen_indexes.add(row_index)
            skipped.append({"row_index": row_index, "reason": "no_change", "name_ko": row.get("name_ko")})
            continue
        seen_indexes.add(row_index)
        updated.append(
            {
                "row_index": row_index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "changed_fields": changed_fields,
                "source_kind": source_kind,
                "confidence": confidence,
                "source_url": source_url,
                "image_url": image_url,
            }
        )

    return {"seed_rows": seed_rows, "updated": updated, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--allow-existing-overwrite", action="store_true")
    parser.add_argument("--allow-source-store-change", action="store_true")
    parser.add_argument("--validate-live-title", action="store_true")
    parser.add_argument(
        "--require-live-title-exact",
        action="store_true",
        help="Fetch the live product title and require it to contain the current seed row's exact name_ja or name_ko.",
    )
    parser.add_argument(
        "--trust-manual-confirmed-title",
        action="store_true",
        help="Allow manually confirmed candidates to bypass the automatic title-token guard.",
    )
    parser.add_argument(
        "--require-manual-confirmed",
        action="store_true",
        help="Skip every candidate that is not explicitly marked manual_confirmed=true.",
    )
    args = parser.parse_args()

    rows = json.loads(args.seed.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise SystemExit(f"{args.seed} must contain a JSON list")
    candidates = _load_items(args.candidates)
    result = import_candidates(
        rows,
        candidates,
        min_confidence=args.min_confidence,
        allow_existing_overwrite=args.allow_existing_overwrite,
        allow_source_store_change=args.allow_source_store_change,
        validate_live_title=args.validate_live_title,
        require_live_title_exact=args.require_live_title_exact,
        trust_manual_confirmed_title=args.trust_manual_confirmed_title,
        require_manual_confirmed=args.require_manual_confirmed,
    )
    report = {
        "write": args.write,
        "seed": str(args.seed),
        "candidates": str(args.candidates),
        "candidate_rows": len(candidates),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "skipped_reasons": Counter(str(item.get("reason") or "") for item in result["skipped"]).most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and result["updated"]:
        args.seed.write_text(json.dumps(result["seed_rows"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("candidate_rows", "updated_rows", "skipped_rows", "write")}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write after reviewing the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
