import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config/monetization_catalog.dart';
import '../models/badge_item.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_avatar.dart';
import '../widgets/deokive_header_title.dart';
import '../widgets/live_banner_ad.dart';
import '../widgets/premium_gate_card.dart';
import 'avatar_editor_screen.dart';
import 'badge_screen.dart';
import 'news_detail_screen.dart';
import 'news_list_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final PageController _pageController = PageController(viewportFraction: 0.92);
  int _currentPage = 0;
  String? _checkedPopupDate;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _openNews(BuildContext context, _HomePost post) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => NewsDetailScreen(
          title: post.title,
          date: post.date,
          content: post.content,
        ),
      ),
    );
  }

  void _showHomePromoPopupIfNeeded(AppState appState) {
    if (_checkedPopupDate == appState.todayStamp ||
        !appState.shouldShowHomePromoPopup) {
      return;
    }
    _checkedPopupDate = appState.todayStamp;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      showDialog(
        context: context,
        builder: (dialogContext) {
          final theme = Theme.of(dialogContext);
          final palette = theme.extension<DeokivePalette>()!;
          return AlertDialog(
            contentPadding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
            content: SizedBox(
              width: 360,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      gradient: LinearGradient(
                        colors: [
                          palette.primary.withValues(alpha: 0.18),
                          palette.accent.withValues(alpha: 0.18),
                        ],
                      ),
                    ),
                    child: const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '오늘의 추천',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        SizedBox(height: 8),
                        Text(
                          '배지 컬렉션과 홈 기능을 더 넓게 쓰고 싶다면 프리미엄 기능을 확인해보세요.',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    '이 팝업은 홈 진입 시 노출되며, 하루 동안 보지 않기를 선택할 수 있습니다.',
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () async {
                  await appState.dismissHomePromoPopupForToday();
                  if (!dialogContext.mounted) return;
                  Navigator.pop(dialogContext);
                },
                child: const Text('하루 동안 보지 않기'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('닫기'),
              ),
            ],
          );
        },
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        _showHomePromoPopupIfNeeded(appState);

        final notices = [
          const _HomePost(
            title: '홈 쇼케이스가 새롭게 정리되었어요',
            date: '2026-03-11',
            summary: '프로필 포토카드와 배지 전시대를 홈에서 바로 확인할 수 있어요.',
            content:
                '홈 상단에 Deokive 포토카드형 프로필을 배치했습니다.\n\n대표 정보와 배지 전시대, 빠른 이동 흐름을 한 카드 안에 담았습니다.',
          ),
          const _HomePost(
            title: '배지 컬렉션 구성이 개선되었어요',
            date: '2026-03-10',
            summary: '카테고리별 확인과 장착 관리가 더 자연스러워졌어요.',
            content: '배지 컬렉션 화면에서 카테고리별로 확인하고, 홈 쇼케이스 배지 전시대와 바로 연결됩니다.',
          ),
        ];

        final goodsNews = [
          const _HomePost(
            title: '이번 주 굿즈 발매 소식',
            date: '2026-03-11',
            summary: '포토카드 세트와 행사 한정 MD 발매 일정을 모아봤어요.',
            content:
                '이번 주 발매 예정 굿즈를 정리했습니다.\n\n캘린더 탭에서도 같은 날짜 기준으로 확인할 수 있습니다.',
          ),
          const _HomePost(
            title: '구매 전 체크 포인트',
            date: '2026-03-09',
            summary: '구성과 판매처 조건을 미리 확인하면 중복 구매를 줄일 수 있어요.',
            content: '시리즈 정보와 판매처 메모를 함께 적어두면 원하는 굿즈를 다시 찾기 쉬워집니다.',
          ),
        ];

        final eventNews = [
          const _HomePost(
            title: '이번 달 행사 일정 모음',
            date: '2026-03-11',
            summary: '팝업, 전시, 이벤트 일정을 달력 기준으로 확인해보세요.',
            content: '행사 일정과 개인 일정을 같은 달력 안에서 함께 볼 수 있도록 구성했습니다.',
          ),
          const _HomePost(
            title: '행사 준비 체크리스트',
            date: '2026-03-08',
            summary: '입장 시간, 현장 수령, 특전 여부를 미리 정리해두세요.',
            content: '행사 준비용 메모와 시간을 함께 기록하면 이동 동선 정리가 쉬워집니다.',
          ),
        ];

        final menus = [
          _HomeMenu(
            title: '공지',
            subtitle: '업데이트와 주요 안내',
            icon: Icons.campaign_outlined,
            posts: notices,
          ),
          _HomeMenu(
            title: '굿즈 소식',
            subtitle: '발매와 예약 정보',
            icon: Icons.newspaper_outlined,
            posts: goodsNews,
          ),
          _HomeMenu(
            title: '행사 이벤트',
            subtitle: '팝업, 전시, 이벤트 일정',
            icon: Icons.event_note_outlined,
            posts: eventNews,
          ),
        ];

        final slides = [
          _PromoSlide(
            title: '쇼케이스 프로필 둘러보기',
            subtitle: '프로필 카드와 배지 전시대를 홈에서 바로 확인해보세요.',
            icon: Icons.auto_awesome_rounded,
            post: notices.first,
          ),
          _PromoSlide(
            title: '굿즈 발매 소식 보기',
            subtitle: '이번 주 굿즈 소식을 빠르게 확인하고 일정까지 함께 정리해보세요.',
            icon: Icons.redeem_outlined,
            post: goodsNews.first,
          ),
          _PromoSlide(
            title: '행사 일정 미리 체크',
            subtitle: '행사와 개인 일정을 같은 흐름으로 관리할 수 있어요.',
            icon: Icons.event_available_outlined,
            post: eventNews.first,
          ),
        ];

        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;

        return Scaffold(
          appBar: AppBar(title: const DeokiveHeaderTitle()),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (appState.shouldShowAd(AdPlacement.homeBanner)) ...[
                const Center(
                  child: LiveBannerAd(placement: AdPlacement.homeBanner),
                ),
                const SizedBox(height: 16),
              ],
              _ShowcaseProfileCard(
                isLoggedIn: appState.isLoggedIn,
                displayName: appState.displayName,
                tag: appState.tag,
                level: appState.totalUnlockedBadgeLevel,
                folderCount: appState.folders.length,
                goodsCount: appState.totalGoodsCount,
                badgeCount: appState.totalUnlockedBadgeCount,
                equippedBadges: appState.equippedBadges,
                avatarBodyType: appState.avatarBodyType,
                avatarBackgroundType: appState.avatarBackgroundType,
                avatarFaceType: appState.avatarFaceType,
                avatarHairStyle: appState.avatarHairStyle,
                avatarHairColorIndex: appState.avatarHairColorIndex,
                avatarAccentColorIndex: appState.avatarAccentColorIndex,
                avatarOutfitColorIndex: appState.avatarOutfitColorIndex,
                avatarSkinToneIndex: appState.avatarSkinToneIndex,
                avatarHasHat: appState.avatarHasHat,
                avatarHasCape: appState.avatarHasCape,
                avatarHasHandheld: appState.avatarHasHandheld,
                avatarHasBackRibbon: appState.avatarHasBackRibbon,
                onEditAvatar: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const AvatarEditorScreen(),
                    ),
                  );
                },
                onOpenBadges: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const BadgeScreen()),
                  );
                },
              ),
              const SizedBox(height: 24),
              Text(
                '추천 배너',
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 214,
                child: Column(
                  children: [
                    Expanded(
                      child: Stack(
                        children: [
                          Positioned.fill(
                            child: PageView.builder(
                              controller: _pageController,
                              itemCount: slides.length,
                              onPageChanged: (index) {
                                setState(() {
                                  _currentPage = index;
                                });
                              },
                              itemBuilder: (context, index) {
                                final slide = slides[index];
                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 20),
                                  child: _PromoSlideCard(
                                    title: slide.title,
                                    subtitle: slide.subtitle,
                                    icon: slide.icon,
                                    onTap: () => _openNews(context, slide.post),
                                  ),
                                );
                              },
                            ),
                          ),
                          Positioned(
                            left: 6,
                            top: 0,
                            bottom: 0,
                            child: Center(
                              child: _BannerArrowButton(
                                icon: Icons.chevron_left,
                                onTap: _currentPage == 0
                                    ? null
                                    : () {
                                        _pageController.previousPage(
                                          duration:
                                              const Duration(milliseconds: 260),
                                          curve: Curves.easeOut,
                                        );
                                      },
                              ),
                            ),
                          ),
                          Positioned(
                            right: 6,
                            top: 0,
                            bottom: 0,
                            child: Center(
                              child: _BannerArrowButton(
                                icon: Icons.chevron_right,
                                onTap: _currentPage == slides.length - 1
                                    ? null
                                    : () {
                                        _pageController.nextPage(
                                          duration:
                                              const Duration(milliseconds: 260),
                                          curve: Curves.easeOut,
                                        );
                                      },
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(
                        slides.length,
                        (index) => AnimatedContainer(
                          duration: const Duration(milliseconds: 180),
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          width: _currentPage == index ? 20 : 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: _currentPage == index
                                ? palette.primary
                                : theme.colorScheme.outline,
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              if (appState.shouldShowAd(AdPlacement.homeBanner))
                const Center(
                  child: LiveBannerAd(placement: AdPlacement.homeBanner),
                ),
              if (appState.isLoggedIn &&
                  !appState.isFeatureUnlocked(PremiumFeature.adFree)) ...[
                const SizedBox(height: 12),
                PremiumGateCard(
                  feature: PremiumFeature.adFree,
                  unlocked: false,
                  trailingLabel: '설정에서 관리',
                  onTap: () => context.read<AppState>().setTab(3),
                ),
              ],
              const SizedBox(height: 24),
              Text(
                '소식',
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 12),
              ...menus.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Card(
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: palette.softSurface,
                        child: Icon(
                          item.icon,
                          color: theme.colorScheme.onSurface,
                        ),
                      ),
                      title: Text(item.title),
                      subtitle: Text(item.subtitle),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => NewsListScreen(
                              title: item.title,
                              posts: item.posts
                                  .map(
                                    (post) => {
                                      'title': post.title,
                                      'date': post.date,
                                      'summary': post.summary,
                                      'content': post.content,
                                    },
                                  )
                                  .toList(),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ShowcaseProfileCard extends StatelessWidget {
  static const double _frameStrokeWidth = 1.4;
  static const double _frameStrokeAlpha = 0.42;

  final bool isLoggedIn;
  final String displayName;
  final String tag;
  final int level;
  final int folderCount;
  final int goodsCount;
  final int badgeCount;
  final List<BadgeItem> equippedBadges;
  final int avatarBodyType;
  final int avatarBackgroundType;
  final int avatarFaceType;
  final int avatarHairStyle;
  final int avatarHairColorIndex;
  final int avatarAccentColorIndex;
  final int avatarOutfitColorIndex;
  final int avatarSkinToneIndex;
  final bool avatarHasHat;
  final bool avatarHasCape;
  final bool avatarHasHandheld;
  final bool avatarHasBackRibbon;
  final VoidCallback onEditAvatar;
  final VoidCallback onOpenBadges;

  const _ShowcaseProfileCard({
    required this.isLoggedIn,
    required this.displayName,
    required this.tag,
    required this.level,
    required this.folderCount,
    required this.goodsCount,
    required this.badgeCount,
    required this.equippedBadges,
    required this.avatarBodyType,
    required this.avatarBackgroundType,
    required this.avatarFaceType,
    required this.avatarHairStyle,
    required this.avatarHairColorIndex,
    required this.avatarAccentColorIndex,
    required this.avatarOutfitColorIndex,
    required this.avatarSkinToneIndex,
    required this.avatarHasHat,
    required this.avatarHasCape,
    required this.avatarHasHandheld,
    required this.avatarHasBackRibbon,
    required this.onEditAvatar,
    required this.onOpenBadges,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    final surfaceColor = theme.colorScheme.surface;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            surfaceColor,
            palette.softSurface.withValues(alpha: 0.95),
          ],
        ),
        border: Border.all(
          color: palette.primary.withValues(alpha: _frameStrokeAlpha),
          width: _frameStrokeWidth,
        ),
        boxShadow: [
          BoxShadow(
            color: palette.primary.withValues(alpha: 0.12),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          color: surfaceColor,
          border: Border.all(
            color: palette.primary.withValues(alpha: _frameStrokeAlpha),
            width: _frameStrokeWidth,
          ),
        ),
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                InkWell(
                  borderRadius: BorderRadius.circular(22),
                  onTap: isLoggedIn ? onEditAvatar : null,
                  child: Container(
                    width: 148,
                    height: 148,
                    clipBehavior: Clip.antiAlias,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(22),
                      border: Border.all(
                        color: palette.primary.withValues(
                          alpha: _frameStrokeAlpha,
                        ),
                        width: _frameStrokeWidth,
                      ),
                    ),
                    child: DeokiveAvatar(
                      palette: palette,
                      padding: const EdgeInsets.fromLTRB(6, 38, 6, 0),
                      bodyType: avatarBodyType,
                      backgroundType: avatarBackgroundType,
                      faceType: -1,
                      hairStyle: avatarHairStyle,
                      hairColorIndex: avatarHairColorIndex,
                      accentColorIndex: avatarAccentColorIndex,
                      outfitColorIndex: avatarOutfitColorIndex,
                      skinToneIndex: avatarSkinToneIndex,
                      hasHat: avatarHasHat,
                      hasCape: avatarHasCape,
                      hasHandheld: avatarHasHandheld,
                      hasBackRibbon: avatarHasBackRibbon,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: SizedBox(
                    height: 148,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: surfaceColor,
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(
                              color: palette.primary.withValues(alpha: 0.22),
                            ),
                          ),
                          child: Text(
                            'Lv.$level',
                            style: theme.textTheme.labelMedium?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        const Spacer(),
                        Text(
                          displayName,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.4,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          tag,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: theme.colorScheme.onSurface.withValues(
                              alpha: 0.72,
                            ),
                          ),
                        ),
                        const Spacer(),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _ProfileSummaryCard(
                    label: '폴더',
                    value: '$folderCount',
                    icon: Icons.folder_copy_outlined,
                    onTap: null,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _ProfileSummaryCard(
                    label: '굿즈',
                    value: '$goodsCount',
                    icon: Icons.inventory_2_outlined,
                    onTap: null,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _ProfileSummaryCard(
                    label: '배지',
                    value: '$badgeCount',
                    icon: Icons.workspace_premium_outlined,
                    onTap: isLoggedIn ? onOpenBadges : null,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            InkWell(
              borderRadius: BorderRadius.circular(18),
              onTap: isLoggedIn ? onOpenBadges : null,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  color: palette.primary.withValues(alpha: 0.08),
                  border: Border.all(
                    color: palette.primary.withValues(alpha: 0.18),
                    width: _frameStrokeWidth,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.workspace_premium_outlined,
                          size: 18,
                          color: palette.primary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '배지 전시대',
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const Spacer(),
                        Icon(
                          Icons.chevron_right_rounded,
                          color: theme.colorScheme.onSurface.withValues(
                            alpha: 0.56,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (equippedBadges.isEmpty)
                      Text(
                        isLoggedIn ? '아직 장착한 배지가 없습니다.' : '로그인 후 배지 전시대를 사용할 수 있습니다.',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurface.withValues(
                            alpha: 0.68,
                          ),
                        ),
                      )
                    else
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: equippedBadges
                            .map((badge) => _BadgeShowcaseChip(badge: badge))
                            .toList(),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileSummaryCard extends StatelessWidget {
  static const double _frameStrokeWidth = 1.4;

  final String label;
  final String value;
  final IconData icon;
  final VoidCallback? onTap;

  const _ProfileSummaryCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    final child = Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: theme.colorScheme.surface,
        border: Border.all(
          color: palette.primary.withValues(alpha: 0.18),
          width: _frameStrokeWidth,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            icon,
            size: 16,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.56),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
              ),
              Text(
                value,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ],
      ),
    );

    if (onTap == null) {
      return child;
    }

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: child,
    );
  }
}

class _BadgeShowcaseChip extends StatelessWidget {
  static const double _frameStrokeWidth = 1.4;
  static const double _frameStrokeAlpha = 0.42;

  final BadgeItem badge;

  const _BadgeShowcaseChip({required this.badge});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: badge.color.withValues(alpha: 0.12),
        border: Border.all(
          color: badge.color.withValues(alpha: _frameStrokeAlpha),
          width: _frameStrokeWidth,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(badge.icon, size: 18, color: badge.color),
          const SizedBox(width: 8),
          Text(
            badge.title,
            style: TextStyle(
              color: badge.color,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _BannerArrowButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;

  const _BannerArrowButton({
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Ink(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color:
              onTap == null ? palette.softSurface : theme.colorScheme.surface,
          shape: BoxShape.circle,
          border: Border.all(color: theme.colorScheme.outline),
        ),
        child: Icon(
          icon,
          size: 20,
          color: onTap == null
              ? theme.colorScheme.onSurface.withValues(alpha: 0.35)
              : theme.colorScheme.onSurface,
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
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return InkWell(
      borderRadius: BorderRadius.circular(24),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              theme.colorScheme.surface,
              palette.softSurface,
            ],
          ),
          border: Border.all(color: theme.colorScheme.outline),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: palette.primary,
              child: Icon(icon, color: palette.text),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    subtitle,
                    style: theme.textTheme.bodyMedium?.copyWith(height: 1.35),
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

class _HomePost {
  final String title;
  final String date;
  final String summary;
  final String content;

  const _HomePost({
    required this.title,
    required this.date,
    required this.summary,
    required this.content,
  });
}

class _HomeMenu {
  final String title;
  final String subtitle;
  final IconData icon;
  final List<_HomePost> posts;

  const _HomeMenu({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.posts,
  });
}

class _PromoSlide {
  final String title;
  final String subtitle;
  final IconData icon;
  final _HomePost post;

  const _PromoSlide({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.post,
  });
}
