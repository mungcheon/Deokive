import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/badge_item.dart';
import '../state/app_state.dart';
import 'badge_screen.dart';
import 'news_detail_screen.dart';
import 'news_list_screen.dart';

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
        final equippedBadges = appState.equippedBadges;

        final notices = <Map<String, String>>[
          {
            'title': '홈 쇼케이스 업데이트 안내',
            'date': '2026-03-11',
            'summary': '프로필 포토카드형 쇼케이스와 배지 진열장이 추가되었습니다.',
            'content':
                '홈 탭 상단에 Deokive 쇼케이스 프로필이 추가되었습니다.\n\n대표 배지는 배지 컬렉션에서 장착할 수 있고, 장착한 배지는 홈 쇼케이스 진열장에 바로 반영됩니다.',
          },
          {
            'title': '배지 컬렉션 개선',
            'date': '2026-03-10',
            'summary': '카테고리별 배지를 접고 펼칠 수 있도록 바뀌었습니다.',
            'content':
                '배지 컬렉션에서 굿즈 개수, 실구매가, 정리 활동 카테고리를 각각 펼치거나 접을 수 있습니다.\n\n대표 배지는 상단 슬롯에서 바로 해제할 수 있습니다.',
          },
        ];

        final goodsNews = <Map<String, String>>[
          {
            'title': '이번 주 신규 굿즈 발매 정리',
            'date': '2026-03-11',
            'summary': '아크릴 스탠드와 포토카드 홀더 발매 소식을 모았습니다.',
            'content':
                '이번 주에는 아크릴 스탠드, 포토카드 홀더, 한정 특전 굿즈 발매가 예정되어 있습니다.\n\n관심 굿즈는 캘린더에 발매 일정으로 등록해두면 더 편하게 관리할 수 있습니다.',
          },
          {
            'title': '한정판 재입고 체크',
            'date': '2026-03-09',
            'summary': '품절 상품 재입고와 수량 한정 판매 소식입니다.',
            'content':
                '인기 굿즈 재입고 소식과 함께 수량 한정 판매가 열리고 있습니다.\n\n원하는 상품은 폴더별로 정리해두고, 발매 일정과 함께 체크해두는 것을 추천합니다.',
          },
        ];

        final eventNews = <Map<String, String>>[
          {
            'title': '이번 달 행사 일정 모아보기',
            'date': '2026-03-11',
            'summary': '팝업, 전시, 팬 이벤트 일정을 한 번에 정리했습니다.',
            'content':
                '이번 달 예정된 팝업 스토어, 전시, 팬 이벤트 일정을 확인해보세요.\n\n가고 싶은 일정은 캘린더에 등록해두면 날짜별로 더 쉽게 확인할 수 있습니다.',
          },
          {
            'title': '행사 체크 포인트',
            'date': '2026-03-08',
            'summary': '행사 전에 확인하면 좋은 준비 사항입니다.',
            'content':
                '입장 시간, 현장 구매 제한, 특전 수령 조건 등 행사 전 확인이 필요한 항목을 정리했습니다.\n\n행사 일정과 개인 일정은 캘린더에서 색상으로 구분해서 볼 수 있습니다.',
          },
        ];

        final newsMenus = [
          {
            'title': '공지',
            'subtitle': '업데이트와 중요한 안내',
            'icon': Icons.campaign_outlined,
            'posts': notices,
          },
          {
            'title': '굿즈 소식',
            'subtitle': '신규 발매와 재입고 소식',
            'icon': Icons.newspaper_outlined,
            'posts': goodsNews,
          },
          {
            'title': '행사 이벤트',
            'subtitle': '팝업, 전시, 행사 일정 정보',
            'icon': Icons.event_note_outlined,
            'posts': eventNews,
          },
        ];

        final promoSlides = [
          {
            'title': '쇼케이스 프로필 오픈',
            'subtitle': '홈에서 대표 배지를 진열하고 프로필 포토카드처럼 확인해보세요.',
            'icon': Icons.auto_awesome_rounded,
            'post': notices.first,
          },
          {
            'title': '굿즈 발매 소식 한눈에',
            'subtitle': '신규 발매와 재입고 소식을 배너에서 바로 살펴볼 수 있어요.',
            'icon': Icons.redeem_outlined,
            'post': goodsNews.first,
          },
          {
            'title': '행사 일정 미리 체크',
            'subtitle': '팝업과 전시 일정을 모아보고 캘린더로 연결해보세요.',
            'icon': Icons.event_available_outlined,
            'post': eventNews.first,
          },
        ];

        return Scaffold(
          appBar: AppBar(
            title: const Text('Deokive'),
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _ShowcaseProfileCard(
                isLoggedIn: appState.isLoggedIn,
                darkModeEnabled: appState.darkModeEnabled,
                equippedBadges: equippedBadges,
                onOpenBadges: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const BadgeScreen(),
                    ),
                  );
                },
              ),
              const SizedBox(height: 24),
              const Text(
                '추천 배너',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
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
                              onPageChanged: (index) {
                                setState(() {
                                  _currentPage = index;
                                });
                              },
                              itemBuilder: (context, index) {
                                final slide = promoSlides[index];
                                return _PromoSlideCard(
                                  title: slide['title'] as String,
                                  subtitle: slide['subtitle'] as String,
                                  icon: slide['icon'] as IconData,
                                  onTap: () {
                                    final post = slide['post'] as Map<String, String>;
                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (_) => NewsDetailScreen(
                                          title: post['title'] ?? '',
                                          date: post['date'] ?? '',
                                          content: post['content'] ?? '',
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
                                ? Colors.deepPurple
                                : Colors.deepPurple.withOpacity(0.25),
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                '소식',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              ...newsMenus.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Card(
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(18),
                      side: BorderSide(color: Colors.grey.shade300),
                    ),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: Colors.deepPurple.shade50,
                        child: Icon(item['icon'] as IconData),
                      ),
                      title: Text(item['title'] as String),
                      subtitle: Text(item['subtitle'] as String),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => NewsListScreen(
                              title: item['title'] as String,
                              posts: item['posts'] as List<Map<String, String>>,
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
  final bool isLoggedIn;
  final bool darkModeEnabled;
  final List<BadgeItem> equippedBadges;
  final VoidCallback onOpenBadges;

  const _ShowcaseProfileCard({
    required this.isLoggedIn,
    required this.darkModeEnabled,
    required this.equippedBadges,
    required this.onOpenBadges,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(26),
        gradient: LinearGradient(
          colors: [
            colorScheme.primaryContainer,
            colorScheme.surface,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: [
          BoxShadow(
            color: colorScheme.primary.withOpacity(0.10),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              color: colorScheme.surface.withOpacity(0.88),
              border: Border.all(
                color: colorScheme.primary.withOpacity(0.12),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 88,
                  height: 118,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    gradient: LinearGradient(
                      colors: [
                        colorScheme.primary,
                        colorScheme.secondary,
                      ],
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircleAvatar(
                        radius: 24,
                        backgroundColor: Colors.white.withOpacity(0.18),
                        child: const Icon(
                          Icons.person,
                          color: Colors.white,
                          size: 24,
                        ),
                      ),
                      const SizedBox(height: 10),
                      const Text(
                        'DEOKIVE',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isLoggedIn ? 'Deokive User' : 'Guest Collector',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        isLoggedIn ? '@deokive' : '@guest',
                        style: TextStyle(
                          color: Colors.grey.shade600,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        isLoggedIn
                            ? '대표 배지와 취향을 전시하는 프로필 쇼케이스'
                            : '로그인 후 나만의 쇼케이스를 꾸며보세요',
                        style: TextStyle(
                          color: Colors.grey.shade700,
                          fontSize: 13.5,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _InfoChip(
                            icon: isLoggedIn
                                ? Icons.verified_user_outlined
                                : Icons.lock_outline,
                            label: isLoggedIn ? '로그인됨' : '게스트',
                          ),
                          _InfoChip(
                            icon: darkModeEnabled
                                ? Icons.dark_mode
                                : Icons.light_mode,
                            label: darkModeEnabled ? '다크 모드' : '라이트 모드',
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              color: colorScheme.surface.withOpacity(0.80),
              border: Border.all(
                color: colorScheme.primary.withOpacity(0.10),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.collections_bookmark_outlined,
                      color: colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '대표 배지 진열장',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ),
                    IconButton(
                      tooltip: '배지 관리',
                      onPressed: onOpenBadges,
                      icon: const Icon(Icons.workspace_premium_outlined),
                      visualDensity: VisualDensity.compact,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: List.generate(3, (index) {
                    if (index < equippedBadges.length) {
                      return _BadgeShowcaseChip(badge: equippedBadges[index]);
                    }
                    return const _EmptyBadgeSlot();
                  }),
                ),
                const SizedBox(height: 12),
                Text(
                  equippedBadges.isEmpty
                      ? '아직 장착한 대표 배지가 없습니다. 우측 상단 아이콘에서 배지를 장착해보세요.',
                  style: TextStyle(
                    color: Colors.grey.shade700,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _InfoChip({
    required this.icon,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _BadgeShowcaseChip extends StatelessWidget {
  final BadgeItem badge;

  const _BadgeShowcaseChip({required this.badge});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: badge.color.withOpacity(0.12),
        border: Border.all(color: badge.color.withOpacity(0.24)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(badge.icon, size: 18, color: badge.color),
          const SizedBox(width: 8),
          Text(
            badge.title,
            style: TextStyle(
              fontWeight: FontWeight.w700,
              color: badge.color,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyBadgeSlot extends StatelessWidget {
  const _EmptyBadgeSlot();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.grey.shade100,
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Text(
        '빈 슬롯',
        style: TextStyle(
          fontWeight: FontWeight.w700,
          color: Colors.grey.shade600,
        ),
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
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Ink(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          color: onTap == null
              ? Colors.grey.shade200
              : Colors.deepPurple.withOpacity(0.08),
          shape: BoxShape.circle,
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Icon(
          icon,
          size: 20,
          color: onTap == null ? Colors.grey : Colors.deepPurple,
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
    return InkWell(
      borderRadius: BorderRadius.circular(24),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: LinearGradient(
            colors: [
              Colors.white,
              Colors.deepPurple.shade50,
            ],
          ),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: Colors.deepPurple.shade100,
              child: Icon(icon, color: Colors.deepPurple),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 13.5,
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
