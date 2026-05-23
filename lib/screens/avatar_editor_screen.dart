import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_avatar.dart';

class AvatarEditorScreen extends StatefulWidget {
  const AvatarEditorScreen({super.key});

  @override
  State<AvatarEditorScreen> createState() => _AvatarEditorScreenState();
}

class _AvatarEditorScreenState extends State<AvatarEditorScreen> {
  final GlobalKey _previewKey = GlobalKey();

  Future<void> _savePreviewImage() async {
    final boundaryContext = _previewKey.currentContext;
    if (boundaryContext == null) return;

    final boundary =
        boundaryContext.findRenderObject() as RenderRepaintBoundary?;
    if (boundary == null) return;

    final image = await boundary.toImage(pixelRatio: 3);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    if (byteData == null || !mounted) return;

    final directory = await getApplicationDocumentsDirectory();
    final saveDir = Directory('${directory.path}\\saved_avatars');
    if (!await saveDir.exists()) {
      await saveDir.create(recursive: true);
    }

    final file = File(
      '${saveDir.path}\\avatar_${DateTime.now().millisecondsSinceEpoch}.png',
    );
    await file.writeAsBytes(byteData.buffer.asUint8List(), flush: true);

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('이미지 저장됨: ${file.path}')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 6,
      child: Consumer<AppState>(
        builder: (context, appState, _) {
          final palette = Theme.of(context).extension<DeokivePalette>()!;

          return Scaffold(
            appBar: AppBar(
              title: const Text('아바타 꾸미기'),
              bottom: const TabBar(
                isScrollable: true,
                tabs: [
                  Tab(text: '배경'),
                  Tab(text: '바디'),
                  Tab(text: '헤어'),
                  Tab(text: '얼굴'),
                  Tab(text: '옷'),
                  Tab(text: '소품'),
                ],
              ),
            ),
            body: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Stack(
                        children: [
                          RepaintBoundary(
                            key: _previewKey,
                            child: AspectRatio(
                              aspectRatio: 1,
                              child: Container(
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(24),
                                  border: Border.all(
                                    color: palette.primary.withValues(alpha: 0.42),
                                    width: 1.4,
                                  ),
                                ),
                                child: DeokiveAvatar(
                                  palette: palette,
                                  bodyType: appState.avatarBodyType,
                                  backgroundType: appState.avatarBackgroundType,
                                  hairStyle: appState.avatarHairStyle,
                                  hairColorIndex: appState.avatarHairColorIndex,
                                  accentColorIndex:
                                      appState.avatarAccentColorIndex,
                                  outfitColorIndex:
                                      appState.avatarOutfitColorIndex,
                                  skinToneIndex: appState.avatarSkinToneIndex,
                                  hasHat: appState.avatarHasHat,
                                  hasCape: appState.avatarHasCape,
                                  hasHandheld: appState.avatarHasHandheld,
                                  hasBackRibbon: appState.avatarHasBackRibbon,
                                ),
                              ),
                            ),
                          ),
                          Positioned(
                            top: 10,
                            right: 10,
                            child: FilledButton.icon(
                              onPressed: _savePreviewImage,
                              icon: const Icon(Icons.download_rounded, size: 18),
                              label: const Text('이미지 저장'),
                              style: FilledButton.styleFrom(
                                visualDensity: VisualDensity.compact,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Expanded(
                  child: TabBarView(
                    children: [
                      _BackgroundTab(appState: appState),
                      _BodyTab(appState: appState),
                      _HairTab(appState: appState),
                      _FaceTab(appState: appState),
                      _OutfitTab(appState: appState),
                      _AccessoryTab(appState: appState),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _BackgroundTab extends StatelessWidget {
  final AppState appState;

  const _BackgroundTab({required this.appState});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        _EditorSection(
          title: '배경 선택',
          child: GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.82,
            children: List.generate(
              deokiveAvatarBackgroundLabels.length,
              (index) => _BackgroundChoiceTile(
                label: deokiveAvatarBackgroundLabels[index],
                assetPath: deokiveAvatarBackgroundAssets[index],
                selected: appState.avatarBackgroundType == index,
                onTap: () => appState.updateAvatar(
                  backgroundType:
                      appState.avatarBackgroundType == index ? -1 : index,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _BodyTab extends StatelessWidget {
  final AppState appState;

  const _BodyTab({required this.appState});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        _EditorSection(
          title: '바디 선택',
          child: GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.82,
            children: List.generate(
              deokiveAvatarBodyAssets.length,
              (index) => _AssetChoiceTile(
                label: deokiveAvatarBodyLabels[index],
                assetPath: deokiveAvatarBodyAssets[index],
                selected: appState.avatarBodyType == index,
                onTap: () => appState.updateAvatar(
                  bodyType: appState.avatarBodyType == index ? -1 : index,
                ),
              ),
            ),
          ),
        ),
        _EditorSection(
          title: '피부톤',
          child: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: List.generate(
              deokiveAvatarSkinColors.length,
              (index) => _ColorDot(
                color: deokiveAvatarSkinColors[index],
                selected: appState.avatarSkinToneIndex == index,
                onTap: () => appState.updateAvatar(
                  skinToneIndex:
                      appState.avatarSkinToneIndex == index ? -1 : index,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _HairTab extends StatelessWidget {
  final AppState appState;

  const _HairTab({required this.appState});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        _EditorSection(
          title: '헤어 선택',
          child: GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.82,
            children: List.generate(
              deokiveAvatarHairAssets.length,
              (index) => _AssetChoiceTile(
                label: deokiveAvatarHairLabels[index],
                assetPath: deokiveAvatarHairAssets[index],
                selected: appState.avatarHairStyle == index,
                onTap: () => appState.updateAvatar(
                  hairStyle: appState.avatarHairStyle == index ? -1 : index,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _FaceTab extends StatelessWidget {
  final AppState appState;

  const _FaceTab({required this.appState});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        _EditorSection(
          title: '얼굴 선택',
          child: GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.82,
            children: List.generate(
              deokiveAvatarFaceLabels.length,
              (index) => _PlaceholderChoiceTile(
                label: deokiveAvatarFaceLabels[index],
                subtitle: '이미지 연결 대기',
                selected: appState.avatarSkinToneIndex == index,
                onTap: () => appState.updateAvatar(
                  skinToneIndex:
                      appState.avatarSkinToneIndex == index ? -1 : index,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _OutfitTab extends StatelessWidget {
  final AppState appState;

  const _OutfitTab({required this.appState});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        _EditorSection(
          title: '옷 선택',
          child: GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.82,
            children: List.generate(
              deokiveAvatarOutfitLabels.length,
              (index) => _PlaceholderChoiceTile(
                label: deokiveAvatarOutfitLabels[index],
                subtitle: '이미지 연결 대기',
                selected: appState.avatarOutfitColorIndex == index,
                onTap: () => appState.updateAvatar(
                  outfitColorIndex:
                      appState.avatarOutfitColorIndex == index ? -1 : index,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _AccessoryTab extends StatelessWidget {
  final AppState appState;

  const _AccessoryTab({required this.appState});

  @override
  Widget build(BuildContext context) {
    final accessoryStates = [
      appState.avatarHasHat,
      appState.avatarHasCape,
      appState.avatarHasHandheld,
      appState.avatarHasBackRibbon,
    ];

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        _EditorSection(
          title: '소품 선택',
          child: GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.82,
            children: List.generate(
              deokiveAvatarAccessoryLabels.length,
              (index) => _AssetChoiceTile(
                label: deokiveAvatarAccessoryLabels[index],
                assetPath: deokiveAvatarAccessoryAssets[index],
                selected: accessoryStates[index],
                onTap: () {
                  switch (index) {
                    case 0:
                      appState.updateAvatar(hasHat: !appState.avatarHasHat);
                      break;
                    case 1:
                      appState.updateAvatar(hasCape: !appState.avatarHasCape);
                      break;
                    case 2:
                      appState.updateAvatar(
                        hasHandheld: !appState.avatarHasHandheld,
                      );
                      break;
                    case 3:
                      appState.updateAvatar(
                        hasBackRibbon: !appState.avatarHasBackRibbon,
                      );
                      break;
                  }
                },
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _EditorSection extends StatelessWidget {
  final String title;
  final Widget child;

  const _EditorSection({
    required this.title,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}

class _AssetChoiceTile extends StatelessWidget {
  final String label;
  final String assetPath;
  final bool selected;
  final VoidCallback onTap;

  const _AssetChoiceTile({
    required this.label,
    required this.assetPath,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected
              ? palette.primary.withValues(alpha: 0.10)
              : theme.colorScheme.surface,
          border: Border.all(
            color: selected ? palette.primary : theme.dividerColor,
            width: selected ? 2 : 1,
          ),
        ),
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  color: theme.colorScheme.surfaceContainerHighest,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Image.asset(assetPath, fit: BoxFit.contain),
                      if (selected)
                        Align(
                          alignment: Alignment.topRight,
                          child: _SelectedBadge(color: palette.primary),
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

class _BackgroundChoiceTile extends StatelessWidget {
  final String label;
  final String assetPath;
  final bool selected;
  final VoidCallback onTap;

  const _BackgroundChoiceTile({
    required this.label,
    required this.assetPath,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected
              ? palette.primary.withValues(alpha: 0.10)
              : theme.colorScheme.surface,
          border: Border.all(
            color: selected ? palette.primary : theme.dividerColor,
            width: selected ? 2 : 1,
          ),
        ),
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    Image.asset(assetPath, fit: BoxFit.cover),
                    if (selected)
                      Align(
                        alignment: Alignment.topRight,
                        child: _SelectedBadge(color: palette.primary),
                      ),
                  ],
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

class _PlaceholderChoiceTile extends StatelessWidget {
  final String label;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  const _PlaceholderChoiceTile({
    required this.label,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected
              ? palette.primary.withValues(alpha: 0.10)
              : theme.colorScheme.surface,
          border: Border.all(
            color: selected ? palette.primary : theme.dividerColor,
            width: selected ? 2 : 1,
          ),
        ),
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  color: theme.colorScheme.surfaceContainerHighest,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Image.asset(deokiveAvatarUnsetAsset, fit: BoxFit.contain),
                      if (selected)
                        Align(
                          alignment: Alignment.topRight,
                          child: _SelectedBadge(color: palette.primary),
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
            const SizedBox(height: 2),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: theme.textTheme.labelSmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _SelectedBadge extends StatelessWidget {
  final Color color;

  const _SelectedBadge({required this.color});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.all(8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        '선택중',
        style: theme.textTheme.labelSmall?.copyWith(
          color: theme.colorScheme.onPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _ColorDot extends StatelessWidget {
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  const _ColorDot({
    required this.color,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          border: Border.all(
            color: selected
                ? Theme.of(context).colorScheme.onSurface
                : Colors.transparent,
            width: 3,
          ),
        ),
        child: selected
            ? Icon(
                Icons.check,
                size: 18,
                color: Theme.of(context).colorScheme.onSurface,
              )
            : null,
      ),
    );
  }
}
