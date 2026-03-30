import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/badge_definitions.dart';
import '../models/badge_item.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';

class BadgeScreen extends StatefulWidget {
  const BadgeScreen({super.key});

  @override
  State<BadgeScreen> createState() => _BadgeScreenState();
}

class _BadgeScreenState extends State<BadgeScreen> {
  bool collectionExpanded = true;
  bool spendingExpanded = false;
  bool organizingExpanded = false;

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final progress = appState.badgeProgress;
        final theme = Theme.of(context);

        return Scaffold(
          appBar: AppBar(title: const Text('배지 컬렉션')),
          body: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1100),
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '장착 배지',
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 10,
                            runSpacing: 10,
                            children: List.generate(appState.maxBadgeSlots, (index) {
                              if (index < appState.equippedBadges.length) {
                                final badge = appState.equippedBadges[index];
                                return _EquippedBadgeChip(
                                  title: badge.title,
                                  icon: badge.icon,
                                  color: badge.color,
                                  onRemove: () => appState.toggleEquipBadge(badge.id),
                                );
                              }
                              return const _EmptyBadgeSlot();
                            }),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            '장착 ${appState.equippedBadges.length}/${appState.maxBadgeSlots}',
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  _BadgeAccordionSection(
                    title: '수집 개수 배지',
                    icon: Icons.inventory_2_outlined,
                    progressText:
                        '${progress.unlockedCountFor(collectionCountBadges)}/${collectionCountBadges.length} 획득',
                    expanded: collectionExpanded,
                    onToggle: () {
                      setState(() {
                        collectionExpanded = !collectionExpanded;
                      });
                    },
                    child: _BadgeGrid(badges: collectionCountBadges),
                  ),
                  const SizedBox(height: 12),
                  _BadgeAccordionSection(
                    title: '누적 금액 배지',
                    icon: Icons.payments_outlined,
                    progressText:
                        '${progress.unlockedCountFor(spendingBadges)}/${spendingBadges.length} 획득',
                    expanded: spendingExpanded,
                    onToggle: () {
                      setState(() {
                        spendingExpanded = !spendingExpanded;
                      });
                    },
                    child: _BadgeGrid(badges: spendingBadges),
                  ),
                  const SizedBox(height: 12),
                  _BadgeAccordionSection(
                    title: '정리 활동 배지',
                    icon: Icons.edit_note_rounded,
                    progressText:
                        '${progress.unlockedCountFor(organizingBadges)}/${organizingBadges.length} 획득',
                    expanded: organizingExpanded,
                    onToggle: () {
                      setState(() {
                        organizingExpanded = !organizingExpanded;
                      });
                    },
                    child: _BadgeGrid(badges: organizingBadges),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _BadgeAccordionSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final String progressText;
  final bool expanded;
  final VoidCallback onToggle;
  final Widget child;

  const _BadgeAccordionSection({
    required this.title,
    required this.icon,
    required this.progressText,
    required this.expanded,
    required this.onToggle,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: onToggle,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(icon, color: theme.colorScheme.onSurface),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(progressText),
                      ],
                    ),
                  ),
                  Icon(
                    expanded ? Icons.expand_less : Icons.expand_more,
                    color: theme.colorScheme.onSurface,
                  ),
                ],
              ),
            ),
          ),
          if (expanded) ...[
            Divider(height: 1, color: theme.colorScheme.outline),
            Padding(
              padding: const EdgeInsets.all(16),
              child: child,
            ),
          ],
        ],
      ),
    );
  }
}

class _BadgeGrid extends StatelessWidget {
  final List<BadgeItem> badges;

  const _BadgeGrid({required this.badges});

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: badges.length,
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 240,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.9,
      ),
      itemBuilder: (context, index) {
        final badge = badges[index];
        final unlocked = appState.isBadgeUnlocked(badge.id);
        final equipped = appState.isBadgeEquipped(badge.id);

        return _BadgeCard(
          title: badge.title,
          description: badge.description,
          level: badge.level,
          icon: badge.icon,
          color: badge.color,
          unlocked: unlocked,
          equipped: equipped,
          onTap: unlocked
              ? () {
                  if (!equipped && !appState.canEquipMoreBadges()) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          '장착 배지는 최대 ${appState.maxBadgeSlots}개까지 사용할 수 있습니다.',
                        ),
                      ),
                    );
                    return;
                  }
                  appState.toggleEquipBadge(badge.id);
                }
              : null,
        );
      },
    );
  }
}

class _BadgeCard extends StatelessWidget {
  final String title;
  final String description;
  final int level;
  final IconData icon;
  final Color color;
  final bool unlocked;
  final bool equipped;
  final VoidCallback? onTap;

  const _BadgeCard({
    required this.title,
    required this.description,
    required this.level,
    required this.icon,
    required this.color,
    required this.unlocked,
    required this.equipped,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    final displayColor = unlocked ? color : Colors.grey;

    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: onTap,
      child: Ink(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          color: unlocked ? theme.colorScheme.surface : palette.softSurface,
          border: Border.all(
            color: equipped
                ? color
                : unlocked
                    ? color.withValues(alpha: 0.25)
                    : theme.colorScheme.outline,
            width: equipped ? 2 : 1,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor: displayColor.withValues(alpha: 0.15),
                    child: Icon(icon, color: displayColor),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: equipped
                          ? color.withValues(alpha: 0.14)
                          : palette.softSurface,
                    ),
                    child: Text(
                      'Lv.$level',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        color: equipped ? color : theme.colorScheme.onSurface,
                      ),
                    ),
                  ),
                ],
              ),
              const Spacer(),
              Text(
                title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: unlocked ? theme.colorScheme.onSurface : Colors.grey,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                description,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  height: 1.35,
                  color: unlocked ? theme.colorScheme.onSurface : Colors.grey,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                equipped ? '장착 중' : unlocked ? '탭해서 장착' : '아직 잠겨 있어요',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: equipped
                      ? color
                      : unlocked
                          ? palette.primary
                          : Colors.grey,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EquippedBadgeChip extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color color;
  final VoidCallback onRemove;

  const _EquippedBadgeChip({
    required this.title,
    required this.icon,
    required this.color,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Text(
            title,
            style: TextStyle(
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          const SizedBox(width: 6),
          IconButton(
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints.tightFor(width: 24, height: 24),
            onPressed: onRemove,
            style: IconButton.styleFrom(
              backgroundColor: color.withValues(alpha: 0.18),
              shape: const CircleBorder(),
            ),
            icon: Icon(Icons.close, size: 14, color: color),
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
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: palette.softSurface,
        border: Border.all(color: theme.colorScheme.outline),
      ),
      child: Text(
        '빈 슬롯',
        style: theme.textTheme.bodyMedium?.copyWith(
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
