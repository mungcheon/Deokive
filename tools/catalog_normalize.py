from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


CATALOG_FIELDS = (
    "name_ko",
    "name_ja",
    "name_en",
    "category",
    "character_name",
    "affiliation",
    "series_name",
    "sub_series",
    "official_price_jpy",
    "official_price_krw",
    "barcode",
    "image_url",
    "source_url",
    "source_store",
    "release_date",
)

CATEGORY_ALIASES = {
    "plush": "인형",
    "mascot": "마스코트",
    "figure": "피규어",
    "acrylic": "아크릴",
    "stand": "아크릴 스탠드",
    "badge": "캔뱃지",
    "button": "캔뱃지",
    "keychain": "키링",
    "key ring": "키링",
    "charm": "참",
    "sticker": "스티커",
    "card": "카드",
    "poster": "포스터",
    "towel": "타월",
    "bag": "가방",
    "pouch": "파우치",
    "mug": "머그컵",
    "cup": "컵",
    "plate": "식기",
    "clear file": "클리어파일",
    "clearfile": "클리어파일",
    "notebook": "문구",
    "memo": "문구",
    "ぬいぐるみ": "인형",
    "マスコット": "마스코트",
    "フィギュア": "피규어",
    "アクリル": "아크릴",
    "スタンド": "아크릴 스탠드",
    "缶バッジ": "캔뱃지",
    "バッジ": "캔뱃지",
    "キーホルダー": "키링",
    "キーリング": "키링",
    "チャーム": "참",
    "ステッカー": "스티커",
    "カード": "카드",
    "ポスター": "포스터",
    "タオル": "타월",
    "バッグ": "가방",
    "ポーチ": "파우치",
    "マグ": "머그컵",
    "グラス": "컵",
    "どんぶり": "식기",
    "クリアファイル": "클리어파일",
    "メモ": "문구",
    "筆記具": "문구",
    "文具": "문구",
    "靴下": "의류",
    "ソックス": "의류",
    "アパレル": "의류",
    "帽子": "의류",
    "生活雑貨": "생활잡화",
    "雑貨": "생활잡화",
    "食器": "식기",
    "うちわ": "응원용품",
    "ファイル": "클리어파일",
    "コスメ・美容": "생활잡화",
    "Tシャツ・パーカー": "의류",
    "スマホケース": "생활잡화",
    "おもちゃ": "완구",
    "ヘアアクセサリー・鏡": "액세서리",
    "カレンダー・手帳・ノート": "문구",
    "充電グッズ": "생활잡화",
    "バス・洗面": "생활잡화",
    "アクセサリー・腕時計": "액세서리",
    "スマホリング": "생활잡화",
    "寝具・クッション": "생활잡화",
    "ワッペン": "생활잡화",
    "お皿・お椀": "식기",
    "マスク・衛生": "생활잡화",
    "お箸・スプーン": "식기",
    "収納": "생활잡화",
    "手袋・マフラー": "의류",
    "傘": "생활잡화",
    "タンブラー・水筒": "컵",
    "ルームシューズ": "의류",
    "パズル": "퍼즐",
    "食品": "식품",
    "ピクニックグッズ": "생활잡화",
    "ふきん・マット": "생활잡화",
    "ウォールインテリア": "생활잡화",
    "お守り": "생활잡화",
    "キット": "굿즈",
    "エプロン": "의류",
    "お弁当箱": "식기",
    "調理道具": "식기",
    "ペット": "생활잡화",
    "照明・加湿器": "생활잡화",
    "マウスパッド": "생활잡화",
    "着ぐるみ": "의류",
    "トレカ": "카드",
    "カーグッズ": "생활잡화",
    "アクスタ": "아크릴 스탠드",
}

KOREAN_CATEGORY_ALIASES = {
    "굿즈": "굿즈",
    "인형": "인형",
    "봉제인형": "인형",
    "마스코트": "마스코트",
    "러버마스코트": "마스코트",
    "피규어": "피규어",
    "미니피규어": "피규어",
    "넨도로이드": "피규어",
    "아크릴": "아크릴",
    "아크릴스탠드": "아크릴 스탠드",
    "스탠드": "아크릴 스탠드",
    "캔뱃지": "캔뱃지",
    "뱃지": "캔뱃지",
    "배지": "캔뱃지",
    "키링": "키링",
    "키홀더": "키링",
    "러버스트랩": "키링",
    "참": "참",
    "스티커": "스티커",
    "카드": "카드",
    "일러스트카드": "카드",
    "포스터": "포스터",
    "타월": "타월",
    "타올": "타월",
    "수건": "타월",
    "가방": "가방",
    "토트백": "가방",
    "백팩": "가방",
    "숄더백": "가방",
    "파우치": "파우치",
    "머그": "머그컵",
    "머그컵": "머그컵",
    "컵": "컵",
    "식기": "식기",
    "클리어파일": "클리어파일",
    "문구": "문구",
    "필기구": "문구",
    "액세서리": "액세서리",
    "악세사리": "액세서리",
    "의류": "의류",
    "완구": "완구",
    "퍼즐": "퍼즐",
    "식품": "식품",
    "양말": "의류",
    "모자": "의류",
    "머리띠": "액세서리",
    "쿠션": "생활잡화",
    "포셰트": "가방",
    "응원봉": "응원봉",
    "펜라이트": "응원봉",
    "우치와": "응원용품",
}

CHARACTER_ALIASES = {
    "치이카와": ("치이카와", "chiikawa", "ちいかわ"),
    "하치와레": ("하치와레", "hachiware", "ハチワレ"),
    "우사기": ("우사기", "usagi", "うさぎ"),
    "모몽가": ("모몽가", "momonga", "モモンガ"),
    "쿠리만쥬": ("쿠리만쥬", "kurimanju", "くりまんじゅう"),
    "라코": ("라코", "rakko", "ラッコ"),
    "시사": ("시사", "shisa", "シーサー"),
    "후루혼야": ("후루혼야", "furuhonya", "古本屋", "かに"),
    "몽키 D. 루피": ("몽키 D. 루피", "몽키 D 루피", "루피", "luffy", "モンキー・D・ルフィ", "ルフィ太郎"),
    "롤로노아 조로": ("롤로노아 조로", "조로", "zoro", "ロロノア・ゾロ", "ゾロ十郎"),
    "상디": ("상디", "sanji", "サンジ", "サン五郎"),
    "트라팔가 로": ("트라팔가 로", "트라팔가 로우", "トラファルガー・ロー"),
    "사보": ("사보", "sabo", "サボ"),
    "카이도": ("카이도", "kaido", "カイドウ"),
}

SOURCE_STORE_ALIASES = {
    "animate": "애니메이트",
    "굿스마일컴퍼니": "굿스마일컴퍼니",
    "goodsmile": "굿스마일컴퍼니",
    "goodsmilecompany": "굿스마일컴퍼니",
    "banpresto": "Banpresto",
    "반프레스토": "Banpresto",
    "모구모구혼포": "치이카와 모구모구 혼포",
    "치이카와모구모구혼포": "치이카와 모구모구 혼포",
}

GENERIC_SOURCE_URLS = {
    "https://nagano-market.jp/ko",
    "https://chiikawamogumogu.shop",
    "https://chiikawamogumogu.shop/",
    "https://chiikawamarket.jp/ko/pages/chiikawapark",
    "https://jp.chiikawa-pocket.com/ja/store/",
    "https://fanding.kr/@stellive/shop",
    "https://shop.weverse.io/home",
    "https://www.nintendo.com/jp/character/",
    "https://www.pokemoncenter-online.com/",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\u3000", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def normalize_for_key(value: Any) -> str:
    text = clean_text(value) or ""
    text = text.lower()
    text = text.replace("～", "~").replace("×", "x")
    return re.sub(r"[\s\-_./|:;,'\"()\[\]{}~]+", "", text)


def normalize_url(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    if text.startswith("//"):
        text = "https:" + text
    return text


def canonical_source_url_key(value: Any) -> str | None:
    url = normalize_url(value)
    if not url:
        return None
    parsed = urlsplit(url)
    if not parsed.netloc:
        return url.split("?", 1)[0].split("#", 1)[0].rstrip("/").lower()

    scheme = "https" if parsed.scheme.lower() in {"http", "https"} else parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = re.sub(r"/+", "/", parsed.path).rstrip("/")
    query = ""
    if netloc == "www.animate-onlineshop.jp" and path == "/products/detail.php":
        match = re.search(r"(?:^|&)product_id=(\d+)(?:&|$)", parsed.query)
        if match:
            query = f"product_id={match.group(1)}"
    if netloc == "www.ktown4u.com" and path == "/iteminfo":
        match = re.search(r"(?:^|&)goods_no=(\d+)(?:&|$)", parsed.query)
        if match:
            query = f"goods_no={match.group(1)}"
    if netloc == "gashapon.jp" and path == "/products/detail.php":
        match = re.search(r"(?:^|&)jan_code=(\d+)(?:&|$)", parsed.query)
        if match:
            query = f"jan_code={match.group(1)}"
    if netloc == "chiikawamarket.jp" and path.startswith("/ko/products/"):
        path = path.removeprefix("/ko")
    return urlunsplit((scheme, netloc, path, query, "")).lower()


def is_generic_source_url(value: Any) -> bool:
    canonical = canonical_source_url_key(value)
    if not canonical:
        return False
    generic = {canonical_source_url_key(item) for item in GENERIC_SOURCE_URLS}
    return canonical in generic


def normalize_barcode_for_key(value: Any) -> str:
    barcode = normalize_for_key(value)
    if not barcode.isdigit() or not 8 <= len(barcode) <= 14:
        return barcode
    without_leading_zeroes = barcode.lstrip("0")
    if 8 <= len(without_leading_zeroes) <= 13:
        return without_leading_zeroes
    return barcode


def normalize_source_store(value: Any) -> str:
    raw = clean_text(value) or ""
    compact = normalize_for_key(raw)
    return SOURCE_STORE_ALIASES.get(compact, raw)


def normalize_category(value: Any, fallback_text: str = "") -> str:
    raw = clean_text(value)
    compact = normalize_for_key(raw)
    if compact in KOREAN_CATEGORY_ALIASES:
        return KOREAN_CATEGORY_ALIASES[compact]

    haystack = f"{raw or ''} {fallback_text}".lower()
    for token, category in CATEGORY_ALIASES.items():
        if token.lower() in haystack:
            return category
    return raw or "굿즈"


def infer_character(*values: Any) -> str:
    haystack = " ".join(clean_text(value) or "" for value in values).lower()
    for name, aliases in CHARACTER_ALIASES.items():
        if any(alias.lower() in haystack for alias in aliases):
            return name
    return "기타"


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in CATALOG_FIELDS:
        value = row.get(field)
        if field in {"official_price_jpy", "official_price_krw"}:
            out[field] = _clean_int(value)
        elif field in {"image_url", "source_url"}:
            out[field] = normalize_url(value)
        else:
            out[field] = clean_text(value)

    name = out.get("name_ko") or out.get("name_ja") or out.get("name_en") or ""
    out["name_ko"] = out.get("name_ko") or name
    out["category"] = normalize_category(out.get("category"), fallback_text=name)
    out["character_name"] = clean_text(out.get("character_name")) or infer_character(
        name,
        out.get("name_ja"),
        out.get("series_name"),
    )
    out["affiliation"] = out.get("affiliation") or _infer_affiliation(out)
    out["source_store"] = normalize_source_store(out.get("source_store"))
    if "online-kuji.chiikawamarket.jp" in str(out.get("source_url") or ""):
        out["source_store"] = "치이카와 온라인 쿠지"
    return out


def canonical_key(row: dict[str, Any]) -> tuple[str, str]:
    normalized = normalize_row(row)
    barcode = normalize_barcode_for_key(normalized.get("barcode"))
    source_store = normalize_for_key(normalized.get("source_store"))
    source_url = normalize_url(normalized.get("source_url"))
    source_url_key = canonical_source_url_key(source_url)
    if barcode:
        return ("barcode", f"{barcode}|{source_store}")
    if (
        source_url_key
        and source_store == normalize_for_key("치이카와 마켓")
        and "chiikawamarket.jp/products/" in source_url_key
    ):
        return ("chiikawa_market_source_url", source_url_key)

    sub_series = normalize_for_key(normalized.get("sub_series"))
    if source_url_key and "online-kuji.chiikawamarket.jp/store/lottery/" in source_url_key:
        prize_key = normalize_for_key(normalized.get("name_ja") or normalized.get("name_ko"))
        if prize_key:
            return ("online_kuji_source_prize", f"{source_url_key}|{prize_key}")
    if source_url_key and source_store == normalize_for_key("이치방쿠지"):
        prize_key = normalize_for_key(normalized.get("name_ja") or normalized.get("name_ko"))
        if prize_key:
            return ("ichiban_kuji_source_prize", f"{source_url_key}|{prize_key}")
    if (
        source_url_key
        and not is_generic_source_url(source_url)
        and source_store != normalize_for_key("이치방쿠지")
        and not sub_series
    ):
        return ("source_url", source_url_key)

    parts = [
        normalized.get("name_ko"),
        normalized.get("affiliation"),
        normalized.get("series_name"),
        normalized.get("sub_series"),
        normalized.get("category"),
        normalized.get("source_store"),
    ]
    return ("logical", "|".join(normalize_for_key(part) for part in parts))


def row_richness(row: dict[str, Any]) -> int:
    score = 0
    for field in CATALOG_FIELDS:
        if row.get(field) not in (None, ""):
            score += 1
    if row.get("image_url"):
        score += 3
    if row.get("source_url"):
        score += 2
    if row.get("barcode"):
        score += 2
    return score


def deterministic_image_name(url: str) -> str:
    clean = normalize_url(url) or url
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:20]
    suffix = clean.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    if suffix not in {"jpg", "jpeg", "png", "webp", "gif"}:
        suffix = "jpg"
    return f"{digest}.{suffix}"


def _clean_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    text = re.sub(r"[^\d]", "", str(value))
    return int(text) if text else None


def _infer_affiliation(row: dict[str, Any]) -> str:
    haystack = " ".join(
        str(row.get(field) or "")
        for field in ("name_ko", "name_ja", "name_en", "series_name", "source_store")
    ).lower()
    if any(token in haystack for token in ("spy×family", "spyxfamily", "spy family")):
        return "SPY×FAMILY"
    if "regloss" in haystack:
        return "hololive DEV_IS"
    if "僕のヴィランアカデミア".lower() in haystack:
        return "나의 히어로 아카데미아"
    if any(token.lower() in haystack for token in ("チョッパー", "chopper")):
        return "원피스"
    if "dragon ball" in haystack:
        return "드래곤볼"
    if any(token.lower() in haystack for token in ("gガンダム", "sdガンダム", "ガンダムシリーズ")):
        return "기동전사 건담"
    if any(token in haystack for token in ("chiikawa", "ちいかわ", "치이카와")):
        return "치이카와"
    return ""
