from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from catalog_normalize import is_generic_source_url


PRODUCT_DETAIL_PATTERNS = (
    re.compile(r"^https://chiikawamarket\.jp/(?:ko/)?products/[^/?#]+/?$", re.I),
    re.compile(r"^https://nagano-market\.jp/(?:ko/)?products/[^/?#]+/?$", re.I),
    re.compile(r"^https://chiikawamogumogu\.shop/products/[^/?#]+/?$", re.I),
    re.compile(r"^https://www\.animate-onlineshop\.jp/(?:products/detail\.php\?product_id=\d+|pd/\d+|(?:sphone/)?pn/.*/pd/\d+/?)", re.I),
    re.compile(r"^https://www\.enskyshop\.com/products/detail/\d+/?$", re.I),
    re.compile(r"^https://www\.goodsmile\.info/(?:ja|en)/product/\d+/?$", re.I),
    re.compile(r"^https://www\.goodsmile\.info/(?:ja|en)/product/\d+/.+\.html$", re.I),
    re.compile(r"^https://www\.goodsmile\.com/(?:ja|en|zh)/product/\d+(?:/[^?#]+)?/?$", re.I),
    re.compile(r"^https://www\.megahobby\.jp/products/item/\d+/?$", re.I),
    re.compile(r"^https://furyuprize\.com/item/\d+/?$", re.I),
    re.compile(r"^https://www\.furyu\.jp/news/20\d{2}/\d{2}/[^/?#]+/?$", re.I),
    re.compile(r"^https://file-origin\.charahiroba\.com/prize/item/detail\?id=\d+", re.I),
    re.compile(r"^https://fanding\.kr/@[^/]+/shop/\d+/?$", re.I),
    re.compile(r"^https://shop\.weverse\.io/[a-z]{2}/shop/[A-Z]{3}/artists/\d+/sales/\d+/?$", re.I),
    re.compile(r"^https://www\.taito\.co\.jp/prize/item/\d+/?$", re.I),
    re.compile(r"^https://www\.taito\.co\.jp/prize/\d+/?$", re.I),
    re.compile(r"^https://(?:www\.)?taito\.co\.jp/taito-prize/\d+/?$", re.I),
    re.compile(r"^https://bsp-prize\.jp/item/\d+/?$", re.I),
    re.compile(r"^https://bsp-prize\.jp/brand/\d+/item/\d+/?$", re.I),
    re.compile(r"^https://segaplaza\.jp/prize/[A-Za-z0-9_-]+/?$", re.I),
    re.compile(r"^https://info\.miku\.sega\.jp/\d+/?$", re.I),
    re.compile(r"^https://blog\.piapro\.net/20\d{2}/\d{2}/[a-z]\d{6,7}(?:-\d+)?\.html$", re.I),
    re.compile(r"^https://www\.kotobukiya\.co\.jp/product/detail/p\d+/?$", re.I),
    re.compile(r"^https://shop\.kotobukiya\.co\.jp/shop/g/g[^/?#]+/?$", re.I),
    re.compile(r"^https://www\.movic\.jp/shop/g/g[^/?#]+/?$", re.I),
    re.compile(r"^https://www\.amiami\.jp/top/detail/detail\?gcode=[^&#]+", re.I),
    re.compile(r"^https://www\.1999\.co\.jp/\d+/?$", re.I),
    re.compile(r"^https://www\.cospa\.com/cospa/detail/id/\d+/?$", re.I),
    re.compile(r"^https://animota\.net/products/[^/?#]+/?$", re.I),
    re.compile(r"^https://bc-onlinestore\.com/c/corabo/\d+/?$", re.I),
    re.compile(r"^https://frieren-anime\.jp/goods/[^/]+/\d+/?$", re.I),
    re.compile(r"^https://www\.nbcuni\.co\.jp/anime/[^/]+/goods/index\d+\.html$", re.I),
    re.compile(r"^https://p-bandai\.jp/item/item-\d+/?$", re.I),
    re.compile(r"^https://www\.bandai\.co\.jp/candy/products/20\d{2}/\d+\.html$", re.I),
    re.compile(r"^https://www\.pokemoncenter-online\.com/\d{8,14}\.html$", re.I),
    re.compile(r"^https://www\.re-ment\.co\.jp/product/r\d+/?$", re.I),
    re.compile(r"^https://store\.jp\.square-enix\.com/item/[A-Z0-9_]+\.html$", re.I),
    re.compile(r"^https://eu\.store\.square-enix-games\.com/[a-z0-9-]+/?$", re.I),
    re.compile(r"^https://apac\.store\.square-enix\.com/products/[a-z0-9-]+/?$", re.I),
    re.compile(r"^https://anime-store\.jp/(?:[a-z-]+/)?products/\d{8,14}(?:-[A-Za-z0-9]+)?/?$", re.I),
    re.compile(r"^https://www\.neowing\.co\.jp/product/[A-Z0-9_-]+/?$", re.I),
    re.compile(r"^https://www\.nin-nin-game\.com/[a-z]{2}/[^/]+/\d+-[^/?#]+\.html$", re.I),
    re.compile(r"^https://ninoma\.com/products/[a-z0-9-]+/?$", re.I),
    re.compile(r"^https://jujutsukaisen\.jp/goods/goods\d+\.php$", re.I),
    re.compile(r"^https://one-piece\.com/news/\d+/index\.html$", re.I),
    re.compile(r"^https://spy-family\.net/goods/goods\d+\.php$", re.I),
    re.compile(r"^https://www\.daiso-sangyo\.co\.jp/item/\d+/?$", re.I),
    re.compile(r"^https://shop\.asobistore\.jp/products/detail/[A-Za-z0-9_-]+/?$", re.I),
)

GENERIC_IMAGE_NAME_RE = re.compile(
    r"(^|[/_.-])(?:ogp?|og-image|share|sns|logo|banner|cover|hero|mainvisual|main-visual|noimage|no-image|placeholder|default)([/_.-]|$)",
    re.I,
)


def normalized_url(value: Any) -> str:
    url = str(value or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    return url


def is_product_specific_source_url(value: Any) -> bool:
    url = normalized_url(value)
    if not url or is_generic_source_url(url):
        return False
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return any(pattern.search(url) for pattern in PRODUCT_DETAIL_PATTERNS)


def looks_like_generic_image_url(value: Any) -> bool:
    url = normalized_url(value)
    if not url:
        return True
    parsed = urlsplit(url)
    path = parsed.path.rsplit("/", 1)[-1] or parsed.path
    return bool(GENERIC_IMAGE_NAME_RE.search(path))


def is_safe_source_image_pair(source_url: Any, image_url: Any) -> bool:
    url = normalized_url(image_url)
    source = normalized_url(source_url)
    if not is_product_specific_source_url(source):
        return False
    if not url.startswith(("http://", "https://")):
        return False
    if (
        "eu.store.square-enix-games.com/" in source
        and re.search(r"^https://cdn11\.bigcommerce\.com/s-uak4l72xa0/products/\d+/images/\d+/", url, re.I)
    ):
        return True
    return not looks_like_generic_image_url(url)
