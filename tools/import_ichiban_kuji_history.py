from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any

from catalog_normalize import infer_character, normalize_category, normalize_row

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "server" / "ichiban_kuji_history_import.json"
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_CAMPAIGN_FILE = ROOT / "data" / "ichiban_kuji_campaigns.json"
DEFAULT_REPORT = ROOT / "server" / "ichiban_kuji_history_import_report.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

DEFAULT_CAMPAIGNS = [
    {"url": "https://1kuji.com/products/chiikawa", "title": "一番くじ ちいかわ"},
    {"url": "https://1kuji.com/products/chiikawa2", "title": "一番くじ ちいかわ ～SWEETS SHOP～"},
    {"url": "https://1kuji.com/products/chiikawa3", "title": "一番くじ ちいかわ ～みんなでラーメン～"},
    {"url": "https://1kuji.com/products/chiikawa4", "title": "一番くじ ちいかわ ～なんかほっこり ちいかわの湯～"},
]

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE | re.DOTALL,
)
ITEM_BLOCK_RE = re.compile(
    r'<div class="itemColList">(.*?)(?=<div class="itemColList">|</section>)',
    re.IGNORECASE | re.DOTALL,
)
NAME_RE = re.compile(
    r'<h4[^>]+class=["\'][^"\']*\bname\b[^"\']*["\'][^>]*>(.*?)</h4>',
    re.IGNORECASE | re.DOTALL,
)
IMG_RE = re.compile(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
HREF_IMAGE_RE = re.compile(r'<a[^>]+href=["\']([^"\']+\.(?:webp|jpe?g|png)(?:\?[^"\']*)?)["\'][^>]*>', re.IGNORECASE)
ALT_RE = re.compile(r'alt=["\']([^"\']+)["\']', re.IGNORECASE)
TEXT_TAG_RE = re.compile(r"<[^>]+>")


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def extract_campaign(url: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    metadata = metadata or {}
    source = fetch_text(url)
    plain = _plain_text(source)
    campaign_title = str(metadata.get("title") or _clean_title(_first_group(TITLE_RE, source) or "一番くじ"))
    release_date = metadata.get("release_date") or _extract_date(plain)
    price = metadata.get("official_price_jpy") or _extract_price(plain)
    rows: list[dict[str, Any]] = []

    extracted = _extract_item_blocks(source, url)
    if not extracted:
        extracted = _extract_fancybox_prize_blocks(source, url)
    if not extracted:
        extracted = _extract_images(source, url)

    for image_url, raw_name in extracted:
        prize_name = _clean_prize_name(raw_name)
        if not prize_name:
            continue
        tier = _extract_tier(prize_name)
        item_name = _strip_tier(prize_name)
        rows.append(
            normalize_row(
                {
                    "name_ko": f"{campaign_title} - {prize_name}",
                    "name_ja": prize_name,
                    "category": normalize_category(None, item_name),
                    "character_name": infer_character(prize_name, campaign_title),
                    "affiliation": _affiliation_from_campaign(campaign_title),
                    "series_name": campaign_title,
                    "sub_series": tier,
                    "official_price_jpy": price,
                    "image_url": image_url,
                    "source_url": url,
                    "source_store": "이치방쿠지",
                    "release_date": release_date,
                }
            )
        )

    return _unique_rows(rows)


def merge_into_seed(rows: list[dict[str, Any]], seed_path: Path) -> tuple[int, int]:
    from catalog_normalize import canonical_key

    seed = json.loads(seed_path.read_text(encoding="utf-8-sig")) if seed_path.exists() else []
    if not isinstance(seed, list):
        raise SystemExit(f"{seed_path} must contain a JSON list")
    normalized_seed = [normalize_row(row) for row in seed if isinstance(row, dict)]
    existing = {canonical_key(row): row for row in normalized_seed}

    created = 0
    updated = 0
    for row in rows:
        key = canonical_key(row)
        current = existing.get(key)
        if current is None:
            normalized_seed.append(row)
            existing[key] = row
            created += 1
            continue
        changed = False
        for field, value in row.items():
            if _should_replace_field(field, current.get(field), value, row):
                current[field] = value
                changed = True
        if changed:
            updated += 1

    seed_path.write_text(
        json.dumps(normalized_seed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return created, updated


def _extract_images(source: str, page_url: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    seen_names: set[str] = set()
    for match in IMG_RE.finditer(source):
        tag = match.group(0)
        image_url = _absolute_url(html.unescape(match.group(1).strip()), page_url)
        alt = html.unescape(_first_group(ALT_RE, tag) or "")
        if not image_url.startswith(("http://", "https://")):
            continue
        if not _looks_like_prize(alt, image_url):
            continue
        if alt in seen_names:
            continue
        seen_names.add(alt)
        results.append((image_url, alt))
    return results


def _extract_item_blocks(source: str, page_url: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for block_match in ITEM_BLOCK_RE.finditer(source):
        block = block_match.group(1)
        name_html = _first_group(NAME_RE, block)
        if not name_html:
            continue
        prize_name = _plain_text(name_html).strip()
        if not prize_name:
            continue
        image_url = _extract_primary_item_image(block, page_url)
        if not image_url:
            continue
        results.append((image_url, prize_name))
    return results


def _extract_fancybox_prize_blocks(source: str, page_url: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    block_pattern = re.compile(
        r'<div\b(?=[^>]+\bid=["\']prize_[^"\']+["\'])(?P<attrs>[^>]*)>(?P<body>.*?)(?=\r?\n\s*<a\b[^>]+data-fancybox|\r?\n\s*</center>)',
        re.IGNORECASE | re.DOTALL,
    )
    name_pattern = re.compile(
        r'<div\b[^>]+class=["\'][^"\']*\bitemDetail\b[^"\']*["\'][^>]*>\s*<div\b[^>]*>(?P<name>.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    item_image_pattern = re.compile(
        r'<div\b[^>]+class=["\'][^"\']*\bitemImage\b[^"\']*["\'][^>]*>(?P<body>.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    for block_match in block_pattern.finditer(source):
        body = block_match.group("body")
        name_match = name_pattern.search(body)
        if not name_match:
            continue
        prize_name = _plain_text(name_match.group("name")).strip()
        if not prize_name:
            continue
        image_area_match = item_image_pattern.search(body)
        image_area = image_area_match.group("body") if image_area_match else body
        image_match = IMG_RE.search(image_area)
        if not image_match:
            continue
        image_url = _absolute_url(html.unescape(image_match.group(1).strip()), page_url)
        key = (prize_name, image_url)
        if not image_url.startswith(("http://", "https://")) or key in seen:
            continue
        seen.add(key)
        results.append((image_url, prize_name))
    return results


def _extract_primary_item_image(block: str, page_url: str) -> str:
    gallery_match = re.search(
        r'<div\b[^>]+class=["\'][^"\']*\bitemColGallery\b[^"\']*["\'][^>]*>(?P<body>.*?)</div>',
        block,
        re.IGNORECASE | re.DOTALL,
    )
    search_area = gallery_match.group("body") if gallery_match else block

    candidates: list[str] = []
    for pattern in (HREF_IMAGE_RE, IMG_RE):
        for match in pattern.finditer(search_area):
            image_url = _absolute_url(html.unescape(match.group(1).strip()), page_url)
            if image_url.startswith(("http://", "https://")):
                candidates.append(image_url)

    if not candidates and gallery_match:
        for match in IMG_RE.finditer(block):
            image_url = _absolute_url(html.unescape(match.group(1).strip()), page_url)
            if image_url.startswith(("http://", "https://")):
                candidates.append(image_url)

    for image_url in candidates:
        if "product_item" in image_url:
            return image_url
    return candidates[0] if candidates else ""


def _absolute_url(value: str, page_url: str) -> str:
    value = value.strip()
    if not value:
        return ""
    base_url = page_url if page_url.endswith("/") else f"{page_url}/"
    return urllib.parse.urljoin(base_url, value)


def _looks_like_prize(alt: str, image_url: str) -> bool:
    return (
        "賞" in alt
        or "ラストワン" in alt
        or "ダブルチャンス" in alt
        or "product_item" in image_url
    )


def _unique_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str | None, str | None]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = (row.get("name_ja"), row.get("image_url"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _affiliation_from_campaign(title: str) -> str:
    mapping = (
        ("SPY×FAMILY", "SPY×FAMILY"),
        ("SPYxFAMILY", "SPY×FAMILY"),
        ("SPY FAMILY", "SPY×FAMILY"),
        ("hololive DEV_IS ReGLOSS", "hololive DEV_IS"),
        ("ReGLOSS", "hololive DEV_IS"),
        ("僕のヴィランアカデミア", "나의 히어로 아카데미아"),
        ("チョッパー", "원피스"),
        ("Chopper", "원피스"),
        ("CHOPPER", "원피스"),
        ("DRAGON BALL", "드래곤볼"),
        ("Gガンダム", "기동전사 건담"),
        ("SDガンダム", "기동전사 건담"),
        ("ガンダムシリーズ", "기동전사 건담"),
        ("ちいかわ", "치이카와"),
        ("ブルーロック", "블루록"),
        ("ワンピース", "원피스"),
        ("ONE PIECE", "원피스"),
        ("星のカービィ", "별의 커비"),
        ("カービィ", "별의 커비"),
        ("HUNTER×HUNTER", "헌터X헌터"),
        ("HUNTER", "헌터X헌터"),
        ("BLEACH", "블리치"),
        ("機動戦士Gundam", "기동전사 건담"),
        ("Gundam", "기동전사 건담"),
        ("おジャ魔女どれみ", "오자마조 도레미"),
        ("スーパーマリオ", "슈퍼마리오"),
        ("マリオ", "슈퍼마리오"),
        ("薬屋のひとりごと", "약사의 혼잣말"),
        ("MOTHER2", "MOTHER2"),
        ("ドラゴンボール", "드래곤볼"),
        ("学園アイドルマスター", "학원 아이돌마스터"),
        ("僕のヒーローアカデミア", "나의 히어로 아카데미아"),
        ("ヒーローアカデミア", "나의 히어로 아카데미아"),
        ("北斗の拳", "북두의 권"),
        ("ぷちきゅあ", "프리큐어"),
        ("プリキュア", "프리큐어"),
        ("NARUTO", "나루토"),
        ("ナルト", "나루토"),
        ("ジョジョの奇妙な冒険", "죠죠의 기묘한 모험"),
        ("ダンダダン", "단다단"),
        ("家庭教師ヒットマンREBORN", "가정교사 히트맨 REBORN!"),
        ("ホロライブ", "홀로라이브"),
        ("アイカツ", "아이카츠"),
        ("Pokémon", "포켓몬"),
        ("ポケピース", "포켓몬"),
        ("勝利の女神", "승리의 여신: 니케"),
        ("NIKKE", "승리의 여신: 니케"),
        ("メダリスト", "메달리스트"),
        ("どうぶつの森", "동물의 숲"),
        ("葬送のフリーレン", "장송의 프리렌"),
        ("フリーレン", "장송의 프리렌"),
        ("トムとジェリー", "톰과 제리"),
        ("WIND BREAKER", "윈드브레이커"),
        ("キングダム", "킹덤"),
        ("モンスターストライク", "몬스터 스트라이크"),
        ("スポンジ・ボブ", "스폰지밥"),
        ("ブルーアーカイブ", "블루 아카이브"),
        ("呪術廻戦", "주술회전"),
        ("機動戦士ガンダム", "기동전사 건담"),
        ("新機動戦記ガンダム", "신기동전기 건담W"),
        ("進撃の巨人", "진격의 거인"),
        ("転生したらスライムだった件", "전생했더니 슬라임이었던 건에 대하여"),
        ("ドラえもん", "도라에몽"),
        ("幽☆遊☆白書", "유유백서"),
        ("ウマ娘", "우마무스메"),
        ("ヴィジランテ", "비질랜티"),
        ("ストリートファイター", "스트리트 파이터"),
        ("ゴールデンカムイ", "골든 카무이"),
        ("カードキャプターさくら", "카드캡터 사쿠라"),
        ("チェンソーマン", "체인소 맨"),
        ("五等分の花嫁", "5등분의 신부"),
        ("エヴァンゲリオン", "에반게리온"),
        ("ハイキュー", "하이큐"),
        ("推しの子", "최애의 아이"),
        ("その着せ替え人形は恋をする", "그 비스크 돌은 사랑을 한다"),
        ("クレヨンしんちゃん", "짱구는 못말려"),
        ("モンスターハンター", "몬스터 헌터"),
        ("ガチアクタ", "가치아쿠타"),
        ("Fate/Grand Order", "Fate/Grand Order"),
        ("Fate", "Fate"),
        ("雪ミク", "하츠네 미쿠"),
        ("にゃんこ大戦争", "냥코 대전쟁"),
        ("桃源暗鬼", "도원암귀"),
        ("ペルソナ", "페르소나"),
        ("MAN WITH A MISSION", "MAN WITH A MISSION"),
        ("ハズビン・ホテル", "하즈빈 호텔"),
        ("珈琲所 コメダ珈琲店", "코메다 커피"),
        ("コメダ珈琲店", "코메다 커피"),
        ("ナルミヤキャラクターズ", "나루미야 캐릭터즈"),
        ("PUPPET SUNSUN", "PUPPET SUNSUN"),
        ("くまのプーさん", "곰돌이 푸"),
        ("クローズ＆WORST", "크로우즈 WORST"),
        ("LAWSON", "LAWSON"),
        ("めちゃでかショッパー", "이치방쿠지"),
        ("銀河特急 ミルキー☆サブウェイ", "은하특급 밀키 서브웨이"),
        ("ゴジラ", "고질라"),
        ("ハリー・ポッター", "해리포터"),
        ("Harry Potter", "해리포터"),
        ("Wicked", "위키드"),
        ("ウィキッド", "위키드"),
        ("ピノ", "피노"),
        ("かわいそうに！", "카와이소니!"),
        ("可哀想に！", "카와이소니!"),
        ("夏目友人帳", "나츠메 우인장"),
        ("FRUITS ZIPPER", "FRUITS ZIPPER"),
        ("歌川国芳", "우타가와 구니요시"),
        ("歌川一門", "우타가와 일문"),
        ("ルルットリリィ", "마법의 자매 루룻토 릴리"),
        ("パワーパフ ガールズ", "파워퍼프걸"),
        ("たまごっち", "다마고치"),
        ("オブングさん", "오붕구상"),
        ("お文具といっしょ", "오붕구상"),
        ("Lil ala mode", "Lil ala mode"),
        ("寺岡奈津美", "테라오카 나츠미"),
        ("てらおかなつみ", "테라오카 나츠미"),
        ("JFA", "일본 축구 국가대표"),
        ("サッカー日本代表", "일본 축구 국가대표"),
        ("Disney", "디즈니"),
        ("リロ＆スティッチ", "스티치"),
        ("スティッチ", "스티치"),
        ("ワイルドバニー", "와일드버니"),
        ("ホワイトタイガーとブラックタイガー", "화이트타이거와 블랙타이거"),
        ("マリッジトキシン", "마리지 톡신"),
        ("ケロロ軍曹", "케로로"),
        ("カイジ", "카이지"),
        ("トイ・ストーリー", "토이 스토리"),
        ("森永", "모리나가"),
        ("オーバーロード", "오버로드"),
        ("バキ", "바키"),
        ("刃牙", "바키"),
        ("ウルトラマン", "울트라맨"),
        ("ゴッホ", "반 고흐"),
        ("鬼滅の刃", "귀멸의 칼날"),
        ("mofusand", "mofusand"),
    )
    for token, affiliation in mapping:
        if token in title:
            return affiliation
    return ""


def _should_replace_field(field: str, current_value: Any, new_value: Any, row: dict[str, Any]) -> bool:
    if new_value in (None, ""):
        return False
    if current_value in (None, ""):
        return True
    current_text = str(current_value)
    if field in {"name_ko", "series_name", "affiliation", "character_name"} and "?" * 3 in current_text:
        return True
    if field == "affiliation" and row.get("source_store") == "이치방쿠지":
        return current_text == "기타"
    return False


def _plain_text(source: str) -> str:
    source = IMG_RE.sub(_image_alt_text, source)
    text = re.sub(r"<script.*?</script>", " ", source, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = TEXT_TAG_RE.sub(" ", text)
    return html.unescape(re.sub(r"\s+", " ", text))


def _image_alt_text(match: re.Match[str]) -> str:
    alt = _first_group(ALT_RE, match.group(0)) or ""
    return f" {alt} "


def _first_group(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return html.unescape(match.group(1).strip()) if match else None


def _clean_title(title: str) -> str:
    title = html.unescape(title)
    title = title.split("｜", 1)[0].strip()
    return title or "一番くじ"


def _clean_prize_name(value: str) -> str | None:
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return None
    if re.fullmatch(r"img\d+", text, flags=re.IGNORECASE):
        return None
    if text in {"画像", "商品画像"}:
        return None
    return text


def _extract_tier(value: str) -> str | None:
    boxed_double_chance = re.match(
        r"^(\u3010[^\u3011]{1,40}\u3011\s*\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3)(?:\s|\u3000|$)",
        value,
    )
    if boxed_double_chance:
        return boxed_double_chance.group(1)
    boxed_numbered_prize = re.match(r"^(\u3010[^\u3011]{1,40}\u3011\s*[0-9\uff10-\uff19]+\u7b49)(?:\s|\u3000|$)", value)
    if boxed_numbered_prize:
        return boxed_numbered_prize.group(1)
    numbered_prize = re.match(r"^([0-9\uff10-\uff19]+\u7b49)(?:\s|\u3000|$)", value)
    if numbered_prize:
        return numbered_prize.group(1)
    if re.match(r"^\u30e9\u30b9\u30c8\u30ef\u30f3(?:\s|\u3000|$)", value):
        return "\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde"
    if re.match(r"^\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3(?:\s|\u3000|$)", value):
        return "\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3"
    leading_spaced_prize = re.match(r"^(.{1,40}\u8cde)(?:\s|\u3000|$)", value)
    if leading_spaced_prize and not leading_spaced_prize.group(1).startswith("\u4e00\u756a\u304f\u3058"):
        return leading_spaced_prize.group(1)
    leading_named_prize = re.match(r"^([^\s\u3000]{1,40}\u8cde)(?:\s|\u3000|$)", value)
    if leading_named_prize:
        return leading_named_prize.group(1)
    match = re.search(
        r"((?:[A-Z\uff21-\uff3a]|\u30e9\u30b9\u30c8\u30ef\u30f3|\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9)[^ \t\u3000]*\u8cde)",
        value,
    )
    return match.group(1) if match else None


def _strip_tier(value: str) -> str:
    value = re.sub(
        r"^\u3010[^\u3011]{1,40}\u3011\s*\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3(?:\s|\u3000)+",
        "",
        value,
    ).strip()
    value = re.sub(r"^\u3010[^\u3011]{1,40}\u3011\s*[0-9\uff10-\uff19]+\u7b49(?:\s|\u3000)+", "", value).strip()
    value = re.sub(r"^[0-9\uff10-\uff19]+\u7b49(?:\s|\u3000)+", "", value).strip()
    value = re.sub(r"^\u30e9\u30b9\u30c8\u30ef\u30f3(?:\s|\u3000)+", "", value).strip()
    value = re.sub(r"^\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3(?:\s|\u3000)+", "", value).strip()
    value = re.sub(r"^(?!\u4e00\u756a\u304f\u3058).{1,40}\u8cde(?:\s|\u3000)+", "", value).strip()
    value = re.sub(r"^[^\s\u3000]{1,40}\u8cde(?:\s|\u3000)+", "", value).strip()
    return re.sub(
        r"^(?:[A-Z\uff21-\uff3a]|\u30e9\u30b9\u30c8\u30ef\u30f3|\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9)[^ \t\u3000]*\u8cde\s*",
        "",
        value,
    ).strip()


def _format_date(match: re.Match[str]) -> str:
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def _extract_date(text: str) -> str | None:
    normalized = re.sub(r"\s+", " ", text)
    release_match = re.search(r"(?:■\s*)?発売日[:：]\s*(?:店頭販売[:：]\s*)?(.{0,100})", normalized)
    if release_match:
        release_text = release_match.group(1).split("■", 1)[0]
        if "未定" in release_text:
            return None
        exact_match = re.search(r"(20\d{2})[年./-]\s*(\d{1,2})[月./-]\s*(\d{1,2})", release_text)
        if exact_match:
            return _format_date(exact_match)
        return None

    detail_start = normalized.find("各等賞一覧")
    double_chance_start = normalized.find("ダブルチャンス")
    search_end = double_chance_start if double_chance_start != -1 else len(normalized)
    if detail_start != -1 and detail_start < search_end:
        candidate_text = normalized[detail_start:search_end]
    else:
        candidate_text = normalized[:search_end]
    match = re.search(r"(20\d{2})[年./-]\s*(\d{1,2})[月./-]\s*(\d{1,2})", candidate_text)
    if not match:
        return None
    return _format_date(match)


def _extract_price(text: str) -> int | None:
    normalized = text.translate(str.maketrans("０１２３４５６７８９，", "0123456789,"))
    label_match = re.search(r"(?:メーカー希望小売価格|価格)[:：]?\s*(?:1回|1個)?[^\d]{0,20}([\d,]+)\s*円", normalized)
    if label_match:
        return int(label_match.group(1).replace(",", ""))
    match = re.search(r"(?:1回|1個)[^\d]{0,12}([\d,]+)\s*円", normalized)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--campaign-file", type=Path, default=DEFAULT_CAMPAIGN_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--merge-seed", action="store_true")
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-campaigns", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--time-budget-seconds", type=float, default=None)
    args = parser.parse_args()

    campaigns = _campaigns_from_args(args.urls) or _campaigns_from_file(args.campaign_file) or DEFAULT_CAMPAIGNS
    campaigns = campaigns[: args.max_campaigns] if args.max_campaigns else campaigns
    all_rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    campaign_results: list[dict[str, Any]] = []
    started_at = time.monotonic()
    time_budget_exhausted = False
    for index, campaign in enumerate(campaigns):
        if args.time_budget_seconds is not None and time.monotonic() - started_at >= args.time_budget_seconds:
            time_budget_exhausted = True
            break
        if index:
            time.sleep(args.sleep)
        try:
            rows = extract_campaign(str(campaign["url"]), campaign)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            message = f"{type(error).__name__}: {error}"
            failures.append({"url": str(campaign["url"]), "error": message})
            campaign_results.append({"url": str(campaign["url"]), "rows": 0, "error": message})
            print(f"{campaign['url']}: skipped ({message})")
            continue
        campaign_results.append({"url": str(campaign["url"]), "rows": len(rows), "error": None})
        print(f"{campaign['url']}: {len(rows)} prize rows")
        all_rows.extend(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_rows)} rows to {args.output}")

    if args.merge_seed:
        created, updated = merge_into_seed(all_rows, args.seed)
        print(f"Merged into {args.seed}: created={created}, updated={updated}")
    else:
        print("Dry run only. Add --merge-seed to update catalog_seed_from_local.json.")

    report = {
        "campaigns": len(campaigns),
        "processed_campaigns": len(campaign_results),
        "rows": len(all_rows),
        "failures": len(failures),
        "time_budget_seconds": args.time_budget_seconds,
        "time_budget_exhausted": time_budget_exhausted,
        "failure_rows": failures,
        "campaign_results": campaign_results,
        "merged_seed": bool(args.merge_seed),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {args.report}")
    return 0


def _campaigns_from_args(urls: list[str]) -> list[dict[str, Any]]:
    return [{"url": url} for url in urls]


def _campaigns_from_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list):
        return []
    campaigns: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            campaigns.append({"url": item})
        elif isinstance(item, dict) and item.get("url"):
            campaigns.append(dict(item))
    return campaigns


if __name__ == "__main__":
    raise SystemExit(main())
