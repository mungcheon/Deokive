from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = ROOT / "data" / "intake" / "incoming"

CONFIDENCE_VALUES = {"confirmed", "candidate", "needs_review"}
EVIDENCE_TYPES = {"official", "trusted", "manual"}
PRICE_CURRENCIES = {"JPY", "KRW", "USD", "CNY", "TWD"}
DATE_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
ICHIBAN_RE = re.compile(r"(ichiban|一番くじ|이치방\s*쿠지|이치방쿠지)", re.IGNORECASE)
ICHIBAN_PRIZE_RE = re.compile(
    r"^(?:[A-Z](?:\s*(?:Prize|상|賞))?|Last\s*One(?:\s*(?:Prize|상|賞))?|ラストワン賞|라스트원상|Double\s*Chance(?:\s*(?:Prize|상|賞))?|ダブルチャンス|더블찬스)$",
    re.IGNORECASE,
)
FRIEREN_KO = "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c"
FERN_JA = "\u30d5\u30a7\u30eb\u30f3"
FERN_CANONICAL_KO = "\ud398\ub978"
FERN_BAD_KO_ALIASES = ("\ud380", "\ud38c", "\ud504\ub80c", "Fern", "Pern")
TOP_LEVEL_FIELDS = {"schema_version", "agent", "items"}
AGENT_FIELDS = {"name", "run_id", "collected_at", "notes"}
ITEM_FIELDS = {
    "external_id",
    "display_name",
    "name_ko",
    "name_ja",
    "name_en",
    "affiliation",
    "category",
    "series_name",
    "sub_series",
    "character_name",
    "source_store",
    "source_url",
    "image_url",
    "release_date",
    "barcode",
    "official_price",
    "official_price_currency",
    "official_price_jpy",
    "evidence",
    "confidence",
    "notes",
}
EVIDENCE_FIELDS = {"url", "type", "note"}


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_string(
    errors: list[str],
    item_path: str,
    payload: dict[str, object],
    key: str,
    *,
    allow_empty: bool = False,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        errors.append(f"{item_path}.{key}: expected string")
        return ""
    if not allow_empty and not value.strip():
        errors.append(f"{item_path}.{key}: must not be empty")
    return value


def reject_unknown_fields(
    errors: list[str],
    item_path: str,
    payload: dict[str, object],
    allowed_fields: set[str],
) -> None:
    unknown = sorted(str(key) for key in payload if key not in allowed_fields)
    if unknown:
        errors.append(f"{item_path}: unknown field(s): {', '.join(unknown)}")


def is_iso_timestamp(value: str) -> bool:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt.datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def is_ichiban_item(item: dict[str, object]) -> bool:
    haystack = " ".join(
        str(item.get(key) or "")
        for key in ("display_name", "name_ko", "name_ja", "name_en", "series_name", "sub_series", "source_store")
    )
    return bool(ICHIBAN_RE.search(haystack))


def validate_ichiban_display_name(errors: list[str], item: dict[str, object], item_path: str) -> None:
    if not is_ichiban_item(item):
        return

    display_name = str(item.get("display_name") or "")
    parts = [part.strip() for part in display_name.split("/")]
    if len(parts) != 4 or any(not part for part in parts):
        errors.append(
            f"{item_path}.display_name: Ichiban Kuji items must use "
            "release name / prize rank / prize name / character name"
        )
        return

    if not ICHIBAN_PRIZE_RE.match(parts[1]):
        errors.append(
            f"{item_path}.display_name: Ichiban Kuji prize rank must be like "
            "A Prize, A상, A賞, Last One Prize, or Double Chance"
        )

    character_name = item.get("character_name")
    if isinstance(character_name, str) and character_name.strip() and character_name.strip() != parts[3]:
        errors.append(
            f"{item_path}.character_name: must match the fourth Ichiban Kuji display_name segment"
        )


def validate_character_aliases(errors: list[str], item: dict[str, object], item_path: str) -> None:
    serialized = json.dumps(item, ensure_ascii=False)
    context_fields = " ".join(
        str(item.get(key) or "")
        for key in ("display_name", "name_ja", "affiliation", "series_name", "sub_series", "character_name")
    )
    is_frieren_context = FRIEREN_KO in context_fields or FERN_JA in serialized
    if not is_frieren_context:
        return

    korean_fields = ("display_name", "name_ko", "affiliation", "character_name")
    display_text = " ".join(str(item.get(key) or "") for key in korean_fields)
    for alias in FERN_BAD_KO_ALIASES:
        if alias in display_text:
            errors.append(
                f"{item_path}: Fern/Frieren Korean aliases must use {FERN_CANONICAL_KO}, not {alias}"
            )
            return


def validate_item(
    errors: list[str],
    item: object,
    item_path: str,
    seen_keys: set[tuple[str, str]],
) -> None:
    if not isinstance(item, dict):
        errors.append(f"{item_path}: expected object")
        return
    reject_unknown_fields(errors, item_path, item, ITEM_FIELDS)

    required = [
        "external_id",
        "display_name",
        "category",
        "series_name",
        "source_store",
        "source_url",
        "confidence",
    ]
    for key in required:
        require_string(errors, item_path, item, key)

    source_url = item.get("source_url")
    if isinstance(source_url, str) and source_url.strip() and not is_url(source_url):
        errors.append(f"{item_path}.source_url: expected http(s) product/detail URL")

    image_url = item.get("image_url")
    if image_url is not None:
        if not isinstance(image_url, str):
            errors.append(f"{item_path}.image_url: expected string when present")
        elif image_url.strip() and not is_url(image_url):
            errors.append(f"{item_path}.image_url: expected http(s) URL")

    release_date = item.get("release_date")
    if release_date is not None:
        if not isinstance(release_date, str):
            errors.append(f"{item_path}.release_date: expected string when present")
        elif release_date.strip() and not DATE_RE.match(release_date.strip()):
            errors.append(f"{item_path}.release_date: expected YYYY, YYYY-MM, or YYYY-MM-DD")

    official_price = item.get("official_price")
    official_price_currency = item.get("official_price_currency")
    if official_price is not None:
        if not isinstance(official_price, int) or isinstance(official_price, bool):
            errors.append(f"{item_path}.official_price: expected integer or null")
        elif official_price < 0:
            errors.append(f"{item_path}.official_price: must be >= 0")
        if official_price_currency not in PRICE_CURRENCIES:
            errors.append(
                f"{item_path}.official_price_currency: required when official_price is set; "
                f"expected one of {', '.join(sorted(PRICE_CURRENCIES))}"
            )
    elif official_price_currency is not None and official_price_currency not in PRICE_CURRENCIES:
        errors.append(
            f"{item_path}.official_price_currency: expected one of "
            f"{', '.join(sorted(PRICE_CURRENCIES))} or null"
        )

    price_jpy = item.get("official_price_jpy")
    if price_jpy is not None:
        if not isinstance(price_jpy, int) or isinstance(price_jpy, bool):
            errors.append(f"{item_path}.official_price_jpy: expected integer yen or null")
        elif price_jpy < 0:
            errors.append(f"{item_path}.official_price_jpy: must be >= 0")
        if official_price is not None and official_price_currency == "JPY" and official_price != price_jpy:
            errors.append(
                f"{item_path}.official_price_jpy: must match official_price when "
                "official_price_currency is JPY"
            )
        if official_price is not None and official_price_currency not in (None, "JPY"):
            errors.append(
                f"{item_path}.official_price_jpy: cannot be combined with "
                f"official_price_currency {official_price_currency}"
            )
    if official_price_currency == "JPY" and price_jpy is None:
        errors.append(f"{item_path}.official_price_jpy: required when official_price_currency is JPY")

    barcode = item.get("barcode")
    if barcode is not None and not isinstance(barcode, str):
        errors.append(f"{item_path}.barcode: expected string or null")

    confidence = item.get("confidence")
    if isinstance(confidence, str) and confidence not in CONFIDENCE_VALUES:
        errors.append(
            f"{item_path}.confidence: expected one of {', '.join(sorted(CONFIDENCE_VALUES))}"
        )

    evidence = item.get("evidence")
    if not isinstance(evidence, list):
        errors.append(f"{item_path}.evidence: expected non-empty array")
    elif not evidence:
        errors.append(f"{item_path}.evidence: must contain at least one source row")
    else:
        evidence_has_source_url = False
        for evidence_index, evidence_row in enumerate(evidence):
            evidence_path = f"{item_path}.evidence[{evidence_index}]"
            if not isinstance(evidence_row, dict):
                errors.append(f"{evidence_path}: expected object")
                continue
            reject_unknown_fields(errors, evidence_path, evidence_row, EVIDENCE_FIELDS)
            url = require_string(errors, evidence_path, evidence_row, "url")
            if url and not is_url(url):
                errors.append(f"{evidence_path}.url: expected http(s) URL")
            if isinstance(source_url, str) and url.rstrip("/") == source_url.rstrip("/"):
                evidence_has_source_url = True
            evidence_type = require_string(errors, evidence_path, evidence_row, "type")
            if evidence_type and evidence_type not in EVIDENCE_TYPES:
                errors.append(
                    f"{evidence_path}.type: expected one of {', '.join(sorted(EVIDENCE_TYPES))}"
                )
        if isinstance(source_url, str) and source_url.strip() and not evidence_has_source_url:
            errors.append(f"{item_path}.evidence: must include the source_url as evidence")

    validate_ichiban_display_name(errors, item, item_path)
    validate_character_aliases(errors, item, item_path)

    duplicate_key = (
        str(item.get("source_store", "")).strip().casefold(),
        str(item.get("external_id", "")).strip().casefold(),
    )
    if duplicate_key in seen_keys:
        errors.append(f"{item_path}: duplicate source_store/external_id in this intake file")
    seen_keys.add(duplicate_key)


def validate_payload(path: Path, payload: object) -> tuple[list[str], dict[str, int | str]]:
    errors: list[str] = []
    summary: dict[str, int | str] = {"path": str(path), "items": 0}

    if not isinstance(payload, dict):
        return [f"{path}: expected top-level object"], summary
    reject_unknown_fields(errors, str(path), payload, TOP_LEVEL_FIELDS)

    if payload.get("schema_version") != 1:
        errors.append("schema_version: expected 1")

    agent = payload.get("agent")
    if not isinstance(agent, dict):
        errors.append("agent: expected object")
    else:
        reject_unknown_fields(errors, "agent", agent, AGENT_FIELDS)
        require_string(errors, "agent", agent, "name")
        require_string(errors, "agent", agent, "run_id")
        collected_at = require_string(errors, "agent", agent, "collected_at")
        if collected_at and not is_iso_timestamp(collected_at):
            errors.append("agent.collected_at: expected ISO-8601 timestamp")

    items = payload.get("items")
    if not isinstance(items, list):
        errors.append("items: expected array")
        return errors, summary
    if not items:
        errors.append("items: must contain at least one item")
    summary["items"] = len(items)

    seen_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(items):
        validate_item(errors, item, f"items[{index}]", seen_keys)

    return errors, summary


def iter_input_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        else:
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Deokive agent goods intake JSON files."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_INTAKE],
        help="Intake JSON file(s) or directories. Defaults to data/intake/incoming.",
    )
    args = parser.parse_args()

    files = iter_input_files(args.paths)
    if not files:
        print("No intake JSON files found.")
        return 0

    total_items = 0
    failed = False
    for path in files:
        try:
            payload = load_json(path)
        except json.JSONDecodeError as exc:
            print(f"{path}: invalid JSON: {exc}", file=sys.stderr)
            failed = True
            continue
        errors, summary = validate_payload(path, payload)
        total_items += int(summary["items"])
        if errors:
            failed = True
            print(f"{path}: FAILED ({len(errors)} issue(s))", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"{path}: OK ({summary['items']} item(s))")

    print(f"Validated {len(files)} file(s), {total_items} item(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
