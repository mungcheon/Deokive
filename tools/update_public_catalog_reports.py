from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import audit_public_catalog_safety
import audit_public_catalog_image_assets
import build_catalog_missing_image_actionability_public
import build_candidate_source_url_review_queue_public
import build_animation_category_action_queue_public
import build_animation_category_review_batches_public
import build_animation_category_split_review_public
import build_animation_category_unmatched_keyword_review_public
import build_deduplication_action_queue_public
import build_deduplication_fast_review_public
import build_ensky_cache_candidate_action_queue_public
import build_gotouchi_official_candidate_review_queue_public
import build_image_attachment_action_queue_public
import build_image_source_url_confirmed_template_public
import build_ichiban_prize_policy_issue_queue_public
import build_ichiban_prize_name_image_patch_candidates_public
import build_ichiban_prize_name_image_review_public
import build_ichiban_kuji_metadata_action_queue_public
import build_ichiban_kuji_metadata_fast_review_public
import build_ichiban_reissue_decision_template_public
import build_ichiban_reissue_deduplication_summary_public
import build_manual_source_url_search_queue_public
import build_missing_image_report_coverage_public
import build_missing_image_priority_public
import build_provider_missing_source_url_queue_public
import build_requested_focus_action_queue_public
import build_requested_focus_next_work_public
import build_source_discovery_next_focus_detail_candidates_public
import build_source_discovery_next_focus_fallback_queue_public
import build_source_discovery_next_focus_pack_fetch_audit_public
import build_source_discovery_next_focus_identity_candidate_review_public
import build_source_discovery_next_focus_pack_public
import build_source_discovery_next_focus_split_queues_public
import import_confirmed_deduplication_rows
import import_confirmed_catalog_field_rows
import import_confirmed_image_attachment_rows
import import_confirmed_source_discovery_rows


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PUBLIC_CATALOG = DATA / "catalog_public.json"
PUBLIC_META = DATA / "catalog_public_meta.json"
QUALITY = DATA / "catalog_quality_public.json"
IMAGE_BACKLOG = DATA / "catalog_image_backlog_public.json"
IMAGE_CANDIDATES = DATA / "catalog_image_candidate_review_public.json"
IMAGE_ASSET_AUDIT = DATA / "catalog_image_asset_audit_public.json"
MISSING_IMAGE_PRIORITY = DATA / "catalog_missing_image_priority_public.json"
SOURCE_DISCOVERY_STARTER_QUEUE = DATA / "source_discovery_starter_queue_public.json"
ANIMATE_MISSING_IMAGE_SEARCH = DATA / "animate_missing_image_search_public.json"
GOODSMILE_MISSING_IMAGE_SEARCH = DATA / "goodsmile_missing_image_search_public.json"
KOTOBUKIYA_MOVIC_MISSING_IMAGE_SEARCH = DATA / "kotobukiya_movic_missing_image_search_public.json"
JUMP_FURYU_TAITO_MISSING_IMAGE_SEARCH = DATA / "jump_furyu_taito_missing_image_search_public.json"
SECONDARY_OFFICIAL_MISSING_IMAGE_SEARCH = DATA / "secondary_official_missing_image_search_public.json"
MANUAL_MISSING_IMAGE_SOURCE_DISCOVERY = DATA / "manual_missing_image_source_discovery_public.json"
GENERIC_STOREFRONT_MISSING_IMAGE_SOURCE = DATA / "generic_storefront_missing_image_source_public.json"
MISSING_IMAGE_REPORT_COVERAGE = DATA / "catalog_missing_image_report_coverage_public.json"
ENSKY_CACHE_COVERAGE = DATA / "ensky_missing_image_cache_coverage_public.json"
ENSKY_CACHE_CANDIDATE_ACTION_QUEUE = DATA / "ensky_cache_candidate_action_queue_public.json"
ENSKY_SEARCH_PAGE_PROBE = DATA / "ensky_search_page_probe_public.json"
STELLIVE_FANDING_CANDIDATES = DATA / "stellive_fanding_candidates_public.json"
DEDUPLICATION = DATA / "catalog_deduplication_public.json"
DEDUPLICATION_REVIEW_BATCHES = DATA / "catalog_deduplication_review_batches_public.json"
DEDUPLICATION_ACTION_QUEUE = DATA / "catalog_deduplication_action_queue_public.json"
DEDUPLICATION_FAST_REVIEW = DATA / "catalog_deduplication_fast_review_public.json"
DEDUPLICATION_CONFIRMED_TEMPLATE = DATA / "catalog_deduplication_confirmed_template_public.json"
DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN = DATA / "catalog_deduplication_template_import_dry_run_public.json"
NAME_DUPLICATE_AUDIT = DATA / "catalog_name_duplicate_audit_public.json"
ANIMATION_CATEGORIES = DATA / "animation_goods_categories_public.json"
ANIMATION_CATEGORY_REVIEW_BATCHES = DATA / "animation_category_review_batches_public.json"
ANIMATION_CATEGORY_ACTION_QUEUE = DATA / "animation_category_action_queue_public.json"
ANIMATION_CATEGORY_SPLIT_REVIEW = DATA / "animation_category_split_review_public.json"
ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW = DATA / "animation_category_unmatched_keyword_review_public.json"
ANIMATION_CATEGORY_COVERAGE_AUDIT = DATA / "animation_category_coverage_audit_public.json"
ICHIIBAN_KUJI_HISTORY = DATA / "ichiban_kuji_history_public.json"
ICHIIBAN_KUJI_CAMPAIGNS = DATA / "ichiban_kuji_campaigns.json"
ICHIIBAN_KUJI_METADATA_PROBE = DATA / "ichiban_kuji_metadata_probe_public.json"
ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES = DATA / "ichiban_kuji_metadata_review_batches_public.json"
ICHIIBAN_KUJI_METADATA_ACTION_QUEUE = DATA / "ichiban_kuji_metadata_action_queue_public.json"
ICHIIBAN_KUJI_METADATA_FAST_REVIEW = DATA / "ichiban_kuji_metadata_fast_review_public.json"
ICHIIBAN_KUJI_HISTORICAL_ROADMAP = DATA / "ichiban_kuji_historical_roadmap_public.json"
ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT = DATA / "ichiban_kuji_prize_policy_audit_public.json"
ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE = DATA / "ichiban_kuji_prize_policy_issue_queue_public.json"
ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW = DATA / "ichiban_kuji_prize_name_image_review_public.json"
ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES = DATA / "ichiban_kuji_prize_name_image_patch_candidates_public.json"
ICHIIBAN_KUJI_REISSUE_DEDUPLICATION = DATA / "ichiban_kuji_reissue_deduplication_public.json"
ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE = DATA / "ichiban_kuji_reissue_decision_template_public.json"
GOTOUCHI = DATA / "gotouchi_chiikawa_image_candidates_public.json"
GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT = DATA / "gotouchi_representative_image_attachment_public.json"
GOTOUCHI_OFFICIAL_CANDIDATE_REVIEW_QUEUE = DATA / "gotouchi_official_candidate_review_queue_public.json"
REQUESTED = DATA / "requested_special_goods_public.json"
REQUESTED_FOCUS = DATA / "requested_focus_enrichment_public.json"
REQUESTED_FOCUS_REVIEW_BATCHES = DATA / "requested_focus_review_batches_public.json"
REQUESTED_FOCUS_ACTION_QUEUE = DATA / "requested_focus_action_queue_public.json"
REQUESTED_FOCUS_NEXT_WORK = DATA / "requested_focus_next_work_public.json"
DANGANRONPA_MISSING_MEDIA = DATA / "danganronpa_missing_media_public.json"
DANGANRONPA_PATCH_TEMPLATE_DRY_RUN = DATA / "danganronpa_patch_template_dry_run_public.json"
DANGANRONPA_GOODSMILE_PROBE = DATA / "danganronpa_goodsmile_probe_public.json"
DANGANRONPA_PRIZE_PROBE = DATA / "danganronpa_prize_probe_public.json"
DANGANRONPA_SOURCE_DETAIL_PROBE = DATA / "danganronpa_source_detail_probe_public.json"
GENERIC_SOURCE = DATA / "generic_source_cleanup_public.json"
GENERIC_SOURCE_PATCH_CANDIDATES = DATA / "generic_source_patch_candidates_public.json"
SOURCE_DETAIL = DATA / "source_detail_probe_public.json"
SOURCE_DISCOVERY = DATA / "source_discovery_queue_public.json"
SOURCE_DISCOVERY_REVIEW_BATCHES = DATA / "source_discovery_review_batches_public.json"
SOURCE_DISCOVERY_ACTION_QUEUE = DATA / "source_discovery_action_queue_public.json"
SOURCE_DISCOVERY_STORE_BOTTLENECKS = DATA / "source_discovery_store_bottlenecks_public.json"
SOURCE_DISCOVERY_FOCUS_PACKS = DATA / "source_discovery_focus_packs_public.json"
SOURCE_DISCOVERY_FOCUS_TEMPLATE = DATA / "source_discovery_focus_confirmed_template_public.json"
SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT = DATA / "source_discovery_focus_template_import_dry_run_public.json"
SOURCE_DISCOVERY_ROADMAP = DATA / "source_discovery_completion_roadmap_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_PACK = DATA / "source_discovery_next_focus_pack_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_PACK_IMPORT = DATA / "source_discovery_next_focus_pack_import_dry_run_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT = DATA / "source_discovery_next_focus_pack_fetch_audit_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES = DATA / "source_discovery_next_focus_detail_candidates_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT = DATA / "source_discovery_next_focus_metadata_field_import_dry_run_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE = DATA / "source_discovery_next_focus_fallback_queue_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_IMPORT = DATA / "source_discovery_next_focus_fallback_import_dry_run_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_EXACT_URL_QUEUE = DATA / "source_discovery_next_focus_exact_url_review_queue_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_BACKFILL_QUEUE = DATA / "source_discovery_next_focus_identity_backfill_queue_public.json"
SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_CANDIDATE_REVIEW_QUEUE = (
    DATA / "source_discovery_next_focus_identity_candidate_review_queue_public.json"
)
SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE = DATA / "source_detail_candidate_action_queue_public.json"
OFFICIAL_DETAIL_REVIEW_BATCHES = DATA / "official_detail_review_batches_public.json"
METADATA_BACKLOG = DATA / "catalog_metadata_backlog_public.json"
METADATA_REVIEW_BATCHES = DATA / "catalog_metadata_review_batches_public.json"
METADATA_ACTION_QUEUE = DATA / "catalog_metadata_action_queue_public.json"
IMAGE_ENRICHMENT_BATCHES = DATA / "catalog_image_enrichment_batches_public.json"
IMAGE_ATTACHMENT_ACTION_QUEUE = DATA / "catalog_image_attachment_action_queue_public.json"
IMAGE_SOURCE_URL_CONFIRMED_TEMPLATE = DATA / "catalog_image_source_url_confirmed_template_public.json"
MANUAL_SOURCE_URL_SEARCH_QUEUE = DATA / "catalog_manual_source_url_search_queue_public.json"
PROVIDER_MISSING_SOURCE_URL_QUEUE = DATA / "catalog_provider_missing_source_url_queue_public.json"
CANDIDATE_SOURCE_URL_REVIEW_QUEUE = DATA / "catalog_candidate_source_url_review_queue_public.json"
IMAGE_ATTACHMENT_CONFIRMED_TEMPLATE = DATA / "catalog_image_attachment_confirmed_template_public.json"
IMAGE_ATTACHMENT_TEMPLATE_IMPORT_DRY_RUN = DATA / "catalog_image_attachment_template_import_dry_run_public.json"
MISSING_IMAGE_ACTIONABILITY = DATA / "catalog_missing_image_actionability_public.json"
CONFIRMED_IMPORT_READINESS = DATA / "catalog_confirmed_import_readiness_public.json"
EXECUTION_PLAN = DATA / "catalog_execution_plan_public.json"
OPERATIONS_REPORT = DATA / "catalog_operations_public.json"
AGENT_WORK_QUEUE = DATA / "catalog_agent_work_queue_public.json"
APP_FOLDER_VISUAL_AUDIT = ROOT / "server" / "app_folder_visual_catalog_audit.json"

MAX_AGENT_WORK_QUEUE_BATCHES = 160

OFFICIAL_SEARCH_TEMPLATES = {
    "애니메이트": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
    "엔스카이": "https://www.enskyshop.com/products/list?name={query}",
    "굿스마일컴퍼니": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "코토부키야": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "Movic": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "FuRyu": "https://furyuprize.com/search?keyword={query}",
    "Taito": "https://www.taito.co.jp/prize?keyword={query}",
    "AmiAmi": "https://www.amiami.jp/top/search/list?s_keywords={query}",
    "Cospa": "https://www.cospa.com/cospa/itemlist/keyword/{query}",
    "메가하우스": "https://www.megahobby.jp/?s={query}",
    "반다이": "https://p-bandai.jp/search/?q={query}",
    "점프 캐릭터즈 스토어": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "무기와라스토어": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "Banpresto": "https://bsp-prize.jp/search/?keyword={query}",
    "SEGA": "https://segaplaza.jp/search/?word={query}",
    "치이카와 마켓": "https://chiikawamarket.jp/search?q={query}",
    "치이카와 모구모구 혼포": "https://chiikawamogumogu.shop/search?q={query}",
    "치이카와 온라인 쿠지": "https://online-kuji.chiikawamarket.jp/search?q={query}",
    "Re-ment": "https://www.re-ment.co.jp/?s={query}",
    "Stellive Store": "https://stellive.fanding.kr/search?keyword={query}",
    "JYP SHOP": "https://en.thejypshop.com/product/search.html?keyword={query}",
    "산리오": "https://shop.sanrio.co.jp/search?keyword={query}",
    "디즈니 스토어": "https://store.disney.co.jp/search?q={query}",
    "가샤폰": "https://gashapon.jp/search/?q={query}",
    "MINISO": "https://www.miniso.com/search?keyword={query}",
    "MINISO 중국": "https://www.miniso.com/search?keyword={query}",
    "ALTER": "https://www.google.com/search?q=site%3Aalter-web.jp%20{query}",
    "Phat! Company": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
    "Bandai Premium": "https://p-bandai.jp/search/?q={query}",
    "Hololive Production Official Shop": "https://shop.hololivepro.com/en/search?q={query}",
    "SM STORE": "https://global.shop.smtown.com/search?q={query}",
    "YG SELECT": "https://en.ygselect.com/product/search.html?keyword={query}",
    "귀멸의 칼날 공식": "https://www.google.com/search?q=site%3Awebshop-global.ufotable.co.jp%20{query}",
    "카도카와": "https://www.amiami.com/eng/search/list/?s_keywords={query}%20KADOKAWA",
    "Algonavis": "https://bushiroad-store.com/search?q={query}",
    "Hobby Max International": "https://www.amiami.com/eng/search/list/?s_keywords={query}%20HOBBY%20MAX",
    "STARSHIP STORE": "https://www.starship-square.com/product/search.html?keyword={query}",
    "CUBE STORE": "https://www.google.com/search?q=site%3Acubee.co.kr%20{query}",
    "IST STORE": "https://www.google.com/search?q=site%3Ashop.weverse.io%20{query}",
    "KQ FELLAZ": "https://www.google.com/search?q=site%3Akqshop.kr%20{query}",
    "롯데웰푸드": "https://www.google.com/search?q=site%3Alottewellfood.com%20{query}",
    "점프 숍": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
    "이세계아이돌 공식 굿즈": "https://www.google.com/search?q=site%3Awithmuulive.com%20{query}",
    "이세계아이돌 팝업스토어": "https://www.google.com/search?q=site%3Awithmuulive.com%20{query}",
    "치이카와 중국 팝업스토어": "https://www.google.com/search?q=site%3Ax.com%2Fchiikawa_kouhou%20{query}",
    "치이카와샵 용산": "https://www.google.com/search?q=site%3Ax.com%2Fchiikawashop_kr%20{query}",
}

LICENSED_RETAILER_STORES = {"AmiAmi"}
GENERIC_STOREFRONT_URLS = {
    "https://fanding.kr/@stellive/shop",
    "https://shop.weverse.io/home",
    "https://www.pokemoncenter-online.com",
    "https://www.pokemoncenter-online.com/",
}
DISCOVERY_PRIORITY = {
    "official_search_url_available": 10,
    "licensed_retailer_search_review": 20,
    "manual_official_research": 40,
}
DEDUPLICATION_KEY_PRIORITY = {
    "barcode": 10,
    "source_url": 20,
    "source_url_normalized_name": 25,
    "image_url": 30,
    "image_url_normalized_name": 35,
}

ANIMATION_STORES = {
    "AmiAmi",
    "Cospa",
    "FuRyu",
    "Movic",
    "Re-ment",
    "Taito",
    "굿스마일컴퍼니",
    "귀멸의 칼날 공식",
    "메가하우스",
    "무기와라스토어",
    "반다이",
    "애니메이트",
    "엔스카이",
    "점프 캐릭터즈 스토어",
    "점프 숍",
    "카도카와",
    "코토부키야",
}

CATEGORY_FAMILIES = {
    "figure": {"피규어", "미니어처", "리플리카", "캡슐토이"},
    "plush": {"인형", "마스코트"},
    "badge": {"캔뱃지"},
    "acrylic": {"아크릴 스탠드"},
    "keyring": {"키링", "아크릴 키링"},
    "stationery": {"문구", "클리어파일", "카드", "트레이딩 카드", "스티커", "색지", "카드/브로마이드"},
    "daily_goods": {"머그컵", "타월", "가방", "생활잡화", "액세서리", "클리어 보틀", "파우치", "식품"},
    "display_goods": {"태피스트리", "포스터", "보드"},
    "apparel": {"의류"},
    "fan_goods": {"응원용품", "응원봉", "콜라보 굿즈"},
}

FAMILY_VISUALS = {
    "figure": {"icon_key": "toys", "color_hint": "teal", "color_hex": "0xFF14B8A6"},
    "plush": {"icon_key": "face", "color_hint": "pink", "color_hex": "0xFFFF8FC3"},
    "badge": {"icon_key": "badge", "color_hint": "rose", "color_hex": "0xFFC8244F"},
    "acrylic": {"icon_key": "view_carousel", "color_hint": "sky", "color_hex": "0xFF7DB7FF"},
    "keyring": {"icon_key": "local_offer", "color_hint": "amber", "color_hex": "0xFFFFC857"},
    "stationery": {"icon_key": "sticky_note", "color_hint": "lavender", "color_hex": "0xFFB197FC"},
    "daily_goods": {"icon_key": "inventory", "color_hint": "emerald", "color_hex": "0xFF10B981"},
    "display_goods": {"icon_key": "photo", "color_hint": "indigo", "color_hex": "0xFF4F46E5"},
    "apparel": {"icon_key": "style", "color_hint": "slate", "color_hex": "0xFF64748B"},
    "fan_goods": {"icon_key": "celebration", "color_hint": "orange", "color_hex": "0xFFFF9F43"},
    "other": {"icon_key": "category", "color_hint": "neutral", "color_hex": "0xFF9CA3AF"},
}

FOLDER_COLOR_PALETTE = [
    {"color_hint": "wine", "color_hex": "0xFF7F1D2D", "sort_order": 10, "color_group": "rose"},
    {"color_hint": "rose", "color_hex": "0xFFC8244F", "sort_order": 20, "color_group": "rose"},
    {"color_hint": "red", "color_hex": "0xFFD64562", "sort_order": 30, "color_group": "rose"},
    {"color_hint": "coral", "color_hex": "0xFFFF6B6B", "sort_order": 40, "color_group": "rose"},
    {"color_hint": "hot_pink", "color_hex": "0xFFFF6FAE", "sort_order": 50, "color_group": "pink"},
    {"color_hint": "pink", "color_hex": "0xFFFF8FC3", "sort_order": 60, "color_group": "pink"},
    {"color_hint": "blush", "color_hex": "0xFFFFC2D8", "sort_order": 70, "color_group": "pink"},
    {"color_hint": "peach", "color_hex": "0xFFFF936A", "sort_order": 80, "color_group": "orange"},
    {"color_hint": "orange", "color_hex": "0xFFFF9F43", "sort_order": 90, "color_group": "orange"},
    {"color_hint": "amber", "color_hex": "0xFFFFC857", "sort_order": 100, "color_group": "yellow"},
    {"color_hint": "yellow", "color_hex": "0xFFFFD84D", "sort_order": 110, "color_group": "yellow"},
    {"color_hint": "cream", "color_hex": "0xFFFFF7D6", "sort_order": 120, "color_group": "yellow"},
    {"color_hint": "sand", "color_hex": "0xFFC8A978", "sort_order": 130, "color_group": "neutral_warm"},
    {"color_hint": "beige", "color_hex": "0xFFF0DFC2", "sort_order": 140, "color_group": "neutral_warm"},
    {"color_hint": "olive", "color_hex": "0xFF84CC16", "sort_order": 150, "color_group": "green"},
    {"color_hint": "lime", "color_hex": "0xFFA3E635", "sort_order": 160, "color_group": "green"},
    {"color_hint": "green", "color_hex": "0xFF42A866", "sort_order": 170, "color_group": "green"},
    {"color_hint": "emerald", "color_hex": "0xFF10B981", "sort_order": 180, "color_group": "green"},
    {"color_hint": "mint", "color_hex": "0xFF28D6C8", "sort_order": 190, "color_group": "teal"},
    {"color_hint": "teal", "color_hex": "0xFF14B8A6", "sort_order": 200, "color_group": "teal"},
    {"color_hint": "cyan", "color_hex": "0xFF22D3EE", "sort_order": 210, "color_group": "cyan"},
    {"color_hint": "sky", "color_hex": "0xFF7DB7FF", "sort_order": 220, "color_group": "blue"},
    {"color_hint": "blue", "color_hex": "0xFF5BA7F7", "sort_order": 230, "color_group": "blue"},
    {"color_hint": "navy", "color_hex": "0xFF2E4A7D", "sort_order": 240, "color_group": "blue"},
    {"color_hint": "indigo", "color_hex": "0xFF4F46E5", "sort_order": 250, "color_group": "violet"},
    {"color_hint": "violet", "color_hex": "0xFF8B5CF6", "sort_order": 260, "color_group": "violet"},
    {"color_hint": "lavender", "color_hex": "0xFFB197FC", "sort_order": 270, "color_group": "violet"},
    {"color_hint": "purple", "color_hex": "0xFFA78BFA", "sort_order": 280, "color_group": "violet"},
    {"color_hint": "white", "color_hex": "0xFFFFFFFF", "sort_order": 290, "color_group": "neutral"},
    {"color_hint": "neutral", "color_hex": "0xFF9CA3AF", "sort_order": 300, "color_group": "neutral"},
    {"color_hint": "slate", "color_hex": "0xFF64748B", "sort_order": 310, "color_group": "neutral"},
    {"color_hint": "graphite", "color_hex": "0xFF374151", "sort_order": 320, "color_group": "neutral"},
]

FAMILY_ICON_OPTIONS = {
    "figure": ["toys", "figure", "miniature", "smart_toy", "extension", "blind_box", "lottery_prize", "casino"],
    "plush": ["face", "plush", "mood", "favorite", "main_character", "costume", "smart_toy", "toys"],
    "badge": ["badge", "can_badge", "pin", "medal", "star", "premium", "verified", "new_releases"],
    "acrylic": ["view_carousel", "acrylic_stand", "standee", "acrylic_keyring", "display_case", "frame", "photo_album", "grid"],
    "keyring": ["local_offer", "keyring", "acrylic_keyring", "tag", "loyalty", "label_tag", "ticket", "activity"],
    "stationery": ["sticky_note", "sticker", "clear_file", "postcard", "article", "draw", "book", "diary"],
    "daily_goods": ["inventory", "bag", "pouch", "coffee_mug", "basket", "backpack", "gift", "storefront"],
    "display_goods": ["photo", "poster", "collections", "wallpaper", "image", "frame", "panorama", "slideshow"],
    "apparel": ["style", "apparel", "checkroom", "laundry", "towel", "badge", "accessibility", "sealed"],
    "fan_goods": ["celebration", "campaign", "flashlight", "favorite", "event", "limited_goods", "collab_goods", "preorder"],
    "other": ["category", "folder", "folder_special", "inventory", "package", "archive", "source", "dashboard"],
}

CANONICAL_CATEGORY_SUGGESTIONS = {
    "클리어파일": "문구",
    "카드": "문구",
    "미니어처": "피규어",
    "트레이딩 카드": "문구",
    "스티커": "문구",
    "클리어 보틀": "생활잡화",
    "파우치": "가방",
    "기타 굿즈": "액세서리",
}

UNKNOWN_CATEGORY_REVIEW_SUGGESTIONS = {
    "굿즈": {
        "suggested_family": "other",
        "suggested_category": "기타 굿즈",
        "color_hint": "neutral",
        "primary_icon_key": "category",
        "review_priority": 70,
        "reason": "Broad catch-all category; inspect names before moving to a specific folder family.",
    },
    "아크릴": {
        "suggested_family": "acrylic",
        "suggested_category": "아크릴 스탠드",
        "color_hint": "sky",
        "primary_icon_key": "view_carousel",
        "review_priority": 20,
        "reason": "Most acrylic goods should be split into acrylic stand/keyholder/card after name review.",
    },
    "참": {
        "suggested_family": "keyring",
        "suggested_category": "키링",
        "color_hint": "amber",
        "primary_icon_key": "local_offer",
        "review_priority": 30,
        "reason": "Charm items usually behave like keyrings in the app folder model.",
    },
    "포스터": {
        "suggested_family": "display_goods",
        "suggested_category": "포스터",
        "color_hint": "indigo",
        "primary_icon_key": "photo",
        "review_priority": 25,
        "reason": "Poster is a display goods folder, but should remain distinct from bromide/photo cards.",
    },
    "컵": {
        "suggested_family": "daily_goods",
        "suggested_category": "머그컵",
        "color_hint": "emerald",
        "primary_icon_key": "inventory",
        "review_priority": 40,
        "reason": "Cup items fit daily goods; verify whether they are mugs, tumblers, or glassware.",
    },
    "캡슐토이": {
        "suggested_family": "figure",
        "suggested_category": "캡슐토이",
        "color_hint": "teal",
        "primary_icon_key": "toys",
        "review_priority": 35,
        "reason": "Capsule toy is usually a small figure/miniature product family.",
    },
    "기타 굿즈": {
        "suggested_family": "other",
        "suggested_category": "기타 굿즈",
        "color_hint": "neutral",
        "primary_icon_key": "category",
        "review_priority": 80,
        "reason": "Already a catch-all category; keep broad unless names clearly identify a better folder.",
    },
    "식품": {
        "suggested_family": "daily_goods",
        "suggested_category": "식품",
        "color_hint": "emerald",
        "primary_icon_key": "inventory",
        "review_priority": 50,
        "reason": "Food items should stay separate from character goods but use daily goods visual treatment.",
    },
}

PUBLIC_FIELDS = [
    "catalog_index",
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
    "local_image_path",
    "source_url",
    "source_store",
    "release_date",
]

PRIVACY_NEEDLES = [
    "C:\\Users",
    "/Users/",
    "localhost",
    "127.0.0.1",
    "deokive_dev.db",
    "password=",
    "secret=",
    "api_key=",
    "ghp_",
    "github_pat_",
    "sk-",
]


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def app_folder_visual_catalog_summary() -> dict[str, Any]:
    audit = load_json(APP_FOLDER_VISUAL_AUDIT, {})
    if not isinstance(audit, dict) or not audit:
        return {}
    return {
        "source": "app_folder_visual_catalog_audit",
        "source_files": [
            "lib/config/app_palette_catalog.dart",
            "lib/config/app_icon_catalog.dart",
        ],
        "icon_count": int(audit.get("icon_count") or 0),
        "icon_group_count": int(audit.get("icon_group_count") or 0),
        "icon_groups": audit.get("icon_groups") or [],
        "color_count": int(audit.get("color_count") or 0),
        "unique_color_count": int(audit.get("unique_color_count") or 0),
        "palette_section_count": int(audit.get("palette_section_count") or 0),
        "palette_sections": audit.get("palette_sections") or [],
        "palette_color_families": audit.get("palette_color_families") or [],
        "palette_picker_order": audit.get("palette_picker_order") or [],
        "palette_sorted_by_family": bool(
            audit.get("palette_sort", {}).get("section_order_matches_expected")
            and audit.get("palette_sort", {}).get("section_order_monotonic")
        ),
        "animation_visuals_covered": bool(audit.get("animation_visuals_covered")),
        "duplicate_icon_keys": audit.get("duplicate_icon_keys") or [],
        "duplicate_colors": audit.get("duplicate_colors") or [],
    }


TIMESTAMP_ONLY_KEYS = {"generated_at", "summary_generated_at"}


def write_json(path: Path, data: Any) -> None:
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        existing_text = path.read_text(encoding="utf-8-sig")
        if existing_text == serialized:
            return
        try:
            existing_data = json.loads(existing_text)
        except json.JSONDecodeError:
            existing_data = None
        if isinstance(existing_data, dict) and isinstance(data, dict):
            existing_without_generated_at = {
                key: value
                for key, value in existing_data.items()
                if key not in TIMESTAMP_ONLY_KEYS
            }
            data_without_generated_at = {
                key: value for key, value in data.items() if key not in TIMESTAMP_ONLY_KEYS
            }
            if existing_without_generated_at == data_without_generated_at:
                return
    path.write_text(serialized, encoding="utf-8")


def _dict_delta(actual: dict[str, Any], expected: dict[str, Any], limit: int = 12) -> dict[str, dict[str, Any]]:
    delta: dict[str, dict[str, Any]] = {}
    for key in sorted(set(actual) | set(expected)):
        if actual.get(key) != expected.get(key):
            delta[key] = {"actual": actual.get(key), "expected": expected.get(key)}
            if len(delta) >= limit:
                break
    return delta


def enrich_image_action_queue_source_url_review(
    image_action_queue: dict[str, Any],
    source_url_template: dict[str, Any],
    existing_action_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    template_rows = _image_source_candidate_rows_by_index(source_url_template)
    existing_rows = _image_source_candidate_rows_by_index(existing_action_queue or {})
    enriched = dict(image_action_queue)
    enriched_batch = []
    for row in image_action_queue.get("next_source_url_review_batch") or []:
        if not isinstance(row, dict):
            continue
        template = _find_image_source_candidate_row(row, template_rows)
        existing = _find_image_source_candidate_row(row, existing_rows)
        if not isinstance(template, dict):
            enriched_batch.append(_merge_existing_image_source_candidate(row, existing))
            continue
        enriched_row = {
            **row,
            "candidate_status": template.get("candidate_status"),
            "candidate_review_lane": template.get("candidate_review_lane"),
            "candidate_score": template.get("candidate_score"),
            "candidate_count": template.get("candidate_count"),
            "candidate_options": template.get("candidate_options") or [],
            "source_url_review_lane": template.get("source_url_review_lane"),
            "source_url_review_blockers": template.get("source_url_review_blockers")
            or [],
            "match_diagnostics": template.get("match_diagnostics") or {},
            "fallback_search_queries": template.get("fallback_search_queries") or [],
            "store_search_hints": template.get("store_search_hints") or {},
        }
        enriched_batch.append(
            _merge_existing_image_source_candidate(enriched_row, existing)
        )
    enriched["next_source_url_review_batch"] = enriched_batch
    enriched["batches"] = _merge_existing_image_source_candidate_batches(
        image_action_queue.get("batches") or [],
        template_rows,
        existing_rows,
    )
    summary = dict(enriched.get("summary") or {})
    summary["source_url_candidate_status_counts"] = _count_pairs(
        enriched_batch, "candidate_status"
    )
    summary["source_url_review_lane_counts"] = _count_pairs(
        enriched_batch, "source_url_review_lane"
    )
    enriched["summary"] = summary
    return enriched


def _merge_existing_image_source_candidate_batches(
    batches: list[dict[str, Any]],
    template_rows: dict[tuple[str, Any], dict[str, Any]],
    existing_rows: dict[tuple[str, Any], dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched_batches = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        enriched_batch = dict(batch)
        if batch.get("workflow") != "replace_generic_source_then_extract_image":
            enriched_batches.append(enriched_batch)
            continue
        items = []
        for item in batch.get("items") or []:
            if not isinstance(item, dict):
                continue
            template = _find_image_source_candidate_row(item, template_rows)
            existing = _find_image_source_candidate_row(item, existing_rows)
            enriched_item = dict(item)
            if isinstance(template, dict):
                enriched_item.update(
                    {
                        "candidate_status": template.get("candidate_status"),
                        "candidate_review_lane": template.get(
                            "candidate_review_lane"
                        ),
                        "candidate_score": template.get("candidate_score"),
                        "candidate_count": template.get("candidate_count"),
                        "candidate_options": template.get("candidate_options")
                        or [],
                        "source_url_review_lane": template.get(
                            "source_url_review_lane"
                        ),
                        "source_url_review_blockers": template.get(
                            "source_url_review_blockers"
                        )
                        or [],
                        "match_diagnostics": template.get("match_diagnostics")
                        or {},
                        "fallback_search_queries": template.get(
                            "fallback_search_queries"
                        )
                        or [],
                        "store_search_hints": template.get("store_search_hints")
                        or {},
                    }
                )
            items.append(_merge_existing_image_source_candidate(enriched_item, existing))
        enriched_batch["items"] = items
        enriched_batches.append(enriched_batch)
    return enriched_batches


def _image_source_candidate_rows_by_index(
    existing_action_queue: dict[str, Any],
) -> dict[tuple[str, Any], dict[str, Any]]:
    rows: dict[tuple[str, Any], dict[str, Any]] = {}

    def add_row(row: dict[str, Any]) -> None:
        for key in _image_source_candidate_identity_keys(row):
            if key not in rows or row.get("candidate_options"):
                rows[key] = row

    for row in existing_action_queue.get("next_source_url_review_batch") or []:
        if isinstance(row, dict):
            add_row(row)
    for row in existing_action_queue.get("items") or []:
        if isinstance(row, dict):
            add_row(row)
    for batch in existing_action_queue.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        for row in batch.get("items") or []:
            if not isinstance(row, dict):
                continue
            add_row(row)
    return rows


def _find_image_source_candidate_row(
    row: dict[str, Any],
    rows_by_key: dict[tuple[str, Any], dict[str, Any]],
) -> dict[str, Any] | None:
    for key in _image_source_candidate_identity_keys(row):
        existing = rows_by_key.get(key)
        if isinstance(existing, dict):
            return existing
    return None


def _image_source_candidate_identity_keys(row: dict[str, Any]) -> list[tuple[str, Any]]:
    keys: list[tuple[str, Any]] = []
    for field in ("row_index", "catalog_index"):
        value = row.get(field)
        if value not in (None, ""):
            keys.append((field, value))
    return keys


def _merge_existing_image_source_candidate(
    row: dict[str, Any],
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(existing, dict):
        return row
    preserved = dict(row)
    if not row.get("candidate_options"):
        _copy_non_empty_image_source_candidate_context(preserved, existing)
    _merge_existing_image_source_nested_review_context(preserved, existing)
    return preserved


def _copy_non_empty_image_source_candidate_context(
    target: dict[str, Any],
    source: dict[str, Any],
) -> None:
    for key in _IMAGE_SOURCE_CANDIDATE_CONTEXT_KEYS:
        value = source.get(key)
        if value not in (None, "", [], {}):
            target[key] = value


_IMAGE_SOURCE_CANDIDATE_CONTEXT_KEYS = (
    "candidate_status",
    "candidate_review_lane",
    "candidate_score",
    "candidate_count",
    "candidate_options",
    "source_url_review_lane",
    "source_url_review_blockers",
    "match_diagnostics",
    "fallback_search_queries",
    "store_search_hints",
)


def _merge_existing_image_source_nested_review_context(
    row: dict[str, Any],
    existing: dict[str, Any],
) -> None:
    for template_key in ("source_url_import_template", "catalog_field_import_template"):
        target_template = row.get(template_key)
        existing_template = existing.get(template_key)
        if not isinstance(target_template, dict) or not isinstance(
            existing_template, dict
        ):
            continue
        merged_template = dict(target_template)
        _copy_non_empty_image_source_candidate_context(
            merged_template, existing_template
        )
        _merge_existing_source_url_review_guidance(
            merged_template, existing_template
        )
        row[template_key] = merged_template

    _merge_existing_source_url_review_guidance(row, existing)


def _merge_existing_source_url_review_guidance(
    target: dict[str, Any],
    source: dict[str, Any],
) -> None:
    target_guidance = target.get("source_url_review_guidance")
    source_guidance = source.get("source_url_review_guidance")
    if not isinstance(target_guidance, dict) or not isinstance(source_guidance, dict):
        return
    merged_guidance = dict(target_guidance)
    for key in (
        "candidate_status",
        "candidate_review_note",
        "candidate_summary",
        "candidate_source_url",
        "top_candidate_title",
    ):
        value = source_guidance.get(key)
        if value not in (None, "", [], {}):
            merged_guidance[key] = value
    target["source_url_review_guidance"] = merged_guidance


def _count_pairs(rows: list[dict[str, Any]], field: str) -> list[list[Any]]:
    counts = Counter(
        str(row.get(field) or "").strip()
        for row in rows
        if isinstance(row, dict) and str(row.get(field) or "").strip()
    )
    return [[key, value] for key, value in counts.most_common()]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _catalog_index_sequence(report: dict[str, Any]) -> list[Any]:
    return [
        item.get("catalog_index")
        for item in report.get("items", [])
        if isinstance(item, dict)
    ]


def fetch_audit_matches_focus_pack(
    fetch_audit: dict[str, Any],
    focus_pack: dict[str, Any],
) -> bool:
    if not isinstance(fetch_audit, dict) or not isinstance(focus_pack, dict):
        return False
    summary = fetch_audit.get("summary")
    if not isinstance(summary, dict) or summary.get("broad_result_link_threshold") != (
        build_source_discovery_next_focus_pack_fetch_audit_public.BROAD_RESULT_LINK_THRESHOLD
    ):
        return False
    return bool(fetch_audit.get("items")) and _catalog_index_sequence(
        fetch_audit
    ) == _catalog_index_sequence(focus_pack)


def present(value: Any) -> bool:
    return value not in (None, "", [], {})


def catalog_currency_invariant_findings(catalog: dict[str, Any]) -> list[str]:
    items = catalog.get("items", [])
    if not isinstance(items, list):
        return ["catalog_public.items is not a list"]

    findings: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            findings.append(f"catalog_public.items[{index}] is not an object")
            continue

        official_price_jpy = item.get("official_price_jpy")
        if not present(official_price_jpy):
            continue

        explicit_currency_fields = {
            "paid_currency": item.get("paid_currency"),
            "purchase_currency": item.get("purchase_currency"),
            "price_currency": item.get("price_currency"),
            "price_currency_code": item.get("price_currency_code"),
        }
        default_purchase = item.get("default_purchase")
        if isinstance(default_purchase, dict):
            explicit_currency_fields["default_purchase.currency"] = default_purchase.get("currency")
            explicit_currency_fields["default_purchase.price_currency_code"] = default_purchase.get(
                "price_currency_code"
            )

        for field, value in explicit_currency_fields.items():
            if present(value) and str(value).upper() != "JPY":
                findings.append(
                    f"catalog row {item.get('catalog_index', index)} has official_price_jpy but {field}={value}"
                )

    return findings


def missing_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {field: sum(1 for item in items if not present(item.get(field))) for field in PUBLIC_FIELDS}


def coverage(missing: dict[str, int], rows: int, fields: list[str]) -> dict[str, float]:
    if rows <= 0:
        return {field: 0.0 for field in fields}
    return {field: round((rows - missing.get(field, 0)) / rows, 4) for field in fields}


def copy_report_summary(path: Path, key: str) -> dict[str, Any]:
    data = load_json(path, {})
    summary = data.get("summary") if isinstance(data, dict) else None
    if not isinstance(summary, dict):
        summary = {}
    return {"public_report": f"data/{path.name}", **summary}


def normalize_ichiban_prize_patch_candidate_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        summary = {}
        report["summary"] = summary

    candidates = [row for row in report.get("candidates", []) if isinstance(row, dict)]
    confirmed_rows = sum(1 for row in candidates if row.get("manual_confirmed") is True)
    open_candidate_rows = max(0, len(candidates) - confirmed_rows)
    summary["candidate_rows"] = len(candidates)
    summary["manual_confirmed_rows"] = confirmed_rows
    summary["open_candidate_rows"] = open_candidate_rows
    return summary


def copy_import_dry_run(path: Path) -> dict[str, Any]:
    data = load_json(path, {})
    if isinstance(data, dict) and isinstance(data.get("summary"), dict):
        return {
            "public_report": f"data/{path.name}",
            **data["summary"],
        }
    return {
        "public_report": f"data/{path.name}",
        "write": bool(data.get("write")) if isinstance(data, dict) else False,
        "updated_rows": int(data.get("updated_rows") or 0) if isinstance(data, dict) else 0,
        "skipped_rows": int(data.get("skipped_rows") or 0) if isinstance(data, dict) else 0,
        "skip_reason_counts": data.get("skip_reason_counts") if isinstance(data, dict) else [],
    }


def build_deduplication_template_import_dry_run_public(
    template: dict[str, Any],
    catalog: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    seed_rows = [row for row in catalog.get("items", []) if isinstance(row, dict)]
    result = import_confirmed_deduplication_rows.import_rows(template, seed_rows)
    items = [item for item in template.get("items", []) if isinstance(item, dict)]
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])

    def confirmed(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "confirmed",
            "확인",
            "확정",
        }

    ready_decision_rows = sum(
        1
        for item in items
        if confirmed(item.get("manual_confirmed"))
        and confirmed(item.get("same_sellable_product_confirmed"))
        and str(item.get("decision") or "").strip()
        in import_confirmed_deduplication_rows.VALID_DECISIONS
        and isinstance(item.get("keep_catalog_index"), int)
        and bool(item.get("drop_catalog_indexes"))
    )
    drop_candidate_rows = sum(len(item.get("drop_catalog_indexes") or []) for item in items)
    summary = {
        "template_items": len(items),
        "manual_confirmed_rows": sum(1 for item in items if confirmed(item.get("manual_confirmed"))),
        "same_sellable_product_confirmed_rows": sum(
            1 for item in items if confirmed(item.get("same_sellable_product_confirmed"))
        ),
        "ready_decision_rows": ready_decision_rows,
        "drop_candidate_rows": drop_candidate_rows,
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "blocked_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
        "write": False,
    }
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "scope": "catalog_deduplication_template_import_dry_run",
        "summary": summary,
        "write": False,
        "queue": str(DEDUPLICATION_CONFIRMED_TEMPLATE.relative_to(ROOT)).replace("\\", "/"),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "blocked_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
        "automation_policy": {
            "import_tool": "tools/import_confirmed_deduplication_rows.py",
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
            "write_enabled": False,
            "required_before_write": [
                "manual_confirmed=true",
                "same_sellable_product_confirmed=true",
                "decision in drop_duplicates/merge_duplicates/remove_duplicate_rows",
                "keep_catalog_index and drop_catalog_indexes verified against current catalog_public.json",
            ],
        },
    }


def build_image_attachment_template_import_dry_run_public(
    template: dict[str, Any],
    catalog: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    seed_rows = [row for row in catalog.get("items", []) if isinstance(row, dict)]
    result = import_confirmed_image_attachment_rows.import_rows(template, seed_rows)
    items = [item for item in template.get("items", []) if isinstance(item, dict)]
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])

    def confirmed(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "confirmed",
            "확인",
            "확정",
        }

    ready_image_rows = sum(
        1
        for item in items
        if confirmed(item.get("manual_confirmed"))
        and str(item.get("field") or "").strip() == "image_url"
        and str(item.get("manual_value") or "").strip()
        and (str(item.get("candidate_source_url") or "").strip() or str(item.get("evidence_url") or "").strip())
    )
    summary = {
        "template_items": len(items),
        "manual_confirmed_rows": sum(1 for item in items if confirmed(item.get("manual_confirmed"))),
        "ready_image_rows": ready_image_rows,
        "source_url_update_required_rows": sum(1 for item in items if item.get("source_url_update_required") is True),
        "representative_image_review_required_rows": sum(
            1 for item in items if item.get("representative_image_review_required") is True
        ),
        "image_url_ready_rows": sum(1 for item in items if item.get("image_url_ready") is True),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "blocked_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "auto_apply_enabled": False,
        "write": False,
    }
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "scope": "catalog_image_attachment_template_import_dry_run",
        "summary": summary,
        "write": False,
        "queue": str(IMAGE_ATTACHMENT_CONFIRMED_TEMPLATE.relative_to(ROOT)).replace("\\", "/"),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "blocked_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
        "automation_policy": {
            "import_tool": "tools/import_confirmed_image_attachment_rows.py",
            "auto_apply_enabled": False,
            "write_enabled": False,
            "required_before_write": [
                "manual_confirmed=true",
                "field=image_url",
                "manual_value is a direct product image URL",
                "candidate_source_url or evidence_url points to the exact product page",
                "source/image pair passes generic-image and product-source safety checks",
            ],
        },
    }


def build_source_discovery_import_dry_run_public(
    queue: dict[str, Any],
    seed_rows: list[dict[str, Any]],
    *,
    queue_path: Path,
) -> dict[str, Any]:
    result = import_confirmed_source_discovery_rows.import_rows(queue, seed_rows)
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])
    return {
        "write": False,
        "queue": str(queue_path.relative_to(ROOT)).replace("\\", "/"),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
    }


def build_metadata_field_import_dry_run_public(
    queue: dict[str, Any],
    seed_rows: list[dict[str, Any]],
    generated_at: str,
    *,
    queue_path: Path,
) -> dict[str, Any]:
    normalized_queue = import_confirmed_catalog_field_rows._normalize_review_queue(queue)
    result = import_confirmed_catalog_field_rows.import_rows(normalized_queue, seed_rows)
    items = [item for item in normalized_queue.get("items", []) if isinstance(item, dict)]
    skip_reasons = Counter(str(item.get("reason") or "unspecified") for item in result["skipped"])
    confirmed = sum(1 for item in items if import_confirmed_catalog_field_rows._confirmed(item.get("manual_confirmed")))
    ready_rows = sum(
        1
        for item in items
        if import_confirmed_catalog_field_rows._confirmed(item.get("manual_confirmed"))
        and str(item.get("manual_value") or "").strip()
        and str(item.get("field") or "").strip() in import_confirmed_catalog_field_rows.ALLOWED_FIELDS
    )
    summary = {
        "template_items": len(items),
        "manual_confirmed_rows": confirmed,
        "ready_field_rows": ready_rows,
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "blocked_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "auto_apply_enabled": False,
        "write": False,
    }
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "source_discovery_next_focus_metadata_field_import_dry_run",
        "summary": summary,
        "write": False,
        "queue": str(queue_path.relative_to(ROOT)).replace("\\", "/"),
        "updated_rows": len(result["updated"]),
        "skipped_rows": len(result["skipped"]),
        "skip_reason_counts": skip_reasons.most_common(),
        "updated": result["updated"],
        "skipped_sample": result["skipped"][:100],
        "automation_policy": {
            "import_tool": "tools/import_confirmed_catalog_field_rows.py",
            "auto_apply_enabled": False,
            "write_enabled": False,
            "required_before_write": [
                "manual_confirmed=true",
                "field in sub_series/name_ja/character_name",
                "manual_value is filled from exact official product evidence",
                "evidence_url or candidate_source_url points to the exact product detail page",
            ],
        },
    }


def build_source_discovery_completion_roadmap_public(
    *,
    generated_at: str,
    missing_image_actionability: dict[str, Any],
    source_discovery_action_queue: dict[str, Any],
    source_discovery_store_bottlenecks: dict[str, Any],
    source_discovery_focus_packs: dict[str, Any],
    source_discovery_next_focus_pack: dict[str, Any],
    source_discovery_next_focus_fallback_queue: dict[str, Any],
    manual_source_url_search_queue: dict[str, Any],
    provider_missing_source_url_queue: dict[str, Any],
    candidate_source_url_review_queue: dict[str, Any],
    image_attachment_action_queue: dict[str, Any],
) -> dict[str, Any]:
    action_summary = source_discovery_action_queue.get("summary", {})
    bottleneck_summary = source_discovery_store_bottlenecks.get("summary", {})
    focus_summary = source_discovery_focus_packs.get("summary", {})
    next_focus_summary = source_discovery_next_focus_pack.get("summary", {})
    fallback_summary = source_discovery_next_focus_fallback_queue.get("summary", {})
    manual_summary = manual_source_url_search_queue.get("summary", {})
    provider_summary = provider_missing_source_url_queue.get("summary", {})
    candidate_summary = candidate_source_url_review_queue.get("summary", {})
    image_action_summary = image_attachment_action_queue.get("summary", {})
    missing_summary = missing_image_actionability.get("summary", {})

    stores = [
        row
        for row in source_discovery_store_bottlenecks.get("stores", [])
        if isinstance(row, dict)
    ]
    focus_packs = [
        row
        for row in source_discovery_focus_packs.get("focus_packs", [])
        if isinstance(row, dict)
    ]
    workstreams_by_store = {
        str(row.get("source_store") or ""): row
        for row in source_discovery_action_queue.get("source_store_workstreams", [])
        if isinstance(row, dict)
    }

    top_store_steps = []
    for rank, store in enumerate(stores[:10], start=1):
        rows = int(store.get("rows") or 0)
        pack_count = sum(
            1
            for pack in focus_packs
            if str(pack.get("source_store") or "") == str(store.get("source_store") or "")
        )
        workstream = workstreams_by_store.get(str(store.get("source_store") or ""), {})
        top_store_steps.append(
            {
                "rank": rank,
                "source_store": store.get("source_store"),
                "rows": rows,
                "estimated_image_rows_unblocked_after_source_confirmation": rows,
                "pack_count": pack_count,
                "top_category": store.get("top_category"),
                "top_allowed_source_domain": store.get("top_allowed_source_domain"),
                "first_batch_id": store.get("first_batch_id"),
                "first_primary_review_url": workstream.get("first_primary_review_url")
                or store.get("first_official_search_url"),
                "first_primary_review_url_kind": workstream.get("first_primary_review_url_kind")
                or (
                    "official_search_url"
                    if store.get("first_official_search_url")
                    else ""
                ),
                "official_search_url_count": workstream.get("official_search_url_count", 0),
                "fallback_web_search_url_count": workstream.get(
                    "fallback_web_search_url_count",
                    0,
                ),
                "next_step": store.get("next_step")
                or "open_official_search_and_confirm_exact_product_source_url",
                "auto_apply_enabled": False,
            }
        )

    current_pack = {
        "focus_pack_id": next_focus_summary.get("focus_pack_id"),
        "source_store": next_focus_summary.get("source_store"),
        "target_category": next_focus_summary.get("target_category"),
        "pack_items": next_focus_summary.get("pack_items", 0),
        "remaining_review_rows": next_focus_summary.get("remaining_review_rows", 0),
        "blocked_rows": next_focus_summary.get("blocked_rows", 0),
        "fallback_queue_rows": fallback_summary.get("queue_rows", 0),
        "first_official_search_url": next_focus_summary.get("first_official_search_url"),
        "first_primary_review_url": fallback_summary.get("first_primary_review_url")
        or next_focus_summary.get("first_official_search_url"),
        "first_primary_review_url_kind": fallback_summary.get("first_primary_review_url_kind")
        or (
            "official_search_url"
            if next_focus_summary.get("first_official_search_url")
            else ""
        ),
        "first_fallback_store_search_url": fallback_summary.get("first_fallback_store_search_url"),
        "recommended_action": "confirm current focus pack source URLs before image attachment",
    }
    completion_readiness_status = (
        "current_focus_fallback_review_required"
        if int(fallback_summary.get("queue_rows") or 0)
        else "current_focus_pack_confirmation_required"
        if int(next_focus_summary.get("remaining_review_rows") or 0)
        else "focus_pack_rotation_required"
        if int(focus_summary.get("remaining_focus_review_rows") or 0)
        else "source_discovery_complete"
    )
    completion_readiness = {
        "status": completion_readiness_status,
        "auto_apply_ready_rows": 0,
        "auto_apply_enabled": False,
        "manual_confirmed_rows": int(fallback_summary.get("manual_confirmed_rows") or 0),
        "queued_source_rows": int(action_summary.get("queued_source_rows") or 0),
        "focus_source_rows": int(focus_summary.get("focus_source_rows") or 0),
        "remaining_focus_review_rows": int(focus_summary.get("remaining_focus_review_rows") or 0),
        "current_focus_pack_id": next_focus_summary.get("focus_pack_id"),
        "current_focus_pack_rows": int(next_focus_summary.get("pack_items") or 0),
        "current_focus_remaining_rows": int(next_focus_summary.get("remaining_review_rows") or 0),
        "current_focus_fallback_rows": int(fallback_summary.get("queue_rows") or 0),
        "next_pack_after_current": next_focus_summary.get("next_pack_after_current"),
        "next_safe_phase": (
            "review_fallback_queue_and_fill_exact_manual_confirmed_source_urls"
            if int(fallback_summary.get("queue_rows") or 0)
            else "confirm_current_focus_pack_source_urls"
            if int(next_focus_summary.get("remaining_review_rows") or 0)
            else "rotate_to_next_focus_pack"
            if int(focus_summary.get("remaining_focus_review_rows") or 0)
            else "archive_source_discovery_completion"
        ),
        "next_queue": {
            "source": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.name}",
            "queue_rows": int(fallback_summary.get("queue_rows") or 0),
            "fallback_reason": fallback_summary.get("fallback_reason"),
            "first_primary_review_url": fallback_summary.get("first_primary_review_url"),
            "first_primary_review_url_kind": fallback_summary.get(
                "first_primary_review_url_kind"
            ),
            "first_domain_limited_web_search_url": fallback_summary.get(
                "first_domain_limited_web_search_url"
            ),
            "first_fallback_store_search_url": fallback_summary.get(
                "first_fallback_store_search_url"
            ),
        }
        if int(fallback_summary.get("queue_rows") or 0)
        else {
            "source": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK.name}",
            "queue_rows": int(next_focus_summary.get("remaining_review_rows") or 0),
            "focus_pack_id": next_focus_summary.get("focus_pack_id"),
            "first_official_search_url": next_focus_summary.get("first_official_search_url"),
            "first_primary_review_url": next_focus_summary.get("first_official_search_url"),
            "first_primary_review_url_kind": (
                "official_search_url"
                if next_focus_summary.get("first_official_search_url")
                else ""
            ),
        },
        "blocked_until": "exact_product_detail_source_url_confirmed",
        "blocked_reasons": [
            "fallback_search_required"
            if int(fallback_summary.get("queue_rows") or 0)
            else "exact_product_source_url_not_confirmed"
        ],
        "safety_note": (
            "Source discovery queues are review-only. Confirm exact official product detail URLs before image attachment."
        ),
    }

    phases = [
        {
            "phase": 1,
            "name": "current_focus_pack_source_confirmation",
            "rows": int(next_focus_summary.get("pack_items") or 0),
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK.name}",
            "blocked_until": "exact_product_detail_source_url_confirmed",
            "next_machine_step": "import_confirmed_source_discovery_rows_after_manual_review",
        },
        {
            "phase": 2,
            "name": "top_store_source_confirmation",
            "rows": int(focus_summary.get("remaining_focus_review_rows") or 0),
            "public_report": f"data/{SOURCE_DISCOVERY_FOCUS_PACKS.name}",
            "blocked_until": "exact_product_detail_source_url_confirmed",
            "next_machine_step": "rotate_focus_packs_until_top_5_stores_are_confirmed",
        },
        {
            "phase": 3,
            "name": "non_focus_source_confirmation",
            "rows": int(action_summary.get("queued_source_rows") or 0)
            - int(focus_summary.get("focus_source_rows") or 0),
            "public_report": f"data/{SOURCE_DISCOVERY_ACTION_QUEUE.name}",
            "blocked_until": "exact_product_detail_source_url_confirmed",
            "next_machine_step": "build_next_focus_pack_from_remaining_store_bottlenecks",
        },
        {
            "phase": 4,
            "name": "generic_or_missing_provider_source_replacement",
            "rows": int(manual_summary.get("manual_search_required_rows") or 0)
            + int(provider_summary.get("provider_missing_rows") or 0)
            + int(candidate_summary.get("candidate_review_rows") or 0),
            "public_report": f"data/{IMAGE_SOURCE_URL_CONFIRMED_TEMPLATE.name}",
            "blocked_until": "generic_source_url_replaced_with_exact_product_source",
            "next_machine_step": "import_confirmed_image_attachment_source_url_updates",
        },
        {
            "phase": 5,
            "name": "image_attachment_after_source_confirmation",
            "rows": int(image_action_summary.get("actionable_image_rows") or 0),
            "public_report": f"data/{IMAGE_ATTACHMENT_ACTION_QUEUE.name}",
            "blocked_until": "exact_source_page_product_image_confirmed",
            "next_machine_step": "import_confirmed_image_attachment_rows_after_manual_review",
        },
    ]

    source_rows = int(action_summary.get("queued_source_rows") or 0)
    focus_rows = int(focus_summary.get("focus_source_rows") or 0)
    top_10_rows = int(bottleneck_summary.get("top_10_store_rows") or 0)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "source_discovery_completion_roadmap",
        "summary": {
            "missing_image_rows": int(missing_summary.get("missing_image_rows") or 0),
            "source_first_rows": int(missing_summary.get("source_first_rows") or 0),
            "queued_source_rows": source_rows,
            "focus_source_rows": focus_rows,
            "focus_coverage": round(focus_rows / source_rows, 4) if source_rows else 0,
            "top_10_store_rows": top_10_rows,
            "top_10_store_coverage": round(top_10_rows / source_rows, 4) if source_rows else 0,
            "current_focus_pack_rows": int(next_focus_summary.get("pack_items") or 0),
            "current_focus_fallback_rows": int(fallback_summary.get("queue_rows") or 0),
            "completion_readiness_status": completion_readiness["status"],
            "auto_apply_ready_rows": 0,
            "generic_source_replacement_rows": int(
                image_action_summary.get("source_url_update_required_rows") or 0
            ),
            "manual_source_search_rows": int(manual_summary.get("manual_search_required_rows") or 0),
            "provider_missing_rows": int(provider_summary.get("provider_missing_rows") or 0),
            "candidate_source_review_rows": int(candidate_summary.get("candidate_review_rows") or 0),
            "direct_image_action_rows": int(image_action_summary.get("actionable_image_rows") or 0),
            "roadmap_phase_count": len(phases),
            "auto_apply_enabled": False,
        },
        "completion_readiness": completion_readiness,
        "current_focus_pack": current_pack,
        "top_store_steps": top_store_steps,
        "phases": phases,
        "automation_policy": {
            "auto_apply_enabled": False,
            "auto_import_source_url": False,
            "auto_import_image_url": False,
            "requires_manual_review": True,
            "reason": "Roadmap only: exact product source URLs and image identity must be manually confirmed before imports.",
        },
    }


def discovery_query(item: dict[str, Any]) -> str:
    for field in ("name_ja", "name_ko", "name_en"):
        value = str(item.get(field) or "").strip()
        if value:
            return value
    return ""


def discovery_workflow(item: dict[str, Any]) -> str:
    store = str(item.get("source_store") or "")
    if store in LICENSED_RETAILER_STORES:
        return "licensed_retailer_search_review"
    if store in OFFICIAL_SEARCH_TEMPLATES:
        return "official_search_url_available"
    return "manual_official_research"


def source_discovery_policy(workflow: str) -> dict[str, Any]:
    policies = {
        "official_search_url_available": {
            "confidence": "official_search",
            "evidence_required": "exact official product detail URL on the expected official domain",
            "auto_apply_enabled": False,
            "acceptance_rule": "product title, product image, and character/variant must match the catalog row",
        },
        "licensed_retailer_search_review": {
            "confidence": "licensed_retailer_review",
            "evidence_required": "trusted licensed retailer product detail URL when official source is unavailable",
            "auto_apply_enabled": False,
            "acceptance_rule": "retailer page must show matching product identity and should not be a broad search/listing page",
        },
        "manual_official_research": {
            "confidence": "manual_research",
            "evidence_required": "manual official or rights-holder source confirmation",
            "auto_apply_enabled": False,
            "acceptance_rule": "manual result must be recorded with exact URL and visible product evidence",
        },
    }
    return policies.get(
        workflow,
        {
            "confidence": "unknown",
            "evidence_required": "trusted exact product evidence",
            "auto_apply_enabled": False,
            "acceptance_rule": "manual review required",
        },
    )


def allowed_source_domains(source_store: str) -> list[str]:
    template = OFFICIAL_SEARCH_TEMPLATES.get(source_store)
    domains: set[str] = set()
    if template:
        netloc = urllib.parse.urlparse(template).netloc.lower()
        if netloc and "google." not in netloc:
            domains.add(netloc)
        decoded = urllib.parse.unquote(template)
        for match in re.finditer(r"site:([A-Za-z0-9_.-]+)", decoded):
            domains.add(match.group(1).lower())
    if source_store in LICENSED_RETAILER_STORES:
        domains.add("amiami.jp")
        domains.add("amiami.com")
    return sorted(domains)


def _normalized_url_domain(value: Any) -> str:
    url = str(value or "").strip().replace("&amp;", "&")
    if url.startswith("//"):
        url = f"https:{url}"
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme and not parsed.netloc:
        return ""
    return parsed.netloc.lower()


def _domain_matches_any(domain: str, allowed_domains: list[str]) -> bool:
    if not domain:
        return False
    normalized = domain.lower()
    for allowed in allowed_domains:
        candidate = str(allowed or "").lower().strip()
        if not candidate:
            continue
        if normalized == candidate or normalized.endswith(f".{candidate}"):
            return True
    return False


def discovery_search_url(item: dict[str, Any], query: str) -> str | None:
    template = OFFICIAL_SEARCH_TEMPLATES.get(str(item.get("source_store") or ""))
    if not template or not query:
        return None
    return template.format(query=urllib.parse.quote(query))


def build_source_discovery_public(items: list[dict[str, Any]], sample_rows: int = 120) -> dict[str, Any]:
    queue: list[dict[str, Any]] = []
    for row_number, item in enumerate(items):
        if present(item.get("source_url")):
            continue
        query = discovery_query(item)
        workflow = discovery_workflow(item)
        source_store = str(item.get("source_store") or "")
        policy = source_discovery_policy(workflow)
        web_query = " ".join(part for part in (query, source_store, "official", "公式 商品画像") if part)
        queue.append(
            {
                "priority": DISCOVERY_PRIORITY[workflow],
                "workflow": workflow,
                "confidence": policy["confidence"],
                "row_index": item.get("catalog_index", row_number),
                "source_store": item.get("source_store"),
                "affiliation": item.get("affiliation"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "official_search_url": discovery_search_url(item, query),
                "web_search_url": "https://www.google.com/search?q=" + urllib.parse.quote(web_query),
                "allowed_source_domains": allowed_source_domains(source_store),
                "evidence_required": policy["evidence_required"],
                "auto_apply_enabled": policy["auto_apply_enabled"],
                "acceptance_rule": policy["acceptance_rule"],
                "recommended_next_action": "find_exact_product_detail_url_then_import_image",
            }
        )

    queue.sort(
        key=lambda row: (
            row["priority"],
            str(row.get("source_store") or ""),
            str(row.get("affiliation") or ""),
            str(row.get("category") or ""),
            str(row.get("name_ja") or row.get("name_ko") or ""),
        )
    )
    by_workflow = Counter(str(item.get("workflow") or "") for item in queue)
    by_store = Counter(str(item.get("source_store") or "") for item in queue)
    by_confidence = Counter(str(item.get("confidence") or "") for item in queue)
    domainless_rows = sum(1 for item in queue if not item.get("allowed_source_domains"))
    published_items = queue[:sample_rows]

    return {
        "schema_version": 1,
        "summary": {
            "source_discovery_rows": len(queue),
            "published_sample_rows": min(sample_rows, len(queue)),
            "stale_excluded_rows": 0,
            "by_workflow": by_workflow.most_common(),
            "by_confidence": by_confidence.most_common(),
            "domainless_review_rows": domainless_rows,
            "published_domainless_review_rows": sum(
                1 for item in published_items if not item.get("allowed_source_domains")
            ),
            "top_source_stores": by_store.most_common(30),
        },
        "workflow_policies": {workflow: source_discovery_policy(workflow) for workflow in sorted(by_workflow)},
        "instructions": [
            "Public work queue for catalog rows that need exact source URLs or image enrichment.",
            "Open official_search_url or web_search_url, verify an exact product detail page, then review source_url/image_url updates.",
            "Do not auto-apply uncertain matches; use manual review before changing the catalog database.",
        ],
        "items": published_items,
    }


def metadata_action(field: str) -> str:
    if field in {"source_url", "image_url"}:
        return "Find exact official product page and attach source_url/image_url together."
    if field in {"release_date", "official_price_jpy"}:
        return "Verify official release/sale dates or stated JPY prices before importing."
    if field == "barcode":
        return "Fill only when barcode is shown by official or trusted retailer data."
    if field == "name_ja":
        return "Verify original Japanese product titles from official listings."
    return "Manual review required."


def metadata_evidence_policy(field: str) -> dict[str, Any]:
    policies = {
        "source_url": {
            "evidence_required": "exact official or trusted licensed product detail page",
            "auto_apply_enabled": False,
            "next_step": "source_url_discovery",
            "risk": "identity_mismatch",
        },
        "image_url": {
            "evidence_required": "product image from exact source_url after identity verification",
            "auto_apply_enabled": False,
            "next_step": "source_then_image_import",
            "risk": "wrong_product_image",
        },
        "release_date": {
            "evidence_required": "official product or campaign page showing release/sale date",
            "auto_apply_enabled": False,
            "next_step": "official_metadata_extraction",
            "risk": "campaign_or_reissue_date_confusion",
        },
        "official_price_jpy": {
            "evidence_required": "official product or campaign page showing tax-inclusive or stated JPY price",
            "auto_apply_enabled": False,
            "next_step": "official_metadata_extraction",
            "risk": "retailer_price_or_prize_price_confusion",
        },
        "barcode": {
            "evidence_required": "JAN/barcode from official listing or trusted retailer product detail",
            "auto_apply_enabled": False,
            "next_step": "barcode_evidence_review",
            "risk": "shared_variant_or_box_barcode",
        },
        "name_ja": {
            "evidence_required": "original Japanese title from official or trusted listing",
            "auto_apply_enabled": False,
            "next_step": "official_title_review",
            "risk": "translated_or_inferred_title",
        },
    }
    return policies.get(
        field,
        {
            "evidence_required": "trusted source evidence",
            "auto_apply_enabled": False,
            "next_step": "manual_review",
            "risk": "unknown_field_policy",
        },
    )


def build_metadata_backlog_public(items: list[dict[str, Any]], sample_groups: int = 120) -> dict[str, Any]:
    tracked_fields = [
        "source_url",
        "image_url",
        "release_date",
        "official_price_jpy",
        "barcode",
        "name_ja",
    ]
    by_field_store: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    field_totals: Counter[str] = Counter()
    store_totals: Counter[str] = Counter()

    for item in items:
        store = str(item.get("source_store") or "unknown")
        missing_fields = [field for field in tracked_fields if not present(item.get(field))]
        for field in missing_fields:
            field_totals[field] += 1
            by_field_store[(field, store)].append(item)
        if missing_fields:
            store_totals[store] += 1

    groups: list[dict[str, Any]] = []
    for (field, store), group_items in sorted(
        by_field_store.items(),
        key=lambda pair: (-len(pair[1]), pair[0][0], pair[0][1]),
    )[:sample_groups]:
        samples = group_items[:8]
        groups.append(
            {
                "field": field,
                "source_store": store,
                "missing_rows": len(group_items),
                "priority_score": len(group_items),
                "recommended_action": metadata_action(field),
                **metadata_evidence_policy(field),
                "sample_catalog_indexes": [item.get("catalog_index") for item in samples],
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "series_name": item.get("series_name"),
                        "category": item.get("category"),
                        "source_url": item.get("source_url"),
                        "image_url": item.get("image_url"),
                    }
                    for item in samples
                ],
            }
        )

    field_review_queue = []
    for field, total in field_totals.most_common():
        policy = metadata_evidence_policy(field)
        top_stores = [
            {
                "source_store": store,
                "missing_rows": len(group_items),
            }
            for (group_field, store), group_items in by_field_store.items()
            if group_field == field
        ]
        top_stores.sort(key=lambda row: (-int(row["missing_rows"]), str(row["source_store"])))
        field_review_queue.append(
            {
                "field": field,
                "missing_rows": total,
                "priority_score": total,
                "recommended_action": metadata_action(field),
                **policy,
                "top_source_stores": top_stores[:12],
            }
        )

    return {
        "schema_version": 1,
        "summary": {
            "tracked_fields": tracked_fields,
            "field_missing_totals": dict(field_totals),
            "store_rows_with_any_missing_metadata": store_totals.most_common(40),
            "published_group_rows": len(groups),
            "field_review_queue_rows": len(field_review_queue),
        },
        "field_review_queue": field_review_queue,
        "instructions": [
            "Public backlog grouped by missing field and source store.",
            "Use this before source/image crawling so agents work on the largest safe gaps first.",
            "Do not infer dates, prices, barcodes, or names without official or trusted source evidence.",
        ],
        "groups": groups,
    }


def metadata_review_workflow(field: str) -> str:
    workflows = {
        "source_url": "source_url_discovery",
        "image_url": "source_then_image_import",
        "release_date": "official_metadata_review",
        "official_price_jpy": "official_metadata_review",
        "barcode": "barcode_evidence_review",
        "name_ja": "official_title_review",
    }
    return workflows.get(field, "manual_evidence_review")


def metadata_review_priority(field: str) -> int:
    priorities = {
        "source_url": 10,
        "image_url": 20,
        "release_date": 30,
        "official_price_jpy": 40,
        "barcode": 50,
        "name_ja": 60,
    }
    return priorities.get(field, 90)


def build_metadata_review_batches_public(
    items: list[dict[str, Any]],
    generated_at: str,
    *,
    batch_size: int = 12,
) -> dict[str, Any]:
    tracked_fields = [
        "name_ja",
        "barcode",
        "release_date",
        "image_url",
        "source_url",
        "official_price_jpy",
    ]
    by_field_store: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    field_totals: Counter[str] = Counter()
    store_totals: Counter[str] = Counter()

    for item in items:
        store = str(item.get("source_store") or "unknown")
        for field in tracked_fields:
            if present(item.get(field)):
                continue
            field_totals[field] += 1
            store_totals[store] += 1
            by_field_store[(field, store)].append(item)

    groups: list[dict[str, Any]] = []
    for (field, store), group_items in by_field_store.items():
        policy = metadata_evidence_policy(field)
        samples = group_items[:8]
        groups.append(
            {
                "field": field,
                "source_store": store,
                "missing_rows": len(group_items),
                "priority": metadata_review_priority(field),
                "workflow": metadata_review_workflow(field),
                "evidence_required": policy["evidence_required"],
                "next_machine_step": policy["next_step"],
                "risk": policy["risk"],
                "recommended_action": metadata_action(field),
                "sample_catalog_indexes": [item.get("catalog_index") for item in samples],
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "series_name": item.get("series_name"),
                        "category": item.get("category"),
                        "source_url": item.get("source_url"),
                        "image_url": item.get("image_url"),
                    }
                    for item in samples
                ],
            }
        )

    groups.sort(
        key=lambda row: (
            int(row["priority"]),
            -int(row["missing_rows"]),
            str(row["field"]),
            str(row["source_store"]),
        )
    )

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(groups), batch_size):
        chunk = groups[offset : offset + batch_size]
        field_counts = Counter(str(row.get("field") or "") for row in chunk)
        workflow_counts = Counter(str(row.get("workflow") or "") for row in chunk)
        batches.append(
            {
                "batch_id": f"metadata-review-{len(batches) + 1:03d}",
                "priority": min(int(row.get("priority") or 99) for row in chunk),
                "group_count": len(chunk),
                "missing_cell_count": sum(int(row.get("missing_rows") or 0) for row in chunk),
                "field_counts": field_counts.most_common(),
                "workflow_counts": workflow_counts.most_common(),
                "review_state": "metadata_evidence_required",
                "next_machine_step": "collect_official_metadata_evidence",
                "recommended_action": "Work field/store groups in priority order; prepare reviewed patches only from trusted evidence.",
                "groups": chunk,
                "auto_apply_enabled": False,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "summary": {
            "catalog_rows": len(items),
            "tracked_fields": tracked_fields,
            "field_store_group_count": len(groups),
            "batch_count": len(batches),
            "batch_size": batch_size,
            "missing_cell_count": sum(field_totals.values()),
            "field_missing_totals": dict(field_totals),
            "top_source_stores_with_missing_metadata": store_totals.most_common(40),
            "auto_apply_enabled": False,
        },
        "instructions": [
            "Review batches are regenerated from data/catalog_public.json so stale field/store bottlenecks do not linger.",
            "Use exact official or trusted source evidence before filling metadata patches.",
            "Do not infer Japanese titles, dates, prices, barcodes, source URLs, or images from translated names alone.",
        ],
        "batches": batches,
        "automation_policy": {
            "auto_apply_metadata": False,
            "requires_manual_review": True,
        },
    }


def image_workflow(item: dict[str, Any]) -> str:
    if str(item.get("source_store") or "") == "ご当地ちいかわ 공식(API)":
        return "review_gotouchi_official_candidates"
    if present(item.get("source_url")):
        if normalize_url_key(item.get("source_url")) in {normalize_url_key(url) for url in GENERIC_STOREFRONT_URLS}:
            return "replace_generic_source_then_extract_image"
        return "extract_from_existing_source_url"
    if str(item.get("source_store") or "") in OFFICIAL_SEARCH_TEMPLATES:
        return "find_source_then_extract_image"
    return "manual_image_research"


def image_import_template(item: dict[str, Any], workflow: str) -> dict[str, Any]:
    source_url = item.get("source_url") if present(item.get("source_url")) else ""
    search_url = discovery_search_url(item, discovery_query(item))
    exact_source_ready = workflow == "extract_from_existing_source_url"
    return {
        "manual_confirmed": False,
        "manual_note": "",
        "row_index": item.get("catalog_index"),
        "field": "image_url",
        "manual_value": "",
        "evidence_url": source_url if exact_source_ready else "",
        "candidate_source_url": source_url if exact_source_ready else "",
        "source_store": item.get("source_store"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "affiliation": item.get("affiliation"),
        "source_search_url": search_url,
        "workflow": workflow,
        "requires_exact_source_url": not exact_source_ready,
        "requires_representative_image_flag": workflow in {"manual_image_research", "review_gotouchi_official_candidates"},
        "blocked_until": "exact_product_source_url_confirmed" if not exact_source_ready else "manual_image_url_confirmed",
    }


def build_image_enrichment_batches_public(
    items: list[dict[str, Any]], sample_groups: int = 80, sample_items: int = 100
) -> dict[str, Any]:
    missing = [item for item in items if not present(item.get("image_url"))]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in missing:
        grouped[(image_workflow(item), str(item.get("source_store") or "unknown"))].append(item)

    workflow_priority = {
        "extract_from_existing_source_url": 10,
        "replace_generic_source_then_extract_image": 15,
        "review_gotouchi_official_candidates": 18,
        "find_source_then_extract_image": 20,
        "manual_image_research": 40,
    }
    groups: list[dict[str, Any]] = []
    for (workflow, store), group_items in sorted(
        grouped.items(),
        key=lambda pair: (workflow_priority.get(pair[0][0], 99), -len(pair[1]), pair[0][1]),
    )[:sample_groups]:
        samples = group_items[:sample_items]
        groups.append(
            {
                "workflow": workflow,
                "source_store": store,
                "missing_image_rows": len(group_items),
                "priority": workflow_priority.get(workflow, 99),
                "recommended_action": {
                    "extract_from_existing_source_url": "crawl verified source_url and review extracted product image",
                    "replace_generic_source_then_extract_image": "replace generic storefront URL with exact product URL before image import",
                    "review_gotouchi_official_candidates": "review gotouchi official motif candidates; do not import motif-only type mismatches",
                    "find_source_then_extract_image": "find exact official product page, then attach source_url and image_url",
                    "manual_image_research": "manual web research with source verification required",
                }.get(workflow, "manual review required"),
                "official_search_available": store in OFFICIAL_SEARCH_TEMPLATES,
                "candidate_review_report": f"data/{GOTOUCHI.name}"
                if workflow == "review_gotouchi_official_candidates" and GOTOUCHI.exists()
                else None,
                "sample_items": [
                    {
                        "catalog_index": item.get("catalog_index"),
                        "name_ko": item.get("name_ko"),
                        "name_ja": item.get("name_ja"),
                        "series_name": item.get("series_name"),
                        "category": item.get("category"),
                        "source_url": item.get("source_url"),
                        "official_search_url": discovery_search_url(item, discovery_query(item)),
                        "catalog_field_import_template": image_import_template(item, workflow),
                    }
                    for item in samples
                ],
            }
        )

    by_workflow = Counter(image_workflow(item) for item in missing)
    by_store = Counter(str(item.get("source_store") or "unknown") for item in missing)
    workflow_steps = {
        "extract_from_existing_source_url": {
            "state": "ready_for_source_image_extraction",
            "blocking_reason": None,
            "next_step": "extract_product_image_from_existing_exact_source_url",
            "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
        },
        "replace_generic_source_then_extract_image": {
            "state": "blocked_by_generic_storefront_url",
            "blocking_reason": "source_url points to a generic storefront, not an exact product detail page",
            "next_step": "replace_with_exact_product_source_url_before_image_import",
            "public_report": f"data/{GENERIC_SOURCE.name}",
        },
        "review_gotouchi_official_candidates": {
            "state": "blocked_by_candidate_type_review",
            "blocking_reason": "official motif candidates may not match row product type",
            "next_step": "review_gotouchi_official_candidate_report",
            "public_report": f"data/{GOTOUCHI.name}",
        },
        "find_source_then_extract_image": {
            "state": "blocked_by_missing_source_url",
            "blocking_reason": "image import requires an exact source_url first",
            "next_step": "find_exact_official_source_url_then_extract_image",
            "public_report": f"data/{SOURCE_DISCOVERY.name}",
        },
        "manual_image_research": {
            "state": "manual_research_required",
            "blocking_reason": "no trusted automated source discovery path is configured for this store",
            "next_step": "manual_official_image_research_with_evidence",
            "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
        },
    }
    blocker_summary = [
        {
            "workflow": workflow,
            "rows": by_workflow.get(workflow, 0),
            **workflow_steps[workflow],
        }
        for workflow in (
            "extract_from_existing_source_url",
            "replace_generic_source_then_extract_image",
            "review_gotouchi_official_candidates",
            "find_source_then_extract_image",
            "manual_image_research",
        )
        if by_workflow.get(workflow, 0)
    ]
    review_batches: list[dict[str, Any]] = []
    groups_by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        groups_by_workflow[str(group.get("workflow") or "manual_image_research")].append(group)
    ordered_workflows = sorted(
        groups_by_workflow,
        key=lambda workflow: (
            workflow_priority.get(workflow, 99),
            -sum(int(group.get("missing_image_rows") or 0) for group in groups_by_workflow[workflow]),
            workflow,
        ),
    )
    for workflow in ordered_workflows:
        workflow_groups = groups_by_workflow[workflow]
        for offset in range(0, len(workflow_groups), 8):
            batch_groups = workflow_groups[offset : offset + 8]
            step = workflow_steps.get(workflow, workflow_steps["manual_image_research"])
            store_rows = Counter(
                str(group.get("source_store") or "unknown")
                for group in batch_groups
                for _ in range(int(group.get("missing_image_rows") or 0))
            )
            review_batches.append(
                {
                    "batch_id": f"image-enrichment-review-{len(review_batches) + 1:03d}",
                    "priority": min(int(group.get("priority") or 99) for group in batch_groups),
                    "workflow": workflow,
                    "workflow_counts": [(workflow, len(batch_groups))],
                    "top_source_stores": store_rows.most_common(8),
                    "group_count": len(batch_groups),
                    "missing_image_rows": sum(int(group.get("missing_image_rows") or 0) for group in batch_groups),
                    "blocked_until": step.get("state"),
                    "next_machine_step": step.get("next_step"),
                    "public_report": step.get("public_report"),
                    "catalog_field_import_template_fields": [
                        "manual_confirmed",
                        "row_index",
                        "field",
                        "manual_value",
                        "evidence_url",
                        "candidate_source_url",
                    ],
                    "acceptance_criteria": [
                        "exact product source_url is available before importing image_url",
                        "image_url comes from the accepted source page or trusted official CDN",
                        "marketplace, blog, resale, and generic listing images stay out of public catalog imports",
                        "generic storefront URLs are replaced before image extraction",
                    ],
                    "auto_apply_enabled": False,
                    "groups": batch_groups,
                }
            )
    return {
        "schema_version": 1,
        "summary": {
            "missing_image_rows": len(missing),
            "source_url_ready_rows": by_workflow.get("extract_from_existing_source_url", 0),
            "generic_source_url_rows": by_workflow.get("replace_generic_source_then_extract_image", 0),
            "gotouchi_official_review_rows": by_workflow.get("review_gotouchi_official_candidates", 0),
            "needs_source_discovery_rows": by_workflow.get("find_source_then_extract_image", 0),
            "manual_image_research_rows": by_workflow.get("manual_image_research", 0),
            "published_group_rows": len(groups),
            "review_batch_count": len(review_batches),
            "sample_image_import_template_count": sum(
                len(group.get("sample_items") or []) for group in groups
            ),
            "top_source_stores": by_store.most_common(30),
            "by_workflow": by_workflow.most_common(),
        },
        "workflow_steps": workflow_steps,
        "blocker_summary": blocker_summary,
        "review_batches": review_batches,
        "instructions": [
            "Public image enrichment batches grouped by readiness and source store.",
            "Rows with source_url should be attempted first because identity evidence already exists.",
            "Generic storefront source_url rows must be replaced with exact product URLs before image import.",
            "Gotouchi rows use the separate official motif candidate report before any image import.",
            "Rows without source_url must attach an exact source URL before image_url is imported.",
        ],
        "groups": groups,
    }


def build_requested_focus_enrichment_public(
    items: list[dict[str, Any]],
    requested_report: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    topics = [
        {
            "topic_id": "requested_special_goods",
            "label": "\uc0ac\uc6a9\uc790 \uc694\uccad \ud2b9\ubcc4 \ub9ac\uc2a4\ud2b8",
            "terms": [],
            "priority": 10,
            "reason": "Keep the user's explicit requested list visible even when every item is already present.",
        },
        {
            "topic_id": "danganronpa",
            "label": "\ub2e8\uac04\ub860\ud30c \uad7f\uc988",
            "terms": ["\ub2e8\uac04\ub860\ud30c", "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1", "Danganronpa"],
            "priority": 20,
            "reason": "Requested repeatedly, including nui and Bukubu-style goods; image/source gaps remain.",
        },
        {
            "topic_id": "ichiban_kuji",
            "label": "\uc774\uce58\ubc29\ucfe0\uc9c0 \uad7f\uc988",
            "terms": ["\uc774\uce58\ubc29\ucfe0\uc9c0", "\u4e00\u756a\u304f\u3058", "1kuji"],
            "priority": 30,
            "reason": "Large historical campaign set; prize images are strong, campaign dates and prices still need review.",
        },
        {
            "topic_id": "maho_saba",
            "label": "\ub9c8\ubc95\uc18c\ub140\uc758 \ub9c8\ub140\uc7ac\ud310 \uad7f\uc988",
            "terms": [
                "\ub9c8\ubc95\uc18c\ub140\uc758 \ub9c8\ub140\uc7ac\ud310",
                "\ub9c8\ub140\uc7ac\ud310",
                "\u9b54\u6cd5\u5c11\u5973\u30ce\u9b54\u5973\u88c1\u5224",
                "\u9b54\u5973\u88c1\u5224",
            ],
            "priority": 40,
            "reason": "Recently requested game goods; keep Animate-imported rows grouped for spot checks.",
        },
        {
            "topic_id": "bokubu_style",
            "label": "\ubd80\ucfe0\ubd80 / \ud31d\ud300\uc560\ud53d \uadf8\ub9bc\uccb4 \uad7f\uc988",
            "terms": [
                "\ubd80\ucfe0\ubd80",
                "\u5927\u5ddd\u3076\u304f\u3076",
                "\ud31d\ud300\uc560\ud53d",
                "\u30dd\u30d7\u30c6\u30d4\u30d4\u30c3\u30af",
                "Pop Team Epic",
            ],
            "priority": 50,
            "reason": "User asked for Pop Team Epic/Bukubu-style goods across Danganronpa, Gintama, Frieren, and others.",
        },
    ]

    requested_items = [
        item for item in requested_report.get("items", []) if isinstance(item, dict)
    ] if isinstance(requested_report, dict) else []

    def matches_terms(item: dict[str, Any], terms: list[str]) -> bool:
        haystack = json.dumps(item, ensure_ascii=False).lower()
        return any(term.lower() in haystack for term in terms)

    def item_issue_count(item: dict[str, Any]) -> int:
        fields = ("image_url", "source_url", "release_date", "official_price_jpy", "barcode", "name_ja")
        return sum(1 for field in fields if not present(item.get(field)))

    topic_rows: list[dict[str, Any]] = []
    all_matched_indexes: set[int] = set()
    for topic in topics:
        terms = list(topic["terms"])
        if topic["topic_id"] == "requested_special_goods":
            matched_requested = requested_items
            matched_catalog: list[dict[str, Any]] = []
            for request in requested_items:
                source_url = str(request.get("matched_source_url") or "")
                name_ko = str(request.get("matched_name_ko") or "")
                for item in items:
                    if source_url and source_url == str(item.get("source_url") or ""):
                        matched_catalog.append(item)
                        break
                    if name_ko and name_ko == str(item.get("name_ko") or ""):
                        matched_catalog.append(item)
                        break
        else:
            matched_catalog = [item for item in items if matches_terms(item, terms)]
            matched_requested = [request for request in requested_items if matches_terms(request, terms)]

        deduped_catalog: list[dict[str, Any]] = []
        seen_indexes: set[int] = set()
        for item in matched_catalog:
            index = int(item.get("catalog_index") or -1)
            if index in seen_indexes:
                continue
            seen_indexes.add(index)
            all_matched_indexes.add(index)
            deduped_catalog.append(item)

        missing_groups = {
            "missing_image_rows": [item for item in deduped_catalog if not present(item.get("image_url"))],
            "missing_source_url_rows": [item for item in deduped_catalog if not present(item.get("source_url"))],
            "missing_release_date_rows": [item for item in deduped_catalog if not present(item.get("release_date"))],
            "missing_official_price_jpy_rows": [
                item for item in deduped_catalog if not present(item.get("official_price_jpy"))
            ],
            "missing_barcode_rows": [item for item in deduped_catalog if not present(item.get("barcode"))],
            "missing_name_ja_rows": [item for item in deduped_catalog if not present(item.get("name_ja"))],
        }
        open_indexes = {
            int(item.get("catalog_index") or -1)
            for group in missing_groups.values()
            for item in group
        }
        requested_needs_review = sum(
            1
            for request in matched_requested
            if request.get("status") != "already_present"
            or not request.get("has_candidate_image")
            or request.get("review_note")
        )

        if missing_groups["missing_image_rows"] or missing_groups["missing_source_url_rows"]:
            next_step = "attach_exact_source_and_image_evidence"
        elif missing_groups["missing_release_date_rows"] or missing_groups["missing_official_price_jpy_rows"]:
            next_step = "verify_official_metadata"
        elif missing_groups["missing_barcode_rows"] or missing_groups["missing_name_ja_rows"]:
            next_step = "fill_identity_metadata"
        elif requested_needs_review:
            next_step = "review_requested_special_item_evidence"
        else:
            next_step = "monitor_coverage"

        ranked_samples = sorted(
            deduped_catalog,
            key=lambda item: (-item_issue_count(item), int(item.get("catalog_index") or 0)),
        )
        row = {
            "topic_id": topic["topic_id"],
            "label": topic["label"],
            "priority": topic["priority"],
            "catalog_rows": len(deduped_catalog),
            "requested_labels": len(matched_requested),
            "requested_needs_review": requested_needs_review,
            "open_rows": len(open_indexes) + requested_needs_review,
            "next_step": next_step,
            "public_source": f"data/{REQUESTED.name}" if matched_requested else f"data/{PUBLIC_CATALOG.name}",
            "auto_apply_enabled": False,
            "review_reason": topic["reason"],
            "sample_items": [compact_sample(item) for item in ranked_samples[:8]],
            "requested_samples": [
                {
                    "request_label": request.get("request_label"),
                    "status": request.get("status"),
                    "existing_count": request.get("existing_count"),
                    "has_candidate_image": request.get("has_candidate_image"),
                    "review_note": request.get("review_note"),
                }
                for request in matched_requested[:8]
            ],
        }
        row.update({key: len(value) for key, value in missing_groups.items()})
        topic_rows.append(row)

    topic_rows.sort(key=lambda row: (int(row.get("priority") or 999), -int(row.get("open_rows") or 0), row["topic_id"]))
    summary = {
        "topic_count": len(topic_rows),
        "total_matched_catalog_rows": len(all_matched_indexes),
        "total_requested_labels": len(requested_items),
        "topics_with_open_work": sum(1 for row in topic_rows if int(row.get("open_rows") or 0) > 0),
        "open_rows": sum(int(row.get("open_rows") or 0) for row in topic_rows),
        "missing_image_rows": sum(int(row.get("missing_image_rows") or 0) for row in topic_rows),
        "missing_source_url_rows": sum(int(row.get("missing_source_url_rows") or 0) for row in topic_rows),
        "missing_release_date_rows": sum(int(row.get("missing_release_date_rows") or 0) for row in topic_rows),
        "missing_official_price_jpy_rows": sum(
            int(row.get("missing_official_price_jpy_rows") or 0) for row in topic_rows
        ),
        "requested_needs_review": sum(int(row.get("requested_needs_review") or 0) for row in topic_rows),
        "auto_apply_enabled": False,
    }
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "requested_focus_enrichment_priority",
        "summary": summary,
        "topics": topic_rows,
        "instructions": [
            "Use this as the user-requested focus queue before broad catalog enrichment.",
            "Rows are public catalog references only; do not import private collection data.",
            "Any catalog patch must be prepared from exact source evidence and reviewed manually.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def slugify_public_id(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if text:
        return text[:48]
    encoded = str(value or "unknown").encode("utf-8", errors="ignore")
    return f"store_{sum(encoded) % 10000:04d}"


def build_danganronpa_missing_media_public(items: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    terms = ["\ub2e8\uac04\ub860\ud30c", "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1", "Danganronpa"]
    store_policies = {
        "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8": {
            "source_kind": "official_manufacturer",
            "allowed_source_domains": ["www.goodsmile.info", "www.goodsmile.com"],
            "search_template": "https://www.goodsmile.info/ja/products/search?utf8=%E2%9C%93&search%5Bquery%5D={query}",
            "confidence": "official_search",
        },
        "\ucf54\ud1a0\ubd80\ud0a4\uc57c": {
            "source_kind": "official_manufacturer",
            "allowed_source_domains": ["shop.kotobukiya.co.jp", "www.kotobukiya.co.jp"],
            "search_template": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword={query}",
            "confidence": "official_search",
        },
        "Taito": {
            "source_kind": "official_prize",
            "allowed_source_domains": ["www.taito.co.jp"],
            "search_template": "https://www.taito.co.jp/prize?keyword={query}",
            "confidence": "official_search",
        },
        "FuRyu": {
            "source_kind": "official_prize",
            "allowed_source_domains": ["furyuprize.com"],
            "search_template": "https://furyuprize.com/search?keyword={query}",
            "confidence": "official_search",
        },
        "\uc5d4\uc2a4\uce74\uc774": {
            "source_kind": "official_manufacturer",
            "allowed_source_domains": ["www.enskyshop.com", "www.ensky.co.jp"],
            "search_template": "https://www.enskyshop.com/products/list?name={query}",
            "confidence": "official_search",
        },
        "Movic": {
            "source_kind": "official_manufacturer",
            "allowed_source_domains": ["www.movic.jp"],
            "search_template": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword={query}",
            "confidence": "official_search",
        },
        "\uc560\ub2c8\uba54\uc774\ud2b8": {
            "source_kind": "licensed_retailer",
            "allowed_source_domains": ["www.animate-onlineshop.jp"],
            "search_template": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt={query}",
            "confidence": "licensed_retailer_review",
        },
        "AmiAmi": {
            "source_kind": "licensed_retailer",
            "allowed_source_domains": ["www.amiami.jp", "www.amiami.com"],
            "search_template": "https://www.amiami.jp/top/search/list?s_keywords={query}",
            "confidence": "licensed_retailer_review",
        },
    }

    def is_danganronpa(item: dict[str, Any]) -> bool:
        haystack = json.dumps(item, ensure_ascii=False).lower()
        return any(term.lower() in haystack for term in terms)

    def query_for(item: dict[str, Any]) -> str:
        title = str(item.get("name_ja") or item.get("name_ko") or "")
        if "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1" not in title:
            title = f"\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1 {title}".strip()
        return title

    rows = [
        item
        for item in items
        if is_danganronpa(item) and (not present(item.get("image_url")) or not present(item.get("source_url")))
    ]
    queue: list[dict[str, Any]] = []
    for item in sorted(rows, key=lambda row: int(row.get("catalog_index") or 0)):
        store = str(item.get("source_store") or "unknown")
        policy = store_policies.get(store, {})
        query = query_for(item)
        search_template = policy.get("search_template")
        official_search_url = (
            str(search_template).format(query=urllib.parse.quote(query)) if search_template else discovery_search_url(item, query)
        )
        missing_fields = [
            field
            for field in ("source_url", "image_url", "release_date", "barcode")
            if not present(item.get(field))
        ]
        queue.append(
            {
                "priority": 10 if policy.get("source_kind") == "official_manufacturer" else 20,
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "category": item.get("category"),
                "character_name": item.get("character_name"),
                "sub_series": item.get("sub_series"),
                "source_store": store,
                "source_kind": policy.get("source_kind", "manual_review"),
                "confidence": policy.get("confidence", "manual_research"),
                "missing_fields": missing_fields,
                "official_search_url": official_search_url,
                "web_search_url": "https://www.google.com/search?q="
                + urllib.parse.quote(f"{query} {store} \u753b\u50cf \u5546\u54c1"),
                "allowed_source_domains": policy.get("allowed_source_domains", []),
                "evidence_required": [
                    "exact product title or product-line title matches the catalog row",
                    "source page shows an official or licensed product image",
                    "source_url must be a product/detail/search-result page specific enough to re-find the item",
                    "image_url must come from the same accepted source page or an official product CDN",
                ],
                "acceptance_rule": "manual_review_required_before_catalog_patch",
                "auto_apply_enabled": False,
                "recommended_next_action": "verify exact source page, then prepare source_url and image_url patch",
            }
        )

    by_store = Counter(str(row.get("source_store") or "unknown") for row in queue)
    by_source_kind = Counter(str(row.get("source_kind") or "unknown") for row in queue)
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in queue:
        grouped[(int(row.get("priority") or 99), str(row.get("source_store") or "unknown"))].append(row)
    review_batches: list[dict[str, Any]] = []
    for batch_rank, ((priority, store), rows_for_store) in enumerate(sorted(grouped.items()), start=1):
        rows_for_store = sorted(rows_for_store, key=lambda row: int(row.get("catalog_index") or 0))
        source_kind = str(rows_for_store[0].get("source_kind") or "manual_review") if rows_for_store else "manual_review"
        review_batches.append(
            {
                "batch_id": f"danganronpa_media_{batch_rank:02d}_{slugify_public_id(store)}",
                "batch_rank": batch_rank,
                "priority": priority,
                "source_store": store,
                "source_kind": source_kind,
                "rows": len(rows_for_store),
                "catalog_indexes": [row.get("catalog_index") for row in rows_for_store],
                "allowed_source_domains": rows_for_store[0].get("allowed_source_domains", []) if rows_for_store else [],
                "first_official_search_url": rows_for_store[0].get("official_search_url") if rows_for_store else None,
                "recommended_next_action": (
                    "Open the official search URLs in this batch, confirm exact product identity, "
                    "then prepare reviewed source_url/image_url patches."
                ),
                "acceptance_rule": "manual_review_required_before_catalog_patch",
                "auto_apply_enabled": False,
            }
        )
    confirmed_patch_template = [
        {
            "catalog_index": row.get("catalog_index"),
            "name_ko": row.get("name_ko"),
            "name_ja": row.get("name_ja"),
            "source_store": row.get("source_store"),
            "source_kind": row.get("source_kind"),
            "official_search_url": row.get("official_search_url"),
            "web_search_url": row.get("web_search_url"),
            "allowed_source_domains": row.get("allowed_source_domains", []),
            "manual_confirmed_source_url": "",
            "manual_confirmed_image_url": "",
            "manual_confirmed_release_date": "",
            "manual_confirmed_barcode": "",
            "manual_evidence_note": "",
            "dry_run_status": "skipped_pending_manual_confirmation",
            "required_evidence": row.get("evidence_required", []),
            "auto_apply_enabled": False,
        }
        for row in queue
    ]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "danganronpa_missing_source_and_image_queue",
        "summary": {
            "missing_media_rows": len(queue),
            "review_batch_count": len(review_batches),
            "missing_source_url_rows": sum(1 for row in queue if "source_url" in row.get("missing_fields", [])),
            "missing_image_url_rows": sum(1 for row in queue if "image_url" in row.get("missing_fields", [])),
            "official_search_rows": sum(1 for row in queue if row.get("source_kind") == "official_manufacturer"),
            "official_prize_search_rows": sum(1 for row in queue if row.get("source_kind") == "official_prize"),
            "licensed_retailer_review_rows": sum(1 for row in queue if row.get("source_kind") == "licensed_retailer"),
            "confirmed_patch_template_rows": len(confirmed_patch_template),
            "confirmed_patch_template_pending_rows": len(
                [
                    row
                    for row in confirmed_patch_template
                    if not present(row.get("manual_confirmed_source_url"))
                    or not present(row.get("manual_confirmed_image_url"))
                ]
            ),
            "by_source_store": by_store.most_common(),
            "by_source_kind": by_source_kind.most_common(),
            "auto_apply_enabled": False,
        },
        "items": queue,
        "review_batches": review_batches,
        "confirmed_patch_template": confirmed_patch_template,
        "instructions": [
            "Work these Danganronpa rows before broad image enrichment because every row lacks both source_url and image_url.",
            "Process review_batches in batch_rank order so official manufacturer batches are cleared before retailer-only rows.",
            "Use official manufacturer or prize pages first; licensed retailers require extra identity review.",
            "Fill confirmed_patch_template only after source_url and image_url evidence both match the same product.",
            "Do not attach images from marketplaces, blogs, or resale listings unless separately promoted into a trusted-source policy.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def build_danganronpa_patch_template_dry_run_public(
    danganronpa_missing_media: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    template_rows = [
        row
        for row in danganronpa_missing_media.get("confirmed_patch_template", [])
        if isinstance(row, dict)
    ]
    items: list[dict[str, Any]] = []

    for row in template_rows:
        source_url = str(row.get("manual_confirmed_source_url") or "").strip()
        image_url = str(row.get("manual_confirmed_image_url") or "").strip()
        release_date = str(row.get("manual_confirmed_release_date") or "").strip()
        barcode = str(row.get("manual_confirmed_barcode") or "").strip()
        allowed_domains = [
            str(domain).strip().lower()
            for domain in row.get("allowed_source_domains", [])
            if str(domain).strip()
        ]
        blocking_reasons: list[str] = []

        if not source_url:
            blocking_reasons.append("missing_manual_confirmed_source_url")
        if not image_url:
            blocking_reasons.append("missing_manual_confirmed_image_url")

        source_domain = _normalized_url_domain(source_url)
        image_domain = _normalized_url_domain(image_url)
        if source_url and not _domain_matches_any(source_domain, allowed_domains):
            blocking_reasons.append("blocked_invalid_source_domain")
        if image_url and not _domain_matches_any(image_domain, allowed_domains):
            blocking_reasons.append("blocked_invalid_image_domain")

        if not source_url or not image_url:
            status = "skipped_pending_manual_confirmation"
        elif blocking_reasons:
            status = "blocked_invalid_domain"
        else:
            status = "ready_for_reviewed_patch"

        would_update_fields = []
        if source_url:
            would_update_fields.append("source_url")
        if image_url:
            would_update_fields.append("image_url")
        if release_date:
            would_update_fields.append("release_date")
        if barcode:
            would_update_fields.append("barcode")

        items.append(
            {
                "catalog_index": row.get("catalog_index"),
                "name_ko": row.get("name_ko"),
                "name_ja": row.get("name_ja"),
                "source_store": row.get("source_store"),
                "source_kind": row.get("source_kind"),
                "manual_confirmed_source_url": source_url,
                "manual_confirmed_image_url": image_url,
                "manual_confirmed_release_date": release_date,
                "manual_confirmed_barcode": barcode,
                "source_domain": source_domain,
                "image_domain": image_domain,
                "allowed_source_domains": allowed_domains,
                "status": status,
                "blocking_reasons": blocking_reasons,
                "would_update_fields": would_update_fields,
                "auto_apply_enabled": False,
            }
        )

    by_status = Counter(str(row.get("status") or "unknown") for row in items)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "danganronpa_confirmed_patch_template_dry_run",
        "summary": {
            "template_rows": len(items),
            "ready_rows": by_status.get("ready_for_reviewed_patch", 0),
            "skipped_rows": by_status.get("skipped_pending_manual_confirmation", 0),
            "blocked_rows": sum(count for status, count in by_status.items() if status.startswith("blocked_")),
            "manual_confirmed_source_rows": sum(1 for row in items if present(row.get("manual_confirmed_source_url"))),
            "manual_confirmed_image_rows": sum(1 for row in items if present(row.get("manual_confirmed_image_url"))),
            "by_status": by_status.most_common(),
            "auto_apply_enabled": False,
        },
        "items": items,
        "instructions": [
            "Fill source_url and image_url only after exact product identity is confirmed from official or trusted evidence.",
            "Rows marked ready_for_reviewed_patch are still not auto-applied; review them before a catalog patch.",
            "Blocked rows must be corrected to an allowed source/image domain or receive an explicit trusted-source policy.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "private_collection_storage": "local_device_only",
        },
    }


def build_operations_public(
    generated_at: str,
    items: list[dict[str, Any]],
    rows: int,
    missing: dict[str, int],
    cov: dict[str, float],
    source_discovery: dict[str, Any],
    metadata_backlog: dict[str, Any],
    image_enrichment_batches: dict[str, Any],
    deduplication: dict[str, Any],
    animation_categories: dict[str, Any],
    ichiban_kuji_history: dict[str, Any],
    generic_source_patch_candidates: dict[str, Any],
    requested_focus: dict[str, Any],
    danganronpa_missing_media: dict[str, Any],
    danganronpa_patch_template_dry_run: dict[str, Any],
    image_asset_audit: dict[str, Any],
    metadata_review_batches_override: dict[str, Any] | None = None,
    metadata_action_queue_override: dict[str, Any] | None = None,
    ichiban_prize_name_image_review_override: dict[str, Any] | None = None,
    ichiban_prize_name_image_patch_candidates_override: dict[str, Any] | None = None,
    source_next_focus_pack_override: dict[str, Any] | None = None,
    source_next_focus_detail_candidates_override: dict[str, Any] | None = None,
    source_next_focus_metadata_field_import_override: dict[str, Any] | None = None,
    source_next_focus_fallback_queue_override: dict[str, Any] | None = None,
    source_discovery_action_queue_override: dict[str, Any] | None = None,
    source_discovery_focus_template_override: dict[str, Any] | None = None,
    source_discovery_focus_template_import_override: dict[str, Any] | None = None,
    deduplication_template_import_dry_run_override: dict[str, Any] | None = None,
    animation_review_batches_override: dict[str, Any] | None = None,
    animation_action_queue_override: dict[str, Any] | None = None,
    animation_split_review_override: dict[str, Any] | None = None,
    animation_unmatched_keyword_review_override: dict[str, Any] | None = None,
    ichiban_reissue_decision_template_override: dict[str, Any] | None = None,
    source_discovery_starter_queue_override: dict[str, Any] | None = None,
    image_attachment_action_queue_override: dict[str, Any] | None = None,
    ensky_cache_candidate_action_queue_override: dict[str, Any] | None = None,
    requested_focus_action_queue_override: dict[str, Any] | None = None,
    requested_focus_next_work_override: dict[str, Any] | None = None,
    deduplication_action_queue_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_summary = source_discovery["summary"]
    source_review_batches = (
        load_json(SOURCE_DISCOVERY_REVIEW_BATCHES, {}) if SOURCE_DISCOVERY_REVIEW_BATCHES.exists() else {}
    )
    source_review_batches_summary = source_review_batches.get("summary", {})
    source_action_queue = (
        source_discovery_action_queue_override
        if source_discovery_action_queue_override is not None
        else load_json(SOURCE_DISCOVERY_ACTION_QUEUE, {}) if SOURCE_DISCOVERY_ACTION_QUEUE.exists() else {}
    )
    source_detail_candidate_action_queue = (
        load_json(SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE, {})
        if SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.exists()
        else {}
    )
    source_detail_candidate_action_queue_summary = source_detail_candidate_action_queue.get("summary", {})
    official_detail_review_batches = (
        load_json(OFFICIAL_DETAIL_REVIEW_BATCHES, {})
        if OFFICIAL_DETAIL_REVIEW_BATCHES.exists()
        else {}
    )
    official_detail_review_batches_summary = official_detail_review_batches.get("summary", {})
    source_action_queue_summary = source_action_queue.get("summary", {})
    source_focus_template = (
        source_discovery_focus_template_override
        if source_discovery_focus_template_override is not None
        else load_json(SOURCE_DISCOVERY_FOCUS_TEMPLATE, {}) if SOURCE_DISCOVERY_FOCUS_TEMPLATE.exists() else {}
    )
    source_focus_template_summary = source_focus_template.get("summary", {})
    source_focus_template_import = (
        source_discovery_focus_template_import_override
        if source_discovery_focus_template_import_override is not None
        else load_json(SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT, {})
        if SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT.exists()
        else {}
    )
    source_next_focus_fetch_audit = (
        load_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.exists()
        else {}
    )
    source_next_focus_fetch_audit_summary = source_next_focus_fetch_audit.get("summary", {})
    source_next_focus_pack = (
        source_next_focus_pack_override
        if source_next_focus_pack_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_PACK.exists()
        else {}
    )
    source_next_focus_pack_summary = source_next_focus_pack.get("summary", {})
    source_next_focus_detail_candidates = (
        source_next_focus_detail_candidates_override
        if source_next_focus_detail_candidates_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.exists()
        else {}
    )
    source_next_focus_detail_candidates_summary = source_next_focus_detail_candidates.get("summary", {})
    source_next_focus_metadata_field_import = (
        source_next_focus_metadata_field_import_override
        if source_next_focus_metadata_field_import_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT.exists()
        else {}
    )
    source_next_focus_metadata_field_import_summary = source_next_focus_metadata_field_import.get("summary", {})
    source_next_focus_fallback_queue = (
        source_next_focus_fallback_queue_override
        if source_next_focus_fallback_queue_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.exists()
        else {}
    )
    source_next_focus_fallback_queue_summary = source_next_focus_fallback_queue.get("summary", {})
    source_discovery_starter_queue = (
        source_discovery_starter_queue_override
        if source_discovery_starter_queue_override is not None
        else load_json(SOURCE_DISCOVERY_STARTER_QUEUE, {})
        if SOURCE_DISCOVERY_STARTER_QUEUE.exists()
        else {}
    )
    source_discovery_starter_queue_summary = source_discovery_starter_queue.get("summary", {})

    def starter_group_key(group: dict[str, Any]) -> str:
        parts = [
            str(group.get("source_store") or "").strip(),
            str(group.get("affiliation") or "").strip(),
            str(group.get("category") or "").strip(),
        ]
        return " | ".join(part for part in parts if part) or "unknown_group"

    def compact_source_workstream(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_store": row.get("source_store"),
            "priority": row.get("priority"),
            "queued_source_rows": row.get("queued_source_rows"),
            "batch_count": row.get("batch_count", 0),
            "next_batch_id": row.get("next_batch_id"),
            "batch_ids": row.get("batch_ids", []),
            "allowed_source_domains": row.get("allowed_source_domains", []),
            "official_search_url_count": row.get("official_search_url_count", 0),
            "workflow_rows": row.get("workflow_rows", []),
            "review_state_rows": row.get("review_state_rows", []),
            "category_rows": row.get("category_rows", []),
            "recommended_next_step": row.get("recommended_next_step"),
            "auto_apply_enabled": row.get("auto_apply_enabled", False),
        }

    source_action_workstreams = [
        compact_source_workstream(row)
        for row in source_action_queue.get("source_store_workstreams", [])
        if isinstance(row, dict)
    ][:8]
    def compact_image_workstream(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "workflow": row.get("workflow"),
            "source_store": row.get("source_store"),
            "priority": row.get("priority"),
            "queued_image_rows": row.get("queued_image_rows", 0),
            "batch_count": row.get("batch_count", 0),
            "next_batch_id": row.get("next_batch_id"),
            "batch_ids": row.get("batch_ids", []),
            "next_machine_step": row.get("next_machine_step"),
            "source_url_update_template_rows": row.get("source_url_update_template_rows", 0),
            "representative_image_review_rows": row.get("representative_image_review_rows", 0),
            "image_url_ready_rows": row.get("image_url_ready_rows", 0),
            "category_rows": row.get("category_rows", []),
            "auto_apply_enabled": row.get("auto_apply_enabled", False),
        }

    image_summary = image_enrichment_batches["summary"]
    image_asset_summary = image_asset_audit.get("summary", {})
    image_missing_evidence_priority = (
        image_asset_audit.get("missing_image_evidence_priority")
        or (image_asset_audit.get("download_readiness") or {}).get("missing_image_evidence_priority")
        or {}
    )
    image_action_queue = (
        image_attachment_action_queue_override
        if image_attachment_action_queue_override is not None
        else load_json(IMAGE_ATTACHMENT_ACTION_QUEUE, {})
        if IMAGE_ATTACHMENT_ACTION_QUEUE.exists()
        else {}
    )
    image_action_queue_summary = image_action_queue.get("summary", {})
    image_action_workstreams = [
        compact_image_workstream(row)
        for row in image_action_queue.get("workstreams", [])
        if isinstance(row, dict)
    ][:8]
    ensky_cache_candidate_action_queue = (
        ensky_cache_candidate_action_queue_override
        if ensky_cache_candidate_action_queue_override is not None
        else load_json(ENSKY_CACHE_CANDIDATE_ACTION_QUEUE, {})
        if ENSKY_CACHE_CANDIDATE_ACTION_QUEUE.exists()
        else {}
    )
    ensky_cache_candidate_action_queue_summary = ensky_cache_candidate_action_queue.get("summary", {})
    dedupe_summary = deduplication["summary"]
    dedupe_review_batches = (
        load_json(DEDUPLICATION_REVIEW_BATCHES, {}) if DEDUPLICATION_REVIEW_BATCHES.exists() else {}
    )
    dedupe_review_batches_summary = dedupe_review_batches.get("summary", {})
    dedupe_action_queue = (
        deduplication_action_queue_override
        if deduplication_action_queue_override is not None
        else load_json(DEDUPLICATION_ACTION_QUEUE, {})
        if DEDUPLICATION_ACTION_QUEUE.exists()
        else {}
    )
    dedupe_action_queue_summary = dedupe_action_queue.get("summary", {})
    ichiban_reissue_decision_template = (
        ichiban_reissue_decision_template_override
        if ichiban_reissue_decision_template_override is not None
        else load_json(ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE, {})
        if ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE.exists()
        else {"summary": {}}
    )
    ichiban_reissue_decision_template_summary = ichiban_reissue_decision_template.get("summary", {})
    dedupe_template_import_dry_run = (
        deduplication_template_import_dry_run_override
        if deduplication_template_import_dry_run_override is not None
        else load_json(DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN, {})
        if DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN.exists()
        else {}
    )
    dedupe_template_import_dry_run_summary = dedupe_template_import_dry_run.get("summary", {})
    animation_summary = animation_categories["summary"]
    animation_review_batches = (
        animation_review_batches_override
        if animation_review_batches_override is not None
        else load_json(ANIMATION_CATEGORY_REVIEW_BATCHES, {}) if ANIMATION_CATEGORY_REVIEW_BATCHES.exists() else {}
    )
    animation_review_batches_summary = animation_review_batches.get("summary", {})
    animation_action_queue = (
        animation_action_queue_override
        if animation_action_queue_override is not None
        else load_json(ANIMATION_CATEGORY_ACTION_QUEUE, {}) if ANIMATION_CATEGORY_ACTION_QUEUE.exists() else {}
    )
    animation_action_queue_summary = animation_action_queue.get("summary", {})
    animation_action_queue_work_order = [
        row for row in animation_action_queue.get("work_order", []) if isinstance(row, dict)
    ]
    animation_split_review = (
        animation_split_review_override
        if animation_split_review_override is not None
        else load_json(ANIMATION_CATEGORY_SPLIT_REVIEW, {}) if ANIMATION_CATEGORY_SPLIT_REVIEW.exists() else {}
    )
    animation_split_review_summary = animation_split_review.get("summary", {})
    animation_unmatched_keyword_review = (
        animation_unmatched_keyword_review_override
        if animation_unmatched_keyword_review_override is not None
        else load_json(ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW, {})
        if ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.exists()
        else {}
    )
    animation_unmatched_keyword_review_summary = animation_unmatched_keyword_review.get("summary", {})
    kuji_summary = ichiban_kuji_history["summary"]
    ichiban_kuji_metadata_probe = (
        load_json(ICHIIBAN_KUJI_METADATA_PROBE, {}) if ICHIIBAN_KUJI_METADATA_PROBE.exists() else {}
    )
    ichiban_kuji_metadata_probe_summary = ichiban_kuji_metadata_probe.get("summary", {})
    ichiban_kuji_metadata_review_batches = (
        load_json(ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES, {})
        if ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES.exists()
        else {}
    )
    ichiban_kuji_metadata_review_batches_summary = ichiban_kuji_metadata_review_batches.get("summary", {})
    ichiban_kuji_metadata_action_queue = (
        load_json(ICHIIBAN_KUJI_METADATA_ACTION_QUEUE, {})
        if ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.exists()
        else {}
    )
    ichiban_kuji_metadata_action_queue_summary = ichiban_kuji_metadata_action_queue.get("summary", {})
    ichiban_kuji_prize_policy_audit = (
        load_json(ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT, {}) if ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.exists() else {}
    )
    ichiban_kuji_prize_policy_audit_summary = ichiban_kuji_prize_policy_audit.get("summary", {})
    ichiban_kuji_prize_name_image_review = (
        ichiban_prize_name_image_review_override
        if ichiban_prize_name_image_review_override is not None
        else load_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW, {})
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.exists()
        else {}
    )
    ichiban_kuji_prize_name_image_review_summary = ichiban_kuji_prize_name_image_review.get("summary", {})
    ichiban_kuji_prize_name_image_patch_candidates = (
        ichiban_prize_name_image_patch_candidates_override
        if ichiban_prize_name_image_patch_candidates_override is not None
        else load_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES, {})
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.exists()
        else {}
    )
    ichiban_kuji_prize_name_image_patch_candidates_summary = (
        normalize_ichiban_prize_patch_candidate_summary(ichiban_kuji_prize_name_image_patch_candidates)
    )
    metadata_summary = metadata_backlog["summary"]
    metadata_review_batches = (
        metadata_review_batches_override
        if metadata_review_batches_override is not None
        else load_json(METADATA_REVIEW_BATCHES, {}) if METADATA_REVIEW_BATCHES.exists() else {}
    )
    metadata_review_batches_summary = metadata_review_batches.get("summary", {})
    metadata_action_queue = (
        metadata_action_queue_override
        if metadata_action_queue_override is not None
        else load_json(METADATA_ACTION_QUEUE, {}) if METADATA_ACTION_QUEUE.exists() else {}
    )
    metadata_action_queue_summary = metadata_action_queue.get("summary", {})
    confirmed_import_readiness = (
        load_json(CONFIRMED_IMPORT_READINESS, {}) if CONFIRMED_IMPORT_READINESS.exists() else {}
    )
    confirmed_import_readiness_summary = confirmed_import_readiness.get("summary", {})
    execution_plan = load_json(EXECUTION_PLAN, {}) if EXECUTION_PLAN.exists() else {}
    execution_plan_summary = execution_plan.get("summary", {})
    generic_patch_summary = generic_source_patch_candidates["summary"]
    requested_focus_summary = requested_focus["summary"]
    requested_focus_review_batches = (
        load_json(REQUESTED_FOCUS_REVIEW_BATCHES, {}) if REQUESTED_FOCUS_REVIEW_BATCHES.exists() else {}
    )
    requested_focus_review_batches_summary = requested_focus_review_batches.get("summary", {})
    requested_focus_action_queue = (
        requested_focus_action_queue_override
        if requested_focus_action_queue_override is not None
        else load_json(REQUESTED_FOCUS_ACTION_QUEUE, {}) if REQUESTED_FOCUS_ACTION_QUEUE.exists() else {}
    )
    requested_focus_action_queue_summary = requested_focus_action_queue.get("summary", {})
    requested_focus_next_work = (
        requested_focus_next_work_override
        if requested_focus_next_work_override is not None
        else load_json(REQUESTED_FOCUS_NEXT_WORK, {}) if REQUESTED_FOCUS_NEXT_WORK.exists() else {}
    )
    requested_focus_next_work_summary = requested_focus_next_work.get("summary", {})
    danganronpa_media_summary = danganronpa_missing_media["summary"]
    danganronpa_dry_run_summary = danganronpa_patch_template_dry_run["summary"]
    danganronpa_goodsmile_probe = (
        load_json(DANGANRONPA_GOODSMILE_PROBE, {}) if DANGANRONPA_GOODSMILE_PROBE.exists() else {}
    )
    danganronpa_goodsmile_probe_summary = danganronpa_goodsmile_probe.get("summary", {})
    danganronpa_prize_probe = (
        load_json(DANGANRONPA_PRIZE_PROBE, {}) if DANGANRONPA_PRIZE_PROBE.exists() else {}
    )
    danganronpa_prize_probe_summary = danganronpa_prize_probe.get("summary", {})
    danganronpa_source_detail_probe = (
        load_json(DANGANRONPA_SOURCE_DETAIL_PROBE, {}) if DANGANRONPA_SOURCE_DETAIL_PROBE.exists() else {}
    )
    danganronpa_source_detail_probe_summary = danganronpa_source_detail_probe.get("summary", {})

    priority_fields = ["source_url", "image_url", "release_date", "official_price_jpy", "barcode"]
    store_totals: dict[str, dict[str, Any]] = defaultdict(lambda: {"rows": 0, **{field: 0 for field in priority_fields}})
    for item in items:
        store = str(item.get("source_store") or "unknown")
        store_totals[store]["rows"] += 1
        for field in priority_fields:
            if not present(item.get(field)):
                store_totals[store][field] += 1

    def store_first_action(row: dict[str, Any]) -> str:
        if row["missing_source_url"] or row["missing_image_url"]:
            return "source_and_image_enrichment"
        if row["missing_release_date"]:
            return "release_date_enrichment"
        if row["missing_price_jpy"]:
            return "price_enrichment"
        if row["missing_barcode"]:
            return "barcode_review"
        return "monitor"

    store_priority_matrix = []
    for store, totals in store_totals.items():
        score = (
            totals["source_url"] * 5
            + totals["image_url"] * 4
            + totals["release_date"] * 2
            + totals["official_price_jpy"]
            + min(totals["barcode"], 200) * 0.5
        )
        if score <= 0:
            continue
        row = {
            "source_store": store,
            "priority_score": round(score, 1),
            "rows": totals["rows"],
            "missing_source_url": totals["source_url"],
            "missing_image_url": totals["image_url"],
            "missing_release_date": totals["release_date"],
            "missing_price_jpy": totals["official_price_jpy"],
            "missing_barcode": totals["barcode"],
        }
        row["recommended_first_action"] = store_first_action(row)
        store_priority_matrix.append(row)
    store_priority_matrix.sort(key=lambda row: (-row["priority_score"], str(row["source_store"])))

    quality_gates = [
        {
            "key": "source_url_coverage",
            "status": "pass" if cov.get("source_url", 0) >= 0.95 else "warn",
            "value": cov.get("source_url", 0),
            "target": 0.95,
        },
        {
            "key": "image_url_coverage",
            "status": "pass" if cov.get("image_url", 0) >= 0.95 else "warn",
            "value": cov.get("image_url", 0),
            "target": 0.95,
        },
        {
            "key": "local_image_asset_coverage",
            "status": "pass"
            if image_asset_summary.get("local_asset_coverage", 0) >= 1
            and image_asset_summary.get("web_public_asset_coverage", 0) >= 1
            else "warn",
            "value": image_asset_summary.get("local_asset_coverage", 0),
            "target": 1,
            "image_url_rows": image_asset_summary.get("image_url_rows", 0),
            "local_image_path_rows": image_asset_summary.get("local_image_path_rows", 0),
            "image_url_without_local_path_rows": image_asset_summary.get("image_url_without_local_path_rows", 0),
            "missing_local_image_files": image_asset_summary.get("missing_local_image_files", 0),
            "missing_web_public_asset_files": image_asset_summary.get("missing_web_public_asset_files", 0),
            "web_public_asset_coverage": image_asset_summary.get("web_public_asset_coverage", 0),
        },
        {
            "key": "release_date_coverage",
            "status": "pass" if cov.get("release_date", 0) >= 0.9 else "warn",
            "value": cov.get("release_date", 0),
            "target": 0.9,
        },
        {
            "key": "source_discovery_backlog",
            "status": "warn" if source_summary.get("source_discovery_rows", 0) else "pass",
            "value": source_summary.get("source_discovery_rows", 0),
            "target": 0,
        },
        {
            "key": "manual_dedupe_backlog",
            "status": "warn" if dedupe_summary.get("duplicate_groups", 0) else "pass",
            "value": dedupe_summary.get("duplicate_groups", 0),
            "target": 0,
        },
    ]

    next_actions = [
        {
            "priority": 5,
            "workstream": "agent_work_queue",
            "public_report": f"data/{AGENT_WORK_QUEUE.name}",
            "recommended_next_action": "Open top_next_batches and assign the first image/source batches before broad metadata work.",
        },
        {
            "priority": 6,
            "workstream": "execution_plan",
            "public_report": f"data/{EXECUTION_PLAN.name}",
            "action_count": execution_plan_summary.get("action_count", 0),
            "blocked_action_count": execution_plan_summary.get("blocked_action_count", 0),
            "manual_review_action_count": execution_plan_summary.get("manual_review_action_count", 0),
            "recommended_next_action": "Use the consolidated execution plan to choose the next safe DB cleanup step.",
        } if execution_plan_summary else None,
        {
            "priority": 10,
            "workstream": "requested_focus_enrichment",
            "public_report": f"data/{REQUESTED_FOCUS.name}",
            "open_rows": requested_focus_summary.get("open_rows", 0),
            "topics_with_open_work": requested_focus_summary.get("topics_with_open_work", 0),
            "recommended_next_action": "Prioritize user-requested focus topics before broad catalog enrichment.",
        },
        {
            "priority": 11,
            "workstream": "requested_focus_review_batches",
            "public_report": f"data/{REQUESTED_FOCUS_REVIEW_BATCHES.name}",
            "batch_count": requested_focus_review_batches_summary.get("batch_count", 0),
            "review_row_count": requested_focus_review_batches_summary.get("review_row_count", 0),
            "recommended_next_action": "Work user-requested focus batches by topic, missing field, and source store.",
        } if requested_focus_review_batches_summary else None,
        {
            "priority": 12,
            "workstream": "requested_focus_action_queue",
            "public_report": f"data/{REQUESTED_FOCUS_ACTION_QUEUE.name}",
            "actionable_template_rows": requested_focus_action_queue_summary.get("actionable_template_rows", 0),
            "queued_action_rows": requested_focus_action_queue_summary.get("queued_action_rows", 0),
            "unqueued_actionable_rows": requested_focus_action_queue_summary.get("unqueued_actionable_rows", 0),
            "queue_coverage": requested_focus_action_queue_summary.get("queue_coverage", 0),
            "barcode_template_rows_excluded": requested_focus_action_queue_summary.get(
                "barcode_template_rows_excluded", 0
            ),
            "non_barcode_template_share": requested_focus_action_queue_summary.get(
                "non_barcode_template_share", 0
            ),
            "review_url_rows": requested_focus_action_queue_summary.get("review_url_rows", 0),
            "primary_review_url_kind_counts": requested_focus_action_queue_summary.get(
                "primary_review_url_kind_counts", []
            ),
            "action_batch_count": requested_focus_action_queue_summary.get("action_batch_count", 0),
            "recommended_next_action": "Work queued non-barcode requested-focus rows, then expand remaining actionable rows before barcode research.",
        } if requested_focus_action_queue_summary else None,
        {
            "priority": 13,
            "workstream": "requested_focus_next_work",
            "public_report": f"data/{REQUESTED_FOCUS_NEXT_WORK.name}",
            "next_batch_id": requested_focus_next_work_summary.get("next_batch_id", ""),
            "next_topic_id": requested_focus_next_work_summary.get("next_topic_id", ""),
            "next_missing_field": requested_focus_next_work_summary.get("next_missing_field", ""),
            "next_source_store": requested_focus_next_work_summary.get("next_source_store", ""),
            "next_row_count": requested_focus_next_work_summary.get("next_row_count", 0),
            "preview_row_count": requested_focus_next_work_summary.get("preview_row_count", 0),
            "next_review_url": requested_focus_next_work_summary.get("next_review_url", ""),
            "recommended_next_action": "Open the next-work report first; confirm this small requested-focus batch before moving through the full queue.",
        } if requested_focus_next_work_summary else None,
        {
            "priority": 15,
            "workstream": "danganronpa_missing_media",
            "public_report": f"data/{DANGANRONPA_MISSING_MEDIA.name}",
            "open_rows": danganronpa_media_summary.get("missing_media_rows", 0),
            "official_search_rows": danganronpa_media_summary.get("official_search_rows", 0),
            "recommended_next_action": "Verify exact Danganronpa source pages and attach source_url/image_url patches.",
        },
        {
            "priority": 15,
            "workstream": "danganronpa_patch_template_dry_run",
            "public_report": f"data/{DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.name}",
            "template_rows": danganronpa_dry_run_summary.get("template_rows", 0),
            "ready_rows": danganronpa_dry_run_summary.get("ready_rows", 0),
            "skipped_rows": danganronpa_dry_run_summary.get("skipped_rows", 0),
            "blocked_rows": danganronpa_dry_run_summary.get("blocked_rows", 0),
            "recommended_next_action": "Review filled Danganronpa template rows here before any catalog patch.",
        },
        {
            "priority": 16,
            "workstream": "danganronpa_goodsmile_probe",
            "public_report": f"data/{DANGANRONPA_GOODSMILE_PROBE.name}",
            "target_rows": danganronpa_goodsmile_probe_summary.get("target_rows", 0),
            "review_rows": danganronpa_goodsmile_probe_summary.get("goodsmile_com_review_rows", 0),
            "recommended_next_action": "Review Good Smile probe misses before attempting automatic source/image attachment.",
        } if danganronpa_goodsmile_probe_summary else None,
        {
            "priority": 17,
            "workstream": "danganronpa_prize_probe",
            "public_report": f"data/{DANGANRONPA_PRIZE_PROBE.name}",
            "target_rows": danganronpa_prize_probe_summary.get("target_rows", 0),
            "no_provider_candidate_rows": danganronpa_prize_probe_summary.get("no_provider_candidate_rows", 0),
            "recommended_next_action": "Route Taito/FuRyu API misses to manual historical official-source review.",
        } if danganronpa_prize_probe_summary else None,
        {
            "priority": 18,
            "workstream": "danganronpa_source_detail_probe",
            "public_report": f"data/{DANGANRONPA_SOURCE_DETAIL_PROBE.name}",
            "target_rows": danganronpa_source_detail_probe_summary.get("target_rows", 0),
            "exact_candidate_rows": danganronpa_source_detail_probe_summary.get("exact_candidate_rows", 0),
            "fetch_failed_rows": danganronpa_source_detail_probe_summary.get("fetch_failed_rows", 0),
            "recommended_next_action": "Use the store-by-store probe misses to drive manual official Danganronpa source lookup.",
        } if danganronpa_source_detail_probe_summary else None,
        {
            "priority": 19,
            "workstream": "image_url_attachment",
            "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
            "ready_rows": image_summary.get("source_url_ready_rows", 0),
            "generic_source_url_rows": image_summary.get("generic_source_url_rows", 0),
            "gotouchi_official_review_rows": image_summary.get("gotouchi_official_review_rows", 0),
            "blocked_rows": image_summary.get("needs_source_discovery_rows", 0),
            "recommended_next_action": "Process exact source_url-ready image rows first; review gotouchi motif candidates and replace generic storefront URLs before image import.",
        },
        {
            "priority": 19,
            "workstream": "local_image_asset_audit",
            "public_report": f"data/{IMAGE_ASSET_AUDIT.name}",
            "image_url_rows": image_asset_summary.get("image_url_rows", 0),
            "local_image_path_rows": image_asset_summary.get("local_image_path_rows", 0),
            "image_url_without_local_path_rows": image_asset_summary.get("image_url_without_local_path_rows", 0),
            "missing_local_image_files": image_asset_summary.get("missing_local_image_files", 0),
            "missing_web_public_asset_files": image_asset_summary.get("missing_web_public_asset_files", 0),
            "local_asset_coverage": image_asset_summary.get("local_asset_coverage", 0),
            "web_public_asset_coverage": image_asset_summary.get("web_public_asset_coverage", 0),
            "rows_still_requiring_image_url_evidence": image_asset_summary.get(
                "rows_still_requiring_image_url_evidence", 0
            ),
            "missing_image_evidence_priority": image_missing_evidence_priority,
            "recommended_next_action": "No download is needed for rows that already have image_url; remaining image work must first find exact image_url/source evidence.",
        } if image_asset_summary else None,
        {
            "priority": 20,
            "workstream": "image_attachment_action_queue",
            "public_report": f"data/{IMAGE_ATTACHMENT_ACTION_QUEUE.name}",
            "actionable_image_rows": image_action_queue_summary.get("actionable_image_rows", 0),
            "queued_image_rows": image_action_queue_summary.get("queued_image_rows", 0),
            "unqueued_actionable_image_rows": image_action_queue_summary.get("unqueued_actionable_image_rows", 0),
            "sample_queue_coverage": image_action_queue_summary.get("sample_queue_coverage", 0),
            "action_batch_count": image_action_queue_summary.get("action_batch_count", 0),
            "source_url_update_required_rows": image_action_queue_summary.get("source_url_update_required_rows", 0),
            "source_url_update_template_rows": image_action_queue_summary.get("source_url_update_template_rows", 0),
            "source_url_update_search_hint_rows": image_action_queue_summary.get(
                "source_url_update_search_hint_rows",
                0,
            ),
            "source_url_update_missing_search_hint_rows": image_action_queue_summary.get(
                "source_url_update_missing_search_hint_rows",
                0,
            ),
            "primary_review_url_rows": image_action_queue_summary.get("primary_review_url_rows", 0),
            "primary_review_url_missing_rows": image_action_queue_summary.get(
                "primary_review_url_missing_rows", 0
            ),
            "primary_review_url_kind_counts": image_action_queue_summary.get(
                "primary_review_url_kind_counts", []
            ),
            "by_review_lane": image_action_queue_summary.get("by_review_lane", []),
            "image_import_blocker_counts": image_action_queue_summary.get(
                "image_import_blocker_counts", []
            ),
            "suggested_local_image_path_rows": image_action_queue_summary.get(
                "suggested_local_image_path_rows", 0
            ),
            "local_image_download_instruction_ready_rows": image_action_queue_summary.get(
                "local_image_download_instruction_ready_rows", 0
            ),
            "blocked_before_image_import_rows": image_action_queue_summary.get(
                "blocked_before_image_import_rows", 0
            ),
            "download_ready_after_manual_image_url_rows": image_action_queue_summary.get(
                "download_ready_after_manual_image_url_rows", 0
            ),
            "workstream_count": image_action_queue_summary.get("workstream_count", 0),
            "source_url_update_workstream_count": image_action_queue_summary.get(
                "source_url_update_workstream_count", 0
            ),
            "representative_image_review_workstream_count": image_action_queue_summary.get(
                "representative_image_review_workstream_count", 0
            ),
            "by_workflow": image_action_queue_summary.get("by_workflow", []),
            "by_source_store": image_action_queue_summary.get("by_source_store", []),
            "top_image_attachment_workstreams": image_action_workstreams,
            "next_source_url_review_batch_rows": image_action_queue_summary.get(
                "next_source_url_review_batch_rows", 0
            ),
            "next_source_url_review_batch_store_count": image_action_queue_summary.get(
                "next_source_url_review_batch_store_count", 0
            ),
            "next_source_url_review_batch_primary_review_url_rows": image_action_queue_summary.get(
                "next_source_url_review_batch_primary_review_url_rows", 0
            ),
            "next_source_url_review_batch_primary_review_url_kind_counts": image_action_queue_summary.get(
                "next_source_url_review_batch_primary_review_url_kind_counts", []
            ),
            "next_source_url_review_batch": [
                row
                for row in image_action_queue.get("next_source_url_review_batch", [])
                if isinstance(row, dict)
            ][:10],
            "next_representative_image_review_batch_rows": image_action_queue_summary.get(
                "next_representative_image_review_batch_rows", 0
            ),
            "next_representative_image_review_batch_store_count": image_action_queue_summary.get(
                "next_representative_image_review_batch_store_count", 0
            ),
            "next_representative_image_review_batch_primary_review_url_rows": image_action_queue_summary.get(
                "next_representative_image_review_batch_primary_review_url_rows", 0
            ),
            "next_representative_image_review_batch_local_path_rows": image_action_queue_summary.get(
                "next_representative_image_review_batch_local_path_rows", 0
            ),
            "next_representative_image_review_batch_primary_review_url_kind_counts": image_action_queue_summary.get(
                "next_representative_image_review_batch_primary_review_url_kind_counts", []
            ),
            "next_representative_image_review_batch_candidate_status_counts": image_action_queue_summary.get(
                "next_representative_image_review_batch_candidate_status_counts", []
            ),
            "next_representative_image_review_batch": [
                row
                for row in image_action_queue.get("next_representative_image_review_batch", [])
                if isinstance(row, dict)
            ][:10],
            "excluded_workflow_rows": image_action_queue_summary.get("excluded_workflow_rows", []),
            "attachment_readiness": image_action_queue.get(
                "attachment_readiness", {}
            ),
            "recommended_next_action": "Work source-url-blocked image rows first; local image paths are prepared but image_url import waits for exact product evidence.",
        } if image_action_queue_summary else None,
        {
            "priority": 19,
            "workstream": "confirmed_import_readiness",
            "public_report": f"data/{CONFIRMED_IMPORT_READINESS.name}",
            "ready_or_pending_import_rows": confirmed_import_readiness_summary.get("ready_or_pending_import_rows", 0),
            "blocked_confirmed_rows": confirmed_import_readiness_summary.get("blocked_confirmed_rows", 0),
            "template_items": confirmed_import_readiness_summary.get("template_items", 0),
            "public_action_queue_rows": confirmed_import_readiness_summary.get("public_action_queue_rows", 0),
            "public_action_queue_batches": confirmed_import_readiness_summary.get("public_action_queue_batches", 0),
            "recommended_next_action": "Review confirmed import readiness before attempting source/image/metadata writes.",
        } if confirmed_import_readiness_summary else None,
        {
            "priority": 12,
            "workstream": "generic_source_patch_candidates",
            "public_report": f"data/{GENERIC_SOURCE_PATCH_CANDIDATES.name}",
            "candidate_rows": generic_patch_summary.get("candidate_rows", 0),
            "manual_confirmed_rows": generic_patch_summary.get("manual_confirmed_rows", 0),
            "auto_apply_enabled": generic_patch_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Review weak generic storefront candidates before preparing any catalog patch.",
        },
        {
            "priority": 20,
            "workstream": "source_discovery_starter_queue",
            "public_report": f"data/{SOURCE_DISCOVERY_STARTER_QUEUE.name}",
            "starter_queue_rows": source_discovery_starter_queue_summary.get("starter_queue_rows", 0),
            "starter_queue_groups": source_discovery_starter_queue_summary.get("starter_queue_groups", 0),
            "next_review_batch_rows": source_discovery_starter_queue_summary.get("next_review_batch_rows", 0),
            "next_review_batch_group_count": source_discovery_starter_queue_summary.get(
                "next_review_batch_group_count", 0
            ),
            "next_review_batch_primary_source_store": source_discovery_starter_queue_summary.get(
                "next_review_batch_primary_source_store"
            ),
            "next_review_batch": [
                row
                for row in source_discovery_starter_queue.get("next_review_batch", [])
                if isinstance(row, dict)
            ][:20],
            "coverage_matches_missing_source_url_rows": source_discovery_starter_queue_summary.get(
                "coverage_matches_missing_source_url_rows",
                False,
            ),
            "top_group_keys": [
                starter_group_key(group)
                for group in source_discovery_starter_queue.get("groups", [])[:5]
                if isinstance(group, dict)
            ],
            "top_search_urls": [
                group.get("first_search_url")
                for group in source_discovery_starter_queue.get("groups", [])[:5]
                if isinstance(group, dict) and group.get("first_search_url")
            ],
            "top_fallback_web_search_urls": [
                group.get("first_fallback_web_search_url")
                for group in source_discovery_starter_queue.get("groups", [])
                if isinstance(group, dict) and group.get("first_fallback_web_search_url")
            ][:5],
            "recommended_next_action": "Open starter search URLs and confirm exact official product/detail source pages before image import.",
        } if source_discovery_starter_queue_summary else None,
        {
            "priority": 20,
            "workstream": "source_discovery",
            "public_report": f"data/{SOURCE_DISCOVERY.name}",
            "ready_rows": source_summary.get("source_discovery_rows", 0),
            "recommended_next_action": "Find exact official detail pages for rows missing source_url.",
        },
        {
            "priority": 20,
            "workstream": "source_discovery_focus_template",
            "public_report": f"data/{SOURCE_DISCOVERY_FOCUS_TEMPLATE.name}",
            "template_items": source_focus_template_summary.get("template_items", 0),
            "work_order_pack_count": source_focus_template_summary.get("work_order_pack_count", 0),
            "next_focus_pack_id": source_focus_template_summary.get("next_focus_pack_id"),
            "next_source_store": source_focus_template_summary.get("next_source_store"),
            "next_target_category": source_focus_template_summary.get("next_target_category"),
            "next_focus_pack_rows": source_focus_template_summary.get("next_focus_pack_rows", 0),
            "next_official_search_url": source_focus_template_summary.get("next_official_search_url"),
            "dry_run_updated_rows": source_focus_template_import.get("updated_rows", 0),
            "dry_run_skipped_rows": source_focus_template_import.get("skipped_rows", 0),
            "recommended_next_action": "Open the focus template work_order and confirm exact product source URLs for the next store/category pack.",
        } if source_focus_template_summary else None,
        {
            "priority": 20,
            "workstream": "source_discovery_next_focus_pack",
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK.name}",
            "focus_pack_id": source_next_focus_pack_summary.get("focus_pack_id"),
            "pack_items": source_next_focus_pack_summary.get("pack_items", 0),
            "focus_pack_progress_queue_count": source_next_focus_pack_summary.get(
                "focus_pack_progress_queue_count", 0
            ),
            "focus_pack_progress_remaining_rows": source_next_focus_pack_summary.get(
                "focus_pack_progress_remaining_rows", 0
            ),
            "current_remaining_review_rows": source_next_focus_pack_summary.get("remaining_review_rows", 0),
            "first_official_search_url": source_next_focus_pack_summary.get("first_official_search_url"),
            "recommended_next_action": "Work the current source discovery focus pack first, then move down the progress queue.",
        } if source_next_focus_pack_summary else None,
        {
            "priority": 20,
            "workstream": "source_discovery_next_focus_pack_fetch_audit",
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.name}",
            "focus_pack_id": source_next_focus_fetch_audit_summary.get("focus_pack_id"),
            "pack_items": source_next_focus_fetch_audit_summary.get("pack_items", 0),
            "official_search_ok_rows": source_next_focus_fetch_audit_summary.get("official_search_ok_rows", 0),
            "official_search_unavailable_rows": source_next_focus_fetch_audit_summary.get(
                "official_search_unavailable_rows", 0
            ),
            "fallback_web_search_required": source_next_focus_fetch_audit_summary.get(
                "fallback_web_search_required", False
            ),
            "recommended_next_action": "Use web search or store archives for the current focus pack before marking any source_url confirmed.",
        } if source_next_focus_fetch_audit_summary else None,
        {
            "priority": 20,
            "workstream": "source_discovery_next_focus_detail_candidates",
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.name}",
            "focus_pack_id": source_next_focus_detail_candidates_summary.get("focus_pack_id"),
            "pack_items": source_next_focus_detail_candidates_summary.get("pack_items", 0),
            "items_with_candidates": source_next_focus_detail_candidates_summary.get("items_with_candidates", 0),
            "candidate_rows": source_next_focus_detail_candidates_summary.get("candidate_rows", 0),
            "metadata_enrichment_template_rows": source_next_focus_detail_candidates_summary.get(
                "metadata_enrichment_template_rows",
                0,
            ),
            "metadata_field_import_template_rows": source_next_focus_detail_candidates_summary.get(
                "metadata_field_import_template_rows",
                0,
            ),
            "metadata_field_import_supported_rows": source_next_focus_detail_candidates_summary.get(
                "metadata_field_import_supported_rows",
                0,
            ),
            "metadata_field_import_dry_run_updated_rows": source_next_focus_metadata_field_import_summary.get("updated_rows", 0),
            "metadata_field_import_dry_run_skipped_rows": source_next_focus_metadata_field_import_summary.get("skipped_rows", 0),
            "metadata_field_import_dry_run_skip_reason_counts": source_next_focus_metadata_field_import_summary.get(
                "skip_reason_counts",
                [],
            ),
            "next_action_lane_count": source_next_focus_detail_candidates_summary.get("next_action_lane_count", 0),
            "next_action_lanes": source_next_focus_detail_candidates_summary.get("next_action_lanes", []),
            "completion_readiness_status": source_next_focus_detail_candidates_summary.get(
                "completion_readiness_status"
            ),
            "auto_apply_ready_rows": source_next_focus_detail_candidates_summary.get("auto_apply_ready_rows", 0),
            "auto_apply_enabled": source_next_focus_detail_candidates_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Work the current focus pack by lane: fallback search, variant metadata, then identity review.",
        } if source_next_focus_detail_candidates_summary else None,
        {
            "priority": 20,
            "workstream": "source_discovery_next_focus_fallback_queue",
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.name}",
            "focus_pack_id": source_next_focus_fallback_queue_summary.get("focus_pack_id"),
            "queue_rows": source_next_focus_fallback_queue_summary.get("queue_rows", 0),
            "manual_confirmed_rows": source_next_focus_fallback_queue_summary.get("manual_confirmed_rows", 0),
            "fallback_reason": source_next_focus_fallback_queue_summary.get("fallback_reason"),
            "by_source_store": source_next_focus_fallback_queue_summary.get("by_source_store", []),
            "by_category": source_next_focus_fallback_queue_summary.get("by_category", []),
            "work_order_steps": source_next_focus_fallback_queue_summary.get("work_order_steps", 0),
            "work_order_lanes": source_next_focus_fallback_queue_summary.get("work_order_lanes", []),
            "first_domain_limited_web_search_url": source_next_focus_fallback_queue_summary.get(
                "first_domain_limited_web_search_url"
            ),
            "first_primary_review_url": source_next_focus_fallback_queue_summary.get(
                "first_primary_review_url"
            ),
            "first_primary_review_url_kind": source_next_focus_fallback_queue_summary.get(
                "first_primary_review_url_kind"
            ),
            "auto_apply_enabled": source_next_focus_fallback_queue_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Review fallback rows and fill exact manual_confirmed_source_url values before source import.",
        } if source_next_focus_fallback_queue_summary else None,
        {
            "priority": 21,
            "workstream": "source_discovery_review_batches",
            "public_report": f"data/{SOURCE_DISCOVERY_REVIEW_BATCHES.name}",
            "batch_count": source_review_batches_summary.get("batch_count", 0),
            "source_discovery_rows": source_review_batches_summary.get("source_discovery_rows", 0),
            "recommended_next_action": "Assign full source discovery batches by store/workflow before image imports.",
        } if source_review_batches_summary else None,
        {
            "priority": 22,
            "workstream": "source_discovery_action_queue",
            "public_report": f"data/{SOURCE_DISCOVERY_ACTION_QUEUE.name}",
            "actionable_source_rows": source_action_queue_summary.get("actionable_source_rows", 0),
            "queued_source_rows": source_action_queue_summary.get("queued_source_rows", 0),
            "unqueued_actionable_source_rows": source_action_queue_summary.get("unqueued_actionable_source_rows", 0),
            "queue_coverage": source_action_queue_summary.get("queue_coverage", 0),
            "action_batch_count": source_action_queue_summary.get("action_batch_count", 0),
            "by_review_state": source_action_queue_summary.get("by_review_state", []),
            "by_workflow": source_action_queue_summary.get("by_workflow", []),
            "by_source_store": source_action_queue_summary.get("by_source_store", []),
            "top_source_store_workstreams": source_action_workstreams,
            "excluded_review_state_rows": source_action_queue_summary.get("excluded_review_state_rows", []),
            "manual_research_backlog_rows": source_action_queue_summary.get("manual_research_backlog_rows", 0),
            "manual_research_backlog_by_source_store": source_action_queue_summary.get(
                "manual_research_backlog_by_source_store", []
            ),
            "recommended_next_action": "Work queued official-search source URL batches, then expand remaining actionable source rows.",
        } if source_action_queue_summary else None,
        {
            "priority": 23,
            "workstream": "ensky_cache_candidate_action_queue",
            "public_report": f"data/{ENSKY_CACHE_CANDIDATE_ACTION_QUEUE.name}",
            "candidate_action_rows": ensky_cache_candidate_action_queue_summary.get("candidate_action_rows", 0),
            "action_batch_count": ensky_cache_candidate_action_queue_summary.get("action_batch_count", 0),
            "manual_confirmed_true": ensky_cache_candidate_action_queue_summary.get("manual_confirmed_true", 0),
            "candidate_source_url_ready_rows": ensky_cache_candidate_action_queue_summary.get(
                "candidate_source_url_ready_rows", 0
            ),
            "candidate_image_url_ready_rows": ensky_cache_candidate_action_queue_summary.get(
                "candidate_image_url_ready_rows", 0
            ),
            "safe_exact_top_candidate_rows": ensky_cache_candidate_action_queue_summary.get(
                "safe_exact_top_candidate_rows", 0
            ),
            "can_import_now_rows": ensky_cache_candidate_action_queue_summary.get("can_import_now_rows", 0),
            "blocked_manual_review_rows": ensky_cache_candidate_action_queue_summary.get(
                "blocked_manual_review_rows", 0
            ),
            "by_affiliation": ensky_cache_candidate_action_queue_summary.get("by_affiliation", []),
            "by_category": ensky_cache_candidate_action_queue_summary.get("by_category", []),
            "import_readiness": ensky_cache_candidate_action_queue.get("import_readiness", {}),
            "auto_apply_enabled": ensky_cache_candidate_action_queue_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Review broad Ensky cache candidates before filling source_url and image_url templates.",
        } if ensky_cache_candidate_action_queue_summary else None,
        {
            "priority": 24,
            "workstream": "source_detail_candidate_action_queue",
            "public_report": f"data/{SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.name}",
            "candidate_action_rows": source_detail_candidate_action_queue_summary.get("candidate_action_rows", 0),
            "action_batch_count": source_detail_candidate_action_queue_summary.get("action_batch_count", 0),
            "manual_confirmed_true": source_detail_candidate_action_queue_summary.get("manual_confirmed_true", 0),
            "safe_source_image_pair_rows": source_detail_candidate_action_queue_summary.get(
                "safe_source_image_pair_rows", 0
            ),
            "manual_confirmation_shortlist_rows": source_detail_candidate_action_queue_summary.get(
                "manual_confirmation_shortlist_rows", 0
            ),
            "candidate_count_review_required_rows": source_detail_candidate_action_queue_summary.get(
                "candidate_count_review_required_rows", 0
            ),
            "priority_manual_review_candidate_rows": source_detail_candidate_action_queue_summary.get(
                "priority_manual_review_candidate_rows", 0
            ),
            "near_or_better_candidate_rows": source_detail_candidate_action_queue_summary.get(
                "near_or_better_candidate_rows", 0
            ),
            "ambiguous_or_weaker_candidate_rows": source_detail_candidate_action_queue_summary.get(
                "ambiguous_or_weaker_candidate_rows", 0
            ),
            "by_source_store": source_detail_candidate_action_queue_summary.get("by_source_store", []),
            "by_review_risk": source_detail_candidate_action_queue_summary.get("by_review_risk", []),
            "by_candidate_count_bucket": source_detail_candidate_action_queue_summary.get(
                "by_candidate_count_bucket", []
            ),
            "auto_apply_enabled": source_detail_candidate_action_queue_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Confirm exact candidate identity before filling source_url and image_url templates.",
        } if source_detail_candidate_action_queue_summary else None,
        {
            "priority": 25,
            "workstream": "official_detail_review_batches",
            "public_report": f"data/{OFFICIAL_DETAIL_REVIEW_BATCHES.name}",
            "reviewable_seed_rows": official_detail_review_batches_summary.get("reviewable_seed_rows", 0),
            "reviewable_candidate_rows": official_detail_review_batches_summary.get("reviewable_candidate_rows", 0),
            "manual_confirmed_true": official_detail_review_batches_summary.get("manual_confirmed_true", 0),
            "by_workflow": official_detail_review_batches_summary.get("by_workflow", []),
            "by_store": official_detail_review_batches_summary.get("by_store", []),
            "auto_apply_enabled": official_detail_review_batches_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Confirm official detail candidates before importing source_url and image_url.",
        } if official_detail_review_batches_summary else None,
        {
            "priority": 30,
            "workstream": "metadata_backlog",
            "public_report": f"data/{METADATA_BACKLOG.name}",
            "tracked_fields": metadata_summary.get("tracked_fields", []),
            "field_review_queue_rows": metadata_summary.get("field_review_queue_rows", 0),
            "recommended_next_action": "Use field_review_queue before store groups to fill release dates, prices, barcodes, and names with evidence.",
        },
        {
            "priority": 31,
            "workstream": "metadata_review_batches",
            "public_report": f"data/{METADATA_REVIEW_BATCHES.name}",
            "batch_count": metadata_review_batches_summary.get("batch_count", 0),
            "field_store_group_count": metadata_review_batches_summary.get("field_store_group_count", 0),
            "missing_cell_count": metadata_review_batches_summary.get("missing_cell_count", 0),
            "recommended_next_action": "Use full field/store metadata batches for title, barcode, date, price, source, and image cleanup.",
        } if metadata_review_batches_summary else None,
        {
            "priority": 32,
            "workstream": "metadata_action_queue",
            "public_report": f"data/{METADATA_ACTION_QUEUE.name}",
            "actionable_group_count": metadata_action_queue_summary.get("actionable_group_count", 0),
            "queued_group_count": metadata_action_queue_summary.get("queued_group_count", 0),
            "unqueued_actionable_group_count": metadata_action_queue_summary.get(
                "unqueued_actionable_group_count", 0
            ),
            "actionable_missing_cells": metadata_action_queue_summary.get("actionable_missing_cells", 0),
            "queued_missing_cells": metadata_action_queue_summary.get("queued_missing_cells", 0),
            "unqueued_actionable_missing_cells": metadata_action_queue_summary.get(
                "unqueued_actionable_missing_cells", 0
            ),
            "group_queue_coverage": metadata_action_queue_summary.get("group_queue_coverage", 0),
            "missing_cell_queue_coverage": metadata_action_queue_summary.get("missing_cell_queue_coverage", 0),
            "action_batch_count": metadata_action_queue_summary.get("action_batch_count", 0),
            "primary_review_url_groups": metadata_action_queue_summary.get("primary_review_url_groups", 0),
            "first_primary_review_url": metadata_action_queue_summary.get("first_primary_review_url"),
            "first_primary_review_url_kind": metadata_action_queue_summary.get("first_primary_review_url_kind"),
            "primary_review_url_kind_counts": metadata_action_queue_summary.get(
                "primary_review_url_kind_counts", []
            ),
            "missing_cells_by_field": metadata_action_queue_summary.get("missing_cells_by_field", []),
            "missing_cells_by_source_store": metadata_action_queue_summary.get("missing_cells_by_source_store", []),
            "top_action_groups": metadata_action_queue_summary.get("top_action_groups", []),
            "recommended_next_action": "Work queued release date, price, and Japanese title groups, then expand remaining actionable metadata.",
        } if metadata_action_queue_summary else None,
        {
            "priority": 40,
            "workstream": "deduplication_review",
            "public_report": f"data/{DEDUPLICATION.name}",
            "review_groups": dedupe_summary.get("duplicate_groups", 0),
            "recommended_next_action": "Review duplicates manually; automatic deletion remains disabled.",
        },
        {
            "priority": 41,
            "workstream": "deduplication_review_batches",
            "public_report": f"data/{DEDUPLICATION_REVIEW_BATCHES.name}",
            "batch_count": dedupe_review_batches_summary.get("batch_count", 0),
            "source_groups": dedupe_review_batches_summary.get("source_groups", 0),
            "high_review_confidence_groups": dict(dedupe_review_batches_summary.get("by_review_confidence", [])).get(
                "high_review_confidence", 0
            ),
            "recommended_next_action": "Work dedupe review batches in priority order; record explicit decisions before any catalog mutation.",
        } if dedupe_review_batches_summary else None,
        {
            "priority": 42,
            "workstream": "deduplication_action_queue",
            "public_report": f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
            "actionable_groups": dedupe_action_queue_summary.get("actionable_groups", 0),
            "queued_groups": dedupe_action_queue_summary.get("queued_groups", 0),
            "unqueued_actionable_groups": dedupe_action_queue_summary.get("unqueued_actionable_groups", 0),
            "queue_coverage": dedupe_action_queue_summary.get("queue_coverage", 0),
            "action_batch_count": dedupe_action_queue_summary.get("action_batch_count", 0),
            "ichiban_reissue_review_groups": dedupe_action_queue_summary.get("ichiban_reissue_review_groups", 0),
            "ichiban_reissue_review_rows": dedupe_action_queue_summary.get("ichiban_reissue_review_rows", 0),
            "ichiban_probable_reissue_review_groups": dedupe_action_queue_summary.get(
                "ichiban_probable_reissue_review_groups", 0
            ),
            "ichiban_reissue_protected_groups": dedupe_action_queue_summary.get(
                "ichiban_reissue_protected_groups", 0
            ),
            "recommended_next_action": "Review queued high/medium-confidence duplicate groups, then expand remaining actionable groups.",
        } if dedupe_action_queue_summary else None,
        {
            "priority": 42.5,
            "workstream": "deduplication_template_import_dry_run",
            "public_report": f"data/{DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN.name}",
            "template_items": dedupe_template_import_dry_run_summary.get("template_items", 0),
            "ready_decision_rows": dedupe_template_import_dry_run_summary.get("ready_decision_rows", 0),
            "updated_rows": dedupe_template_import_dry_run_summary.get("updated_rows", 0),
            "skipped_rows": dedupe_template_import_dry_run_summary.get("skipped_rows", 0),
            "skip_reason_counts": dedupe_template_import_dry_run_summary.get("skip_reason_counts", []),
            "recommended_next_action": "Confirm same-sellable-product keep/drop rows before running any dedupe import with --write.",
        } if dedupe_template_import_dry_run_summary else None,
        {
            "priority": 43,
            "workstream": "ichiban_kuji_reissue_dedupe_review",
            "public_report": f"data/{ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE.name}",
            "work_order_report": f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
            "review_groups": dedupe_action_queue_summary.get("ichiban_reissue_review_groups", 0),
            "probable_reissue_groups": dedupe_action_queue_summary.get(
                "ichiban_probable_reissue_review_groups", 0
            ),
            "review_rows": dedupe_action_queue_summary.get("ichiban_reissue_review_rows", 0),
            "work_order_rows": dedupe_action_queue_summary.get("ichiban_reissue_work_order_rows", 0),
            "campaign_url_comparison_preview": [
                {
                    "work_order_id": row.get("work_order_id"),
                    "normalized_name": row.get("normalized_name"),
                    "campaign_url_comparison": row.get("campaign_url_comparison"),
                }
                for row in dedupe_action_queue.get("ichiban_reissue_work_order", [])[:5]
                if isinstance(row, dict)
            ],
            "next_campaign_review_batch_rows": ichiban_reissue_decision_template_summary.get(
                "campaign_review_batch_rows", 0
            ),
            "next_campaign_review_batch_item_work_order_rows": (
                ichiban_reissue_decision_template_summary.get(
                    "campaign_review_batch_item_work_order_rows", 0
                )
            ),
            "next_campaign_review_batch_catalog_index_rows": (
                ichiban_reissue_decision_template_summary.get(
                    "campaign_review_batch_catalog_index_rows", 0
                )
            ),
            "next_campaign_review_batch_visible_item_preview_rows": (
                ichiban_reissue_decision_template_summary.get(
                    "campaign_review_batch_visible_item_preview_rows", 0
                )
            ),
            "next_campaign_review_batch": [
                row
                for row in ichiban_reissue_decision_template.get(
                    "next_campaign_review_batch", []
                )
                if isinstance(row, dict)
            ][:4],
            "decision_template_rows": dedupe_action_queue_summary.get(
                "ichiban_reissue_decision_template_rows", 0
            ),
            "campaign_decision_template_rows": ichiban_reissue_decision_template_summary.get(
                "campaign_template_rows", 0
            ),
            "item_decision_template_rows": ichiban_reissue_decision_template_summary.get(
                "item_template_rows", 0
            ),
            "manual_confirmed_rows": dedupe_action_queue_summary.get(
                "ichiban_reissue_manual_confirmed_rows", 0
            ),
            "protected_groups": dedupe_action_queue_summary.get("ichiban_reissue_protected_groups", 0),
            "next_step": "fill_ichiban_reissue_decision_template_before_dedupe",
            "recommended_next_action": (
                "Fill the Ichiban reissue decision template from the work order before any dedupe import."
            ),
        } if dedupe_action_queue_summary else None,
        {
            "priority": 50,
            "workstream": "ichiban_kuji_history",
            "public_report": f"data/{ICHIIBAN_KUJI_HISTORY.name}",
            "campaign_metadata_review_queue_rows": kuji_summary.get("campaign_metadata_review_queue_rows", 0),
            "missing_release_date_campaign_groups": kuji_summary.get("missing_release_date_campaign_groups", 0),
            "missing_price_campaign_groups": kuji_summary.get("missing_official_price_jpy_campaign_groups", 0),
            "recommended_next_action": "Use campaign_metadata_review_queue to verify official pages before applying dates or prices.",
        },
        {
            "priority": 51,
            "workstream": "ichiban_kuji_metadata_probe",
            "public_report": f"data/{ICHIIBAN_KUJI_METADATA_PROBE.name}",
            "audited_urls": ichiban_kuji_metadata_probe_summary.get("audited_urls", 0),
            "safe_release_row_count": ichiban_kuji_metadata_probe_summary.get("safe_release_row_count", 0),
            "safe_price_row_count": ichiban_kuji_metadata_probe_summary.get("safe_price_row_count", 0),
            "blocked_reasons": ichiban_kuji_metadata_probe_summary.get("blocked_reasons", []),
            "recommended_next_action": "Keep Ichiban Kuji date/price gaps blocked unless a labeled official source is found.",
        } if ichiban_kuji_metadata_probe_summary else None,
        {
            "priority": 52,
            "workstream": "ichiban_kuji_metadata_review_batches",
            "public_report": f"data/{ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES.name}",
            "batch_count": ichiban_kuji_metadata_review_batches_summary.get("batch_count", 0),
            "source_campaigns": ichiban_kuji_metadata_review_batches_summary.get("source_campaigns", 0),
            "catalog_item_rows": ichiban_kuji_metadata_review_batches_summary.get("catalog_item_rows", 0),
            "recommended_next_action": "Review batched 1kuji campaign metadata evidence before applying release dates or prices.",
        } if ichiban_kuji_metadata_review_batches_summary else None,
        {
            "priority": 53,
            "workstream": "ichiban_kuji_metadata_action_queue",
            "public_report": f"data/{ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.name}",
            "actionable_campaigns": ichiban_kuji_metadata_action_queue_summary.get("actionable_campaigns", 0),
            "queued_action_campaigns": ichiban_kuji_metadata_action_queue_summary.get("queued_action_campaigns", 0),
            "unqueued_action_campaigns": ichiban_kuji_metadata_action_queue_summary.get("unqueued_action_campaigns", 0),
            "campaign_queue_coverage": ichiban_kuji_metadata_action_queue_summary.get("campaign_queue_coverage", 0),
            "queued_catalog_item_rows": ichiban_kuji_metadata_action_queue_summary.get("queued_catalog_item_rows", 0),
            "action_batch_count": ichiban_kuji_metadata_action_queue_summary.get("action_batch_count", 0),
            "field_patch_template_counts": ichiban_kuji_metadata_action_queue_summary.get(
                "field_patch_template_counts", []
            ),
            "next_campaign_patch_review_batch_rows": ichiban_kuji_metadata_action_queue_summary.get(
                "next_campaign_patch_review_batch_rows", 0
            ),
            "next_campaign_patch_review_batch_template_rows": ichiban_kuji_metadata_action_queue_summary.get(
                "next_campaign_patch_review_batch_template_rows", 0
            ),
            "next_campaign_patch_review_batch_primary_review_url_rows": (
                ichiban_kuji_metadata_action_queue_summary.get(
                    "next_campaign_patch_review_batch_primary_review_url_rows", 0
                )
            ),
            "next_campaign_patch_review_batch_field_counts": (
                ichiban_kuji_metadata_action_queue_summary.get(
                    "next_campaign_patch_review_batch_field_counts", []
                )
            ),
            "work_order_steps": ichiban_kuji_metadata_action_queue_summary.get("work_order_steps", 0),
            "work_order_lanes": ichiban_kuji_metadata_action_queue_summary.get("work_order_lanes", []),
            "recommended_next_action": "Work queued 1kuji metadata templates, then expand remaining actionable campaigns.",
        } if ichiban_kuji_metadata_action_queue_summary else None,
        {
            "priority": 54,
            "workstream": "ichiban_kuji_prize_name_image_review",
            "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}",
            "review_rows": ichiban_kuji_prize_name_image_review_summary.get("review_rows", 0),
            "name_structure_review_rows": ichiban_kuji_prize_name_image_review_summary.get(
                "name_structure_review_rows", 0
            ),
            "image_identity_review_rows": ichiban_kuji_prize_name_image_review_summary.get(
                "image_identity_review_rows", 0
            ),
            "multi_item_prize_rank_groups": ichiban_kuji_prize_name_image_review_summary.get(
                "multi_item_prize_rank_groups", 0
            ),
            "multi_item_prize_rank_catalog_rows": ichiban_kuji_prize_name_image_review_summary.get(
                "multi_item_prize_rank_catalog_rows", 0
            ),
            "auto_apply_enabled": ichiban_kuji_prize_name_image_review_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Review prize display names and image identity against official Ichiban Kuji campaign lineups.",
        } if ichiban_kuji_prize_name_image_review_summary else None,
        {
            "priority": 54,
            "workstream": "ichiban_kuji_prize_name_image_patch_candidates",
            "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.name}",
            "candidate_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get("candidate_rows", 0),
            "open_candidate_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "open_candidate_rows", 0
            ),
            "manual_confirmed_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "manual_confirmed_rows", 0
            ),
            "exact_image_match_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "exact_image_match_rows", 0
            ),
            "strong_name_match_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "strong_name_match_rows", 0
            ),
            "blocked_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get("blocked_rows", 0),
            "fetch_failure_urls": ichiban_kuji_prize_name_image_patch_candidates_summary.get("fetch_failure_urls", 0),
            "auto_apply_enabled": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "auto_apply_enabled", False
            ),
            "recommended_next_action": "Manual-confirm exact 1kuji name/image patch candidates before catalog mutation.",
        } if ichiban_kuji_prize_name_image_patch_candidates_summary else None,
        {
            "priority": 55,
            "workstream": "ichiban_kuji_prize_policy_audit",
            "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.name}",
            "last_one_rows": ichiban_kuji_prize_policy_audit_summary.get("last_one_rows", 0),
            "last_one_nonzero_price_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "last_one_nonzero_price_rows", 0
            ),
            "double_chance_rows": ichiban_kuji_prize_policy_audit_summary.get("double_chance_rows", 0),
            "double_chance_nonzero_price_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "double_chance_nonzero_price_rows", 0
            ),
            "multi_item_prize_label_groups": ichiban_kuji_prize_policy_audit_summary.get(
                "multi_item_prize_label_groups", 0
            ),
            "multi_item_prize_label_manual_review_groups": ichiban_kuji_prize_policy_audit_summary.get(
                "multi_item_prize_label_manual_review_groups", 0
            ),
            "multi_item_prize_label_review_batch_count": ichiban_kuji_prize_policy_audit_summary.get(
                "multi_item_prize_label_review_batch_count", 0
            ),
            "multi_item_prize_label_review_catalog_item_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "multi_item_prize_label_review_catalog_item_rows", 0
            ),
            "multi_item_prize_label_manual_review_catalog_item_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "multi_item_prize_label_manual_review_catalog_item_rows", 0
            ),
            "numbered_variant_complete_prize_label_groups": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_complete_prize_label_groups", 0
            ),
            "numbered_variant_prize_label_groups": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_prize_label_groups", 0
            ),
            "incomplete_numbered_variant_prize_label_groups": ichiban_kuji_prize_policy_audit_summary.get(
                "incomplete_numbered_variant_prize_label_groups", 0
            ),
            "numbered_variant_coverage_policy_pass": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_coverage_policy_pass", False
            ),
            "numbered_variant_application_write": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_application_write", False
            ),
            "numbered_variant_source_prizes_considered": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_source_prizes_considered", 0
            ),
            "numbered_variant_applied_prizes": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_applied_prizes", 0
            ),
            "numbered_variant_updated_existing_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_updated_existing_rows", 0
            ),
            "numbered_variant_created_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_created_rows", 0
            ),
            "numbered_variant_application_skipped_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "numbered_variant_application_skipped_rows", 0
            ),
            "repeated_name_different_source_groups": ichiban_kuji_prize_policy_audit_summary.get(
                "repeated_name_different_source_groups", 0
            ),
            "repeated_name_different_source_review_batch_count": ichiban_kuji_prize_policy_audit_summary.get(
                "repeated_name_different_source_review_batch_count", 0
            ),
            "repeated_name_different_source_review_catalog_item_rows": ichiban_kuji_prize_policy_audit_summary.get(
                "repeated_name_different_source_review_catalog_item_rows", 0
            ),
            "probable_reissue_review_groups": ichiban_kuji_prize_policy_audit_summary.get(
                "probable_reissue_review_groups", 0
            ),
            "prize_policy_review_batch_count": ichiban_kuji_prize_policy_audit_summary.get(
                "prize_policy_review_batch_count", 0
            ),
            "zero_price_exception_policy_pass": ichiban_kuji_prize_policy_audit_summary.get(
                "zero_price_exception_policy_pass", False
            ),
            "auto_apply_enabled": ichiban_kuji_prize_policy_audit_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Work the next prize policy review batch; verify same-prize variants and repeated-name campaign URLs against official 1kuji pages before mutation.",
        } if ichiban_kuji_prize_policy_audit_summary else None,
        {
            "priority": 60,
            "workstream": "animation_folder_visuals",
            "public_report": f"data/{ANIMATION_CATEGORIES.name}",
            "category_count": animation_summary.get("category_count", 0),
            "unknown_category_rows": animation_summary.get("unknown_category_rows", 0),
            "app_folder_color_count": animation_summary.get("app_folder_color_count", 0),
            "app_folder_icon_option_count": animation_summary.get("app_folder_icon_option_count", 0),
            "app_folder_palette_sorted_by_family": animation_summary.get("app_folder_palette_sorted_by_family", False),
            "recommended_next_action": "Use taxonomy_review_queue and folder_visual_tokens for app folder colors, icons, and category cleanup.",
        },
        {
            "priority": 61,
            "workstream": "animation_category_review_batches",
            "public_report": f"data/{ANIMATION_CATEGORY_REVIEW_BATCHES.name}",
            "batch_count": animation_review_batches_summary.get("batch_count", 0),
            "source_rows": animation_review_batches_summary.get("source_rows", 0),
            "folder_visual_token_count": animation_review_batches_summary.get("folder_visual_token_count", 0),
            "app_folder_color_count": animation_review_batches_summary.get("app_folder_color_count", 0),
            "app_folder_icon_option_count": animation_review_batches_summary.get("app_folder_icon_option_count", 0),
            "app_folder_palette_sorted_by_family": animation_review_batches_summary.get(
                "app_folder_palette_sorted_by_family", False
            ),
            "recommended_next_action": "Review category batches before applying folder mappings; keep color order grouped by the palette.",
        } if animation_review_batches_summary else None,
        {
            "priority": 62,
            "workstream": "animation_category_action_queue",
            "public_report": f"data/{ANIMATION_CATEGORY_ACTION_QUEUE.name}",
            "queued_categories": animation_action_queue_summary.get("queued_categories", 0),
            "queued_catalog_rows": animation_action_queue_summary.get("queued_catalog_rows", 0),
            "action_batch_count": animation_action_queue_summary.get("action_batch_count", 0),
            "split_review_categories": animation_action_queue_summary.get("split_review_categories", 0),
            "direct_mapping_categories": animation_action_queue_summary.get("direct_mapping_categories", 0),
            "work_order_steps": animation_action_queue_summary.get("work_order_steps", 0),
            "work_order_lanes": animation_action_queue_summary.get("work_order_lanes", []),
            "split_first_blocked_categories": animation_action_queue_summary.get(
                "split_first_blocked_categories", []
            ),
            "app_folder_color_count": animation_action_queue_summary.get("app_folder_color_count", 0),
            "app_folder_icon_option_count": animation_action_queue_summary.get("app_folder_icon_option_count", 0),
            "app_folder_palette_sorted_by_family": animation_action_queue_summary.get(
                "app_folder_palette_sorted_by_family", False
            ),
            "recommended_next_action": "Split broad animation categories before confirming direct category-to-folder mappings.",
        } if animation_action_queue_summary else None,
        {
            "priority": 63,
            "workstream": "animation_category_split_review",
            "public_report": f"data/{ANIMATION_CATEGORY_SPLIT_REVIEW.name}",
            "split_review_categories": animation_split_review_summary.get("split_review_categories", 0),
            "affected_catalog_rows": animation_split_review_summary.get("affected_catalog_rows", 0),
            "candidate_split_rules": animation_split_review_summary.get("candidate_split_rules", 0),
            "matched_sample_names": animation_split_review_summary.get("matched_sample_names", 0),
            "unmatched_sample_names": animation_split_review_summary.get("unmatched_sample_names", 0),
            "catalog_source_category_rows": animation_split_review_summary.get("catalog_source_category_rows", 0),
            "matched_catalog_rows": animation_split_review_summary.get("matched_catalog_rows", 0),
            "unmatched_catalog_rows": animation_split_review_summary.get("unmatched_catalog_rows", 0),
            "auto_apply_enabled": animation_split_review_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Confirm name-level split templates before changing broad goods categories.",
        } if animation_split_review_summary else None,
        {
            "priority": 64,
            "workstream": "animation_category_unmatched_keyword_review",
            "public_report": f"data/{ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.name}",
            "source_categories": animation_unmatched_keyword_review_summary.get("source_categories", 0),
            "unmatched_rows": animation_unmatched_keyword_review_summary.get("unmatched_rows", 0),
            "token_candidate_count": animation_unmatched_keyword_review_summary.get("token_candidate_count", 0),
            "product_type_candidate_count": animation_unmatched_keyword_review_summary.get(
                "product_type_candidate_count", 0
            ),
            "noise_candidate_count": animation_unmatched_keyword_review_summary.get("noise_candidate_count", 0),
            "auto_apply_enabled": animation_unmatched_keyword_review_summary.get("auto_apply_enabled", False),
            "recommended_next_action": "Review unmatched broad-category tokens before adding more split keywords.",
        } if animation_unmatched_keyword_review_summary else None,
    ]
    next_actions = [item for item in next_actions if item is not None]
    workstream_scorecard = [
        {
            "workstream": "requested_focus_enrichment",
            "status": "open" if requested_focus_summary.get("open_rows", 0) else "clear",
            "open_rows": requested_focus_summary.get("open_rows", 0),
            "primary_report": f"data/{REQUESTED_FOCUS.name}",
            "next_step": "work_user_requested_focus_topics_first",
            "auto_apply_enabled": requested_focus_summary.get("auto_apply_enabled", False),
        },
        {
            "workstream": "requested_focus_review_batches",
            "status": "manual_review" if requested_focus_review_batches_summary.get("batch_count", 0) else "clear",
            "open_rows": requested_focus_review_batches_summary.get("review_row_count", 0),
            "primary_report": f"data/{REQUESTED_FOCUS_REVIEW_BATCHES.name}",
            "next_step": "work_requested_focus_batches_by_topic_field_store",
            "auto_apply_enabled": requested_focus_review_batches_summary.get("auto_apply_enabled", False),
        } if requested_focus_review_batches_summary else None,
        {
            "workstream": "requested_focus_action_queue",
            "status": "manual_review" if requested_focus_action_queue_summary.get("action_batch_count", 0) else "clear",
            "open_rows": requested_focus_action_queue_summary.get("queued_action_rows", 0),
            "actionable_template_rows": requested_focus_action_queue_summary.get("actionable_template_rows", 0),
            "unqueued_actionable_rows": requested_focus_action_queue_summary.get("unqueued_actionable_rows", 0),
            "queue_coverage": requested_focus_action_queue_summary.get("queue_coverage", 0),
            "barcode_template_rows_excluded": requested_focus_action_queue_summary.get(
                "barcode_template_rows_excluded", 0
            ),
            "review_url_rows": requested_focus_action_queue_summary.get("review_url_rows", 0),
            "primary_report": f"data/{REQUESTED_FOCUS_ACTION_QUEUE.name}",
            "next_step": "work_non_barcode_requested_focus_batches_first",
            "auto_apply_enabled": requested_focus_action_queue_summary.get("auto_apply_enabled", False),
        } if requested_focus_action_queue_summary else None,
        {
            "workstream": "source_discovery",
            "status": "open" if source_summary.get("source_discovery_rows", 0) else "clear",
            "open_rows": source_summary.get("source_discovery_rows", 0),
            "primary_report": f"data/{SOURCE_DISCOVERY.name}",
            "next_step": "find_exact_official_source_url",
            "auto_apply_enabled": False,
        },
        {
            "workstream": "source_discovery_focus_template",
            "status": "manual_review" if source_focus_template_summary.get("template_items", 0) else "clear",
            "open_rows": source_focus_template_summary.get("template_items", 0),
            "work_order_pack_count": source_focus_template_summary.get("work_order_pack_count", 0),
            "next_focus_pack_id": source_focus_template_summary.get("next_focus_pack_id"),
            "next_source_store": source_focus_template_summary.get("next_source_store"),
            "next_target_category": source_focus_template_summary.get("next_target_category"),
            "next_focus_pack_rows": source_focus_template_summary.get("next_focus_pack_rows", 0),
            "next_official_search_url": source_focus_template_summary.get("next_official_search_url"),
            "template_confirmed_rows": source_focus_template_summary.get("manual_confirmed_rows", 0),
            "dry_run_updated_rows": source_focus_template_import.get("updated_rows", 0),
            "dry_run_skipped_rows": source_focus_template_import.get("skipped_rows", 0),
            "primary_report": f"data/{SOURCE_DISCOVERY_FOCUS_TEMPLATE.name}",
            "next_step": "work_source_focus_template_work_order_top_to_bottom",
            "auto_apply_enabled": source_focus_template_summary.get("auto_apply_enabled", False),
        } if source_focus_template_summary else None,
        {
            "workstream": "source_discovery_next_focus_pack_fetch_audit",
            "status": (
                "fallback_required"
                if source_next_focus_fetch_audit_summary.get("fallback_web_search_required")
                else "ready_for_manual_review"
            ),
            "open_rows": source_next_focus_fetch_audit_summary.get("official_search_unavailable_rows", 0),
            "focus_pack_id": source_next_focus_fetch_audit_summary.get("focus_pack_id"),
            "pack_items": source_next_focus_fetch_audit_summary.get("pack_items", 0),
            "official_search_ok_rows": source_next_focus_fetch_audit_summary.get("official_search_ok_rows", 0),
            "official_search_unavailable_rows": source_next_focus_fetch_audit_summary.get(
                "official_search_unavailable_rows", 0
            ),
            "status_counts": source_next_focus_fetch_audit_summary.get("status_counts", []),
            "primary_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.name}",
            "next_step": "resolve_unavailable_official_search_urls_before_source_import",
            "auto_apply_enabled": source_next_focus_fetch_audit_summary.get("auto_apply_enabled", False),
        } if source_next_focus_fetch_audit_summary else None,
        {
            "workstream": "source_discovery_next_focus_detail_candidates",
            "status": (
                "manual_review"
                if source_next_focus_detail_candidates_summary.get("next_action_lane_count", 0)
                else "clear"
            ),
            "open_rows": source_next_focus_detail_candidates_summary.get("pack_items", 0),
            "focus_pack_id": source_next_focus_detail_candidates_summary.get("focus_pack_id"),
            "items_with_candidates": source_next_focus_detail_candidates_summary.get("items_with_candidates", 0),
            "candidate_rows": source_next_focus_detail_candidates_summary.get("candidate_rows", 0),
            "metadata_enrichment_template_rows": source_next_focus_detail_candidates_summary.get(
                "metadata_enrichment_template_rows",
                0,
            ),
            "metadata_field_import_template_rows": source_next_focus_detail_candidates_summary.get(
                "metadata_field_import_template_rows",
                0,
            ),
            "metadata_field_import_supported_rows": source_next_focus_detail_candidates_summary.get(
                "metadata_field_import_supported_rows",
                0,
            ),
            "metadata_field_import_dry_run_updated_rows": source_next_focus_metadata_field_import_summary.get("updated_rows", 0),
            "metadata_field_import_dry_run_skipped_rows": source_next_focus_metadata_field_import_summary.get("skipped_rows", 0),
            "metadata_field_import_dry_run_skip_reason_counts": source_next_focus_metadata_field_import_summary.get(
                "skip_reason_counts",
                [],
            ),
            "next_action_lane_count": source_next_focus_detail_candidates_summary.get("next_action_lane_count", 0),
            "next_action_lanes": source_next_focus_detail_candidates_summary.get("next_action_lanes", []),
            "completion_readiness_status": source_next_focus_detail_candidates_summary.get(
                "completion_readiness_status"
            ),
            "primary_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.name}",
            "next_step": "resolve_current_focus_pack_lanes_before_source_import",
            "auto_apply_enabled": source_next_focus_detail_candidates_summary.get("auto_apply_enabled", False),
        } if source_next_focus_detail_candidates_summary else None,
        {
            "workstream": "source_discovery_next_focus_fallback_queue",
            "status": "manual_review" if source_next_focus_fallback_queue_summary.get("queue_rows", 0) else "clear",
            "open_rows": source_next_focus_fallback_queue_summary.get("queue_rows", 0),
            "manual_confirmed_rows": source_next_focus_fallback_queue_summary.get("manual_confirmed_rows", 0),
            "fallback_reason": source_next_focus_fallback_queue_summary.get("fallback_reason"),
            "by_source_store": source_next_focus_fallback_queue_summary.get("by_source_store", []),
            "by_category": source_next_focus_fallback_queue_summary.get("by_category", []),
            "primary_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.name}",
            "next_step": "fill_exact_manual_confirmed_source_urls_from_fallback_research",
            "work_order_lanes": source_next_focus_fallback_queue_summary.get("work_order_lanes", []),
            "first_primary_review_url": source_next_focus_fallback_queue_summary.get(
                "first_primary_review_url"
            ),
            "first_primary_review_url_kind": source_next_focus_fallback_queue_summary.get(
                "first_primary_review_url_kind"
            ),
            "auto_apply_enabled": source_next_focus_fallback_queue_summary.get("auto_apply_enabled", False),
        } if source_next_focus_fallback_queue_summary else None,
        {
            "workstream": "source_discovery_starter_queue",
            "status": (
                "manual_review"
                if source_discovery_starter_queue_summary.get("starter_queue_rows", 0)
                else "clear"
            ),
            "open_rows": source_discovery_starter_queue_summary.get("starter_queue_rows", 0),
            "starter_queue_groups": source_discovery_starter_queue_summary.get("starter_queue_groups", 0),
            "coverage_matches_missing_source_url_rows": source_discovery_starter_queue_summary.get(
                "coverage_matches_missing_source_url_rows",
                False,
            ),
            "primary_report": f"data/{SOURCE_DISCOVERY_STARTER_QUEUE.name}",
            "next_step": "find_exact_official_product_source_url",
            "auto_apply_enabled": source_discovery_starter_queue_summary.get("auto_apply_enabled", False),
        } if source_discovery_starter_queue_summary else None,
        {
            "workstream": "source_discovery_review_batches",
            "status": "open" if source_review_batches_summary.get("source_discovery_rows", 0) else "clear",
            "open_rows": source_review_batches_summary.get("source_discovery_rows", 0),
            "primary_report": f"data/{SOURCE_DISCOVERY_REVIEW_BATCHES.name}",
            "next_step": "work_source_discovery_batches_by_store",
            "auto_apply_enabled": source_review_batches_summary.get("auto_apply_enabled", False),
        } if source_review_batches_summary else None,
        {
            "workstream": "source_discovery_action_queue",
            "status": "manual_review" if source_action_queue_summary.get("queued_source_rows", 0) else "clear",
            "open_rows": source_action_queue_summary.get("queued_source_rows", 0),
            "actionable_source_rows": source_action_queue_summary.get("actionable_source_rows", 0),
            "unqueued_actionable_source_rows": source_action_queue_summary.get("unqueued_actionable_source_rows", 0),
            "queue_coverage": source_action_queue_summary.get("queue_coverage", 0),
            "by_review_state": source_action_queue_summary.get("by_review_state", []),
            "by_workflow": source_action_queue_summary.get("by_workflow", []),
            "by_source_store": source_action_queue_summary.get("by_source_store", []),
            "top_source_store_workstreams": source_action_workstreams,
            "excluded_review_state_rows": source_action_queue_summary.get("excluded_review_state_rows", []),
            "manual_research_backlog_rows": source_action_queue_summary.get("manual_research_backlog_rows", 0),
            "manual_research_backlog_by_source_store": source_action_queue_summary.get(
                "manual_research_backlog_by_source_store", []
            ),
            "primary_report": f"data/{SOURCE_DISCOVERY_ACTION_QUEUE.name}",
            "next_step": "confirm_exact_source_url_then_fill_source_templates",
            "auto_apply_enabled": source_action_queue_summary.get("auto_apply_enabled", False),
        } if source_action_queue_summary else None,
        {
            "workstream": "source_detail_candidate_action_queue",
            "status": "manual_review" if source_detail_candidate_action_queue_summary.get("candidate_action_rows", 0) else "clear",
            "open_rows": source_detail_candidate_action_queue_summary.get("candidate_action_rows", 0),
            "action_batch_count": source_detail_candidate_action_queue_summary.get("action_batch_count", 0),
            "manual_confirmed_true": source_detail_candidate_action_queue_summary.get("manual_confirmed_true", 0),
            "safe_source_image_pair_rows": source_detail_candidate_action_queue_summary.get(
                "safe_source_image_pair_rows", 0
            ),
            "manual_confirmation_shortlist_rows": source_detail_candidate_action_queue_summary.get(
                "manual_confirmation_shortlist_rows", 0
            ),
            "candidate_count_review_required_rows": source_detail_candidate_action_queue_summary.get(
                "candidate_count_review_required_rows", 0
            ),
            "priority_manual_review_candidate_rows": source_detail_candidate_action_queue_summary.get(
                "priority_manual_review_candidate_rows", 0
            ),
            "near_or_better_candidate_rows": source_detail_candidate_action_queue_summary.get(
                "near_or_better_candidate_rows", 0
            ),
            "ambiguous_or_weaker_candidate_rows": source_detail_candidate_action_queue_summary.get(
                "ambiguous_or_weaker_candidate_rows", 0
            ),
            "by_source_store": source_detail_candidate_action_queue_summary.get("by_source_store", []),
            "by_review_risk": source_detail_candidate_action_queue_summary.get("by_review_risk", []),
            "by_candidate_count_bucket": source_detail_candidate_action_queue_summary.get(
                "by_candidate_count_bucket", []
            ),
            "primary_report": f"data/{SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.name}",
            "next_step": "confirm_candidate_identity_then_fill_source_and_image_templates",
            "auto_apply_enabled": source_detail_candidate_action_queue_summary.get("auto_apply_enabled", False),
        } if source_detail_candidate_action_queue_summary else None,
        {
            "workstream": "official_detail_review_batches",
            "status": "manual_review" if official_detail_review_batches_summary.get("reviewable_seed_rows", 0) else "clear",
            "open_rows": official_detail_review_batches_summary.get("reviewable_seed_rows", 0),
            "reviewable_candidate_rows": official_detail_review_batches_summary.get("reviewable_candidate_rows", 0),
            "manual_confirmed_true": official_detail_review_batches_summary.get("manual_confirmed_true", 0),
            "by_workflow": official_detail_review_batches_summary.get("by_workflow", []),
            "by_store": official_detail_review_batches_summary.get("by_store", []),
            "primary_report": f"data/{OFFICIAL_DETAIL_REVIEW_BATCHES.name}",
            "next_step": "confirm_official_detail_candidates_before_import",
            "auto_apply_enabled": official_detail_review_batches_summary.get("auto_apply_enabled", False),
        } if official_detail_review_batches_summary else None,
        {
            "workstream": "ensky_cache_candidate_action_queue",
            "status": "manual_review" if ensky_cache_candidate_action_queue_summary.get("candidate_action_rows", 0) else "clear",
            "open_rows": ensky_cache_candidate_action_queue_summary.get("candidate_action_rows", 0),
            "action_batch_count": ensky_cache_candidate_action_queue_summary.get("action_batch_count", 0),
            "manual_confirmed_true": ensky_cache_candidate_action_queue_summary.get("manual_confirmed_true", 0),
            "candidate_source_url_ready_rows": ensky_cache_candidate_action_queue_summary.get(
                "candidate_source_url_ready_rows", 0
            ),
            "candidate_image_url_ready_rows": ensky_cache_candidate_action_queue_summary.get(
                "candidate_image_url_ready_rows", 0
            ),
            "safe_exact_top_candidate_rows": ensky_cache_candidate_action_queue_summary.get(
                "safe_exact_top_candidate_rows", 0
            ),
            "can_import_now_rows": ensky_cache_candidate_action_queue_summary.get("can_import_now_rows", 0),
            "blocked_manual_review_rows": ensky_cache_candidate_action_queue_summary.get(
                "blocked_manual_review_rows", 0
            ),
            "by_affiliation": ensky_cache_candidate_action_queue_summary.get("by_affiliation", []),
            "by_category": ensky_cache_candidate_action_queue_summary.get("by_category", []),
            "import_readiness": ensky_cache_candidate_action_queue.get("import_readiness", {}),
            "primary_report": f"data/{ENSKY_CACHE_CANDIDATE_ACTION_QUEUE.name}",
            "next_step": "manual_confirm_ensky_cache_candidate_then_fill_source_and_image_templates",
            "auto_apply_enabled": ensky_cache_candidate_action_queue_summary.get("auto_apply_enabled", False),
        } if ensky_cache_candidate_action_queue_summary else None,
        {
            "workstream": "danganronpa_missing_media",
            "status": "open" if danganronpa_media_summary.get("missing_media_rows", 0) else "clear",
            "open_rows": danganronpa_media_summary.get("missing_media_rows", 0),
            "primary_report": f"data/{DANGANRONPA_MISSING_MEDIA.name}",
            "next_step": "verify_danganronpa_exact_source_pages",
            "auto_apply_enabled": danganronpa_media_summary.get("auto_apply_enabled", False),
        },
        {
            "workstream": "danganronpa_patch_template_dry_run",
            "status": (
                "manual_review"
                if danganronpa_dry_run_summary.get("ready_rows", 0)
                or danganronpa_dry_run_summary.get("blocked_rows", 0)
                else "pending_confirmation"
            ),
            "open_rows": danganronpa_dry_run_summary.get("template_rows", 0),
            "ready_rows": danganronpa_dry_run_summary.get("ready_rows", 0),
            "blocked_rows": danganronpa_dry_run_summary.get("blocked_rows", 0),
            "primary_report": f"data/{DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.name}",
            "next_step": "fill_and_review_danganronpa_confirmed_patch_template",
            "auto_apply_enabled": danganronpa_dry_run_summary.get("auto_apply_enabled", False),
        },
        {
            "workstream": "image_enrichment",
            "status": "blocked" if image_summary.get("missing_image_rows", 0) else "clear",
            "open_rows": image_summary.get("missing_image_rows", 0),
            "primary_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
            "next_step": "resolve_blocker_summary_before_image_import",
            "auto_apply_enabled": False,
        },
        {
            "workstream": "image_attachment_action_queue",
            "status": "manual_review" if image_action_queue_summary.get("action_batch_count", 0) else "clear",
            "open_rows": image_action_queue_summary.get("queued_image_rows", 0),
            "actionable_image_rows": image_action_queue_summary.get("actionable_image_rows", 0),
            "unqueued_actionable_image_rows": image_action_queue_summary.get("unqueued_actionable_image_rows", 0),
            "sample_queue_coverage": image_action_queue_summary.get("sample_queue_coverage", 0),
            "source_url_update_search_hint_rows": image_action_queue_summary.get(
                "source_url_update_search_hint_rows",
                0,
            ),
            "source_url_update_missing_search_hint_rows": image_action_queue_summary.get(
                "source_url_update_missing_search_hint_rows",
                0,
            ),
            "primary_review_url_rows": image_action_queue_summary.get("primary_review_url_rows", 0),
            "primary_review_url_missing_rows": image_action_queue_summary.get(
                "primary_review_url_missing_rows", 0
            ),
            "primary_review_url_kind_counts": image_action_queue_summary.get(
                "primary_review_url_kind_counts", []
            ),
            "by_review_lane": image_action_queue_summary.get("by_review_lane", []),
            "image_import_blocker_counts": image_action_queue_summary.get(
                "image_import_blocker_counts", []
            ),
            "suggested_local_image_path_rows": image_action_queue_summary.get(
                "suggested_local_image_path_rows", 0
            ),
            "local_image_download_instruction_ready_rows": image_action_queue_summary.get(
                "local_image_download_instruction_ready_rows", 0
            ),
            "blocked_before_image_import_rows": image_action_queue_summary.get(
                "blocked_before_image_import_rows", 0
            ),
            "download_ready_after_manual_image_url_rows": image_action_queue_summary.get(
                "download_ready_after_manual_image_url_rows", 0
            ),
            "by_workflow": image_action_queue_summary.get("by_workflow", []),
            "by_source_store": image_action_queue_summary.get("by_source_store", []),
            "top_image_attachment_workstreams": image_action_workstreams,
            "excluded_workflow_rows": image_action_queue_summary.get("excluded_workflow_rows", []),
            "attachment_readiness": image_action_queue.get("attachment_readiness", {}),
            "primary_report": f"data/{IMAGE_ATTACHMENT_ACTION_QUEUE.name}",
            "next_step": "confirm_source_then_fill_image_url_templates",
            "auto_apply_enabled": image_action_queue_summary.get("auto_apply_enabled", False),
        } if image_action_queue_summary else None,
        {
            "workstream": "metadata_backlog",
            "status": "open" if sum(int(value or 0) for value in metadata_summary.get("field_missing_totals", {}).values()) else "clear",
            "open_rows": sum(int(value or 0) for value in metadata_summary.get("field_missing_totals", {}).values()),
            "primary_report": f"data/{METADATA_BACKLOG.name}",
            "next_step": "review_field_evidence_policy",
            "auto_apply_enabled": False,
        },
        {
            "workstream": "metadata_review_batches",
            "status": "manual_review" if metadata_review_batches_summary.get("missing_cell_count", 0) else "clear",
            "open_rows": metadata_review_batches_summary.get("missing_cell_count", 0),
            "primary_report": f"data/{METADATA_REVIEW_BATCHES.name}",
            "next_step": "work_full_metadata_review_batches",
            "auto_apply_enabled": metadata_review_batches_summary.get("auto_apply_enabled", False),
        } if metadata_review_batches_summary else None,
        {
            "workstream": "metadata_action_queue",
            "status": "manual_review" if metadata_action_queue_summary.get("queued_missing_cells", 0) else "clear",
            "open_rows": metadata_action_queue_summary.get("queued_missing_cells", 0),
            "actionable_group_count": metadata_action_queue_summary.get("actionable_group_count", 0),
            "unqueued_actionable_group_count": metadata_action_queue_summary.get(
                "unqueued_actionable_group_count", 0
            ),
            "actionable_missing_cells": metadata_action_queue_summary.get("actionable_missing_cells", 0),
            "unqueued_actionable_missing_cells": metadata_action_queue_summary.get(
                "unqueued_actionable_missing_cells", 0
            ),
            "group_queue_coverage": metadata_action_queue_summary.get("group_queue_coverage", 0),
            "missing_cell_queue_coverage": metadata_action_queue_summary.get("missing_cell_queue_coverage", 0),
            "primary_review_url_groups": metadata_action_queue_summary.get("primary_review_url_groups", 0),
            "first_primary_review_url": metadata_action_queue_summary.get("first_primary_review_url"),
            "first_primary_review_url_kind": metadata_action_queue_summary.get("first_primary_review_url_kind"),
            "primary_review_url_kind_counts": metadata_action_queue_summary.get(
                "primary_review_url_kind_counts", []
            ),
            "primary_report": f"data/{METADATA_ACTION_QUEUE.name}",
            "next_step": "fill_confirmed_metadata_patch_templates",
            "missing_cells_by_field": metadata_action_queue_summary.get("missing_cells_by_field", []),
            "missing_cells_by_source_store": metadata_action_queue_summary.get("missing_cells_by_source_store", []),
            "top_action_groups": metadata_action_queue_summary.get("top_action_groups", []),
            "auto_apply_enabled": metadata_action_queue_summary.get("auto_apply_enabled", False),
        } if metadata_action_queue_summary else None,
        {
            "workstream": "deduplication",
            "status": "manual_review" if dedupe_summary.get("duplicate_groups", 0) else "clear",
            "open_rows": dedupe_summary.get("duplicate_groups", 0),
            "primary_report": f"data/{DEDUPLICATION.name}",
            "next_step": "review_risk_ranked_duplicate_groups",
            "auto_apply_enabled": False,
        },
        {
            "workstream": "deduplication_review_batches",
            "status": "manual_review" if dedupe_review_batches_summary.get("source_groups", 0) else "clear",
            "open_rows": dedupe_review_batches_summary.get("source_groups", 0),
            "primary_report": f"data/{DEDUPLICATION_REVIEW_BATCHES.name}",
            "next_step": "record_manual_keep_drop_decisions",
            "auto_apply_enabled": False,
        } if dedupe_review_batches_summary else None,
        {
            "workstream": "deduplication_action_queue",
            "status": "manual_review" if dedupe_action_queue_summary.get("queued_groups", 0) else "clear",
            "open_rows": dedupe_action_queue_summary.get("queued_groups", 0),
            "actionable_groups": dedupe_action_queue_summary.get("actionable_groups", 0),
            "unqueued_actionable_groups": dedupe_action_queue_summary.get("unqueued_actionable_groups", 0),
            "queue_coverage": dedupe_action_queue_summary.get("queue_coverage", 0),
            "ichiban_reissue_review_groups": dedupe_action_queue_summary.get("ichiban_reissue_review_groups", 0),
            "ichiban_probable_reissue_review_groups": dedupe_action_queue_summary.get(
                "ichiban_probable_reissue_review_groups", 0
            ),
            "ichiban_reissue_protected_groups": dedupe_action_queue_summary.get(
                "ichiban_reissue_protected_groups", 0
            ),
            "primary_report": f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
            "next_step": "review_high_medium_confidence_dedupe_first",
            "auto_apply_enabled": dedupe_action_queue_summary.get("auto_delete_enabled", False),
        } if dedupe_action_queue_summary else None,
        {
            "workstream": "deduplication_template_import_dry_run",
            "status": "blocked"
            if dedupe_template_import_dry_run_summary.get("skipped_rows", 0)
            else "ready",
            "open_rows": dedupe_template_import_dry_run_summary.get("skipped_rows", 0),
            "ready_decision_rows": dedupe_template_import_dry_run_summary.get("ready_decision_rows", 0),
            "updated_rows": dedupe_template_import_dry_run_summary.get("updated_rows", 0),
            "primary_report": f"data/{DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN.name}",
            "next_step": "set_manual_confirmed_and_same_sellable_product_confirmed_before_write_import",
            "auto_apply_enabled": False,
        } if dedupe_template_import_dry_run_summary else None,
        {
            "workstream": "ichiban_kuji_reissue_dedupe_review",
            "status": "manual_review"
            if dedupe_action_queue_summary.get("ichiban_reissue_review_groups", 0)
            else "clear",
            "open_rows": dedupe_action_queue_summary.get("ichiban_reissue_review_groups", 0),
            "probable_reissue_groups": dedupe_action_queue_summary.get(
                "ichiban_probable_reissue_review_groups", 0
            ),
            "review_rows": dedupe_action_queue_summary.get("ichiban_reissue_review_rows", 0),
            "work_order_rows": dedupe_action_queue_summary.get("ichiban_reissue_work_order_rows", 0),
            "decision_template_rows": dedupe_action_queue_summary.get(
                "ichiban_reissue_decision_template_rows", 0
            ),
            "manual_confirmed_rows": dedupe_action_queue_summary.get(
                "ichiban_reissue_manual_confirmed_rows", 0
            ),
            "protected_groups": dedupe_action_queue_summary.get("ichiban_reissue_protected_groups", 0),
            "primary_report": f"data/{ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE.name}",
            "work_order_report": f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
            "next_step": "fill_ichiban_reissue_decision_template_before_dedupe",
            "auto_apply_enabled": False,
        } if dedupe_action_queue_summary else None,
        {
            "workstream": "ichiban_kuji_history",
            "status": "open" if kuji_summary.get("campaign_metadata_review_queue_rows", 0) else "clear",
            "open_rows": kuji_summary.get("campaign_metadata_review_queue_rows", 0),
            "primary_report": f"data/{ICHIIBAN_KUJI_HISTORY.name}",
            "next_step": "verify_campaign_metadata_review_queue",
            "auto_apply_enabled": False,
        },
        {
            "workstream": "ichiban_kuji_metadata_probe",
            "status": "blocked" if ichiban_kuji_metadata_probe_summary and not (
                ichiban_kuji_metadata_probe_summary.get("safe_release_row_count", 0)
                or ichiban_kuji_metadata_probe_summary.get("safe_price_row_count", 0)
            ) else "open",
            "open_rows": ichiban_kuji_metadata_probe_summary.get("rows_missing_release_date", 0)
            + ichiban_kuji_metadata_probe_summary.get("rows_missing_official_price_jpy", 0),
            "primary_report": f"data/{ICHIIBAN_KUJI_METADATA_PROBE.name}",
            "next_step": "find_labeled_official_ichiban_metadata_evidence",
            "auto_apply_enabled": ichiban_kuji_metadata_probe_summary.get("auto_apply_enabled", False),
        } if ichiban_kuji_metadata_probe_summary else None,
        {
            "workstream": "ichiban_kuji_metadata_review_batches",
            "status": "manual_review" if ichiban_kuji_metadata_review_batches_summary.get("source_campaigns", 0) else "clear",
            "open_rows": ichiban_kuji_metadata_review_batches_summary.get("catalog_item_rows", 0),
            "primary_report": f"data/{ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES.name}",
            "next_step": "verify_batched_ichiban_campaign_metadata",
            "auto_apply_enabled": ichiban_kuji_metadata_review_batches_summary.get("auto_apply_enabled", False),
        } if ichiban_kuji_metadata_review_batches_summary else None,
        {
            "workstream": "ichiban_kuji_metadata_action_queue",
            "status": "manual_review" if ichiban_kuji_metadata_action_queue_summary.get("queued_action_campaigns", 0) else "clear",
            "open_rows": ichiban_kuji_metadata_action_queue_summary.get("queued_action_campaigns", 0),
            "actionable_campaigns": ichiban_kuji_metadata_action_queue_summary.get("actionable_campaigns", 0),
            "unqueued_action_campaigns": ichiban_kuji_metadata_action_queue_summary.get("unqueued_action_campaigns", 0),
            "campaign_queue_coverage": ichiban_kuji_metadata_action_queue_summary.get("campaign_queue_coverage", 0),
            "queued_catalog_item_rows": ichiban_kuji_metadata_action_queue_summary.get("queued_catalog_item_rows", 0),
            "primary_report": f"data/{ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.name}",
            "next_step": "fill_confirmed_ichiban_campaign_patch_templates",
            "next_campaign_patch_review_batch_rows": ichiban_kuji_metadata_action_queue_summary.get(
                "next_campaign_patch_review_batch_rows", 0
            ),
            "next_campaign_patch_review_batch_template_rows": ichiban_kuji_metadata_action_queue_summary.get(
                "next_campaign_patch_review_batch_template_rows", 0
            ),
            "next_campaign_patch_review_batch_field_counts": (
                ichiban_kuji_metadata_action_queue_summary.get(
                    "next_campaign_patch_review_batch_field_counts", []
                )
            ),
            "work_order_lanes": ichiban_kuji_metadata_action_queue_summary.get("work_order_lanes", []),
            "auto_apply_enabled": ichiban_kuji_metadata_action_queue_summary.get("auto_apply_enabled", False),
        } if ichiban_kuji_metadata_action_queue_summary else None,
        {
            "workstream": "ichiban_kuji_prize_name_image_review",
            "status": "manual_review" if ichiban_kuji_prize_name_image_review_summary.get("review_rows", 0) else "clear",
            "open_rows": ichiban_kuji_prize_name_image_review_summary.get("review_rows", 0),
            "name_structure_review_rows": ichiban_kuji_prize_name_image_review_summary.get(
                "name_structure_review_rows", 0
            ),
            "image_identity_review_rows": ichiban_kuji_prize_name_image_review_summary.get(
                "image_identity_review_rows", 0
            ),
            "multi_item_prize_rank_groups": ichiban_kuji_prize_name_image_review_summary.get(
                "multi_item_prize_rank_groups", 0
            ),
            "multi_item_prize_rank_catalog_rows": ichiban_kuji_prize_name_image_review_summary.get(
                "multi_item_prize_rank_catalog_rows", 0
            ),
            "primary_report": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}",
            "next_step": "confirm_prize_name_components_and_image_identity",
            "auto_apply_enabled": ichiban_kuji_prize_name_image_review_summary.get("auto_apply_enabled", False),
        } if ichiban_kuji_prize_name_image_review_summary else None,
        {
            "workstream": "ichiban_kuji_prize_name_image_patch_candidates",
            "status": "manual_review"
            if ichiban_kuji_prize_name_image_patch_candidates_summary.get("open_candidate_rows", 0)
            else "clear",
            "open_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get("open_candidate_rows", 0),
            "candidate_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get("candidate_rows", 0),
            "manual_confirmed_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "manual_confirmed_rows", 0
            ),
            "exact_image_match_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "exact_image_match_rows", 0
            ),
            "strong_name_match_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "strong_name_match_rows", 0
            ),
            "blocked_rows": ichiban_kuji_prize_name_image_patch_candidates_summary.get("blocked_rows", 0),
            "primary_report": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.name}",
            "next_step": "manual_confirm_exact_official_patch_candidates",
            "auto_apply_enabled": ichiban_kuji_prize_name_image_patch_candidates_summary.get(
                "auto_apply_enabled", False
            ),
        } if ichiban_kuji_prize_name_image_patch_candidates_summary else None,
        {
            "workstream": "animation_taxonomy",
            "status": "manual_review" if animation_summary.get("unknown_category_rows", 0) else "clear",
            "open_rows": animation_summary.get("unknown_category_rows", 0),
            "primary_report": f"data/{ANIMATION_CATEGORIES.name}",
            "next_step": "review_taxonomy_folder_visual_tokens",
            "app_folder_color_count": animation_summary.get("app_folder_color_count", 0),
            "app_folder_icon_option_count": animation_summary.get("app_folder_icon_option_count", 0),
            "app_folder_palette_sorted_by_family": animation_summary.get("app_folder_palette_sorted_by_family", False),
            "auto_apply_enabled": False,
        },
        {
            "workstream": "animation_category_review_batches",
            "status": "manual_review" if animation_review_batches_summary.get("source_rows", 0) else "clear",
            "open_rows": animation_review_batches_summary.get("source_rows", 0),
            "primary_report": f"data/{ANIMATION_CATEGORY_REVIEW_BATCHES.name}",
            "next_step": "review_batched_taxonomy_folder_visual_decisions",
            "app_folder_color_count": animation_review_batches_summary.get("app_folder_color_count", 0),
            "app_folder_icon_option_count": animation_review_batches_summary.get("app_folder_icon_option_count", 0),
            "app_folder_palette_sorted_by_family": animation_review_batches_summary.get(
                "app_folder_palette_sorted_by_family", False
            ),
            "auto_apply_enabled": animation_review_batches_summary.get("auto_apply_enabled", False),
        } if animation_review_batches_summary else None,
        {
            "workstream": "animation_category_action_queue",
            "status": "manual_review" if animation_action_queue_summary.get("queued_catalog_rows", 0) else "clear",
            "open_rows": animation_action_queue_summary.get("queued_catalog_rows", 0),
            "split_review_categories": animation_action_queue_summary.get("split_review_categories", 0),
            "direct_mapping_categories": animation_action_queue_summary.get("direct_mapping_categories", 0),
            "work_order_steps": animation_action_queue_summary.get("work_order_steps", 0),
            "work_order_lanes": animation_action_queue_summary.get("work_order_lanes", []),
            "split_first_blocked_categories": animation_action_queue_summary.get(
                "split_first_blocked_categories", []
            ),
            "primary_report": f"data/{ANIMATION_CATEGORY_ACTION_QUEUE.name}",
            "next_step": (
                animation_action_queue_work_order[0].get("next_step")
                if animation_action_queue_work_order
                else "fill_confirmed_animation_category_mapping_templates"
            ),
            "app_folder_color_count": animation_action_queue_summary.get("app_folder_color_count", 0),
            "app_folder_icon_option_count": animation_action_queue_summary.get("app_folder_icon_option_count", 0),
            "app_folder_palette_sorted_by_family": animation_action_queue_summary.get(
                "app_folder_palette_sorted_by_family", False
            ),
            "auto_apply_enabled": animation_action_queue_summary.get("auto_apply_enabled", False),
        } if animation_action_queue_summary else None,
        {
            "workstream": "animation_category_split_review",
            "status": "manual_review" if animation_split_review_summary.get("affected_catalog_rows", 0) else "clear",
            "open_rows": animation_split_review_summary.get("affected_catalog_rows", 0),
            "split_review_categories": animation_split_review_summary.get("split_review_categories", 0),
            "candidate_split_rules": animation_split_review_summary.get("candidate_split_rules", 0),
            "matched_sample_names": animation_split_review_summary.get("matched_sample_names", 0),
            "unmatched_sample_names": animation_split_review_summary.get("unmatched_sample_names", 0),
            "catalog_source_category_rows": animation_split_review_summary.get("catalog_source_category_rows", 0),
            "matched_catalog_rows": animation_split_review_summary.get("matched_catalog_rows", 0),
            "unmatched_catalog_rows": animation_split_review_summary.get("unmatched_catalog_rows", 0),
            "primary_report": f"data/{ANIMATION_CATEGORY_SPLIT_REVIEW.name}",
            "next_step": "confirm_animation_category_name_split_templates",
            "auto_apply_enabled": animation_split_review_summary.get("auto_apply_enabled", False),
        } if animation_split_review_summary else None,
        {
            "workstream": "animation_category_unmatched_keyword_review",
            "status": "manual_review" if animation_unmatched_keyword_review_summary.get("unmatched_rows", 0) else "clear",
            "open_rows": animation_unmatched_keyword_review_summary.get("unmatched_rows", 0),
            "source_categories": animation_unmatched_keyword_review_summary.get("source_categories", 0),
            "token_candidate_count": animation_unmatched_keyword_review_summary.get("token_candidate_count", 0),
            "product_type_candidate_count": animation_unmatched_keyword_review_summary.get(
                "product_type_candidate_count", 0
            ),
            "noise_candidate_count": animation_unmatched_keyword_review_summary.get("noise_candidate_count", 0),
            "primary_report": f"data/{ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.name}",
            "next_step": "review_unmatched_animation_keyword_candidates",
            "auto_apply_enabled": animation_unmatched_keyword_review_summary.get("auto_apply_enabled", False),
        } if animation_unmatched_keyword_review_summary else None,
        {
            "workstream": "generic_source_patch_candidates",
            "status": "candidate_review" if generic_patch_summary.get("candidate_rows", 0) else "clear",
            "open_rows": generic_patch_summary.get("candidate_rows", 0),
            "primary_report": f"data/{GENERIC_SOURCE_PATCH_CANDIDATES.name}",
            "next_step": "verify_weak_candidates_before_patch",
            "auto_apply_enabled": generic_patch_summary.get("auto_apply_enabled", False),
        },
    ]

    open_review_queues = {
        "source_discovery_rows": source_summary.get("source_discovery_rows", 0),
        "image_missing_rows": image_summary.get("missing_image_rows", 0),
        "dedupe_groups": dedupe_summary.get("duplicate_groups", 0),
        "animation_unknown_categories": animation_summary.get("unknown_category_count", 0),
        "ichiban_missing_release_date_rows": kuji_summary.get("missing_release_date_rows", 0),
        "ichiban_missing_price_rows": kuji_summary.get("missing_official_price_jpy_rows", 0),
        "generic_source_patch_candidate_rows": generic_patch_summary.get("candidate_rows", 0),
        "requested_focus_open_rows": requested_focus_summary.get("open_rows", 0),
        "danganronpa_missing_media_rows": danganronpa_media_summary.get("missing_media_rows", 0),
        "danganronpa_patch_template_pending_rows": danganronpa_dry_run_summary.get("skipped_rows", 0),
        "danganronpa_patch_template_ready_rows": danganronpa_dry_run_summary.get("ready_rows", 0),
    }
    if confirmed_import_readiness_summary:
        open_review_queues["confirmed_import_template_rows"] = confirmed_import_readiness_summary.get("template_items", 0)
        open_review_queues["confirmed_import_action_queue_rows"] = confirmed_import_readiness_summary.get(
            "public_action_queue_rows", 0
        )
        open_review_queues["confirmed_import_pending_rows"] = confirmed_import_readiness_summary.get(
            "ready_or_pending_import_rows", 0
        )
        open_review_queues[
            "confirmed_import_variant_metadata_template_rows"
        ] = confirmed_import_readiness_summary.get("variant_metadata_template_rows", 0)
    if dedupe_action_queue_summary:
        open_review_queues["dedupe_action_groups"] = dedupe_action_queue_summary.get("queued_groups", 0)
        open_review_queues["dedupe_actionable_groups"] = dedupe_action_queue_summary.get("actionable_groups", 0)
        open_review_queues["dedupe_unqueued_actionable_groups"] = dedupe_action_queue_summary.get(
            "unqueued_actionable_groups", 0
        )
        open_review_queues["ichiban_reissue_dedupe_review_groups"] = dedupe_action_queue_summary.get(
            "ichiban_reissue_review_groups", 0
        )
        open_review_queues["ichiban_probable_reissue_dedupe_review_groups"] = dedupe_action_queue_summary.get(
            "ichiban_probable_reissue_review_groups", 0
        )
    if requested_focus_review_batches_summary:
        open_review_queues["requested_focus_review_rows"] = requested_focus_review_batches_summary.get("review_row_count", 0)
    if requested_focus_action_queue_summary:
        open_review_queues["requested_focus_action_rows"] = requested_focus_action_queue_summary.get("queued_action_rows", 0)
        open_review_queues["requested_focus_actionable_rows"] = requested_focus_action_queue_summary.get(
            "actionable_template_rows", 0
        )
        open_review_queues["requested_focus_unqueued_actionable_rows"] = requested_focus_action_queue_summary.get(
            "unqueued_actionable_rows", 0
        )
        open_review_queues["requested_focus_barcode_template_rows_excluded"] = (
            requested_focus_action_queue_summary.get("barcode_template_rows_excluded", 0)
        )
    if source_action_queue_summary:
        open_review_queues["source_discovery_action_rows"] = source_action_queue_summary.get("queued_source_rows", 0)
        open_review_queues["source_discovery_actionable_rows"] = source_action_queue_summary.get(
            "actionable_source_rows", 0
        )
        open_review_queues["source_discovery_unqueued_actionable_rows"] = source_action_queue_summary.get(
            "unqueued_actionable_source_rows", 0
        )
        open_review_queues["source_discovery_manual_research_backlog_rows"] = (
            source_action_queue_summary.get("manual_research_backlog_rows", 0)
        )
        open_review_queues["source_discovery_manual_identity_backfill_required_rows"] = (
            source_action_queue_summary.get("manual_research_identity_backfill_required_rows", 0)
        )
        open_review_queues["source_discovery_manual_official_lookup_rows"] = (
            source_action_queue_summary.get("manual_research_official_lookup_rows", 0)
        )
    if source_focus_template_summary:
        open_review_queues["source_discovery_focus_template_rows"] = source_focus_template_summary.get(
            "template_items", 0
        )
        open_review_queues["source_discovery_focus_template_work_order_packs"] = source_focus_template_summary.get(
            "work_order_pack_count", 0
        )
        open_review_queues["source_discovery_focus_template_dry_run_skipped_rows"] = source_focus_template_import.get(
            "skipped_rows", 0
        )
    if source_next_focus_pack_summary:
        open_review_queues["source_discovery_next_focus_pack_rows"] = source_next_focus_pack_summary.get(
            "pack_items", 0
        )
        open_review_queues["source_discovery_focus_pack_progress_queues"] = source_next_focus_pack_summary.get(
            "focus_pack_progress_queue_count", 0
        )
        open_review_queues["source_discovery_focus_pack_progress_remaining_rows"] = (
            source_next_focus_pack_summary.get("focus_pack_progress_remaining_rows", 0)
        )
    if source_discovery_starter_queue_summary:
        open_review_queues["source_discovery_starter_queue_rows"] = source_discovery_starter_queue_summary.get(
            "starter_queue_rows", 0
        )
        open_review_queues["source_discovery_starter_queue_groups"] = source_discovery_starter_queue_summary.get(
            "starter_queue_groups", 0
        )
    if source_next_focus_fallback_queue_summary:
        open_review_queues["source_discovery_next_focus_fallback_rows"] = (
            source_next_focus_fallback_queue_summary.get("queue_rows", 0)
        )
        open_review_queues["source_discovery_next_focus_fallback_manual_confirmed_rows"] = (
            source_next_focus_fallback_queue_summary.get("manual_confirmed_rows", 0)
        )
    if source_detail_candidate_action_queue_summary:
        open_review_queues["source_detail_candidate_action_rows"] = (
            source_detail_candidate_action_queue_summary.get("candidate_action_rows", 0)
        )
        open_review_queues["source_detail_candidate_manual_confirmed_rows"] = (
            source_detail_candidate_action_queue_summary.get("manual_confirmed_true", 0)
        )
        open_review_queues["source_detail_candidate_manual_confirmation_shortlist_rows"] = (
            source_detail_candidate_action_queue_summary.get("manual_confirmation_shortlist_rows", 0)
        )
        open_review_queues["source_detail_candidate_count_review_required_rows"] = (
            source_detail_candidate_action_queue_summary.get("candidate_count_review_required_rows", 0)
        )
        open_review_queues["source_detail_candidate_priority_manual_review_rows"] = (
            source_detail_candidate_action_queue_summary.get("priority_manual_review_candidate_rows", 0)
        )
    if official_detail_review_batches_summary:
        open_review_queues["official_detail_review_rows"] = (
            official_detail_review_batches_summary.get("reviewable_seed_rows", 0)
        )
        open_review_queues["official_detail_review_candidate_rows"] = (
            official_detail_review_batches_summary.get("reviewable_candidate_rows", 0)
        )
        open_review_queues["official_detail_review_manual_confirmed_rows"] = (
            official_detail_review_batches_summary.get("manual_confirmed_true", 0)
        )
    if ensky_cache_candidate_action_queue_summary:
        open_review_queues["ensky_cache_candidate_action_rows"] = ensky_cache_candidate_action_queue_summary.get(
            "candidate_action_rows", 0
        )
        open_review_queues["ensky_cache_candidate_manual_confirmed_rows"] = (
            ensky_cache_candidate_action_queue_summary.get("manual_confirmed_true", 0)
        )
    if image_action_queue_summary:
        open_review_queues["image_attachment_action_rows"] = image_action_queue_summary.get("queued_image_rows", 0)
        open_review_queues["image_attachment_actionable_rows"] = image_action_queue_summary.get(
            "actionable_image_rows", 0
        )
        open_review_queues["image_attachment_unqueued_actionable_rows"] = image_action_queue_summary.get(
            "unqueued_actionable_image_rows", 0
        )
        open_review_queues["image_attachment_source_url_search_hint_rows"] = image_action_queue_summary.get(
            "source_url_update_search_hint_rows", 0
        )
        open_review_queues["image_attachment_source_url_missing_search_hint_rows"] = image_action_queue_summary.get(
            "source_url_update_missing_search_hint_rows", 0
        )
        open_review_queues["image_attachment_source_url_fallback_web_search_rows"] = (
            image_action_queue_summary.get("source_url_update_fallback_web_search_rows", 0)
        )
        open_review_queues["image_attachment_source_url_any_search_hint_rows"] = (
            image_action_queue_summary.get("source_url_update_any_search_hint_rows", 0)
        )
        open_review_queues["image_attachment_source_url_missing_any_search_hint_rows"] = (
            image_action_queue_summary.get("source_url_update_missing_any_search_hint_rows", 0)
        )
        open_review_queues["image_attachment_local_download_ready_rows"] = (
            image_action_queue_summary.get("local_image_download_instruction_ready_rows", 0)
        )
    if ichiban_kuji_metadata_action_queue_summary:
        open_review_queues["ichiban_metadata_action_campaigns"] = ichiban_kuji_metadata_action_queue_summary.get(
            "queued_action_campaigns", 0
        )
        open_review_queues["ichiban_metadata_actionable_campaigns"] = ichiban_kuji_metadata_action_queue_summary.get(
            "actionable_campaigns", 0
        )
        open_review_queues["ichiban_metadata_unqueued_action_campaigns"] = (
            ichiban_kuji_metadata_action_queue_summary.get("unqueued_action_campaigns", 0)
        )
        open_review_queues["ichiban_metadata_queued_catalog_item_rows"] = (
            ichiban_kuji_metadata_action_queue_summary.get("queued_catalog_item_rows", 0)
        )
        open_review_queues["ichiban_metadata_next_campaign_patch_review_batch_rows"] = (
            ichiban_kuji_metadata_action_queue_summary.get("next_campaign_patch_review_batch_rows", 0)
        )
        open_review_queues["ichiban_metadata_next_campaign_patch_review_batch_template_rows"] = (
            ichiban_kuji_metadata_action_queue_summary.get(
                "next_campaign_patch_review_batch_template_rows", 0
            )
        )
        open_review_queues["ichiban_metadata_next_campaign_patch_review_batch_primary_review_url_rows"] = (
            ichiban_kuji_metadata_action_queue_summary.get(
                "next_campaign_patch_review_batch_primary_review_url_rows", 0
            )
        )
    if metadata_action_queue_summary:
        open_review_queues["metadata_action_missing_cells"] = metadata_action_queue_summary.get(
            "queued_missing_cells", 0
        )
        open_review_queues["metadata_actionable_groups"] = metadata_action_queue_summary.get(
            "actionable_group_count", 0
        )
        open_review_queues["metadata_unqueued_actionable_groups"] = metadata_action_queue_summary.get(
            "unqueued_actionable_group_count", 0
        )
        open_review_queues["metadata_actionable_missing_cells"] = metadata_action_queue_summary.get(
            "actionable_missing_cells", 0
        )
        open_review_queues["metadata_unqueued_actionable_missing_cells"] = metadata_action_queue_summary.get(
            "unqueued_actionable_missing_cells", 0
        )
        open_review_queues["metadata_primary_review_url_groups"] = metadata_action_queue_summary.get(
            "primary_review_url_groups", 0
        )
    if animation_review_batches_summary:
        open_review_queues["animation_category_review_rows"] = animation_review_batches_summary.get("source_rows", 0)
    if animation_action_queue_summary:
        open_review_queues["animation_category_action_rows"] = animation_action_queue_summary.get(
            "queued_catalog_rows", 0
        )
        open_review_queues["animation_category_split_review_categories"] = animation_action_queue_summary.get(
            "split_review_categories", 0
        )
        open_review_queues["animation_category_direct_mapping_categories"] = animation_action_queue_summary.get(
            "direct_mapping_categories", 0
        )
    if animation_split_review_summary:
        open_review_queues["animation_category_name_split_rows"] = animation_split_review_summary.get(
            "affected_catalog_rows", 0
        )
        open_review_queues["animation_category_name_split_candidates"] = animation_split_review_summary.get(
            "candidate_split_rules", 0
        )
        open_review_queues["animation_category_name_split_unmatched_catalog_rows"] = (
            animation_split_review_summary.get("unmatched_catalog_rows", 0)
        )
    if animation_unmatched_keyword_review_summary:
        open_review_queues["animation_category_unmatched_keyword_rows"] = (
            animation_unmatched_keyword_review_summary.get("unmatched_rows", 0)
        )
        open_review_queues["animation_category_unmatched_keyword_candidates"] = (
            animation_unmatched_keyword_review_summary.get("token_candidate_count", 0)
        )
        open_review_queues["animation_category_unmatched_keyword_product_type_candidates"] = (
            animation_unmatched_keyword_review_summary.get("product_type_candidate_count", 0)
        )
    if ichiban_kuji_prize_name_image_review_summary:
        open_review_queues["ichiban_prize_name_image_review_rows"] = (
            ichiban_kuji_prize_name_image_review_summary.get("review_rows", 0)
        )
        open_review_queues["ichiban_prize_multi_item_rank_groups"] = (
            ichiban_kuji_prize_name_image_review_summary.get("multi_item_prize_rank_groups", 0)
        )
    if ichiban_kuji_prize_name_image_patch_candidates_summary:
        open_review_queues["ichiban_prize_name_image_patch_candidate_rows"] = (
            ichiban_kuji_prize_name_image_patch_candidates_summary.get("open_candidate_rows", 0)
        )
        open_review_queues["ichiban_prize_name_image_patch_manual_confirmed_rows"] = (
            ichiban_kuji_prize_name_image_patch_candidates_summary.get("manual_confirmed_rows", 0)
        )
        open_review_queues["ichiban_prize_name_image_patch_blocked_rows"] = (
            ichiban_kuji_prize_name_image_patch_candidates_summary.get("blocked_rows", 0)
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "summary": {
            "catalog_rows": rows,
            "coverage": cov,
            "missing": {
                "source_url": missing.get("source_url", 0),
                "image_url": missing.get("image_url", 0),
                "release_date": missing.get("release_date", 0),
                "official_price_jpy": missing.get("official_price_jpy", 0),
                "barcode": missing.get("barcode", 0),
                "name_ja": missing.get("name_ja", 0),
            },
            "open_review_queues": open_review_queues,
            "top_store_priority_score": store_priority_matrix[0]["priority_score"] if store_priority_matrix else 0,
        },
        "quality_gates": quality_gates,
        "workstream_scorecard": workstream_scorecard,
        "store_priority_matrix": store_priority_matrix[:40],
        "reports": [
            {"key": "quality", "public_report": f"data/{QUALITY.name}"},
            {"key": "image_backlog", "public_report": f"data/{IMAGE_BACKLOG.name}"},
            {"key": "image_asset_audit", "public_report": f"data/{IMAGE_ASSET_AUDIT.name}"},
            {"key": "execution_plan", "public_report": f"data/{EXECUTION_PLAN.name}"},
            {"key": "generic_source_patch_candidates", "public_report": f"data/{GENERIC_SOURCE_PATCH_CANDIDATES.name}"},
            {"key": "requested_focus_enrichment", "public_report": f"data/{REQUESTED_FOCUS.name}"},
            {"key": "requested_focus_review_batches", "public_report": f"data/{REQUESTED_FOCUS_REVIEW_BATCHES.name}"},
            {"key": "danganronpa_missing_media", "public_report": f"data/{DANGANRONPA_MISSING_MEDIA.name}"},
            {"key": "danganronpa_patch_template_dry_run", "public_report": f"data/{DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.name}"},
            {"key": "danganronpa_goodsmile_probe", "public_report": f"data/{DANGANRONPA_GOODSMILE_PROBE.name}"},
            {"key": "danganronpa_prize_probe", "public_report": f"data/{DANGANRONPA_PRIZE_PROBE.name}"},
            {"key": "danganronpa_source_detail_probe", "public_report": f"data/{DANGANRONPA_SOURCE_DETAIL_PROBE.name}"},
            {"key": "image_enrichment_batches", "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}"},
            {"key": "source_discovery", "public_report": f"data/{SOURCE_DISCOVERY.name}"},
            {"key": "source_discovery_review_batches", "public_report": f"data/{SOURCE_DISCOVERY_REVIEW_BATCHES.name}"},
            {"key": "source_discovery_focus_template", "public_report": f"data/{SOURCE_DISCOVERY_FOCUS_TEMPLATE.name}"},
            {"key": "source_discovery_starter_queue", "public_report": f"data/{SOURCE_DISCOVERY_STARTER_QUEUE.name}"},
            {"key": "source_discovery_next_focus_pack", "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK.name}"},
            {"key": "source_discovery_next_focus_detail_candidates", "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.name}"},
            {"key": "source_discovery_next_focus_fallback_queue", "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.name}"},
            {"key": "ensky_cache_candidate_action_queue", "public_report": f"data/{ENSKY_CACHE_CANDIDATE_ACTION_QUEUE.name}"},
            {"key": "source_detail_candidate_action_queue", "public_report": f"data/{SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.name}"},
            {"key": "official_detail_review_batches", "public_report": f"data/{OFFICIAL_DETAIL_REVIEW_BATCHES.name}"},
            {"key": "metadata_backlog", "public_report": f"data/{METADATA_BACKLOG.name}"},
            {"key": "metadata_review_batches", "public_report": f"data/{METADATA_REVIEW_BATCHES.name}"},
            {"key": "metadata_action_queue", "public_report": f"data/{METADATA_ACTION_QUEUE.name}"},
            {"key": "confirmed_import_readiness", "public_report": f"data/{CONFIRMED_IMPORT_READINESS.name}"},
            {"key": "deduplication", "public_report": f"data/{DEDUPLICATION.name}"},
            {"key": "deduplication_review_batches", "public_report": f"data/{DEDUPLICATION_REVIEW_BATCHES.name}"},
            {"key": "deduplication_action_queue", "public_report": f"data/{DEDUPLICATION_ACTION_QUEUE.name}"},
            {"key": "animation_categories", "public_report": f"data/{ANIMATION_CATEGORIES.name}"},
            {"key": "animation_category_review_batches", "public_report": f"data/{ANIMATION_CATEGORY_REVIEW_BATCHES.name}"},
            {"key": "animation_category_action_queue", "public_report": f"data/{ANIMATION_CATEGORY_ACTION_QUEUE.name}"},
            {"key": "animation_category_split_review", "public_report": f"data/{ANIMATION_CATEGORY_SPLIT_REVIEW.name}"},
            {"key": "animation_category_unmatched_keyword_review", "public_report": f"data/{ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.name}"},
            {"key": "ichiban_kuji_history", "public_report": f"data/{ICHIIBAN_KUJI_HISTORY.name}"},
            {"key": "ichiban_kuji_metadata_probe", "public_report": f"data/{ICHIIBAN_KUJI_METADATA_PROBE.name}"},
            {"key": "ichiban_kuji_metadata_review_batches", "public_report": f"data/{ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES.name}"},
            {"key": "ichiban_kuji_prize_name_image_review", "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}"},
            {"key": "ichiban_kuji_prize_name_image_patch_candidates", "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.name}"},
            {"key": "ichiban_kuji_prize_policy_audit", "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.name}"},
            {"key": "ichiban_kuji_prize_policy_issue_queue", "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.name}"},
            {"key": "agent_work_queue", "public_report": f"data/{AGENT_WORK_QUEUE.name}"},
        ],
        "next_actions": next_actions,
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "requires_manual_review_for_imports": True,
            "scheduled_refresh": "Daily at 04:20 KST via GitHub Actions plus manual workflow_dispatch.",
            "reason": "This report coordinates public queues; it does not mutate catalog data by itself.",
        },
    }


def compact_sample(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("catalog_index") or item.get("row_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "series_name": item.get("series_name"),
        "category": item.get("category"),
        "source_store": item.get("source_store"),
        "source_url": item.get("source_url"),
        "official_search_url": normalize_public_search_url(item.get("official_search_url")),
    }


def normalize_public_search_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.lower() == "stellive.fanding.kr" and parsed.path.rstrip("/") == "/search":
        return urllib.parse.urlunsplit(("https", "fanding.kr", "/@stellive/shop", parsed.query, parsed.fragment))
    return url


def build_agent_work_queue_public(
    generated_at: str,
    source_discovery: dict[str, Any],
    metadata_backlog: dict[str, Any],
    image_enrichment_batches: dict[str, Any],
    deduplication: dict[str, Any],
    animation_categories: dict[str, Any],
    ichiban_kuji_history: dict[str, Any],
    operations: dict[str, Any],
    requested_focus: dict[str, Any],
    danganronpa_missing_media: dict[str, Any],
    metadata_review_batches_override: dict[str, Any] | None = None,
    metadata_action_queue_override: dict[str, Any] | None = None,
    animation_review_batches_override: dict[str, Any] | None = None,
    animation_action_queue_override: dict[str, Any] | None = None,
    animation_split_review_override: dict[str, Any] | None = None,
    animation_unmatched_keyword_review_override: dict[str, Any] | None = None,
    source_next_focus_pack_override: dict[str, Any] | None = None,
    source_next_focus_detail_candidates_override: dict[str, Any] | None = None,
    source_next_focus_metadata_field_import_override: dict[str, Any] | None = None,
    source_next_focus_fallback_queue_override: dict[str, Any] | None = None,
    source_discovery_starter_queue_override: dict[str, Any] | None = None,
    requested_focus_action_queue_override: dict[str, Any] | None = None,
    image_attachment_action_queue_override: dict[str, Any] | None = None,
    deduplication_action_queue_override: dict[str, Any] | None = None,
    ichiban_prize_policy_issue_queue_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    batches: list[dict[str, Any]] = []
    generic_source_report = load_json(GENERIC_SOURCE, {}) if GENERIC_SOURCE.exists() else {}
    gotouchi_report = load_json(GOTOUCHI, {}) if GOTOUCHI.exists() else {}
    source_review_batches = (
        load_json(SOURCE_DISCOVERY_REVIEW_BATCHES, {}) if SOURCE_DISCOVERY_REVIEW_BATCHES.exists() else {}
    )
    source_action_queue = (
        load_json(SOURCE_DISCOVERY_ACTION_QUEUE, {}) if SOURCE_DISCOVERY_ACTION_QUEUE.exists() else {}
    )
    source_detail_candidate_action_queue = (
        load_json(SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE, {})
        if SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.exists()
        else {}
    )
    requested_focus_review_batches = (
        load_json(REQUESTED_FOCUS_REVIEW_BATCHES, {}) if REQUESTED_FOCUS_REVIEW_BATCHES.exists() else {}
    )
    requested_focus_action_queue = (
        requested_focus_action_queue_override
        if requested_focus_action_queue_override is not None
        else load_json(REQUESTED_FOCUS_ACTION_QUEUE, {}) if REQUESTED_FOCUS_ACTION_QUEUE.exists() else {}
    )
    image_action_queue = (
        image_attachment_action_queue_override
        if image_attachment_action_queue_override is not None
        else load_json(IMAGE_ATTACHMENT_ACTION_QUEUE, {}) if IMAGE_ATTACHMENT_ACTION_QUEUE.exists() else {}
    )
    source_next_focus_pack = (
        source_next_focus_pack_override
        if source_next_focus_pack_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_PACK.exists()
        else {}
    )
    source_next_focus_detail_candidates = (
        source_next_focus_detail_candidates_override
        if source_next_focus_detail_candidates_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.exists()
        else {}
    )
    source_next_focus_metadata_field_import = (
        source_next_focus_metadata_field_import_override
        if source_next_focus_metadata_field_import_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT.exists()
        else {}
    )
    source_next_focus_fallback_queue = (
        source_next_focus_fallback_queue_override
        if source_next_focus_fallback_queue_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.exists()
        else {}
    )
    source_discovery_starter_queue = (
        source_discovery_starter_queue_override
        if source_discovery_starter_queue_override is not None
        else load_json(SOURCE_DISCOVERY_STARTER_QUEUE, {})
        if SOURCE_DISCOVERY_STARTER_QUEUE.exists()
        else {}
    )
    dedupe_action_queue = (
        deduplication_action_queue_override
        if deduplication_action_queue_override is not None
        else load_json(DEDUPLICATION_ACTION_QUEUE, {})
        if DEDUPLICATION_ACTION_QUEUE.exists()
        else {}
    )
    ichiban_reissue_decision_template = (
        load_json(ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE, {})
        if ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE.exists()
        else {}
    )
    metadata_review_batches = (
        metadata_review_batches_override
        if metadata_review_batches_override is not None
        else load_json(METADATA_REVIEW_BATCHES, {}) if METADATA_REVIEW_BATCHES.exists() else {}
    )
    metadata_action_queue = (
        metadata_action_queue_override
        if metadata_action_queue_override is not None
        else load_json(METADATA_ACTION_QUEUE, {}) if METADATA_ACTION_QUEUE.exists() else {}
    )
    confirmed_import_readiness = (
        load_json(CONFIRMED_IMPORT_READINESS, {}) if CONFIRMED_IMPORT_READINESS.exists() else {}
    )
    ichiban_metadata_review_batches = (
        load_json(ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES, {})
        if ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES.exists()
        else {}
    )
    ichiban_metadata_action_queue = (
        load_json(ICHIIBAN_KUJI_METADATA_ACTION_QUEUE, {})
        if ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.exists()
        else {}
    )
    ichiban_metadata_fast_review = (
        build_ichiban_kuji_metadata_fast_review_public.build_report(
            ichiban_metadata_action_queue,
            generated_at=generated_at,
        )
        if ichiban_metadata_action_queue
        else {}
    )
    ichiban_prize_policy_audit = (
        load_json(ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT, {})
        if ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.exists()
        else {}
    )
    ichiban_prize_policy_issue_queue = (
        ichiban_prize_policy_issue_queue_override
        if ichiban_prize_policy_issue_queue_override is not None
        else load_json(ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE, {})
        if ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.exists()
        else {}
    )
    ichiban_prize_name_image_review = (
        load_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW, {})
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.exists()
        else {}
    )
    ichiban_prize_name_image_patch_candidates = (
        load_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES, {})
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.exists()
        else {}
    )
    animation_review_batches = (
        animation_review_batches_override
        if animation_review_batches_override is not None
        else load_json(ANIMATION_CATEGORY_REVIEW_BATCHES, {}) if ANIMATION_CATEGORY_REVIEW_BATCHES.exists() else {}
    )
    animation_action_queue = (
        animation_action_queue_override
        if animation_action_queue_override is not None
        else load_json(ANIMATION_CATEGORY_ACTION_QUEUE, {}) if ANIMATION_CATEGORY_ACTION_QUEUE.exists() else {}
    )
    animation_action_queue_summary = animation_action_queue.get("summary", {})
    animation_split_review = (
        animation_split_review_override
        if animation_split_review_override is not None
        else load_json(ANIMATION_CATEGORY_SPLIT_REVIEW, {}) if ANIMATION_CATEGORY_SPLIT_REVIEW.exists() else {}
    )
    animation_unmatched_keyword_review = (
        animation_unmatched_keyword_review_override
        if animation_unmatched_keyword_review_override is not None
        else load_json(ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW, {})
        if ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.exists()
        else {}
    )

    def generic_source_review_summary(source_store: str) -> dict[str, int]:
        items = [
            item
            for item in generic_source_report.get("items", [])
            if isinstance(item, dict) and str(item.get("source_store") or "") == source_store
        ]
        candidate_statuses = Counter(str(item.get("candidate_status") or "no_candidate_report") for item in items)
        return {
            "review_rows": len(items),
            "candidate_rows": sum(1 for item in items if item.get("candidate_source_url")),
            "manual_confirmed_rows": sum(1 for item in items if item.get("manual_confirmed") is True),
            "weak_or_low_confidence_rows": sum(
                1
                for item in items
                if item.get("candidate_status") in {"weak_manual_review_candidate", "low_confidence_candidate"}
            ),
            "no_candidate_rows": candidate_statuses.get("no_candidate_report", 0),
        }

    def gotouchi_review_summary() -> dict[str, int]:
        summary = gotouchi_report.get("summary", {}) if isinstance(gotouchi_report, dict) else {}
        keys = (
            "rows_checked",
            "exact_type_candidate_rows",
            "motif_only_type_mismatch_rows",
            "no_official_candidate_rows",
            "attached_representative_rows",
            "visual_mismatch_rows",
        )
        return {key: int(summary.get(key) or 0) for key in keys}

    def review_state_for_batch(workstream: str, review_summary: dict[str, int] | None = None) -> str:
        if workstream == "generic_source_url_cleanup":
            if review_summary and review_summary.get("manual_confirmed_rows", 0) > 0:
                return "manual_confirmed_candidates_ready"
            if review_summary and review_summary.get("candidate_rows", 0) > 0:
                return "candidate_review_required"
            return "exact_source_discovery_required"
        if workstream == "gotouchi_official_candidate_review":
            if review_summary and review_summary.get("exact_type_candidate_rows", 0) > 0:
                return "official_exact_candidate_review_required"
            return "official_candidate_mismatch_review_required"
        if workstream in {
            "image_url_attachment",
            "image_attachment_source_url_next_review_batch",
        }:
            return "source_discovery_then_image_attachment"
        if workstream == "image_attachment_action_queue":
            return "image_evidence_confirmation_required"
        if workstream == "source_discovery_action_queue":
            return "source_evidence_confirmation_required"
        if workstream == "source_detail_candidate_action_queue":
            return "candidate_review_required"
        if workstream == "source_discovery_starter_queue":
            return "exact_source_discovery_required"
        if workstream == "source_discovery_next_focus_fallback_queue":
            return "exact_source_discovery_required"
        if workstream == "source_url_discovery":
            return "exact_source_discovery_required"
        if workstream == "metadata_backlog":
            return "metadata_evidence_required"
        if workstream == "metadata_action_queue":
            return "manual_metadata_evidence_confirmation_required"
        if workstream == "confirmed_import_readiness":
            return "manual_review_required"
        if workstream == "danganronpa_missing_media":
            return "source_and_image_evidence_required"
        if workstream == "deduplication_action_queue":
            return "manual_dedupe_action_confirmation_required"
        if workstream == "deduplication_review":
            return "manual_dedupe_review_required"
        if workstream.startswith("ichiban_kuji"):
            if workstream == "ichiban_kuji_metadata_action_queue":
                return "manual_official_campaign_metadata_confirmation_required"
            if workstream == "ichiban_kuji_prize_policy_audit":
                return "manual_official_prize_variant_confirmation_required"
            if workstream == "ichiban_kuji_prize_name_image_review":
                return "manual_prize_name_structure_confirmation_required"
            if workstream == "ichiban_kuji_prize_name_image_patch_candidates":
                return "manual_prize_image_patch_confirmation_required"
            return "official_campaign_evidence_required"
        if workstream == "animation_category_review":
            return "taxonomy_mapping_required"
        if workstream == "animation_category_action_queue":
            return "manual_category_mapping_confirmation_required"
        if workstream == "animation_category_split_review":
            return "manual_name_level_split_confirmation_required"
        if workstream == "animation_category_unmatched_keyword_review":
            return "manual_keyword_candidate_review_required"
        return "manual_review_required"

    def next_machine_step_for_state(review_state: str) -> str:
        return {
            "manual_confirmed_candidates_ready": "prepare_reviewed_catalog_patch",
            "candidate_review_required": "open_candidate_report_and_verify_exact_product_identity",
            "exact_source_discovery_required": "find_exact_official_product_source_url",
            "official_exact_candidate_review_required": "verify_official_candidate_image_matches_row_type",
            "official_candidate_mismatch_review_required": "review_official_candidates_before_import",
            "source_discovery_then_image_attachment": "find_source_url_before_image_import",
            "image_evidence_confirmation_required": "confirm_source_then_fill_image_url_templates",
            "source_and_image_evidence_required": "confirm_exact_source_then_fill_image_url_templates",
            "source_evidence_confirmation_required": "confirm_exact_source_url_then_fill_source_templates",
            "metadata_evidence_required": "collect_official_metadata_evidence",
            "manual_metadata_evidence_confirmation_required": "fill_confirmed_metadata_patch_templates",
            "manual_dedupe_action_confirmation_required": "confirm_manual_keep_drop_dedupe_decisions",
            "manual_dedupe_review_required": "compare_duplicate_group_evidence",
            "official_campaign_evidence_required": "verify_ichiban_campaign_page",
            "manual_official_campaign_metadata_confirmation_required": "fill_confirmed_ichiban_campaign_patch_templates",
            "manual_official_prize_variant_confirmation_required": "verify_ichiban_prize_variants_against_campaign_lineup",
            "manual_prize_name_structure_confirmation_required": "confirm_ichiban_prize_name_structure_templates",
            "manual_prize_image_patch_confirmation_required": "confirm_ichiban_prize_image_patch_templates",
            "taxonomy_mapping_required": "map_category_to_folder_color_and_icon",
            "manual_category_mapping_confirmation_required": "fill_confirmed_animation_category_mapping_templates",
            "manual_name_level_split_confirmation_required": "confirm_animation_category_name_split_templates",
            "manual_keyword_candidate_review_required": "review_unmatched_animation_keyword_candidates",
        }.get(review_state, "manual_review")

    def add_batch(
        *,
        agent_id: str,
        workstream: str,
        priority: int,
        title: str,
        public_report: Path,
        rows: int,
        recommended_action: str,
        acceptance_criteria: list[str],
        samples: list[dict[str, Any]],
        sample_limit: int = 8,
        review_summary: dict[str, Any] | None = None,
    ) -> None:
        if rows <= 0:
            return
        batch = {
            "batch_id": f"{priority:03d}-{agent_id}-{len(batches) + 1:02d}",
            "agent_id": agent_id,
            "workstream": workstream,
            "priority": priority,
            "title": title,
            "public_report": f"data/{public_report.name}",
            "rows": rows,
            "recommended_action": recommended_action,
            "acceptance_criteria": acceptance_criteria,
            "sample_items": samples[:sample_limit],
        }
        if review_summary is not None:
            batch["review_summary"] = review_summary
        review_state = review_state_for_batch(workstream, review_summary)
        batch["review_state"] = review_state
        batch["next_machine_step"] = next_machine_step_for_state(review_state)
        batches.append(batch)

    def source_detail_candidate_agent_sample(item: dict[str, Any]) -> dict[str, Any]:
        sample = dict(item)
        if (
            item.get("recommended_action")
            == "recheck_candidate_identity_before_source_or_image_patch"
        ):
            candidate_source_url = sample.pop("candidate_source_url", None)
            candidate_image_url = sample.pop("candidate_image_url", None)
            sample.pop("source_patch_template", None)
            sample.pop("image_patch_template", None)
            if candidate_source_url:
                sample["rejected_candidate_source_url"] = candidate_source_url
            if candidate_image_url:
                sample["rejected_candidate_image_url"] = candidate_image_url
            sample["candidate_status"] = "recheck_required_not_actionable"
            sample["blocked_until"] = "candidate_identity_rechecked_or_replaced"
            sample["safe_source_image_pair"] = False
        return sample

    danganronpa_items = danganronpa_missing_media.get("items", [])
    danganronpa_by_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in danganronpa_items:
        if isinstance(item, dict):
            danganronpa_by_store[str(item.get("source_store") or "unknown")].append(item)
    for store, store_items in sorted(danganronpa_by_store.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        add_batch(
            agent_id="agent-danganronpa-media",
            workstream="danganronpa_missing_media",
            priority=12,
            title=f"단간론파 {store} 소스/이미지 보강",
            public_report=DANGANRONPA_MISSING_MEDIA,
            rows=len(store_items),
            recommended_action="verify exact official or licensed source pages before preparing image/source patch",
            acceptance_criteria=[
                "Every accepted candidate must match the exact product or product-line identity.",
                "source_url and image_url must come from allowed_source_domains or an explicitly reviewed trusted source.",
                "No marketplace or resale image may be imported through this queue.",
            ],
            samples=store_items[:8],
        )

    for topic in requested_focus.get("topics", []):
        open_rows = int(topic.get("open_rows") or 0)
        if open_rows <= 0:
            continue
        add_batch(
            agent_id="agent-requested-focus",
            workstream="requested_focus_enrichment",
            priority=int(topic.get("priority") or 10),
            title=f"요청 우선 보강: {topic.get('label')}",
            public_report=REQUESTED_FOCUS,
            rows=open_rows,
            recommended_action=str(topic.get("next_step") or "review requested focus topic"),
            acceptance_criteria=[
                "Confirm each update against exact official or trusted source evidence.",
                "Do not import private collection or device-only ownership data.",
                "Prepare catalog patches only for reviewed rows; auto-apply remains disabled.",
            ],
            samples=topic.get("sample_items", []),
        )

    requested_focus_batch_rows = [
        batch for batch in requested_focus_review_batches.get("batches", []) if isinstance(batch, dict)
    ]
    if requested_focus_batch_rows:
        for focus_batch in requested_focus_batch_rows[:16]:
            add_batch(
                agent_id="agent-requested-focus-detail",
                workstream="requested_focus_review_batches",
                priority=int(focus_batch.get("priority") or 99),
                title=f"{focus_batch.get('topic_label')} {focus_batch.get('missing_field')} review",
                public_report=REQUESTED_FOCUS_REVIEW_BATCHES,
                rows=int(focus_batch.get("row_count") or 0),
                recommended_action=str(focus_batch.get("recommended_action") or "review requested focus batch"),
                acceptance_criteria=[
                    "Verify each candidate against exact official or trusted source evidence.",
                    "Keep private collection ownership data on the local device only.",
                    "Prepare reviewed catalog patches only; auto-apply remains disabled.",
                ],
                samples=[item for item in focus_batch.get("items", []) if isinstance(item, dict)],
            )

    requested_focus_action_batches = [
        batch for batch in requested_focus_action_queue.get("batches", []) if isinstance(batch, dict)
    ]
    if requested_focus_action_batches:
        for action_batch in requested_focus_action_batches[:12]:
            add_batch(
                agent_id="agent-requested-focus-action",
                workstream="requested_focus_action_queue",
                priority=int(action_batch.get("priority") or 99),
                title=f"{action_batch.get('topic_id')} {action_batch.get('missing_field')} actionable review",
                public_report=REQUESTED_FOCUS_ACTION_QUEUE,
                rows=int(action_batch.get("row_count") or 0),
                recommended_action=str(action_batch.get("recommended_action") or "review requested focus action batch"),
                acceptance_criteria=[
                    "Review non-barcode fields before long barcode research.",
                    "Confirm every source, image, date, price, or Japanese name against exact evidence.",
                    "Prepare reviewed catalog patches only; auto-apply remains disabled.",
                ],
                samples=[item for item in action_batch.get("items", []) if isinstance(item, dict)],
                review_summary={
                    "action_batch_rows": int(action_batch.get("row_count") or 0),
                    "missing_field": action_batch.get("missing_field"),
                    "blocked_reason": action_batch.get("blocked_reason"),
                    "first_primary_review_url": action_batch.get("first_primary_review_url"),
                    "first_primary_review_url_kind": action_batch.get("first_primary_review_url_kind"),
                },
            )

    image_action_batches = [batch for batch in image_action_queue.get("batches", []) if isinstance(batch, dict)]
    image_next_source_url_batch = [
        row
        for row in image_action_queue.get("next_source_url_review_batch", [])
        if isinstance(row, dict)
    ]
    image_next_representative_batch = [
        row
        for row in image_action_queue.get("next_representative_image_review_batch", [])
        if isinstance(row, dict)
    ]
    image_action_summary = image_action_queue.get("summary", {})
    if image_next_source_url_batch:
        add_batch(
            agent_id="agent-image-action",
            workstream="image_attachment_source_url_next_review_batch",
            priority=18,
            title="Next image source-url replacement review batch",
            public_report=IMAGE_ATTACHMENT_ACTION_QUEUE,
            rows=len(image_next_source_url_batch),
            recommended_action=(
                "Open each primary_review_url and replace generic storefront URLs with exact "
                "product/detail source URLs before image import."
            ),
            acceptance_criteria=[
                "Accepted source_url must be an exact product or product-detail page.",
                "Do not attach image_url until the exact product page image is visible.",
                "Use source_search_url before fallback web search when present.",
                "Keep auto-apply disabled; prepare reviewed source_url template rows only.",
            ],
            samples=image_next_source_url_batch,
            sample_limit=10,
            review_summary={
                "next_source_url_review_batch_rows": len(image_next_source_url_batch),
                "next_source_url_review_batch_store_count": int(
                    image_action_summary.get("next_source_url_review_batch_store_count") or 0
                ),
                "next_source_url_review_batch_primary_review_url_rows": int(
                    image_action_summary.get(
                        "next_source_url_review_batch_primary_review_url_rows"
                    )
                    or 0
                ),
                "next_source_url_review_batch_primary_review_url_kind_counts": (
                    image_action_summary.get(
                        "next_source_url_review_batch_primary_review_url_kind_counts",
                        [],
                    )
                ),
            },
        )
    if image_next_representative_batch:
        add_batch(
            agent_id="agent-image-action",
            workstream="image_attachment_action_queue",
            priority=19,
            title="대표 이미지 후보 다음 10개 검수",
            public_report=IMAGE_ATTACHMENT_ACTION_QUEUE,
            rows=len(image_next_representative_batch),
            recommended_action=(
                "Open each primary_review_url, confirm the representative image matches "
                "product type and variant, then fill manual_image_url and evidence_url."
            ),
            acceptance_criteria=[
                "Confirm character, regional motif, product type, and variant before import.",
                "Use representative images only when the exact variant cannot be separated safely.",
                "Every accepted row keeps a suggested_local_image_path for later local download.",
                "Prepare reviewed image templates only; auto-apply remains disabled.",
            ],
            samples=image_next_representative_batch,
            sample_limit=10,
            review_summary={
                "next_representative_image_review_batch_rows": len(
                    image_next_representative_batch
                ),
                "next_representative_image_review_batch_primary_review_url_rows": int(
                    image_action_summary.get(
                        "next_representative_image_review_batch_primary_review_url_rows"
                    )
                    or 0
                ),
                "next_representative_image_review_batch_local_path_rows": int(
                    image_action_summary.get(
                        "next_representative_image_review_batch_local_path_rows"
                    )
                    or 0
                ),
                "next_representative_image_review_batch_primary_review_url_kind_counts": (
                    image_action_summary.get(
                        "next_representative_image_review_batch_primary_review_url_kind_counts",
                        [],
                    )
                ),
            },
        )
    if image_action_batches:
        for action_batch in image_action_batches[:10]:
            add_batch(
                agent_id="agent-image-action",
                workstream="image_attachment_action_queue",
                priority=int(action_batch.get("priority") or 99),
                title=f"{action_batch.get('source_store')} image attachment action",
                public_report=IMAGE_ATTACHMENT_ACTION_QUEUE,
                rows=int(action_batch.get("row_count") or 0),
                recommended_action=str(action_batch.get("recommended_action") or "review image action batch"),
                acceptance_criteria=[
                    "Confirm exact product identity before filling image_url.",
                    "For generic storefront rows, fill source_url_import_template before image_url.",
                    "Use official or trusted product image evidence, not resale or generic listing images.",
                    "Prepare reviewed image templates only; auto-apply remains disabled.",
                ],
                samples=[item for item in action_batch.get("items", []) if isinstance(item, dict)],
                review_summary={
                    "action_batch_rows": int(action_batch.get("row_count") or 0),
                    "primary_review_url_rows": int(
                        action_batch.get("primary_review_url_rows") or 0
                    ),
                    "first_primary_review_url": action_batch.get("first_primary_review_url"),
                    "first_primary_review_url_kind": action_batch.get(
                        "first_primary_review_url_kind"
                    ),
                    "review_lane_counts": action_batch.get("review_lane_counts", []),
                    "image_import_blocker_counts": action_batch.get(
                        "image_import_blocker_counts", []
                    ),
                    "suggested_local_image_path_rows": int(
                        action_batch.get("suggested_local_image_path_rows") or 0
                    ),
                    "local_image_download_instruction_ready_rows": int(
                        action_batch.get("local_image_download_instruction_ready_rows") or 0
                    ),
                    "blocked_before_image_import_rows": int(
                        (action_batch.get("attachment_readiness") or {}).get(
                            "blocked_before_image_import_rows"
                        )
                        or 0
                    ),
                    "can_import_image_urls_now_rows": int(
                        (action_batch.get("attachment_readiness") or {}).get(
                            "can_import_image_urls_now_rows"
                        )
                        or 0
                    ),
                    "attachment_readiness": action_batch.get("attachment_readiness") or {},
                    "workflow": action_batch.get("workflow"),
                    "source_store": action_batch.get("source_store"),
                },
            )

    focus_progress_rows = [
        row for row in source_next_focus_pack.get("focus_pack_progress_queue", []) if isinstance(row, dict)
    ]
    if focus_progress_rows:
        add_batch(
            agent_id="agent-source-focus-pack",
            workstream="source_discovery_next_focus_pack",
            priority=20,
            title="현재 출처 탐색 포커스팩 진행",
            public_report=SOURCE_DISCOVERY_NEXT_FOCUS_PACK,
            rows=sum(int(row.get("remaining_review_rows") or 0) for row in focus_progress_rows),
            recommended_action="Start with the current focus pack and confirm exact source URLs before image import.",
            acceptance_criteria=[
                "Each accepted source_url must be an exact product/detail page.",
                "Search or category pages stay blocked until replaced by exact product URLs.",
                "Only source evidence is confirmed here; image_url import waits for source confirmation.",
            ],
            samples=focus_progress_rows[:8],
            review_summary={
                "focus_pack_progress_queue_count": len(focus_progress_rows),
                "focus_pack_progress_remaining_rows": sum(
                    int(row.get("remaining_review_rows") or 0) for row in focus_progress_rows
                ),
            },
        )

    fallback_summary = source_next_focus_fallback_queue.get("summary", {})
    fallback_review_rows = [
        row for row in source_next_focus_fallback_queue.get("review_table", []) if isinstance(row, dict)
    ]
    fallback_source_ready_rows = [
        row
        for row in fallback_review_rows
        if row.get("identity_review_status") == "exact_page_match_review_ready"
        and row.get("primary_review_url")
    ]
    if fallback_source_ready_rows:
        add_batch(
            agent_id="agent-source-fallback",
            workstream="source_discovery_next_focus_fallback_queue",
            priority=19,
            title="포커스팩 exact source 후보 15개 확인",
            public_report=SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE,
            rows=len(fallback_source_ready_rows),
            recommended_action=(
                "Open domain-limited primary_review_url values first, then confirm exact product detail source URLs."
            ),
            acceptance_criteria=[
                "Accepted manual_confirmed_source_url must be an exact product/detail page, not a search page.",
                "Product title, image, character, and variant must match the catalog row.",
                "manual_confirmed_image_url is optional and only allowed after the exact page image is verified.",
                "Keep auto-apply disabled and run the dry-run importer before any write import.",
            ],
            samples=fallback_source_ready_rows,
            review_summary={
                "source_confirmation_ready_rows": len(fallback_source_ready_rows),
                "queue_rows": int(fallback_summary.get("queue_rows") or len(fallback_review_rows)),
                "manual_entry_template_rows": int(
                    fallback_summary.get("manual_entry_template_rows") or 0
                ),
                "first_primary_review_url": fallback_summary.get("first_primary_review_url"),
                "first_primary_review_url_kind": fallback_summary.get("first_primary_review_url_kind"),
                "dry_run_command": (
                    source_next_focus_fallback_queue.get("manual_entry_template", {}).get(
                        "dry_run_command"
                    )
                ),
            },
        )
    if fallback_review_rows:
        add_batch(
            agent_id="agent-source-fallback",
            workstream="source_discovery_next_focus_fallback_queue",
            priority=20,
            title="현재 포커스팩 fallback 소스 확인",
            public_report=SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE,
            rows=int(fallback_summary.get("queue_rows") or len(fallback_review_rows)),
            recommended_action=(
                "Open primary_review_url values and fill manual_confirmed_source_url only for exact product pages."
            ),
            acceptance_criteria=[
                "primary_review_url is only a review starting point; accepted source_url must be an exact product/detail page.",
                "Rows with variant or metadata blockers stay blocked until identity is disambiguated.",
                "Keep auto-apply disabled and prepare manual confirmed source templates only.",
            ],
            samples=fallback_review_rows[:8],
            review_summary={
                "queue_rows": int(fallback_summary.get("queue_rows") or len(fallback_review_rows)),
                "review_table_rows": int(fallback_summary.get("review_table_rows") or len(fallback_review_rows)),
                "source_confirmation_ready_rows": int(
                    fallback_summary.get("source_confirmation_ready_rows") or 0
                ),
                "metadata_backfill_required_rows": int(
                    fallback_summary.get("metadata_backfill_required_rows") or 0
                ),
                "variant_disambiguation_required_rows": int(
                    fallback_summary.get("variant_disambiguation_required_rows") or 0
                ),
                "first_primary_review_url": fallback_summary.get("first_primary_review_url"),
                "first_primary_review_url_kind": fallback_summary.get("first_primary_review_url_kind"),
                "first_domain_limited_web_search_url": fallback_summary.get(
                    "first_domain_limited_web_search_url"
                ),
                "work_order_lanes": fallback_summary.get("work_order_lanes", []),
            },
        )

    source_detail_summary = source_next_focus_detail_candidates.get("summary", {})
    metadata_field_import_summary = source_next_focus_metadata_field_import.get("summary", {})
    metadata_enrichment_rows = [
        row
        for row in source_next_focus_detail_candidates.get("metadata_enrichment_template", [])
        if isinstance(row, dict)
    ]
    metadata_field_import_rows = [
        row
        for row in source_next_focus_detail_candidates.get("metadata_field_import_template", [])
        if isinstance(row, dict)
    ]
    if metadata_enrichment_rows:
        add_batch(
            agent_id="agent-source-detail-candidate",
            workstream="source_discovery_next_focus_detail_candidates",
            priority=20,
            title="현재 source focus pack variant 메타데이터 보강",
            public_report=SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES,
            rows=len(metadata_enrichment_rows),
            recommended_action=(
                "Confirm exact character, variant, sub_series, and source/image identity before any source_url or image_url import."
            ),
            acceptance_criteria=[
                "Do not attach candidate images to broad catalog rows until the exact variant is identified.",
                "Fill suggested_name_ja, suggested_sub_series, and suggested_character_name only from official product evidence.",
                "Use candidate_options as review evidence; auto-apply remains disabled.",
            ],
            samples=metadata_enrichment_rows[:8],
            review_summary={
                "focus_pack_id": source_detail_summary.get("focus_pack_id"),
                "metadata_enrichment_template_rows": len(metadata_enrichment_rows),
                "metadata_field_import_template_rows": len(metadata_field_import_rows),
                "metadata_field_import_supported_rows": sum(
                    1 for row in metadata_field_import_rows if row.get("import_supported") is True
                ),
                "metadata_field_import_dry_run_updated_rows": int(
                    metadata_field_import_summary.get("updated_rows") or 0
                ),
                "metadata_field_import_dry_run_skipped_rows": int(
                    metadata_field_import_summary.get("skipped_rows") or 0
                ),
                "metadata_field_import_dry_run_skip_reason_counts": metadata_field_import_summary.get(
                    "skip_reason_counts", []
                ),
                "variant_detail_required_rows": int(
                    source_detail_summary.get("variant_detail_required_rows") or 0
                ),
                "candidate_rows": int(source_detail_summary.get("candidate_rows") or 0),
                "next_action_lanes": source_detail_summary.get("next_action_lanes", []),
            },
        )

    readiness_workflows = [
        row for row in confirmed_import_readiness.get("workflows", []) if isinstance(row, dict)
    ]
    pending_or_blocked = [
        row
        for row in readiness_workflows
        if int(row.get("manual_confirmed_true") or 0) > 0
        or int(row.get("template_items") or 0) > 0
        or int(row.get("public_action_rows") or 0) > 0
    ]
    if pending_or_blocked:
        add_batch(
            agent_id="agent-confirmed-import",
            workstream="confirmed_import_readiness",
            priority=19,
            title="Confirmed import readiness review",
            public_report=CONFIRMED_IMPORT_READINESS,
            rows=sum(
                int(row.get("manual_confirmed_true") or 0)
                + int(row.get("template_items") or 0)
                + int(row.get("public_action_rows") or 0)
                for row in pending_or_blocked
            ),
            recommended_action="Review pending/blocked confirmed imports before any catalog write.",
            acceptance_criteria=[
                "Do not expose row-level private candidate details in public reports.",
                "Run guarded dry-runs before writing confirmed source, image, or metadata rows.",
                "Only manually confirmed exact matches may be imported.",
            ],
            samples=pending_or_blocked,
        )

    for group in image_enrichment_batches.get("groups", [])[:12]:
        workflow = str(group.get("workflow") or "")
        if workflow == "extract_from_existing_source_url":
            agent_id = "agent-image-existing-source"
            workstream = "image_url_attachment"
            batch_report = IMAGE_ENRICHMENT_BATCHES
        elif workflow == "replace_generic_source_then_extract_image":
            agent_id = "agent-generic-source-cleanup"
            workstream = "generic_source_url_cleanup"
            batch_report = GENERIC_SOURCE if GENERIC_SOURCE.exists() else IMAGE_ENRICHMENT_BATCHES
        elif workflow == "review_gotouchi_official_candidates":
            agent_id = "agent-gotouchi-review"
            workstream = "gotouchi_official_candidate_review"
            batch_report = GOTOUCHI if GOTOUCHI.exists() else IMAGE_ENRICHMENT_BATCHES
        else:
            agent_id = "agent-source-image"
            workstream = "image_url_attachment"
            batch_report = IMAGE_ENRICHMENT_BATCHES
        add_batch(
            agent_id=agent_id,
            workstream=workstream,
            priority=int(group.get("priority") or 99),
            title=f"{group.get('source_store')} 이미지 보강 ({workflow})",
            public_report=batch_report,
            rows=int(group.get("missing_image_rows") or 0),
            recommended_action=str(group.get("recommended_action") or "review image candidates"),
            acceptance_criteria=[
                "Exact product identity is verified before importing image_url.",
                "Rows without source_url must receive an exact source_url before image_url is accepted.",
                "No marketplace or unrelated stock image is imported without matching product evidence.",
            ],
            samples=[compact_sample(item) for item in group.get("sample_items", []) if isinstance(item, dict)],
            review_summary=(
                generic_source_review_summary(str(group.get("source_store") or ""))
                if workflow == "replace_generic_source_then_extract_image"
                else gotouchi_review_summary()
                if workflow == "review_gotouchi_official_candidates"
                else None
            ),
        )

    source_review_batch_rows = [batch for batch in source_review_batches.get("batches", []) if isinstance(batch, dict)]
    source_action_batches = [batch for batch in source_action_queue.get("batches", []) if isinstance(batch, dict)]
    source_detail_candidate_action_batches = [
        batch for batch in source_detail_candidate_action_queue.get("batches", []) if isinstance(batch, dict)
    ]
    for action_batch in source_action_batches[:10]:
        add_batch(
            agent_id="agent-source-action",
            workstream="source_discovery_action_queue",
            priority=18 + int(action_batch.get("priority") or 99),
            title=f"{action_batch.get('source_store')} source URL action",
            public_report=SOURCE_DISCOVERY_ACTION_QUEUE,
            rows=int(action_batch.get("row_count") or 0),
            recommended_action=str(action_batch.get("recommended_action") or "confirm exact source URL candidates"),
            acceptance_criteria=[
                "Accepted source_url must be an exact product/detail page.",
                "Search result and storefront pages remain blocked until an exact product URL is found.",
                "source_url templates are filled only after manual evidence confirmation.",
            ],
            samples=[item for item in action_batch.get("items", []) if isinstance(item, dict)],
        )
    for action_batch in source_detail_candidate_action_batches[:6]:
        add_batch(
            agent_id="agent-source-detail-candidate",
            workstream="source_detail_candidate_action_queue",
            priority=22 + int(action_batch.get("offset") or 0),
            title=f"Source detail candidate review {action_batch.get('batch_id')}",
            public_report=SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE,
            rows=int(action_batch.get("row_count") or 0),
            recommended_action=str(
                action_batch.get("recommended_action")
                or "Review candidate identity and confirm only exact source/image matches."
            ),
            acceptance_criteria=[
                "Candidate title must match the same product, character, and variant as the catalog row.",
                "Accept source_url only when the candidate page is an exact product/detail page.",
                "Accept image_url only when it comes from the accepted source page or trusted official CDN.",
                "Leave manual_confirmed false for related products, bundles, or wrong variants.",
            ],
            samples=[
                source_detail_candidate_agent_sample(item)
                for item in action_batch.get("items", [])
                if isinstance(item, dict)
            ],
        )
    if source_review_batch_rows:
        for source_batch in source_review_batch_rows[:12]:
            workflow = str(source_batch.get("workflow") or "")
            store = str(source_batch.get("source_store") or "unknown")
            add_batch(
                agent_id="agent-source-discovery",
                workstream="source_url_discovery",
                priority=20 + int(source_batch.get("priority") or DISCOVERY_PRIORITY.get(workflow, 99)),
                title=f"{store} 출처 URL 탐색: {source_batch.get('batch_id')}",
                public_report=SOURCE_DISCOVERY_REVIEW_BATCHES,
                rows=int(source_batch.get("row_count") or 0),
                recommended_action=str(
                    source_batch.get("recommended_action")
                    or "Find exact official product detail URLs and prepare source_url updates."
                ),
                acceptance_criteria=[
                    "Candidate URL is an exact official or trusted licensed product/detail page.",
                    "Product title and image/metadata match the catalog row.",
                    "Generic search/listing pages stay in review and are not imported as final source_url.",
                ],
                samples=[compact_sample(item) for item in source_batch.get("items", []) if isinstance(item, dict)],
            )
    else:
        source_items = [item for item in source_discovery.get("items", []) if isinstance(item, dict)]
        source_grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in source_items:
            source_grouped[(str(item.get("workflow") or ""), str(item.get("source_store") or "unknown"))].append(item)
        for (workflow, store), items in sorted(
            source_grouped.items(),
            key=lambda pair: (DISCOVERY_PRIORITY.get(pair[0][0], 99), -len(pair[1]), pair[0][1]),
        )[:10]:
            add_batch(
                agent_id="agent-source-discovery",
                workstream="source_url_discovery",
                priority=20 + DISCOVERY_PRIORITY.get(workflow, 99),
                title=f"{store} 출처 URL 탐색 ({workflow})",
                public_report=SOURCE_DISCOVERY,
                rows=len(items),
                recommended_action="Find exact official product detail URLs and prepare source_url updates.",
                acceptance_criteria=[
                    "Candidate URL is an exact official or trusted licensed product/detail page.",
                    "Product title and image/metadata match the catalog row.",
                    "Generic search/listing pages stay in review and are not imported as final source_url.",
                ],
                samples=[compact_sample(item) for item in items],
            )

    metadata_review_batch_rows = [batch for batch in metadata_review_batches.get("batches", []) if isinstance(batch, dict)]
    metadata_action_batches = [batch for batch in metadata_action_queue.get("batches", []) if isinstance(batch, dict)]
    for action_batch in metadata_action_batches[:8]:
        add_batch(
            agent_id="agent-metadata-action",
            workstream="metadata_action_queue",
            priority=35 + int(action_batch.get("priority") or 99),
            title=f"Metadata action {action_batch.get('batch_id')}",
            public_report=METADATA_ACTION_QUEUE,
            rows=int(action_batch.get("missing_cell_count") or 0),
            recommended_action=str(action_batch.get("recommended_action") or "fill confirmed metadata templates"),
            acceptance_criteria=[
                "Only release_date, official_price_jpy, and name_ja groups are included here.",
                "Every value requires official or trusted evidence before import.",
                "Barcode, source_url, and image_url remain in their dedicated queues.",
            ],
            samples=[
                compact_sample(item)
                for group in action_batch.get("groups", [])
                if isinstance(group, dict)
                for item in group.get("sample_items", [])
                if isinstance(item, dict)
            ],
            review_summary={
                "action_batch_groups": int(action_batch.get("group_count") or 0),
                "action_batch_missing_cells": int(action_batch.get("missing_cell_count") or 0),
                "primary_review_url_groups": int(action_batch.get("primary_review_url_groups") or 0),
                "first_primary_review_url": action_batch.get("first_primary_review_url"),
                "first_primary_review_url_kind": action_batch.get("first_primary_review_url_kind"),
                "primary_review_url_kind_counts": action_batch.get("primary_review_url_kind_counts", []),
            },
        )
    if metadata_review_batch_rows:
        for metadata_batch in metadata_review_batch_rows[:12]:
            add_batch(
                agent_id="agent-metadata",
                workstream="metadata_backlog",
                priority=40 + int(metadata_batch.get("priority") or 99),
                title=f"메타데이터 검수: {metadata_batch.get('batch_id')}",
                public_report=METADATA_REVIEW_BATCHES,
                rows=int(metadata_batch.get("missing_cell_count") or 0),
                recommended_action=str(metadata_batch.get("recommended_action") or "verify missing metadata"),
                acceptance_criteria=[
                    "Dates, prices, names, barcodes, source URLs, and images are copied only from official or trusted evidence.",
                    "Every proposed update includes catalog_index and source evidence.",
                    "Unverified inferred metadata remains in the review queue.",
                ],
                samples=[
                    compact_sample(item)
                    for group in metadata_batch.get("groups", [])
                    if isinstance(group, dict)
                    for item in group.get("sample_items", [])
                    if isinstance(item, dict)
                ],
            )
    else:
        for group in metadata_backlog.get("groups", [])[:10]:
            add_batch(
                agent_id="agent-metadata",
                workstream="metadata_backlog",
                priority=60,
                title=f"{group.get('source_store')} {group.get('field')} 누락 보강",
                public_report=METADATA_BACKLOG,
                rows=int(group.get("missing_rows") or 0),
                recommended_action=str(group.get("recommended_action") or "verify missing metadata"),
                acceptance_criteria=[
                    "Dates, prices, names, and barcodes are copied only from official or trusted evidence.",
                    "Every proposed update includes catalog_index and source evidence.",
                    "Unverified inferred metadata remains in the review queue.",
                ],
                samples=[compact_sample(item) for item in group.get("sample_items", []) if isinstance(item, dict)],
            )

    dedupe_action_batches = [batch for batch in dedupe_action_queue.get("batches", []) if isinstance(batch, dict)]
    reissue_campaign_review_batch = [
        row
        for row in ichiban_reissue_decision_template.get(
            "next_campaign_review_batch", []
        )
        if isinstance(row, dict)
    ]
    reissue_decision_summary = ichiban_reissue_decision_template.get("summary", {})
    if reissue_campaign_review_batch:
        add_batch(
            agent_id="agent-ichiban-reissue-dedupe",
            workstream="ichiban_kuji_reissue_dedupe_review",
            priority=54,
            title="Ichiban Kuji reissue campaign decisions first",
            public_report=ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE,
            rows=len(reissue_campaign_review_batch),
            recommended_action=(
                "Compare campaign page pairs first; campaign decisions can settle "
                "many same-prize item duplicate candidates safely."
            ),
            acceptance_criteria=[
                "Open every source_url in each campaign pair before judging item-level duplicates.",
                "Mark campaign waves or reissues as keep-separate before any keep/drop item work.",
                "Use same-sellable keep/drop only after the campaign context is confirmed as duplicate.",
                "Auto-merge and auto-delete remain disabled.",
            ],
            samples=reissue_campaign_review_batch,
            review_summary={
                "campaign_review_batch_rows": len(reissue_campaign_review_batch),
                "campaign_review_batch_item_work_order_rows": int(
                    reissue_decision_summary.get(
                        "campaign_review_batch_item_work_order_rows"
                    )
                    or 0
                ),
                "campaign_review_batch_catalog_index_rows": int(
                    reissue_decision_summary.get(
                        "campaign_review_batch_catalog_index_rows"
                    )
                    or 0
                ),
                "campaign_review_batch_visible_item_preview_rows": int(
                    reissue_decision_summary.get(
                        "campaign_review_batch_visible_item_preview_rows"
                    )
                    or 0
                ),
                "campaign_review_batch_truncated_campaigns": int(
                    reissue_decision_summary.get(
                        "campaign_review_batch_truncated_campaigns"
                    )
                    or 0
                ),
            },
        )
    ichiban_reissue_review_lane = [
        lane for lane in dedupe_action_queue.get("ichiban_reissue_review_lane", []) if isinstance(lane, dict)
    ]
    for lane_index, lane in enumerate(ichiban_reissue_review_lane[:8], start=1):
        add_batch(
            agent_id="agent-ichiban-reissue-dedupe",
            workstream="ichiban_kuji_reissue_dedupe_review",
            priority=55 + lane_index,
            title=f"Ichiban Kuji reissue dedupe check {lane_index:03d}",
            public_report=ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE,
            rows=int(lane.get("row_count") or 0),
            recommended_action=str(
                lane.get("review_reason")
                or "Verify campaign-specific 1kuji rows before dedupe decisions."
            ),
            acceptance_criteria=[
                "Compare every source_url campaign page before marking rows as exact duplicates.",
                "Preserve same-name rows when they belong to different releases, reruns, or campaign pages.",
                "Only record a keep/drop dedupe decision when official evidence proves the rows are the same sellable item.",
                "Auto-merge and auto-delete remain disabled.",
            ],
            samples=[
                {
                    **compact_sample(item),
                    "source_url": item.get("source_url"),
                    "campaign_url_comparison": lane.get("campaign_url_comparison"),
                }
                for item in lane.get("sample_rows", [])
                if isinstance(item, dict)
            ],
            review_summary={
                "source_url_count": int(lane.get("source_url_count") or 0),
                "first_evidence_url": next(
                    (
                        str(url).strip()
                        for url in lane.get("source_urls", [])
                        if isinstance(url, str) and url.strip()
                    ),
                    "",
                ),
                "has_reissue_signal": bool(lane.get("has_reissue_signal")),
                "reissue_signal_reasons": lane.get("reissue_signal_reasons") or [],
            },
        )
    campaign_first_review_plan = [
        row
        for row in ichiban_prize_policy_issue_queue.get("campaign_first_review_plan", [])
        if isinstance(row, dict)
    ]
    for plan_index, plan_row in enumerate(campaign_first_review_plan[:6], start=1):
        add_batch(
            agent_id="agent-ichiban-campaign-first",
            workstream="ichiban_kuji_campaign_first_reissue_review",
            priority=50 + plan_index,
            title=f"Ichiban Kuji campaign-pair review {plan_row.get('campaign_work_order_id')}",
            public_report=ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE,
            rows=int(plan_row.get("item_work_order_count") or 0),
            recommended_action=str(
                plan_row.get("recommended_action")
                or "Compare both official campaign pages before item-level keep/drop decisions."
            ),
            acceptance_criteria=[
                "Open every source_url in the campaign pair before judging item-level duplicates.",
                "If pages are separate releases, reruns, or campaign waves, keep affected rows separate.",
                "Only move to item-level keep/drop when the campaign pair is confirmed as an exact duplicate context.",
                "Auto-merge and auto-delete remain disabled.",
            ],
            samples=[
                {
                    "campaign_work_order_id": plan_row.get("campaign_work_order_id"),
                    "source_urls": plan_row.get("source_urls") or [],
                    "first_evidence_url": plan_row.get("first_evidence_url"),
                    "catalog_indexes": plan_row.get("catalog_indexes") or [],
                    "prize_labels": plan_row.get("prize_labels") or [],
                    "affected_item_work_order_ids": plan_row.get("affected_item_work_order_ids") or [],
                    "campaign_url_comparison": plan_row.get("campaign_url_comparison") or {},
                }
            ],
            review_summary={
                "campaign_work_order_id": plan_row.get("campaign_work_order_id"),
                "item_work_order_count": int(plan_row.get("item_work_order_count") or 0),
                "evidence_url_count": int(plan_row.get("evidence_url_count") or 0),
                "first_evidence_url": plan_row.get("first_evidence_url"),
                "likely_same_campaign_family_reissue": (
                    (plan_row.get("campaign_url_comparison") or {}).get(
                        "likely_same_campaign_family_reissue"
                    )
                ),
                "affected_item_work_order_ids": plan_row.get("affected_item_work_order_ids") or [],
            },
        )
    for action_batch in dedupe_action_batches[:6]:
        add_batch(
            agent_id="agent-dedupe-action",
            workstream="deduplication_action_queue",
            priority=75 + int(action_batch.get("priority") or 99),
            title=f"Safe dedupe action {action_batch.get('batch_id')}",
            public_report=DEDUPLICATION_ACTION_QUEUE,
            rows=int(action_batch.get("group_count") or 0),
            recommended_action=str(action_batch.get("recommended_action") or "record manual dedupe decisions"),
            acceptance_criteria=[
                "Only high/medium-confidence groups are included in this queue.",
                "Every accepted group still needs an explicit manual keep/drop decision.",
                "Auto-merge and auto-delete remain disabled.",
            ],
            samples=[group for group in action_batch.get("groups", []) if isinstance(group, dict)],
        )

    for group in deduplication.get("groups", [])[:10]:
        add_batch(
            agent_id="agent-dedupe",
            workstream="deduplication_review",
            priority=80 + DEDUPLICATION_KEY_PRIORITY.get(str(group.get("key_type")), 99),
            title=f"중복 후보 검토: {group.get('key_type')}",
            public_report=DEDUPLICATION,
            rows=len(group.get("rows") or []),
            recommended_action="Review keep/drop suggestions and prepare a manual-only dedupe decision.",
            acceptance_criteria=[
                "Variants, alternate prizes, and campaign-specific rows are preserved.",
                "Only evidence-backed exact duplicates are proposed for merge/delete.",
                "Auto-delete remains disabled.",
            ],
            samples=[compact_sample(item) for item in group.get("rows", []) if isinstance(item, dict)],
        )

    ichiban_review_batch_rows = [
        batch for batch in ichiban_metadata_review_batches.get("batches", []) if isinstance(batch, dict)
    ]
    ichiban_action_batches = [
        batch for batch in ichiban_metadata_action_queue.get("batches", []) if isinstance(batch, dict)
    ]
    ichiban_next_patch_batch = [
        row
        for row in ichiban_metadata_action_queue.get(
            "next_campaign_patch_review_batch", []
        )
        if isinstance(row, dict)
    ]
    ichiban_action_summary = ichiban_metadata_action_queue.get("summary", {})
    ichiban_action_work_order = [
        step for step in ichiban_metadata_action_queue.get("work_order", []) if isinstance(step, dict)
    ]
    if ichiban_next_patch_batch:
        add_batch(
            agent_id="agent-ichiban-action",
            workstream="ichiban_kuji_metadata_action_queue",
            priority=18,
            title="Ichiban Kuji metadata next campaign patch review",
            public_report=ICHIIBAN_KUJI_METADATA_ACTION_QUEUE,
            rows=len(ichiban_next_patch_batch),
            recommended_action=(
                "Open each primary_review_url, confirm labeled campaign metadata, "
                "then fill the campaign patch template fields."
            ),
            acceptance_criteria=[
                "Use the primary_review_url before any fallback evidence URL.",
                "Fill only fields listed in fields_to_confirm for each campaign.",
                "Set manual_confirmed=true only after every manual_value field is filled from labeled official evidence.",
                "Auto-apply remains disabled for historical campaign metadata.",
            ],
            samples=ichiban_next_patch_batch,
            review_summary={
                "next_campaign_patch_review_batch_rows": len(ichiban_next_patch_batch),
                "next_campaign_patch_review_batch_template_rows": int(
                    ichiban_action_summary.get(
                        "next_campaign_patch_review_batch_template_rows"
                    )
                    or 0
                ),
                "next_campaign_patch_review_batch_primary_review_url_rows": int(
                    ichiban_action_summary.get(
                        "next_campaign_patch_review_batch_primary_review_url_rows"
                    )
                    or 0
                ),
                "next_campaign_patch_review_batch_field_counts": (
                    ichiban_action_summary.get(
                        "next_campaign_patch_review_batch_field_counts", []
                    )
                ),
            },
        )
    for step in ichiban_action_work_order:
        add_batch(
            agent_id="agent-ichiban-action",
            workstream="ichiban_kuji_metadata_action_work_order",
            priority=int(step.get("rank") or 90),
            title=f"Ichiban Kuji metadata work order: {step.get('lane')}",
            public_report=ICHIIBAN_KUJI_METADATA_ACTION_QUEUE,
            rows=int(step.get("campaign_count") or 0),
            recommended_action=str(step.get("description") or "Work queued 1kuji metadata confirmations."),
            acceptance_criteria=[
                "Use only labeled official 1kuji campaign metadata or captured official evidence.",
                "Fill the manual confirmation queue before running the guarded import tool.",
                "Keep auto-apply disabled for historical campaign metadata.",
            ],
            samples=[campaign for campaign in step.get("sample_campaigns", []) if isinstance(campaign, dict)],
        )
    for action_batch in ichiban_action_batches[:6]:
        add_batch(
            agent_id="agent-ichiban-action",
            workstream="ichiban_kuji_metadata_action_queue",
            priority=18 + int(action_batch.get("priority") or 99),
            title=f"Ichiban Kuji metadata action {action_batch.get('batch_id')}",
            public_report=ICHIIBAN_KUJI_METADATA_ACTION_QUEUE,
            rows=int(action_batch.get("campaign_count") or 0),
            recommended_action=str(action_batch.get("recommended_action") or "fill confirmed 1kuji metadata templates"),
            acceptance_criteria=[
                "Use only labeled official 1kuji campaign metadata or captured official evidence.",
                "Fill release_date or official_price_jpy templates only after manual confirmation.",
                "Auto-apply remains disabled for historical campaign metadata.",
            ],
            samples=[campaign for campaign in action_batch.get("campaigns", []) if isinstance(campaign, dict)],
        )
    if ichiban_review_batch_rows:
        for review_batch in ichiban_review_batch_rows[:8]:
            workflows = {
                str(workflow)
                for workflow, _ in review_batch.get("workflow_counts", [])
                if workflow
            }
            if workflows == {"release_date_review"}:
                workstream = "ichiban_kuji_release_date"
            elif workflows == {"price_review"}:
                workstream = "ichiban_kuji_price"
            else:
                workstream = "ichiban_kuji_metadata"
            add_batch(
                agent_id="agent-ichiban-kuji",
                workstream=workstream,
                priority=100 + int(review_batch.get("priority") or 99),
                title=f"이치방쿠지 메타데이터 검수: {review_batch.get('batch_id')}",
                public_report=ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES,
                rows=int(review_batch.get("catalog_item_rows") or 0),
                recommended_action=str(
                    review_batch.get("recommended_action")
                    or "Verify official campaign metadata before applying catalog updates."
                ),
                acceptance_criteria=[
                    "Official 1kuji campaign page or captured official evidence confirms the value.",
                    "Unlabeled dates, double-chance dates, and inferred prices remain blocked.",
                    "All updated catalog rows belong to the reviewed campaign group.",
                ],
                samples=[
                    {
                        "catalog_index": index,
                        "name_ko": name,
                        "source_url": campaign.get("url"),
                    }
                    for campaign in review_batch.get("campaigns", [])
                    if isinstance(campaign, dict)
                    for index, name in zip(
                        campaign.get("sample_catalog_indexes", []), campaign.get("sample_names", [])
                    )
                ],
            )
    else:
        for group in ichiban_kuji_history.get("missing_release_date_campaigns", [])[:6]:
            add_batch(
                agent_id="agent-ichiban-kuji",
                workstream="ichiban_kuji_release_date",
                priority=110,
                title=f"이치방쿠지 발매일 확인: {group.get('slug') or group.get('title')}",
                public_report=ICHIIBAN_KUJI_HISTORY,
                rows=int(group.get("catalog_item_rows") or 0),
                recommended_action="Verify official campaign date before applying release_date to linked rows.",
                acceptance_criteria=[
                    "Official 1kuji campaign page or captured official campaign data confirms the date.",
                    "All updated catalog rows belong to the same campaign group.",
                ],
                samples=[
                    {
                        "catalog_index": index,
                        "name_ko": name,
                        "source_url": group.get("url"),
                    }
                    for index, name in zip(group.get("sample_catalog_indexes", []), group.get("sample_names", []))
                ],
            )

        for group in ichiban_kuji_history.get("missing_official_price_jpy_campaigns", [])[:8]:
            add_batch(
                agent_id="agent-ichiban-kuji",
                workstream="ichiban_kuji_price",
                priority=120,
                title=f"이치방쿠지 가격 확인: {group.get('slug') or group.get('title')}",
                public_report=ICHIIBAN_KUJI_HISTORY,
                rows=int(group.get("catalog_item_rows") or 0),
                recommended_action="Verify official campaign price before applying official_price_jpy.",
                acceptance_criteria=[
                    "Price is confirmed from official 1kuji campaign data.",
                    "Non-prize collateral and campaign rows are not assigned a price unless evidence applies.",
                ],
                samples=[
                    {
                        "catalog_index": index,
                        "name_ko": name,
                        "source_url": group.get("url"),
                    }
                    for index, name in zip(group.get("sample_catalog_indexes", []), group.get("sample_names", []))
                ],
            )

    for review_batch in [
        batch for batch in ichiban_prize_policy_audit.get("review_batches", []) if isinstance(batch, dict)
    ][:8]:
        add_batch(
            agent_id="agent-ichiban-prize-policy",
            workstream="ichiban_kuji_prize_policy_audit",
            priority=55 + int(review_batch.get("priority") or 99),
            title=f"Ichiban Kuji prize policy review {review_batch.get('batch_id')}",
            public_report=ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT,
            rows=int(review_batch.get("catalog_item_rows") or 0),
            recommended_action=str(
                review_batch.get("recommended_action")
                or "Verify same-prize variants and repeated campaign names against official 1kuji lineup pages."
            ),
            acceptance_criteria=[
                "Same prize-letter variants stay separate when the official campaign lists multiple items.",
                "Repeated names across different campaign URLs are treated as possible reissues until verified.",
                "Last One and Double Chance price exceptions remain zero-price rows.",
            ],
            samples=[group for group in review_batch.get("groups", []) if isinstance(group, dict)],
            review_summary={
                "workflow": str(review_batch.get("workflow") or ""),
                "group_count": int(review_batch.get("group_count") or 0),
                "catalog_item_rows": int(review_batch.get("catalog_item_rows") or 0),
            },
        )

    ichiban_name_review_rows = [
        row for row in ichiban_prize_name_image_review.get("review_rows", []) if isinstance(row, dict)
    ]
    if ichiban_name_review_rows:
        add_batch(
            agent_id="agent-ichiban-prize-name-image",
            workstream="ichiban_kuji_prize_name_image_review",
            priority=56,
            title="Ichiban Kuji prize name/image structure review",
            public_report=ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW,
            rows=len(ichiban_name_review_rows),
            recommended_action=(
                "Confirm each prize display name includes campaign, prize rank, prize item, and variant detail."
            ),
            acceptance_criteria=[
                "Display names include the release name, prize rank, and prize item name.",
                "Same-prize multi-item rows include numbering, character, color, or item-type detail.",
                "Images are only changed when same campaign, prize rank, and variant identity all match.",
            ],
            samples=ichiban_name_review_rows,
            review_summary=ichiban_prize_name_image_review.get("summary", {}),
        )

    ichiban_patch_candidates = [
        row
        for row in ichiban_prize_name_image_patch_candidates.get("candidates", [])
        if isinstance(row, dict) and row.get("manual_confirmed") is not True
    ]
    if ichiban_patch_candidates:
        add_batch(
            agent_id="agent-ichiban-prize-name-image",
            workstream="ichiban_kuji_prize_name_image_patch_candidates",
            priority=57,
            title="Ichiban Kuji prize image/name patch candidates",
            public_report=ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES,
            rows=len(ichiban_patch_candidates),
            recommended_action="Review exact image matches and confirm only safe catalog patch templates.",
            acceptance_criteria=[
                "candidate image URL must match the same official campaign prize and item variant.",
                "field_changes must not erase variant details or collapse distinct prize rows.",
                "catalog_patch_template stays manual_confirmed=false until reviewed.",
            ],
            samples=ichiban_patch_candidates,
            review_summary=ichiban_prize_name_image_patch_candidates.get("summary", {}),
        )

    animation_action_batches = [batch for batch in animation_action_queue.get("batches", []) if isinstance(batch, dict)]
    for action_index, action_batch in enumerate(animation_action_batches[:4]):
        mapping_mode_counts = Counter(
            str(row.get("mapping_mode") or "unknown")
            for row in action_batch.get("categories", [])
            if isinstance(row, dict)
        )
        add_batch(
            agent_id="agent-animation-category-action",
            workstream="animation_category_action_queue",
            priority=22 + action_index,
            title=f"애니메이션 카테고리 매핑 템플릿 확인: {action_batch.get('batch_id')}",
            public_report=ANIMATION_CATEGORY_ACTION_QUEUE,
            rows=int(action_batch.get("affected_catalog_rows") or 0),
            recommended_action=(
                "Split name-level review categories first, then confirm direct category-to-folder mapping templates."
            ),
            acceptance_criteria=[
                "Each category_mapping_template remains manual_confirmed=false until sample names are reviewed.",
                "Broad source categories are split before one folder mapping is applied.",
                "Folder color and icon keys already exist in app visual catalogs.",
            ],
            samples=[row for row in action_batch.get("categories", []) if isinstance(row, dict)],
            review_summary={
                "split_review_categories": mapping_mode_counts.get("name_level_split_review_required", 0),
                "direct_mapping_categories": mapping_mode_counts.get("direct_category_mapping_review", 0),
                "category_count": int(action_batch.get("category_count") or 0),
                "work_order_lanes": animation_action_queue_summary.get("work_order_lanes", []),
                "split_first_blocked_categories": animation_action_queue_summary.get(
                    "split_first_blocked_categories", []
                ),
            },
        )

    animation_split_items = [
        row for row in animation_split_review.get("review_items", []) if isinstance(row, dict)
    ]
    for split_index, split_item in enumerate(animation_split_items[:4]):
        add_batch(
            agent_id="agent-animation-category-split",
            workstream="animation_category_split_review",
            priority=26 + split_index,
            title=f"애니메이션 이름별 세부 분류 확인: {split_item.get('source_category')}",
            public_report=ANIMATION_CATEGORY_SPLIT_REVIEW,
            rows=int(split_item.get("affected_catalog_rows") or 0),
            recommended_action=(
                "Confirm name keyword templates before applying broad category split rules to catalog rows."
            ),
            acceptance_criteria=[
                "Each name_level_split_template remains manual_confirmed=false until item names are reviewed.",
                "Same prize-letter variants remain separate catalog rows when the official campaign has multiple types.",
                "Unmatched samples stay blocked until a safer keyword or official category is confirmed.",
            ],
            samples=[candidate for candidate in split_item.get("split_candidates", []) if isinstance(candidate, dict)],
            review_summary={
                "split_candidate_count": int(split_item.get("split_candidate_count") or 0),
                "matched_sample_count": int(split_item.get("matched_sample_count") or 0),
                "unmatched_sample_count": int(split_item.get("unmatched_sample_count") or 0),
            },
        )

    animation_keyword_items = [
        row for row in animation_unmatched_keyword_review.get("review_items", []) if isinstance(row, dict)
    ]
    for keyword_index, keyword_item in enumerate(animation_keyword_items[:4]):
        product_type_candidates = [
            row for row in keyword_item.get("promotable_token_candidates", []) if isinstance(row, dict)
        ]
        top_token_candidates = [
            row for row in keyword_item.get("top_token_candidates", []) if isinstance(row, dict)
        ]
        add_batch(
            agent_id="agent-animation-keyword-review",
            workstream="animation_category_unmatched_keyword_review",
            priority=34 + keyword_index,
            title=f"애니메이션 미매칭 키워드 후보 검수: {keyword_item.get('source_category')}",
            public_report=ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW,
            rows=int(keyword_item.get("unmatched_rows") or 0),
            recommended_action=(
                "Review token candidates and promote only product-type keywords into split rules."
            ),
            acceptance_criteria=[
                "Token candidates remain manual_confirmed=false until sample rows are checked.",
                "Series names, character names, and store-only tokens are not promoted as product categories.",
                "Accepted keywords map to an existing app folder color and icon family.",
            ],
            samples=(product_type_candidates or top_token_candidates)[:12],
            review_summary={
                "unmatched_rows": int(keyword_item.get("unmatched_rows") or 0),
                "token_candidate_count": len(top_token_candidates),
                "product_type_candidate_count": len(product_type_candidates),
                "sample_source": "product_type_candidates" if product_type_candidates else "top_token_candidates",
                "source_category_rows": int(keyword_item.get("source_category_rows") or 0),
            },
        )

    review_batches = [batch for batch in animation_review_batches.get("batches", []) if isinstance(batch, dict)]
    if review_batches:
        for review_batch in review_batches[:4]:
            add_batch(
                agent_id="agent-animation-taxonomy",
                workstream="animation_category_review",
                priority=140 + int(review_batch.get("priority") or 99),
                title=f"애니메이션 굿즈 카테고리 검수: {review_batch.get('batch_id')}",
                public_report=ANIMATION_CATEGORY_REVIEW_BATCHES,
                rows=int(review_batch.get("row_count") or 0),
                recommended_action=str(review_batch.get("recommended_action") or "Map category batches to app folders."),
                acceptance_criteria=[
                    "Folder color hints follow folder_color_palette sort order.",
                    "Icon choices use existing icon keys from folder_visual_tokens.",
                    "Category changes remain review-only until app navigation impact is checked.",
                ],
                samples=[row for row in review_batch.get("categories", []) if isinstance(row, dict)],
            )
    else:
        unknown_categories = animation_categories.get("unknown_categories", [])
        if unknown_categories:
            add_batch(
                agent_id="agent-animation-taxonomy",
                workstream="animation_category_review",
                priority=140,
                title="애니메이션 굿즈 미분류 카테고리 정리",
                public_report=ANIMATION_CATEGORIES,
                rows=int(animation_categories.get("summary", {}).get("unknown_category_count") or 0),
                recommended_action="Map unknown categories to app folder families and visual tokens.",
                acceptance_criteria=[
                    "Folder color hints follow folder_color_palette sort order.",
                    "Icon choices use existing icon keys from folder_visual_tokens.",
                    "Category changes remain review-only until app navigation impact is checked.",
                ],
                samples=[row for row in unknown_categories if isinstance(row, dict)],
            )

    starter_groups = [
        row for row in source_discovery_starter_queue.get("groups", []) if isinstance(row, dict)
    ]
    starter_next_review_batch = [
        row
        for row in source_discovery_starter_queue.get("next_review_batch", [])
        if isinstance(row, dict)
    ]
    if starter_next_review_batch:
        add_batch(
            agent_id="agent-source-starter",
            workstream="source_discovery_starter_next_review_batch",
            priority=20,
            title="Next missing-image source review batch",
            public_report=SOURCE_DISCOVERY_STARTER_QUEUE,
            rows=len(starter_next_review_batch),
            recommended_action=(
                "Open this flat 20-row batch first and confirm exact product/detail source pages "
                "before broad missing-image research."
            ),
            acceptance_criteria=[
                "Open search_url first when present; otherwise use the fallback web search URL.",
                "Accepted source_url must be an exact official or licensed product/detail page.",
                "Only prepare image_url when the exact product image is visible on the accepted source.",
                "Keep auto-apply disabled; produce reviewed template rows only.",
            ],
            samples=starter_next_review_batch,
            sample_limit=20,
            review_summary={
                "next_review_batch_rows": len(starter_next_review_batch),
                "next_review_batch_group_count": int(
                    source_discovery_starter_queue.get("summary", {}).get(
                        "next_review_batch_group_count", 0
                    )
                    or 0
                ),
                "next_review_batch_primary_source_store": source_discovery_starter_queue.get(
                    "summary", {}
                ).get("next_review_batch_primary_source_store"),
            },
        )
    for group in starter_groups[:10]:
        sample_items = [item for item in group.get("sample_items", []) if isinstance(item, dict)]
        add_batch(
            agent_id="agent-source-starter",
            workstream="source_discovery_starter_queue",
            priority=21 + int(group.get("priority") or 99),
            title=(
                f"{group.get('source_store')} {group.get('affiliation')} "
                f"{group.get('category')} source starter"
            ),
            public_report=SOURCE_DISCOVERY_STARTER_QUEUE,
            rows=int(group.get("rows") or 0),
            recommended_action=str(
                group.get("next_step")
                or "Open search URLs and confirm exact product source pages."
            ),
            acceptance_criteria=[
                "Open the provided search_url values before using web-wide fallback search.",
                "Accepted source_url must be an exact product/detail page for the same item or product line.",
                "Product image evidence must be visible on the confirmed source before image_url import.",
                "Keep auto-apply disabled; only prepare manually reviewed source/image templates.",
            ],
            samples=sample_items,
            review_summary={
                "starter_group_rows": int(group.get("rows") or 0),
                "starter_sample_rows": len(sample_items),
            },
        )

    batches.sort(key=lambda row: (row["priority"], -row["rows"], row["batch_id"]))
    published_batches = batches[:MAX_AGENT_WORK_QUEUE_BATCHES]
    by_workstream = Counter(str(batch["workstream"]) for batch in published_batches)
    by_agent = Counter(str(batch["agent_id"]) for batch in published_batches)
    confirmed_summary = confirmed_import_readiness.get("summary", {})
    confirmed_template_rows = int(confirmed_summary.get("template_items") or 0)
    confirmed_action_rows = int(confirmed_summary.get("public_action_queue_rows") or 0)
    confirmed_ready_rows = int(confirmed_summary.get("manual_confirmed_true") or 0)
    confirmed_pending_rows = int(confirmed_summary.get("ready_or_pending_import_rows") or 0)
    confirmed_blocked_rows = int(confirmed_summary.get("blocked_confirmed_rows") or 0)
    confirmed_variant_metadata_template_rows = int(
        confirmed_summary.get("variant_metadata_template_rows") or 0
    )
    confirmed_variant_metadata_manual_confirmed_rows = int(
        confirmed_summary.get("variant_metadata_manual_confirmed_rows") or 0
    )
    confirmed_variant_metadata_skipped_rows = int(
        confirmed_summary.get("variant_metadata_skipped_rows") or 0
    )
    image_asset_next_action = next(
        (
            row
            for row in operations.get("next_actions", [])
            if isinstance(row, dict)
            and row.get("workstream") == "local_image_asset_audit"
        ),
        {},
    )
    image_missing_evidence_priority = (
        image_asset_next_action.get("missing_image_evidence_priority") or {}
    )
    top_next_batches = [
        {
            "batch_id": batch["batch_id"],
            "agent_id": batch["agent_id"],
            "workstream": batch["workstream"],
            "priority": batch["priority"],
            "rows": batch["rows"],
            "title": batch["title"],
            "public_report": batch["public_report"],
            "review_state": batch["review_state"],
            "next_machine_step": batch["next_machine_step"],
            **({"review_summary": batch["review_summary"]} if "review_summary" in batch else {}),
        }
        for batch in published_batches[:10]
    ]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "summary": {
            "batch_count": len(published_batches),
            "max_published_batches": MAX_AGENT_WORK_QUEUE_BATCHES,
            "summed_batch_rows": sum(int(batch.get("rows") or 0) for batch in published_batches),
            "top_next_batch_count": len(top_next_batches),
            "by_workstream": by_workstream.most_common(),
            "by_agent": by_agent.most_common(),
            "open_review_queues": operations["summary"]["open_review_queues"],
            "confirmed_import_template_rows": confirmed_template_rows,
            "confirmed_import_action_queue_rows": confirmed_action_rows,
            "confirmed_import_manual_confirmed_ready_rows": confirmed_ready_rows,
            "confirmed_import_pending_rows": confirmed_pending_rows,
            "confirmed_import_blocked_confirmed_rows": confirmed_blocked_rows,
            "confirmed_import_variant_metadata_template_rows": confirmed_variant_metadata_template_rows,
            "confirmed_import_variant_metadata_manual_confirmed_rows": confirmed_variant_metadata_manual_confirmed_rows,
            "confirmed_import_variant_metadata_skipped_rows": confirmed_variant_metadata_skipped_rows,
            "confirmed_import_manual_confirmation_backlog_rows": max(
                confirmed_template_rows + confirmed_action_rows - confirmed_ready_rows,
                0,
            ),
            "confirmed_import_work_order_lanes": int(confirmed_summary.get("work_order_lanes") or 0),
            "confirmed_import_top_work_order_lane": confirmed_summary.get("top_work_order_lane"),
            "confirmed_import_top_work_order_workflow": confirmed_summary.get("top_work_order_workflow"),
            "confirmed_import_top_work_order_row_count": int(confirmed_summary.get("top_work_order_row_count") or 0),
            "image_rows_still_requiring_url_evidence": int(
                image_asset_next_action.get("rows_still_requiring_image_url_evidence") or 0
            ),
            "image_missing_evidence_top_source_stores": image_missing_evidence_priority.get(
                "by_source_store", []
            )[:8],
            "image_missing_evidence_top_categories": image_missing_evidence_priority.get(
                "by_category", []
            )[:8],
            "source_discovery_starter_next_review_batch_rows": int(
                source_discovery_starter_queue.get("summary", {}).get(
                    "next_review_batch_rows", 0
                )
                or 0
            ),
            "source_discovery_starter_next_review_batch_group_count": int(
                source_discovery_starter_queue.get("summary", {}).get(
                    "next_review_batch_group_count", 0
                )
                or 0
            ),
            "source_discovery_starter_next_review_batch_primary_source_store": source_discovery_starter_queue.get(
                "summary", {}
            ).get("next_review_batch_primary_source_store"),
        },
        "top_next_batches": top_next_batches,
        "instructions": [
            "Agent-ready public work queue generated from the public catalog reports.",
            "Use this file to split DB cleanup across agents without exposing private local data.",
            "Every proposed catalog mutation still needs exact source evidence and review before import.",
        ],
        "batches": published_batches,
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "safe_for_github_pages": True,
            "reason": "This queue coordinates work; it does not contain credentials or private ownership data.",
        },
    }


def build_generic_source_patch_candidates_public(generated_at: str) -> dict[str, Any]:
    generic_source_report = load_json(GENERIC_SOURCE, {}) if GENERIC_SOURCE.exists() else {}
    items: list[dict[str, Any]] = []
    for item in generic_source_report.get("items", []):
        if not isinstance(item, dict) or not item.get("candidate_source_url"):
            continue
        candidate_status = str(item.get("candidate_status") or "candidate_review_required")
        confidence = (
            "manual_confirmed"
            if item.get("manual_confirmed") is True
            else "weak"
            if candidate_status == "weak_manual_review_candidate"
            else "low"
        )
        items.append(
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "current_source_url": item.get("current_source_url"),
                "candidate_source_url": item.get("candidate_source_url"),
                "candidate_image_url": item.get("candidate_image_url"),
                "candidate_title": item.get("candidate_title"),
                "candidate_score": item.get("candidate_score"),
                "candidate_status": candidate_status,
                "confidence": confidence,
                "proposed_fields": {
                    "source_url": item.get("candidate_source_url"),
                    "image_url": item.get("candidate_image_url"),
                },
                "review_required": True,
                "review_checks": [
                    "Candidate title must describe the exact same goods item or set.",
                    "Candidate image must visually match the catalog item, not only the same brand/store.",
                    "Generic storefront source_url must be replaced only after exact product identity is confirmed.",
                ],
            }
        )

    by_status = Counter(str(item.get("candidate_status") or "") for item in items)
    by_confidence = Counter(str(item.get("confidence") or "") for item in items)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "generic_source_review_patch_candidates",
        "summary": {
            "candidate_rows": len(items),
            "manual_confirmed_rows": by_confidence.get("manual_confirmed", 0),
            "weak_candidate_rows": by_confidence.get("weak", 0),
            "low_confidence_candidate_rows": by_confidence.get("low", 0),
            "auto_apply_enabled": False,
            "source_report": f"data/{GENERIC_SOURCE.name}",
            "by_candidate_status": by_status.most_common(),
            "by_confidence": by_confidence.most_common(),
        },
        "items": items,
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "reason": "These candidates came from generic storefront cleanup and may be related but not exact.",
        },
    }


def normalize_text_key(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_dedupe_name(value: Any) -> str:
    text = normalize_text_key(value)
    drop_chars = " \t\r\n-_/\\.,，、・:：;；'\"`´[](){}<>【】「」『』（）［］〈〉《》"
    return "".join(char for char in text if char not in drop_chars)


def normalize_url_key(value: Any) -> str:
    return normalize_text_key(value).rstrip("/")


def row_richness(item: dict[str, Any]) -> int:
    return sum(1 for field in PUBLIC_FIELDS if present(item.get(field)))


def dedupe_keys(item: dict[str, Any]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    name = normalize_text_key(item.get("name_ja") or item.get("name_ko"))
    normalized_name = normalize_dedupe_name(item.get("name_ja") or item.get("name_ko"))
    barcode = normalize_text_key(item.get("barcode"))
    if barcode:
        keys.append(("barcode", barcode))
    source_url = normalize_url_key(item.get("source_url"))
    if source_url and len(name) >= 6:
        keys.append(("source_url", f"{source_url}|{name}"))
    if source_url and len(normalized_name) >= 6 and normalized_name != name:
        keys.append(("source_url_normalized_name", f"{source_url}|{normalized_name}"))
    image_url = normalize_url_key(item.get("image_url"))
    if image_url:
        if len(name) >= 6:
            keys.append(("image_url", f"{image_url}|{name}"))
        if len(normalized_name) >= 6 and normalized_name != name:
            keys.append(("image_url_normalized_name", f"{image_url}|{normalized_name}"))
    return keys


def shared_source_url_exclusion_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    source_url_groups: dict[str, list[int]] = defaultdict(list)
    for index, item in enumerate(items):
        source_url = normalize_url_key(item.get("source_url"))
        if source_url:
            source_url_groups[source_url].append(index)

    shared_groups = [indices for indices in source_url_groups.values() if len(set(indices)) > 1]
    shared_rows = sum(len(set(indices)) for indices in shared_groups)
    dedupe_key_groups = 0
    for indices in shared_groups:
        grouped_by_name: dict[str, set[int]] = defaultdict(set)
        for index in indices:
            item = items[index]
            for key_type, key_value in dedupe_keys(item):
                if key_type.startswith("source_url"):
                    grouped_by_name[key_value].add(index)
        dedupe_key_groups += sum(1 for grouped_indices in grouped_by_name.values() if len(grouped_indices) > 1)

    return {
        "shared_source_url_value_groups": len(shared_groups),
        "shared_source_url_value_rows": shared_rows,
        "source_url_name_matched_review_groups": dedupe_key_groups,
        "excluded_shared_source_url_value_groups": max(len(shared_groups) - dedupe_key_groups, 0),
    }


def build_deduplication_public(items: list[dict[str, Any]], sample_groups: int = 80) -> dict[str, Any]:
    key_to_indices: dict[tuple[str, str], list[int]] = {}
    for index, item in enumerate(items):
        for key in dedupe_keys(item):
            key_to_indices.setdefault(key, []).append(index)

    def dedupe_review_metadata(key_type: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        categories = {str(row.get("category") or "") for row in rows if row.get("category")}
        stores = {str(row.get("source_store") or "") for row in rows if row.get("source_store")}
        image_urls = {str(row.get("image_url") or "") for row in rows if row.get("image_url")}
        source_urls = {str(row.get("source_url") or "") for row in rows if row.get("source_url")}
        barcodes = {str(row.get("barcode") or "") for row in rows if row.get("barcode")}
        evidence: list[str] = [key_type]
        if len(barcodes) == 1 and barcodes:
            evidence.append("same_barcode")
        if len(source_urls) == 1 and source_urls:
            evidence.append("same_source_url")
        if len(image_urls) == 1 and image_urls:
            evidence.append("same_image_url")
        if len(categories) > 1:
            evidence.append("category_mismatch")
        if len(stores) > 1:
            evidence.append("multi_store")

        if "category_mismatch" in evidence:
            review_risk = "variant_risk_review"
            recommended_action = "Compare product type/category before any merge; preserve variants if category is truly different."
            review_priority = 40
        elif key_type == "barcode" and "same_barcode" in evidence:
            review_risk = "strong_identity_review"
            recommended_action = "Verify names/images match the same product, then prefer the richer official row as keep."
            review_priority = 10
        elif key_type.startswith("source_url") and "same_source_url" in evidence:
            review_risk = "source_identity_review"
            recommended_action = "Verify rows point to the same product detail page before merge."
            review_priority = 20
        elif key_type.startswith("image_url") and "same_image_url" in evidence:
            review_risk = "image_identity_review"
            recommended_action = "Check that the shared image is not a reused lineup/placeholder image before merge."
            review_priority = 30
        else:
            review_risk = "manual_identity_review"
            recommended_action = "Review all evidence manually before proposing keep/drop."
            review_priority = 50

        return {
            "review_priority": review_priority,
            "review_risk": review_risk,
            "evidence": evidence,
            "recommended_action": recommended_action,
        }

    seen_groups: set[tuple[int, ...]] = set()
    groups: list[dict[str, Any]] = []
    duplicate_rows: set[int] = set()
    for key, indices in sorted(
        key_to_indices.items(),
        key=lambda pair: (DEDUPLICATION_KEY_PRIORITY.get(pair[0][0], 99), pair[0][1]),
    ):
        unique_indices = sorted(set(indices))
        if len(unique_indices) < 2:
            continue
        signature = tuple(unique_indices)
        if signature in seen_groups:
            continue
        seen_groups.add(signature)
        keep = max(unique_indices, key=lambda idx: (row_richness(items[idx]), -idx))
        drops = [idx for idx in unique_indices if idx != keep]
        duplicate_rows.update(drops)
        group_rows = [
            {
                "catalog_index": item.get("catalog_index", idx),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "source_store": item.get("source_store"),
                "category": item.get("category"),
                "barcode": item.get("barcode"),
                "source_url": item.get("source_url"),
                "image_url": item.get("image_url"),
                "richness": row_richness(item),
            }
            for idx in unique_indices
            for item in [items[idx]]
        ]
        review_metadata = dedupe_review_metadata(key[0], group_rows)
        groups.append(
            {
                "key_type": key[0],
                "key": key[1],
                "keep_catalog_index": items[keep].get("catalog_index", keep),
                "drop_catalog_indexes": [items[idx].get("catalog_index", idx) for idx in drops],
                **review_metadata,
                "rows": group_rows,
            }
        )

    by_key_type = Counter(group["key_type"] for group in groups)
    by_review_risk = Counter(group["review_risk"] for group in groups)
    source_url_exclusions = shared_source_url_exclusion_summary(items)
    groups.sort(
        key=lambda group: (
            int(group.get("review_priority") or 99),
            DEDUPLICATION_KEY_PRIORITY.get(str(group.get("key_type")), 99),
            -len(group.get("rows") or []),
            str(group.get("key") or ""),
        )
    )
    return {
        "schema_version": 1,
        "summary": {
            "rows": len(items),
            "duplicate_groups": len(groups),
            "duplicate_rows": len(duplicate_rows),
            "published_groups": min(sample_groups, len(groups)),
            "by_key_type": by_key_type.most_common(),
            "by_review_risk": by_review_risk.most_common(),
            "top_review_risk": groups[0]["review_risk"] if groups else None,
            "source_url_exclusions": source_url_exclusions,
        },
        "automation_policy": {
            "auto_delete": False,
            "requires_manual_review": True,
            "reason": "Shared barcode/source/image evidence can still represent variants; public report is a review queue only.",
            "normalization": "Names are normalized only when barcode/source_url/image_url evidence is shared.",
            "excluded": "Broad same-name matches across different campaign URLs and broad same-source-url matches are excluded because they often represent legitimate variants, campaign prize rows, or lineup pages.",
        },
        "groups": groups[:sample_groups],
    }


def build_name_duplicate_audit_public(items: list[dict[str, Any]], sample_groups: int = 120) -> dict[str, Any]:
    groups_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        name_key = normalize_dedupe_name(item.get("name_ja") or item.get("name_ko"))
        if len(name_key) >= 6:
            groups_by_name[name_key].append(item)

    duplicate_groups = [
        rows for rows in groups_by_name.values() if len({int(row.get("catalog_index") or -1) for row in rows}) > 1
    ]

    def distinct_values(rows: list[dict[str, Any]], field: str) -> set[str]:
        return {str(row.get(field) or "").strip() for row in rows if present(row.get(field))}

    def classify(rows: list[dict[str, Any]]) -> tuple[str, int, str, str]:
        barcodes = distinct_values(rows, "barcode")
        categories = distinct_values(rows, "category")
        source_urls = distinct_values(rows, "source_url")
        source_stores = distinct_values(rows, "source_store")
        sub_series = distinct_values(rows, "sub_series")
        character_names = distinct_values(rows, "character_name")
        has_ichiban = any(is_ichiban_kuji_item(row) for row in rows)
        campaign_urls = {
            url
            for url in source_urls
            if "1kuji.com/products/" in url
        }

        if has_ichiban and len(campaign_urls) > 1:
            return (
                "ichiban_campaign_or_reissue_protected",
                10,
                "Same visible prize name appears across multiple 1kuji campaign URLs.",
                "Compare campaign pages and only record a dedupe decision if official evidence proves the same sellable product.",
            )
        if len(barcodes) == 1 and barcodes:
            return (
                "same_barcode_name_review",
                20,
                "Rows share a barcode and normalized name.",
                "Verify product images/source pages, then prefer the richer official row before any keep/drop decision.",
            )
        if len(barcodes) > 1:
            return (
                "same_name_distinct_barcode_variant_protected",
                30,
                "Same normalized name has distinct barcode values.",
                "Treat as likely variants or rereleases unless source evidence proves otherwise.",
            )
        if len(categories) > 1 or len(sub_series) > 1 or len(character_names) > 1:
            return (
                "same_name_variant_risk_review",
                40,
                "Same normalized name spans category, character, or sub-series differences.",
                "Preserve variants unless official evidence proves rows are accidental duplicates.",
            )
        if len(source_urls) > 1 or len(source_stores) > 1:
            return (
                "same_name_multi_source_review",
                50,
                "Same normalized name appears across multiple sources.",
                "Review source identity and release context before proposing a merge.",
            )
        return (
            "same_name_manual_review",
            60,
            "Same normalized name lacks stronger shared barcode/source/image evidence.",
            "Manually compare images, source, release date, and product variant labels before any action.",
        )

    rows_out: list[dict[str, Any]] = []
    lane_counts: Counter[str] = Counter()
    protected_lanes = {
        "ichiban_campaign_or_reissue_protected",
        "same_name_distinct_barcode_variant_protected",
        "same_name_variant_risk_review",
    }
    protected_groups = 0
    manual_review_groups = 0
    for group_rows in duplicate_groups:
        lane, priority, reason, action = classify(group_rows)
        lane_counts[lane] += 1
        if lane in protected_lanes:
            protected_groups += 1
        else:
            manual_review_groups += 1

        sorted_rows = sorted(group_rows, key=lambda row: int(row.get("catalog_index") or 0))
        rows_out.append(
            {
                "name_key": normalize_dedupe_name(sorted_rows[0].get("name_ja") or sorted_rows[0].get("name_ko")),
                "sample_name_ko": sorted_rows[0].get("name_ko"),
                "sample_name_ja": sorted_rows[0].get("name_ja"),
                "rows": len(sorted_rows),
                "catalog_indexes": [row.get("catalog_index") for row in sorted_rows],
                "lane": lane,
                "review_priority": priority,
                "blocked_reason": reason,
                "recommended_action": action,
                "distinct_barcodes": sorted(distinct_values(sorted_rows, "barcode")),
                "distinct_source_urls": sorted(distinct_values(sorted_rows, "source_url"))[:12],
                "distinct_categories": sorted(distinct_values(sorted_rows, "category")),
                "distinct_sub_series": sorted(distinct_values(sorted_rows, "sub_series")),
                "distinct_source_stores": sorted(distinct_values(sorted_rows, "source_store")),
                "sample_items": [
                    {
                        "catalog_index": row.get("catalog_index"),
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                        "category": row.get("category"),
                        "sub_series": row.get("sub_series"),
                        "barcode": row.get("barcode"),
                        "source_store": row.get("source_store"),
                        "source_url": row.get("source_url"),
                        "release_date": row.get("release_date"),
                    }
                    for row in sorted_rows[:8]
                ],
            }
        )

    rows_out.sort(
        key=lambda row: (
            int(row.get("review_priority") or 99),
            -int(row.get("rows") or 0),
            str(row.get("sample_name_ko") or ""),
        )
    )
    duplicate_rows = sum(len(rows) for rows in duplicate_groups)
    return {
        "schema_version": 1,
        "scope": "catalog_name_duplicate_audit",
        "summary": {
            "catalog_rows": len(items),
            "name_duplicate_groups": len(duplicate_groups),
            "name_duplicate_rows": duplicate_rows,
            "published_groups": min(sample_groups, len(rows_out)),
            "manual_review_groups": manual_review_groups,
            "protected_groups": protected_groups,
            "ichiban_campaign_or_reissue_protected_groups": lane_counts.get(
                "ichiban_campaign_or_reissue_protected", 0
            ),
            "same_barcode_name_review_groups": lane_counts.get("same_barcode_name_review", 0),
            "same_name_distinct_barcode_variant_protected_groups": lane_counts.get(
                "same_name_distinct_barcode_variant_protected", 0
            ),
            "same_name_variant_risk_review_groups": lane_counts.get("same_name_variant_risk_review", 0),
            "same_name_multi_source_review_groups": lane_counts.get("same_name_multi_source_review", 0),
            "same_name_manual_review_groups": lane_counts.get("same_name_manual_review", 0),
            "lane_counts": lane_counts.most_common(),
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        "groups": rows_out[:sample_groups],
        "automation_policy": {
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
            "requires_manual_review": True,
            "reason": "Same-name groups often include rereleases, Ichiban Kuji campaign variants, or distinct barcode variants.",
            "required_before_write": [
                "open every source_url in the group",
                "confirm official product identity",
                "confirm same barcode/source/image only when applicable",
                "record explicit keep/drop decisions in the confirmed deduplication template",
            ],
        },
    }


def category_family(category: str) -> str:
    for family, values in CATEGORY_FAMILIES.items():
        if category in values:
            return family
    return "other"


def color_sort_order(color_hint: str) -> int:
    for row in FOLDER_COLOR_PALETTE:
        if row["color_hint"] == color_hint:
            return int(row["sort_order"])
    return 999


def color_group(color_hint: str) -> str:
    for row in FOLDER_COLOR_PALETTE:
        if row["color_hint"] == color_hint:
            return str(row.get("color_group") or "neutral")
    return "neutral"


def folder_visual_token(category: str, family: str, rows: int) -> dict[str, Any]:
    visual = FAMILY_VISUALS.get(family, FAMILY_VISUALS["other"])
    return {
        "category": category,
        "family": family,
        "rows": rows,
        "color_hint": visual["color_hint"],
        "color_hex": visual["color_hex"],
        "color_group": color_group(visual["color_hint"]),
        "color_sort_order": color_sort_order(visual["color_hint"]),
        "primary_icon_key": visual["icon_key"],
        "icon_options": FAMILY_ICON_OPTIONS.get(family, FAMILY_ICON_OPTIONS["other"]),
    }


def counter_rows(counter: Counter[Any], keys: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for values, count in counter.most_common(limit):
        if not isinstance(values, tuple):
            values = (values,)
        item = {key: value for key, value in zip(keys, values)}
        item["rows"] = count
        rows.append(item)
    return rows


def is_animation_goods(item: dict[str, Any]) -> bool:
    if str(item.get("source_store") or "") in ANIMATION_STORES:
        return True
    affiliation = str(item.get("affiliation") or "")
    series = str(item.get("series_name") or "")
    return any(token in affiliation or token in series for token in ("단간론파", "주술회전", "헌터헌터", "프리렌", "최애의아이", "나의 히어로"))


def build_animation_categories_public(items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [item for item in items if is_animation_goods(item)]
    app_visual_catalog = app_folder_visual_catalog_summary()
    by_category = Counter(str(item.get("category") or "미분류") for item in rows)
    by_family = Counter(category_family(str(item.get("category") or "")) for item in rows)
    by_store_category = Counter(
        (str(item.get("source_store") or ""), str(item.get("category") or "미분류")) for item in rows
    )
    missing_image_by_category = Counter(
        str(item.get("category") or "미분류") for item in rows if not present(item.get("image_url"))
    )
    missing_source_by_category = Counter(
        str(item.get("category") or "미분류") for item in rows if not present(item.get("source_url"))
    )
    by_sub_series = Counter(str(item.get("sub_series") or "") for item in rows if present(item.get("sub_series")))

    category_visuals = []
    folder_visual_tokens = []
    for category, count in by_category.most_common(120):
        family = category_family(category)
        visual = FAMILY_VISUALS.get(family, FAMILY_VISUALS["other"])
        category_visuals.append(
            {
                "category": category,
                "family": family,
                "rows": count,
                "recommended_icon_key": visual["icon_key"],
                "recommended_color_hint": visual["color_hint"],
                "recommended_color_hex": visual["color_hex"],
            }
        )
        folder_visual_tokens.append(folder_visual_token(category, family, count))

    folder_visual_tokens.sort(
        key=lambda row: (
            row["color_sort_order"],
            str(row.get("family") or ""),
            str(row.get("category") or ""),
        )
    )

    suggestions = []
    for category, canonical in CANONICAL_CATEGORY_SUGGESTIONS.items():
        affected = [item for item in rows if item.get("category") == category]
        if not affected:
            continue
        suggestions.append(
            {
                "category": category,
                "suggested_category": canonical,
                "rows": len(affected),
                "risk": "medium",
                "reason": "Subtype-like category may work better as sub_series while using a broader app category.",
                "sample_names": [item.get("name_ko") for item in affected[:8]],
            }
        )
    normalization_review_queue = []
    for index, suggestion in enumerate(suggestions, start=1):
        normalization_review_queue.append(
            {
                "review_id": f"animation-category-normalization-{index:03d}",
                "category": suggestion["category"],
                "suggested_category": suggestion["suggested_category"],
                "affected_catalog_rows": suggestion["rows"],
                "risk": suggestion["risk"],
                "review_reason": suggestion["reason"],
                "sample_names": suggestion["sample_names"],
                "mapping_mode": "canonical_category_normalization_review",
                "next_step": "confirm_category_normalization_before_import",
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
                "blocked_until": "canonical_category_normalization_manually_confirmed",
                "blocked_reason": "subtype_category_may_need_sub_series_preservation",
                "required_evidence": [
                    "sample_names_match_suggested_broader_category",
                    "source_category_should_be_preserved_as_sub_series_or_note",
                    "folder_color_and_icon_exist_in_app_catalog",
                    "manual_note_for_category_semantics",
                ],
                "category_mapping_template": {
                    "manual_confirmed": False,
                    "source_category": suggestion["category"],
                    "target_category": suggestion["suggested_category"],
                    "preserve_source_category_as_sub_series": True,
                    "affected_catalog_rows": suggestion["rows"],
                    "manual_note": "",
                },
            }
        )

    unknown_categories = []
    for category, count in by_category.most_common():
        if category_family(category) != "other":
            continue
        suggestion = UNKNOWN_CATEGORY_REVIEW_SUGGESTIONS.get(
            category,
            {
                "suggested_family": "other",
                "suggested_category": category,
                "color_hint": "neutral",
                "primary_icon_key": "category",
                "review_priority": 90,
                "reason": "No exact mapping exists yet; keep in manual taxonomy review.",
            },
        )
        color_hint = str(suggestion["color_hint"])
        affected = [item for item in rows if str(item.get("category") or "") == category]
        unknown_categories.append(
            {
                "category": category,
                "rows": count,
                "review_priority": suggestion["review_priority"],
                "suggested_family": suggestion["suggested_family"],
                "suggested_category": suggestion["suggested_category"],
                "suggested_color_hint": color_hint,
                "suggested_color_hex": next(
                    (row["color_hex"] for row in FOLDER_COLOR_PALETTE if row["color_hint"] == color_hint),
                    FAMILY_VISUALS["other"]["color_hex"],
                ),
                "suggested_color_group": color_group(color_hint),
                "suggested_color_sort_order": color_sort_order(color_hint),
                "suggested_primary_icon_key": suggestion["primary_icon_key"],
                "suggested_icon_options": FAMILY_ICON_OPTIONS.get(
                    str(suggestion["suggested_family"]), FAMILY_ICON_OPTIONS["other"]
                ),
                "review_reason": suggestion["reason"],
                "sample_names": [item.get("name_ko") for item in affected[:8]],
            }
        )
    unknown_categories.sort(
        key=lambda row: (
            int(row.get("review_priority") or 99),
            int(row.get("suggested_color_sort_order") or 999),
            str(row.get("category") or ""),
        )
    )
    normalization_review_rows = sum(
        int(row.get("affected_catalog_rows") or 0)
        for row in normalization_review_queue
    )
    unknown_category_rows = sum(int(row.get("rows") or 0) for row in unknown_categories)
    visual_coverage_ready = bool(
        app_visual_catalog.get("palette_sorted_by_family", False)
        and app_visual_catalog.get("animation_visuals_covered", False)
        and int(app_visual_catalog.get("color_count") or 0) > 0
        and int(app_visual_catalog.get("icon_count") or 0) > 0
    )
    category_completion_status = (
        "normalization_review_required"
        if normalization_review_queue
        else "unknown_category_review_required"
        if unknown_categories
        else "ready"
        if visual_coverage_ready
        else "folder_visual_catalog_review_required"
    )
    category_readiness = {
        "status": category_completion_status,
        "auto_apply_ready_rows": 0,
        "auto_apply_enabled": False,
        "manual_confirmed_rows": 0,
        "manual_review_categories": len(normalization_review_queue) + len(unknown_categories),
        "manual_review_rows": normalization_review_rows + unknown_category_rows,
        "unknown_category_rows": unknown_category_rows,
        "unknown_category_count": len(unknown_categories),
        "normalization_review_queue_rows": normalization_review_rows,
        "normalization_review_queue_count": len(normalization_review_queue),
        "folder_visual_coverage_ready": visual_coverage_ready,
        "app_folder_color_count": app_visual_catalog.get("color_count", 0),
        "app_folder_icon_option_count": app_visual_catalog.get("icon_count", 0),
        "app_folder_palette_sorted_by_family": app_visual_catalog.get("palette_sorted_by_family", False),
        "blocked_reasons": [
            "canonical_category_normalization_manually_confirmed"
            if normalization_review_queue
            else None,
            "unknown_category_mapping_required" if unknown_categories else None,
            "folder_visual_catalog_review_required" if not visual_coverage_ready else None,
        ],
        "next_safe_phase": (
            "confirm_category_normalization_before_import"
            if normalization_review_queue
            else "map_unknown_categories_to_folder_families"
            if unknown_categories
            else "no_animation_category_cleanup_required"
            if visual_coverage_ready
            else "verify_folder_color_and_icon_catalog"
        ),
        "safety_note": (
            "Animation category changes affect navigation and folder semantics; "
            "preserve subtype labels as sub_series or notes unless manual review confirms a direct category change."
        ),
    }
    next_review_item = normalization_review_queue[0] if normalization_review_queue else (
        unknown_categories[0] if unknown_categories else {}
    )
    if next_review_item:
        category_readiness["next_review_item"] = {
            "review_id": next_review_item.get("review_id"),
            "category": next_review_item.get("category"),
            "suggested_category": next_review_item.get("suggested_category"),
            "affected_catalog_rows": next_review_item.get("affected_catalog_rows")
            or next_review_item.get("rows"),
            "mapping_mode": next_review_item.get("mapping_mode")
            or "unknown_category_mapping_review",
            "blocked_until": next_review_item.get("blocked_until")
            or "unknown_category_mapping_manually_confirmed",
            "next_step": next_review_item.get("next_step")
            or category_readiness["next_safe_phase"],
        }
    category_readiness["blocked_reasons"] = [
        reason for reason in category_readiness["blocked_reasons"] if reason
    ]

    return {
        "schema_version": 1,
        "summary": {
            "animation_goods_rows": len(rows),
            "category_count": len(by_category),
            "unknown_category_count": len(unknown_categories),
            "unknown_category_rows": unknown_category_rows,
            "normalization_suggestion_count": len(suggestions),
            "normalization_review_queue_rows": normalization_review_rows,
            "normalization_review_queue_count": len(normalization_review_queue),
            "category_readiness_status": category_completion_status,
            "manual_review_categories": category_readiness["manual_review_categories"],
            "manual_review_rows": category_readiness["manual_review_rows"],
            "auto_apply_ready_rows": 0,
            "folder_visual_coverage_ready": visual_coverage_ready,
            "missing_image_rows": sum(1 for item in rows if not present(item.get("image_url"))),
            "missing_source_url_rows": sum(1 for item in rows if not present(item.get("source_url"))),
            "folder_color_palette_count": len(FOLDER_COLOR_PALETTE),
            "folder_icon_family_count": len(FAMILY_ICON_OPTIONS),
            "folder_icon_option_count": sum(len(options) for options in FAMILY_ICON_OPTIONS.values()),
            "app_folder_color_count": app_visual_catalog.get("color_count", 0),
            "app_folder_icon_option_count": app_visual_catalog.get("icon_count", 0),
            "app_folder_icon_group_count": app_visual_catalog.get("icon_group_count", 0),
            "app_folder_palette_section_count": app_visual_catalog.get("palette_section_count", 0),
            "app_folder_palette_sorted_by_family": app_visual_catalog.get("palette_sorted_by_family", False),
            "app_animation_visuals_covered": app_visual_catalog.get("animation_visuals_covered", False),
        },
        "category_families": counter_rows(by_family, ("family",), 40),
        "categories": counter_rows(by_category, ("category",), 120),
        "category_visuals": category_visuals,
        "folder_color_palette": FOLDER_COLOR_PALETTE,
        "app_folder_visual_catalog": app_visual_catalog,
        "folder_visual_tokens": folder_visual_tokens,
        "top_store_categories": counter_rows(by_store_category, ("source_store", "category"), 120),
        "missing_image_by_category": counter_rows(missing_image_by_category, ("category",), 60),
        "missing_source_url_by_category": counter_rows(missing_source_by_category, ("category",), 60),
        "top_sub_series": counter_rows(by_sub_series, ("sub_series",), 80),
        "normalization_suggestions": suggestions,
        "normalization_review_queue": normalization_review_queue,
        "category_readiness": category_readiness,
        "unknown_categories": unknown_categories[:80],
        "taxonomy_review_queue": unknown_categories[:80],
        "automation_policy": {
            "auto_apply_category_changes": False,
            "requires_manual_review": True,
            "reason": "Category changes affect app navigation and folder semantics; this public report is a review queue.",
        },
    }


def build_animation_category_coverage_audit_public(
    animation_categories: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    summary = animation_categories.get("summary", {})
    categories = [
        row for row in animation_categories.get("categories", []) if isinstance(row, dict)
    ]
    visual_tokens = [
        row
        for row in animation_categories.get("folder_visual_tokens", [])
        if isinstance(row, dict)
    ]
    token_categories = {str(row.get("category") or "") for row in visual_tokens}
    missing_visual_token_categories = [
        str(row.get("category") or "")
        for row in categories
        if str(row.get("category") or "") not in token_categories
    ]
    unknown_categories = [
        row for row in animation_categories.get("unknown_categories", []) if isinstance(row, dict)
    ]
    normalization_suggestions = [
        row
        for row in animation_categories.get("normalization_suggestions", [])
        if isinstance(row, dict)
    ]
    checks = [
        {
            "key": "unknown_categories_clear",
            "status": "pass"
            if int(summary.get("unknown_category_count") or 0) == 0
            else "fail",
            "value": int(summary.get("unknown_category_count") or 0),
        },
        {
            "key": "folder_visual_tokens_cover_categories",
            "status": "pass" if not missing_visual_token_categories else "fail",
            "value": len(missing_visual_token_categories),
            "missing_categories": missing_visual_token_categories[:50],
        },
        {
            "key": "folder_palette_sorted_by_family",
            "status": "pass"
            if summary.get("app_folder_palette_sorted_by_family") is True
            else "fail",
            "value": bool(summary.get("app_folder_palette_sorted_by_family")),
        },
        {
            "key": "app_animation_visuals_covered",
            "status": "pass"
            if summary.get("app_animation_visuals_covered") is True
            else "fail",
            "value": bool(summary.get("app_animation_visuals_covered")),
        },
    ]
    failed_checks = [row for row in checks if row.get("status") != "pass"]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": "animation_category_coverage_audit",
        "summary": {
            "animation_goods_rows": int(summary.get("animation_goods_rows") or 0),
            "category_count": int(summary.get("category_count") or len(categories)),
            "unknown_category_count": int(summary.get("unknown_category_count") or 0),
            "unknown_category_rows": int(summary.get("unknown_category_rows") or 0),
            "normalization_suggestion_count": len(normalization_suggestions),
            "folder_visual_token_count": len(visual_tokens),
            "missing_visual_token_categories": len(missing_visual_token_categories),
            "folder_color_palette_count": int(summary.get("folder_color_palette_count") or 0),
            "folder_icon_option_count": int(summary.get("folder_icon_option_count") or 0),
            "app_folder_color_count": int(summary.get("app_folder_color_count") or 0),
            "app_folder_icon_option_count": int(summary.get("app_folder_icon_option_count") or 0),
            "app_folder_palette_sorted_by_family": summary.get(
                "app_folder_palette_sorted_by_family"
            )
            is True,
            "app_animation_visuals_covered": summary.get("app_animation_visuals_covered")
            is True,
            "failed_check_count": len(failed_checks),
            "status": "pass" if not failed_checks else "fail",
            "auto_apply_enabled": False,
        },
        "checks": checks,
        "normalization_suggestions": normalization_suggestions,
        "unknown_categories": unknown_categories,
        "category_families": animation_categories.get("category_families", []),
        "folder_visual_tokens": visual_tokens,
        "automation_policy": {
            "auto_apply_enabled": False,
            "reason": "Coverage audit only; category normalization suggestions require manual review before import.",
        },
    }


def year_of(value: Any) -> str:
    text = str(value or "").strip()
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else "unknown"


def is_ichiban_kuji_item(item: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(item.get(field) or "")
        for field in ("source_url", "source_store", "series_name", "sub_series", "name_ko", "name_ja")
    )
    return "1kuji.com" in haystack or "一番くじ" in haystack or "이치방쿠지" in haystack


def campaign_slug(url: Any) -> str:
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    return text.split("/")[-1]


def build_ichiban_kuji_history_public(items: list[dict[str, Any]]) -> dict[str, Any]:
    campaigns = load_json(ICHIIBAN_KUJI_CAMPAIGNS, [])
    if not isinstance(campaigns, list):
        campaigns = []
    campaign_rows = [row for row in campaigns if isinstance(row, dict)]
    kuji_items = [item for item in items if is_ichiban_kuji_item(item)]

    campaign_by_url = {str(row.get("url") or "").rstrip("/"): row for row in campaign_rows}
    campaign_urls_in_catalog = {
        str(item.get("source_url") or "").rstrip("/")
        for item in kuji_items
        if "1kuji.com/products/" in str(item.get("source_url") or "")
    }
    campaign_with_catalog_rows = sorted(url for url in campaign_by_url if url in campaign_urls_in_catalog)
    missing_catalog_campaigns = sorted(url for url in campaign_by_url if url not in campaign_urls_in_catalog)

    by_campaign: Counter[str] = Counter()
    for item in kuji_items:
        url = str(item.get("source_url") or "").rstrip("/")
        if "1kuji.com/products/" in url:
            by_campaign[url] += 1

    by_campaign_year = Counter(year_of(row.get("release_date")) for row in campaign_rows)
    by_item_year = Counter(year_of(item.get("release_date")) for item in kuji_items)
    by_category = Counter(str(item.get("category") or "미분류") for item in kuji_items)
    by_sub_series = Counter(str(item.get("sub_series") or "미분류") for item in kuji_items)
    missing_release = [item for item in kuji_items if not present(item.get("release_date"))]
    missing_price = [item for item in kuji_items if not present(item.get("official_price_jpy"))]

    def item_group_key(item: dict[str, Any]) -> str:
        url = str(item.get("source_url") or "").strip().rstrip("/")
        if "1kuji.com/products/" in url:
            return url
        series = str(item.get("series_name") or "").strip()
        if series:
            return f"series:{series}"
        return "unknown"

    def grouped_item_backlog(backlog_items: list[dict[str, Any]], max_groups: int = 80) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in backlog_items:
            grouped[item_group_key(item)].append(item)

        rows: list[dict[str, Any]] = []
        for key, group_items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:max_groups]:
            url = key if key.startswith("http") else ""
            campaign = campaign_by_url.get(url, {})
            sample_items = group_items[:8]
            rows.append(
                {
                    "group_key": key,
                    "url": url or None,
                    "slug": campaign_slug(url),
                    "title": campaign.get("title") or sample_items[0].get("series_name"),
                    "release_date": campaign.get("release_date"),
                    "catalog_item_rows": len(group_items),
                    "sample_catalog_indexes": [item.get("catalog_index") for item in sample_items],
                    "sample_names": [
                        item.get("name_ko") or item.get("name_ja") or item.get("name_en")
                        for item in sample_items
                    ],
                    "review_action": "verify campaign detail page before applying inferred metadata",
                }
            )
        return rows

    missing_release_groups = grouped_item_backlog(missing_release)
    missing_price_groups = grouped_item_backlog(missing_price)
    campaign_metadata_review_by_key: dict[str, dict[str, Any]] = {}

    def merge_campaign_metadata_review(groups: list[dict[str, Any]], field: str, priority: int) -> None:
        for group in groups:
            key = str(group.get("group_key") or "")
            if key not in campaign_metadata_review_by_key:
                campaign_metadata_review_by_key[key] = {
                    "group_key": key,
                    "url": group.get("url"),
                    "slug": group.get("slug"),
                    "title": group.get("title"),
                    "release_date": group.get("release_date"),
                    "catalog_item_rows": group.get("catalog_item_rows", 0),
                    "missing_fields": [],
                    "review_priority": priority,
                    "sample_catalog_indexes": group.get("sample_catalog_indexes", []),
                    "sample_names": group.get("sample_names", []),
                    "source_evidence_required": "official_1kuji_campaign_page",
                    "recommended_action": "Verify official campaign page before applying missing campaign metadata.",
                }
            row = campaign_metadata_review_by_key[key]
            if field not in row["missing_fields"]:
                row["missing_fields"].append(field)
            row["review_priority"] = min(int(row.get("review_priority") or priority), priority)

    merge_campaign_metadata_review(missing_release_groups, "release_date", 10)
    merge_campaign_metadata_review(missing_price_groups, "official_price_jpy", 20)
    campaign_metadata_review_queue = sorted(
        campaign_metadata_review_by_key.values(),
        key=lambda row: (
            int(row.get("review_priority") or 99),
            -len(row.get("missing_fields") or []),
            -int(row.get("catalog_item_rows") or 0),
            str(row.get("slug") or row.get("group_key") or ""),
        ),
    )
    price_review_queue_campaigns = sum(
        1
        for row in campaign_metadata_review_queue
        if "official_price_jpy" in (row.get("missing_fields") or [])
    )
    release_review_queue_campaigns = sum(
        1
        for row in campaign_metadata_review_queue
        if "release_date" in (row.get("missing_fields") or [])
    )
    price_rows_per_campaign = (
        round(len(missing_price) / len(missing_price_groups), 2)
        if missing_price_groups
        else 0
    )
    metadata_resolution_summary = {
        "missing_release_date_rows": len(missing_release),
        "release_date_review_queue_campaigns": release_review_queue_campaigns,
        "missing_official_price_jpy_rows": len(missing_price),
        "missing_official_price_jpy_campaign_groups": len(missing_price_groups),
        "official_price_jpy_review_queue_campaigns": price_review_queue_campaigns,
        "avg_catalog_rows_per_price_campaign": price_rows_per_campaign,
        "price_patch_scope": "all_catalog_rows_for_campaign_url",
        "price_resolution_unit": "campaign_draw_price",
        "review_queue_covers_all_price_campaign_groups": (
            price_review_queue_campaigns == len(missing_price_groups)
        ),
        "guardrails": [
            "confirm draw price from the labeled official campaign page or captured official archive",
            "do not use Last One or Double Chance exception rows as draw-price evidence",
            "do not overwrite zero-price Last One or Double Chance exception rows",
            "apply confirmed draw price only to rows in the same campaign URL scope",
        ],
        "auto_apply_enabled": False,
    }
    next_review_campaign = campaign_metadata_review_queue[0] if campaign_metadata_review_queue else {}
    next_review_missing_fields = list(next_review_campaign.get("missing_fields") or [])
    metadata_resolution_readiness = {
        "status": (
            "manual_campaign_metadata_review_required"
            if campaign_metadata_review_queue
            else "metadata_complete"
        ),
        "manual_review_campaigns": len(campaign_metadata_review_queue),
        "manual_review_catalog_item_rows": sum(
            int(row.get("catalog_item_rows") or 0)
            for row in campaign_metadata_review_queue
        ),
        "release_date_review_queue_campaigns": release_review_queue_campaigns,
        "price_review_queue_campaigns": price_review_queue_campaigns,
        "missing_release_date_rows": len(missing_release),
        "missing_official_price_jpy_rows": len(missing_price),
        "review_queue_covers_all_price_campaign_groups": (
            price_review_queue_campaigns == len(missing_price_groups)
        ),
        "auto_apply_ready_campaigns": 0,
        "auto_apply_enabled": False,
        "blocked_until": "labeled_official_1kuji_campaign_metadata_confirmed",
        "blocked_reasons": (
            ["campaign_metadata_requires_labeled_official_evidence"]
            if campaign_metadata_review_queue
            else ["none"]
        ),
        "next_safe_phase": (
            "verify_labeled_official_release_date"
            if "release_date" in next_review_missing_fields
            else "verify_labeled_official_price_jpy"
            if "official_price_jpy" in next_review_missing_fields
            else "archive_ichiban_metadata_completion"
        ),
        "next_review_campaign": {
            "group_key": next_review_campaign.get("group_key"),
            "url": next_review_campaign.get("url"),
            "slug": next_review_campaign.get("slug"),
            "title": next_review_campaign.get("title"),
            "catalog_item_rows": next_review_campaign.get("catalog_item_rows"),
            "missing_fields": next_review_missing_fields,
            "review_priority": next_review_campaign.get("review_priority"),
            "sample_catalog_indexes": next_review_campaign.get("sample_catalog_indexes", []),
            "source_evidence_required": next_review_campaign.get("source_evidence_required"),
        }
        if next_review_campaign
        else {},
        "safety_note": (
            "Apply release dates and draw prices only after a labeled official 1kuji "
            "campaign page or captured official archive confirms the field for the same campaign URL."
        ),
    }

    latest_campaigns = sorted(
        campaign_rows,
        key=lambda row: str(row.get("release_date") or ""),
        reverse=True,
    )[:20]

    return {
        "schema_version": 1,
        "summary": {
            "campaign_rows": len(campaign_rows),
            "catalog_kuji_item_rows": len(kuji_items),
            "campaigns_with_catalog_items": len(campaign_with_catalog_rows),
            "campaigns_without_catalog_items": len(missing_catalog_campaigns),
            "missing_release_date_rows": len(missing_release),
            "missing_release_date_campaign_groups": len(missing_release_groups),
            "missing_official_price_jpy_rows": len(missing_price),
            "missing_official_price_jpy_campaign_groups": len(missing_price_groups),
            "official_price_jpy_review_queue_campaigns": price_review_queue_campaigns,
            "avg_missing_price_rows_per_campaign_group": price_rows_per_campaign,
            "metadata_resolution_readiness_status": metadata_resolution_readiness["status"],
            "metadata_manual_review_campaigns": metadata_resolution_readiness["manual_review_campaigns"],
            "metadata_auto_apply_ready_campaigns": 0,
            "metadata_review_queue_covers_all_price_campaign_groups": (
                price_review_queue_campaigns == len(missing_price_groups)
            ),
            "campaign_metadata_review_queue_rows": len(campaign_metadata_review_queue),
            "image_coverage": round(
                (len(kuji_items) - sum(1 for item in kuji_items if not present(item.get("image_url")))) / len(kuji_items),
                4,
            )
            if kuji_items
            else 0.0,
            "source_url_coverage": round(
                (len(kuji_items) - sum(1 for item in kuji_items if not present(item.get("source_url")))) / len(kuji_items),
                4,
            )
            if kuji_items
            else 0.0,
        },
        "campaigns_by_year": counter_rows(by_campaign_year, ("year",), 40),
        "catalog_items_by_year": counter_rows(by_item_year, ("year",), 40),
        "top_categories": counter_rows(by_category, ("category",), 40),
        "top_prize_labels": counter_rows(by_sub_series, ("sub_series",), 80),
        "top_campaigns_by_item_count": [
            {
                "url": url,
                "slug": campaign_slug(url),
                "title": campaign_by_url.get(url, {}).get("title"),
                "release_date": campaign_by_url.get(url, {}).get("release_date"),
                "catalog_item_rows": count,
            }
            for url, count in by_campaign.most_common(80)
        ],
        "latest_campaigns": latest_campaigns,
        "missing_catalog_campaign_samples": [
            {
                "url": url,
                "slug": campaign_slug(url),
                "title": campaign_by_url.get(url, {}).get("title"),
                "release_date": campaign_by_url.get(url, {}).get("release_date"),
            }
            for url in missing_catalog_campaigns[:80]
        ],
        "missing_release_date_samples": [
            {
                "catalog_index": item.get("catalog_index"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "series_name": item.get("series_name"),
                "sub_series": item.get("sub_series"),
                "source_url": item.get("source_url"),
            }
            for item in missing_release[:80]
        ],
        "missing_release_date_campaigns": missing_release_groups,
        "missing_official_price_jpy_campaigns": missing_price_groups,
        "campaign_metadata_review_queue": campaign_metadata_review_queue[:120],
        "metadata_resolution_summary": metadata_resolution_summary,
        "metadata_resolution_readiness": metadata_resolution_readiness,
        "automation_policy": {
            "auto_import_campaigns": False,
            "requires_manual_review": True,
            "reason": "Campaign-level pages and prize rows are tracked separately; missing catalog links should be reviewed before import.",
        },
    }


def build_ichiban_kuji_historical_roadmap_public(
    *,
    generated_at: str,
    ichiban_kuji_history: dict[str, Any],
    ichiban_metadata_action_queue: dict[str, Any],
    ichiban_metadata_fast_review: dict[str, Any],
    ichiban_kuji_prize_policy_issue_queue: dict[str, Any],
    deduplication_action_queue: dict[str, Any],
    name_duplicate_audit: dict[str, Any],
    ichiban_kuji_prize_name_image_review: dict[str, Any],
    ichiban_kuji_prize_name_image_patch_candidates: dict[str, Any],
) -> dict[str, Any]:
    history = ichiban_kuji_history.get("summary", {})
    metadata_resolution = ichiban_kuji_history.get("metadata_resolution_summary", {})
    metadata_action = ichiban_metadata_action_queue.get("summary", {})
    metadata_fast = ichiban_metadata_fast_review.get("summary", {})
    prize_policy = ichiban_kuji_prize_policy_issue_queue.get("summary", {})
    dedupe = deduplication_action_queue.get("summary", {})
    duplicate_names = name_duplicate_audit.get("summary", {})
    prize_name_image = ichiban_kuji_prize_name_image_review.get("summary", {})
    patch_candidates = normalize_ichiban_prize_patch_candidate_summary(
        ichiban_kuji_prize_name_image_patch_candidates
    )

    def value(summary: dict[str, Any], key: str, default: int = 0) -> int:
        raw = summary.get(key, default)
        return raw if isinstance(raw, int) else default

    phases = [
        {
            "phase": "confirm_ichiban_campaign_metadata",
            "label": "Confirm official campaign metadata",
            "rows": value(metadata_action, "actionable_campaigns")
            or value(history, "campaign_metadata_review_queue_rows"),
            "price_resolution_unit": metadata_resolution.get(
                "price_resolution_unit", "campaign_draw_price"
            ),
            "official_price_jpy_review_queue_campaigns": value(
                metadata_resolution, "official_price_jpy_review_queue_campaigns"
            ),
            "missing_official_price_jpy_rows": value(
                metadata_resolution, "missing_official_price_jpy_rows"
            ),
            "avg_missing_price_rows_per_campaign_group": metadata_resolution.get(
                "avg_catalog_rows_per_price_campaign", 0
            ),
            "blocking_reason": "Campaign release dates and draw prices must be confirmed from official campaign pages.",
            "public_reports": [
                f"data/{ICHIIBAN_KUJI_HISTORY.name}",
                f"data/{ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.name}",
                f"data/{ICHIIBAN_KUJI_METADATA_FAST_REVIEW.name}",
            ],
            "recommended_next_action": "Work release-date and official-price templates before mutating catalog metadata.",
            "guardrails": metadata_resolution.get("guardrails", []),
            "auto_apply_enabled": False,
        },
        {
            "phase": "resolve_ichiban_reissue_identity",
            "label": "Resolve reissue and campaign-variant identity",
            "rows": value(dedupe, "ichiban_reissue_work_order_rows")
            or value(prize_policy, "probable_reissue_work_order_rows"),
            "review_groups": value(dedupe, "ichiban_reissue_review_groups")
            or value(prize_policy, "probable_reissue_review_groups"),
            "blocking_reason": "Repeated names across official campaign URLs may be legitimate reissues, variants, or duplicates.",
            "public_reports": [
                f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
                f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.name}",
            ],
            "recommended_next_action": "Compare official campaign pages and mark keep/merge decisions manually.",
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
        {
            "phase": "verify_prize_policy_exceptions",
            "label": "Verify prize policy exceptions",
            "rows": value(prize_policy, "open_issue_rows") or value(prize_policy, "issue_rows"),
            "blocking_reason": "Last One and Double Chance rows should keep zero price, while numbered same-rank variants must remain represented.",
            "public_reports": [f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.name}"],
            "policy_checks": {
                "zero_price_exception_policy_pass": prize_policy.get(
                    "zero_price_exception_policy_pass", False
                ),
                "numbered_variant_coverage_policy_pass": prize_policy.get(
                    "numbered_variant_coverage_policy_pass", False
                ),
                "zero_price_violation_rows": value(prize_policy, "zero_price_violation_rows"),
            },
            "recommended_next_action": "Keep zero-price exception rows protected and review remaining same-prize-rank groups manually.",
            "auto_apply_enabled": False,
        },
        {
            "phase": "review_prize_name_image_patches",
            "label": "Review prize name and image patch candidates",
            "rows": value(patch_candidates, "open_candidate_rows")
            + value(prize_name_image, "review_rows"),
            "multi_item_prize_rank_groups": value(
                prize_name_image, "multi_item_prize_rank_groups"
            ),
            "blocking_reason": "Prize names and images must match official campaign lineup cards before any patch is applied.",
            "public_reports": [
                f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}",
                f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.name}",
            ],
            "recommended_next_action": "Confirm exact official patch candidates, then fill manual templates for blocked rows.",
            "auto_apply_enabled": False,
        },
        {
            "phase": "archive_protected_name_duplicates",
            "label": "Archive protected same-name duplicate groups",
            "rows": value(duplicate_names, "ichiban_campaign_or_reissue_protected_groups"),
            "blocking_reason": "These same-name groups are protected because campaign/reissue context may intentionally repeat product names.",
            "public_reports": [f"data/{NAME_DUPLICATE_AUDIT.name}"],
            "recommended_next_action": "Keep protected groups documented; do not merge by name alone.",
            "auto_merge_enabled": False,
            "auto_delete_enabled": False,
        },
    ]

    summary = {
        "catalog_ichiban_rows": value(history, "catalog_kuji_item_rows"),
        "campaign_rows": value(history, "campaign_rows"),
        "campaign_metadata_review_queue_rows": value(
            history, "campaign_metadata_review_queue_rows"
        ),
        "metadata_actionable_campaigns": value(metadata_action, "actionable_campaigns"),
        "metadata_queued_action_campaigns": value(
            metadata_action, "queued_action_campaigns"
        ),
        "metadata_unqueued_action_campaigns": value(
            metadata_action, "unqueued_action_campaigns"
        ),
        "metadata_fast_review_campaigns": value(metadata_fast, "fast_review_campaigns"),
        "missing_release_date_rows": value(history, "missing_release_date_rows"),
        "missing_official_price_jpy_rows": value(
            history, "missing_official_price_jpy_rows"
        ),
        "missing_official_price_jpy_campaign_groups": value(
            history, "missing_official_price_jpy_campaign_groups"
        ),
        "official_price_jpy_review_queue_campaigns": value(
            history, "official_price_jpy_review_queue_campaigns"
        ),
        "metadata_review_queue_covers_all_price_campaign_groups": history.get(
            "metadata_review_queue_covers_all_price_campaign_groups", False
        ),
        "avg_missing_price_rows_per_campaign_group": history.get(
            "avg_missing_price_rows_per_campaign_group", 0
        ),
        "probable_reissue_review_groups": value(
            prize_policy, "probable_reissue_review_groups"
        ),
        "probable_reissue_work_order_rows": value(
            prize_policy, "probable_reissue_work_order_rows"
        ),
        "dedupe_ichiban_reissue_review_groups": value(
            dedupe, "ichiban_reissue_review_groups"
        ),
        "dedupe_ichiban_reissue_work_order_rows": value(
            dedupe, "ichiban_reissue_work_order_rows"
        ),
        "repeated_name_different_source_groups": value(
            prize_policy, "repeated_name_different_source_groups"
        ),
        "name_duplicate_ichiban_protected_groups": value(
            duplicate_names, "ichiban_campaign_or_reissue_protected_groups"
        ),
        "prize_policy_issue_rows": value(prize_policy, "issue_rows"),
        "zero_price_violation_rows": value(prize_policy, "zero_price_violation_rows"),
        "zero_price_exception_policy_pass": prize_policy.get(
            "zero_price_exception_policy_pass", False
        ),
        "numbered_variant_coverage_policy_pass": prize_policy.get(
            "numbered_variant_coverage_policy_pass", False
        ),
        "prize_name_image_review_rows": value(prize_name_image, "review_rows"),
        "prize_name_image_patch_open_rows": value(
            patch_candidates, "open_candidate_rows"
        ),
        "roadmap_phase_count": len(phases),
        "completion_readiness": {
            "status": "manual_review_required",
            "manual_metadata_campaigns": value(metadata_action, "actionable_campaigns"),
            "manual_reissue_review_groups": value(
                prize_policy,
                "probable_reissue_review_groups",
            ),
            "manual_prize_name_image_patch_rows": value(
                patch_candidates,
                "open_candidate_rows",
            )
            + value(prize_name_image, "review_rows"),
            "zero_price_policy_ready": prize_policy.get(
                "zero_price_exception_policy_pass",
                False,
            )
            is True
            and value(prize_policy, "zero_price_violation_rows") == 0,
            "numbered_variant_policy_ready": prize_policy.get(
                "numbered_variant_coverage_policy_pass",
                False,
            )
            is True,
            "blocked_auto_apply_reasons": [
                "campaign_metadata_requires_official_confirmation",
                "same_name_reissue_groups_require_keep_or_merge_decisions",
                "prize_name_image_patches_require_official_lineup_confirmation",
            ],
            "next_safe_phase": "confirm_ichiban_campaign_metadata",
        },
        "auto_apply_enabled": False,
        "auto_merge_enabled": False,
        "auto_delete_enabled": False,
    }

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "summary": summary,
        "phases": phases,
        "instructions": [
            "Use this roadmap as the public manual work order for historical Ichiban Kuji cleanup.",
            "Do not delete or merge reissue-looking rows until official campaign identity is confirmed.",
            "Keep Last One and Double Chance price exceptions at zero unless official policy changes.",
            "Apply prize name/image patches only after exact official campaign lineup confirmation.",
        ],
        "inputs": {
            "ichiban_kuji_history": f"data/{ICHIIBAN_KUJI_HISTORY.name}",
            "ichiban_kuji_metadata_action_queue": f"data/{ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.name}",
            "ichiban_kuji_metadata_fast_review": f"data/{ICHIIBAN_KUJI_METADATA_FAST_REVIEW.name}",
            "ichiban_kuji_prize_policy_issue_queue": f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.name}",
            "catalog_deduplication_action_queue": f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
            "catalog_name_duplicate_audit": f"data/{NAME_DUPLICATE_AUDIT.name}",
            "ichiban_kuji_prize_name_image_review": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}",
            "ichiban_kuji_prize_name_image_patch_candidates": f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.name}",
        },
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "auto_merge_catalog_rows": False,
            "auto_delete_catalog_rows": False,
            "requires_manual_official_confirmation": True,
            "reason": "Historical Ichiban Kuji rows can repeat names across campaigns, reissues, ranks, and prize variants.",
        },
    }


def validate_public_files(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.exists():
            findings.append(f"missing:{path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            json.loads(text)
        for needle in PRIVACY_NEEDLES:
            if needle.lower() in text.lower():
                findings.append(f"{path.as_posix()} contains {needle}")
        if "???" in text:
            findings.append(f"{path.as_posix()} contains replacement placeholder ???")
    return findings


def discover_public_json_files() -> list[Path]:
    public_files = {PUBLIC_CATALOG, PUBLIC_META}
    public_files.update(DATA.glob("*_public.json"))
    return sorted(path for path in public_files if path.exists())


def validate_all_public_json_files() -> dict[str, Any]:
    public_files = discover_public_json_files()
    findings = validate_public_files(public_files)
    findings.extend(catalog_currency_invariant_findings(load_json(PUBLIC_CATALOG)))
    return {
        "checked_files": len(public_files),
        "findings": findings,
        "status": "pass" if not findings else "fail",
    }


def validate_report_consistency(
    rows: int,
    missing: dict[str, int],
    source_discovery: dict[str, Any],
    metadata_backlog: dict[str, Any],
    image_enrichment_batches: dict[str, Any],
    deduplication: dict[str, Any],
    animation_categories: dict[str, Any],
    ichiban_kuji_history: dict[str, Any],
    generic_source_patch_candidates: dict[str, Any],
    requested_focus: dict[str, Any],
    danganronpa_missing_media: dict[str, Any],
    danganronpa_patch_template_dry_run: dict[str, Any],
    operations: dict[str, Any],
    agent_work_queue: dict[str, Any],
    metadata_action_queue_override: dict[str, Any] | None = None,
    animation_review_batches_override: dict[str, Any] | None = None,
    animation_action_queue_override: dict[str, Any] | None = None,
    animation_split_review_override: dict[str, Any] | None = None,
    animation_unmatched_keyword_review_override: dict[str, Any] | None = None,
    source_next_focus_fallback_queue_override: dict[str, Any] | None = None,
    source_discovery_starter_queue_override: dict[str, Any] | None = None,
    source_discovery_action_queue_override: dict[str, Any] | None = None,
    source_discovery_focus_template_override: dict[str, Any] | None = None,
    source_discovery_focus_template_import_override: dict[str, Any] | None = None,
    source_discovery_next_focus_pack_override: dict[str, Any] | None = None,
    image_attachment_action_queue_override: dict[str, Any] | None = None,
) -> list[str]:
    findings: list[str] = []
    source_summary = source_discovery["summary"]
    metadata_summary = metadata_backlog["summary"]
    image_summary = image_enrichment_batches["summary"]
    dedupe_summary = deduplication["summary"]
    animation_summary = animation_categories["summary"]
    kuji_summary = ichiban_kuji_history["summary"]
    generic_patch_summary = generic_source_patch_candidates["summary"]
    requested_focus_summary = requested_focus["summary"]
    danganronpa_media_summary = danganronpa_missing_media["summary"]
    danganronpa_dry_run_summary = danganronpa_patch_template_dry_run["summary"]
    operations_summary = operations["summary"]
    open_queues = operations_summary["open_review_queues"]
    agent_summary = agent_work_queue["summary"]
    batches = agent_work_queue.get("batches", [])
    top_next_batches = agent_work_queue.get("top_next_batches", [])

    expected_missing = {
        "source_url": missing["source_url"],
        "image_url": missing["image_url"],
        "release_date": missing["release_date"],
        "official_price_jpy": missing["official_price_jpy"],
        "barcode": missing["barcode"],
        "name_ja": missing["name_ja"],
    }
    if operations_summary.get("catalog_rows") != rows:
        findings.append("operations.catalog_rows does not match public catalog row count")
    if operations_summary.get("missing") != expected_missing:
        findings.append("operations.missing does not match generated missing counts")

    field_totals = metadata_summary.get("field_missing_totals", {})
    for field, expected in expected_missing.items():
        if field_totals.get(field) != expected:
            findings.append(f"metadata_backlog.field_missing_totals.{field} does not match missing counts")
    field_review_queue = metadata_backlog.get("field_review_queue", [])
    if metadata_summary.get("field_review_queue_rows") != len(field_review_queue):
        findings.append("metadata_backlog.field_review_queue_rows does not match queue length")
    queue_field_totals = {row.get("field"): row.get("missing_rows") for row in field_review_queue if isinstance(row, dict)}
    for field, expected in field_totals.items():
        if queue_field_totals.get(field) != expected:
            findings.append(f"metadata_backlog.field_review_queue.{field} does not match field totals")
    required_metadata_policy_fields = {
        "field",
        "missing_rows",
        "recommended_action",
        "evidence_required",
        "auto_apply_enabled",
        "next_step",
        "risk",
        "top_source_stores",
    }
    for row in field_review_queue:
        if not isinstance(row, dict):
            findings.append("metadata_backlog.field_review_queue contains non-object row")
            continue
        missing_policy_fields = required_metadata_policy_fields - set(row)
        if missing_policy_fields:
            findings.append(f"metadata field review row missing fields: {sorted(missing_policy_fields)}")
        if row.get("auto_apply_enabled") is not False:
            findings.append(f"metadata field review row enables auto apply: {row.get('field')}")

    requested_focus_topics = requested_focus.get("topics", [])
    if requested_focus_summary.get("topic_count") != len(requested_focus_topics):
        findings.append("requested_focus.topic_count does not match topics length")
    if requested_focus_summary.get("open_rows") != sum(
        int(topic.get("open_rows") or 0) for topic in requested_focus_topics if isinstance(topic, dict)
    ):
        findings.append("requested_focus.open_rows does not match topic rows")
    if requested_focus_summary.get("auto_apply_enabled") is not False:
        findings.append("requested_focus enables auto apply")
    required_focus_fields = {
        "topic_id",
        "label",
        "priority",
        "catalog_rows",
        "open_rows",
        "next_step",
        "auto_apply_enabled",
        "review_reason",
        "sample_items",
    }
    for topic in requested_focus_topics:
        if not isinstance(topic, dict):
            findings.append("requested_focus.topics contains non-object row")
            continue
        missing_focus_fields = required_focus_fields - set(topic)
        if missing_focus_fields:
            findings.append(f"requested focus topic missing fields: {sorted(missing_focus_fields)}")
        if topic.get("auto_apply_enabled") is not False:
            findings.append(f"requested focus topic enables auto apply: {topic.get('topic_id')}")

    danganronpa_items = danganronpa_missing_media.get("items", [])
    if danganronpa_media_summary.get("missing_media_rows") != len(danganronpa_items):
        findings.append("danganronpa_missing_media.missing_media_rows does not match item length")
    if danganronpa_media_summary.get("auto_apply_enabled") is not False:
        findings.append("danganronpa_missing_media enables auto apply")
    required_danganronpa_fields = {
        "catalog_index",
        "name_ko",
        "name_ja",
        "source_store",
        "source_kind",
        "missing_fields",
        "official_search_url",
        "web_search_url",
        "allowed_source_domains",
        "evidence_required",
        "acceptance_rule",
        "auto_apply_enabled",
        "recommended_next_action",
    }
    for item in danganronpa_items:
        if not isinstance(item, dict):
            findings.append("danganronpa_missing_media.items contains non-object row")
            continue
        missing_danganronpa_fields = required_danganronpa_fields - set(item)
        if missing_danganronpa_fields:
            findings.append(f"danganronpa missing media item missing fields: {sorted(missing_danganronpa_fields)}")
        if item.get("auto_apply_enabled") is not False:
            findings.append(f"danganronpa missing media row enables auto apply: {item.get('catalog_index')}")
        if "source_url" not in item.get("missing_fields", []) or "image_url" not in item.get("missing_fields", []):
            findings.append(f"danganronpa missing media row lacks source/image missing markers: {item.get('catalog_index')}")

    if source_summary.get("source_discovery_rows") != missing["source_url"]:
        findings.append("source_discovery_rows does not match missing source_url count")
    source_items = source_discovery.get("items", [])
    source_workflow_policies = source_discovery.get("workflow_policies", {})
    if not isinstance(source_workflow_policies, dict) or not source_workflow_policies:
        findings.append("source_discovery.workflow_policies is missing")
    if source_summary.get("published_domainless_review_rows") != sum(
        1 for item in source_items if isinstance(item, dict) and not item.get("allowed_source_domains")
    ):
        findings.append("source_discovery.published_domainless_review_rows does not match published items")
    required_source_discovery_fields = {
        "priority",
        "workflow",
        "confidence",
        "row_index",
        "source_store",
        "official_search_url",
        "web_search_url",
        "allowed_source_domains",
        "evidence_required",
        "auto_apply_enabled",
        "acceptance_rule",
        "recommended_next_action",
    }
    for item in source_items:
        if not isinstance(item, dict):
            findings.append("source_discovery.items contains non-object row")
            continue
        missing_source_fields = required_source_discovery_fields - set(item)
        if missing_source_fields:
            findings.append(f"source discovery row missing fields: {sorted(missing_source_fields)}")
        if item.get("auto_apply_enabled") is not False:
            findings.append(f"source discovery row enables auto apply: {item.get('row_index')}")
    if image_summary.get("missing_image_rows") != missing["image_url"]:
        findings.append("image_enrichment missing_image_rows does not match missing image_url count")
    image_workflow_total = sum(
        int(image_summary.get(key, 0))
        for key in (
            "source_url_ready_rows",
            "generic_source_url_rows",
            "gotouchi_official_review_rows",
            "needs_source_discovery_rows",
            "manual_image_research_rows",
        )
    )
    if image_workflow_total != image_summary.get("missing_image_rows"):
        findings.append("image_enrichment workflow totals do not sum to missing_image_rows")
    blocker_summary = image_enrichment_batches.get("blocker_summary", [])
    if sum(int(row.get("rows") or 0) for row in blocker_summary if isinstance(row, dict)) != image_summary.get(
        "missing_image_rows"
    ):
        findings.append("image_enrichment blocker_summary rows do not sum to missing_image_rows")
    required_blocker_fields = {
        "workflow",
        "rows",
        "state",
        "blocking_reason",
        "next_step",
        "public_report",
    }
    for row in blocker_summary:
        if not isinstance(row, dict):
            findings.append("image_enrichment blocker_summary contains non-object row")
            continue
        missing_blocker_fields = required_blocker_fields - set(row)
        if missing_blocker_fields:
            findings.append(f"image_enrichment blocker_summary row missing fields: {sorted(missing_blocker_fields)}")

    expected_open_queues = {
        "source_discovery_rows": source_summary.get("source_discovery_rows", 0),
        "image_missing_rows": image_summary.get("missing_image_rows", 0),
        "dedupe_groups": dedupe_summary.get("duplicate_groups", 0),
        "animation_unknown_categories": animation_summary.get("unknown_category_count", 0),
        "ichiban_missing_release_date_rows": kuji_summary.get("missing_release_date_rows", 0),
        "ichiban_missing_price_rows": kuji_summary.get("missing_official_price_jpy_rows", 0),
        "generic_source_patch_candidate_rows": generic_patch_summary.get("candidate_rows", 0),
        "requested_focus_open_rows": requested_focus_summary.get("open_rows", 0),
        "danganronpa_missing_media_rows": danganronpa_media_summary.get("missing_media_rows", 0),
        "danganronpa_patch_template_pending_rows": danganronpa_dry_run_summary.get("skipped_rows", 0),
        "danganronpa_patch_template_ready_rows": danganronpa_dry_run_summary.get("ready_rows", 0),
    }
    animation_review_batches = (
        animation_review_batches_override
        if animation_review_batches_override is not None
        else load_json(ANIMATION_CATEGORY_REVIEW_BATCHES, {}) if ANIMATION_CATEGORY_REVIEW_BATCHES.exists() else {}
    )
    animation_review_summary = animation_review_batches.get("summary", {})
    requested_focus_review_batches = (
        load_json(REQUESTED_FOCUS_REVIEW_BATCHES, {}) if REQUESTED_FOCUS_REVIEW_BATCHES.exists() else {}
    )
    requested_focus_review_summary = requested_focus_review_batches.get("summary", {})
    confirmed_import_readiness = (
        load_json(CONFIRMED_IMPORT_READINESS, {}) if CONFIRMED_IMPORT_READINESS.exists() else {}
    )
    confirmed_import_readiness_summary = confirmed_import_readiness.get("summary", {})
    if confirmed_import_readiness_summary:
        expected_open_queues["confirmed_import_template_rows"] = confirmed_import_readiness_summary.get(
            "template_items", 0
        )
        expected_open_queues["confirmed_import_action_queue_rows"] = confirmed_import_readiness_summary.get(
            "public_action_queue_rows", 0
        )
        expected_open_queues["confirmed_import_pending_rows"] = confirmed_import_readiness_summary.get(
            "ready_or_pending_import_rows", 0
        )
        expected_open_queues[
            "confirmed_import_variant_metadata_template_rows"
        ] = confirmed_import_readiness_summary.get("variant_metadata_template_rows", 0)
    if requested_focus_review_summary:
        expected_open_queues["requested_focus_review_rows"] = requested_focus_review_summary.get("review_row_count", 0)
    requested_focus_action_queue = (
        load_json(REQUESTED_FOCUS_ACTION_QUEUE, {}) if REQUESTED_FOCUS_ACTION_QUEUE.exists() else {}
    )
    requested_focus_action_summary = requested_focus_action_queue.get("summary", {})
    if requested_focus_action_summary:
        expected_open_queues["requested_focus_action_rows"] = requested_focus_action_summary.get(
            "queued_action_rows", 0
        )
        expected_open_queues["requested_focus_actionable_rows"] = requested_focus_action_summary.get(
            "actionable_template_rows", 0
        )
        expected_open_queues["requested_focus_unqueued_actionable_rows"] = requested_focus_action_summary.get(
            "unqueued_actionable_rows", 0
        )
        expected_open_queues["requested_focus_barcode_template_rows_excluded"] = (
            requested_focus_action_summary.get("barcode_template_rows_excluded", 0)
        )
    source_action_queue = (
        source_discovery_action_queue_override
        if source_discovery_action_queue_override is not None
        else load_json(SOURCE_DISCOVERY_ACTION_QUEUE, {}) if SOURCE_DISCOVERY_ACTION_QUEUE.exists() else {}
    )
    source_action_summary = source_action_queue.get("summary", {})
    if source_action_summary:
        expected_open_queues["source_discovery_action_rows"] = source_action_summary.get("queued_source_rows", 0)
        expected_open_queues["source_discovery_actionable_rows"] = source_action_summary.get(
            "actionable_source_rows", 0
        )
        expected_open_queues["source_discovery_unqueued_actionable_rows"] = source_action_summary.get(
            "unqueued_actionable_source_rows", 0
        )
        expected_open_queues["source_discovery_manual_research_backlog_rows"] = (
            source_action_summary.get("manual_research_backlog_rows", 0)
        )
        expected_open_queues["source_discovery_manual_identity_backfill_required_rows"] = (
            source_action_summary.get("manual_research_identity_backfill_required_rows", 0)
        )
        expected_open_queues["source_discovery_manual_official_lookup_rows"] = (
            source_action_summary.get("manual_research_official_lookup_rows", 0)
        )
    source_focus_template = (
        source_discovery_focus_template_override
        if source_discovery_focus_template_override is not None
        else load_json(SOURCE_DISCOVERY_FOCUS_TEMPLATE, {}) if SOURCE_DISCOVERY_FOCUS_TEMPLATE.exists() else {}
    )
    source_focus_template_summary = source_focus_template.get("summary", {})
    source_focus_template_import = (
        source_discovery_focus_template_import_override
        if source_discovery_focus_template_import_override is not None
        else load_json(SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT, {})
        if SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT.exists()
        else {}
    )
    if source_focus_template_summary:
        expected_open_queues["source_discovery_focus_template_rows"] = source_focus_template_summary.get(
            "template_items", 0
        )
        expected_open_queues["source_discovery_focus_template_work_order_packs"] = (
            source_focus_template_summary.get("work_order_pack_count", 0)
        )
        expected_open_queues["source_discovery_focus_template_dry_run_skipped_rows"] = (
            source_focus_template_import.get("skipped_rows", 0)
        )
    source_next_focus_pack = (
        source_discovery_next_focus_pack_override
        if source_discovery_next_focus_pack_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_PACK.exists()
        else {}
    )
    source_next_focus_pack_summary = source_next_focus_pack.get("summary", {})
    if source_next_focus_pack_summary:
        expected_open_queues["source_discovery_next_focus_pack_rows"] = source_next_focus_pack_summary.get(
            "pack_items", 0
        )
        expected_open_queues["source_discovery_focus_pack_progress_queues"] = (
            source_next_focus_pack_summary.get("focus_pack_progress_queue_count", 0)
        )
        expected_open_queues["source_discovery_focus_pack_progress_remaining_rows"] = (
            source_next_focus_pack_summary.get("focus_pack_progress_remaining_rows", 0)
        )
    source_discovery_starter_queue = (
        source_discovery_starter_queue_override
        if source_discovery_starter_queue_override is not None
        else load_json(SOURCE_DISCOVERY_STARTER_QUEUE, {})
        if SOURCE_DISCOVERY_STARTER_QUEUE.exists()
        else {}
    )
    source_discovery_starter_summary = source_discovery_starter_queue.get("summary", {})
    if source_discovery_starter_summary:
        expected_open_queues["source_discovery_starter_queue_rows"] = source_discovery_starter_summary.get(
            "starter_queue_rows", 0
        )
        expected_open_queues["source_discovery_starter_queue_groups"] = source_discovery_starter_summary.get(
            "starter_queue_groups", 0
        )
    source_next_focus_fallback_queue = (
        source_next_focus_fallback_queue_override
        if source_next_focus_fallback_queue_override is not None
        else load_json(SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.exists()
        else {}
    )
    source_next_focus_fallback_summary = source_next_focus_fallback_queue.get("summary", {})
    if source_next_focus_fallback_summary:
        expected_open_queues["source_discovery_next_focus_fallback_rows"] = (
            source_next_focus_fallback_summary.get("queue_rows", 0)
        )
        expected_open_queues["source_discovery_next_focus_fallback_manual_confirmed_rows"] = (
            source_next_focus_fallback_summary.get("manual_confirmed_rows", 0)
        )
    source_detail_candidate_action_queue = (
        load_json(SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE, {})
        if SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.exists()
        else {}
    )
    source_detail_candidate_action_summary = source_detail_candidate_action_queue.get("summary", {})
    if source_detail_candidate_action_summary:
        expected_open_queues["source_detail_candidate_action_rows"] = (
            source_detail_candidate_action_summary.get("candidate_action_rows", 0)
        )
        expected_open_queues["source_detail_candidate_manual_confirmed_rows"] = (
            source_detail_candidate_action_summary.get("manual_confirmed_true", 0)
        )
        expected_open_queues["source_detail_candidate_manual_confirmation_shortlist_rows"] = (
            source_detail_candidate_action_summary.get("manual_confirmation_shortlist_rows", 0)
        )
        expected_open_queues["source_detail_candidate_count_review_required_rows"] = (
            source_detail_candidate_action_summary.get("candidate_count_review_required_rows", 0)
        )
        expected_open_queues["source_detail_candidate_priority_manual_review_rows"] = (
            source_detail_candidate_action_summary.get("priority_manual_review_candidate_rows", 0)
        )
    official_detail_review_batches = (
        load_json(OFFICIAL_DETAIL_REVIEW_BATCHES, {})
        if OFFICIAL_DETAIL_REVIEW_BATCHES.exists()
        else {}
    )
    official_detail_review_summary = official_detail_review_batches.get("summary", {})
    if official_detail_review_summary:
        expected_open_queues["official_detail_review_rows"] = (
            official_detail_review_summary.get("reviewable_seed_rows", 0)
        )
        expected_open_queues["official_detail_review_candidate_rows"] = (
            official_detail_review_summary.get("reviewable_candidate_rows", 0)
        )
        expected_open_queues["official_detail_review_manual_confirmed_rows"] = (
            official_detail_review_summary.get("manual_confirmed_true", 0)
        )
    ensky_cache_candidate_action_queue = (
        load_json(ENSKY_CACHE_CANDIDATE_ACTION_QUEUE, {})
        if ENSKY_CACHE_CANDIDATE_ACTION_QUEUE.exists()
        else {}
    )
    ensky_cache_candidate_action_summary = ensky_cache_candidate_action_queue.get("summary", {})
    if ensky_cache_candidate_action_summary:
        expected_open_queues["ensky_cache_candidate_action_rows"] = (
            ensky_cache_candidate_action_summary.get("candidate_action_rows", 0)
        )
        expected_open_queues["ensky_cache_candidate_manual_confirmed_rows"] = (
            ensky_cache_candidate_action_summary.get("manual_confirmed_true", 0)
        )
    metadata_action_queue = (
        metadata_action_queue_override
        if metadata_action_queue_override is not None
        else load_json(METADATA_ACTION_QUEUE, {}) if METADATA_ACTION_QUEUE.exists() else {}
    )
    metadata_action_summary = metadata_action_queue.get("summary", {})
    if metadata_action_summary:
        expected_open_queues["metadata_action_missing_cells"] = metadata_action_summary.get("queued_missing_cells", 0)
        expected_open_queues["metadata_actionable_groups"] = metadata_action_summary.get("actionable_group_count", 0)
        expected_open_queues["metadata_unqueued_actionable_groups"] = metadata_action_summary.get(
            "unqueued_actionable_group_count", 0
        )
        expected_open_queues["metadata_actionable_missing_cells"] = metadata_action_summary.get(
            "actionable_missing_cells", 0
        )
        expected_open_queues["metadata_unqueued_actionable_missing_cells"] = metadata_action_summary.get(
            "unqueued_actionable_missing_cells", 0
        )
        expected_open_queues["metadata_primary_review_url_groups"] = metadata_action_summary.get(
            "primary_review_url_groups", 0
        )
    image_action_queue = (
        image_attachment_action_queue_override
        if image_attachment_action_queue_override is not None
        else load_json(IMAGE_ATTACHMENT_ACTION_QUEUE, {})
        if IMAGE_ATTACHMENT_ACTION_QUEUE.exists()
        else {}
    )
    image_action_summary = image_action_queue.get("summary", {})
    if image_action_summary:
        expected_open_queues["image_attachment_action_rows"] = image_action_summary.get("queued_image_rows", 0)
        expected_open_queues["image_attachment_actionable_rows"] = image_action_summary.get("actionable_image_rows", 0)
        expected_open_queues["image_attachment_unqueued_actionable_rows"] = image_action_summary.get(
            "unqueued_actionable_image_rows", 0
        )
        expected_open_queues["image_attachment_source_url_search_hint_rows"] = image_action_summary.get(
            "source_url_update_search_hint_rows", 0
        )
        expected_open_queues["image_attachment_source_url_missing_search_hint_rows"] = image_action_summary.get(
            "source_url_update_missing_search_hint_rows", 0
        )
        expected_open_queues["image_attachment_source_url_fallback_web_search_rows"] = image_action_summary.get(
            "source_url_update_fallback_web_search_rows", 0
        )
        expected_open_queues["image_attachment_source_url_any_search_hint_rows"] = image_action_summary.get(
            "source_url_update_any_search_hint_rows", 0
        )
        expected_open_queues["image_attachment_source_url_missing_any_search_hint_rows"] = image_action_summary.get(
            "source_url_update_missing_any_search_hint_rows", 0
        )
        expected_open_queues["image_attachment_local_download_ready_rows"] = image_action_summary.get(
            "local_image_download_instruction_ready_rows", 0
        )
    ichiban_action_queue = (
        load_json(ICHIIBAN_KUJI_METADATA_ACTION_QUEUE, {}) if ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.exists() else {}
    )
    ichiban_action_summary = ichiban_action_queue.get("summary", {})
    if ichiban_action_summary:
        expected_open_queues["ichiban_metadata_action_campaigns"] = ichiban_action_summary.get(
            "queued_action_campaigns", 0
        )
        expected_open_queues["ichiban_metadata_actionable_campaigns"] = ichiban_action_summary.get(
            "actionable_campaigns", 0
        )
        expected_open_queues["ichiban_metadata_unqueued_action_campaigns"] = ichiban_action_summary.get(
            "unqueued_action_campaigns", 0
        )
        expected_open_queues["ichiban_metadata_queued_catalog_item_rows"] = ichiban_action_summary.get(
            "queued_catalog_item_rows", 0
        )
        expected_open_queues["ichiban_metadata_next_campaign_patch_review_batch_rows"] = (
            ichiban_action_summary.get("next_campaign_patch_review_batch_rows", 0)
        )
        expected_open_queues["ichiban_metadata_next_campaign_patch_review_batch_template_rows"] = (
            ichiban_action_summary.get("next_campaign_patch_review_batch_template_rows", 0)
        )
        expected_open_queues["ichiban_metadata_next_campaign_patch_review_batch_primary_review_url_rows"] = (
            ichiban_action_summary.get(
                "next_campaign_patch_review_batch_primary_review_url_rows", 0
            )
        )
    ichiban_prize_name_image_review = (
        load_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW, {})
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.exists()
        else {}
    )
    ichiban_prize_name_image_summary = ichiban_prize_name_image_review.get("summary", {})
    if ichiban_prize_name_image_summary:
        expected_open_queues["ichiban_prize_name_image_review_rows"] = (
            ichiban_prize_name_image_summary.get("review_rows", 0)
        )
        expected_open_queues["ichiban_prize_multi_item_rank_groups"] = (
            ichiban_prize_name_image_summary.get("multi_item_prize_rank_groups", 0)
        )
    ichiban_prize_name_image_patch_candidates = (
        load_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES, {})
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.exists()
        else {}
    )
    ichiban_prize_name_image_patch_summary = normalize_ichiban_prize_patch_candidate_summary(
        ichiban_prize_name_image_patch_candidates
    )
    if ichiban_prize_name_image_patch_summary:
        expected_open_queues["ichiban_prize_name_image_patch_candidate_rows"] = (
            ichiban_prize_name_image_patch_summary.get("open_candidate_rows", 0)
        )
        expected_open_queues["ichiban_prize_name_image_patch_manual_confirmed_rows"] = (
            ichiban_prize_name_image_patch_summary.get("manual_confirmed_rows", 0)
        )
        expected_open_queues["ichiban_prize_name_image_patch_blocked_rows"] = (
            ichiban_prize_name_image_patch_summary.get("blocked_rows", 0)
        )
    dedupe_action_queue = load_json(DEDUPLICATION_ACTION_QUEUE, {}) if DEDUPLICATION_ACTION_QUEUE.exists() else {}
    dedupe_action_summary = dedupe_action_queue.get("summary", {})
    if dedupe_action_summary:
        expected_open_queues["dedupe_action_groups"] = dedupe_action_summary.get("queued_groups", 0)
        expected_open_queues["dedupe_actionable_groups"] = dedupe_action_summary.get("actionable_groups", 0)
        expected_open_queues["dedupe_unqueued_actionable_groups"] = dedupe_action_summary.get(
            "unqueued_actionable_groups", 0
        )
        expected_open_queues["ichiban_reissue_dedupe_review_groups"] = dedupe_action_summary.get(
            "ichiban_reissue_review_groups", 0
        )
        expected_open_queues["ichiban_probable_reissue_dedupe_review_groups"] = dedupe_action_summary.get(
            "ichiban_probable_reissue_review_groups", 0
        )
    if animation_review_summary:
        expected_open_queues["animation_category_review_rows"] = animation_review_summary.get("source_rows", 0)
    animation_action_queue = (
        animation_action_queue_override
        if animation_action_queue_override is not None
        else load_json(ANIMATION_CATEGORY_ACTION_QUEUE, {}) if ANIMATION_CATEGORY_ACTION_QUEUE.exists() else {}
    )
    animation_action_summary = animation_action_queue.get("summary", {})
    if animation_action_summary:
        expected_open_queues["animation_category_action_rows"] = animation_action_summary.get("queued_catalog_rows", 0)
        expected_open_queues["animation_category_split_review_categories"] = animation_action_summary.get(
            "split_review_categories", 0
        )
        expected_open_queues["animation_category_direct_mapping_categories"] = animation_action_summary.get(
            "direct_mapping_categories", 0
        )
    animation_split_review = (
        animation_split_review_override
        if animation_split_review_override is not None
        else load_json(ANIMATION_CATEGORY_SPLIT_REVIEW, {}) if ANIMATION_CATEGORY_SPLIT_REVIEW.exists() else {}
    )
    animation_split_summary = animation_split_review.get("summary", {})
    if animation_split_summary:
        expected_open_queues["animation_category_name_split_rows"] = animation_split_summary.get(
            "affected_catalog_rows", 0
        )
        expected_open_queues["animation_category_name_split_candidates"] = animation_split_summary.get(
            "candidate_split_rules", 0
        )
        expected_open_queues["animation_category_name_split_unmatched_catalog_rows"] = (
            animation_split_summary.get("unmatched_catalog_rows", 0)
        )
    animation_unmatched_keyword_review = (
        animation_unmatched_keyword_review_override
        if animation_unmatched_keyword_review_override is not None
        else load_json(ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW, {})
        if ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.exists()
        else {}
    )
    animation_unmatched_keyword_summary = animation_unmatched_keyword_review.get("summary", {})
    if animation_unmatched_keyword_summary:
        expected_open_queues["animation_category_unmatched_keyword_rows"] = (
            animation_unmatched_keyword_summary.get("unmatched_rows", 0)
        )
        expected_open_queues["animation_category_unmatched_keyword_candidates"] = (
            animation_unmatched_keyword_summary.get("token_candidate_count", 0)
        )
        expected_open_queues["animation_category_unmatched_keyword_product_type_candidates"] = (
            animation_unmatched_keyword_summary.get("product_type_candidate_count", 0)
        )
    if open_queues != expected_open_queues:
        findings.append(
            "operations.open_review_queues does not match source report summaries: "
            + json.dumps(_dict_delta(open_queues, expected_open_queues), ensure_ascii=False, sort_keys=True)
        )
    taxonomy_review_queue = animation_categories.get("taxonomy_review_queue", [])
    unknown_categories = animation_categories.get("unknown_categories", [])
    if taxonomy_review_queue != unknown_categories:
        findings.append("animation_categories.taxonomy_review_queue does not match unknown_categories")
    if animation_summary.get("unknown_category_rows") != sum(
        int(row.get("rows") or 0) for row in taxonomy_review_queue if isinstance(row, dict)
    ):
        findings.append("animation_categories.unknown_category_rows does not match taxonomy review queue")
    for row in taxonomy_review_queue:
        if not isinstance(row, dict):
            findings.append("animation_categories.taxonomy_review_queue contains non-object row")
            continue
        required_taxonomy_fields = {
            "category",
            "rows",
            "review_priority",
            "suggested_family",
            "suggested_category",
            "suggested_color_hint",
            "suggested_color_hex",
            "suggested_primary_icon_key",
            "suggested_icon_options",
            "review_reason",
        }
        missing_taxonomy_fields = required_taxonomy_fields - set(row)
        if missing_taxonomy_fields:
            findings.append(f"animation taxonomy row missing fields: {sorted(missing_taxonomy_fields)}")

    campaign_metadata_review_queue = ichiban_kuji_history.get("campaign_metadata_review_queue", [])
    if kuji_summary.get("campaign_metadata_review_queue_rows") != len(campaign_metadata_review_queue):
        findings.append("ichiban_kuji_history.campaign_metadata_review_queue_rows does not match queue")
    for row in campaign_metadata_review_queue:
        if not isinstance(row, dict):
            findings.append("ichiban_kuji_history.campaign_metadata_review_queue contains non-object row")
            continue
        required_campaign_fields = {
            "group_key",
            "slug",
            "title",
            "catalog_item_rows",
            "missing_fields",
            "review_priority",
            "source_evidence_required",
            "recommended_action",
        }
        missing_campaign_fields = required_campaign_fields - set(row)
        if missing_campaign_fields:
            findings.append(f"ichiban metadata review row missing fields: {sorted(missing_campaign_fields)}")
        if not isinstance(row.get("missing_fields"), list) or not row.get("missing_fields"):
            findings.append("ichiban metadata review row has no missing_fields")

    store_matrix = operations.get("store_priority_matrix", [])
    workstream_scorecard = operations.get("workstream_scorecard", [])
    required_scorecard_fields = {
        "workstream",
        "status",
        "open_rows",
        "primary_report",
        "next_step",
        "auto_apply_enabled",
    }
    if not isinstance(workstream_scorecard, list) or not workstream_scorecard:
        findings.append("operations.workstream_scorecard is missing")
    for row in workstream_scorecard:
        if not isinstance(row, dict):
            findings.append("operations.workstream_scorecard contains non-object row")
            continue
        missing_scorecard_fields = required_scorecard_fields - set(row)
        if missing_scorecard_fields:
            findings.append(f"operations scorecard row missing fields: {sorted(missing_scorecard_fields)}")
        if row.get("auto_apply_enabled") is not False:
            findings.append(f"operations scorecard enables auto apply: {row.get('workstream')}")
        if int(row.get("open_rows") or 0) < 0:
            findings.append(f"operations scorecard has negative open_rows: {row.get('workstream')}")

    if store_matrix:
        scores = [row.get("priority_score", 0) for row in store_matrix]
        if scores != sorted(scores, reverse=True):
            findings.append("operations.store_priority_matrix is not sorted by descending priority_score")
        if operations_summary.get("top_store_priority_score") != store_matrix[0].get("priority_score"):
            findings.append("operations.top_store_priority_score does not match first store priority")

    if agent_summary.get("open_review_queues") != expected_open_queues:
        findings.append(
            "agent_work_queue.open_review_queues does not match source report summaries: "
            + json.dumps(
                _dict_delta(agent_summary.get("open_review_queues") or {}, expected_open_queues),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    if agent_summary.get("batch_count") != len(batches):
        findings.append("agent_work_queue.batch_count does not match published batches")
    if agent_summary.get("top_next_batch_count") != len(top_next_batches):
        findings.append("agent_work_queue.top_next_batch_count does not match top_next_batches")
    if agent_summary.get("summed_batch_rows") != sum(int(batch.get("rows", 0)) for batch in batches):
        findings.append("agent_work_queue.summed_batch_rows does not match published batches")
    if agent_summary.get("by_workstream") != Counter(str(batch.get("workstream") or "") for batch in batches).most_common():
        findings.append("agent_work_queue.by_workstream does not match published batches")
    if agent_summary.get("by_agent") != Counter(str(batch.get("agent_id") or "") for batch in batches).most_common():
        findings.append("agent_work_queue.by_agent does not match published batches")
    confirmed_template_rows = int(confirmed_import_readiness_summary.get("template_items") or 0)
    confirmed_action_rows = int(confirmed_import_readiness_summary.get("public_action_queue_rows") or 0)
    confirmed_ready_rows = int(confirmed_import_readiness_summary.get("manual_confirmed_true") or 0)
    expected_confirmation_backlog = max(confirmed_template_rows + confirmed_action_rows - confirmed_ready_rows, 0)
    agent_confirmation_fields = {
        "confirmed_import_template_rows": confirmed_template_rows,
        "confirmed_import_action_queue_rows": confirmed_action_rows,
        "confirmed_import_manual_confirmed_ready_rows": confirmed_ready_rows,
        "confirmed_import_pending_rows": int(confirmed_import_readiness_summary.get("ready_or_pending_import_rows") or 0),
        "confirmed_import_blocked_confirmed_rows": int(confirmed_import_readiness_summary.get("blocked_confirmed_rows") or 0),
        "confirmed_import_variant_metadata_template_rows": int(
            confirmed_import_readiness_summary.get("variant_metadata_template_rows") or 0
        ),
        "confirmed_import_variant_metadata_manual_confirmed_rows": int(
            confirmed_import_readiness_summary.get("variant_metadata_manual_confirmed_rows") or 0
        ),
        "confirmed_import_variant_metadata_skipped_rows": int(
            confirmed_import_readiness_summary.get("variant_metadata_skipped_rows") or 0
        ),
        "confirmed_import_manual_confirmation_backlog_rows": expected_confirmation_backlog,
        "confirmed_import_work_order_lanes": int(confirmed_import_readiness_summary.get("work_order_lanes") or 0),
        "confirmed_import_top_work_order_lane": confirmed_import_readiness_summary.get("top_work_order_lane"),
        "confirmed_import_top_work_order_workflow": confirmed_import_readiness_summary.get("top_work_order_workflow"),
        "confirmed_import_top_work_order_row_count": int(
            confirmed_import_readiness_summary.get("top_work_order_row_count") or 0
        ),
    }
    for field, expected in agent_confirmation_fields.items():
        if agent_summary.get(field) != expected:
            findings.append(f"agent_work_queue.{field} does not match confirmed import readiness")
    batch_priorities = [int(batch.get("priority", 999)) for batch in batches]
    if batch_priorities != sorted(batch_priorities):
        findings.append("agent_work_queue.batches are not sorted by ascending priority")
    expected_top_next_batches = [
        {
            "batch_id": batch["batch_id"],
            "agent_id": batch["agent_id"],
            "workstream": batch["workstream"],
            "priority": batch["priority"],
            "rows": batch["rows"],
            "title": batch["title"],
            "public_report": batch["public_report"],
            "review_state": batch["review_state"],
            "next_machine_step": batch["next_machine_step"],
            **({"review_summary": batch["review_summary"]} if "review_summary" in batch else {}),
        }
        for batch in batches[:10]
    ]
    if top_next_batches != expected_top_next_batches:
        findings.append("agent_work_queue.top_next_batches does not match first published batches")
    seen_batch_ids: set[str] = set()
    allowed_reports = {
        f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
        f"data/{SOURCE_DISCOVERY_ACTION_QUEUE.name}",
        f"data/{SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.name}",
        f"data/{SOURCE_DISCOVERY.name}",
        f"data/{SOURCE_DISCOVERY_REVIEW_BATCHES.name}",
        f"data/{SOURCE_DISCOVERY_STARTER_QUEUE.name}",
        f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK.name}",
        f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.name}",
        f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.name}",
        f"data/{METADATA_BACKLOG.name}",
        f"data/{METADATA_REVIEW_BATCHES.name}",
        f"data/{METADATA_ACTION_QUEUE.name}",
        f"data/{CONFIRMED_IMPORT_READINESS.name}",
        f"data/{DEDUPLICATION.name}",
        f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
        f"data/{ANIMATION_CATEGORIES.name}",
        f"data/{ANIMATION_CATEGORY_REVIEW_BATCHES.name}",
        f"data/{ANIMATION_CATEGORY_ACTION_QUEUE.name}",
        f"data/{ANIMATION_CATEGORY_SPLIT_REVIEW.name}",
        f"data/{ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.name}",
        f"data/{ICHIIBAN_KUJI_HISTORY.name}",
        f"data/{ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES.name}",
        f"data/{ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.name}",
        f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.name}",
        f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.name}",
        f"data/{ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE.name}",
        f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}",
        f"data/{ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.name}",
        f"data/{GENERIC_SOURCE.name}",
        f"data/{GOTOUCHI.name}",
        f"data/{REQUESTED_FOCUS.name}",
        f"data/{REQUESTED_FOCUS_REVIEW_BATCHES.name}",
        f"data/{REQUESTED_FOCUS_ACTION_QUEUE.name}",
        f"data/{IMAGE_ATTACHMENT_ACTION_QUEUE.name}",
        f"data/{DANGANRONPA_MISSING_MEDIA.name}",
        f"data/{DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.name}",
    }
    required_batch_fields = {
        "batch_id",
        "agent_id",
        "workstream",
        "priority",
        "title",
        "public_report",
        "rows",
        "recommended_action",
        "acceptance_criteria",
        "sample_items",
        "review_state",
        "next_machine_step",
    }
    allowed_review_states = {
        "manual_confirmed_candidates_ready",
        "candidate_review_required",
        "exact_source_discovery_required",
        "official_exact_candidate_review_required",
        "official_candidate_mismatch_review_required",
        "source_discovery_then_image_attachment",
        "image_evidence_confirmation_required",
        "source_and_image_evidence_required",
        "source_evidence_confirmation_required",
        "metadata_evidence_required",
        "manual_metadata_evidence_confirmation_required",
        "manual_dedupe_action_confirmation_required",
        "manual_dedupe_review_required",
        "official_campaign_evidence_required",
        "manual_official_campaign_metadata_confirmation_required",
        "manual_official_prize_variant_confirmation_required",
        "manual_prize_name_structure_confirmation_required",
        "manual_prize_image_patch_confirmation_required",
        "taxonomy_mapping_required",
        "manual_category_mapping_confirmation_required",
        "manual_name_level_split_confirmation_required",
        "manual_keyword_candidate_review_required",
        "manual_review_required",
    }
    allowed_next_machine_steps = {
        "prepare_reviewed_catalog_patch",
        "open_candidate_report_and_verify_exact_product_identity",
        "find_exact_official_product_source_url",
        "verify_official_candidate_image_matches_row_type",
        "review_official_candidates_before_import",
        "find_source_url_before_image_import",
        "confirm_source_then_fill_image_url_templates",
        "confirm_exact_source_then_fill_image_url_templates",
        "confirm_exact_source_url_then_fill_source_templates",
        "collect_official_metadata_evidence",
        "fill_confirmed_metadata_patch_templates",
        "confirm_manual_keep_drop_dedupe_decisions",
        "compare_duplicate_group_evidence",
        "verify_ichiban_campaign_page",
        "fill_confirmed_ichiban_campaign_patch_templates",
        "verify_ichiban_prize_variants_against_campaign_lineup",
        "confirm_ichiban_prize_name_structure_templates",
        "confirm_ichiban_prize_image_patch_templates",
        "map_category_to_folder_color_and_icon",
        "fill_confirmed_animation_category_mapping_templates",
        "confirm_animation_category_name_split_templates",
        "review_unmatched_animation_keyword_candidates",
        "manual_review",
    }
    for batch in batches:
        missing_fields = required_batch_fields - set(batch)
        if missing_fields:
            findings.append(f"agent_work_queue batch missing fields: {sorted(missing_fields)}")
            continue
        batch_id = str(batch.get("batch_id") or "")
        if batch_id in seen_batch_ids:
            findings.append(f"agent_work_queue duplicate batch_id: {batch_id}")
        seen_batch_ids.add(batch_id)
        if batch.get("public_report") not in allowed_reports:
            findings.append(f"agent_work_queue has unsupported public_report: {batch.get('public_report')}")
        if int(batch.get("rows") or 0) <= 0:
            findings.append(f"agent_work_queue batch has non-positive rows: {batch_id}")
        if not isinstance(batch.get("acceptance_criteria"), list) or not batch.get("acceptance_criteria"):
            findings.append(f"agent_work_queue batch missing acceptance criteria: {batch_id}")
        if not isinstance(batch.get("sample_items"), list):
            findings.append(f"agent_work_queue batch sample_items is not a list: {batch_id}")
        if batch.get("review_state") not in allowed_review_states:
            findings.append(f"agent_work_queue batch has unsupported review_state: {batch_id}")
        if batch.get("next_machine_step") not in allowed_next_machine_steps:
            findings.append(f"agent_work_queue batch has unsupported next_machine_step: {batch_id}")
        if batch.get("workstream") in {"generic_source_url_cleanup", "gotouchi_official_candidate_review"}:
            review_summary = batch.get("review_summary")
            if not isinstance(review_summary, dict) or not review_summary:
                findings.append(f"agent_work_queue batch missing review_summary: {batch_id}")
            elif any(not isinstance(value, int) or value < 0 for value in review_summary.values()):
                findings.append(f"agent_work_queue batch review_summary has invalid counts: {batch_id}")

    return findings


def build_public_catalog_crosscheck(items: list[dict[str, Any]]) -> dict[str, Any]:
    public_summary = audit_public_catalog_safety.summarize_seed(items)
    public_compact = {
        "path": f"data/{PUBLIC_CATALOG.name}",
        "exists": True,
        "rows": public_summary["rows"],
        "duplicate_groups": public_summary["duplicate_groups"],
        "duplicate_rows": public_summary["duplicate_rows"],
        "missing_enrichment": public_summary["missing_enrichment"],
    }
    seed_path = audit_public_catalog_safety.DEFAULT_SEED
    if not seed_path.exists():
        return {
            "public_catalog": public_compact,
            "seed_catalog": {
                "path": seed_path.relative_to(ROOT).as_posix(),
                "exists": False,
            },
            "comparison": {
                "same_row_count": False,
                "row_delta": public_summary["rows"],
                "public_image_missing_rows": public_summary["missing_enrichment"].get("image_url", 0),
                "seed_image_missing_rows": None,
                "image_missing_delta": None,
                "note": "data/catalog_public.json is the GitHub Pages source of truth; local seed export was not present.",
            },
        }

    seed_rows = audit_public_catalog_safety.load_json(seed_path)
    if not isinstance(seed_rows, list):
        seed_rows = []
    seed_summary = audit_public_catalog_safety.summarize_seed(
        [row for row in seed_rows if isinstance(row, dict)]
    )
    seed_compact = {
        "path": seed_path.relative_to(ROOT).as_posix(),
        "exists": True,
        "rows": seed_summary["rows"],
        "duplicate_groups": seed_summary["duplicate_groups"],
        "duplicate_rows": seed_summary["duplicate_rows"],
        "missing_enrichment": seed_summary["missing_enrichment"],
    }
    return {
        "public_catalog": public_compact,
        "seed_catalog": seed_compact,
        "comparison": audit_public_catalog_safety.compare_public_catalog(public_compact, seed_summary),
    }


def update_reports(write: bool) -> dict[str, Any]:
    catalog = load_json(PUBLIC_CATALOG)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("items"), list):
        raise ValueError("data/catalog_public.json must have an items list")

    items: list[dict[str, Any]] = catalog["items"]
    rows = len(items)
    missing = missing_counts(items)
    cov = coverage(missing, rows, ["source_url", "image_url", "release_date"])
    public_catalog_crosscheck = build_public_catalog_crosscheck(items)
    generated_at = now_utc()
    source_discovery = build_source_discovery_public(items)
    metadata_backlog = build_metadata_backlog_public(items)
    metadata_review_batches = build_metadata_review_batches_public(items, generated_at)
    from build_metadata_action_queue_public import build_report as build_metadata_action_queue_report

    metadata_action_queue = build_metadata_action_queue_report(metadata_review_batches)
    image_enrichment_batches = build_image_enrichment_batches_public(items)
    deduplication = build_deduplication_public(items)
    name_duplicate_audit = build_name_duplicate_audit_public(items)
    deduplication_confirmed_template = (
        load_json(DEDUPLICATION_CONFIRMED_TEMPLATE, {})
        if DEDUPLICATION_CONFIRMED_TEMPLATE.exists()
        else {"items": []}
    )
    deduplication_template_import_dry_run = build_deduplication_template_import_dry_run_public(
        deduplication_confirmed_template,
        catalog,
        generated_at,
    )
    animation_categories = build_animation_categories_public(items)
    animation_category_coverage_audit = build_animation_category_coverage_audit_public(
        animation_categories,
        generated_at,
    )
    animation_review_queue = [
        row
        for row in (
            animation_categories.get("taxonomy_review_queue")
            or animation_categories.get("unknown_categories")
            or []
        )
        if isinstance(row, dict)
    ]
    animation_review_batches = build_animation_category_review_batches_public.build_report(
        animation_categories,
        animation_review_queue,
    )
    animation_action_queue = build_animation_category_action_queue_public.build_queue(
        animation_review_batches,
        normalization_review=animation_categories,
    )
    animation_split_review = build_animation_category_split_review_public.build_report(
        animation_action_queue,
        catalog,
    )
    animation_unmatched_keyword_review = (
        build_animation_category_unmatched_keyword_review_public.build_report(
            animation_split_review,
            catalog,
        )
    )
    animation_action_queue = build_animation_category_action_queue_public.build_queue(
        animation_review_batches,
        unmatched_keyword_review=animation_unmatched_keyword_review,
        normalization_review=animation_categories,
    )
    ichiban_kuji_history = build_ichiban_kuji_history_public(items)
    ichiban_metadata_review_batches = load_json(
        ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES,
        {},
    )
    ichiban_metadata_action_queue = (
        build_ichiban_kuji_metadata_action_queue_public.build_report(
            ichiban_metadata_review_batches,
            max_campaigns=64,
            batch_size=8,
        )
        if ichiban_metadata_review_batches
        else {}
    )
    ichiban_metadata_fast_review = (
        build_ichiban_kuji_metadata_fast_review_public.build_report(
            ichiban_metadata_action_queue,
            generated_at=generated_at,
        )
        if ichiban_metadata_action_queue
        else {}
    )
    ichiban_kuji_prize_name_image_review = build_ichiban_prize_name_image_review_public.build_report(
        catalog,
        generated_at=generated_at,
    )
    ichiban_kuji_prize_name_image_patch_candidates = (
        build_ichiban_prize_name_image_patch_candidates_public.build_report(
            ichiban_kuji_prize_name_image_review,
            generated_at=generated_at,
        )
    )
    generic_source_patch_candidates = build_generic_source_patch_candidates_public(generated_at)
    requested_report = load_json(REQUESTED, {}) if REQUESTED.exists() else {}
    requested_focus = build_requested_focus_enrichment_public(items, requested_report, generated_at)
    requested_focus_review_batches = load_json(REQUESTED_FOCUS_REVIEW_BATCHES, {})
    requested_focus_action_queue = build_requested_focus_action_queue_public.build_report(
        requested_focus_review_batches,
        generated_at=generated_at,
    )
    requested_focus_next_work = build_requested_focus_next_work_public.build_report(
        requested_focus_action_queue,
        generated_at=generated_at,
    )
    danganronpa_missing_media = build_danganronpa_missing_media_public(items, generated_at)
    danganronpa_patch_template_dry_run = build_danganronpa_patch_template_dry_run_public(
        danganronpa_missing_media,
        generated_at,
    )
    image_asset_audit = audit_public_catalog_image_assets.build_report(catalog, generated_at=generated_at)
    missing_image_priority = build_missing_image_priority_public.build_report(
        catalog,
        load_json(DATA / "catalog_missing_image_work_queue_public.json", {"items": []}),
        generated_at=generated_at,
    )
    source_discovery_starter_queue = build_missing_image_priority_public.build_starter_queue_report(
        missing_image_priority,
        generated_at=generated_at,
    )
    missing_image_report_coverage = build_missing_image_report_coverage_public.build_report(
        catalog,
        load_json(DATA / "catalog_missing_image_work_queue_public.json", {"items": []}),
        generated_at=generated_at,
    )
    ensky_cache_coverage = load_json(ENSKY_CACHE_COVERAGE, {}) if ENSKY_CACHE_COVERAGE.exists() else {}
    ensky_cache_candidate_action_queue = build_ensky_cache_candidate_action_queue_public.build_report(
        ensky_cache_coverage,
        generated_at=generated_at,
    )
    patch_candidate_items = generic_source_patch_candidates.get("items", [])
    patch_candidate_summary = generic_source_patch_candidates.get("summary", {})
    if patch_candidate_summary.get("candidate_rows") != len(patch_candidate_items):
        raise ValueError("generic source patch candidate count does not match item count")
    if patch_candidate_summary.get("auto_apply_enabled") is not False:
        raise ValueError("generic source patch candidates must stay manual-review only")
    image_attachment_action_queue = build_image_attachment_action_queue_public.build_report(
        image_enrichment_batches,
        {"items": items},
        load_json(GOTOUCHI, {}) if GOTOUCHI.exists() else None,
    )
    existing_image_attachment_action_queue = (
        load_json(IMAGE_ATTACHMENT_ACTION_QUEUE, {})
        if IMAGE_ATTACHMENT_ACTION_QUEUE.exists()
        else {}
    )
    image_source_url_confirmed_template = build_image_source_url_confirmed_template_public.build_template(
        image_attachment_action_queue,
        load_json(STELLIVE_FANDING_CANDIDATES, {}) if STELLIVE_FANDING_CANDIDATES.exists() else None,
        generated_at=generated_at,
    )
    image_attachment_action_queue = enrich_image_action_queue_source_url_review(
        image_attachment_action_queue,
        image_source_url_confirmed_template,
        existing_action_queue=existing_image_attachment_action_queue,
    )
    image_attachment_confirmed_template = (
        load_json(IMAGE_ATTACHMENT_CONFIRMED_TEMPLATE, {})
        if IMAGE_ATTACHMENT_CONFIRMED_TEMPLATE.exists()
        else {"items": []}
    )
    image_attachment_template_import_dry_run = build_image_attachment_template_import_dry_run_public(
        image_attachment_confirmed_template,
        catalog,
        generated_at,
    )
    manual_source_url_search_queue = build_manual_source_url_search_queue_public.build_queue(
        image_source_url_confirmed_template,
        generated_at=generated_at,
    )
    provider_missing_source_url_queue = build_provider_missing_source_url_queue_public.build_queue(
        image_source_url_confirmed_template,
        generated_at=generated_at,
    )
    candidate_source_url_review_queue = build_candidate_source_url_review_queue_public.build_queue(
        image_source_url_confirmed_template,
        generated_at=generated_at,
    )
    gotouchi_official_candidate_review_queue = (
        build_gotouchi_official_candidate_review_queue_public.build_queue(
            image_attachment_action_queue,
            load_json(GOTOUCHI, {}) if GOTOUCHI.exists() else {"items": []},
            generated_at=generated_at,
        )
    )
    ichiban_prize_policy_audit_source = (
        load_json(ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT, {})
        if ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.exists()
        else {}
    )
    deduplication_action_queue = build_deduplication_action_queue_public.build_report(
        load_json(DEDUPLICATION_REVIEW_BATCHES, {})
        if DEDUPLICATION_REVIEW_BATCHES.exists()
        else {},
        max_groups=100,
        batch_size=10,
        ichiban_policy_audit=ichiban_prize_policy_audit_source,
    )
    deduplication_fast_review = build_deduplication_fast_review_public.build_report(
        deduplication_action_queue,
        generated_at=generated_at,
    )
    ichiban_kuji_prize_policy_issue_queue = (
        build_ichiban_prize_policy_issue_queue_public.build_queue(
            ichiban_prize_policy_audit_source,
            deduplication_action_queue,
            generated_at=generated_at,
        )
    )
    ichiban_kuji_reissue_deduplication = (
        build_ichiban_reissue_deduplication_summary_public.build_report(
            load_json(ICHIIBAN_KUJI_REISSUE_DEDUPLICATION, {})
            if ICHIIBAN_KUJI_REISSUE_DEDUPLICATION.exists()
            else {"groups": []},
            asset_root=ROOT,
        )
    )
    ichiban_kuji_reissue_decision_template = (
        build_ichiban_reissue_decision_template_public.build_report(
            deduplication_action_queue,
            generated_at=generated_at,
        )
    )
    ichiban_kuji_historical_roadmap = build_ichiban_kuji_historical_roadmap_public(
        generated_at=generated_at,
        ichiban_kuji_history=ichiban_kuji_history,
        ichiban_metadata_action_queue=ichiban_metadata_action_queue,
        ichiban_metadata_fast_review=ichiban_metadata_fast_review,
        ichiban_kuji_prize_policy_issue_queue=ichiban_kuji_prize_policy_issue_queue,
        deduplication_action_queue=deduplication_action_queue,
        name_duplicate_audit=name_duplicate_audit,
        ichiban_kuji_prize_name_image_review=ichiban_kuji_prize_name_image_review,
        ichiban_kuji_prize_name_image_patch_candidates=ichiban_kuji_prize_name_image_patch_candidates,
    )
    import build_source_discovery_action_queue_public
    import build_source_discovery_focus_confirmed_template_public
    import build_source_discovery_focus_packs_public
    import build_source_discovery_review_batches_public
    import build_source_discovery_store_bottlenecks_public

    source_discovery_review_batches = build_source_discovery_review_batches_public.build_report(
        items,
        batch_size=25,
    )
    source_discovery_action_queue = build_source_discovery_action_queue_public.build_report(
        source_discovery_review_batches,
    )
    source_discovery_store_bottlenecks = build_source_discovery_store_bottlenecks_public.build_report(
        source_discovery_action_queue,
        generated_at=generated_at,
    )
    source_discovery_focus_packs = build_source_discovery_focus_packs_public.build_report(
        source_discovery_action_queue,
        source_discovery_store_bottlenecks,
        generated_at=generated_at,
    )
    source_discovery_focus_template = build_source_discovery_focus_confirmed_template_public.build_template(
        source_discovery_focus_packs,
        generated_at=generated_at,
    )
    source_discovery_focus_template_import = build_source_discovery_import_dry_run_public(
        source_discovery_focus_template,
        items,
        queue_path=SOURCE_DISCOVERY_FOCUS_TEMPLATE,
    )
    source_discovery_next_focus_pack = build_source_discovery_next_focus_pack_public.build_report(
        source_discovery_focus_template,
        generated_at=generated_at,
    )
    source_discovery_next_focus_pack_import = build_source_discovery_import_dry_run_public(
        source_discovery_next_focus_pack,
        items,
        queue_path=SOURCE_DISCOVERY_NEXT_FOCUS_PACK,
    )
    existing_source_discovery_next_focus_fetch_audit = (
        load_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT, {})
        if SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.exists()
        else {}
    )
    source_discovery_next_focus_fetch_audit = (
        existing_source_discovery_next_focus_fetch_audit
        if fetch_audit_matches_focus_pack(
            existing_source_discovery_next_focus_fetch_audit,
            source_discovery_next_focus_pack,
        )
        else build_source_discovery_next_focus_pack_fetch_audit_public.build_report(
            source_discovery_next_focus_pack,
            generated_at=generated_at,
        )
    )
    source_discovery_next_focus_fallback_queue = (
        build_source_discovery_next_focus_fallback_queue_public.build_report(
            source_discovery_next_focus_pack,
            source_discovery_next_focus_fetch_audit,
            generated_at=generated_at,
        )
    )
    source_discovery_next_focus_detail_candidates = (
        build_source_discovery_next_focus_detail_candidates_public.build_report(
            source_discovery_next_focus_pack,
            fetch_audit=source_discovery_next_focus_fetch_audit,
            fallback_queue=source_discovery_next_focus_fallback_queue,
            generated_at=generated_at,
        )
    )
    source_discovery_next_focus_metadata_field_import = build_metadata_field_import_dry_run_public(
        source_discovery_next_focus_detail_candidates,
        items,
        generated_at,
        queue_path=SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES,
    )
    (
        source_discovery_next_focus_exact_url_queue,
        source_discovery_next_focus_identity_backfill_queue,
    ) = build_source_discovery_next_focus_split_queues_public.build_reports(
        source_discovery_next_focus_fallback_queue,
        generated_at=generated_at,
    )
    source_discovery_next_focus_identity_candidate_review_queue = (
        build_source_discovery_next_focus_identity_candidate_review_public.build_report(
            source_discovery_next_focus_identity_backfill_queue,
            generated_at=generated_at,
        )
    )
    source_discovery_next_focus_fallback_import = build_source_discovery_import_dry_run_public(
        source_discovery_next_focus_fallback_queue,
        items,
        queue_path=SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE,
    )
    missing_image_actionability = build_catalog_missing_image_actionability_public.build_report(
        image_enrichment_batches,
        image_attachment_action_queue,
        load_json(SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE, {}) if SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.exists() else {},
        source_discovery_focus_packs,
        source_discovery_focus_template,
        source_discovery_focus_template_import,
        image_attachment_confirmed_template,
        image_attachment_template_import_dry_run,
        source_discovery_next_focus_detail_candidates=source_discovery_next_focus_detail_candidates,
        source_discovery_next_focus_fallback_queue=source_discovery_next_focus_fallback_queue,
        source_discovery_next_focus_exact_url_queue=source_discovery_next_focus_exact_url_queue,
        source_discovery_next_focus_identity_backfill_queue=source_discovery_next_focus_identity_backfill_queue,
        generated_at=generated_at,
    )
    source_discovery_completion_roadmap = build_source_discovery_completion_roadmap_public(
        generated_at=generated_at,
        missing_image_actionability=missing_image_actionability,
        source_discovery_action_queue=source_discovery_action_queue,
        source_discovery_store_bottlenecks=source_discovery_store_bottlenecks,
        source_discovery_focus_packs=source_discovery_focus_packs,
        source_discovery_next_focus_pack=source_discovery_next_focus_pack,
        source_discovery_next_focus_fallback_queue=source_discovery_next_focus_fallback_queue,
        manual_source_url_search_queue=manual_source_url_search_queue,
        provider_missing_source_url_queue=provider_missing_source_url_queue,
        candidate_source_url_review_queue=candidate_source_url_review_queue,
        image_attachment_action_queue=image_attachment_action_queue,
    )
    operations = build_operations_public(
        generated_at,
        items,
        rows,
        missing,
        cov,
        source_discovery,
        metadata_backlog,
        image_enrichment_batches,
        deduplication,
        animation_categories,
        ichiban_kuji_history,
        generic_source_patch_candidates,
        requested_focus,
        danganronpa_missing_media,
        danganronpa_patch_template_dry_run,
        image_asset_audit,
        metadata_review_batches_override=metadata_review_batches,
        metadata_action_queue_override=metadata_action_queue,
        ichiban_prize_name_image_review_override=ichiban_kuji_prize_name_image_review,
        ichiban_prize_name_image_patch_candidates_override=ichiban_kuji_prize_name_image_patch_candidates,
        source_next_focus_pack_override=source_discovery_next_focus_pack,
        source_next_focus_detail_candidates_override=source_discovery_next_focus_detail_candidates,
        source_next_focus_metadata_field_import_override=source_discovery_next_focus_metadata_field_import,
        source_next_focus_fallback_queue_override=source_discovery_next_focus_fallback_queue,
        source_discovery_action_queue_override=source_discovery_action_queue,
        source_discovery_focus_template_override=source_discovery_focus_template,
        source_discovery_focus_template_import_override=source_discovery_focus_template_import,
        deduplication_template_import_dry_run_override=deduplication_template_import_dry_run,
        animation_review_batches_override=animation_review_batches,
        animation_action_queue_override=animation_action_queue,
        animation_split_review_override=animation_split_review,
        animation_unmatched_keyword_review_override=animation_unmatched_keyword_review,
        ichiban_reissue_decision_template_override=ichiban_kuji_reissue_decision_template,
        source_discovery_starter_queue_override=source_discovery_starter_queue,
        image_attachment_action_queue_override=image_attachment_action_queue,
        ensky_cache_candidate_action_queue_override=ensky_cache_candidate_action_queue,
        requested_focus_action_queue_override=requested_focus_action_queue,
        requested_focus_next_work_override=requested_focus_next_work,
        deduplication_action_queue_override=deduplication_action_queue,
    )
    agent_work_queue = build_agent_work_queue_public(
        generated_at,
        source_discovery,
        metadata_backlog,
        image_enrichment_batches,
        deduplication,
        animation_categories,
        ichiban_kuji_history,
        operations,
        requested_focus,
        danganronpa_missing_media,
        metadata_review_batches,
        metadata_action_queue,
        animation_review_batches,
        animation_action_queue,
        animation_split_review,
        animation_unmatched_keyword_review,
        source_discovery_next_focus_pack,
        source_discovery_next_focus_detail_candidates,
        source_discovery_next_focus_metadata_field_import,
        source_discovery_next_focus_fallback_queue,
        source_discovery_starter_queue,
        requested_focus_action_queue,
        image_attachment_action_queue,
        deduplication_action_queue,
        ichiban_kuji_prize_policy_issue_queue,
    )
    from build_catalog_execution_plan_public import build_plan_from_reports

    execution_plan = build_plan_from_reports(
        {
            "catalog_operations_public.json": operations,
            "catalog_image_enrichment_batches_public.json": image_enrichment_batches,
            "catalog_image_attachment_action_queue_public.json": image_attachment_action_queue,
            "source_discovery_focus_confirmed_template_public.json": source_discovery_focus_template,
            "source_discovery_focus_template_import_dry_run_public.json": source_discovery_focus_template_import,
            "source_discovery_completion_roadmap_public.json": source_discovery_completion_roadmap,
            "source_discovery_starter_queue_public.json": source_discovery_starter_queue,
            "source_discovery_next_focus_pack_public.json": source_discovery_next_focus_pack,
            "source_discovery_next_focus_pack_fetch_audit_public.json": source_discovery_next_focus_fetch_audit,
            "source_discovery_next_focus_detail_candidates_public.json": source_discovery_next_focus_detail_candidates,
            "source_discovery_next_focus_metadata_field_import_dry_run_public.json": source_discovery_next_focus_metadata_field_import,
            "source_discovery_next_focus_fallback_queue_public.json": source_discovery_next_focus_fallback_queue,
            "source_discovery_review_batches_public.json": source_discovery_review_batches,
            "source_discovery_action_queue_public.json": source_discovery_action_queue,
            "ensky_cache_candidate_action_queue_public.json": ensky_cache_candidate_action_queue,
            "catalog_metadata_review_batches_public.json": metadata_review_batches,
            "catalog_metadata_action_queue_public.json": metadata_action_queue,
            "requested_focus_review_batches_public.json": requested_focus_review_batches,
            "requested_focus_action_queue_public.json": requested_focus_action_queue,
            "catalog_deduplication_review_batches_public.json": load_json(DEDUPLICATION_REVIEW_BATCHES, {}),
            "catalog_deduplication_action_queue_public.json": deduplication_action_queue,
            "ichiban_kuji_reissue_decision_template_public.json": ichiban_kuji_reissue_decision_template,
            "ichiban_kuji_metadata_review_batches_public.json": ichiban_metadata_review_batches,
            "ichiban_kuji_metadata_action_queue_public.json": ichiban_metadata_action_queue,
            "ichiban_kuji_prize_name_image_review_public.json": ichiban_kuji_prize_name_image_review,
            "ichiban_kuji_prize_name_image_patch_candidates_public.json": (
                ichiban_kuji_prize_name_image_patch_candidates
            ),
            "animation_category_review_batches_public.json": animation_review_batches,
            "animation_category_action_queue_public.json": animation_action_queue,
            "animation_category_split_review_public.json": animation_split_review,
            "animation_category_unmatched_keyword_review_public.json": animation_unmatched_keyword_review,
            "catalog_confirmed_import_readiness_public.json": load_json(CONFIRMED_IMPORT_READINESS, {}),
        }
    )
    if execution_plan["summary"].get("open_review_queues") != operations["summary"]["open_review_queues"]:
        raise ValueError("execution plan open queues do not match operations open queues")

    catalog_generated_at = catalog.get("meta", {}).get("generated_at") or generated_at
    public_meta = load_json(PUBLIC_META, {})
    public_meta.update(
        {
            "schema_version": public_meta.get("schema_version", 1),
            "generated_at": catalog_generated_at,
            "row_count": rows,
            "total_items": rows,
            "fields": PUBLIC_FIELDS,
            "missing": missing,
            "privacy": {
                "contains_user_accounts": False,
                "contains_local_folders": False,
                "contains_private_memos": False,
                "contains_device_profiles": False,
                "contains_server_tokens": False,
            },
        }
    )

    quality = load_json(QUALITY, {})
    quality_missing = {
        "source_url": missing["source_url"],
        "image_url": missing["image_url"],
        "release_date": missing["release_date"],
        "barcode": missing["barcode"],
        "series_name": missing["series_name"],
        "sub_series": missing["sub_series"],
        "official_price_jpy": missing["official_price_jpy"],
    }
    quality_changed = (
        quality.get("row_count") != rows
        or quality.get("missing") != quality_missing
        or quality.get("coverage") != cov
    )
    quality.update(
        {
            "schema_version": quality.get("schema_version", 1),
            "row_count": rows,
            "missing": quality_missing,
            "coverage": cov,
            "public_catalog_crosscheck": public_catalog_crosscheck,
        }
    )
    if quality_changed:
        quality["generated_at"] = generated_at

    image_backlog = load_json(IMAGE_BACKLOG, {})
    summary = image_backlog.setdefault("summary", {})
    summary.update(
        {
            "rows": rows,
            "missing_images": missing["image_url"],
            "missing_with_source_url": sum(
                1 for item in items if present(item.get("source_url")) and not present(item.get("image_url"))
            ),
            "missing_with_exact_source_url": 0,
            "missing_with_generic_source_url": sum(
                1 for item in items if present(item.get("source_url")) and not present(item.get("image_url"))
            ),
        }
    )

    image_candidates = load_json(IMAGE_CANDIDATES, {})
    image_candidate_summary = image_candidates.setdefault("summary", {})
    image_candidate_summary.update(
        {
            "rows": rows,
            "missing_images": missing["image_url"],
            "missing_with_source_url": summary["missing_with_source_url"],
            "missing_with_exact_source_url": summary["missing_with_exact_source_url"],
            "missing_with_generic_source_url": summary["missing_with_generic_source_url"],
        }
    )
    image_backlog["candidate_review_summary"] = dict(image_candidate_summary)
    quality["image_backlog"] = {
        **(quality.get("image_backlog") if isinstance(quality.get("image_backlog"), dict) else {}),
        "missing_images": missing["image_url"],
        "provider_candidate_items": image_candidate_summary.get("provider_candidate_items", 0),
        "manual_or_blocked_items": image_candidate_summary.get("manual_or_blocked_items", 0),
        "missing_with_generic_source_url": summary["missing_with_generic_source_url"],
        "public_report": f"data/{IMAGE_BACKLOG.name}",
        "candidate_review_report": f"data/{IMAGE_CANDIDATES.name}",
        "candidate_review_summary": dict(image_candidate_summary),
    }

    for target in (quality, image_backlog, image_candidates):
        if GOTOUCHI.exists():
            target["gotouchi_chiikawa_image_candidates"] = copy_report_summary(GOTOUCHI, "gotouchi")
        if GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT.exists():
            target["gotouchi_representative_image_attachment"] = copy_report_summary(
                GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT, "gotouchi_representative_image_attachment"
            )
        target["gotouchi_official_candidate_review_queue"] = {
            "public_report": f"data/{GOTOUCHI_OFFICIAL_CANDIDATE_REVIEW_QUEUE.name}",
            **gotouchi_official_candidate_review_queue["summary"],
        }
        if REQUESTED.exists():
            target["requested_special_goods_review"] = copy_report_summary(REQUESTED, "requested")
        if GENERIC_SOURCE.exists():
            target["generic_source_cleanup_queue"] = copy_report_summary(GENERIC_SOURCE, "generic_source")
        target["generic_source_patch_candidates"] = {
            "public_report": f"data/{GENERIC_SOURCE_PATCH_CANDIDATES.name}",
            **generic_source_patch_candidates["summary"],
        }
        target["image_asset_audit"] = {
            "public_report": f"data/{IMAGE_ASSET_AUDIT.name}",
            **image_asset_audit["summary"],
            "download_readiness": image_asset_audit.get("download_readiness", {}),
        }
        target["missing_image_priority"] = {
            "public_report": f"data/{MISSING_IMAGE_PRIORITY.name}",
            **missing_image_priority["summary"],
        }
        if target is quality:
            target["source_discovery_starter_queue"] = {
                "public_report": f"data/{SOURCE_DISCOVERY_STARTER_QUEUE.name}",
                **source_discovery_starter_queue["summary"],
            }
        target["source_discovery_focus_packs"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_FOCUS_PACKS.name}",
            **source_discovery_focus_packs["summary"],
        }
        target["source_discovery_next_focus_pack"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK.name}",
            **source_discovery_next_focus_pack["summary"],
        }
        target["source_discovery_next_focus_pack_import_dry_run"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK_IMPORT.name}",
            "write": source_discovery_next_focus_pack_import["write"],
            "updated_rows": source_discovery_next_focus_pack_import["updated_rows"],
            "skipped_rows": source_discovery_next_focus_pack_import["skipped_rows"],
            "skip_reason_counts": source_discovery_next_focus_pack_import["skip_reason_counts"],
        }
        if source_discovery_next_focus_fetch_audit.get("summary"):
            target["source_discovery_next_focus_pack_fetch_audit"] = {
                "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.name}",
                **source_discovery_next_focus_fetch_audit["summary"],
            }
        if source_discovery_next_focus_detail_candidates.get("summary"):
            target["source_discovery_next_focus_detail_candidates"] = {
                "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.name}",
                **source_discovery_next_focus_detail_candidates["summary"],
            }
        if source_discovery_next_focus_metadata_field_import.get("summary"):
            target["source_discovery_next_focus_metadata_field_import_dry_run"] = {
                "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT.name}",
                **source_discovery_next_focus_metadata_field_import["summary"],
            }
        target["source_discovery_next_focus_fallback_queue"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.name}",
            **source_discovery_next_focus_fallback_queue["summary"],
        }
        target["source_discovery_next_focus_exact_url_review_queue"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_EXACT_URL_QUEUE.name}",
            **source_discovery_next_focus_exact_url_queue["summary"],
        }
        target["source_discovery_next_focus_identity_backfill_queue"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_BACKFILL_QUEUE.name}",
            **source_discovery_next_focus_identity_backfill_queue["summary"],
        }
        target["source_discovery_next_focus_identity_candidate_review_queue"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_CANDIDATE_REVIEW_QUEUE.name}",
            **source_discovery_next_focus_identity_candidate_review_queue["summary"],
        }
        target["source_discovery_next_focus_fallback_import_dry_run"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_IMPORT.name}",
            "write": source_discovery_next_focus_fallback_import["write"],
            "updated_rows": source_discovery_next_focus_fallback_import["updated_rows"],
            "skipped_rows": source_discovery_next_focus_fallback_import["skipped_rows"],
            "skip_reason_counts": source_discovery_next_focus_fallback_import["skip_reason_counts"],
        }
        target["source_discovery_completion_roadmap"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_ROADMAP.name}",
            **source_discovery_completion_roadmap["summary"],
            "completion_readiness": source_discovery_completion_roadmap.get(
                "completion_readiness",
                {},
            ),
        }
        if ANIMATE_MISSING_IMAGE_SEARCH.exists():
            target["animate_missing_image_search"] = copy_report_summary(
                ANIMATE_MISSING_IMAGE_SEARCH, "animate_missing_image_search"
            )
        if GOODSMILE_MISSING_IMAGE_SEARCH.exists():
            target["goodsmile_missing_image_search"] = copy_report_summary(
                GOODSMILE_MISSING_IMAGE_SEARCH, "goodsmile_missing_image_search"
            )
        if KOTOBUKIYA_MOVIC_MISSING_IMAGE_SEARCH.exists():
            target["kotobukiya_movic_missing_image_search"] = copy_report_summary(
                KOTOBUKIYA_MOVIC_MISSING_IMAGE_SEARCH, "kotobukiya_movic_missing_image_search"
            )
        if JUMP_FURYU_TAITO_MISSING_IMAGE_SEARCH.exists():
            target["jump_furyu_taito_missing_image_search"] = copy_report_summary(
                JUMP_FURYU_TAITO_MISSING_IMAGE_SEARCH, "jump_furyu_taito_missing_image_search"
            )
        if SECONDARY_OFFICIAL_MISSING_IMAGE_SEARCH.exists():
            target["secondary_official_missing_image_search"] = copy_report_summary(
                SECONDARY_OFFICIAL_MISSING_IMAGE_SEARCH, "secondary_official_missing_image_search"
            )
        if MANUAL_MISSING_IMAGE_SOURCE_DISCOVERY.exists():
            target["manual_missing_image_source_discovery"] = copy_report_summary(
                MANUAL_MISSING_IMAGE_SOURCE_DISCOVERY, "manual_missing_image_source_discovery"
            )
        if GENERIC_STOREFRONT_MISSING_IMAGE_SOURCE.exists():
            target["generic_storefront_missing_image_source"] = copy_report_summary(
                GENERIC_STOREFRONT_MISSING_IMAGE_SOURCE, "generic_storefront_missing_image_source"
            )
        target["missing_image_report_coverage"] = {
            "public_report": f"data/{MISSING_IMAGE_REPORT_COVERAGE.name}",
            **missing_image_report_coverage["summary"],
        }
        if ENSKY_CACHE_COVERAGE.exists():
            target["ensky_cache_coverage"] = copy_report_summary(ENSKY_CACHE_COVERAGE, "ensky_cache_coverage")
        target["ensky_cache_candidate_action_queue"] = {
            "public_report": f"data/{ENSKY_CACHE_CANDIDATE_ACTION_QUEUE.name}",
            **ensky_cache_candidate_action_queue.get("summary", {}),
            "import_readiness": ensky_cache_candidate_action_queue.get("import_readiness", {}),
        }
        if ENSKY_SEARCH_PAGE_PROBE.exists():
            target["ensky_search_page_probe"] = copy_report_summary(ENSKY_SEARCH_PAGE_PROBE, "ensky_search_page_probe")
        if STELLIVE_FANDING_CANDIDATES.exists():
            target["stellive_fanding_candidates"] = copy_report_summary(
                STELLIVE_FANDING_CANDIDATES, "stellive_fanding_candidates"
            )
        target["image_source_url_confirmed_template"] = {
            "public_report": f"data/{IMAGE_SOURCE_URL_CONFIRMED_TEMPLATE.name}",
            **image_source_url_confirmed_template["summary"],
        }
        target["image_attachment_template_import_dry_run"] = {
            "public_report": f"data/{IMAGE_ATTACHMENT_TEMPLATE_IMPORT_DRY_RUN.name}",
            **image_attachment_template_import_dry_run["summary"],
        }
        target["manual_source_url_search_queue"] = {
            "public_report": f"data/{MANUAL_SOURCE_URL_SEARCH_QUEUE.name}",
            **manual_source_url_search_queue["summary"],
            "review_readiness": manual_source_url_search_queue.get("review_readiness", {}),
        }
        target["provider_missing_source_url_queue"] = {
            "public_report": f"data/{PROVIDER_MISSING_SOURCE_URL_QUEUE.name}",
            **provider_missing_source_url_queue["summary"],
            "review_readiness": provider_missing_source_url_queue.get("review_readiness", {}),
        }
        target["candidate_source_url_review_queue"] = {
            "public_report": f"data/{CANDIDATE_SOURCE_URL_REVIEW_QUEUE.name}",
            **candidate_source_url_review_queue["summary"],
            "review_readiness": candidate_source_url_review_queue.get("review_readiness", {}),
        }
        target["source_url_update_queue_split"] = {
            "public_reports": [
                f"data/{MANUAL_SOURCE_URL_SEARCH_QUEUE.name}",
                f"data/{PROVIDER_MISSING_SOURCE_URL_QUEUE.name}",
                f"data/{CANDIDATE_SOURCE_URL_REVIEW_QUEUE.name}",
            ],
            "source_url_update_required_rows": image_source_url_confirmed_template["summary"].get(
                "template_items", 0
            ),
            "manual_search_required_rows": manual_source_url_search_queue["summary"].get(
                "manual_search_required_rows", 0
            ),
            "provider_missing_rows": provider_missing_source_url_queue["summary"].get(
                "provider_missing_rows", 0
            ),
            "candidate_review_rows": candidate_source_url_review_queue["summary"].get(
                "candidate_review_rows", 0
            ),
            "covered_rows": (
                manual_source_url_search_queue["summary"].get("manual_search_required_rows", 0)
                + provider_missing_source_url_queue["summary"].get("provider_missing_rows", 0)
                + candidate_source_url_review_queue["summary"].get("candidate_review_rows", 0)
            ),
            "review_readiness": {
                "status": (
                    "manual_review_required"
                    if image_source_url_confirmed_template["summary"].get("template_items", 0)
                    else "empty"
                ),
                "source_url_update_required_rows": image_source_url_confirmed_template[
                    "summary"
                ].get("template_items", 0),
                "covered_rows": (
                    manual_source_url_search_queue["summary"].get(
                        "manual_search_required_rows",
                        0,
                    )
                    + provider_missing_source_url_queue["summary"].get(
                        "provider_missing_rows",
                        0,
                    )
                    + candidate_source_url_review_queue["summary"].get(
                        "candidate_review_rows",
                        0,
                    )
                ),
                "auto_apply_ready_rows": (
                    manual_source_url_search_queue.get("review_readiness", {}).get(
                        "auto_apply_ready_rows",
                        0,
                    )
                    + provider_missing_source_url_queue.get("review_readiness", {}).get(
                        "auto_apply_ready_rows",
                        0,
                    )
                    + candidate_source_url_review_queue.get("review_readiness", {}).get(
                        "auto_apply_ready_rows",
                        0,
                    )
                ),
                "manual_review_rows": (
                    manual_source_url_search_queue.get("review_readiness", {}).get(
                        "manual_review_rows",
                        0,
                    )
                    + provider_missing_source_url_queue.get("review_readiness", {}).get(
                        "manual_review_rows",
                        0,
                    )
                    + candidate_source_url_review_queue.get("review_readiness", {}).get(
                        "manual_review_rows",
                        0,
                    )
                ),
                "lanes": [
                    {
                        "lane": "manual_search_required",
                        "rows": manual_source_url_search_queue["summary"].get(
                            "manual_search_required_rows",
                            0,
                        ),
                        "status": manual_source_url_search_queue.get(
                            "review_readiness",
                            {},
                        ).get("status"),
                        "next_review_row": manual_source_url_search_queue.get(
                            "review_readiness",
                            {},
                        ).get("next_review_row", {}),
                    },
                    {
                        "lane": "provider_or_manual_refresh_required",
                        "rows": provider_missing_source_url_queue["summary"].get(
                            "provider_missing_rows",
                            0,
                        ),
                        "status": provider_missing_source_url_queue.get(
                            "review_readiness",
                            {},
                        ).get("status"),
                        "next_review_row": provider_missing_source_url_queue.get(
                            "review_readiness",
                            {},
                        ).get("next_review_row", {}),
                    },
                    {
                        "lane": "candidate_review_required",
                        "rows": candidate_source_url_review_queue["summary"].get(
                            "candidate_review_rows",
                            0,
                        ),
                        "status": candidate_source_url_review_queue.get(
                            "review_readiness",
                            {},
                        ).get("status"),
                        "next_review_row": candidate_source_url_review_queue.get(
                            "review_readiness",
                            {},
                        ).get("next_review_row", {}),
                    },
                ],
                "next_queue": {
                    "lane": "candidate_review_required",
                    "reason": "candidate_options_exist_for_review",
                    "rows": candidate_source_url_review_queue["summary"].get(
                        "candidate_review_rows",
                        0,
                    ),
                    "next_review_row": candidate_source_url_review_queue.get(
                        "review_readiness",
                        {},
                    ).get("next_review_row", {}),
                }
                if candidate_source_url_review_queue["summary"].get(
                    "candidate_review_rows",
                    0,
                )
                else {
                    "lane": "manual_search_required",
                    "reason": "no_candidate_options_available",
                    "rows": manual_source_url_search_queue["summary"].get(
                        "manual_search_required_rows",
                        0,
                    ),
                    "next_review_row": manual_source_url_search_queue.get(
                        "review_readiness",
                        {},
                    ).get("next_review_row", {}),
                },
                "blocked_reason": "source_url_identity_not_confirmed",
                "blocked_until": "manual_exact_source_url_confirmation",
                "auto_apply_enabled": False,
            },
            "auto_apply_enabled": False,
        }
        target["requested_focus_enrichment"] = {
            "public_report": f"data/{REQUESTED_FOCUS.name}",
            **requested_focus["summary"],
        }
        if REQUESTED_FOCUS_REVIEW_BATCHES.exists():
            target["requested_focus_review_batches"] = copy_report_summary(
                REQUESTED_FOCUS_REVIEW_BATCHES, "requested_focus_review_batches"
            )
        if REQUESTED_FOCUS_ACTION_QUEUE.exists():
            target["requested_focus_action_queue"] = copy_report_summary(
                REQUESTED_FOCUS_ACTION_QUEUE, "requested_focus_action_queue"
            )
        target["requested_focus_next_work"] = {
            "public_report": f"data/{REQUESTED_FOCUS_NEXT_WORK.name}",
            **requested_focus_next_work["summary"],
        }
        if IMAGE_ATTACHMENT_ACTION_QUEUE.exists():
            image_attachment_action_summary = image_attachment_action_queue.get("summary", {})
            target["image_attachment_action_queue"] = copy_report_summary(
                IMAGE_ATTACHMENT_ACTION_QUEUE, "image_attachment_action_queue"
            )
            target["image_attachment_queue_alignment"] = {
                "public_reports": [
                    f"data/{MISSING_IMAGE_PRIORITY.name}",
                    f"data/{IMAGE_ATTACHMENT_ACTION_QUEUE.name}",
                    f"data/{IMAGE_ATTACHMENT_CONFIRMED_TEMPLATE.name}",
                    f"data/{IMAGE_ATTACHMENT_TEMPLATE_IMPORT_DRY_RUN.name}",
                    f"data/{MISSING_IMAGE_ACTIONABILITY.name}",
                ],
                "missing_image_rows": missing_image_priority["summary"].get("missing_image_rows", 0),
                "actionable_image_rows": image_attachment_action_summary.get(
                    "actionable_image_rows", 0
                ),
                "queued_image_rows": image_attachment_action_summary.get("queued_image_rows", 0),
                "unqueued_actionable_image_rows": image_attachment_action_summary.get(
                    "unqueued_actionable_image_rows", 0
                ),
                "source_url_update_required_rows": image_attachment_action_summary.get(
                    "source_url_update_required_rows", 0
                ),
                "source_url_update_template_rows": image_attachment_action_summary.get(
                    "source_url_update_template_rows", 0
                ),
                "source_url_update_template_batch_count": image_attachment_action_summary.get(
                    "source_url_update_template_batch_count", 0
                ),
                "representative_image_review_required_rows": image_attachment_action_summary.get(
                    "representative_image_review_required_rows", 0
                ),
                "image_url_ready_rows": image_attachment_action_summary.get(
                    "image_url_ready_rows", 0
                ),
                "primary_review_url_missing_rows": image_attachment_action_summary.get(
                    "primary_review_url_missing_rows", 0
                ),
                "blocked_before_image_import_rows": image_attachment_action_summary.get(
                    "blocked_before_image_import_rows", 0
                ),
                "download_ready_after_manual_image_url_rows": image_attachment_action_summary.get(
                    "download_ready_after_manual_image_url_rows", 0
                ),
                "template_rows": image_attachment_template_import_dry_run["summary"].get(
                    "template_items", 0
                ),
                "template_confirmed_rows": image_attachment_template_import_dry_run[
                    "summary"
                ].get("manual_confirmed_rows", 0),
                "dry_run_updated_rows": image_attachment_template_import_dry_run[
                    "summary"
                ].get("updated_rows", 0),
                "dry_run_skipped_rows": image_attachment_template_import_dry_run[
                    "summary"
                ].get("skipped_rows", 0),
                "sample_queue_coverage": image_attachment_action_summary.get(
                    "sample_queue_coverage", 0
                ),
                "attachment_readiness": image_attachment_action_queue.get(
                    "attachment_readiness", {}
                ),
                "next_step": "confirm_source_url_updates_before_representative_image_reviews",
                "blocked_reason": "image_attachment_requires_source_or_representative_image_confirmation",
                "explanation": (
                    "Image-missing rows are not auto-filled from search results. "
                    "Queued rows first need source URL confirmation or representative "
                    "image review, then confirmed template rows can be imported."
                ),
                "auto_apply_enabled": False,
                "manual_confirmation_required": True,
            }
        target["missing_image_actionability"] = {
            "public_report": f"data/{MISSING_IMAGE_ACTIONABILITY.name}",
            **missing_image_actionability["summary"],
            "manual_validation_focus": missing_image_actionability.get(
                "manual_validation_focus",
                {},
            ),
            "execution_queue_summary": missing_image_actionability.get(
                "execution_queue_summary",
                {},
            ),
            "blocking_dashboard": missing_image_actionability.get(
                "blocking_dashboard",
                {},
            ),
        }
        target["danganronpa_missing_media"] = {
            "public_report": f"data/{DANGANRONPA_MISSING_MEDIA.name}",
            **danganronpa_missing_media["summary"],
        }
        target["danganronpa_patch_template_dry_run"] = {
            "public_report": f"data/{DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.name}",
            **danganronpa_patch_template_dry_run["summary"],
        }
        if DANGANRONPA_GOODSMILE_PROBE.exists():
            target["danganronpa_goodsmile_probe"] = copy_report_summary(
                DANGANRONPA_GOODSMILE_PROBE, "danganronpa_goodsmile_probe"
            )
        if DANGANRONPA_PRIZE_PROBE.exists():
            target["danganronpa_prize_probe"] = copy_report_summary(
                DANGANRONPA_PRIZE_PROBE, "danganronpa_prize_probe"
            )
        if DANGANRONPA_SOURCE_DETAIL_PROBE.exists():
            target["danganronpa_source_detail_probe"] = copy_report_summary(
                DANGANRONPA_SOURCE_DETAIL_PROBE, "danganronpa_source_detail_probe"
            )
        if SOURCE_DETAIL.exists():
            source_detail_probe_summary = copy_report_summary(SOURCE_DETAIL, "source_detail")
            if "unique_review_candidate_rows" in source_detail_probe_summary:
                source_detail_probe_summary["raw_candidate_review_rows"] = source_detail_probe_summary.get(
                    "candidate_review_rows", 0
                )
                source_detail_probe_summary["candidate_review_rows"] = source_detail_probe_summary.get(
                    "unique_review_candidate_rows", 0
                )
            target["source_detail_candidate_probe"] = source_detail_probe_summary
        if SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.exists():
            target["source_detail_candidate_action_queue"] = copy_report_summary(
                SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE, "source_detail_candidate_action_queue"
            )
        if OFFICIAL_DETAIL_REVIEW_BATCHES.exists():
            target["official_detail_review_batches"] = copy_report_summary(
                OFFICIAL_DETAIL_REVIEW_BATCHES, "official_detail_review_batches"
            )
        target["source_discovery_queue"] = {
            "public_report": f"data/{SOURCE_DISCOVERY.name}",
            **source_discovery["summary"],
        }
        target["source_discovery_review_batches"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_REVIEW_BATCHES.name}",
            **source_discovery_review_batches["summary"],
        }
        target["source_discovery_action_queue"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_ACTION_QUEUE.name}",
            **source_discovery_action_queue["summary"],
        }
        source_discovery_focus_template_import_summary = (
            source_discovery_focus_template_import.get("summary")
            if isinstance(source_discovery_focus_template_import.get("summary"), dict)
            else source_discovery_focus_template_import
        )
        target["source_discovery_queue_alignment"] = {
            "public_reports": [
                f"data/{SOURCE_DISCOVERY_ACTION_QUEUE.name}",
                f"data/{SOURCE_DISCOVERY_FOCUS_PACKS.name}",
                f"data/{SOURCE_DISCOVERY_FOCUS_TEMPLATE.name}",
                f"data/{SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT.name}",
                f"data/{SOURCE_DISCOVERY_STORE_BOTTLENECKS.name}",
            ],
            "missing_source_url_rows": source_discovery_starter_queue["summary"].get(
                "missing_source_url_rows", 0
            ),
            "actionable_source_rows": source_discovery_action_queue["summary"].get(
                "actionable_source_rows", 0
            ),
            "queued_source_rows": source_discovery_action_queue["summary"].get(
                "queued_source_rows", 0
            ),
            "source_discovery_template_rows": source_discovery_action_queue[
                "summary"
            ].get("source_discovery_template_rows", 0),
            "source_discovery_template_batch_count": source_discovery_action_queue[
                "summary"
            ].get("source_discovery_template_batch_count", 0),
            "focus_template_items": source_discovery_focus_template[
                "summary"
            ].get("template_items", 0),
            "focus_template_confirmed_rows": source_discovery_focus_template_import_summary.get(
                "manual_confirmed_rows", 0
            ),
            "dry_run_updated_rows": source_discovery_focus_template_import_summary.get(
                "updated_rows", 0
            ),
            "dry_run_skipped_rows": source_discovery_focus_template_import_summary.get(
                "skipped_rows", 0
            ),
            "next_step": "confirm_exact_product_detail_source_urls",
            "blocked_reason": "source_discovery_requires_exact_product_evidence",
            "manual_confirmation_required": True,
            "auto_apply_enabled": False,
        }
        target["source_discovery_action_queue"]["top_source_store_workstreams"] = [
            {
                "source_store": row.get("source_store"),
                "priority": row.get("priority"),
                "queued_source_rows": row.get("queued_source_rows"),
                "batch_count": row.get("batch_count", 0),
                "next_batch_id": row.get("next_batch_id"),
                "batch_ids": row.get("batch_ids", []),
                "allowed_source_domains": row.get("allowed_source_domains", []),
                "official_search_url_count": row.get("official_search_url_count", 0),
                "workflow_rows": row.get("workflow_rows", []),
                "review_state_rows": row.get("review_state_rows", []),
                "category_rows": row.get("category_rows", []),
                "recommended_next_step": row.get("recommended_next_step"),
                "auto_apply_enabled": row.get("auto_apply_enabled", False),
            }
            for row in source_discovery_action_queue.get("source_store_workstreams", [])
            if isinstance(row, dict)
        ][:8]
        target["source_discovery_store_bottlenecks"] = {
            "public_report": f"data/{SOURCE_DISCOVERY_STORE_BOTTLENECKS.name}",
            **source_discovery_store_bottlenecks["summary"],
        }
        target["metadata_backlog"] = {
            "public_report": f"data/{METADATA_BACKLOG.name}",
            **metadata_backlog["summary"],
        }
        if METADATA_REVIEW_BATCHES.exists():
            target["metadata_review_batches"] = copy_report_summary(METADATA_REVIEW_BATCHES, "metadata_review_batches")
        if METADATA_ACTION_QUEUE.exists():
            target["metadata_action_queue"] = copy_report_summary(METADATA_ACTION_QUEUE, "metadata_action_queue")
        if CONFIRMED_IMPORT_READINESS.exists():
            target["confirmed_import_readiness"] = copy_report_summary(
                CONFIRMED_IMPORT_READINESS, "confirmed_import_readiness"
            )
        target["execution_plan"] = {
            "public_report": f"data/{EXECUTION_PLAN.name}",
            **execution_plan["summary"],
        }
        target["image_enrichment_batches"] = {
            "public_report": f"data/{IMAGE_ENRICHMENT_BATCHES.name}",
            **image_enrichment_batches["summary"],
        }
        target["deduplication_review"] = {
            "public_report": f"data/{DEDUPLICATION.name}",
            **deduplication["summary"],
        }
        target["name_duplicate_audit"] = {
            "public_report": f"data/{NAME_DUPLICATE_AUDIT.name}",
            **name_duplicate_audit["summary"],
        }
        if DEDUPLICATION_REVIEW_BATCHES.exists():
            target["deduplication_review_batches"] = copy_report_summary(
                DEDUPLICATION_REVIEW_BATCHES, "deduplication_review_batches"
            )
        dedupe_action_queue_summary = {}
        if DEDUPLICATION_ACTION_QUEUE.exists():
            dedupe_action_queue = load_json(DEDUPLICATION_ACTION_QUEUE, {})
            dedupe_action_queue_summary = dedupe_action_queue.get("summary", {})
            target["deduplication_action_queue"] = copy_report_summary(
                DEDUPLICATION_ACTION_QUEUE, "deduplication_action_queue"
            )
        if DEDUPLICATION_FAST_REVIEW.exists():
            dedupe_fast_review = load_json(DEDUPLICATION_FAST_REVIEW, {})
            dedupe_fast_summary = dedupe_fast_review.get("summary", {})
            target["deduplication_fast_review"] = copy_report_summary(
                DEDUPLICATION_FAST_REVIEW, "deduplication_fast_review"
            )
            target["deduplication_queue_alignment"] = {
                "public_reports": [
                    f"data/{DEDUPLICATION.name}",
                    f"data/{DEDUPLICATION_ACTION_QUEUE.name}",
                    f"data/{DEDUPLICATION_FAST_REVIEW.name}",
                    f"data/{NAME_DUPLICATE_AUDIT.name}",
                ],
                "duplicate_review_groups": deduplication["summary"].get("duplicate_groups", 0),
                "actionable_groups": dedupe_action_queue_summary.get("actionable_groups", 0),
                "queued_groups": dedupe_action_queue_summary.get("queued_groups", 0),
                "non_action_queue_groups": max(
                    0,
                    int(deduplication["summary"].get("duplicate_groups") or 0)
                    - int(dedupe_action_queue_summary.get("actionable_groups") or 0),
                ),
                "fast_review_groups": dedupe_fast_summary.get("fast_review_groups", 0),
                "held_for_later_groups": dedupe_fast_summary.get("held_for_later_groups", 0),
                "manual_confirmed_true": dedupe_fast_summary.get("manual_confirmed_true", 0),
                "name_duplicate_protected_groups": name_duplicate_audit["summary"].get(
                    "protected_groups", 0
                ),
                "ichiban_campaign_or_reissue_protected_groups": name_duplicate_audit[
                    "summary"
                ].get("ichiban_campaign_or_reissue_protected_groups", 0),
                "queue_coverage": dedupe_action_queue_summary.get("queue_coverage", 0),
                "next_step": "review_fast_same_barcode_groups_before_held_variant_groups",
                "blocked_reason": "dedupe_requires_explicit_same_sellable_product_confirmation",
                "explanation": (
                    "Only high-confidence duplicate candidates enter the action queue. "
                    "Remaining duplicate-review groups and same-name groups stay held or "
                    "protected when barcode, variant, source, or reissue evidence is ambiguous."
                ),
                "auto_merge_enabled": False,
                "auto_delete_enabled": False,
                "manual_confirmation_required": True,
            }
        if DEDUPLICATION_CONFIRMED_TEMPLATE.exists():
            target["deduplication_confirmed_template"] = copy_report_summary(
                DEDUPLICATION_CONFIRMED_TEMPLATE, "deduplication_confirmed_template"
            )
        target["deduplication_template_import_dry_run"] = {
            "public_report": f"data/{DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN.name}",
            **deduplication_template_import_dry_run["summary"],
        }
        target["animation_category_review"] = {
            "public_report": f"data/{ANIMATION_CATEGORIES.name}",
            **animation_categories["summary"],
            "category_readiness": animation_categories.get("category_readiness", {}),
        }
        target["animation_category_coverage_audit"] = {
            "public_report": f"data/{ANIMATION_CATEGORY_COVERAGE_AUDIT.name}",
            **animation_category_coverage_audit["summary"],
        }
        if ANIMATION_CATEGORY_REVIEW_BATCHES.exists():
            target["animation_category_review_batches"] = copy_report_summary(
                ANIMATION_CATEGORY_REVIEW_BATCHES, "animation_category_review_batches"
            )
        if ANIMATION_CATEGORY_ACTION_QUEUE.exists():
            target["animation_category_action_queue"] = copy_report_summary(
                ANIMATION_CATEGORY_ACTION_QUEUE, "animation_category_action_queue"
            )
        if ANIMATION_CATEGORY_SPLIT_REVIEW.exists():
            target["animation_category_split_review"] = copy_report_summary(
                ANIMATION_CATEGORY_SPLIT_REVIEW, "animation_category_split_review"
            )
        if ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.exists():
            target["animation_category_unmatched_keyword_review"] = copy_report_summary(
                ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW, "animation_category_unmatched_keyword_review"
            )
        target["ichiban_kuji_history"] = {
            "public_report": f"data/{ICHIIBAN_KUJI_HISTORY.name}",
            **ichiban_kuji_history["summary"],
            "metadata_resolution_readiness": ichiban_kuji_history.get(
                "metadata_resolution_readiness",
                {},
            ),
        }
        if ICHIIBAN_KUJI_METADATA_PROBE.exists():
            target["ichiban_kuji_metadata_probe"] = copy_report_summary(
                ICHIIBAN_KUJI_METADATA_PROBE, "ichiban_kuji_metadata_probe"
            )
        if ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES.exists():
            target["ichiban_kuji_metadata_review_batches"] = copy_report_summary(
                ICHIIBAN_KUJI_METADATA_REVIEW_BATCHES, "ichiban_kuji_metadata_review_batches"
            )
        if ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.exists():
            target["ichiban_kuji_metadata_action_queue"] = copy_report_summary(
                ICHIIBAN_KUJI_METADATA_ACTION_QUEUE, "ichiban_kuji_metadata_action_queue"
            )
        if ichiban_metadata_fast_review:
            target["ichiban_kuji_metadata_fast_review"] = {
                "public_report": f"data/{ICHIIBAN_KUJI_METADATA_FAST_REVIEW.name}",
                **ichiban_metadata_fast_review.get("summary", {}),
            }
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.exists():
            target["ichiban_kuji_prize_name_image_review"] = copy_report_summary(
                ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW, "ichiban_kuji_prize_name_image_review"
            )
        if ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.exists():
            target["ichiban_kuji_prize_name_image_patch_candidates"] = copy_report_summary(
                ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES,
                "ichiban_kuji_prize_name_image_patch_candidates",
            )
        if ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.exists():
            target["ichiban_kuji_prize_policy_audit"] = copy_report_summary(
                ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT, "ichiban_kuji_prize_policy_audit"
            )
        target["ichiban_kuji_prize_policy_issue_queue"] = {
            "public_report": f"data/{ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.name}",
            **ichiban_kuji_prize_policy_issue_queue.get("summary", {}),
            "completion_readiness": ichiban_kuji_prize_policy_issue_queue.get(
                "completion_readiness",
                {},
            ),
        }
        target["ichiban_kuji_reissue_deduplication"] = {
            "public_report": f"data/{ICHIIBAN_KUJI_REISSUE_DEDUPLICATION.name}",
            **ichiban_kuji_reissue_deduplication.get("summary", {}),
        }
        target["ichiban_kuji_reissue_decision_template"] = {
            "public_report": f"data/{ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE.name}",
            **ichiban_kuji_reissue_decision_template.get("summary", {}),
        }
        target["ichiban_kuji_historical_roadmap"] = {
            "public_report": f"data/{ICHIIBAN_KUJI_HISTORICAL_ROADMAP.name}",
            **ichiban_kuji_historical_roadmap.get("summary", {}),
        }
        target["operations"] = {
            "public_report": f"data/{OPERATIONS_REPORT.name}",
            **operations["summary"]["open_review_queues"],
        }
        target["agent_work_queue"] = {
            "public_report": f"data/{AGENT_WORK_QUEUE.name}",
            **agent_work_queue["summary"],
        }

    consistency_findings = validate_report_consistency(
        rows,
        missing,
        source_discovery,
        metadata_backlog,
        image_enrichment_batches,
        deduplication,
        animation_categories,
        ichiban_kuji_history,
        generic_source_patch_candidates,
        requested_focus,
        danganronpa_missing_media,
        danganronpa_patch_template_dry_run,
        operations,
        agent_work_queue,
        metadata_action_queue,
        animation_review_batches,
        animation_action_queue,
        animation_split_review,
        animation_unmatched_keyword_review,
        source_discovery_next_focus_fallback_queue,
        source_discovery_starter_queue,
        source_discovery_action_queue_override=source_discovery_action_queue,
        source_discovery_focus_template_override=source_discovery_focus_template,
        source_discovery_focus_template_import_override=source_discovery_focus_template_import,
        source_discovery_next_focus_pack_override=source_discovery_next_focus_pack,
        image_attachment_action_queue_override=image_attachment_action_queue,
    )
    if consistency_findings:
        raise ValueError("public report consistency validation failed: " + "; ".join(consistency_findings))

    public_validation = validate_all_public_json_files()
    findings = public_validation["findings"]
    if findings:
        raise ValueError("public safety validation failed: " + "; ".join(findings))

    if write:
        write_json(SOURCE_DISCOVERY, source_discovery)
        write_json(METADATA_BACKLOG, metadata_backlog)
        write_json(METADATA_REVIEW_BATCHES, metadata_review_batches)
        write_json(METADATA_ACTION_QUEUE, metadata_action_queue)
        write_json(IMAGE_ENRICHMENT_BATCHES, image_enrichment_batches)
        write_json(DEDUPLICATION, deduplication)
        write_json(DEDUPLICATION_ACTION_QUEUE, deduplication_action_queue)
        write_json(DEDUPLICATION_FAST_REVIEW, deduplication_fast_review)
        write_json(NAME_DUPLICATE_AUDIT, name_duplicate_audit)
        write_json(ANIMATION_CATEGORIES, animation_categories)
        write_json(ANIMATION_CATEGORY_COVERAGE_AUDIT, animation_category_coverage_audit)
        write_json(ANIMATION_CATEGORY_REVIEW_BATCHES, animation_review_batches)
        write_json(ANIMATION_CATEGORY_ACTION_QUEUE, animation_action_queue)
        write_json(ANIMATION_CATEGORY_SPLIT_REVIEW, animation_split_review)
        write_json(ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW, animation_unmatched_keyword_review)
        write_json(ICHIIBAN_KUJI_HISTORY, ichiban_kuji_history)
        write_json(ICHIIBAN_KUJI_METADATA_ACTION_QUEUE, ichiban_metadata_action_queue)
        write_json(ICHIIBAN_KUJI_METADATA_FAST_REVIEW, ichiban_metadata_fast_review)
        write_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW, ichiban_kuji_prize_name_image_review)
        write_json(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES, ichiban_kuji_prize_name_image_patch_candidates)
        write_json(ICHIIBAN_KUJI_HISTORICAL_ROADMAP, ichiban_kuji_historical_roadmap)
        write_json(OPERATIONS_REPORT, operations)
        write_json(AGENT_WORK_QUEUE, agent_work_queue)
        write_json(EXECUTION_PLAN, execution_plan)
        write_json(PUBLIC_META, public_meta)
        write_json(QUALITY, quality)
        write_json(IMAGE_BACKLOG, image_backlog)
        write_json(IMAGE_CANDIDATES, image_candidates)
        write_json(IMAGE_ASSET_AUDIT, image_asset_audit)
        missing_image_priority_public = dict(missing_image_priority)
        missing_image_priority_public.pop("_source_discovery_starter_queue_full", None)
        write_json(MISSING_IMAGE_PRIORITY, missing_image_priority_public)
        write_json(SOURCE_DISCOVERY_STARTER_QUEUE, source_discovery_starter_queue)
        write_json(MISSING_IMAGE_REPORT_COVERAGE, missing_image_report_coverage)
        write_json(ENSKY_CACHE_CANDIDATE_ACTION_QUEUE, ensky_cache_candidate_action_queue)
        write_json(IMAGE_ATTACHMENT_ACTION_QUEUE, image_attachment_action_queue)
        write_json(IMAGE_SOURCE_URL_CONFIRMED_TEMPLATE, image_source_url_confirmed_template)
        write_json(IMAGE_ATTACHMENT_TEMPLATE_IMPORT_DRY_RUN, image_attachment_template_import_dry_run)
        write_json(MANUAL_SOURCE_URL_SEARCH_QUEUE, manual_source_url_search_queue)
        write_json(PROVIDER_MISSING_SOURCE_URL_QUEUE, provider_missing_source_url_queue)
        write_json(CANDIDATE_SOURCE_URL_REVIEW_QUEUE, candidate_source_url_review_queue)
        write_json(GOTOUCHI_OFFICIAL_CANDIDATE_REVIEW_QUEUE, gotouchi_official_candidate_review_queue)
        write_json(ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE, ichiban_kuji_prize_policy_issue_queue)
        write_json(ICHIIBAN_KUJI_REISSUE_DEDUPLICATION, ichiban_kuji_reissue_deduplication)
        write_json(ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE, ichiban_kuji_reissue_decision_template)
        write_json(SOURCE_DISCOVERY_REVIEW_BATCHES, source_discovery_review_batches)
        write_json(SOURCE_DISCOVERY_ACTION_QUEUE, source_discovery_action_queue)
        write_json(SOURCE_DISCOVERY_STORE_BOTTLENECKS, source_discovery_store_bottlenecks)
        write_json(SOURCE_DISCOVERY_FOCUS_PACKS, source_discovery_focus_packs)
        write_json(SOURCE_DISCOVERY_FOCUS_TEMPLATE, source_discovery_focus_template)
        write_json(SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT, source_discovery_focus_template_import)
        write_json(SOURCE_DISCOVERY_ROADMAP, source_discovery_completion_roadmap)
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK, source_discovery_next_focus_pack)
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK_IMPORT, source_discovery_next_focus_pack_import)
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT, source_discovery_next_focus_fetch_audit)
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES, source_discovery_next_focus_detail_candidates)
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT, source_discovery_next_focus_metadata_field_import)
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE, source_discovery_next_focus_fallback_queue)
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_EXACT_URL_QUEUE, source_discovery_next_focus_exact_url_queue)
        write_json(
            SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_BACKFILL_QUEUE,
            source_discovery_next_focus_identity_backfill_queue,
        )
        write_json(
            SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_CANDIDATE_REVIEW_QUEUE,
            source_discovery_next_focus_identity_candidate_review_queue,
        )
        write_json(SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_IMPORT, source_discovery_next_focus_fallback_import)
        write_json(MISSING_IMAGE_ACTIONABILITY, missing_image_actionability)
        write_json(GENERIC_SOURCE_PATCH_CANDIDATES, generic_source_patch_candidates)
        write_json(REQUESTED_FOCUS, requested_focus)
        write_json(REQUESTED_FOCUS_ACTION_QUEUE, requested_focus_action_queue)
        write_json(REQUESTED_FOCUS_NEXT_WORK, requested_focus_next_work)
        write_json(DANGANRONPA_MISSING_MEDIA, danganronpa_missing_media)
        write_json(DANGANRONPA_PATCH_TEMPLATE_DRY_RUN, danganronpa_patch_template_dry_run)
        write_json(DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN, deduplication_template_import_dry_run)

    return {
        "write": write,
        "rows": rows,
        "missing": missing,
        "coverage": cov,
        "public_validation": public_validation,
        "updated_files": [
            str(PUBLIC_META.relative_to(ROOT)),
            str(QUALITY.relative_to(ROOT)),
            str(IMAGE_BACKLOG.relative_to(ROOT)),
            str(IMAGE_CANDIDATES.relative_to(ROOT)),
            str(IMAGE_ASSET_AUDIT.relative_to(ROOT)),
            str(MISSING_IMAGE_PRIORITY.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_STARTER_QUEUE.relative_to(ROOT)),
            str(ANIMATE_MISSING_IMAGE_SEARCH.relative_to(ROOT)),
            str(GOODSMILE_MISSING_IMAGE_SEARCH.relative_to(ROOT)),
            str(KOTOBUKIYA_MOVIC_MISSING_IMAGE_SEARCH.relative_to(ROOT)),
            str(JUMP_FURYU_TAITO_MISSING_IMAGE_SEARCH.relative_to(ROOT)),
            str(SECONDARY_OFFICIAL_MISSING_IMAGE_SEARCH.relative_to(ROOT)),
            str(MANUAL_MISSING_IMAGE_SOURCE_DISCOVERY.relative_to(ROOT)),
            str(GENERIC_STOREFRONT_MISSING_IMAGE_SOURCE.relative_to(ROOT)),
            str(MISSING_IMAGE_REPORT_COVERAGE.relative_to(ROOT)),
            str(ENSKY_CACHE_COVERAGE.relative_to(ROOT)),
            str(ENSKY_CACHE_CANDIDATE_ACTION_QUEUE.relative_to(ROOT)),
            str(ENSKY_SEARCH_PAGE_PROBE.relative_to(ROOT)),
            str(STELLIVE_FANDING_CANDIDATES.relative_to(ROOT)),
            str(GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT.relative_to(ROOT)),
            str(GOTOUCHI_OFFICIAL_CANDIDATE_REVIEW_QUEUE.relative_to(ROOT)),
            str(IMAGE_ATTACHMENT_ACTION_QUEUE.relative_to(ROOT)),
            str(IMAGE_SOURCE_URL_CONFIRMED_TEMPLATE.relative_to(ROOT)),
            str(MANUAL_SOURCE_URL_SEARCH_QUEUE.relative_to(ROOT)),
            str(PROVIDER_MISSING_SOURCE_URL_QUEUE.relative_to(ROOT)),
            str(CANDIDATE_SOURCE_URL_REVIEW_QUEUE.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_PACK.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_PACK_IMPORT.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_METADATA_FIELD_IMPORT.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_EXACT_URL_QUEUE.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_BACKFILL_QUEUE.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_IDENTITY_CANDIDATE_REVIEW_QUEUE.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_IMPORT.relative_to(ROOT)),
            str(MISSING_IMAGE_ACTIONABILITY.relative_to(ROOT)),
            str(GENERIC_SOURCE_PATCH_CANDIDATES.relative_to(ROOT)),
            str(REQUESTED_FOCUS.relative_to(ROOT)),
            str(REQUESTED_FOCUS_REVIEW_BATCHES.relative_to(ROOT)),
            str(REQUESTED_FOCUS_ACTION_QUEUE.relative_to(ROOT)),
            str(REQUESTED_FOCUS_NEXT_WORK.relative_to(ROOT)),
            str(DANGANRONPA_MISSING_MEDIA.relative_to(ROOT)),
            str(DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.relative_to(ROOT)),
            str(SOURCE_DETAIL.relative_to(ROOT)),
            str(SOURCE_DISCOVERY.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_REVIEW_BATCHES.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_ACTION_QUEUE.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_STORE_BOTTLENECKS.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_FOCUS_PACKS.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_FOCUS_TEMPLATE.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT.relative_to(ROOT)),
            str(SOURCE_DISCOVERY_ROADMAP.relative_to(ROOT)),
            str(SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.relative_to(ROOT)),
            str(OFFICIAL_DETAIL_REVIEW_BATCHES.relative_to(ROOT)),
            str(METADATA_BACKLOG.relative_to(ROOT)),
            str(METADATA_REVIEW_BATCHES.relative_to(ROOT)),
            str(METADATA_ACTION_QUEUE.relative_to(ROOT)),
            str(CONFIRMED_IMPORT_READINESS.relative_to(ROOT)),
            str(EXECUTION_PLAN.relative_to(ROOT)),
            str(IMAGE_ENRICHMENT_BATCHES.relative_to(ROOT)),
            str(DEDUPLICATION.relative_to(ROOT)),
            str(NAME_DUPLICATE_AUDIT.relative_to(ROOT)),
            str(DEDUPLICATION_ACTION_QUEUE.relative_to(ROOT)),
            str(DEDUPLICATION_FAST_REVIEW.relative_to(ROOT)),
            str(DEDUPLICATION_CONFIRMED_TEMPLATE.relative_to(ROOT)),
            str(DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN.relative_to(ROOT)),
            str(ANIMATION_CATEGORIES.relative_to(ROOT)),
            str(ANIMATION_CATEGORY_COVERAGE_AUDIT.relative_to(ROOT)),
            str(ANIMATION_CATEGORY_REVIEW_BATCHES.relative_to(ROOT)),
            str(ANIMATION_CATEGORY_ACTION_QUEUE.relative_to(ROOT)),
            str(ANIMATION_CATEGORY_SPLIT_REVIEW.relative_to(ROOT)),
            str(ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_HISTORY.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_METADATA_ACTION_QUEUE.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_METADATA_FAST_REVIEW.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_HISTORICAL_ROADMAP.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_REISSUE_DEDUPLICATION.relative_to(ROOT)),
            str(ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE.relative_to(ROOT)),
            str(OPERATIONS_REPORT.relative_to(ROOT)),
            str(AGENT_WORK_QUEUE.relative_to(ROOT)),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(update_reports(write=args.write), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
