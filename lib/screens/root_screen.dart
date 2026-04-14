import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config/monetization_catalog.dart';
import '../l10n/app_strings.dart';
import '../services/ad_service.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
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
  Timer? _startupAdPreloadTimer;
  bool _restorePromptVisible = false;

  @override
  void initState() {
    super.initState();
    _startupAdPreloadTimer = Timer(
      const Duration(seconds: 2),
      () => AdService.instance.preloadInterstitial(
        AdPlacement.folderInterstitial,
      ),
    );
  }

  @override
  void dispose() {
    _startupAdPreloadTimer?.cancel();
    super.dispose();
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

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        if (appState.hasPendingRestorePrompt && !_restorePromptVisible) {
          _restorePromptVisible = true;
          WidgetsBinding.instance.addPostFrameCallback((_) async {
            final restore = await showDialog<bool>(
              context: context,
              barrierDismissible: false,
              builder: (dialogContext) {
                return AlertDialog(
                  title: const Text('백업 복원'),
                  content: const Text(
                    '이 계정으로 저장된 백업 데이터를 찾았습니다. 이 기기로 가져올까요?',
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(dialogContext, false),
                      child: const Text('나중에'),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.pop(dialogContext, true),
                      child: const Text('가져오기'),
                    ),
                  ],
                );
              },
            );

            if (!mounted) return;
            if (restore == true) {
              final success = await appState.restorePendingServerBackup();
              if (!mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    success ? '백업 데이터를 이 기기로 가져왔습니다.' : '백업 복원에 실패했습니다.',
                  ),
                ),
              );
            } else {
              await appState.dismissPendingServerBackup();
            }
            _restorePromptVisible = false;
          });
        }

        final pages = [
          const HomeScreen(),
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
          canPop: false,
          onPopInvokedWithResult: (didPop, _) async {
            if (didPop) return;
            final shouldPop = await _handleSystemBack(appState);
            if (shouldPop && context.mounted) {
              Navigator.of(context).maybePop();
            }
          },
          child: Stack(
            children: [
              Scaffold(
                body: pages[appState.currentTabIndex],
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
              if (appState.isBusy)
                Positioned.fill(
                  child: ColoredBox(
                    color: Colors.black.withValues(alpha: 0.32),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 320),
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const SizedBox(
                                  width: 30,
                                  height: 30,
                                  child: CircularProgressIndicator(),
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  appState.syncStatusMessage ?? '동기화 중입니다.',
                                  textAlign: TextAlign.center,
                                ),
                              ],
                            ),
                          ),
                        ),
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
