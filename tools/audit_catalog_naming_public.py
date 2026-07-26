from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_OUTPUT = DATA / "catalog_naming_audit_public.json"

FERN_BAD_KO = "\ud380"
FERN_GOOD_KO = "\ud398\ub978"
FERN_JA = "\u30d5\u30a7\u30eb\u30f3"
FRIEREN_KO = "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c"
ICHIBAN_STORE = "\uc774\uce58\ubc29\ucfe0\uc9c0"
LAST_ONE = "\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde"
DOUBLE_CHANCE = "\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9"
VALID_KUJI_RELEASE_TOKENS = (
    "\u4e00\u756a",
    "\uc774\uce58\ubc29",
    "\u304f\u3058",
    "kuji",
)
VALID_NON_STANDARD_PRIZE_LABEL_TOKENS = (
    "\u3081\u3061\u3083\u3067\u304b\u30b7\u30e7\u30c3\u30d1\u30fc",
    "\u95a2\u9023\u5546\u54c1",
    "\u306c\u3044\u3050\u308b\u307f",
    "\u4ed8\u7b8b",
    "\u7f36\u30d0\u30c3\u30b8",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON list or an object with items")
    return [row for row in rows if isinstance(row, dict)]


def is_ichiban_row(row: dict[str, Any]) -> bool:
    fields = " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "source_store", "source_url", "sub_series")
    ).casefold()
    return ICHIBAN_STORE in fields or "\u4e00\u756a\u304f\u3058" in fields or "1kuji.com" in fields


def compact_row(row: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "reason": reason,
        "catalog_index": row.get("catalog_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "affiliation": row.get("affiliation"),
        "category": row.get("category"),
        "character_name": row.get("character_name"),
        "sub_series": row.get("sub_series"),
        "source_store": row.get("source_store"),
        "official_price_jpy": row.get("official_price_jpy"),
        "source_url": row.get("source_url"),
    }


def is_valid_prize_rank(value: str) -> bool:
    rank = value.strip()
    if not rank:
        return False
    if rank.endswith("\u8cde") or rank.endswith("\u7b49"):
        return True
    if DOUBLE_CHANCE in rank or "\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3" in rank:
        return True
    if "\u30ad\u30e3\u30f3\u30da\u30fc\u30f3" in rank:
        return True
    if "\u304f\u3058" in rank or "kuji" in rank.casefold():
        return True
    if any(token in rank for token in VALID_NON_STANDARD_PRIZE_LABEL_TOKENS):
        return True
    return False


def audit_fern_names(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in rows:
        serialized = json.dumps(row, ensure_ascii=False)
        is_fern_context = (
            FERN_JA in serialized
            or str(row.get("affiliation") or "") == FRIEREN_KO
            or str(row.get("character_name") or "") in {FERN_BAD_KO, FERN_GOOD_KO}
        )
        if is_fern_context and FERN_BAD_KO in serialized:
            issues.append(compact_row(row, reason="fern_korean_name_should_be_peoreun"))
        if FERN_JA in serialized and str(row.get("character_name") or "") not in {"", FERN_GOOD_KO}:
            issues.append(compact_row(row, reason="fern_japanese_name_character_mismatch"))
    return issues


def audit_ichiban_names(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in rows:
        if not is_ichiban_row(row):
            continue
        name = str(row.get("name_ko") or "")
        parts = [part.strip() for part in name.split("/")]
        sub_series = str(row.get("sub_series") or "").strip()
        character_name = str(row.get("character_name") or "").strip()
        price = row.get("official_price_jpy")
        if len(parts) < 4:
            issues.append(compact_row(row, reason="ichiban_name_missing_release_prize_item_character_parts"))
            continue
        release_name = parts[0]
        prize_index = 1
        if sub_series:
            for index, part in enumerate(parts[1:-1], start=1):
                if part == sub_series:
                    prize_index = index
                    break
        prize_rank, character_part = parts[prize_index], parts[-1]
        item_name = " / ".join(parts[prize_index + 1 : -1]).strip()
        release_name_key = release_name.casefold()
        if not any(token in release_name_key for token in VALID_KUJI_RELEASE_TOKENS):
            issues.append(compact_row(row, reason="ichiban_release_name_missing_ichiban_prefix"))
        if not is_valid_prize_rank(prize_rank):
            issues.append(compact_row(row, reason="ichiban_prize_rank_part_missing_sho_suffix"))
        if not item_name:
            issues.append(compact_row(row, reason="ichiban_item_name_part_empty"))
        if character_name and character_part and character_part != character_name:
            issues.append(compact_row(row, reason="ichiban_character_part_mismatch"))
        if sub_series and prize_rank != sub_series:
            issues.append(compact_row(row, reason="ichiban_sub_series_prize_rank_mismatch"))
        if (LAST_ONE in prize_rank or DOUBLE_CHANCE in prize_rank) and price not in (0, None):
            issues.append(compact_row(row, reason="ichiban_last_one_or_double_chance_price_should_be_zero"))
    return issues


def build_report(rows: list[dict[str, Any]], *, generated_at: str | None = None) -> dict[str, Any]:
    fern_issues = audit_fern_names(rows)
    ichiban_issues = audit_ichiban_names(rows)
    ichiban_rows = [row for row in rows if is_ichiban_row(row)]
    issues = fern_issues + ichiban_issues
    by_reason = Counter(issue["reason"] for issue in issues)
    return {
        "generated_at": generated_at or now_utc(),
        "summary": {
            "catalog_rows": len(rows),
            "ichiban_rows": len(ichiban_rows),
            "fern_issue_rows": len(fern_issues),
            "ichiban_issue_rows": len(ichiban_issues),
            "total_issue_rows": len(issues),
            "by_reason": [[reason, count] for reason, count in sorted(by_reason.items())],
            "status": "pass" if not issues else "needs_review",
            "auto_apply_enabled": False,
        },
        "naming_rules": {
            "fern_korean_character_name": FERN_GOOD_KO,
            "ichiban_name_ko_format": "\uc774\uce58\ubc29\ucfe0\uc9c0 \ubc1c\ub9e4\uba85 / ?\u8cde / \uc0c1\ud488\uc774\ub984 / \uce90\ub9ad\ud130\uba85",
            "ichiban_variant_rule": "\uac19\uc740 \uc0c1\uc5d0 \uce90\ub9ad\ud130\uac00 \uc5ec\ub7ec \uba85\uc774\uba74 \uce90\ub9ad\ud130\uba85\ub9cc \ub2e4\ub978 \ubcc4\ub3c4 \ud589\uc73c\ub85c \uc720\uc9c0",
            "ichiban_non_standard_prize_labels": list(VALID_NON_STANDARD_PRIZE_LABEL_TOKENS),
            "ichiban_last_one_double_chance_price_jpy": 0,
        },
        "issues": issues[:200],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_catalog(args.catalog))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.write:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
