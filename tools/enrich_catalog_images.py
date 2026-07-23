from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET
import sqlite3
import unicodedata
import requests

from image_enrichment_safety import is_product_specific_source_url, is_safe_source_image_pair
from catalog_normalize import is_generic_source_url


DEFAULT_INPUT = Path("server/catalog_seed_from_local.json")
DEFAULT_REPORT = Path("server/catalog_missing_images_report.json")
DEFAULT_CACHE_DIR = Path("server/.catalog_image_cache")
DEFAULT_DB = Path("server/deokive_dev.db")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

STORE_ALIASES = {
    "animate": "애니메이트",
    "ensky": "엔스카이",
    "goodsmile": "굿스마일컴퍼니",
    "stellive": "Stellive Store",
    "furyu": "FuRyu",
    "banpresto": "Banpresto",
    "taito": "Taito",
    "sega": "SEGA",
    "movic": "Movic",
    "kotobukiya": "코토부키야",
    "chiikawa_market": "치이카와 마켓",
}


STORE_PROVIDERS = {
    "치이카와 마켓": {
        "products_json": "https://chiikawamarket.jp/ko/products.json?limit=250&page={page}",
        "search_url": "https://chiikawamarket.jp/ko/search?q={query}&type=product",
        "sitemap_index": "https://chiikawamarket.jp/sitemap.xml",
    },
    "나가노 마켓": {
        "products_json": "https://nagano-market.jp/ko/products.json?limit=250&page={page}",
        "search_url": "https://nagano-market.jp/ko/search?q={query}&type=product",
        "sitemap_index": "https://nagano-market.jp/sitemap.xml",
    },
    "치이카와 모구모구 혼포": {
        "products_json": "https://chiikawamogumogu.shop/products.json?limit=250&page={page}",
        "search_url": "https://chiikawamogumogu.shop/search?q={query}&type=product",
        "sitemap_index": "https://chiikawamogumogu.shop/sitemap.xml",
    },
}

SEARCH_PROVIDERS = {
    "애니메이트": {
        "search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    },
    "Animate": {
        "search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    },
    "FuRyu": {
        "search_url": "https://furyuprize.com/search?keyword={query}",
    },
    "굿스마일컴퍼니": {
        "search_url": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    },
    "Taito": {
        "search_url": "https://www.taito.co.jp/api/Prize/?keyword={query}&storeID=&offset=0&limit=60&sortName=TaitoPrizeRank&isDesc=true&date=",
    },
    "SEGA": {
        "search_url": "https://segaplaza.jp/search/?word={query}",
    },
    "Banpresto": {
        "search_url": "https://bsp-prize.jp/search/?keyword={query}",
    },
    "코토부키야": {
        "search_url": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
        "base_url": "https://shop.kotobukiya.co.jp",
    },
    "Movic": {
        "search_url": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}",
        "base_url": "https://www.movic.jp",
    },
}

AFFILIATION_JA_QUERY_PREFIXES = {
    "나의 히어로 아카데미아": "僕のヒーローアカデミア",
    "하츠네 미쿠": "初音ミク",
    "주술회전": "呪術廻戦",
    "블루록": "ブルーロック",
    "원피스": "ワンピース",
    "드래곤볼": "ドラゴンボール",
    "SPY×FAMILY": "SPY×FAMILY",
    "헌터X헌터": "HUNTER×HUNTER",
    "나루토": "NARUTO",
    "귀멸의 칼날": "鬼滅の刃",
    "메이드 인 어비스": "メイドインアビス",
    "체인소맨": "チェンソーマン",
    "체인소 맨": "チェンソーマン",
    "진격의 거인": "進撃の巨人",
    "도쿄 리벤저스": "東京リベンジャーズ",
    "최애의 아이": "推しの子",
    "죠죠의 기묘한 모험": "ジョジョの奇妙な冒険",
    "슬램덩크": "SLAM DUNK",
    "리제로": "Re:ゼロから始める異世界生活",
    "전생슬": "転生したらスライムだった件",
    "슈타인즈게이트": "STEINS;GATE",
    "스킵과 로퍼": "スキップとローファー",
    "이루마군": "魔入りました！入間くん",
    "단다단": "ダンダダン",
    "명탐정 코난": "名探偵コナン",
    "짱구는 못말려": "クレヨンしんちゃん",
    "도라에몽": "ドラえもん",
    "카드캡터 체리": "カードキャプターさくら",
    "세일러문": "セーラームーン",
    "신세기 에반게리온": "新世紀エヴァンゲリオン",
    "강철의 연금술사": "鋼の錬金術師",
    "호리미야": "ホリミヤ",
}

KOREAN_GOODS_TYPE_JA_QUERY = {
    "봉제 인형": "ぬいぐるみ",
    "인형": "ぬいぐるみ",
    "마스코트": "マスコット",
    "아크릴 키링": "アクリルキーホルダー",
    "키링": "キーホルダー",
    "클리어 파일": "クリアファイル",
    "문구": "クリアファイル",
    "캔뱃지": "缶バッジ",
    "뱃지": "缶バッジ",
    "아크릴 스탠드": "アクリルスタンド",
    "머그컵": "マグカップ",
    "피규어": "フィギュア",
}

KOREAN_CHARACTER_JA_QUERY = {
    "탄지로": "竈門炭治郎",
    "카마도 탄지로": "竈門炭治郎",
    "네즈코": "竈門禰豆子",
    "카마도 네즈코": "竈門禰豆子",
    "토니토니 쵸파": "チョッパー",
    "쵸파": "チョッパー",
    "루피": "ルフィ",
    "고죠 사토루": "五条悟",
    "고죠": "五条悟",
    "미도리야 이즈쿠": "緑谷出久",
    "데쿠": "緑谷出久",
    "바쿠고 카츠키": "爆豪勝己",
    "바쿠고": "爆豪勝己",
    "토도로키 쇼토": "轟焦凍",
    "토도로키": "轟焦凍",
    "토가 히미코": "トガヒミコ",
    "올마이트": "オールマイト",
    "아냐 포저": "アーニャ・フォージャー",
    "아냐": "アーニャ",
    "요르 포저": "ヨル・フォージャー",
    "요르": "ヨル",
    "본드": "ボンド",
    "덴지": "デンジ",
    "파워": "パワー",
    "마키마": "マキマ",
    "포치타": "ポチタ",
    "나루토": "うずまきナルト",
    "사스케": "うちはサスケ",
    "카카시": "はたけカカシ",
    "리코": "リコ",
    "레그": "レグ",
    "나나치": "ナナチ",
    "미티": "ミーティ",
    "모노쿠마": "モノクマ",
    "코마에다": "狛枝凪斗",
    "코마에다 나기토": "狛枝凪斗",
    "히나타 하지메": "日向創",
    "고토 히토리": "後藤ひとり",
    "키타 이쿠요": "喜多郁代",
    "치이카와": "ちいかわ",
    "하치와레": "ハチワレ",
    "우사기": "うさぎ",
    "모몽가": "モモンガ",
    "쿠리만쥬": "栗まんじゅう",
    "미카사": "ミカサ",
    "리바이": "リヴァイ",
    "진": "ジャン",
    "에르빈": "エルヴィン",
    "한지": "ハンジ",
    "멤초": "MEMちょ",
    "B코마치": "B小町",
    "마히토": "真人",
    "쿠도 신이치": "工藤新一",
    "모리 란": "毛利蘭",
    "모리 코고로": "毛利小五郎",
    "아무로 토오루": "安室透",
    "아카이 슈이치": "赤井秀一",
    "하이바라 아이": "灰原哀",
    "코난": "コナン",
    "고토 히토리": "後藤ひとり",
    "이지치 닛카": "伊地知虹夏",
    "결속밴드": "結束バンド",
    "스즈키 이루마": "鈴木入間",
    "이루마": "入間",
    "아스모데우스 알리": "アスモデウス・アリス",
    "아스모데우스": "アスモデウス・アリス",
    "알리스": "アリス",
    "바빌스 학원": "バビルス",
    "아메리 아자즈": "アメリ",
    "알리": "アリス",
    "불량 트리오": "問題児クラス",
    "아인즈 울 고운": "アインズ・ウール・ゴウン",
    "아인즈": "アインズ",
    "세바스": "セバス",
    "알베도": "アルベド",
    "네코마 고교 랜덤": "音駒高校",
    "마이키": "佐野万次郎",
    "드라켄": "龍宮寺堅",
    "호시노 아이": "星野アイ",
    "카나": "有馬かな",
    "아리마 카나": "有馬かな",
    "아카네": "黒川あかね",
    "쿠로카와 아카네": "黒川あかね",
    "아쿠아": "アクア",
    "루비": "ルビー",
    "오카룽": "オカルン",
    "터보 할머니": "ターボババア",
    "강백호": "桜木花道",
    "서태웅": "流川楓",
    "에도가와 코난": "江戸川コナン",
    "카이토 키드": "怪盗キッド",
    "시로": "シロ",
    "짱구": "野原しんのすけ",
    "도라에몽": "ドラえもん",
    "베니마루": "紅丸",
    "디아블로": "ディアブロ",
    "오카베 린타로": "岡部倫太郎",
    "하시다 이타루": "橋田至",
    "페이리스 NyanNyan": "フェイリス・ニャンニャン",
    "페이리스": "フェイリス・ニャンニャン",
    "우루시바라 루카": "漆原るか",
    "무카이 유즈키": "向井結月",
    "시바 마카토": "柴山誠",
    "사쿠라": "木之本桜",
    "키노모토 사쿠라": "木之本桜",
    "케로짱": "ケルベロス",
    "케로": "ケルベロス",
    "세일러문": "セーラームーン",
    "아야나미 레이": "綾波レイ",
    "소류 아스카 랑글레": "惣流・アスカ・ラングレー",
    "아스카": "アスカ",
    "에드워드": "エドワード",
    "에드워드 엘릭": "エドワード・エルリック",
    "알폰스": "アルフォンス",
    "알폰스 엘릭": "アルフォンス・エルリック",
    "호리 쿄코": "堀京子",
    "미야무라 이즈미": "宮村伊澄",
}

ANIMATE_STORE = "\uc560\ub2c8\uba54\uc774\ud2b8"
ENSKY_STORE = "\uc5d4\uc2a4\uce74\uc774"
GOODSMILE_STORE = "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8"
KOTOBUKIYA_STORE = "\ucf54\ud1a0\ubd80\ud0a4\uc57c"
CHIIKAWA_MARKET_STORE = "\uce58\uc774\uce74\uc640 \ub9c8\ucf13"
NAGANO_MARKET_STORE = "\ub098\uac00\ub178 \ub9c8\ucf13"
CHIIKAWA_MOGUMOGU_STORE = "\uce58\uc774\uce74\uc640 \ubaa8\uad6c\ubaa8\uad6c \ud63c\ud3ec"

STORE_ALIASES.update(
    {
        "animate": ANIMATE_STORE,
        "ensky": ENSKY_STORE,
        "goodsmile": GOODSMILE_STORE,
        "gsc": GOODSMILE_STORE,
        "kotobukiya": KOTOBUKIYA_STORE,
        "chiikawa_market": CHIIKAWA_MARKET_STORE,
        "nagano_market": NAGANO_MARKET_STORE,
        "chiikawa_mogumogu": CHIIKAWA_MOGUMOGU_STORE,
    }
)

STORE_PROVIDERS.update(
    {
        CHIIKAWA_MARKET_STORE: {
            "products_json": "https://chiikawamarket.jp/ko/products.json?limit=250&page={page}",
            "search_url": "https://chiikawamarket.jp/ko/search?q={query}&type=product",
            "sitemap_index": "https://chiikawamarket.jp/sitemap.xml",
        },
        NAGANO_MARKET_STORE: {
            "products_json": "https://nagano-market.jp/ko/products.json?limit=250&page={page}",
            "search_url": "https://nagano-market.jp/ko/search?q={query}&type=product",
            "sitemap_index": "https://nagano-market.jp/sitemap.xml",
        },
        CHIIKAWA_MOGUMOGU_STORE: {
            "products_json": "https://chiikawamogumogu.shop/products.json?limit=250&page={page}",
            "search_url": "https://chiikawamogumogu.shop/search?q={query}&type=product",
            "sitemap_index": "https://chiikawamogumogu.shop/sitemap.xml",
        },
    }
)

SEARCH_PROVIDERS.update(
    {
        ANIMATE_STORE: {
            "search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
        },
        ENSKY_STORE: {
            "search_url": "https://www.enskyshop.com/products/list?name={query}",
        },
        GOODSMILE_STORE: {
            "search_url": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
        },
        KOTOBUKIYA_STORE: {
            "search_url": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
            "base_url": "https://shop.kotobukiya.co.jp",
        },
    }
)

BANPRESTO_TITLE_PAGES = {
    "僕のヒーローアカデミア": "https://bsp-prize.jp/title/IP00002053/",
    "初音ミク": "https://bsp-prize.jp/title/IP00003994/",
    "呪術廻戦": "https://bsp-prize.jp/title/IP00002080/",
    "ブルーロック": "https://bsp-prize.jp/title/IP00003607/",
    "ワンピース": "https://bsp-prize.jp/title/IP00002025/",
    "ドラゴンボール": "https://bsp-prize.jp/title/IP00003375/",
    "SPY×FAMILY": "https://bsp-prize.jp/title/IP00004878/",
    "HUNTER×HUNTER": "https://bsp-prize.jp/title/IP00006048/",
    "NARUTO": "https://bsp-prize.jp/title/IP00006142/",
}

MANUAL_OVERRIDES = {
    "치이카와 메테오 마스코트 (우사기)": "https://chiikawamarket.jp/cdn/shop/files/4571609364726_1.jpg?v=1750074581",
    "치이카와 메테오 마스코트 (하치와레)": "https://chiikawamarket.jp/cdn/shop/files/4571609364719_1.jpg?v=1750074566",
    "치이카와 메테오 마스코트 (치이카와)": "https://chiikawamarket.jp/cdn/shop/files/4571609364702_1.jpg?v=1750074551",
    "치이카와 숲의 토벌 창 마스코트 (하치와레 동봉)": "https://chiikawamarket.jp/cdn/shop/products/000000000954_1.jpg?v=1655033782",
    "치이카와 츤 마스코트 (하치와레)": "https://chiikawamarket.jp/cdn/shop/products/000000000274_1.jpg?v=1655033007",
}


IMG_RE = re.compile(
    r'<img[^>]+src="([^"]+)"[^>]+alt="([^"]*)"',
    re.IGNORECASE,
)
OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError(f"Unable to fetch: {url}")


def _fetch_json(url: str, timeout: int = 20) -> dict:
    return json.loads(_fetch_text(url, timeout=timeout))


def _normalize(text: str | None) -> str:
    value = unicodedata.normalize("NFKC", (text or "").strip().lower())
    value = (
        value.replace("（", "(")
        .replace("）", ")")
        .replace("[", "(")
        .replace("]", ")")
        .replace("’", "'")
        .replace("…", "")
        .replace("·", " ")
    )
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _squash(text: str | None) -> str:
    return re.sub(r"[\s\-\u3000=/／*＊()（）\[\]{}【】「」『』<>〈〉《》=＝!！・･]", "", _normalize(text))


def _tokens(text: str | None) -> list[str]:
    return [
        token
        for token in re.split(r"[\s()（）/_:,=／＊【】「」『』<>〈〉《》=＝!！・･]+", _normalize(text))
        if token and len(token) >= 2
    ]


def _search_query_variants(query: str) -> list[str]:
    variants = [query]
    compact = re.sub(r"\s+", " ", query or "").strip()
    if not compact:
        return []
    cleaned = re.sub(r"(?i)\bver\.?\b", "", compact)
    cleaned = re.sub(r"(?i)\bfigure\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned and cleaned not in variants:
        variants.append(cleaned)

    year_match = re.search(r"(20\d{2})", compact)
    if "桜ミク" in compact and year_match:
        variants.append(f"桜ミク {year_match.group(1)}")
    if "初音ミク" in compact:
        if "ぬーどるストッパー" in compact:
            variants.append("ぬーどるストッパーフィギュア 初音ミク")
        if "Trio-Try-iT" in compact:
            variants.append("Trio-Try-iT 初音ミク")
        if "BiCute" in compact:
            variants.append("BiCute 初音ミク")
    if "Desktop Cute" in compact and "初音ミク" in compact:
        variants.append("Desktop Cute 初音ミク")

    out: list[str] = []
    seen: set[str] = set()
    for item in variants:
        key = _squash(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _score(query: str, candidate: str) -> tuple[int, float]:
    q_tokens = [t for t in _tokens(query) if t not in {"치이카와", "nagano", "characters"}]
    c_tokens = set(_tokens(candidate))
    overlap = sum(1 for token in q_tokens if token in c_tokens)
    q_squash = _squash(query)
    c_squash = _squash(candidate)
    if not q_squash or not c_squash:
        return overlap, 0.0
    prefix_bonus = 0.12 if q_squash in c_squash or c_squash in q_squash else 0.0
    common = len(set(q_squash) & set(c_squash)) / max(len(set(q_squash)), 1)
    return overlap, min(common + prefix_bonus, 1.0)


def _distinctive_query_tokens(query: str) -> list[str]:
    normalized = _normalize(query)
    normalized = re.sub(r"(?i)\bver\.?\b", " ", normalized)
    raw_tokens = _tokens(normalized)
    common = {
        "初音ミク",
        "フィギュア",
        "ぬーどるストッパーフィギュア",
        "ぬーどるストッパー",
        "trio-try-it",
        "figure",
        "bicute",
        "desktop",
        "cute",
        "collection",
        "コレクション",
    }
    out: list[str] = []
    for token in raw_tokens:
        cleaned = re.sub(r"(?i)ver\.?$", "", token).strip()
        if not cleaned or cleaned in common or len(cleaned) < 2:
            continue
        out.append(cleaned)
    return out


DISTINCTIVE_TOKEN_ALIASES = {
    "転スラ": ("転生したらスライムだった件",),
}


def _candidate_matches_distinctive_token(token: str, candidate_tokens: set[str], candidate_key: str) -> bool:
    token_key = _squash(token)
    if not token_key:
        return True
    if token_key in candidate_tokens:
        return True
    if len(token_key) >= 4 and token_key in candidate_key:
        return True
    for alias in DISTINCTIVE_TOKEN_ALIASES.get(token, ()):
        alias_key = _squash(alias)
        if not alias_key:
            continue
        if alias_key in candidate_tokens:
            return True
        if len(alias_key) >= 4 and alias_key in candidate_key:
            return True
    return False


def _has_distinctive_token_match(query: str, candidate: str) -> bool:
    tokens = _distinctive_query_tokens(query)
    if not tokens:
        return True
    candidate_tokens = {_squash(token) for token in _tokens(candidate)}
    candidate_key = _squash(candidate)
    for token in tokens:
        if _candidate_matches_distinctive_token(token, candidate_tokens, candidate_key):
            return True
    return False


def _has_all_distinctive_token_matches(query: str, candidate: str) -> bool:
    tokens = _distinctive_query_tokens(query)
    if not tokens:
        return True
    candidate_tokens = {_squash(token) for token in _tokens(candidate)}
    candidate_key = _squash(candidate)
    for token in tokens:
        if not _candidate_matches_distinctive_token(token, candidate_tokens, candidate_key):
            return False
    return True


def _parenthetical_terms_match(query: str, candidate: str) -> bool:
    terms = [term.strip() for term in re.findall(r"\(([^)]+)\)", query or "") if term.strip()]
    if not terms:
        return True
    candidate_tokens = {_squash(token) for token in _tokens(candidate)}
    candidate_key = _squash(candidate)
    for term in terms:
        term_key = _squash(term)
        if not term_key:
            continue
        if term_key in candidate_tokens:
            continue
        if len(term_key) >= 4 and term_key in candidate_key:
            continue
        return False
    return True


GOODS_TYPE_SIGNAL_GROUPS = (
    ("acrylic_stand", ("アクリルスタンド", "アクスタ", "acrylic stand", "아크릴 스탠드")),
    ("acrylic_keychain", ("アクリルキーホルダー", "アクリルチャーム", "아크릴 키링", "아크릴 키홀더")),
    ("rubber_strap", ("ラバーストラップ", "ラバスト", "러버 스트랩")),
    ("keychain", ("キーホルダー", "キーリング", "チャーム", "키링", "키홀더")),
    ("badge", ("缶バッジ", "カンバッジ", "can badge", "캔뱃지", "뱃지")),
    ("plush", ("ぬいぐるみ", "マスコット", "mascot", "인형", "마스코트")),
    ("card", ("カード", "card", "포토카드", "트레이딩 카드")),
    ("file", ("クリアファイル", "clear file", "클리어파일")),
    ("mug", ("マグカップ", "mug", "머그컵")),
    ("towel", ("タオル", "towel", "타올", "수건")),
    ("sticker", ("ステッカー", "sticker", "스티커")),
    ("figure", ("フィギュア", "figure", "피규어")),
)


def _goods_type_signals(value: str | None) -> set[str]:
    normalized = _normalize(value)
    squashed = _squash(value)
    signals: set[str] = set()
    for group, tokens in GOODS_TYPE_SIGNAL_GROUPS:
        for token in tokens:
            token_normalized = _normalize(token)
            token_squashed = _squash(token)
            if (token_normalized and token_normalized in normalized) or (
                token_squashed and token_squashed in squashed
            ):
                signals.add(group)
                break
    return signals


def _has_goods_type_compatibility(query: str, candidate: str) -> bool:
    query_signals = _goods_type_signals(query)
    if not query_signals:
        return True
    candidate_signals = _goods_type_signals(candidate)
    return bool(query_signals & candidate_signals)


def _is_high_confidence_product_detail_match(query: str, item: ProductImage, score: tuple[int, float]) -> bool:
    return (
        score[0] >= 3
        and score[1] >= 0.9
        and _has_goods_type_compatibility(query, item.title)
        and _has_all_distinctive_token_matches(query, item.title)
        and _parenthetical_terms_match(query, item.title)
        and is_product_specific_source_url(item.source_url)
        and is_safe_source_image_pair(item.source_url, item.image_url)
    )


def _canonical_image_url(url: str) -> str:
    normalized = html.unescape(url.strip())
    if normalized.startswith("//"):
        normalized = f"https:{normalized}"
    return normalized


def _absolute_url(url: str, base_url: str) -> str:
    normalized = html.unescape(url.strip())
    if normalized.startswith("//"):
        return f"https:{normalized}"
    return urllib.parse.urljoin(base_url, normalized)


def _looks_like_valid_image(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _image_from_source_url(url: str | None) -> str | None:
    if not url or not is_product_specific_source_url(url):
        return None
    try:
        text = _fetch_text(url, timeout=20)
    except Exception:
        return None
    match = OG_IMAGE_RE.search(text)
    if not match:
        return None
    image_url = _canonical_image_url(match.group(1))
    return image_url if is_safe_source_image_pair(url, image_url) else None


def _furyu_release_date(item: dict[str, object]) -> str | None:
    raw = str(item.get("release_month") or "").strip()
    match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月", raw)
    if not match:
        return None
    return f"{match.group(1)}-{int(match.group(2)):02d}"


@dataclass
class ProductImage:
    title: str
    image_url: str
    source_url: str | None = None
    release_date: str | None = None


class ShopifyProvider:
    def __init__(
        self,
        store_name: str,
        products_json: str,
        search_url: str,
        sitemap_index: str | None = None,
    ) -> None:
        self.store_name = store_name
        self.products_json = products_json
        self.search_url = search_url
        self.sitemap_index = sitemap_index
        self._products: list[ProductImage] | None = None
        self._sitemap_products: list[ProductImage] | None = None
        self.cache_dir = DEFAULT_CACHE_DIR

    def product_url_for_handle(self, handle: str) -> str | None:
        handle = str(handle or "").strip()
        if not handle:
            return None
        parsed = urllib.parse.urlsplit(self.products_json.format(page=1))
        base_path = parsed.path.split("/products.json", 1)[0]
        path = f"{base_path}/products/{urllib.parse.quote(handle)}"
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

    def products(self) -> list[ProductImage]:
        if self._products is not None:
            return self._products
        products: list[ProductImage] = []
        page = 1
        while True:
            payload = _fetch_json(self.products_json.format(page=page))
            rows = payload.get("products", [])
            if not rows:
                break
            for row in rows:
                images = row.get("images") or []
                src = None
                if images:
                    src = images[0].get("src")
                if not _looks_like_valid_image(src):
                    continue
                title = str(row.get("title") or "").strip()
                if not title:
                    continue
                products.append(
                    ProductImage(
                        title=title,
                        image_url=str(src),
                        source_url=self.product_url_for_handle(str(row.get("handle") or "")),
                    )
                )
            page += 1
            time.sleep(0.05)
        self._products = products
        return products

    def sitemap_products(self) -> list[ProductImage]:
        if self._sitemap_products is not None:
            return self._sitemap_products
        if not self.sitemap_index:
            self._sitemap_products = []
            return self._sitemap_products

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / f"{_squash(self.store_name)}_sitemap_index.json"
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                self._sitemap_products = [
                    ProductImage(title=str(item["title"]), image_url=str(item["image_url"]), source_url=item.get("source_url"))
                    for item in cached
                    if item.get("title") and item.get("image_url")
                ]
                if self._sitemap_products:
                    return self._sitemap_products
            except Exception:
                pass

        product_urls = self._product_urls_from_sitemap_index()
        products = self._resolve_product_titles(product_urls)
        cache_path.write_text(
            json.dumps(
                [{"title": item.title, "image_url": item.image_url, "source_url": item.source_url} for item in products],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._sitemap_products = products
        return products

    def _product_urls_from_sitemap_index(self) -> list[tuple[str, str]]:
        index_text = _fetch_text(self.sitemap_index)
        sitemap_urls = re.findall(r"<loc>([^<]+sitemap_products_[^<]+)</loc>", index_text)
        localized = [url for url in sitemap_urls if "/ko/" in url]
        if localized:
            sitemap_urls = localized
        pairs: list[tuple[str, str]] = []
        for sitemap_url in sitemap_urls:
            sitemap_url = html.unescape(sitemap_url)
            xml_text = _fetch_text(sitemap_url)
            root = ET.fromstring(xml_text)
            ns = {
                "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "img": "http://www.google.com/schemas/sitemap-image/1.1",
            }
            for url_node in root.findall("sm:url", ns):
                loc = url_node.findtext("sm:loc", default="", namespaces=ns).strip()
                image_loc = url_node.findtext("img:image/img:loc", default="", namespaces=ns).strip()
                if "/products/" not in loc or not image_loc:
                    continue
                pairs.append((loc, image_loc))
        return pairs

    def _resolve_product_titles(self, product_urls: list[tuple[str, str]]) -> list[ProductImage]:
        def fetch_one(pair: tuple[str, str]) -> ProductImage | None:
            product_url, image_url = pair
            js_url = f"{product_url}.js"
            try:
                payload = _fetch_json(js_url, timeout=20)
            except Exception:
                return None
            title = str(payload.get("title") or "").strip()
            if not title:
                return None
            return ProductImage(title=title, image_url=image_url, source_url=product_url)

        products: list[ProductImage] = []
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(fetch_one, pair) for pair in product_urls]
            for future in as_completed(futures):
                item = future.result()
                if item is not None:
                    products.append(item)
        return products

    def search_images(self, query: str) -> list[ProductImage]:
        url = self.search_url.format(query=urllib.parse.quote(query))
        text = _fetch_text(url)
        results: list[ProductImage] = []
        for src, alt in IMG_RE.findall(text):
            alt = html.unescape(alt).strip()
            if not alt:
                continue
            if "치이카와" not in alt and "Nagano Characters" not in alt:
                continue
            image_url = _canonical_image_url(src)
            results.append(ProductImage(title=alt, image_url=image_url))
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = list(self.products())
        sitemap_candidates = self.sitemap_products()
        if sitemap_candidates:
            seen = {_squash(item.title) for item in candidates}
            for item in sitemap_candidates:
                if _squash(item.title) not in seen:
                    candidates.append(item)
        scored = [
            (_score(query, product.title), product)
            for product in candidates
        ]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        if scored:
            best_score, best_product = scored[0]
            second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
            if (
                best_score[0] >= 3
                and best_score[1] >= 0.72
                and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.08)
            ):
                return best_product
            if (
                best_score[0] >= 2
                and best_score[1] >= 0.86
                and best_score[1] - second_score[1] >= 0.1
            ):
                return best_product

        search_candidates = self.search_images(query)
        if not search_candidates:
            return None
        exact = [item for item in search_candidates if _squash(item.title) == _squash(query)]
        if exact:
            return exact[0]
        scored_search = [
            (_score(query, item.title), item)
            for item in search_candidates
        ]
        scored_search.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_product = scored_search[0]
        second_score = scored_search[1][0] if len(scored_search) > 1 else (0, 0.0)
        if (
            best_score[0] >= 2
            and best_score[1] >= 0.74
            and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.08)
        ):
            return best_product
        return None


class SearchPageProvider:
    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        time.sleep(0.4)
        results: list[ProductImage] = []
        cards = re.findall(
            r'<a href="(https://www\.enskyshop\.com/products/detail/\d+)">\s*'
            r'<picture>\s*<source srcset="([^"]+)"[^>]*>\s*<img src="[^"]*" alt="([^"]+)">',
            text,
            re.IGNORECASE | re.DOTALL,
        )
        for source_url, image_url, title in cards:
            if not image_url or not title:
                continue
            results.append(
                ProductImage(
                    title=html.unescape(title).strip(),
                    image_url=_canonical_image_url(f"https://www.enskyshop.com{image_url}"),
                    source_url=source_url,
                )
            )
        shelf_cards = re.findall(
            r'<li class="ec-shelfGrid__item">(?P<body>.*?)</li>',
            text,
            re.IGNORECASE | re.DOTALL,
        )
        for body in shelf_cards:
            href_match = re.search(
                r'<a href="(https://www\.enskyshop\.com/products/detail/\d+)"',
                body,
                re.IGNORECASE,
            )
            image_match = re.search(r'<img src="([^"]+)"', body, re.IGNORECASE)
            title_match = re.search(
                r'<p class="ec-shelfGrid__item-name">\s*<a[^>]*>(.*?)</a>',
                body,
                re.IGNORECASE | re.DOTALL,
            )
            if not href_match or not image_match or not title_match:
                continue
            title = html.unescape(re.sub(r"<[^>]+>", " ", title_match.group(1)))
            title = re.sub(r"\s+", " ", title).strip()
            image_url = _canonical_image_url(f"https://www.enskyshop.com{image_match.group(1)}")
            if not title or not _looks_like_valid_image(image_url):
                continue
            results.append(
                ProductImage(
                    title=title,
                    image_url=image_url,
                    source_url=href_match.group(1),
                )
            )
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        if not _has_goods_type_compatibility(query, best_item.title):
            return None
        if (
            best_score[0] >= 2
            and best_score[1] >= 0.72
            and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.08)
        ):
            return best_item
        return None


class AnimateSearchProvider:
    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        time.sleep(0.35)
        cards = re.findall(
            r'<div class="item_list_thumb">\s*<a href="([^"]+)">\s*'
            r'<img src="([^"]+)"[^>]+title=[\'"]([^\'"]+)[\'"][^>]*>\s*</a>\s*</div>\s*'
            r'<h3>\s*<a href="([^"]+)" title=[\'"]([^\'"]+)[\'"]>(.*?)</a>\s*</h3>',
            text,
            re.IGNORECASE | re.DOTALL,
        )
        results: list[ProductImage] = []
        for thumb_href, image_url, image_title, link_href, link_title, body_title in cards:
            title = html.unescape(link_title or image_title or re.sub(r"<[^>]+>", "", body_title)).strip()
            if not title or not image_url:
                continue
            source_url = html.unescape(link_href or thumb_href).strip()
            if source_url.startswith("/"):
                source_url = "https://www.animate-onlineshop.jp" + source_url
            results.append(
                ProductImage(
                    title=title,
                    image_url=_canonical_image_url(image_url),
                    source_url=source_url if source_url.startswith(("http://", "https://")) else None,
                )
            )
        if results:
            self._query_cache[query] = results
            return results

        item_list_match = re.search(r'<div class="item_list">(.*?)</div>\s*</div>\s*</div>', text, re.IGNORECASE | re.DOTALL)
        search_area = item_list_match.group(1) if item_list_match else text
        for item_html in re.findall(r"<li\b[^>]*>(.*?)</li>", search_area, re.IGNORECASE | re.DOTALL):
            thumb_match = re.search(r'<div class="item_list_thumb".*?</div>', item_html, re.IGNORECASE | re.DOTALL)
            title_match = re.search(r"<h3>\s*<a\b([^>]*)>(.*?)</a>\s*</h3>", item_html, re.IGNORECASE | re.DOTALL)
            if not thumb_match or not title_match:
                continue
            image_match = re.search(r'<img\b[^>]+src=["\']([^"\']+)["\']', thumb_match.group(0), re.IGNORECASE)
            thumb_href_match = re.search(r'<a\b[^>]+href=["\']([^"\']+)["\']', thumb_match.group(0), re.IGNORECASE)
            link_attrs = title_match.group(1)
            link_href_match = re.search(r'href=["\']([^"\']+)["\']', link_attrs, re.IGNORECASE)
            link_title_match = re.search(r'title=["\']([^"\']+)["\']', link_attrs, re.IGNORECASE)
            if not image_match:
                continue
            title = html.unescape(
                (link_title_match.group(1) if link_title_match else re.sub(r"<[^>]+>", " ", title_match.group(2)))
            )
            title = re.sub(r"\s+", " ", title).strip()
            image_url = _canonical_image_url(image_match.group(1))
            if not title or not _looks_like_valid_image(image_url):
                continue
            source_url = None
            href_match = link_href_match or thumb_href_match
            if href_match:
                source_url = _absolute_url(href_match.group(1), "https://www.animate-onlineshop.jp")
            results.append(ProductImage(title=title, image_url=image_url, source_url=source_url))
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        if not _has_goods_type_compatibility(query, best_item.title):
            return None
        if not _has_all_distinctive_token_matches(query, best_item.title):
            return None
        if not _parenthetical_terms_match(query, best_item.title):
            return None
        if (
            best_score[0] >= 2
            and best_score[1] >= 0.68
            and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.06)
        ):
            return best_item
        if _is_high_confidence_product_detail_match(query, best_item, best_score):
            return best_item
        return None


class ImageAltSearchProvider:
    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        time.sleep(0.35)
        results: list[ProductImage] = []
        for tag_match in re.finditer(r"<img\b[^>]*>", text, re.IGNORECASE | re.DOTALL):
            tag = tag_match.group(0)
            src_match = re.search(r'(?:src|data-src)=["\']([^"\']+)["\']', tag, re.IGNORECASE)
            title_match = re.search(r'(?:alt|title)=["\']([^"\']*)["\']', tag, re.IGNORECASE)
            if not src_match or not title_match:
                continue
            image_url = _canonical_image_url(src_match.group(1))
            title = html.unescape(title_match.group(1)).strip()
            lowered = image_url.lower()
            if not title or not _looks_like_valid_image(image_url):
                continue
            if any(part in lowered for part in ("/common/", "/bnr/", "/sldr/", "logo", "icon", "favicon")):
                continue
            results.append(ProductImage(title=title, image_url=image_url))
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        best_squash = _squash(best_item.title)
        query_squash = _squash(query)
        if (
            query_squash
            and best_squash
            and (query_squash in best_squash or best_squash in query_squash)
            and best_score[1] >= 0.92
        ):
            return best_item
        if (
            best_score[0] >= 2
            and best_score[1] >= 0.7
            and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.06)
        ):
            return best_item
        return None


class FuryuApiProvider:
    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        results: list[ProductImage] = []
        seen: set[str] = set()
        for search_query in _search_query_variants(query):
            api_url = "https://furyuprize.com/api/search?keyword={query}&page=1".format(
                query=urllib.parse.quote(search_query)
            )
            try:
                payload = _fetch_json(api_url, timeout=25)
            except Exception:
                continue
            time.sleep(0.35)
            for item in payload.get("items") or []:
                title = str(item.get("name_item") or "").strip()
                image_url = str(item.get("img_item_main") or "").strip()
                code = str(item.get("code") or "").strip()
                if image_url.startswith("/"):
                    image_url = "https://furyuprize.com/files/images" + image_url
                if not title or not code or not _looks_like_valid_image(image_url):
                    continue
                key = code or _squash(title)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    ProductImage(
                        title=title,
                        image_url=image_url,
                        source_url=f"https://furyuprize.com/item/{code}",
                        release_date=_furyu_release_date(item),
                    )
                )
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        query_key = _squash(query)
        best_key = _squash(best_item.title)
        if not _has_distinctive_token_match(query, best_item.title):
            return None
        if query_key and best_key and query_key in best_key and best_score[1] >= 0.82:
            return best_item
        if (
            best_score[0] >= 2
            and best_score[1] >= 0.78
            and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.1)
        ):
            return best_item
        if (
            len(scored) == 1
            and best_score[1] >= 0.7
            and _has_goods_type_compatibility(query, best_item.title)
            and is_product_specific_source_url(best_item.source_url)
            and is_safe_source_image_pair(best_item.source_url, best_item.image_url)
        ):
            return best_item
        return None


class GoodSmileInfoProvider:
    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}

    def _search_new_site_images(self, query: str) -> list[ProductImage]:
        filter_payload = json.dumps({"search_keyword": query}, ensure_ascii=False)
        params = urllib.parse.urlencode(
            {
                "filter": filter_payload,
                "orderBy": "1",
                "limit": "20",
                "offset": "0",
                "couponId": "",
                "searchIndex": "-1",
            }
        )
        url = f"https://www.goodsmile.com/ja/search/list?{params}"
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            return []
        results: list[ProductImage] = []
        blocks = re.findall(
            r'<div class="p-product-list__item">(.*?)</a>\s*</div>',
            text,
            re.IGNORECASE | re.DOTALL,
        )
        for block in blocks:
            href_match = re.search(r'<a[^>]+href=["\']([^"\']*/ja/product/\d+[^"\']*)["\']', block, re.IGNORECASE)
            image_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.IGNORECASE)
            if href_match is None or image_match is None:
                continue
            title_text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", block))).strip()
            title_text = re.sub(r"^\d+\s+", "", title_text)
            title_text = re.sub(r"\s*￥[0-9,]+.*$", "", title_text).strip()
            title_text = re.sub(r"^(?:特典付き|再販|新商品|予約受付中)\s+", "", title_text).strip()
            source_url = _absolute_url(href_match.group(1), "https://www.goodsmile.com")
            image_url = _canonical_image_url(_absolute_url(image_match.group(1), "https://www.goodsmile.com"))
            if title_text and _looks_like_valid_image(image_url):
                results.append(ProductImage(title=title_text, image_url=image_url, source_url=source_url))
        return results

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        time.sleep(0.35)
        blocks = re.findall(
            r'<div\s+class=["\'][^"\']*\bhitItem\b[^"\']*["\']>\s*'
            r'<div\s+class=["\'][^"\']*\bhitBox\b[^"\']*["\']>(.*?)</div>\s*</div>',
            text,
            re.IGNORECASE | re.DOTALL,
        )
        results: list[ProductImage] = []
        for block in blocks:
            href_match = re.search(r'<a[^>]+href=["\']([^"\']*(?:/ja)?/product/[^"\']+)["\']', block, re.IGNORECASE)
            image_match = re.search(
                r'<img[^>]+data-original=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*\bitemImg\b',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if image_match is None:
                image_match = re.search(
                    r'<img[^>]+class=["\'][^"\']*\bitemImg\b[^>]+data-original=["\']([^"\']+)["\']',
                    block,
                    re.IGNORECASE | re.DOTALL,
                )
            title_match = re.search(
                r'<span class="hitTtl">\s*<span>(.*?)</span>\s*</span>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if image_match is None or title_match is None:
                continue
            title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title_match.group(1)))).strip()
            image_url = _canonical_image_url(image_match.group(1))
            source_url = _absolute_url(href_match.group(1), "https://www.goodsmile.info") if href_match else None
            if title and _looks_like_valid_image(image_url):
                if source_url:
                    detail_image = _image_from_source_url(source_url)
                    if detail_image:
                        image_url = detail_image
                results.append(ProductImage(title=title, image_url=image_url, source_url=source_url))
        seen_sources = {str(item.source_url or "") for item in results if item.source_url}
        for item in self._search_new_site_images(query):
            source_key = str(item.source_url or "")
            if source_key and source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            results.append(item)
        results = _filter_goodsmile_search_results(query, results)
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        query_key = _squash(query)
        best_key = _squash(best_item.title)
        if query_key and best_key and query_key == best_key:
            return best_item
        return None


class TaitoApiProvider:
    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}
        self._session: requests.Session | None = None

    def _fetch_payload(self, url: str) -> object:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,text/plain,*/*",
                }
            )
            self._session.get("https://www.taito.co.jp/prize", timeout=25)
        response = self._session.get(
            url,
            headers={
                "Referer": "https://www.taito.co.jp/prize",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=25,
        )
        response.raise_for_status()
        return response.json()

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            payload = self._fetch_payload(url)
        except Exception:
            self._query_cache[query] = []
            return []
        time.sleep(0.35)
        raw_items: object
        if isinstance(payload, dict):
            raw_items = payload.get("data") or payload.get("items") or payload.get("Products") or payload
        else:
            raw_items = payload
        if isinstance(raw_items, dict):
            for key in ("ProductList", "list", "results"):
                if isinstance(raw_items.get(key), list):
                    raw_items = raw_items[key]
                    break
        results: list[ProductImage] = []
        if not isinstance(raw_items, list):
            self._query_cache[query] = []
            return []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            base_data = item.get("BaseShoppingProductData")
            if not isinstance(base_data, dict):
                base_data = {}
            title = str(
                item.get("ProductName")
                or base_data.get("ProductName")
                or item.get("Name")
                or item.get("name")
                or item.get("Title")
                or ""
            ).strip()
            product_id = str(
                item.get("ProductID") or base_data.get("ProductID") or item.get("Id") or item.get("id") or ""
            ).strip()
            image_path = str(item.get("ImagePath") or base_data.get("ImagePath") or item.get("imagePath") or "").strip()
            image_name = str(
                item.get("ImageName01") or base_data.get("ImageName01") or item.get("ImageName") or item.get("image") or ""
            ).strip()
            if image_path and not image_path.startswith(("http://", "https://", "//", "/")):
                image_path = f"https://{image_path}"
            image_url = _absolute_url(image_path + image_name, "https://www.taito.co.jp") if image_path or image_name else ""
            if not title or not product_id or not _looks_like_valid_image(image_url):
                continue
            results.append(
                ProductImage(
                    title=title,
                    image_url=image_url,
                    source_url=f"https://www.taito.co.jp/prize/item/{product_id}",
                )
            )
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        query_key = _squash(query)
        best_key = _squash(best_item.title)
        if query_key and best_key and (query_key == best_key or query_key in best_key) and best_score[1] >= 0.86:
            return best_item
        return None


class BanprestoSearchProvider:
    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}
        self._title_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        time.sleep(0.35)
        results: list[ProductImage] = []
        for block in _banpresto_product_blocks(text):
            href_match = re.search(r'<a[^>]+href=["\']([^"\']*/item/[^"\']+)["\']', block, re.I)
            name_match = re.search(r'<[^>]+class=["\'][^"\']*products_name[^"\']*["\'][^>]*>(.*?)</', block, re.I | re.S)
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.I)
            if not href_match or not name_match or not img_match:
                continue
            title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", name_match.group(1)))).strip()
            source_url = _absolute_url(href_match.group(1), "https://bsp-prize.jp")
            image_url = _absolute_url(img_match.group(1), "https://bsp-prize.jp")
            if title and _looks_like_valid_image(image_url):
                results.append(ProductImage(title=title, image_url=image_url, source_url=source_url))
        self._query_cache[query] = results
        return results

    def title_page_products(self, query: str) -> list[ProductImage]:
        title_url = _banpresto_title_url_for_query(query)
        if not title_url:
            return []
        if title_url in self._title_cache:
            return self._title_cache[title_url]

        products: list[ProductImage] = []
        seen_urls: set[str] = set()
        page_url = title_url
        for _ in range(6):
            try:
                text = _fetch_text(page_url, timeout=25)
            except Exception:
                break
            for block in _banpresto_product_blocks(text):
                href_match = re.search(r'<a[^>]+href=["\']([^"\']*/item/[^"\']+)["\']', block, re.I)
                name_match = re.search(r'<[^>]+class=["\'][^"\']*products_name[^"\']*["\'][^>]*>(.*?)</', block, re.I | re.S)
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.I)
                if not href_match or not name_match or not img_match:
                    continue
                source_url = _absolute_url(html.unescape(href_match.group(1)), "https://bsp-prize.jp")
                if source_url in seen_urls:
                    continue
                seen_urls.add(source_url)
                title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", name_match.group(1)))).strip()
                image_url = _absolute_url(html.unescape(img_match.group(1)), "https://bsp-prize.jp")
                if title and _looks_like_valid_image(image_url):
                    products.append(ProductImage(title=title, image_url=image_url, source_url=source_url))
            next_match = re.search(
                r'<li[^>]+class=["\'][^"\']*pager_next[^"\']*["\'][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\']',
                text,
                re.I | re.S,
            )
            if not next_match:
                break
            page_url = _absolute_url(html.unescape(next_match.group(1)), "https://bsp-prize.jp")
            time.sleep(0.15)
        self._title_cache[title_url] = products
        return products

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query) + self.title_page_products(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        query_key = _squash(query)
        best_key = _squash(best_item.title)
        if query_key and best_key and query_key == best_key:
            detail_image = _image_from_source_url(best_item.source_url)
            if detail_image:
                best_item = ProductImage(title=best_item.title, image_url=detail_image, source_url=best_item.source_url)
            return best_item
        if best_score[0] >= 3 and best_score[1] >= 0.88 and best_score[1] - second_score[1] >= 0.12:
            detail_image = _image_from_source_url(best_item.source_url)
            if detail_image:
                best_item = ProductImage(title=best_item.title, image_url=detail_image, source_url=best_item.source_url)
            return best_item
        return None


def _banpresto_product_blocks(text: str) -> list[str]:
    return re.findall(
        r'<(?:div|li)[^>]+class=["\'][^"\']*products_item[^"\']*["\'][^>]*>(.*?)(?:</div><!-- /\.\s*products_item -->|</li>)',
        text,
        re.I | re.S,
    )


def _banpresto_title_url_for_query(query: str) -> str | None:
    for token, url in BANPRESTO_TITLE_PAGES.items():
        if token in query:
            return url
    return None


class SegaPlazaProvider:
    _catalog_cache: list[ProductImage] | None = None

    def __init__(self, store_name: str, search_url: str) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self._query_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        results = self._search_static_catalog(query, text)
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        title_key = self._normalized_key(best_item.title)
        query_terms = self._distinctive_query_terms(query)
        line_terms = self._required_line_terms(query)
        if (
            best_item.source_url
            and best_item.image_url
            and all(term in title_key for term in query_terms)
            and all(term in title_key for term in line_terms)
            and best_score[1] >= 0.7
            and (len(scored) == 1 or best_score[1] - second_score[1] >= 0.08 or best_score[0] > second_score[0])
        ):
            return best_item
        return None

    def _search_static_catalog(self, query: str, search_html: str) -> list[ProductImage]:
        catalog = self._load_static_catalog(search_html)
        required_terms = self._distinctive_query_terms(query)
        required_line_terms = self._required_line_terms(query)
        scored: list[tuple[tuple[int, float], ProductImage]] = []
        for item in catalog:
            title_key = self._normalized_key(item.title)
            if required_line_terms and not all(term in title_key for term in required_line_terms):
                continue
            if required_terms and not all(term in title_key for term in required_terms):
                continue
            score = _score(query, item.title)
            if score[0] >= 1 or score[1] >= 0.45:
                scored.append((score, item))
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        return [item for _, item in scored[:30]]

    def _load_static_catalog(self, search_html: str) -> list[ProductImage]:
        if SegaPlazaProvider._catalog_cache is not None:
            return SegaPlazaProvider._catalog_cache
        script_refs = re.findall(r'(?:src|href)=["\']([^"\']+\.js)["\']', search_html, re.I)
        product_scripts: list[str] = []
        image_scripts: list[str] = []
        for script_ref in dict.fromkeys(script_refs):
            script_url = _absolute_url(script_ref, "https://segaplaza.jp")
            try:
                script_text = _fetch_text(script_url, timeout=25)
            except Exception:
                continue
            if 'prizeId:"' in script_text:
                product_scripts.append(script_text)
            if "/images-v2/" in script_text and "prize:" in script_text:
                image_scripts.append(script_text)

        image_map: dict[str, tuple[str, int]] = {}
        for script_text in image_scripts:
            image_map.update(self._parse_image_map(script_text))

        catalog: list[ProductImage] = []
        seen: set[str] = set()
        for script_text in product_scripts:
            for item in self._parse_product_items(script_text, image_map):
                source_url = str(item.source_url or "")
                if source_url in seen:
                    continue
                seen.add(source_url)
                catalog.append(item)
        SegaPlazaProvider._catalog_cache = catalog
        return catalog

    @staticmethod
    def _parse_image_map(script_text: str) -> dict[str, tuple[str, int]]:
        variables = {
            match.group(1): (match.group(2), int(match.group(3)))
            for match in re.finditer(r'([A-Za-z_$][\w$]*)=\["([0-9a-f]{6})",(\d+)\]', script_text)
        }
        out: dict[str, tuple[str, int]] = {}
        for match in re.finditer(r'(?<![\w$])(D\d{6}):([A-Za-z_$][\w$]*)', script_text):
            image_info = variables.get(match.group(2))
            if image_info:
                out[match.group(1)] = image_info
        return out

    @staticmethod
    def _parse_product_items(script_text: str, image_map: dict[str, tuple[str, int]]) -> list[ProductImage]:
        out: list[ProductImage] = []
        product_re = re.compile(
            r'[A-Za-z_$][\w$]*=\{prizeId:"(D\d{6})",(.*?)(?=\},[A-Za-z_$][\w$]*=\{prizeId:|\};|\},[A-Za-z_$][\w$]*=\[)',
            re.S,
        )
        for match in product_re.finditer(script_text):
            prize_id = match.group(1)
            body = match.group(2)
            title = SegaPlazaProvider._js_string_field(body, "name")
            if not title:
                continue
            image_info = image_map.get(prize_id)
            image_url = ""
            if image_info:
                image_hash, _count = image_info
                image_url = f"https://segaplaza.jp/images-v2/prize/{prize_id}_{image_hash}/large/{prize_id}_01.webp"
            out.append(
                ProductImage(
                    title=title,
                    image_url=image_url,
                    source_url=f"https://segaplaza.jp/prize/{prize_id}/",
                    release_date=SegaPlazaProvider._js_string_field(body, "releaseDate") or None,
                )
            )
        return out

    @staticmethod
    def _js_string_field(body: str, field: str) -> str:
        match = re.search(rf'{re.escape(field)}:"((?:\\.|[^"\\])*)"', body)
        if not match:
            return ""
        raw = match.group(1)
        try:
            return str(json.loads(f'"{raw}"'))
        except Exception:
            return raw

    @staticmethod
    def _normalized_key(value: str) -> str:
        return unicodedata.normalize("NFKC", value or "").casefold()

    @staticmethod
    def _required_line_terms(query: str) -> list[str]:
        normalized = SegaPlazaProvider._normalized_key(query)
        if "ちょこのせ" in normalized or "chokonose" in normalized:
            return ["ちょこのせ"]
        return []

    @staticmethod
    def _distinctive_query_terms(query: str) -> list[str]:
        normalized = SegaPlazaProvider._normalized_key(query)
        common = (
            "ちょこのせ",
            "プレミアムフィギュア",
            "プレミアム",
            "フィギュア",
            "chokonose",
            "premium",
            "figure",
        )
        terms: list[str] = []
        for raw_term in re.findall(r"[0-9a-z]+|[\u3040-\u30ff]+|[\u3400-\u9fff]+", normalized):
            term = raw_term
            for common_term in common:
                term = term.replace(common_term, "")
            term = term.strip()
            if len(term) >= 2:
                terms.append(term)
        return terms


class GoodsSearchDetailProvider:
    def __init__(self, store_name: str, search_url: str, base_url: str, max_detail_urls: int = 10) -> None:
        self.store_name = store_name
        self.search_url = search_url
        self.base_url = base_url
        self.max_detail_urls = max_detail_urls
        self._query_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        detail_urls = []
        for href in re.findall(r'href=["\']([^"\']*/shop/g/g[^"\']+)["\']', text, re.I):
            source_url = _absolute_url(href, self.base_url)
            if source_url not in detail_urls:
                detail_urls.append(source_url)
        results: list[ProductImage] = []
        for source_url in detail_urls[: self.max_detail_urls]:
            try:
                detail = _fetch_text(source_url, timeout=20)
            except Exception:
                continue
            title_match = (
                re.search(r'<h1[^>]+class=["\'][^"\']*(?:goods_name_|block-goods-name--text)[^"\']*["\'][^>]*>(.*?)</h1>', detail, re.I | re.S)
                or re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', detail, re.I)
            )
            image_match = (
                re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', detail, re.I)
                or re.search(r'<img[^>]+src=["\']([^"\']*/img/goods/L/[^"\']+)["\']', detail, re.I)
                or re.search(r'<img[^>]+srcset=["\']([^"\']+)["\']', detail, re.I)
            )
            if not title_match or not image_match:
                continue
            title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title_match.group(1)))).strip()
            image_url = image_match.group(1).split()[0]
            image_url = _absolute_url(image_url, self.base_url)
            if title and _looks_like_valid_image(image_url):
                results.append(ProductImage(title=title, image_url=image_url, source_url=source_url))
            time.sleep(0.12)
        self._query_cache[query] = results
        return results

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        query_key = _squash(query)
        best_key = _squash(best_item.title)
        if query_key and best_key and query_key == best_key:
            return best_item
        if query_key and best_key and query_key in best_key and best_score[1] >= 0.9:
            return best_item
        return None


class EnskySitemapProvider:
    def __init__(self, store_name: str, sitemap_url: str, allow_sitemap_fallback: bool = True) -> None:
        self.store_name = store_name
        self.sitemap_url = sitemap_url
        self.allow_sitemap_fallback = allow_sitemap_fallback
        self.search_url = "https://www.enskyshop.com/products/list?name={query}"
        self.cache_dir = DEFAULT_CACHE_DIR
        self._products: list[ProductImage] | None = None
        self._query_cache: dict[str, list[ProductImage]] = {}

    def search_images(self, query: str) -> list[ProductImage]:
        if query in self._query_cache:
            return self._query_cache[query]
        url = self.search_url.format(query=urllib.parse.quote(query))
        try:
            text = _fetch_text(url, timeout=25)
        except Exception:
            self._query_cache[query] = []
            return []
        time.sleep(0.35)
        results = _filter_ensky_search_results(query, _parse_ensky_product_cards(text))
        self._query_cache[query] = results
        return results

    def products(self) -> list[ProductImage]:
        if self._products is not None:
            return self._products
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / "ensky_sitemap_index.json"
        state_path = self.cache_dir / "ensky_sitemap_state.json"
        cached: list[dict[str, str | None]] = []
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                self._products = [
                    ProductImage(title=str(item["title"]), image_url=str(item["image_url"]), source_url=item.get("source_url"))
                    for item in cached
                    if item.get("title") and item.get("image_url")
                ]
            except Exception:
                cached = []
                self._products = []

        sitemap_text = _fetch_text(self.sitemap_url, timeout=30)
        urls = re.findall(r"<loc>(https://www\.enskyshop\.com/products/detail/\d+)</loc>", sitemap_text)
        try:
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        except Exception:
            state = {}
        cached_source_urls = {str(item.source_url) for item in (self._products or []) if item.source_url}
        cursor = int(state.get("cursor", 0) or 0)
        batch_size = 400
        batch_urls = urls[cursor : cursor + batch_size]
        if not batch_urls and len(cached_source_urls) < len(urls):
            batch_urls = [url for url in urls if url not in cached_source_urls][:batch_size]
        if not batch_urls:
            self._products = self._products or []
            return self._products

        def fetch_detail(url: str) -> ProductImage | None:
            try:
                response = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
                response.raise_for_status()
                text = response.text
            except Exception:
                return None
            title_match = re.search(r'<meta property="og:title" content="([^"]+)"', text, re.IGNORECASE)
            image_match = re.search(r'<meta property="og:image" content="([^"]+)"', text, re.IGNORECASE)
            if not title_match or not image_match:
                return None
            title = html.unescape(title_match.group(1)).strip()
            image_url = _canonical_image_url(image_match.group(1))
            if not title or not _looks_like_valid_image(image_url):
                return None
            return ProductImage(title=title, image_url=image_url, source_url=url)

        products: list[ProductImage] = self._products or []
        existing_titles = {_squash(item.title) for item in products}
        existing_sources = {str(item.source_url) for item in products if item.source_url}
        fetched_items: list[ProductImage] = []
        for url in batch_urls:
            if url in existing_sources:
                continue
            item = fetch_detail(url)
            if item is None:
                continue
            key = _squash(item.title)
            if key in existing_titles:
                for existing in products:
                    if _squash(existing.title) == key and not existing.source_url:
                        existing.source_url = item.source_url
                        break
                continue
            existing_titles.add(key)
            existing_sources.add(url)
            fetched_items.append(item)
            time.sleep(0.08)
        products.extend(fetched_items)
        cache_path.write_text(
            json.dumps(
                [{"title": item.title, "image_url": item.image_url, "source_url": item.source_url} for item in products],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        state_path.write_text(
            json.dumps({"cursor": min(cursor + batch_size, len(urls)), "total_urls": len(urls)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._products = products
        return products

    def match(self, query: str) -> ProductImage | None:
        candidates = self.search_images(query)
        if candidates:
            scored_search = [(_score(query, item.title), item) for item in candidates]
            scored_search.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
            best_score, best_item = scored_search[0]
            second_score = scored_search[1][0] if len(scored_search) > 1 else (0, 0.0)
            if not _has_goods_type_compatibility(query, best_item.title):
                return None
            if (
                best_score[0] >= 2
                and best_score[1] >= 0.72
                and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.08)
            ):
                return best_item

        if not self.allow_sitemap_fallback:
            return None

        candidates = self.products()
        if not candidates:
            return None
        scored = [(_score(query, item.title), item) for item in candidates]
        scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
        best_score, best_item = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else (0, 0.0)
        if not _has_goods_type_compatibility(query, best_item.title):
            return None
        if (
            best_score[0] >= 2
            and best_score[1] >= 0.72
            and (best_score[0] > second_score[0] or best_score[1] - second_score[1] >= 0.08)
        ):
            return best_item
        return None


def _filter_ensky_search_results(query: str, results: list[ProductImage]) -> list[ProductImage]:
    filtered: list[ProductImage] = []
    for item in results:
        if not _has_goods_type_compatibility(query, item.title):
            continue
        if not _has_distinctive_token_match(query, item.title):
            continue
        score = _score(query, item.title)
        if score[0] <= 0 and score[1] < 0.5:
            continue
        filtered.append(item)
    return filtered


def _filter_goodsmile_search_results(query: str, results: list[ProductImage]) -> list[ProductImage]:
    filtered: list[ProductImage] = []
    for item in results:
        if not _has_goods_type_compatibility(query, item.title):
            continue
        if not _has_all_distinctive_token_matches(query, item.title):
            continue
        filtered.append(item)
    return filtered


def _parse_ensky_product_cards(text: str) -> list[ProductImage]:
    results: list[ProductImage] = []
    seen: set[str] = set()
    cards = re.findall(
        r'<a\s+href=["\'](https://www\.enskyshop\.com/products/detail/\d+)["\']>\s*'
        r'<picture>\s*<source\s+srcset=["\']([^"\']+)["\'][^>]*>\s*'
        r'<img\s+src=["\'][^"\']*["\']\s+alt=["\']([^"\']+)["\']',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    for source_url, image_url, title in cards:
        title = html.unescape(re.sub(r"\s+", " ", title)).strip()
        image_url = _absolute_url(image_url.split()[0], "https://www.enskyshop.com")
        key = f"{_squash(title)}|{source_url}"
        if not title or not _looks_like_valid_image(image_url) or key in seen:
            continue
        seen.add(key)
        results.append(ProductImage(title=title, image_url=_canonical_image_url(image_url), source_url=source_url))
    if results:
        return results

    for item_html in re.findall(r'<div class="tabBox_item[^"]*">(.*?)</div>\s*(?:</div>|<div class="tabBox_item)', text, re.IGNORECASE | re.DOTALL):
        href_match = re.search(r'<a\b[^>]+href=["\']([^"\']*/products/detail/\d+)["\']', item_html, re.IGNORECASE)
        image_match = re.search(r'<source\b[^>]+srcset=["\']([^"\']+)["\']', item_html, re.IGNORECASE)
        if not image_match:
            image_match = re.search(r'<img\b[^>]+src=["\']([^"\']+)["\']', item_html, re.IGNORECASE)
        title_match = re.search(r'<img\b[^>]+alt=["\']([^"\']+)["\']', item_html, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r"<span>(.*?)</span>", item_html, re.IGNORECASE | re.DOTALL)
        if not href_match or not image_match or not title_match:
            continue
        title = html.unescape(re.sub(r"<[^>]+>", " ", title_match.group(1)))
        title = re.sub(r"\s+", " ", title).strip()
        image_url = _absolute_url(image_match.group(1).split()[0], "https://www.enskyshop.com")
        source_url = _absolute_url(href_match.group(1), "https://www.enskyshop.com")
        key = f"{_squash(title)}|{source_url}"
        if not title or not _looks_like_valid_image(image_url) or key in seen:
            continue
        seen.add(key)
        results.append(ProductImage(title=title, image_url=_canonical_image_url(image_url), source_url=source_url))
    return results


def _preferred_query_for_row(row: dict[str, object | None]) -> str:
    store_name = str(row.get("source_store") or "").strip()
    preferred_stores = {
        "\uc560\ub2c8\uba54\uc774\ud2b8",
        "\uc5d4\uc2a4\uce74\uc774",
        "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
        "FuRyu",
        "SEGA",
        "Taito",
        "Banpresto",
        "Movic",
        "\ucf54\ud1a0\ubd80\ud0a4\uc57c",
        CHIIKAWA_MARKET_STORE,
        NAGANO_MARKET_STORE,
        CHIIKAWA_MOGUMOGU_STORE,
    }
    if store_name in preferred_stores:
        if store_name == "Banpresto":
            prefix = AFFILIATION_JA_QUERY_PREFIXES.get(str(row.get("affiliation") or ""))
            name_ja = str(row.get("name_ja") or "").strip()
            if prefix and name_ja and prefix not in name_ja:
                return f"{prefix} {name_ja}"
        if store_name in {"\uc560\ub2c8\uba54\uc774\ud2b8"} and not row.get("name_ja"):
            localized = _localized_ja_query_from_korean_row(row)
            if localized:
                return localized
        if store_name in {"\uc560\ub2c8\uba54\uc774\ud2b8"} and row.get("name_ja"):
            name_ja = str(row.get("name_ja") or "").strip()
            paren_match = re.search(r"\(([^)]+)\)", str(row.get("name_ko") or ""))
            if paren_match:
                character_ja = KOREAN_CHARACTER_JA_QUERY.get(paren_match.group(1).strip())
                character_key = _squash(character_ja) if character_ja else ""
                existing_keys = {_squash(token) for token in _tokens(name_ja)}
                if character_ja and character_key and character_key not in existing_keys:
                    return f"{name_ja} {character_ja}"
        for field in ("name_ja", "name_en", "name_ko"):
            value = str(row.get(field) or "").strip()
            if value:
                return value
    return str(row.get("name_ko") or "").strip()


def _localized_ja_query_from_korean_row(row: dict[str, object | None]) -> str | None:
    name_ko = str(row.get("name_ko") or "").strip()
    affiliation = str(row.get("affiliation") or "").strip()
    category = str(row.get("category") or "").strip()
    parts: list[str] = []

    affiliation_ja = AFFILIATION_JA_QUERY_PREFIXES.get(affiliation)
    if affiliation_ja:
        parts.append(affiliation_ja)

    goods_type = None
    for ko, ja in KOREAN_GOODS_TYPE_JA_QUERY.items():
        if ko in name_ko or ko in category:
            goods_type = ja
            break
    if goods_type:
        parts.append(goods_type)

    paren_match = re.search(r"\(([^)]+)\)", name_ko)
    is_random_or_blind = any(token in name_ko for token in ("랜덤", "블라인드", "트레이딩"))
    if paren_match:
        character_key = paren_match.group(1).strip()
        character_ja = KOREAN_CHARACTER_JA_QUERY.get(character_key)
        if character_ja:
            parts.append(character_ja)
    elif is_random_or_blind:
        pass

    if len(parts) >= 2:
        return " ".join(parts)
    return None


def _is_broad_random_row(row: dict[str, object | None]) -> bool:
    name_ko = str(row.get("name_ko") or "")
    if not any(token in name_ko for token in ("랜덤", "블라인드", "트레이딩")):
        return False
    match = re.search(r"\(([^)]+)\)", name_ko)
    if not match:
        return True
    return match.group(1).strip() not in KOREAN_CHARACTER_JA_QUERY


def _iter_missing_rows(rows: Iterable[dict]) -> Iterable[dict]:
    for row in rows:
        if row.get("image_url"):
            continue
        yield row


def _candidate_preview(query: str, candidates: list[ProductImage], limit: int = 5) -> list[dict[str, object]]:
    scored = [(_score(query, item.title), item) for item in candidates]
    scored.sort(key=lambda item: (item[0][0], item[0][1]), reverse=True)
    preview: list[dict[str, object]] = []
    for score, item in scored[:limit]:
        preview.append(
            {
                "title": item.title,
                "source_url": item.source_url,
                "image_url": item.image_url,
                "score_overlap": score[0],
                "score_similarity": round(score[1], 4),
                "goods_type_compatible": _has_goods_type_compatibility(query, item.title),
                "distinctive_token_match": _has_distinctive_token_match(query, item.title),
                "all_distinctive_token_match": _has_all_distinctive_token_matches(query, item.title),
                "parenthetical_terms_match": _parenthetical_terms_match(query, item.title),
                "source_url_is_product_detail": is_product_specific_source_url(item.source_url),
                "safe_source_image_pair": is_safe_source_image_pair(item.source_url, item.image_url),
            }
        )
    return preview


def _provider_diagnostic(provider: object, query: str) -> dict[str, object]:
    if isinstance(provider, ShopifyProvider):
        try:
            candidates = list(provider.products())
            sitemap_candidates = provider.sitemap_products()
            if sitemap_candidates:
                seen = {_squash(item.title) for item in candidates}
                for item in sitemap_candidates:
                    if _squash(item.title) not in seen:
                        candidates.append(item)
        except Exception as error:
            return {"reason": "provider_search_failed", "query": query, "error": str(error)}
        if not candidates:
            return {"reason": "no_provider_candidates", "query": query, "candidate_count": 0}
        preview = _candidate_preview(query, candidates)
        best = preview[0] if preview else {}
        second = preview[1] if len(preview) > 1 else {}
        failed_checks = [
            key
            for key in (
                "goods_type_compatible",
                "all_distinctive_token_match",
                "parenthetical_terms_match",
                "source_url_is_product_detail",
                "safe_source_image_pair",
            )
            if best.get(key) is False
        ]
        if failed_checks:
            rejection_reason = "failed_safety_checks"
        elif second and best.get("score_overlap") == second.get("score_overlap"):
            rejection_reason = "ambiguous_close_candidates"
        else:
            rejection_reason = "below_match_threshold"
        return {
            "reason": "best_candidate_rejected",
            "rejection_reason": rejection_reason,
            "failed_checks": failed_checks,
            "query": query,
            "candidate_count": len(candidates),
            "best_score_overlap": best.get("score_overlap"),
            "best_score_similarity": best.get("score_similarity"),
            "second_score_overlap": second.get("score_overlap"),
            "second_score_similarity": second.get("score_similarity"),
            "best_goods_type_compatible": best.get("goods_type_compatible"),
            "best_distinctive_token_match": best.get("distinctive_token_match"),
            "best_all_distinctive_token_match": best.get("all_distinctive_token_match"),
            "best_parenthetical_terms_match": best.get("parenthetical_terms_match"),
            "best_source_url_is_product_detail": best.get("source_url_is_product_detail"),
            "best_safe_source_image_pair": best.get("safe_source_image_pair"),
            "top_candidates": preview,
        }
    search_images = getattr(provider, "search_images", None)
    if not callable(search_images):
        return {"reason": "provider_has_no_search_diagnostics", "query": query}
    try:
        candidates = search_images(query)
    except Exception as error:
        return {"reason": "provider_search_failed", "query": query, "error": str(error)}
    if not candidates:
        return {"reason": "no_provider_candidates", "query": query, "candidate_count": 0}
    preview = _candidate_preview(query, candidates)
    best = preview[0] if preview else {}
    second = preview[1] if len(preview) > 1 else {}
    failed_checks = [
        key
        for key in (
            "goods_type_compatible",
            "all_distinctive_token_match",
            "parenthetical_terms_match",
            "source_url_is_product_detail",
            "safe_source_image_pair",
        )
        if best.get(key) is False
    ]
    if failed_checks:
        rejection_reason = "failed_safety_checks"
    elif second and best.get("score_overlap") == second.get("score_overlap"):
        rejection_reason = "ambiguous_close_candidates"
    else:
        rejection_reason = "below_match_threshold"
    return {
        "reason": "best_candidate_rejected",
        "rejection_reason": rejection_reason,
        "failed_checks": failed_checks,
        "query": query,
        "candidate_count": len(candidates),
        "best_score_overlap": best.get("score_overlap"),
        "best_score_similarity": best.get("score_similarity"),
        "second_score_overlap": second.get("score_overlap"),
        "second_score_similarity": second.get("score_similarity"),
        "best_goods_type_compatible": best.get("goods_type_compatible"),
        "best_distinctive_token_match": best.get("distinctive_token_match"),
        "best_all_distinctive_token_match": best.get("all_distinctive_token_match"),
        "best_parenthetical_terms_match": best.get("parenthetical_terms_match"),
        "best_source_url_is_product_detail": best.get("source_url_is_product_detail"),
        "best_safe_source_image_pair": best.get("safe_source_image_pair"),
        "top_candidates": preview,
    }


def _unresolved_summary(unresolved: Iterable[dict[str, object | None]]) -> dict[str, object]:
    by_reason: Counter[str] = Counter()
    by_rejection_reason: Counter[str] = Counter()
    by_failed_check: Counter[str] = Counter()

    for item in unresolved:
        reason = item.get("reason")
        if reason:
            by_reason[str(reason)] += 1

        rejection_reason = item.get("rejection_reason")
        if rejection_reason:
            by_rejection_reason[str(rejection_reason)] += 1

        failed_checks = item.get("failed_checks")
        if isinstance(failed_checks, list):
            for check in failed_checks:
                if check:
                    by_failed_check[str(check)] += 1

    return {
        "total": sum(by_reason.values()),
        "by_reason": dict(by_reason.most_common()),
        "by_rejection_reason": dict(by_rejection_reason.most_common()),
        "by_failed_check": dict(by_failed_check.most_common()),
    }


def _db_image_lookup() -> dict[tuple[str, str], str]:
    if not DEFAULT_DB.exists():
        return {}
    lookup: dict[tuple[str, str], str] = {}
    conn = sqlite3.connect(DEFAULT_DB)
    try:
        query = """
            select name_ko, affiliation, image_url
            from goods_catalog
            where image_url is not null and trim(image_url) <> ''
        """
        for name_ko, affiliation, image_url in conn.execute(query):
            if not name_ko or not affiliation or not image_url:
                continue
            lookup.setdefault((str(name_ko), str(affiliation)), str(image_url))
    finally:
        conn.close()
    return lookup


def _build_providers() -> dict[str, object]:
    providers: dict[str, object] = {
        store_name: ShopifyProvider(store_name=store_name, **config)
        for store_name, config in STORE_PROVIDERS.items()
    }
    for store_name, config in SEARCH_PROVIDERS.items():
        if store_name in {ANIMATE_STORE, "Animate"}:
            providers[store_name] = AnimateSearchProvider(store_name=store_name, **config)
        elif store_name == "FuRyu":
            providers[store_name] = FuryuApiProvider(store_name=store_name, **config)
        elif store_name == GOODSMILE_STORE:
            providers[store_name] = GoodSmileInfoProvider(store_name=store_name, **config)
        elif store_name == "Taito":
            providers[store_name] = TaitoApiProvider(store_name=store_name, **config)
        elif store_name == "SEGA":
            providers[store_name] = SegaPlazaProvider(store_name=store_name, **config)
        elif store_name == "Banpresto":
            providers[store_name] = BanprestoSearchProvider(store_name=store_name, **config)
        elif store_name in {KOTOBUKIYA_STORE, "Movic"}:
            providers[store_name] = GoodsSearchDetailProvider(store_name=store_name, **config)
        else:
            providers[store_name] = SearchPageProvider(store_name=store_name, **config)
    providers[ENSKY_STORE] = EnskySitemapProvider(
        store_name=ENSKY_STORE,
        sitemap_url="https://www.enskyshop.com/sitemap.xml",
    )
    return providers


def _load_rows(path: Path) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)], payload
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], None
    raise SystemExit(f"{path} must contain a JSON list or a catalog object with items")


def _write_rows(path: Path, rows: list[dict[str, object]], wrapper: dict[str, object] | None) -> None:
    if wrapper is not None:
        wrapper["items"] = rows
        meta = wrapper.get("meta")
        if isinstance(meta, dict):
            missing = dict(meta.get("missing") or {})
            missing["image_url"] = sum(1 for row in rows if not row.get("image_url"))
            missing["local_image_path"] = sum(1 for row in rows if not row.get("local_image_path"))
            meta["missing"] = missing
            meta["row_count"] = len(rows)
            meta["total_items"] = len(rows)
        path.write_text(json.dumps(wrapper, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        return
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--store", action="append")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument(
        "--time-budget-seconds",
        type=float,
        default=None,
        help="Stop cleanly after this many seconds and write a partial report.",
    )
    parser.add_argument(
        "--allow-local-fallbacks",
        action="store_true",
        help="Allow DB lookup and manual overrides. Disabled by default so automatic attachment stays official-source-only.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    report_path = Path(args.report)
    rows, wrapper = _load_rows(input_path)
    allowed_stores = set()
    for store in args.store or []:
        normalized = store.strip()
        if not normalized:
            continue
        allowed_stores.add(STORE_ALIASES.get(normalized.lower(), STORE_ALIASES.get(normalized, normalized)))

    providers = _build_providers()
    db_lookup = _db_image_lookup() if args.allow_local_fallbacks else {}

    filled = 0
    filled_changes: list[dict[str, object | None]] = []
    unresolved: list[dict[str, object | None]] = []
    processed_rows = 0
    started_at = time.monotonic()
    time_budget_exhausted = False
    for row_index, row in ((index, row) for index, row in enumerate(rows) if isinstance(row, dict) and not row.get("image_url")):
        store_name = str(row.get("source_store") or "").strip()
        if allowed_stores and store_name not in allowed_stores:
            continue
        if args.max_rows is not None and processed_rows >= args.max_rows:
            break
        if args.time_budget_seconds is not None and time.monotonic() - started_at >= args.time_budget_seconds:
            time_budget_exhausted = True
            break
        processed_rows += 1

        db_image = db_lookup.get((str(row.get("name_ko") or ""), str(row.get("affiliation") or "")))
        if db_image:
            row["image_url"] = db_image
            filled += 1
            filled_changes.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "source_store": store_name,
                    "image_url": db_image,
                    "source_url": row.get("source_url"),
                    "match_title": "db_lookup",
                }
            )
            continue

        manual_image = MANUAL_OVERRIDES.get(str(row.get("name_ko") or "").strip()) if args.allow_local_fallbacks else None
        if manual_image:
            row["image_url"] = manual_image
            filled += 1
            filled_changes.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "source_store": store_name,
                    "image_url": manual_image,
                    "source_url": row.get("source_url"),
                    "match_title": "manual_override",
                }
            )
            continue

        source_image = _image_from_source_url(str(row.get("source_url") or ""))
        if source_image:
            row["image_url"] = source_image
            filled += 1
            filled_changes.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "source_store": store_name,
                    "image_url": source_image,
                    "source_url": row.get("source_url"),
                    "match_title": "source_url_og_image",
                }
            )
            continue

        provider = providers.get(store_name)
        query = _preferred_query_for_row(row)
        if provider is None:
            unresolved.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "affiliation": row.get("affiliation"),
                    "source_store": store_name,
                    "source_url": row.get("source_url"),
                    "query": query,
                    "reason": "no_provider_config",
                }
            )
            continue
        try:
            match = provider.match(query)
        except Exception as error:
            unresolved.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "affiliation": row.get("affiliation"),
                    "source_store": store_name,
                    "source_url": row.get("source_url"),
                    "query": query,
                    "reason": "provider_match_failed",
                    "error": str(error),
                }
            )
            continue
        if match is None:
            diagnostic = _provider_diagnostic(provider, query)
            unresolved.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "affiliation": row.get("affiliation"),
                    "source_store": store_name,
                    "source_url": row.get("source_url"),
                    "query": query,
                    **diagnostic,
                }
            )
            continue
        if not is_safe_source_image_pair(match.source_url, match.image_url):
            unresolved.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "affiliation": row.get("affiliation"),
                    "source_store": store_name,
                    "source_url": match.source_url or row.get("source_url"),
                    "query": query,
                    "match_title": match.title,
                    "image_url": match.image_url,
                    "reason": "unsafe_or_non_product_detail_image_source",
                }
            )
            continue
        if _is_broad_random_row(row):
            unresolved.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "affiliation": row.get("affiliation"),
                    "source_store": store_name,
                    "source_url": match.source_url or row.get("source_url"),
                    "query": query,
                    "match_title": match.title,
                    "image_url": match.image_url,
                    "reason": "random_broad_requires_manual_variant_confirmation",
                }
            )
            continue
        row["image_url"] = _canonical_image_url(match.image_url)
        if match.source_url and (not row.get("source_url") or is_generic_source_url(row.get("source_url"))):
            row["source_url"] = match.source_url
        filled += 1
        filled_changes.append(
            {
                "row_index": row_index,
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_store": store_name,
                "image_url": row.get("image_url"),
                "source_url": row.get("source_url"),
                "match_title": match.title,
            }
        )
        time.sleep(0.05)

    report_path.write_text(
        json.dumps(
            {
                "filled": filled,
                "processed_rows": processed_rows,
                "time_budget_seconds": args.time_budget_seconds,
                "time_budget_exhausted": time_budget_exhausted,
                "allowed_stores": sorted(allowed_stores) if allowed_stores else "all",
                "filled_changes": filled_changes,
                "unresolved": unresolved,
                "unresolved_summary": _unresolved_summary(unresolved),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if args.write:
        _write_rows(input_path, rows, wrapper)

    total_missing_after = sum(1 for row in rows if not row.get("image_url"))
    print(
        json.dumps(
            {
                "filled": filled,
                "processed_rows": processed_rows,
                "time_budget_exhausted": time_budget_exhausted,
                "missing_after": total_missing_after,
                "report_path": str(report_path),
                "updated_input": str(input_path) if args.write else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
