
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_avatar.dart';

class AvatarEditorScreen extends StatefulWidget {
  const AvatarEditorScreen({super.key});

  @override
  State<AvatarEditorScreen> createState() => _AvatarEditorScreenState();
}

class _AvatarEditorScreenState extends State<AvatarEditorScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  static const _tabTitles = [
    '배경',
    '몸',
    '머리',
    '의상',
    '소품',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabTitles.length, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;
        final outfitColors = deokiveAvatarOutfitColors(palette);
        final screenHeight = MediaQuery.sizeOf(context).height;
        final previewSize = screenHeight < 760 ? 168.0 : 220.0;

        return Scaffold(
          appBar: AppBar(
            title: const Text('아바타 꾸미기'),
          ),
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
                      child: Column(
                        children: [
                          SizedBox(
                            height: previewSize,
                            child: AspectRatio(
                              aspectRatio: 1,
                              child: Container(
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(22),
                                    border: Border.all(
                                      color:
                                          palette.primary.withValues(alpha: 0.30),
                                    ),
                                  ),
                                  child: DeokiveAvatar(
                                    palette: palette,
                                    bodyType: appState.avatarBodyType,
                                    backgroundType: appState.avatarBackgroundType,
                                    hairStyle: appState.avatarHairStyle,
                                    hairColorIndex:
                                        appState.avatarHairColorIndex,
                                    accentColorIndex:
                                        appState.avatarAccentColorIndex,
                                    outfitColorIndex:
                                        appState.avatarOutfitColorIndex,
                                    skinToneIndex:
                                        appState.avatarSkinToneIndex,
                                    hasHat: appState.avatarHasHat,
                                    hasCape: appState.avatarHasCape,
                                    hasHandheld: appState.avatarHasHandheld,
                                    hasBackRibbon: appState.avatarHasBackRibbon,
                                  ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            '아래 탭에서 실제 에셋을 골라서 적용해 주세요.',
                            textAlign: TextAlign.center,
                            style: theme.textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Material(
                    color: Colors.transparent,
                    child: TabBar(
                      controller: _tabController,
                      isScrollable: true,
                      tabAlignment: TabAlignment.start,
                      tabs: _tabTitles.map((title) => Tab(text: title)).toList(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: TabBarView(
                      controller: _tabController,
                      children: [
                        _EditorPane(
                          title: '배경 선택',
                          description: '배경 이미지를 고르거나 미설정으로 둘 수 있어요.',
                          child: _AssetOptionGrid(
                            labels: deokiveAvatarBackgroundLabels,
                            assets: deokiveAvatarBackgroundAssets,
                            selectedIndex: appState.avatarBackgroundType,
                            fit: BoxFit.cover,
                            onTap: (index) => appState.updateAvatar(
                              backgroundType: index,
                            ),
                          ),
                        ),
                        _EditorPane(
                          title: '몸 선택',
                          description: '몸 에셋을 고른 뒤 바로 아래에서 피부색을 바꿔 주세요.',
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _AssetOptionGrid(
                                labels: deokiveAvatarBodyLabels,
                                assets: deokiveAvatarBodyAssets,
                                selectedIndex: appState.avatarBodyType,
                                onTap: (index) => appState.updateAvatar(
                                  bodyType: index,
                                ),
                              ),
                              const SizedBox(height: 18),
                              Text(
                                '피부색',
                                style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 10),
                              _ColorPaletteWrap(
                                colors: deokiveAvatarSkinColors,
                                labels: const [
                                  '기본',
                                  '밝은 톤',
                                  '살구 톤',
                                  '태닝',
                                  '브라운',
                                  '블루',
                                  '퍼플',
                                  '핑크',
                                ],
                                selectedIndex: appState.avatarSkinToneIndex,
                                onTap: (index) => appState.updateAvatar(
                                  skinToneIndex: index,
                                ),
                              ),
                            ],
                          ),
                        ),
                        _EditorPane(
                          title: '머리 선택',
                          description: '머리 에셋을 고른 뒤 바로 아래에서 머리색을 바꿔 주세요.',
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _AssetOptionGrid(
                                labels: deokiveAvatarHairLabels,
                                assets: deokiveAvatarHairAssets,
                                selectedIndex: appState.avatarHairStyle,
                                onTap: (index) => appState.updateAvatar(
                                  hairStyle: index,
                                ),
                              ),
                              const SizedBox(height: 18),
                              Text(
                                '머리색',
                                style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 10),
                              _ColorPaletteWrap(
                                colors: deokiveAvatarHairColors,
                                labels: const [
                                  '브라운',
                                  '블랙',
                                  '카멜',
                                  '블루',
                                  '핑크',
                                  '민트',
                                ],
                                selectedIndex: appState.avatarHairColorIndex,
                                onTap: (index) => appState.updateAvatar(
                                  hairColorIndex: index,
                                ),
                              ),
                            ],
                          ),
                        ),
                        _EditorPane(
                          title: '의상 색상',
                          description: '의상은 도형이 아니라 아바타 본체 색감에 자연스럽게 반영돼요.',
                          child: _ColorPaletteWrap(
                            colors: outfitColors,
                            labels: deokiveAvatarOutfitLabels,
                            selectedIndex: appState.avatarOutfitColorIndex,
                            onTap: (index) => appState.updateAvatar(
                              outfitColorIndex: index,
                            ),
                          ),
                        ),
                        _EditorPane(
                          title: '소품 선택',
                          description: '소품 에셋을 바로 켜고 끌 수 있어요.',
                          child: _AccessoryOptionGrid(
                            assets: deokiveAvatarAccessoryAssets,
                            labels: deokiveAvatarAccessoryLabels,
                            selectedStates: [
                              appState.avatarHasHat,
                              appState.avatarHasCape,
                              appState.avatarHasHandheld,
                              appState.avatarHasBackRibbon,
                            ],
                            onTap: [
                              () => appState.updateAvatar(
                                    hasHat: !appState.avatarHasHat,
                                  ),
                              () => appState.updateAvatar(
                                    hasCape: !appState.avatarHasCape,
                                  ),
                              () => appState.updateAvatar(
                                    hasHandheld: !appState.avatarHasHandheld,
                                  ),
                              () => appState.updateAvatar(
                                    hasBackRibbon: !appState.avatarHasBackRibbon,
                                  ),
                            ],
                          ),
                        ),
                      ],
                    ),
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

class _EditorPane extends StatelessWidget {
  final String title;
  final String description;
  final Widget child;

  const _EditorPane({
    required this.title,
    required this.description,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              description,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }
}

class _AssetOptionGrid extends StatelessWidget {
  final List<String> labels;
  final List<String> assets;
  final int selectedIndex;
  final ValueChanged<int> onTap;
  final BoxFit fit;

  const _AssetOptionGrid({
    required this.labels,
    required this.assets,
    required this.selectedIndex,
    required this.onTap,
    this.fit = BoxFit.contain,
  });

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.95,
      ),
      itemCount: labels.length + 1,
      itemBuilder: (context, index) {
        if (index == 0) {
          return _SelectableCard(
            label: '미설정',
            selected: selectedIndex < 0,
            onTap: () => onTap(-1),
            child: const Center(
              child: Icon(Icons.do_not_disturb_alt_rounded, size: 34),
            ),
          );
        }

        final assetIndex = index - 1;
        return _SelectableCard(
          label: labels[assetIndex],
          selected: selectedIndex == assetIndex,
          onTap: () => onTap(assetIndex),
          child: Image.asset(
            assets[assetIndex],
            fit: fit,
            alignment: Alignment.center,
            errorBuilder: (context, error, stackTrace) {
              return const Center(
                child: Icon(Icons.broken_image_outlined, size: 28),
              );
            },
          ),
        );
      },
    );
  }
}

class _AccessoryOptionGrid extends StatelessWidget {
  final List<String> assets;
  final List<String> labels;
  final List<bool> selectedStates;
  final List<VoidCallback> onTap;

  const _AccessoryOptionGrid({
    required this.assets,
    required this.labels,
    required this.selectedStates,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.95,
      ),
      itemCount: labels.length,
      itemBuilder: (context, index) {
        return _SelectableCard(
          label: labels[index],
          selected: selectedStates[index],
          onTap: onTap[index],
          child: Image.asset(
            assets[index],
            fit: BoxFit.contain,
            alignment: Alignment.center,
            errorBuilder: (context, error, stackTrace) {
              return const Center(
                child: Icon(Icons.broken_image_outlined, size: 28),
              );
            },
          ),
        );
      },
    );
  }
}

class _SelectableCard extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Widget child;

  const _SelectableCard({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected
              ? theme.colorScheme.primary.withValues(alpha: 0.10)
              : theme.colorScheme.surface,
          border: Border.all(
            color: selected ? theme.colorScheme.primary : theme.dividerColor,
            width: selected ? 2 : 1,
          ),
        ),
        padding: const EdgeInsets.all(10),
        child: Column(
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  color: theme.colorScheme.surfaceContainerHighest,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      child,
                      if (selected)
                        const Align(
                          alignment: Alignment.topRight,
                          child: Padding(
                            padding: EdgeInsets.all(8),
                            child: Icon(Icons.check_circle),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              label,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ColorPaletteWrap extends StatelessWidget {
  final List<Color> colors;
  final List<String> labels;
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _ColorPaletteWrap({
    required this.colors,
    required this.labels,
    required this.selectedIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 12,
      children: List.generate(
        colors.length,
        (index) => _LabeledColorDot(
          color: colors[index],
          label: labels[index],
          selected: selectedIndex == index,
          onTap: () => onTap(index),
        ),
      ),
    );
  }
}

class _LabeledColorDot extends StatelessWidget {
  final Color color;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _LabeledColorDot({
    required this.color,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 68,
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(999),
            onTap: onTap,
            child: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: color,
                border: Border.all(
                  color: selected
                      ? Theme.of(context).colorScheme.primary
                      : Colors.black.withValues(alpha: 0.08),
                  width: selected ? 3 : 1.4,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.08),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: selected
                  ? const Icon(Icons.check, size: 18, color: Colors.white)
                  : null,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}
