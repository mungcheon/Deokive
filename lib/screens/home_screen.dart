import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/board_posts.dart';
import '../l10n/app_strings.dart';
import '../models/badge_item.dart';
import '../models/goods_catalog_entry.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_avatar.dart';
import '../widgets/deokive_header_title.dart';
import '../widgets/showcase_background.dart';
import 'avatar_editor_screen.dart';
import 'badge_screen.dart';
import 'catalog_database_screen.dart';
import 'news_detail_screen.dart';
import 'stats_screen.dart' show StatsContent;

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final PageController _pageController = PageController(viewportFraction: 0.94);
  int _currentPage = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _goToPreviousPage() {
    if (_currentPage > 0) {
      _pageController.previousPage(
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOut,
      );
    }
  }

  void _goToNextPage(int itemCount) {
    if (_currentPage < itemCount - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;
        final equippedBadges = appState.equippedBadges;

        final boardPosts = appState.boardPosts;
        // Marquee: latest notice-tagged posts only, max 5, newest first.
        // Keeps the scrolling strip short and focused on real announcements
        // instead of every info-bot post.
        final noticeSorted = boardPosts
            .where((p) => p.tag == BoardPostTag.notice)
            .toList()
          ..sort((a, b) => b.date.compareTo(a.date));
        final marqueeTitles = noticeSorted.take(5).map((p) => p.title).toList();

        // Tutorial slides — replaces the news/notice banner until live content
        // is in place. Each slide doubles as a feature walkthrough.
        final promoSlides = <Map<String, dynamic>>[
          {
            'title': '굿즈를 폴더에 정리해 보세요',
            'subtitle': '컬렉션을 캐릭터·IP별 폴더로 나눠 한눈에 관리할 수 있어요.',
            'icon': Icons.folder_special_rounded,
            'detailTitle': '굿즈를 폴더에 정리해 보세요',
            'detailDate': '사용 가이드',
            'detailContent': '1. 하단 탭 [폴더]로 이동\n'
                '2. 우측 상단 + 버튼으로 새 폴더 생성 (캐릭터·IP 단위 추천)\n'
                '3. 폴더 안에서 + 버튼으로 굿즈 추가\n\n'
                '👉 사고 싶은 아이템은 위시리스트 폴더에 따로 모아두면 결제 추적과 분리돼서 편해요.',
          },
          {
            'title': '위시리스트도 같이 관리',
            'subtitle': '아직 안 산 굿즈는 구매가 0원 상태로 따로 담아둘 수 있어요.',
            'icon': Icons.favorite_border_rounded,
            'detailTitle': '위시리스트도 같이 관리',
            'detailDate': '사용 가이드',
            'detailContent': 'DB에서 항목을 고를 때 내 굿즈함 대신 위시리스트를 선택할 수 있어요.\n\n'
                '위시리스트에 넣은 굿즈는 구매가 0원, 상태는 위시로 저장해서 실제 보유 굿즈 통계와 섞이지 않게 관리합니다.\n\n'
                '👉 사고 싶은 목록과 이미 가진 목록을 분리해두면 정리가 훨씬 편해요.',
          },
          {
            'title': '뱃지를 모아 등급을 올려보세요',
            'subtitle': '컬렉션 활동을 하면 자동으로 뱃지가 잠금 해제됩니다.',
            'icon': Icons.workspace_premium_rounded,
            'detailTitle': '뱃지를 모아 등급을 올려보세요',
            'detailDate': '사용 가이드',
            'detailContent': '굿즈 등록 수, 폴더 다양성, 출석 등 다양한 조건으로 뱃지가 잠금 해제돼요.\n\n'
                '획득한 뱃지는 홈 화면 프로필 카드 위 전시대에 장착할 수 있고, '
                '레벨이 올라갈수록 전시대 배경이 더 화려해져요.\n\n'
                '👉 홈 → 뱃지 카드를 눌러 전체 컬렉션 확인.',
          },
          {
            'title': '게시판에서 다른 덕후들과 소통',
            'subtitle': '정보봇이 굿즈 소식을 가져오고, 직접 글도 작성·저장할 수 있어요.',
            'icon': Icons.forum_rounded,
            'detailTitle': '게시판에서 다른 덕후들과 소통',
            'detailDate': '사용 가이드',
            'detailContent': '게시판 탭에서는 세 가지를 할 수 있어요.\n\n'
                '• 자유게시판: 정보봇이 자동으로 가져오는 공식 X 계정의 굿즈 소식 + 직접 작성하는 일반 글\n'
                '• 글 저장소: 내가 쓴 글과 좋아요·북마크한 글을 모아 보기\n'
                '• 행사 일정: 캘린더로 팝업·전시·이벤트 일정 확인\n\n'
                '👉 정보봇 글은 설정 언어에 맞춰 자동 번역돼서 표시돼요.',
          },
          {
            'title': '아바타와 프로필을 꾸며 보세요',
            'subtitle': '캐릭터를 커스터마이즈하고 컬렉션 전시대를 자랑할 수 있어요.',
            'icon': Icons.face_retouching_natural_rounded,
            'detailTitle': '아바타와 프로필을 꾸며 보세요',
            'detailDate': '사용 가이드',
            'detailContent': '홈 화면 프로필 카드의 아바타를 탭하면 편집기로 이동합니다.\n\n'
                '머리 스타일·의상 색·모자·망토·소품 등을 자유롭게 조합할 수 있고, '
                '뱃지 등급이 오를수록 더 화려한 전시대 배경이 자동으로 열립니다.\n\n'
                '👉 친구의 프로필 코드를 입력해서 서로의 컬렉션을 구경할 수도 있어요 (예정).',
          },
        ];

        return Scaffold(
          appBar: AppBar(
            title: const DeokiveHeaderTitle(),
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _NoticeMarquee(
                notices: marqueeTitles.where((s) => s.isNotEmpty).toList(),
                palette: palette,
              ),
              const SizedBox(height: 12),
              _MapleProfileCard(appState: appState, palette: palette),
              const SizedBox(height: 18),
              _BadgeShowcase(
                equippedBadges: equippedBadges,
                backgroundTier: appState
                    .effectiveShowcaseBgTier(appState.totalUnlockedBadgeLevel),
                onOpenBadges: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const BadgeScreen()),
                  );
                },
              ),
              const SizedBox(height: 18),
              _CatalogImportPanel(appState: appState, palette: palette),
              const SizedBox(height: 24),
              const Text(
                '덕카이브 시작 가이드',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 210,
                child: Column(
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          _BannerArrowButton(
                            icon: Icons.chevron_left,
                            onTap: _currentPage == 0 ? null : _goToPreviousPage,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: PageView.builder(
                              controller: _pageController,
                              itemCount: promoSlides.length,
                              onPageChanged: (index) =>
                                  setState(() => _currentPage = index),
                              itemBuilder: (context, index) {
                                final slide = promoSlides[index];
                                return _PromoSlideCard(
                                  title: slide['title'] as String,
                                  subtitle: slide['subtitle'] as String,
                                  icon: slide['icon'] as IconData,
                                  onTap: () {
                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (_) => NewsDetailScreen(
                                          title: slide['detailTitle'] as String,
                                          date: slide['detailDate'] as String,
                                          content:
                                              slide['detailContent'] as String,
                                        ),
                                      ),
                                    );
                                  },
                                );
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          _BannerArrowButton(
                            icon: Icons.chevron_right,
                            onTap: _currentPage == promoSlides.length - 1
                                ? null
                                : () => _goToNextPage(promoSlides.length),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(
                        promoSlides.length,
                        (index) => AnimatedContainer(
                          duration: const Duration(milliseconds: 180),
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          width: _currentPage == index ? 20 : 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: _currentPage == index
                                ? palette.primary
                                : palette.primary.withValues(alpha: 0.25),
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              const StatsContent(),
            ],
          ),
        );
      },
    );
  }
}

String _truncateNickname(String name) {
  if (name.runes.length <= 15) return name;
  return String.fromCharCodes(name.runes.take(15));
}

class _CatalogImportPanel extends StatelessWidget {
  final AppState appState;
  final DeokivePalette palette;

  const _CatalogImportPanel({
    required this.appState,
    required this.palette,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final entries = appState.curatedCatalogEntries;
    final health = _CatalogHealthSummary.from(entries);

    return LayoutBuilder(
      builder: (context, constraints) {
        return Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: palette.primary.withValues(alpha: 0.18)),
          ),
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 156),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: palette.primary.withValues(alpha: 0.14),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.dataset_outlined,
                        color: palette.primary,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '굿즈 DB',
                            maxLines: 1,
                            softWrap: false,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 5),
                          Row(
                            children: [
                              Expanded(
                                child: _CatalogMetaChip(
                                  label:
                                      '정리 ${_CatalogHealthSummary.formatCount(health.uniqueCount)}개',
                                  palette: palette,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                child: _CatalogMetaChip(
                                  label: '사진 ${health.imageCoverageLabel}',
                                  palette: palette,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  '중복과 예시 항목을 제외한 공개 DB에서 바로 추가해요.',
                  maxLines: 1,
                  softWrap: false,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
                    height: 1.35,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  height: 46,
                  child: FilledButton.icon(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const CatalogDatabaseScreen(),
                        ),
                      );
                    },
                    icon: const Icon(Icons.manage_search_rounded, size: 19),
                    label: const Text(
                      'DB 보기',
                      maxLines: 1,
                      softWrap: false,
                      overflow: TextOverflow.ellipsis,
                    ),
                    style: FilledButton.styleFrom(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _CatalogMetaChip extends StatelessWidget {
  final String label;
  final DeokivePalette palette;

  const _CatalogMetaChip({
    required this.label,
    required this.palette,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: palette.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: theme.textTheme.labelSmall?.copyWith(
          color: theme.colorScheme.onSurface.withValues(alpha: 0.68),
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _CatalogHealthSummary {
  final int uniqueCount;
  final int duplicateCount;
  final double imageCoverage;

  const _CatalogHealthSummary({
    required this.uniqueCount,
    required this.duplicateCount,
    required this.imageCoverage,
  });

  String get imageCoverageLabel => _formatCoverage(imageCoverage);

  static _CatalogHealthSummary from(List<GoodsCatalogEntry> entries) {
    final uniqueEntries = <GoodsCatalogEntry>[];
    final seenKeys = <String>{};

    for (final entry in entries) {
      if (_isExampleEntry(entry)) continue;

      final key = _identityKey(entry);
      if (seenKeys.add(key)) {
        uniqueEntries.add(entry);
      }
    }

    var imageCount = 0;

    for (final entry in uniqueEntries) {
      if (_hasRealDisplayImage(entry)) {
        imageCount += 1;
      }
    }

    final total = uniqueEntries.length;
    return _CatalogHealthSummary(
      uniqueCount: total,
      duplicateCount: entries.length - total,
      imageCoverage: total == 0 ? 0 : imageCount / total,
    );
  }

  static String _identityKey(GoodsCatalogEntry entry) {
    final barcode = entry.barcode?.trim() ?? '';
    if (barcode.isNotEmpty) return 'barcode:$barcode';

    final identityParts = [
      entry.affiliation,
      entry.seriesName ?? '',
      entry.nameKo,
      entry.nameJa ?? '',
      entry.category,
      entry.characterName,
      entry.subSeries ?? '',
    ].map((value) => value.trim().toLowerCase()).join('|');
    if (identityParts.replaceAll('|', '').isNotEmpty) {
      return 'identity:$identityParts';
    }

    final sourceUrl = entry.sourceUrl?.trim().toLowerCase() ?? '';
    if (sourceUrl.isNotEmpty) return 'source:$sourceUrl';

    return 'entry:${entry.id ?? entry.hashCode}';
  }

  static bool _isExampleEntry(GoodsCatalogEntry entry) {
    final values = [
      entry.nameKo,
      entry.nameJa ?? '',
      entry.nameEn ?? '',
      entry.category,
      entry.characterName,
      entry.affiliation,
      entry.seriesName ?? '',
      entry.subSeries ?? '',
      entry.sourceStore,
      entry.sourceUrl ?? '',
      entry.displayImagePath ?? '',
    ].map((value) => value.trim().toLowerCase());

    return values.any(_looksLikeExampleText);
  }

  static bool _hasRealDisplayImage(GoodsCatalogEntry entry) {
    final imagePath = (entry.displayImagePath ?? '').trim().toLowerCase();
    if (imagePath.isEmpty) return false;

    return !_looksLikeExampleText(imagePath);
  }

  static bool _looksLikeExampleText(String value) {
    if (value.isEmpty) return false;

    return [
      'sample',
      'example',
      'placeholder',
      'image_placeholder',
      'no_image',
      'no-image',
      'noimage',
      'dummy',
      'test-image',
      'fixture',
      'blank',
      'default-image',
      'default_image',
      'coming-soon',
      'coming_soon',
      '예시',
      '샘플',
      '테스트',
      '더미',
    ].any(value.contains);
  }

  static String _formatCoverage(double value) {
    return '${(value * 100).round()}%';
  }

  static String formatCount(int value) {
    final raw = value.toString();
    final buffer = StringBuffer();
    for (var i = 0; i < raw.length; i += 1) {
      final remaining = raw.length - i;
      buffer.write(raw[i]);
      if (remaining > 1 && remaining % 3 == 1) {
        buffer.write(',');
      }
    }
    return buffer.toString();
  }
}

class _MapleProfileCard extends StatelessWidget {
  final AppState appState;
  final DeokivePalette palette;

  const _MapleProfileCard({required this.appState, required this.palette});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLoggedIn = appState.isLoggedIn;
    final folderCount =
        appState.folders.where((f) => !f.isSystemWishlist).length;
    final goodsCount = appState.totalGoodsCount;
    final badgeCount = appState.totalUnlockedBadgeCount;
    final profileLevel = appState.totalUnlockedBadgeLevel;

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        color: theme.colorScheme.surface,
        border: Border.all(color: palette.primary.withValues(alpha: 0.22)),
        boxShadow: [
          BoxShadow(
            color: palette.primary.withValues(alpha: 0.08),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 18),
      child: Column(
        children: [
          _MapleAvatarStage(appState: appState, palette: palette),
          const SizedBox(height: 14),
          _LevelPill(level: profileLevel, palette: palette),
          const SizedBox(height: 10),
          Text(
            _truncateNickname(
                isLoggedIn ? appState.currentDisplayName : 'Guest Collector'),
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _StatTile(
                  icon: Icons.folder_rounded,
                  label: '폴더',
                  value: '$folderCount',
                  accent: palette.primary,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _StatTile(
                  icon: Icons.collections_bookmark_rounded,
                  label: '굿즈',
                  value: '$goodsCount',
                  accent: palette.accent,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _StatTile(
                  icon: Icons.military_tech_rounded,
                  label: '배지',
                  value: '$badgeCount',
                  accent: const Color(0xFFD4A656),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MapleAvatarStage extends StatelessWidget {
  final AppState appState;
  final DeokivePalette palette;

  const _MapleAvatarStage({required this.appState, required this.palette});

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(22),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const AvatarEditorScreen(),
              ),
            );
          },
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              color: palette.softSurface.withValues(alpha: 0.5),
              border: Border.all(
                color: palette.primary.withValues(alpha: 0.24),
                width: 1.4,
              ),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(22),
              child: DeokiveAvatar(
                palette: palette,
                padding: const EdgeInsets.fromLTRB(12, 24, 12, 6),
                bodyType: appState.avatarBodyType,
                backgroundType: appState.avatarBackgroundType,
                hairStyle: appState.avatarHairStyle,
                hairColorIndex: appState.avatarHairColorIndex,
                accentColorIndex: appState.avatarAccentColorIndex,
                outfitColorIndex: appState.avatarOutfitColorIndex,
                skinToneIndex: appState.avatarSkinToneIndex,
                hasHat: appState.avatarHasHat,
                hasCape: appState.avatarHasCape,
                hasHandheld: appState.avatarHasHandheld,
                hasBackRibbon: appState.avatarHasBackRibbon,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LevelPill extends StatelessWidget {
  final int level;
  final DeokivePalette palette;

  const _LevelPill({required this.level, required this.palette});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: palette.primary,
      ),
      child: Text(
        'Lv.$level',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 13,
          fontWeight: FontWeight.w900,
          letterSpacing: 0.6,
        ),
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color accent;

  const _StatTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.accent,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: accent.withValues(alpha: 0.26)),
      ),
      child: Column(
        children: [
          Icon(icon, size: 18, color: accent),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: Colors.grey.shade700,
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Badge Showcase ──────────────────────────────────────────────────────
//
// Each emblem = clean, consistent circle with the badge's own icon — kept
// simple so the icon is well visible. The *background* of the showcase
// gets fancier every 5 profile levels; the user can pick any unlocked tier
// from the badge collection screen.

class _BadgeShowcase extends StatelessWidget {
  final List<BadgeItem> equippedBadges;
  final int backgroundTier;
  final VoidCallback onOpenBadges;

  const _BadgeShowcase({
    required this.equippedBadges,
    required this.backgroundTier,
    required this.onOpenBadges,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    final strings = AppStrings.of(context.read<AppState>().appLanguage);

    final onSurface = theme.colorScheme.onSurface;
    final tier = backgroundTier;

    return ClipRRect(
      borderRadius: BorderRadius.circular(28),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          color: theme.colorScheme.surface,
          border: Border.all(color: palette.primary.withValues(alpha: 0.22)),
          boxShadow: [
            BoxShadow(
              color: palette.primary.withValues(alpha: 0.08),
              blurRadius: 14,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Stack(
          children: [
            // Decorative background that scales with profile level.
            Positioned.fill(
              child: CustomPaint(
                painter: ShowcaseTierBackgroundPainter(
                  tier: tier,
                  primary: palette.primary,
                  accent: palette.accent,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
              child: Column(
                children: [
                  Row(
                    children: [
                      Icon(Icons.workspace_premium_outlined,
                          color: palette.primary, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          strings.homeBadgeShowcase,
                          style: TextStyle(
                            color: onSurface,
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      IconButton(
                        tooltip: '배지 관리',
                        visualDensity: VisualDensity.compact,
                        color: onSurface.withValues(alpha: 0.7),
                        onPressed: onOpenBadges,
                        icon: const Icon(Icons.tune_rounded),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: List.generate(3, (index) {
                      if (index < equippedBadges.length) {
                        return _SimpleEmblemSlot(badge: equippedBadges[index]);
                      }
                      return _EmptyEmblemSlot(accent: palette.primary);
                    }),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SimpleEmblemSlot extends StatelessWidget {
  final BadgeItem badge;

  const _SimpleEmblemSlot({required this.badge});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      width: 96,
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: theme.colorScheme.surface,
              border: Border.all(
                color: badge.color.withValues(alpha: 0.45),
                width: 1.6,
              ),
              boxShadow: [
                BoxShadow(
                  color: badge.color.withValues(alpha: 0.18),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Icon(badge.icon, color: badge.color, size: 30),
          ),
          const SizedBox(height: 8),
          Text(
            badge.title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: theme.colorScheme.onSurface,
              fontSize: 11.5,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyEmblemSlot extends StatelessWidget {
  final Color accent;

  const _EmptyEmblemSlot({required this.accent});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      width: 96,
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.04),
              border: Border.all(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.16),
                width: 1.4,
              ),
            ),
            child: Icon(
              Icons.add_rounded,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.35),
              size: 26,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '빈 슬롯',
            style: TextStyle(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.50),
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Banner widgets ──────────────────────────────────────────────────────

class _BannerArrowButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;

  const _BannerArrowButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final palette = Theme.of(context).extension<DeokivePalette>()!;
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Ink(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          color: onTap == null
              ? Colors.grey.shade200
              : palette.primary.withValues(alpha: 0.10),
          shape: BoxShape.circle,
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Icon(
          icon,
          size: 20,
          color: onTap == null ? Colors.grey : palette.primary,
        ),
      ),
    );
  }
}

class _PromoSlideCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  const _PromoSlideCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final palette = Theme.of(context).extension<DeokivePalette>()!;
    return InkWell(
      borderRadius: BorderRadius.circular(24),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: palette.primary.withValues(alpha: 0.14),
              child: Icon(icon, color: palette.primary),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 16,
                      height: 1.18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.grey.shade700,
                      height: 1.35,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── MapleStory-style scrolling announcement marquee ─────────────────────

class _NoticeMarquee extends StatefulWidget {
  final List<String> notices;
  final DeokivePalette palette;

  const _NoticeMarquee({required this.notices, required this.palette});

  @override
  State<_NoticeMarquee> createState() => _NoticeMarqueeState();
}

class _NoticeMarqueeState extends State<_NoticeMarquee>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 14),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.notices.isEmpty) return const SizedBox.shrink();
    final palette = widget.palette;
    final marqueeText = widget.notices.join('   ✦   ');

    final deepThemeColor =
        Color.lerp(palette.primary, Colors.black, 0.30) ?? palette.primary;

    return Container(
      height: 38,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: deepThemeColor,
        boxShadow: [
          BoxShadow(
            color: palette.primary.withValues(alpha: 0.20),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Row(
          children: [
            const SizedBox(width: 12),
            const Icon(Icons.campaign_rounded, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: ClipRect(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    return _ScrollingText(
                      text: marqueeText,
                      controller: _controller,
                      viewportWidth: constraints.maxWidth,
                    );
                  },
                ),
              ),
            ),
            const SizedBox(width: 12),
          ],
        ),
      ),
    );
  }
}

class _ScrollingText extends StatelessWidget {
  final String text;
  final AnimationController controller;
  final double viewportWidth;

  const _ScrollingText({
    required this.text,
    required this.controller,
    required this.viewportWidth,
  });

  @override
  Widget build(BuildContext context) {
    const style = TextStyle(
      color: Colors.white,
      fontSize: 13,
      fontWeight: FontWeight.w800,
      letterSpacing: 0,
    );

    // Measure the text width to compute scroll distance.
    final tp = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
      maxLines: 1,
    )..layout();
    final textWidth = tp.width;
    // Gap between repeats so it reads continuously without abrupt jump.
    const gap = 80.0;
    final totalShift = textWidth + gap;

    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final dx = viewportWidth - controller.value * totalShift;
        return Stack(
          clipBehavior: Clip.none,
          children: [
            Positioned(
              left: dx,
              top: 0,
              bottom: 0,
              child: Center(child: Text(text, style: style, maxLines: 1)),
            ),
            Positioned(
              left: dx + totalShift,
              top: 0,
              bottom: 0,
              child: Center(child: Text(text, style: style, maxLines: 1)),
            ),
          ],
        );
      },
    );
  }
}
