import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../l10n/app_strings.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import 'board_screen.dart';
import 'calendar_screen.dart';
import 'folders_screen.dart';
import 'home_screen.dart';
import 'settings_screen.dart';

class RootScreen extends StatefulWidget {
  const RootScreen({super.key});

  @override
  State<RootScreen> createState() => _RootScreenState();
}

class _RootScreenState extends State<RootScreen> {
  final List<int> _tabHistory = [];
  bool _showingBoardAlert = false;
  bool _showUpdateNotice = true;
  Timer? _updateNoticeTimer;

  @override
  void initState() {
    super.initState();
    _updateNoticeTimer = Timer(const Duration(seconds: 70), () {
      if (mounted) {
        setState(() => _showUpdateNotice = false);
      }
    });
  }

  @override
  void dispose() {
    _updateNoticeTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _showPendingBoardAlerts();
    });
  }

  Future<void> _showPendingBoardAlerts() async {
    if (_showingBoardAlert || !mounted) return;
    final appState = context.read<AppState>();
    final alerts = appState.takePendingBoardCommentAlerts();
    if (alerts.isEmpty) return;
    _showingBoardAlert = true;
    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            title: const Text('새 댓글 알림'),
            content: SizedBox(
              width: 360,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: alerts
                      .map(
                        (alert) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Text(alert),
                        ),
                      )
                      .toList(),
                ),
              ),
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('확인'),
              ),
            ],
          );
        },
      );
    } finally {
      _showingBoardAlert = false;
    }
  }

  Future<void> _onDestinationSelected(AppState appState, int index) async {
    final previousIndex = appState.currentTabIndex;
    if (previousIndex == index) return;

    _tabHistory.remove(index);
    _tabHistory.add(previousIndex);
    appState.setTab(index);
  }

  Future<bool> _handleSystemBack(AppState appState) async {
    if (_tabHistory.isNotEmpty) {
      final previousTab = _tabHistory.removeLast();
      appState.setTab(previousTab);
      return false;
    }

    if (appState.currentTabIndex != 0) {
      appState.setTab(0);
      return false;
    }

    return true;
  }

  bool _canPopRoot(AppState appState) {
    return _tabHistory.isEmpty && appState.currentTabIndex == 0;
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final pages = [
          const HomeScreen(),
          const BoardScreen(),
          const FoldersScreen(),
          const CalendarScreen(),
          const SettingsScreen(),
        ];
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;
        final strings = AppStrings.of(appState.appLanguage);
        final items = [
          _BottomTabItem(
            icon: Icons.home_outlined,
            selectedIcon: Icons.home,
            label: strings.home,
          ),
          _BottomTabItem(
            icon: Icons.forum_outlined,
            selectedIcon: Icons.forum,
            label: strings.board,
          ),
          _BottomTabItem(
            icon: Icons.folder_outlined,
            selectedIcon: Icons.folder,
            label: strings.folders,
          ),
          _BottomTabItem(
            icon: Icons.calendar_month_outlined,
            selectedIcon: Icons.calendar_month,
            label: strings.calendar,
          ),
          _BottomTabItem(
            icon: Icons.settings_outlined,
            selectedIcon: Icons.settings,
            label: strings.settings,
          ),
        ];

        return PopScope(
          canPop: _canPopRoot(appState),
          onPopInvokedWithResult: (didPop, _) {
            if (!didPop) {
              _handleSystemBack(appState);
            }
          },
          child: Scaffold(
            body: Column(
              children: [
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  child: _showUpdateNotice
                      ? _UpdateNoticeBanner(
                          onClose: () =>
                              setState(() => _showUpdateNotice = false),
                        )
                      : const SizedBox.shrink(),
                ),
                Expanded(
                  child: IndexedStack(
                    index: appState.currentTabIndex,
                    children: pages,
                  ),
                ),
              ],
            ),
            bottomNavigationBar: SafeArea(
              top: false,
              child: Container(
                padding: const EdgeInsets.fromLTRB(12, 10, 12, 14),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface,
                  border: Border(
                    top: BorderSide(
                      color: theme.colorScheme.outline.withValues(alpha: 0.9),
                    ),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.04),
                      blurRadius: 10,
                      offset: const Offset(0, -2),
                    ),
                  ],
                ),
                child: Row(
                  children: List.generate(items.length, (index) {
                    final item = items[index];
                    final selected = index == appState.currentTabIndex;

                    return Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(18),
                          onTap: () => _onDestinationSelected(appState, index),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 180),
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: selected
                                  ? palette.primary.withValues(alpha: 0.16)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(
                                color: selected
                                    ? palette.primary.withValues(alpha: 0.28)
                                    : Colors.transparent,
                              ),
                            ),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  selected ? item.selectedIcon : item.icon,
                                  color: selected
                                      ? palette.primary
                                      : theme.colorScheme.onSurface.withValues(
                                          alpha: 0.72,
                                        ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  item.label,
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: selected
                                        ? palette.primary
                                        : theme.colorScheme.onSurface
                                            .withValues(
                                            alpha: 0.72,
                                          ),
                                    fontWeight: selected
                                        ? FontWeight.w800
                                        : FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  }),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _UpdateNoticeBanner extends StatelessWidget {
  final VoidCallback onClose;

  const _UpdateNoticeBanner({required this.onClose});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    final textColor = theme.colorScheme.onSurface;

    return SafeArea(
      bottom: false,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
        decoration: BoxDecoration(
          color: Color.lerp(theme.colorScheme.surface, palette.accent, 0.14),
          border: Border(
            bottom: BorderSide(
              color: palette.primary.withValues(alpha: 0.18),
            ),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.system_update_alt_rounded,
              size: 18,
              color: palette.primary,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  '1분 뒤 업데이트를 시작합니다. 작업 중이라면 종료해 주세요.',
                  maxLines: 1,
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: textColor,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              visualDensity: VisualDensity.compact,
              iconSize: 18,
              tooltip: '닫기',
              onPressed: onClose,
              icon: Icon(
                Icons.close_rounded,
                color: textColor.withValues(alpha: 0.72),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BottomTabItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;

  const _BottomTabItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });
}
