from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "server" / "catalog_character_name_policy_report.json"

ICHIBAN_PREFIX = "\u4e00\u756a\u304f\u3058"
LAST_ONE_LABEL = "\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde"
DOUBLE_CHANCE_LABELS = ("\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9", "W\u30c1\u30e3\u30f3\u30b9")
ICHIBAN_PRIZE_LABEL_SUFFIXES = (
    "\u8cde",
    "\u7b49",
    "\u30ad\u30e3\u30f3\u30da\u30fc\u30f3",
    "\u95a2\u9023\u5546\u54c1",
)
ICHIBAN_PRIZE_LABEL_EXACT = {
    "\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9",
    "\u306c\u3044\u3050\u308b\u307f",
    "\u4ed8\u7b8b",
    "\u3081\u3061\u3083\u3067\u304b\u30b7\u30e7\u30c3\u30d1\u30fc",
}

CHARACTER_MOJIBAKE_OR_ALIAS_FINDINGS = {
    "\ud380": {
        "expected": "\ud398\ub978",
        "fields": ("character_name", "affiliation", "name_ko"),
        "reason": "likely_korean_frieren_character_typo",
        "affiliation_scope": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
        "match": "contains",
    },
    "\ud38c": {
        "expected": "\ud398\ub978",
        "fields": ("character_name", "affiliation", "name_ko"),
        "reason": "likely_korean_frieren_character_typo",
        "affiliation_scope": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
        "match": "contains",
    },
    "\ud504\ub80c": {
        "expected": "\ud398\ub978",
        "fields": ("character_name", "affiliation", "name_ko"),
        "reason": "likely_korean_frieren_character_typo",
        "affiliation_scope": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
        "match": "contains",
    },
    "Pern": {
        "expected": "\ud398\ub978",
        "fields": ("character_name", "name_ko"),
        "reason": "likely_romanized_frieren_character_alias_in_korean_fields",
        "affiliation_scope": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
        "match": "contains",
    },
    "Fern": {
        "expected": "\ud398\ub978",
        "fields": ("character_name", "name_ko"),
        "reason": "likely_romanized_frieren_character_alias_in_korean_fields",
        "affiliation_scope": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
        "match": "contains",
    },
    "\ud6c4\ub9ac\ub80c": {
        "expected": "\ud504\ub9ac\ub80c",
        "fields": ("character_name", "affiliation", "name_ko"),
        "reason": "likely_korean_frieren_title_or_character_typo",
        "affiliation_scope": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
        "match": "contains",
    },
    "\ud504\ub9ac\ub79c": {
        "expected": "\ud504\ub9ac\ub80c",
        "fields": ("character_name", "affiliation", "name_ko"),
        "reason": "likely_korean_frieren_title_or_character_typo",
        "affiliation_scope": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
        "match": "contains",
    },
    "\uccb4\uc778\uc18c \ub9e8": {
        "expected": "\uccb4\uc778\uc18c\ub9e8",
        "fields": ("affiliation",),
        "reason": "korean_affiliation_spacing_alias",
        "match": "exact",
    },
    "\uac11\uc637 \uc528": {
        "expected": "\uac11\uc637\uc528",
        "fields": ("character_name",),
        "reason": "korean_character_spacing_alias",
        "match": "exact",
    },
    "\uc5d0\ub178\uc2dc\ub9c8 \uc970\ucf54": {
        "expected": "\uc5d0\ub178\uc2dc\ub9c8 \uc900\ucf54",
        "fields": ("character_name", "name_ko"),
        "reason": "likely_korean_danganronpa_character_typo",
        "affiliation_scope": "\ub2e8\uac04\ub860\ud30c",
        "match": "contains",
    },
}

CHARACTER_ALIAS_MONITOR_TARGETS = {
    "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c": {
        "canonical_characters": (
            "\ud504\ub9ac\ub80c",
            "\ud398\ub978",
            "\uc288\ud0c0\ub974\ud06c",
            "\ud788\uba5c",
            "\uc544\uc774\uc820",
            "\ud558\uc774\ud130",
            "\ud63c\ud569",
            "\uae30\ud0c0",
        ),
        "watched_aliases": {
            "\ud380": "\ud398\ub978",
            "\ud38c": "\ud398\ub978",
            "\ud504\ub80c": "\ud398\ub978",
            "Pern": "\ud398\ub978",
            "Fern": "\ud398\ub978",
            "\ud6c4\ub9ac\ub80c": "\ud504\ub9ac\ub80c",
            "\ud504\ub9ac\ub79c": "\ud504\ub9ac\ub80c",
        },
    },
    "\ub2e8\uac04\ub860\ud30c": {
        "canonical_characters": (
            "\ub098\uc5d0\uae30 \ub9c8\ucf54\ud1a0",
            "\ud0a4\ub9ac\uae30\ub9ac \ucfc4\ucf54",
            "\uc5d0\ub178\uc2dc\ub9c8 \uc900\ucf54",
            "\ud1a0\uac00\ubbf8 \ubc4c\ucfe0\uc57c",
            "\uc774\uc2dc\ub9c8\ub8e8 \ud0a4\uc694\ud0c0\uce74",
            "\ud788\ub098\ud0c0 \ud558\uc9c0\uba54",
            "\ucf54\ub9c8\uc5d0\ub2e4 \ub098\uae30\ud1a0",
            "\ub098\ub098\ubbf8 \uce58\uc544\ud0a4",
            "\uc0ac\uc774\uc628\uc9c0 \ud788\uc694\ucf54",
            "\uce20\ubbf8\ud0a4 \ubbf8\uce78",
            "\uc0ac\uc774\ud558\ub77c \uc288\uc774\uce58",
            "\uc624\uc6b0\ub9c8 \ucf54\ud0a4\uce58",
            "\uc544\uce74\ub9c8\uce20 \uce74\uc5d0\ub370",
            "\ubaa8\ubaa8\ud0c0 \uce74\uc774\ud1a0",
            "\uc544\ub9c8\ubbf8 \ub780\ud0c0\ub85c",
            "\uc774\ub8e8\ub9c8 \ubbf8\uc6b0",
            "\ubaa8\ub178\ucfe0\ub9c8",
            "\ud63c\ud569",
            "\uae30\ud0c0",
        ),
        "watched_aliases": {
            "\uc5d0\ub178\uc2dc\ub9c8 \uc970\ucf54": "\uc5d0\ub178\uc2dc\ub9c8 \uc900\ucf54",
        },
    }
}

ICHIBAN_PRODUCT_CHARACTER_TOKENS = (
    ("\u30c1\u30e7\u30c3\u30d1\u30fc", "\ud1a0\ub2c8\ud1a0\ub2c8 \ucd78\ud30c"),
    ("\u30cf\u30f3\u30b3\u30c3\u30af", "\ubcf4\uc544 \ud578\ucf55"),
    ("\u30da\u30ed\u30fc\u30ca", "\ud398\ub85c\ub098"),
    ("\u3057\u3089\u307b\u3057", "\uc2dc\ub77c\ud638\uc2dc"),
    ("\u30d5\u30ea\u30fc\u30ec\u30f3", "\ud504\ub9ac\ub80c"),
    ("\u30b7\u30e5\u30bf\u30eb\u30af", "\uc288\ud0c0\ub974\ud06c"),
    ("\u30d5\u30a7\u30eb\u30f3", "\ud398\ub978"),
    ("\u30d2\u30f3\u30e1\u30eb", "\ud788\uba5c"),
    ("\u30eb\u30d5\u30a3", "\ubabd\ud0a4 D. \ub8e8\ud53c"),
    ("\u30ed\u30d3\u30f3", "\ub2c8\ucf54 \ub85c\ube48"),
    ("\u30a6\u30bd\u30c3\u30d7", "\uc6b0\uc19d"),
    ("\u30b5\u30f3\u30b8", "\uc0c1\ub514"),
    ("\u30be\u30ed", "\ub864\ub85c\ub178\uc544 \uc870\ub85c"),
    ("\u30ca\u30df", "\ub098\ubbf8"),
    ("\u30ed\u30fc", "\ud2b8\ub77c\ud314\uac00 \ub85c"),
    ("\u70ad\u6cbb\u90ce", "\uce74\ub9c8\ub3c4 \ud0c4\uc9c0\ub85c"),
    ("\u79b0\u8c46\u5b50", "\uce74\ub9c8\ub3c4 \ub124\uc988\ucf54"),
    ("\u5584\u9038", "\uc544\uac00\uce20\ub9c8 \uc820\uc774\uce20"),
    ("\u4f0a\u4e4b\u52a9", "\ud558\uc2dc\ube44\ub77c \uc774\ub178\uc2a4\ucf00"),
    ("\u7149\u7344", "\ub80c\uace0\ucfe0 \ucfc4\uc96c\ub85c"),
    ("\u30b4\u30c6\u30f3\u30af\u30b9", "\uc624\ucc9c\ud06c\uc2a4"),
    ("\u30d9\u30b8\u30c3\u30c8", "\ubca0\uc9c0\ud2b8"),
    ("\u30c8\u30e9\u30f3\u30af\u30b9", "\ud2b8\ub7ad\ud06c\uc2a4"),
    ("\u30d9\u30b8\u30fc\u30bf", "\ubca0\uc9c0\ud130"),
    ("\u609f\u98ef", "\uc190\uc624\ubc18"),
    ("\u609f\u7a7a", "\uc190\uc624\uacf5"),
)

ICHIBAN_COMBINED_PRODUCT_MARKERS = ("&", "\uff06", "\u00d7", "VS", "vs", "\u30fb")

KATAKANA = set("".join(chr(codepoint) for codepoint in range(0x30A0, 0x30FF + 1)))


def product_token_matches(product_name: str, japanese_token: str) -> bool:
    start = 0
    token_is_katakana = any(char in KATAKANA for char in japanese_token)
    while True:
        index = product_name.find(japanese_token, start)
        if index < 0:
            return False
        before = product_name[index - 1] if index > 0 else ""
        if token_is_katakana and before in KATAKANA:
            start = index + 1
            continue
        return True


def load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        rows = payload.get("items")
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain an item list or an items array")
    return [row for row in rows if isinstance(row, dict)]


def is_ichiban_row(row: dict[str, Any]) -> bool:
    return str(row.get("series_name") or "").startswith(ICHIBAN_PREFIX) or ICHIBAN_PREFIX in str(
        row.get("name_ko") or ""
    )


def _compact_alias_sample(row: dict[str, Any], *, field: str, value: Any, expected: str) -> dict[str, Any]:
    return {
        "catalog_index": row.get("catalog_index"),
        "field": field,
        "value": value,
        "expected": expected,
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "character_name": row.get("character_name"),
        "affiliation": row.get("affiliation"),
        "source_url": row.get("source_url"),
    }


def build_character_alias_monitor(rows: list[dict[str, Any]]) -> dict[str, Any]:
    monitored_affiliations: dict[str, Any] = {}
    total_alias_hits = 0
    total_unknown_character_rows = 0

    for affiliation, policy in CHARACTER_ALIAS_MONITOR_TARGETS.items():
        scoped_rows = [row for row in rows if str(row.get("affiliation") or "") == affiliation]
        canonical = set(policy.get("canonical_characters") or ())
        watched_aliases: dict[str, str] = dict(policy.get("watched_aliases") or {})
        character_counts: dict[str, int] = {}
        unknown_character_rows: list[dict[str, Any]] = []
        alias_hits: list[dict[str, Any]] = []

        for row in scoped_rows:
            character_name = str(row.get("character_name") or "")
            character_counts[character_name] = character_counts.get(character_name, 0) + 1
            if character_name not in canonical:
                total_unknown_character_rows += 1
                unknown_character_rows.append(
                    {
                        "catalog_index": row.get("catalog_index"),
                        "character_name": row.get("character_name"),
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                    }
                )

            for alias, expected in watched_aliases.items():
                for field in ("character_name", "name_ko", "name_ja"):
                    value = row.get(field)
                    if alias and alias in str(value or ""):
                        total_alias_hits += 1
                        alias_hits.append(_compact_alias_sample(row, field=field, value=value, expected=expected))

        monitored_affiliations[affiliation] = {
            "rows": len(scoped_rows),
            "canonical_character_counts": sorted(character_counts.items(), key=lambda item: (-item[1], item[0])),
            "watched_alias_hit_count": len(alias_hits),
            "watched_alias_samples": alias_hits[:40],
            "unknown_character_rows": len(unknown_character_rows),
            "unknown_character_samples": unknown_character_rows[:40],
        }

    return {
        "scope": "character_alias_monitor",
        "total_watched_alias_hits": total_alias_hits,
        "total_unknown_character_rows": total_unknown_character_rows,
        "monitored_affiliations": monitored_affiliations,
    }


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    character_alias_violations: list[dict[str, Any]] = []
    ichiban_display_name_violations: list[dict[str, Any]] = []
    ichiban_display_character_mismatches: list[dict[str, Any]] = []
    ichiban_product_character_violations: list[dict[str, Any]] = []
    ichiban_multi_character_product_review_candidates: list[dict[str, Any]] = []
    ichiban_multi_character_combined_goods_exceptions: list[dict[str, Any]] = []
    zero_price_violations: list[dict[str, Any]] = []

    for row in rows:
        catalog_index = row.get("catalog_index")
        for bad_value, rule in CHARACTER_MOJIBAKE_OR_ALIAS_FINDINGS.items():
            affiliation_scope = rule.get("affiliation_scope")
            if affiliation_scope and affiliation_scope not in str(row.get("affiliation") or ""):
                continue
            for field in rule["fields"]:
                value = row.get(field)
                match_mode = rule.get("match", "exact")
                violation = value == bad_value
                if match_mode == "contains":
                    violation = bad_value in str(value or "")
                if violation:
                    character_alias_violations.append(
                        {
                            "catalog_index": catalog_index,
                            "field": field,
                            "value": value,
                            "expected": rule["expected"],
                            "reason": rule["reason"],
                            "name_ko": row.get("name_ko"),
                        }
                    )

        if not is_ichiban_row(row):
            continue

        name_ko = str(row.get("name_ko") or "")
        parts = [part.strip() for part in name_ko.split(" / ")]
        prize_label = parts[1] if len(parts) > 1 else ""
        product_name = parts[2] if len(parts) > 2 else name_ko
        display_character_name = parts[3] if len(parts) > 3 else ""
        valid_prize_label = prize_label.endswith(ICHIBAN_PRIZE_LABEL_SUFFIXES) or prize_label in ICHIBAN_PRIZE_LABEL_EXACT
        if len(parts) != 4 or ICHIBAN_PREFIX not in parts[0] or not valid_prize_label:
            ichiban_display_name_violations.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "series_name": row.get("series_name"),
                    "sub_series": row.get("sub_series"),
                    "character_name": row.get("character_name"),
                    "reason": "expected_kuji_campaign_prize_product_character_display_name",
                }
            )
        character_name = str(row.get("character_name") or "")
        if len(parts) == 4 and character_name and display_character_name != character_name:
            ichiban_display_character_mismatches.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "series_name": row.get("series_name"),
                    "sub_series": row.get("sub_series"),
                    "display_character_name": display_character_name,
                    "character_name": row.get("character_name"),
                    "reason": "display_character_name_must_match_character_name_field",
                }
            )
        matched_product_characters = []
        for japanese_token, expected_character in ICHIBAN_PRODUCT_CHARACTER_TOKENS:
            if product_token_matches(product_name, japanese_token):
                matched_product_characters.append(
                    {
                        "matched_token": japanese_token,
                        "expected_character": expected_character,
                    }
                )
        unique_matched_characters = sorted(
            {item["expected_character"] for item in matched_product_characters}
        )
        if len(unique_matched_characters) > 1:
            multi_character_record = {
                "catalog_index": catalog_index,
                "name_ko": row.get("name_ko"),
                "product_name": product_name,
                "character_name": row.get("character_name"),
                "matched_characters": unique_matched_characters,
                "matched_tokens": matched_product_characters,
            }
            if any(marker in product_name for marker in ICHIBAN_COMBINED_PRODUCT_MARKERS):
                ichiban_multi_character_combined_goods_exceptions.append(
                    {
                        **multi_character_record,
                        "reason": "product_name_is_combined_goods_preserve_as_mixed_row",
                    }
                )
            else:
                ichiban_multi_character_product_review_candidates.append(
                    {
                        **multi_character_record,
                        "reason": "product_name_contains_multiple_character_tokens_review_before_splitting",
                    }
                )
        if character_name not in ("", "\uae30\ud0c0", "\ud63c\ud569"):
            for item in matched_product_characters:
                expected_character = item["expected_character"]
                if expected_character not in character_name:
                    ichiban_product_character_violations.append(
                        {
                            "catalog_index": catalog_index,
                            "name_ko": row.get("name_ko"),
                            "product_name": product_name,
                            "character_name": row.get("character_name"),
                            "expected": expected_character,
                            "matched_token": item["matched_token"],
                            "reason": "product_name_character_token_mismatch",
                        }
                    )
                break

        sub_series = str(row.get("sub_series") or "")
        if (
            LAST_ONE_LABEL in sub_series
            or any(label in sub_series for label in DOUBLE_CHANCE_LABELS)
            or "\ub77c\uc2a4\ud2b8\uc6d0" in name_ko
            or "\ub354\ube14\ucc2c\uc2a4" in name_ko
        ) and row.get("official_price_jpy") not in (0, None):
            zero_price_violations.append(
                {
                    "catalog_index": catalog_index,
                    "name_ko": row.get("name_ko"),
                    "sub_series": row.get("sub_series"),
                    "official_price_jpy": row.get("official_price_jpy"),
                    "reason": "last_one_and_double_chance_rows_must_have_zero_price",
                }
            )

    findings = (
        len(character_alias_violations)
        + len(ichiban_display_name_violations)
        + len(ichiban_display_character_mismatches)
        + len(ichiban_product_character_violations)
        + len(ichiban_multi_character_product_review_candidates)
        + len(zero_price_violations)
    )
    alias_monitor = build_character_alias_monitor(rows)

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "catalog_character_name_policy",
        "summary": {
            "rows": len(rows),
            "ichiban_rows": sum(1 for row in rows if is_ichiban_row(row)),
            "character_alias_violations": len(character_alias_violations),
            "ichiban_display_name_violations": len(ichiban_display_name_violations),
            "ichiban_display_character_mismatches": len(ichiban_display_character_mismatches),
            "ichiban_product_character_violations": len(ichiban_product_character_violations),
            "ichiban_multi_character_product_review_candidates": len(
                ichiban_multi_character_product_review_candidates
            ),
            "ichiban_multi_character_combined_goods_exceptions": len(
                ichiban_multi_character_combined_goods_exceptions
            ),
            "zero_price_violations": len(zero_price_violations),
            "watched_alias_hits": alias_monitor["total_watched_alias_hits"],
            "unknown_monitored_character_rows": alias_monitor["total_unknown_character_rows"],
            "findings": findings,
            "status": "pass" if findings == 0 else "needs_review",
        },
        "policy": {
            "character_name_aliases": CHARACTER_MOJIBAKE_OR_ALIAS_FINDINGS,
            "ichiban_product_character_tokens": ICHIBAN_PRODUCT_CHARACTER_TOKENS,
            "ichiban_display_name_format": (
                "\uc774\uce58\ubc29\ucfe0\uc9c0 \ubc1c\ub9e4\uba85 / \uc0c1 / "
                "\uc0c1\ud488\uc774\ub984 / \uce90\ub9ad\ud130\uba85"
            ),
            "ichiban_display_name_official_language_note": (
                "Keep official campaign and product names in their official source language; the app layer may "
                "translate display text for each viewer locale."
            ),
            "ichiban_variant_split_rule": (
                "If an official Ichiban Kuji prize rank has separate character variants, keep one catalog row per "
                "character. Example: the same prize rank with three characters must become three rows whose display "
                "names only differ by the final character segment."
            ),
            "last_one_and_double_chance_price_jpy": 0,
            "multi_character_product_review": (
                "Rows whose product name contains multiple character tokens but no combined-goods marker are "
                "blocking split-review findings. True pair/team goods using &, ＆, ×, VS, or ・ are preserved "
                "as mixed rows unless official source evidence lists separate prize items."
            ),
        },
        "character_alias_violations": character_alias_violations,
        "ichiban_display_name_violations": ichiban_display_name_violations,
        "ichiban_display_character_mismatches": ichiban_display_character_mismatches,
        "ichiban_product_character_violations": ichiban_product_character_violations,
        "ichiban_multi_character_product_review_candidates": ichiban_multi_character_product_review_candidates,
        "ichiban_multi_character_combined_goods_exceptions": ichiban_multi_character_combined_goods_exceptions,
        "zero_price_violations": zero_price_violations,
        "character_alias_monitor": alias_monitor,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero when the catalog still has character/name policy findings.",
    )
    args = parser.parse_args()

    report = audit(load_catalog(args.catalog))
    if args.write:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.fail_on_findings and report["summary"]["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
