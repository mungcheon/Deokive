import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../config/monetization_catalog.dart';
import '../l10n/app_language.dart';
import '../l10n/app_strings.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_header_title.dart';
import '../widgets/premium_gate_card.dart';
import 'auth_screen.dart';
import 'support_write_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  Future<Uint8List?> _pickProfileImage(BuildContext context) async {
    final picker = ImagePicker();
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.photo_camera_outlined),
                title: const Text('카메라로 촬영'),
                onTap: () => Navigator.pop(sheetContext, ImageSource.camera),
              ),
              ListTile(
                leading: const Icon(Icons.photo_library_outlined),
                title: const Text('앨범에서 선택'),
                onTap: () => Navigator.pop(sheetContext, ImageSource.gallery),
              ),
            ],
          ),
        );
      },
    );

    if (source == null) return null;
    final result = await picker.pickImage(source: source, imageQuality: 92);
    if (result == null) return null;
    return result.readAsBytes();
  }

  Future<void> _openProfileEditDialog(
    BuildContext context,
    AppState appState,
  ) async {
    if (!appState.canEditProfile) return;

    final nameController = TextEditingController(text: appState.displayName);
    final idController = TextEditingController(text: appState.accountId);
    final tagController =
        TextEditingController(text: appState.tag.replaceFirst('@', ''));
    Uint8List? selectedImage;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('프로필 수정'),
              content: SizedBox(
                width: 420,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Center(
                        child: GestureDetector(
                          onTap: () async {
                            final image = await _pickProfileImage(context);
                            if (image == null) return;
                            setDialogState(() => selectedImage = image);
                          },
                          child: CircleAvatar(
                            radius: 42,
                            backgroundColor: Theme.of(context)
                                .colorScheme
                                .surfaceContainerHighest,
                            backgroundImage: selectedImage != null
                                ? MemoryImage(selectedImage!)
                                : (appState.profileImageBytes != null
                                    ? MemoryImage(appState.profileImageBytes!)
                                    : null) as ImageProvider<Object>?,
                            child: selectedImage == null &&
                                    appState.profileImageBytes == null
                                ? const Icon(Icons.person_outline, size: 32)
                                : null,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: nameController,
                        decoration: const InputDecoration(labelText: '닉네임'),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: idController,
                        enabled: !appState.isGoogleLinked,
                        decoration: InputDecoration(
                          labelText: '아이디',
                          helperText: appState.isGoogleLinked
                              ? '구글 로그인 계정은 아이디를 변경할 수 없습니다.'
                              : '영문과 숫자만 사용할 수 있습니다.',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: tagController,
                        decoration: const InputDecoration(
                          labelText: '태그',
                          prefixText: '@',
                          helperText: '영문과 숫자만 사용할 수 있고 띄어쓰기는 지원하지 않습니다.',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () {
                    final success = appState.setProfile(
                      name: nameController.text.trim(),
                      handle: tagController.text.trim(),
                      id: appState.isGoogleLinked
                          ? null
                          : idController.text.trim(),
                      imageBytes: selectedImage,
                    );
                    if (!success) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            '프로필 정보를 저장할 수 없습니다. 태그와 아이디 형식을 확인해 주세요.',
                          ),
                        ),
                      );
                      return;
                    }
                    Navigator.pop(dialogContext);
                  },
                  child: const Text('저장'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _openPaletteSheet(
      BuildContext context, AppState appState) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: ListView.separated(
            shrinkWrap: true,
            itemCount: deokivePalettes.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final spec = deokivePalettes[index];
              final selected = spec.palette == appState.appPalette;
              return ListTile(
                leading: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _PaletteDot(color: spec.primary),
                    const SizedBox(width: 6),
                    _PaletteDot(color: spec.accent),
                  ],
                ),
                title: Text(spec.label),
                trailing: selected ? const Icon(Icons.check_rounded) : null,
                onTap: () {
                  appState.setAppPalette(spec.palette);
                  Navigator.pop(sheetContext);
                },
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _openLanguageSheet(
    BuildContext context,
    AppState appState,
  ) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: AppLanguage.values.map((language) {
              final selected = appState.appLanguage == language;
              return ListTile(
                title: Text(language.label),
                trailing: selected ? const Icon(Icons.check_rounded) : null,
                onTap: () {
                  appState.setAppLanguage(language);
                  Navigator.pop(sheetContext);
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;
        final selectedPaletteSpec = paletteSpecFor(appState.appPalette);
        final strings = AppStrings.of(appState.appLanguage);

        return Scaffold(
          appBar: AppBar(
            title: const DeokiveHeaderTitle(),
            centerTitle: false,
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 34,
                            backgroundColor: palette.softSurface,
                            backgroundImage: appState.profileImageBytes != null
                                ? MemoryImage(appState.profileImageBytes!)
                                : null,
                            child: appState.profileImageBytes == null
                                ? const Icon(Icons.person_outline, size: 28)
                                : null,
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  appState.displayName,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: theme.textTheme.titleLarge?.copyWith(
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(appState.tag),
                                const SizedBox(height: 8),
                                Text(
                                  appState.backupStatusLabel,
                                  style: theme.textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (!appState.isLoggedIn) ...[
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => const AuthScreen(),
                                    ),
                                  );
                                },
                                child: const Text('로그인'),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: FilledButton(
                                onPressed: appState.supportsGoogleSignIn
                                    ? () async {
                                        final success =
                                            await appState.signInWithGoogle();
                                        if (!context.mounted || success) return;
                                        ScaffoldMessenger.of(context)
                                            .showSnackBar(
                                          SnackBar(
                                            content: Text(
                                              appState.googleSignInMessage,
                                            ),
                                          ),
                                        );
                                      }
                                    : null,
                                child: const Text('구글로 로그인'),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          appState.googleSignInMessage,
                          style: theme.textTheme.bodySmall,
                        ),
                      ] else ...[
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () =>
                                    _openProfileEditDialog(context, appState),
                                child: const Text('프로필 수정'),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: FilledButton(
                                onPressed: () => appState.signOut(),
                                child: const Text('로그아웃'),
                              ),
                            ),
                          ],
                        ),
                        if (appState.authProvider == AuthProviderType.google &&
                            appState.driveBackupError ==
                                'drive_scope_missing') ...[
                          const SizedBox(height: 8),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.tonalIcon(
                              onPressed: appState.driveBackupInProgress
                                  ? null
                                  : () async {
                                      final success = await appState
                                          .retryDriveBackupAuthorizationAndSync();
                                      if (!context.mounted) return;
                                      ScaffoldMessenger.of(context)
                                          .showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            success
                                                ? '로컬 데이터를 Google Drive에 백업했습니다.'
                                                : 'Google Drive 권한이 아직 허용되지 않았습니다.',
                                          ),
                                        ),
                                      );
                                    },
                              icon: const Icon(Icons.cloud_sync_outlined),
                              label: Text(
                                appState.driveBackupInProgress
                                    ? '백업 연결 중...'
                                    : 'Google Drive 백업 다시 연결',
                              ),
                            ),
                          ),
                        ],
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.palette_outlined),
                      title: const Text('팔레트'),
                      subtitle: Text(selectedPaletteSpec.label),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openPaletteSheet(context, appState),
                    ),
                    ListTile(
                      leading: const Icon(Icons.language_rounded),
                      title: Text(strings.languageLabel),
                      subtitle: Text(appState.appLanguage.label),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openLanguageSheet(context, appState),
                    ),
                    SwitchListTile(
                      value: appState.darkModeEnabled,
                      title: const Text('다크 모드'),
                      onChanged: appState.setDarkModeEnabled,
                    ),
                    SwitchListTile(
                      value: appState.pushEnabled,
                      title: const Text('알림 받기'),
                      onChanged: appState.setPushEnabled,
                    ),
                  ],
                ),
              ),
              if (appState.isLoggedIn) ...[
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        PremiumGateCard(
                          feature: PremiumFeature.unlimitedGoods,
                          unlocked: appState.isFeatureUnlocked(
                            PremiumFeature.unlimitedGoods,
                          ),
                          trailingLabel: appState.remainingGoodsSlots < 0
                              ? '무제한'
                              : '${appState.remainingGoodsSlots}개 남음',
                        ),
                        const SizedBox(height: 12),
                        PremiumGateCard(
                          feature: PremiumFeature.unlimitedFolders,
                          unlocked: appState.isFeatureUnlocked(
                            PremiumFeature.unlimitedFolders,
                          ),
                          trailingLabel: appState.remainingFolderSlots < 0
                              ? '무제한'
                              : '${appState.remainingFolderSlots}개 남음',
                        ),
                        const SizedBox(height: 12),
                        PremiumGateCard(
                          feature: PremiumFeature.adFree,
                          unlocked: appState.isFeatureUnlocked(
                            PremiumFeature.adFree,
                          ),
                          trailingLabel:
                              appState.shouldShowAd(AdPlacement.homeBanner)
                                  ? '광고 표시 중'
                                  : '광고 제거',
                        ),
                        const SizedBox(height: 12),
                        SwitchListTile(
                          value: appState.premiumEnabled,
                          title: const Text('프리미엄 미리보기'),
                          onChanged: appState.setPremiumEnabled,
                        ),
                        SwitchListTile(
                          value: appState.isFeatureUnlocked(
                            PremiumFeature.adFree,
                          ),
                          title: const Text('광고 제거 미리보기'),
                          onChanged: appState.setAdsRemoved,
                        ),
                        SwitchListTile(
                          value: appState.debugAdsEnabled,
                          title: const Text('테스트 광고 표시'),
                          onChanged: appState.setDebugAdsEnabled,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.support_agent_outlined),
                  title: const Text('문의하기'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const SupportWriteScreen(),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _PaletteDot extends StatelessWidget {
  final Color color;

  const _PaletteDot({required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 14,
      height: 14,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
    );
  }
}
