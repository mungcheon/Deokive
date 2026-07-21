import 'package:flutter/material.dart';

class AppIconOption {
  final String key;
  final IconData icon;
  final String label;
  final String group;

  const AppIconOption({
    required this.key,
    required this.icon,
    required this.label,
    required this.group,
  });
}

class AppIconCatalog {
  static const List<AppIconOption> folderIcons = [
    // Storage
    AppIconOption(
        key: 'folder', icon: Icons.folder_rounded, label: '기본 폴더', group: '보관'),
    AppIconOption(
        key: 'folder_open',
        icon: Icons.folder_open_rounded,
        label: '열린 폴더',
        group: '보관'),
    AppIconOption(
        key: 'folder_copy',
        icon: Icons.folder_copy_rounded,
        label: '폴더 묶음',
        group: '보관'),
    AppIconOption(
        key: 'folder_special',
        icon: Icons.folder_special_rounded,
        label: '스페셜 폴더',
        group: '보관'),
    AppIconOption(
        key: 'create_new_folder',
        icon: Icons.create_new_folder_rounded,
        label: '새 폴더',
        group: '보관'),
    AppIconOption(
        key: 'inventory',
        icon: Icons.inventory_2_rounded,
        label: '보관함',
        group: '보관'),
    AppIconOption(
        key: 'category',
        icon: Icons.category_rounded,
        label: '분류',
        group: '보관'),
    AppIconOption(
        key: 'package',
        icon: Icons.inventory_rounded,
        label: '패키지',
        group: '보관'),
    AppIconOption(
        key: 'warehouse',
        icon: Icons.warehouse_rounded,
        label: '창고',
        group: '보관'),
    AppIconOption(
        key: 'archive',
        icon: Icons.archive_rounded,
        label: '아카이브',
        group: '보관'),
    AppIconOption(
        key: 'inbox', icon: Icons.inbox_rounded, label: '수납함', group: '보관'),
    AppIconOption(
        key: 'all_inbox',
        icon: Icons.all_inbox_rounded,
        label: '전체 수납',
        group: '보관'),
    AppIconOption(
        key: 'cloud', icon: Icons.cloud_rounded, label: '클라우드', group: '보관'),
    AppIconOption(
        key: 'source', icon: Icons.source_rounded, label: '자료함', group: '보관'),
    AppIconOption(
        key: 'checklist',
        icon: Icons.checklist_rounded,
        label: '체크리스트',
        group: '보관'),
    AppIconOption(
        key: 'dashboard',
        icon: Icons.dashboard_rounded,
        label: '대시보드',
        group: '보관'),
    AppIconOption(
        key: 'shelves',
        icon: Icons.view_stream_rounded,
        label: '선반',
        group: '보관'),
    AppIconOption(
        key: 'dresser',
        icon: Icons.table_bar_rounded,
        label: '서랍장',
        group: '보관'),
    AppIconOption(
        key: 'view_kanban',
        icon: Icons.view_kanban_rounded,
        label: '칸반 보드',
        group: '보관'),
    AppIconOption(
        key: 'analytics',
        icon: Icons.analytics_rounded,
        label: '통계',
        group: '보관'),
    AppIconOption(
        key: 'bar_chart',
        icon: Icons.bar_chart_rounded,
        label: '차트',
        group: '보관'),
    AppIconOption(
        key: 'bookmark',
        icon: Icons.bookmark_rounded,
        label: '북마크',
        group: '보관'),
    AppIconOption(
        key: 'label_tag', icon: Icons.label_rounded, label: '라벨', group: '보관'),

    // Goods
    AppIconOption(
        key: 'bag',
        icon: Icons.shopping_bag_rounded,
        label: '굿즈백',
        group: '굿즈'),
    AppIconOption(
        key: 'backpack',
        icon: Icons.backpack_rounded,
        label: '백팩',
        group: '굿즈'),
    AppIconOption(
        key: 'basket',
        icon: Icons.shopping_basket_rounded,
        label: '바구니',
        group: '굿즈'),
    AppIconOption(
        key: 'cart',
        icon: Icons.shopping_cart_rounded,
        label: '장바구니',
        group: '굿즈'),
    AppIconOption(
        key: 'shipping',
        icon: Icons.local_shipping_rounded,
        label: '배송',
        group: '굿즈'),
    AppIconOption(
        key: 'receipt',
        icon: Icons.receipt_long_rounded,
        label: '구매내역',
        group: '굿즈'),
    AppIconOption(
        key: 'payments',
        icon: Icons.payments_rounded,
        label: '결제',
        group: '굿즈'),
    AppIconOption(
        key: 'wallet',
        icon: Icons.account_balance_wallet_rounded,
        label: '예산',
        group: '굿즈'),
    AppIconOption(
        key: 'discount',
        icon: Icons.discount_rounded,
        label: '할인',
        group: '굿즈'),
    AppIconOption(
        key: 'membership',
        icon: Icons.card_membership_rounded,
        label: '멤버십 카드',
        group: '굿즈'),
    AppIconOption(
        key: 'add_cart',
        icon: Icons.add_shopping_cart_rounded,
        label: '구매 예정',
        group: '굿즈'),
    AppIconOption(
        key: 'gift', icon: Icons.redeem_rounded, label: '선물', group: '굿즈'),
    AppIconOption(
        key: 'gift_card',
        icon: Icons.card_giftcard_rounded,
        label: '기프트',
        group: '굿즈'),
    AppIconOption(
        key: 'ticket',
        icon: Icons.confirmation_number_rounded,
        label: '티켓',
        group: '굿즈'),
    AppIconOption(
        key: 'activity',
        icon: Icons.local_activity_rounded,
        label: '이벤트권',
        group: '굿즈'),
    AppIconOption(
        key: 'tag', icon: Icons.sell_rounded, label: '태그', group: '굿즈'),
    AppIconOption(
        key: 'local_offer',
        icon: Icons.local_offer_rounded,
        label: '라벨',
        group: '굿즈'),
    AppIconOption(
        key: 'loyalty', icon: Icons.loyalty_rounded, label: '멤버십', group: '굿즈'),
    AppIconOption(
        key: 'qr', icon: Icons.qr_code_2_rounded, label: '바코드', group: '굿즈'),
    AppIconOption(
        key: 'pin', icon: Icons.push_pin_rounded, label: '핀/뱃지', group: '굿즈'),
    AppIconOption(
        key: 'medal',
        icon: Icons.military_tech_rounded,
        label: '메달',
        group: '굿즈'),
    AppIconOption(
        key: 'keyring', icon: Icons.key_rounded, label: '키링', group: '굿즈'),
    AppIconOption(
        key: 'watch', icon: Icons.watch_rounded, label: '시계', group: '굿즈'),
    AppIconOption(
        key: 'checkroom',
        icon: Icons.checkroom_rounded,
        label: '의류',
        group: '굿즈'),
    AppIconOption(
        key: 'style', icon: Icons.style_rounded, label: '카드/포카', group: '굿즈'),
    AppIconOption(
        key: 'badge', icon: Icons.badge_rounded, label: '명찰', group: '굿즈'),
    AppIconOption(
        key: 'magnet',
        icon: Icons.attractions_rounded,
        label: '마그넷',
        group: '굿즈'),
    AppIconOption(
        key: 'bubble_chart',
        icon: Icons.bubble_chart_rounded,
        label: '랜덤팩',
        group: '굿즈'),
    AppIconOption(
        key: 'apparel',
        icon: Icons.dry_cleaning_rounded,
        label: '패션',
        group: '굿즈'),
    AppIconOption(
        key: 'laundry',
        icon: Icons.local_laundry_service_rounded,
        label: '패브릭',
        group: '굿즈'),
    AppIconOption(
        key: 'coffee_mug',
        icon: Icons.coffee_rounded,
        label: '머그컵',
        group: '굿즈'),
    AppIconOption(
        key: 'acrylic_stand',
        icon: Icons.view_in_ar_rounded,
        label: '아크릴 스탠드',
        group: '굿즈'),
    AppIconOption(
        key: 'clear_file',
        icon: Icons.file_copy_rounded,
        label: '클리어 파일',
        group: '굿즈'),
    AppIconOption(
        key: 'can_badge',
        icon: Icons.radio_button_checked_rounded,
        label: '캔뱃지',
        group: '굿즈'),
    AppIconOption(
        key: 'plush',
        icon: Icons.smart_toy_rounded,
        label: '누이/인형',
        group: '굿즈'),
    AppIconOption(
        key: 'figure', icon: Icons.category_rounded, label: '피규어', group: '굿즈'),
    AppIconOption(
        key: 'acrylic_keyring',
        icon: Icons.vpn_key_rounded,
        label: '아크릴 키링',
        group: '굿즈'),
    AppIconOption(
        key: 'trading_card',
        icon: Icons.credit_card_rounded,
        label: '트레이딩 카드',
        group: '굿즈'),
    AppIconOption(
        key: 'postcard',
        icon: Icons.markunread_mailbox_rounded,
        label: '엽서',
        group: '굿즈'),
    AppIconOption(
        key: 'sticker',
        icon: Icons.sticky_note_2_rounded,
        label: '스티커',
        group: '굿즈'),
    AppIconOption(
        key: 'towel',
        icon: Icons.dry_cleaning_rounded,
        label: '타월',
        group: '굿즈'),
    AppIconOption(
        key: 'pouch',
        icon: Icons.work_rounded,
        label: '파우치',
        group: '굿즈'),
    AppIconOption(
        key: 'standee',
        icon: Icons.web_asset_rounded,
        label: '스탠디',
        group: '굿즈'),
    AppIconOption(
        key: 'blind_box',
        icon: Icons.inventory_2_rounded,
        label: '블라인드 박스',
        group: '굿즈'),
    AppIconOption(
        key: 'lottery_prize',
        icon: Icons.confirmation_number_rounded,
        label: '쿠지 경품',
        group: '굿즈'),
    AppIconOption(
        key: 'limited_goods',
        icon: Icons.local_fire_department_rounded,
        label: '한정 굿즈',
        group: '굿즈'),
    AppIconOption(
        key: 'collab_goods',
        icon: Icons.handshake_rounded,
        label: '콜라보',
        group: '굿즈'),
    AppIconOption(
        key: 'preorder',
        icon: Icons.event_available_rounded,
        label: '예약 굿즈',
        group: '굿즈'),

    // Gallery
    AppIconOption(
        key: 'photo_album',
        icon: Icons.photo_library_rounded,
        label: '사진첩',
        group: '사진첩'),
    AppIconOption(
        key: 'collections',
        icon: Icons.collections_rounded,
        label: '앨범',
        group: '사진첩'),
    AppIconOption(
        key: 'collections_bookmark',
        icon: Icons.collections_bookmark_rounded,
        label: '컬렉션',
        group: '사진첩'),
    AppIconOption(
        key: 'photo', icon: Icons.photo_rounded, label: '사진', group: '사진첩'),
    AppIconOption(
        key: 'portrait',
        icon: Icons.portrait_rounded,
        label: '프로필 사진',
        group: '사진첩'),
    AppIconOption(
        key: 'image', icon: Icons.image_rounded, label: '이미지', group: '사진첩'),
    AppIconOption(
        key: 'image_search',
        icon: Icons.image_search_rounded,
        label: '이미지 검색',
        group: '사진첩'),
    AppIconOption(
        key: 'camera',
        icon: Icons.photo_camera_rounded,
        label: '카메라',
        group: '사진첩'),
    AppIconOption(
        key: 'camera_back',
        icon: Icons.photo_camera_back_rounded,
        label: '촬영 사진',
        group: '사진첩'),
    AppIconOption(
        key: 'frame',
        icon: Icons.filter_frames_rounded,
        label: '프레임',
        group: '사진첩'),
    AppIconOption(
        key: 'poster',
        icon: Icons.image_aspect_ratio_rounded,
        label: '포스터',
        group: '사진첩'),
    AppIconOption(
        key: 'view_carousel',
        icon: Icons.view_carousel_rounded,
        label: '카드 진열',
        group: '사진첩'),
    AppIconOption(
        key: 'grid', icon: Icons.grid_view_rounded, label: '그리드', group: '사진첩'),
    AppIconOption(
        key: 'display_case',
        icon: Icons.view_quilt_rounded,
        label: '진열장',
        group: '사진첩'),
    AppIconOption(
        key: 'wallpaper',
        icon: Icons.wallpaper_rounded,
        label: '배경사진',
        group: '사진첩'),
    AppIconOption(
        key: 'photo_filter',
        icon: Icons.filter_rounded,
        label: '필터',
        group: '사진첩'),
    AppIconOption(
        key: 'compare', icon: Icons.compare_rounded, label: '비교', group: '사진첩'),
    AppIconOption(
        key: 'burst',
        icon: Icons.burst_mode_rounded,
        label: '연속사진',
        group: '사진첩'),
    AppIconOption(
        key: 'add_photo',
        icon: Icons.add_photo_alternate_rounded,
        label: '사진 추가',
        group: '사진첩'),
    AppIconOption(
        key: 'slideshow',
        icon: Icons.slideshow_rounded,
        label: '슬라이드',
        group: '사진첩'),
    AppIconOption(
        key: 'panorama',
        icon: Icons.panorama_rounded,
        label: '파노라마',
        group: '사진첩'),
    AppIconOption(
        key: 'screenshot_album',
        icon: Icons.screenshot_rounded,
        label: '스크린샷',
        group: '사진첩'),
    AppIconOption(
        key: 'scan_album',
        icon: Icons.document_scanner_rounded,
        label: '스캔',
        group: '사진첩'),
    AppIconOption(
        key: 'detail_shot',
        icon: Icons.center_focus_strong_rounded,
        label: '상세샷',
        group: '사진첩'),
    AppIconOption(
        key: 'unboxing_photo',
        icon: Icons.unarchive_rounded,
        label: '언박싱',
        group: '사진첩'),
    AppIconOption(
        key: 'wishlist_photo',
        icon: Icons.add_photo_alternate_rounded,
        label: '위시 사진',
        group: '사진첩'),

    // Character
    AppIconOption(
        key: 'face', icon: Icons.face_rounded, label: '캐릭터', group: '캐릭터'),
    AppIconOption(
        key: 'mood', icon: Icons.mood_rounded, label: '표정', group: '캐릭터'),
    AppIconOption(
        key: 'person', icon: Icons.person_rounded, label: '인물', group: '캐릭터'),
    AppIconOption(
        key: 'group', icon: Icons.groups_rounded, label: '그룹', group: '캐릭터'),
    AppIconOption(
        key: 'theater',
        icon: Icons.theater_comedy_rounded,
        label: '장르',
        group: '캐릭터'),
    AppIconOption(
        key: 'pets', icon: Icons.pets_rounded, label: '동물 캐릭터', group: '캐릭터'),
    AppIconOption(
        key: 'toys', icon: Icons.toys_rounded, label: '인형', group: '캐릭터'),
    AppIconOption(
        key: 'smart_toy',
        icon: Icons.smart_toy_rounded,
        label: '피규어',
        group: '캐릭터'),
    AppIconOption(
        key: 'miniature',
        icon: Icons.view_in_ar_rounded,
        label: '미니어처',
        group: '캐릭터'),
    AppIconOption(
        key: 'extension',
        icon: Icons.extension_rounded,
        label: '퍼즐',
        group: '캐릭터'),
    AppIconOption(
        key: 'casino', icon: Icons.casino_rounded, label: '랜덤', group: '캐릭터'),
    AppIconOption(
        key: 'sports_mma',
        icon: Icons.sports_mma_rounded,
        label: '액션',
        group: '캐릭터'),
    AppIconOption(
        key: 'emoji_people',
        icon: Icons.emoji_people_rounded,
        label: '포즈',
        group: '캐릭터'),
    AppIconOption(
        key: 'diversity',
        icon: Icons.diversity_3_rounded,
        label: '유닛',
        group: '캐릭터'),
    AppIconOption(
        key: 'accessibility',
        icon: Icons.accessibility_new_rounded,
        label: '전신',
        group: '캐릭터'),
    AppIconOption(
        key: 'main_character',
        icon: Icons.person_pin_rounded,
        label: '대표 캐릭터',
        group: '캐릭터'),
    AppIconOption(
        key: 'unit',
        icon: Icons.diversity_2_rounded,
        label: '유닛',
        group: '캐릭터'),
    AppIconOption(
        key: 'voice',
        icon: Icons.record_voice_over_rounded,
        label: '보이스',
        group: '캐릭터'),
    AppIconOption(
        key: 'costume',
        icon: Icons.face_retouching_natural_rounded,
        label: '의상',
        group: '캐릭터'),

    // Status
    AppIconOption(
        key: 'favorite',
        icon: Icons.favorite_rounded,
        label: '최애',
        group: '상태'),
    AppIconOption(
        key: 'star', icon: Icons.star_rounded, label: '별표', group: '상태'),
    AppIconOption(
        key: 'hobby_sparkle',
        icon: Icons.auto_awesome_rounded,
        label: '반짝',
        group: '상태'),
    AppIconOption(
        key: 'diamond', icon: Icons.diamond_rounded, label: '레어', group: '상태'),
    AppIconOption(
        key: 'celebration',
        icon: Icons.celebration_rounded,
        label: '기념',
        group: '상태'),
    AppIconOption(
        key: 'trophy',
        icon: Icons.emoji_events_rounded,
        label: '트로피',
        group: '상태'),
    AppIconOption(
        key: 'premium',
        icon: Icons.workspace_premium_rounded,
        label: '프리미엄',
        group: '상태'),
    AppIconOption(
        key: 'verified',
        icon: Icons.verified_rounded,
        label: '확정',
        group: '상태'),
    AppIconOption(
        key: 'shield', icon: Icons.shield_rounded, label: '보호', group: '상태'),
    AppIconOption(
        key: 'lock', icon: Icons.lock_rounded, label: '비공개', group: '상태'),
    AppIconOption(
        key: 'visibility',
        icon: Icons.visibility_rounded,
        label: '공개',
        group: '상태'),
    AppIconOption(
        key: 'bolt', icon: Icons.bolt_rounded, label: '빠른 정리', group: '상태'),
    AppIconOption(
        key: 'flag', icon: Icons.flag_rounded, label: '목표', group: '상태'),
    AppIconOption(
        key: 'new_releases',
        icon: Icons.new_releases_rounded,
        label: '신상',
        group: '상태'),
    AppIconOption(
        key: 'history', icon: Icons.history_rounded, label: '기록', group: '상태'),
    AppIconOption(
        key: 'owned',
        icon: Icons.check_box_rounded,
        label: '보유',
        group: '상태'),
    AppIconOption(
        key: 'wishlist',
        icon: Icons.favorite_border_rounded,
        label: '위시',
        group: '상태'),
    AppIconOption(
        key: 'trade_ready',
        icon: Icons.swap_horiz_rounded,
        label: '교환 가능',
        group: '상태'),
    AppIconOption(
        key: 'sold_out',
        icon: Icons.remove_shopping_cart_rounded,
        label: '품절',
        group: '상태'),
    AppIconOption(
        key: 'sealed',
        icon: Icons.inventory_rounded,
        label: '미개봉',
        group: '상태'),
    AppIconOption(
        key: 'opened',
        icon: Icons.outbox_rounded,
        label: '개봉',
        group: '상태'),

    // Hobby
    AppIconOption(
        key: 'music', icon: Icons.music_note_rounded, label: '음악', group: '취향'),
    AppIconOption(
        key: 'album', icon: Icons.album_rounded, label: '음반', group: '취향'),
    AppIconOption(
        key: 'headphones',
        icon: Icons.headphones_rounded,
        label: '헤드폰',
        group: '취향'),
    AppIconOption(
        key: 'game',
        icon: Icons.sports_esports_rounded,
        label: '게임',
        group: '취향'),
    AppIconOption(
        key: 'book', icon: Icons.book_rounded, label: '책', group: '취향'),
    AppIconOption(
        key: 'library',
        icon: Icons.local_library_rounded,
        label: '도서관',
        group: '취향'),
    AppIconOption(
        key: 'stories',
        icon: Icons.auto_stories_rounded,
        label: '스토리',
        group: '취향'),
    AppIconOption(
        key: 'diary',
        icon: Icons.menu_book_rounded,
        label: '다이어리',
        group: '취향'),
    AppIconOption(
        key: 'sticky_note',
        icon: Icons.sticky_note_2_rounded,
        label: '메모',
        group: '취향'),
    AppIconOption(
        key: 'draw', icon: Icons.draw_rounded, label: '그림', group: '취향'),
    AppIconOption(
        key: 'palette', icon: Icons.palette_rounded, label: '아트', group: '취향'),
    AppIconOption(
        key: 'stage',
        icon: Icons.theaters_rounded,
        label: '무대',
        group: '취향'),
    AppIconOption(
        key: 'stream',
        icon: Icons.live_tv_rounded,
        label: '방송',
        group: '취향'),
    AppIconOption(
        key: 'microphone',
        icon: Icons.mic_rounded,
        label: '마이크',
        group: '취향'),
    AppIconOption(
        key: 'cinema',
        icon: Icons.movie_rounded,
        label: '영화',
        group: '취향'),
    AppIconOption(
        key: 'animation',
        icon: Icons.animation_rounded,
        label: '애니메이션',
        group: '취향'),
    AppIconOption(
        key: 'brush', icon: Icons.brush_rounded, label: '브러시', group: '취향'),
    AppIconOption(
        key: 'movie', icon: Icons.movie_rounded, label: '영상', group: '취향'),
    AppIconOption(
        key: 'tv', icon: Icons.live_tv_rounded, label: '방송', group: '취향'),
    AppIconOption(
        key: 'mic', icon: Icons.mic_rounded, label: '라이브', group: '취향'),
    AppIconOption(
        key: 'campaign',
        icon: Icons.campaign_rounded,
        label: '응원',
        group: '취향'),
    AppIconOption(
        key: 'flashlight',
        icon: Icons.flashlight_on_rounded,
        label: '펜라이트',
        group: '취향'),
    AppIconOption(
        key: 'podcasts',
        icon: Icons.podcasts_rounded,
        label: '라디오',
        group: '취향'),
    AppIconOption(
        key: 'lyrics', icon: Icons.lyrics_rounded, label: '가사', group: '취향'),
    AppIconOption(
        key: 'sparkle',
        icon: Icons.auto_awesome_rounded,
        label: '반짝임',
        group: '취향'),
    AppIconOption(
        key: 'hobby_diamond',
        icon: Icons.diamond_rounded,
        label: '레어',
        group: '취향'),
    AppIconOption(
        key: 'hobby_premium',
        icon: Icons.workspace_premium_rounded,
        label: '프리미엄',
        group: '취향'),

    // Events
    AppIconOption(
        key: 'calendar',
        icon: Icons.calendar_month_rounded,
        label: '캘린더',
        group: '일정'),
    AppIconOption(
        key: 'event', icon: Icons.event_rounded, label: '이벤트', group: '일정'),
    AppIconOption(
        key: 'event_note',
        icon: Icons.event_note_rounded,
        label: '일정표',
        group: '일정'),
    AppIconOption(
        key: 'date_range',
        icon: Icons.date_range_rounded,
        label: '기간',
        group: '일정'),
    AppIconOption(
        key: 'schedule',
        icon: Icons.schedule_rounded,
        label: '시간',
        group: '일정'),
    AppIconOption(
        key: 'article', icon: Icons.article_rounded, label: '게시글', group: '일정'),
    AppIconOption(
        key: 'forum', icon: Icons.forum_rounded, label: '게시판', group: '일정'),
    AppIconOption(
        key: 'chat', icon: Icons.chat_bubble_rounded, label: '채팅', group: '일정'),
    AppIconOption(
        key: 'news', icon: Icons.newspaper_rounded, label: '뉴스', group: '일정'),
    AppIconOption(
        key: 'feed', icon: Icons.feed_rounded, label: '피드', group: '일정'),
    AppIconOption(
        key: 'mail', icon: Icons.mail_rounded, label: '메일', group: '일정'),
    AppIconOption(
        key: 'notice',
        icon: Icons.notifications_rounded,
        label: '알림',
        group: '일정'),
    AppIconOption(
        key: 'alarm', icon: Icons.alarm_rounded, label: '리마인더', group: '일정'),
    AppIconOption(
        key: 'check_circle',
        icon: Icons.check_circle_rounded,
        label: '완료',
        group: '일정'),
    AppIconOption(
        key: 'pending',
        icon: Icons.pending_actions_rounded,
        label: '대기',
        group: '일정'),
    AppIconOption(
        key: 'schedule_history',
        icon: Icons.history_rounded,
        label: '기록',
        group: '일정'),
    AppIconOption(
        key: 'update', icon: Icons.update_rounded, label: '업데이트', group: '일정'),

    // Place and food
    AppIconOption(
        key: 'storefront',
        icon: Icons.storefront_rounded,
        label: '스토어',
        group: '장소'),
    AppIconOption(
        key: 'mall', icon: Icons.local_mall_rounded, label: '쇼핑몰', group: '장소'),
    AppIconOption(
        key: 'place', icon: Icons.place_rounded, label: '장소', group: '장소'),
    AppIconOption(
        key: 'map', icon: Icons.map_rounded, label: '지도', group: '장소'),
    AppIconOption(
        key: 'home', icon: Icons.home_rounded, label: '집', group: '장소'),
    AppIconOption(
        key: 'cafe', icon: Icons.local_cafe_rounded, label: '카페', group: '장소'),
    AppIconOption(
        key: 'cake', icon: Icons.cake_rounded, label: '케이크', group: '장소'),
    AppIconOption(
        key: 'bakery',
        icon: Icons.bakery_dining_rounded,
        label: '베이커리',
        group: '장소'),
    AppIconOption(
        key: 'cookie', icon: Icons.cookie_rounded, label: '쿠키', group: '장소'),
    AppIconOption(
        key: 'icecream',
        icon: Icons.icecream_rounded,
        label: '아이스크림',
        group: '장소'),
    AppIconOption(
        key: 'ramen',
        icon: Icons.ramen_dining_rounded,
        label: '라멘',
        group: '장소'),
    AppIconOption(
        key: 'drink',
        icon: Icons.local_drink_rounded,
        label: '컵/텀블러',
        group: '장소'),
    AppIconOption(
        key: 'restaurant',
        icon: Icons.restaurant_rounded,
        label: '식사',
        group: '장소'),
    AppIconOption(
        key: 'fastfood',
        icon: Icons.fastfood_rounded,
        label: '간식',
        group: '장소'),
    AppIconOption(
        key: 'museum', icon: Icons.museum_rounded, label: '전시', group: '장소'),
    AppIconOption(
        key: 'festival',
        icon: Icons.festival_rounded,
        label: '페스티벌',
        group: '장소'),
    AppIconOption(
        key: 'flight',
        icon: Icons.flight_takeoff_rounded,
        label: '원정',
        group: '장소'),
    AppIconOption(
        key: 'pin_drop', icon: Icons.pin_drop_rounded, label: '핀', group: '장소'),
    AppIconOption(
        key: 'explore', icon: Icons.explore_rounded, label: '탐색', group: '장소'),
    AppIconOption(
        key: 'route', icon: Icons.route_rounded, label: '루트', group: '장소'),

    // Nature
    AppIconOption(
        key: 'flower',
        icon: Icons.local_florist_rounded,
        label: '꽃',
        group: '분위기'),
    AppIconOption(
        key: 'spa', icon: Icons.spa_rounded, label: '힐링', group: '분위기'),
    AppIconOption(
        key: 'park', icon: Icons.park_rounded, label: '공원', group: '분위기'),
    AppIconOption(
        key: 'sun', icon: Icons.wb_sunny_rounded, label: '햇살', group: '분위기'),
    AppIconOption(
        key: 'moon', icon: Icons.nightlight_rounded, label: '밤', group: '분위기'),
    AppIconOption(
        key: 'rocket',
        icon: Icons.rocket_launch_rounded,
        label: '출발',
        group: '분위기'),
    AppIconOption(
        key: 'travel',
        icon: Icons.travel_explore_rounded,
        label: '여행',
        group: '분위기'),
    AppIconOption(
        key: 'cloudy',
        icon: Icons.cloud_queue_rounded,
        label: '구름',
        group: '분위기'),
    AppIconOption(
        key: 'water',
        icon: Icons.water_drop_rounded,
        label: '물방울',
        group: '분위기'),
    AppIconOption(
        key: 'weather_bolt',
        icon: Icons.bolt_rounded,
        label: '번개',
        group: '분위기'),
  ];
}
