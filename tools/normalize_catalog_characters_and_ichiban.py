from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from generate_seed_catalog_dart import generate
    from audit_catalog_character_names import ICHIBAN_PRODUCT_CHARACTER_TOKENS, product_token_matches
except ModuleNotFoundError:
    from tools.generate_seed_catalog_dart import generate
    from tools.audit_catalog_character_names import ICHIBAN_PRODUCT_CHARACTER_TOKENS, product_token_matches

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_SEED_OUTPUT = ROOT / "lib" / "data" / "catalog" / "seed_catalog.dart"
DEFAULT_REPORT = ROOT / "data" / "catalog_character_ichiban_normalization_public.json"

GENERIC_CHARACTERS = {"기타", "혼합", ""}
CHARACTER_ALIAS_RULES = {
    "키르아 조르딕": "키루아 조르딕",
    "키르아": "키루아",
    "보아 행콕": "보아 핸콕",
    "행콕": "핸콕",
}
FRIEREN_JA_TO_KO = {
    "フリーレン": "프리렌",
    "フェルン": "페른",
    "シュタルク": "슈타르크",
    "ヒンメル": "히멜",
    "ハイター": "하이터",
    "アイゼン": "아이젠",
}
FRIEREN_KO_TO_JA = {value: key for key, value in FRIEREN_JA_TO_KO.items()}
FRIEREN_SCOPED_ALIAS_RULES = {
    "펀": "페른",
    "펌": "페른",
    "프렌": "페른",
    "Pern": "페른",
    "Fern": "페른",
    "후리렌": "프리렌",
    "프리랜": "프리렌",
}
ICHIBAN_CHARACTER_RULES: dict[str, list[tuple[str, str]]] = {
    "블루록": [
        ("潔 世一", "이사기 요이치"),
        ("潔世一", "이사기 요이치"),
        ("凪 誠士郎", "나기 세이시로"),
        ("凪誠士郎", "나기 세이시로"),
        ("馬狼", "바로 쇼에이"),
        ("蜂楽 廻", "바치라 메구루"),
        ("蜂楽廻", "바치라 메구루"),
        ("千切 豹馬", "치기리 효마"),
        ("千切豹馬", "치기리 효마"),
        ("糸師 凛", "이토시 린"),
        ("糸師凛", "이토시 린"),
        ("糸師 冴", "이토시 사에"),
        ("糸師冴", "이토시 사에"),
        ("御影 玲王", "미카게 레오"),
        ("御影玲王", "미카게 레오"),
        ("國神 錬介", "쿠니가미 렌스케"),
        ("國神錬介", "쿠니가미 렌스케"),
        ("雷市 陣吾", "라이치 진고"),
        ("雷市陣吾", "라이치 진고"),
        ("我牙丸 吟", "가가마루 긴"),
        ("我牙丸吟", "가가마루 긴"),
        ("絵心 甚八", "에고 진파치"),
        ("絵心甚八", "에고 진파치"),
        ("帝襟 アンリ", "테이에리 안리"),
        ("帝襟アンリ", "테이에리 안리"),
        ("二子 一揮", "니코 잇키"),
        ("二子一揮", "니코 잇키"),
        ("蟻生 十兵衛", "아류 주베에"),
        ("蟻生十兵衛", "아류 주베에"),
        ("時光 青志", "토키미츠 아오시"),
        ("時光青志", "토키미츠 아오시"),
        ("士道 龍聖", "시도 류세이"),
        ("士道龍聖", "시도 류세이"),
    ],
    "원피스": [
        ("モンキー・D・ルフィ", "몽키 D. 루피"),
        ("モンキー・D・ルフィ太郎", "몽키 D. 루피"),
        ("ルフィ", "몽키 D. 루피"),
        ("ロロノア・ゾロ", "롤로노아 조로"),
        ("ゾロ十郎", "롤로노아 조로"),
        ("ゾロ", "롤로노아 조로"),
        ("ナミ", "나미"),
        ("サンジ", "상디"),
        ("ウソップ", "우솝"),
        ("トニートニー・チョッパー", "토니토니 쵸파"),
        ("チョッパー", "토니토니 쵸파"),
        ("ニコ・ロビン", "니코 로빈"),
        ("ロビン", "니코 로빈"),
        ("フランキー", "프랑키"),
        ("ブルック", "브룩"),
        ("ジンベエ", "징베"),
        ("トラファルガー・ロー", "트라팔가 로"),
        ("トラファルガー・D・ワーテル・ロー", "트라팔가 로"),
        ("ペローナ", "페로나"),
        ("ロー", "트라팔가 로"),
        ("ポートガス・D・エース", "포트거스 D. 에이스"),
        ("エース", "포트거스 D. 에이스"),
        ("サボ", "사보"),
        ("シャンクス", "샹크스"),
        ("バギー", "버기"),
        ("ボア・ハンコック", "보아 핸콕"),
        ("ハンコック", "보아 핸콕"),
        ("ヤマト", "야마토"),
        ("カイドウ", "카이도"),
        ("光月おでん", "코즈키 오뎅"),
        ("おでん", "코즈키 오뎅"),
        ("しらほし", "시라호시"),
        ("ビビ", "네펠타리 비비"),
        ("キャロット", "캐럿"),
        ("ウタ", "우타"),
        ("ロジャー", "골 D. 로저"),
        ("エドワード・ニューゲート", "에드워드 뉴게이트"),
        ("白ひげ", "에드워드 뉴게이트"),
        ("マルコ", "마르코"),
        ("クロコダイル", "크로커다일"),
        ("ミホーク", "쥬라큘 미호크"),
        ("ドフラミンゴ", "돈키호테 도플라밍고"),
        ("キッド", "유스타스 키드"),
    ],
    "헌터X헌터": [
        ("ゴン=フリークス", "곤 프릭스"),
        ("ゴン＝フリークス", "곤 프릭스"),
        ("キルア=ゾルディック", "키루아 조르딕"),
        ("キルア＝ゾルディック", "키루아 조르딕"),
        ("キルアのヨーヨー", "키루아 조르딕"),
        ("アルカ=ゾルディック", "아르카 조르딕"),
        ("アルカ＝ゾルディック", "아르카 조르딕"),
        ("ナニカ", "나니카"),
        ("ゼノ=ゾルディック", "제노 조르딕"),
        ("ゼノ＝ゾルディック", "제노 조르딕"),
        ("シルバ=ゾルディック", "실버 조르딕"),
        ("シルバ＝ゾルディック", "실버 조르딕"),
        ("クラピカ", "쿠라피카"),
        ("ヒソカ=モロウ", "히소카 모로"),
        ("ヒソカ＝モロウ", "히소카 모로"),
        ("ヒソカ", "히소카 모로"),
        ("レオリオ", "레오리오"),
        ("クロロ", "쿠로로 루실풀"),
        ("イルミ", "일루미"),
        ("メルエム", "메루엠"),
    ],
    "주술회전": [
        ("虎杖悠仁", "이타도리 유지"),
        ("伏黒恵", "후시구로 메구미"),
        ("釘崎野薔薇", "쿠기사키 노바라"),
        ("五条悟", "고죠 사토루"),
        ("夏油傑", "게토 스구루"),
        ("両面宿儺", "료멘 스쿠나"),
        ("七海建人", "나나미 켄토"),
        ("禪院真希", "젠인 마키"),
        ("禪院真依", "젠인 마이"),
        ("乙骨憂太", "옷코츠 유타"),
        ("祈本里香", "오리모토 리카"),
        ("リカ", "리카"),
        ("秤金次", "하카리 킨지"),
        ("星綺羅羅", "호시 키라라"),
        ("日車寛見", "히구루마 히로미"),
        ("レジィ・スター", "레지 스타"),
        ("髙羽史彦", "타카바 후미히코"),
        ("高羽史彦", "타카바 후미히코"),
        ("石流龍", "이시고리 류"),
        ("羂索", "켄자쿠"),
        ("九十九由基", "츠쿠모 유키"),
        ("禪院直哉", "젠인 나오야"),
        ("脹相", "쵸소"),
        ("真希", "젠인 마키"),
        ("真依", "젠인 마이"),
        ("狗巻棘", "이누마키 토게"),
        ("パンダ", "판다"),
        ("真人", "마히토"),
    ],
    "나의 히어로 아카데미아": [
        ("緑谷出久", "미도리야 이즈쿠"),
        ("爆豪勝己", "바쿠고 카츠키"),
        ("轟焦凍", "토도로키 쇼토"),
        ("麗日お茶子", "우라라카 오챠코"),
        ("蛙吹梅雨", "츠유 아스이"),
        ("飯田天哉", "이이다 텐야"),
        ("切島鋭児郎", "키리시마 에이지로"),
        ("上鳴電気", "카미나리 덴키"),
        ("耳郎響香", "지로 쿄카"),
        ("八百万百", "야오요로즈 모모"),
        ("相澤消太", "아이자와 쇼타"),
        ("山田ひざし", "야마다 히자시"),
        ("白雲朧", "시라쿠모 오보로"),
        ("死柄木弔", "시가라키 토무라"),
        ("トガヒミコ", "토가 히미코"),
        ("荼毘", "다비"),
        ("ホークス", "호크스"),
        ("エンデヴァー", "엔데버"),
        ("オールマイト", "올마이트"),
        ("アーマード・オールマイト", "올마이트"),
        ("ステイン", "스테인"),
        ("峰田実", "미네타 미노루"),
        ("灰廻航一", "하이마와리 코이치"),
    ],
    "귀멸의 칼날": [
        ("竈門炭治郎", "카마도 탄지로"),
        ("炭治郎", "카마도 탄지로"),
        ("竈門禰豆子", "카마도 네즈코"),
        ("禰豆子", "카마도 네즈코"),
        ("我妻善逸", "아가츠마 젠이츠"),
        ("善逸", "아가츠마 젠이츠"),
        ("嘴平伊之助", "하시비라 이노스케"),
        ("伊之助", "하시비라 이노스케"),
        ("冨岡義勇", "토미오카 기유"),
        ("富岡義勇", "토미오카 기유"),
        ("義勇", "토미오카 기유"),
        ("胡蝶しのぶ", "코쵸 시노부"),
        ("栗花落カナヲ", "츠유리 카나오"),
        ("煉獄杏寿郎", "렌고쿠 쿄쥬로"),
        ("宇髄天元", "우즈이 텐겐"),
        ("時透無一郎", "토키토 무이치로"),
        ("甘露寺蜜璃", "칸로지 미츠리"),
        ("悲鳴嶼行冥", "히메지마 교메이"),
        ("不死川実弥", "시나즈가와 사네미"),
        ("童磨", "도우마"),
        ("獪岳", "카이가쿠"),
        ("狛治", "하쿠지"),
    ],
    "블리치": [
        ("黒崎一護", "쿠로사키 이치고"),
        ("朽木ルキア", "쿠치키 루키아"),
        ("日番谷冬獅郎", "히츠가야 토시로"),
        ("平子真子", "히라코 신지"),
        ("藍染惣右介", "아이젠 소스케"),
        ("浦原喜助", "우라하라 키스케"),
    ],
    "드래곤볼": [
        ("悟空", "손오공"),
        ("悟飯", "손오반"),
        ("ベジータ", "베지터"),
        ("トランクス", "트랭크스"),
        ("ゴテンクス", "오천크스"),
        ("ベジット", "베지트"),
    ],
}


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise SystemExit(f"{path} must contain an object with items")
    return data


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_character_aliases(rows: list[dict[str, Any]], *, write: bool) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for row in rows:
        before_character = _text(row.get("character_name"))
        after_character = CHARACTER_ALIAS_RULES.get(before_character)
        before_name = _text(row.get("name_ko"))
        after_name = before_name
        for before, after in CHARACTER_ALIAS_RULES.items():
            after_name = after_name.replace(before, after)
        if not after_character and before_name == after_name:
            continue
        changes.append(
            {
                "catalog_index": row.get("catalog_index"),
                "field_changes": {
                    "character_name": {
                        "from": row.get("character_name"),
                        "to": after_character or row.get("character_name"),
                    },
                    "name_ko": {"from": row.get("name_ko"), "to": after_name},
                },
            }
        )
        if write:
            if after_character:
                row["character_name"] = after_character
            row["name_ko"] = after_name
    return changes


def _is_ichiban(row: dict[str, Any]) -> bool:
    fields = [_text(row.get(key)) for key in ("name_ko", "name_ja", "series_name", "source_url")]
    return any("一番くじ" in value or "이치방쿠지" in value for value in fields) or any(
        "1kuji.com/products/" in value for value in fields
    )


def _prize_item_name(row: dict[str, Any]) -> str:
    name = _text(row.get("name_ja")) or _text(row.get("name_ko"))
    tier = _text(row.get("sub_series"))
    if tier and name.startswith(tier):
        return name[len(tier) :].strip()
    return name


def _ichiban_display_name(row: dict[str, Any], character_name: str | None = None) -> str:
    release = _text(row.get("series_name"))
    tier = _text(row.get("sub_series"))
    item = _prize_item_name(row)
    character = _text(character_name if character_name is not None else row.get("character_name"))
    parts = [part for part in (release, tier, item, character) if part]
    return " / ".join(parts)


def _extract_frieren_characters(row: dict[str, Any]) -> list[str]:
    # Only inspect the prize item itself. The release name contains フリーレン,
    # which would incorrectly mark every prize in the campaign as Frieren.
    text = _prize_item_name(row)
    return [ko for ja, ko in FRIEREN_JA_TO_KO.items() if ja in text]


def _normalize_frieren_aliases(rows: list[dict[str, Any]], *, write: bool) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for row in rows:
        haystack = " ".join(_text(row.get(key)) for key in ("name_ja", "name_ko", "affiliation", "series_name"))
        if "フェルン" not in haystack and "장송의 프리렌" not in haystack:
            continue
        before = {
            "name_ko": row.get("name_ko"),
            "character_name": row.get("character_name"),
            "affiliation": row.get("affiliation"),
        }
        after_name = _text(row.get("name_ko"))
        after_character = _text(row.get("character_name"))
        after_affiliation = _text(row.get("affiliation"))
        for alias, canonical in FRIEREN_SCOPED_ALIAS_RULES.items():
            after_name = after_name.replace(alias, canonical)
            after_character = after_character.replace(alias, canonical)
            after_affiliation = after_affiliation.replace(alias, canonical)
        if (
            before["name_ko"] == after_name
            and before["character_name"] == after_character
            and before["affiliation"] == after_affiliation
        ):
            continue
        changes.append(
            {
                "catalog_index": row.get("catalog_index"),
                "field_changes": {
                    "name_ko": {"from": before["name_ko"], "to": after_name},
                    "character_name": {"from": before["character_name"], "to": after_character},
                    "affiliation": {"from": before["affiliation"], "to": after_affiliation},
                },
            }
        )
        if write:
            row["name_ko"] = after_name
            row["character_name"] = after_character
            row["affiliation"] = after_affiliation
    return changes


def _normalize_last_one_prices(rows: list[dict[str, Any]], *, write: bool) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for row in rows:
        if not _is_ichiban(row):
            continue
        text = " ".join(_text(row.get(key)) for key in ("name_ko", "name_ja", "sub_series"))
        if not any(keyword in text for keyword in ("ラストワン", "라스트원", "ダブルチャンス", "더블찬스")):
            continue
        if row.get("official_price_jpy") == 0:
            continue
        changes.append(
            {
                "catalog_index": row.get("catalog_index"),
                "field_changes": {
                    "official_price_jpy": {"from": row.get("official_price_jpy"), "to": 0}
                },
            }
        )
        if write:
            row["official_price_jpy"] = 0
    return changes


def _normalize_ichiban_direct_character_rules(
    rows: list[dict[str, Any]], *, write: bool
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for row in rows:
        if not _is_ichiban(row):
            continue
        rules = ICHIBAN_CHARACTER_RULES.get(_text(row.get("affiliation")))
        if not rules:
            continue
        item_name = _prize_item_name(row)
        multi_marker_text = re.sub(r"（[^）]*）|\([^)]*\)", "", item_name)
        if any(marker in multi_marker_text for marker in ("＆", "&", "、", "／", "/", "VS", "vs")):
            continue
        if "吸収" in item_name or "ザマス" in item_name:
            continue
        matches: list[str] = []
        for alias, character in rules:
            if product_token_matches(item_name, alias) and character not in matches:
                matches.append(character)
        if len(matches) != 1:
            continue
        character = matches[0]
        new_name = _ichiban_display_name(row, character)
        if row.get("character_name") == character and row.get("name_ko") == new_name:
            continue
        changes.append(
            {
                "catalog_index": row.get("catalog_index"),
                "affiliation": row.get("affiliation"),
                "matched_character": character,
                "field_changes": {
                    "character_name": {"from": row.get("character_name"), "to": character},
                    "name_ko": {"from": row.get("name_ko"), "to": new_name},
                },
            }
        )
        if write:
            row["character_name"] = character
            row["name_ko"] = new_name
    return changes


def _normalize_ichiban_multi_character_sets(
    rows: list[dict[str, Any]], *, write: bool
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for row in rows:
        if not _is_ichiban(row) or _text(row.get("character_name")) != "기타":
            continue
        item_name = _prize_item_name(row)
        matched_characters: list[str] = []
        for token, character in ICHIBAN_PRODUCT_CHARACTER_TOKENS:
            if product_token_matches(item_name, token) and character not in matched_characters:
                matched_characters.append(character)
        if len(matched_characters) <= 1:
            continue
        new_name = _ichiban_display_name(row, "혼합")
        changes.append(
            {
                "catalog_index": row.get("catalog_index"),
                "matched_characters": matched_characters,
                "field_changes": {
                    "character_name": {"from": row.get("character_name"), "to": "혼합"},
                    "name_ko": {"from": row.get("name_ko"), "to": new_name},
                },
            }
        )
        if write:
            row["character_name"] = "혼합"
            row["name_ko"] = new_name
    return changes


def _split_frieren_ichiban(rows: list[dict[str, Any]], *, write: bool) -> dict[str, Any]:
    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    created_indexes: set[int] = set()
    max_index = max((int(row.get("catalog_index")) for row in rows if isinstance(row.get("catalog_index"), int)), default=-1)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if _text(row.get("series_name")) == "一番くじ 葬送のフリーレン":
            grouped.setdefault((_text(row.get("source_url")), _text(row.get("sub_series"))), []).append(row)

    for (_source_url, _tier), group_rows in sorted(
        grouped.items(), key=lambda item: min(int(row.get("catalog_index")) for row in item[1])
    ):
        group_rows.sort(key=lambda row: int(row.get("catalog_index")))
        base_row = group_rows[0]
        characters = []
        for candidate_row in group_rows:
            for character in _extract_frieren_characters(candidate_row):
                if character not in characters:
                    characters.append(character)
        if not characters:
            new_name = _ichiban_display_name(base_row, "혼합")
            if base_row.get("character_name") != "혼합" or base_row.get("name_ko") != new_name:
                updated.append(
                    {
                        "catalog_index": base_row.get("catalog_index"),
                        "field_changes": {
                            "character_name": {"from": base_row.get("character_name"), "to": "혼합"},
                            "name_ko": {"from": base_row.get("name_ko"), "to": new_name},
                        },
                    }
                )
            if write and updated and updated[-1].get("catalog_index") == base_row.get("catalog_index"):
                base_row["character_name"] = "혼합"
                base_row["name_ko"] = new_name
            continue

        if len(characters) == 1:
            new_name = _ichiban_display_name(base_row, characters[0])
            if base_row.get("character_name") != characters[0] or base_row.get("name_ko") != new_name:
                updated.append(
                    {
                        "catalog_index": base_row.get("catalog_index"),
                        "field_changes": {
                            "character_name": {"from": base_row.get("character_name"), "to": characters[0]},
                            "name_ko": {"from": base_row.get("name_ko"), "to": new_name},
                        },
                    }
                )
            if write and updated and updated[-1].get("catalog_index") == base_row.get("catalog_index"):
                base_row["character_name"] = characters[0]
                base_row["name_ko"] = new_name
            continue

        # Rows whose official prize item lists several characters represent selectable variants.
        # Keep the first catalog index and create one sibling row for each remaining character.
        while len(group_rows) < len(characters):
            max_index += 1
            new_row = deepcopy(base_row)
            new_row["catalog_index"] = max_index
            new_row.pop("barcode", None)
            group_rows.append(new_row)
            created_indexes.add(max_index)
            if write:
                rows.append(new_row)

        for extra in group_rows[len(characters) :]:
            removed.append(
                {
                    "catalog_index": extra.get("catalog_index"),
                    "reason": "extra_frieren_ichiban_variant_row",
                    "name_ko": extra.get("name_ko"),
                    "name_ja": extra.get("name_ja"),
                    "character_name": extra.get("character_name"),
                }
            )
            if write and extra in rows:
                rows.remove(extra)

        for position, character in enumerate(characters):
            target = group_rows[position]
            character_ja = FRIEREN_KO_TO_JA[character]
            variant_item = _frieren_variant_item_name(base_row, character_ja)
            new_name_ja = f"{_text(base_row.get('sub_series'))} {variant_item}".strip()
            new_name_ko = _ichiban_display_name({**target, "name_ja": new_name_ja}, character)
            was_created_this_run = target.get("catalog_index") in created_indexes
            before_snapshot = {
                "name_ja": target.get("name_ja"),
                "character_name": target.get("character_name"),
                "name_ko": target.get("name_ko"),
            }
            has_changes = (
                before_snapshot["name_ja"] != new_name_ja
                or before_snapshot["character_name"] != character
                or before_snapshot["name_ko"] != new_name_ko
            )
            if write:
                target["name_ja"] = new_name_ja
                target["character_name"] = character
                target["name_ko"] = new_name_ko
            if target in rows and not was_created_this_run:
                if not has_changes:
                    continue
                updated.append(
                    {
                        "catalog_index": target.get("catalog_index"),
                        "field_changes": {
                            "name_ja": {"from": before_snapshot["name_ja"], "to": target.get("name_ja")},
                            "character_name": {"from": before_snapshot["character_name"], "to": character},
                            "name_ko": {"from": before_snapshot["name_ko"], "to": target.get("name_ko")},
                        },
                    }
                )
            elif was_created_this_run:
                created.append(
                    {
                        "catalog_index": target.get("catalog_index"),
                        "from_catalog_index": base_row.get("catalog_index"),
                        "name_ko": target.get("name_ko"),
                        "name_ja": target.get("name_ja"),
                        "character_name": target.get("character_name"),
                    }
                )

    return {"updated": updated, "created": created, "removed": removed, "skipped": skipped}


def _frieren_variant_item_name(row: dict[str, Any], character_ja: str) -> str:
    if _text(row.get("source_url")) == "https://1kuji.com/products/frieren" and _text(
        row.get("sub_series")
    ) in {"C賞", "D賞"}:
        return f"ちょこのっこフィギュア {character_ja}"
    item = _prize_item_name(row)
    item = re.sub(r"\s*\([^()]*\)\s*$", "", item).strip()
    for joined in ("フリーレン、フェルン、シュタルク", "ヒンメル、ハイター、アイゼン"):
        if joined in item:
            return item.replace(joined, character_ja)
    return f"{item} {character_ja}".strip()


def _audit_ichiban(rows: list[dict[str, Any]]) -> dict[str, Any]:
    needs_character = []
    needs_display_name = []
    multi_character_rows = []
    for row in rows:
        if not _is_ichiban(row):
            continue
        character = _text(row.get("character_name"))
        expected = _ichiban_display_name(row)
        if character in GENERIC_CHARACTERS:
            needs_character.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "series_name": row.get("series_name"),
                    "sub_series": row.get("sub_series"),
                    "name_ja": row.get("name_ja"),
                    "character_name": row.get("character_name"),
                    "source_url": row.get("source_url"),
                }
            )
        if expected and _text(row.get("name_ko")) != expected:
            needs_display_name.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "current_name_ko": row.get("name_ko"),
                    "expected_name_ko": expected,
                }
            )
        if re.search(r"[、/／]", _prize_item_name(row)):
            multi_character_rows.append(
                {
                    "catalog_index": row.get("catalog_index"),
                    "series_name": row.get("series_name"),
                    "sub_series": row.get("sub_series"),
                    "name_ja": row.get("name_ja"),
                    "character_name": row.get("character_name"),
                    "source_url": row.get("source_url"),
                }
            )
    return {
        "needs_character_assignment_count": len(needs_character),
        "needs_display_name_format_count": len(needs_display_name),
        "multi_character_or_variant_rows_count": len(multi_character_rows),
        "needs_character_assignment_sample": needs_character[:80],
        "needs_display_name_format_sample": needs_display_name[:80],
        "multi_character_or_variant_rows_sample": multi_character_rows[:80],
    }


def _missing_by_field(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    return {field: sum(1 for row in rows if row.get(field) in (None, "")) for field in fields}


def _sync_seed(catalog: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate(catalog["items"], source_label="data/catalog_public.json"), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--seed-output", type=Path, default=DEFAULT_SEED_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    catalog = _load(args.catalog)
    rows: list[dict[str, Any]] = catalog["items"]
    before_count = len(rows)

    global_character_alias_changes = _normalize_character_aliases(rows, write=args.write)
    character_alias_changes = _normalize_frieren_aliases(rows, write=args.write)
    ichiban_direct_character_changes = _normalize_ichiban_direct_character_rules(
        rows, write=args.write
    )
    ichiban_multi_character_set_changes = _normalize_ichiban_multi_character_sets(
        rows, write=args.write
    )
    last_one_price_changes = _normalize_last_one_prices(rows, write=args.write)
    frieren_ichiban = _split_frieren_ichiban(rows, write=args.write)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if args.write:
        fields = catalog.get("meta", {}).get("fields") or []
        catalog.setdefault("meta", {})["generated_at"] = now
        catalog["meta"]["row_count"] = len(rows)
        catalog["meta"]["total_items"] = len(rows)
        catalog["meta"]["missing"] = _missing_by_field(rows, fields)
        args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        _sync_seed(catalog, args.seed_output)

    audit = _audit_ichiban(rows)
    report = {
        "schema_version": 1,
        "generated_at": now,
        "write": args.write,
        "policy": {
            "character_aliases": {
                "장송의 프리렌 scoped aliases": FRIEREN_SCOPED_ALIAS_RULES,
                "global aliases": CHARACTER_ALIAS_RULES,
            },
            "ichiban_display_name_format": "쿠지 발매명 / 상 / 상품이름 / 캐릭터명",
            "ichiban_multi_character_policy": "same prize rank with several character variants must be split into one row per character",
            "last_one_and_double_chance_price_jpy": 0,
        },
        "summary": {
            "rows_before": before_count,
            "rows_after": len(rows),
            "global_character_alias_changes": len(global_character_alias_changes),
            "character_alias_changes": len(character_alias_changes),
            "ichiban_direct_character_changes": len(ichiban_direct_character_changes),
            "ichiban_multi_character_set_changes": len(ichiban_multi_character_set_changes),
            "last_one_price_changes": len(last_one_price_changes),
            "frieren_ichiban_updated_rows": len(frieren_ichiban["updated"]),
            "frieren_ichiban_created_rows": len(frieren_ichiban["created"]),
            "frieren_ichiban_removed_rows": len(frieren_ichiban["removed"]),
        },
        "global_character_alias_changes": global_character_alias_changes,
        "character_alias_changes": character_alias_changes,
        "ichiban_direct_character_changes": ichiban_direct_character_changes,
        "ichiban_multi_character_set_changes": ichiban_multi_character_set_changes,
        "last_one_price_changes": last_one_price_changes,
        "frieren_ichiban": frieren_ichiban,
        "ichiban_audit_after": audit,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(json.dumps(audit, ensure_ascii=False, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
