import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../l10n/app_language.dart';
import '../l10n/app_strings.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../theme/font_catalog.dart';
import '../widgets/deokive_header_title.dart';
import 'auth_screen.dart';
import 'support_write_screen.dart';

const bool _showGoogleUi = false;

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
    final pickedBytes = await result.readAsBytes();
    if (!context.mounted) return null;
    return _openProfileImageEditor(context, pickedBytes);
  }

  Future<Uint8List?> _openProfileImageEditor(
    BuildContext context,
    Uint8List originalBytes,
  ) async {
    final codec = await ui.instantiateImageCodec(originalBytes);
    final frame = await codec.getNextFrame();
    final image = frame.image;
    if (!context.mounted) return null;
    const previewSize = 240.0;
    final baseScale = math.max(
      previewSize / image.width,
      previewSize / image.height,
    );
    double zoom = 1;
    double offsetX = 0;
    double offsetY = 0;

    return showDialog<Uint8List>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            double maxOffsetX() {
              final displayedWidth = image.width * baseScale * zoom;
              return math.max(0, (displayedWidth - previewSize) / 2);
            }

            double maxOffsetY() {
              final displayedHeight = image.height * baseScale * zoom;
              return math.max(0, (displayedHeight - previewSize) / 2);
            }

            void clampOffsets() {
              offsetX = offsetX.clamp(-maxOffsetX(), maxOffsetX());
              offsetY = offsetY.clamp(-maxOffsetY(), maxOffsetY());
            }

            final displayedWidth = image.width * baseScale * zoom;
            final displayedHeight = image.height * baseScale * zoom;
            final left = (previewSize - displayedWidth) / 2 + offsetX;
            final top = (previewSize - displayedHeight) / 2 + offsetY;

            Future<Uint8List> exportImage() async {
              final scale = baseScale * zoom;
              final cropLeft =
                  ((image.width * scale - previewSize) / 2 - offsetX) / scale;
              final cropTop =
                  ((image.height * scale - previewSize) / 2 - offsetY) / scale;
              final cropSize = previewSize / scale;
              final srcRect = Rect.fromLTWH(
                cropLeft
                    .clamp(0, math.max(0, image.width - cropSize))
                    .toDouble(),
                cropTop
                    .clamp(0, math.max(0, image.height - cropSize))
                    .toDouble(),
                cropSize.clamp(1, image.width.toDouble()).toDouble(),
                cropSize.clamp(1, image.height.toDouble()).toDouble(),
              );
              const outputSize = 900.0;
              final recorder = ui.PictureRecorder();
              final canvas = Canvas(recorder);
              final clipPath = Path()
                ..addOval(
                  const Rect.fromLTWH(0, 0, outputSize, outputSize),
                );
              canvas.clipPath(clipPath);
              canvas.drawImageRect(
                image,
                srcRect,
                const Rect.fromLTWH(0, 0, outputSize, outputSize),
                Paint(),
              );
              final rendered = await recorder.endRecording().toImage(
                    outputSize.toInt(),
                    outputSize.toInt(),
                  );
              final byteData =
                  await rendered.toByteData(format: ui.ImageByteFormat.png);
              return byteData!.buffer.asUint8List();
            }

            return AlertDialog(
              title: const Text('프로필 사진 조정'),
              content: SizedBox(
                width: 360,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: SizedBox(
                        width: previewSize,
                        height: previewSize,
                        child: GestureDetector(
                          onPanUpdate: (details) {
                            setDialogState(() {
                              offsetX += details.delta.dx;
                              offsetY += details.delta.dy;
                              clampOffsets();
                            });
                          },
                          child: Stack(
                            children: [
                              Positioned.fill(
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: Colors.black12,
                                    borderRadius: BorderRadius.circular(24),
                                  ),
                                ),
                              ),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(24),
                                child: Stack(
                                  children: [
                                    Positioned(
                                      left: left,
                                      top: top,
                                      child: Image.memory(
                                        originalBytes,
                                        width: displayedWidth,
                                        height: displayedHeight,
                                        fit: BoxFit.cover,
                                      ),
                                    ),
                                    const Positioned.fill(
                                      child: IgnorePointer(
                                        child: CustomPaint(
                                          painter: _ProfileCropOverlayPainter(),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      '사진을 드래그해서 중앙을 맞추고, 아래 슬라이더로 확대를 조정해 주세요.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    const Text('확대'),
                    Slider(
                      value: zoom,
                      min: 1,
                      max: 3,
                      onChanged: (value) {
                        setDialogState(() {
                          zoom = value;
                          clampOffsets();
                        });
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () async {
                    final cropped = await exportImage();
                    if (!dialogContext.mounted) return;
                    Navigator.pop(dialogContext, cropped);
                  },
                  child: const Text('적용'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _openProfileEditDialog(
    BuildContext context,
    AppState appState,
  ) async {
    if (!appState.canEditProfile) return;

    final nameController =
        TextEditingController(text: appState.currentDisplayName);
    final isAdmin = appState.isAdminSession;
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
                        maxLength: 15,
                        enabled: !isAdmin,
                        decoration: InputDecoration(
                          labelText: '닉네임',
                          counterText: '',
                          helperText:
                              isAdmin ? '관리자 닉네임은 변경할 수 없어요.' : '최대 15자',
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
                  onPressed: () async {
                    final success = await appState.setProfile(
                      name: nameController.text.trim(),
                      handle: '',
                      id: null,
                      imageBytes: selectedImage,
                    );
                    if (!context.mounted || !dialogContext.mounted) return;
                    if (!success) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            '프로필 정보를 저장할 수 없습니다. 입력값을 다시 확인해 주세요.',
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

  Future<void> _openFontSizeSheet(
    BuildContext context,
    AppState appState,
  ) async {
    final current = AppFontSizeX.fromScale(appState.fontScale);
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: AppFontSize.values.map((size) {
              final selected = size == current;
              return ListTile(
                title: Text(
                  size.label,
                  style: TextStyle(fontSize: 14 * size.scale),
                ),
                trailing: selected ? const Icon(Icons.check_rounded) : null,
                onTap: () {
                  appState.setFontScale(size.scale);
                  Navigator.pop(sheetContext);
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  Future<void> _openFontFamilySheet(
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
            children: kAppFonts.map((font) {
              final selected = (appState.fontFamily ?? 'pretendard') == font.id;
              return ListTile(
                title: Text(
                  font.label,
                  style: TextStyle(
                    fontFamily: fontFamilyFor(font.id) ?? 'Pretendard',
                  ),
                ),
                trailing: selected ? const Icon(Icons.check_rounded) : null,
                onTap: () {
                  appState.setFontFamily(
                    font.id == 'pretendard' ? null : font.id,
                  );
                  Navigator.pop(sheetContext);
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  Future<void> _confirmDeleteNickname(
    BuildContext context,
    AppState appState,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('탈퇴하기'),
          content: const Text(
            '정말로 탈퇴할까요?\n'
            '탈퇴하면 현재 닉네임 연결만 해제되고, 이 기기에 저장된 굿즈 데이터는 삭제되지 않아요.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('탈퇴하기'),
            ),
          ],
        );
      },
    );
    if (confirmed != true || !context.mounted) return;
    await appState.clearDeviceNicknamePreservingLocalData();
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('탈퇴했어요. 이 기기의 로컬 데이터는 그대로 유지돼요.'),
      ),
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
            centerTitle: true,
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
                                  appState.currentDisplayName,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: theme.textTheme.titleLarge?.copyWith(
                                    fontWeight: FontWeight.w800,
                                  ),
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
                                child: const Text('닉네임 설정'),
                              ),
                            ),
                            if (_showGoogleUi) ...[
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
                          ],
                        ),
                        if (_showGoogleUi) ...[
                          const SizedBox(height: 10),
                          Text(
                            appState.googleSignInMessage,
                            style: theme.textTheme.bodySmall,
                          ),
                          if (appState.googleSignInDebugError != null) ...[
                            const SizedBox(height: 8),
                            SelectableText(
                              appState.googleSignInDebugError!,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.error,
                              ),
                            ),
                          ],
                        ],
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
                            if (!appState.isAdminSession) ...[
                            const SizedBox(width: 8),
                            Expanded(
                              child: FilledButton(
                                onPressed: () =>
                                    _confirmDeleteNickname(context, appState),
                                child: const Text('탈퇴하기'),
                              ),
                            ),
                            ],
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (_showGoogleUi &&
                  appState.isLoggedIn &&
                  appState.authProvider == AuthProviderType.local) ...[
                Card(
                  child: ListTile(
                    leading: Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: appState.linkedGoogleEmail != null
                            ? Colors.green.shade50
                            : palette.softSurface,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(
                        appState.linkedGoogleEmail != null
                            ? Icons.check_circle_rounded
                            : Icons.link_rounded,
                        color: appState.linkedGoogleEmail != null
                            ? Colors.green.shade600
                            : palette.primary,
                        size: 20,
                      ),
                    ),
                    title: const Text('구글 계정 연동'),
                    subtitle: Text(
                      appState.linkedGoogleEmailMasked ?? '구글 로그인으로도 같은 계정에 접속',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _openGoogleLinkSheet(context, appState),
                  ),
                ),
                const SizedBox(height: 16),
              ],
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
                    ListTile(
                      leading: const Icon(Icons.format_size_rounded),
                      title: const Text('글자 크기'),
                      subtitle: Text(
                          AppFontSizeX.fromScale(appState.fontScale).label),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openFontSizeSheet(context, appState),
                    ),
                    ListTile(
                      leading: const Icon(Icons.text_fields_rounded),
                      title: const Text('글꼴'),
                      subtitle: Text(
                        kAppFonts
                            .firstWhere(
                              (f) =>
                                  f.id == (appState.fontFamily ?? 'pretendard'),
                              orElse: () => kAppFonts.first,
                            )
                            .label,
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openFontFamilySheet(context, appState),
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
              const SizedBox(height: 16),
              Card(
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.gavel_rounded),
                      title: const Text('이용약관'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openLegal(
                        context,
                        title: '이용약관',
                        body: _kTermsOfService,
                      ),
                    ),
                    const Divider(height: 0),
                    ListTile(
                      leading: const Icon(Icons.privacy_tip_outlined),
                      title: const Text('개인정보 처리방침'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openLegal(
                        context,
                        title: '개인정보 처리방침',
                        body: _kPrivacyPolicy,
                      ),
                    ),
                    const Divider(height: 0),
                    ListTile(
                      leading: const Icon(Icons.copyright_outlined),
                      title: const Text('라이선스 / 저작권'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openLicenseSummary(context),
                    ),
                    const Divider(height: 0),
                    const ListTile(
                      leading: Icon(Icons.info_outline),
                      title: Text('앱 버전'),
                      subtitle: Text('1.0.0'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _openLegal(BuildContext context,
      {required String title, required String body}) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(title)),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Text(body, style: const TextStyle(height: 1.5)),
          ),
        ),
      ),
    );
  }

  void _openLicenseSummary(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text('라이선스 / 저작권')),
          body: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                'Deokive 라이선스 안내',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Deokive는 자체 제작 코드와 오픈소스 Flutter 및 여러 서드파티 패키지를 함께 사용하고 있습니다.',
                style: TextStyle(height: 1.6),
              ),
              const SizedBox(height: 20),
              const Text(
                '저작권',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Copyright 2026 Deokive. All rights reserved.',
                style: TextStyle(height: 1.6),
              ),
              const SizedBox(height: 20),
              const Text(
                '사용 중인 주요 오픈소스',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Flutter SDK\n'
                'provider\n'
                'http\n'
                'hive_ce_flutter\n'
                'google_sign_in\n'
                'image_picker',
                style: TextStyle(height: 1.7),
              ),
              const SizedBox(height: 20),
              const Text(
                '안내',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '각 오픈소스 라이선스 전문은 아래 버튼에서 확인할 수 있습니다.',
                style: TextStyle(height: 1.6),
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => showLicensePage(
                  context: context,
                  applicationName: 'Deokive',
                  applicationLegalese:
                      'Copyright 2026 Deokive. All rights reserved.',
                ),
                child: const Text('전체 오픈소스 고지 보기'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
class _ProfileCropOverlayPainter extends CustomPainter {
  const _ProfileCropOverlayPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final outer = Path()..addRect(Rect.fromLTWH(0, 0, size.width, size.height));
    final circle = Path()
      ..addOval(
        Rect.fromCircle(
          center: Offset(size.width / 2, size.height / 2),
          radius: size.width / 2,
        ),
      );
    final overlay = Path.combine(PathOperation.difference, outer, circle);
    canvas.drawPath(
      overlay,
      Paint()..color = Colors.black.withValues(alpha: 0.35),
    );
    canvas.drawOval(
      Rect.fromCircle(
        center: Offset(size.width / 2, size.height / 2),
        radius: size.width / 2 - 1,
      ),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = Colors.white.withValues(alpha: 0.92),
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

const String _kTermsOfService = '''
Deokive 이용약관 (요약)

1. 서비스 목적
Deokive는 굿즈 컬렉션을 기록하고 정리하기 위한 개인 아카이브 서비스입니다.

2. 계정과 책임
이용자는 닉네임, 기기 정보 등 자신의 연결 정보를 스스로 관리해야 하며, 부주의로 인한 문제에 대한 책임은 이용자 본인에게 있습니다.

3. 콘텐츠
이용자가 작성하거나 업로드한 글, 댓글, 이미지의 책임은 이용자에게 있습니다. Deokive는 서비스 제공을 위한 범위 안에서만 해당 데이터를 처리합니다.

4. 금지 행위
타인의 권리를 침해하는 행위, 불법 콘텐츠 게시, 서비스 운영을 방해하는 행위는 금지됩니다.

5. 약관 변경
약관이 변경되면 공지나 업데이트를 통해 안내합니다.
''';

const String _kPrivacyPolicy = '''
Deokive 개인정보 처리방침 (요약)

1. 수집 항목
- 기기/프로필: 기기 식별값, 닉네임, 프로필 이미지(선택)
- 개인 보관 데이터: 사용자가 입력한 굿즈 정보, 폴더 정보, 개인 일정, 메모, 이미지
- 공유 데이터: 게시판 글, 댓글, 좋아요, 조회 기록, 관리자 공지/정보글, 공유 일정
- 선택 항목: 구글 계정 연동 시 구글이 제공하는 기본 프로필 정보 일부

2. 이용 목적
- 웹앱 기능 제공
- 기기별 로컬 보관함 유지
- 게시판/공유 일정/공지 데이터 동기화
- 관리자 운영, 문의 응답, 기본적인 오류 대응

3. 저장 위치
- 개인 굿즈 보관함, 폴더, 개인 일정 등 대부분의 개인 데이터는 현재 이 기기의 브라우저 로컬 저장소에 저장됩니다.
- 게시판 글/댓글, 좋아요, 조회 기록, 닉네임, 기기 식별값, 관리자 공지/정보글, 공유 일정처럼 여러 사용자가 함께 봐야 하는 데이터는 서버에 저장될 수 있습니다.
- 현재 별도의 자동 클라우드 백업 기능은 제공하지 않습니다.

4. 제3자 제공
법령에 따른 경우를 제외하고 이용자 데이터를 외부에 판매하거나 임의 제공하지 않습니다.

5. 이용자 권리
- 이용자는 닉네임 변경, 기기 연결 해제, 브라우저 로컬 데이터 삭제 등을 직접 수행할 수 있습니다.
- 브라우저 데이터 삭제 또는 기기 변경 시, 로컬에만 저장된 개인 보관 데이터는 복구되지 않을 수 있습니다.

6. 오프라인 사용
- 일부 화면과 개인 보관 데이터는 오프라인 상태에서도 기기 캐시를 통해 열람될 수 있습니다.
- 오프라인 상태에서 변경한 내용은 서버 연결이 필요한 기능에 즉시 반영되지 않을 수 있습니다.

문의: deokivecs@gmail.com
''';

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

String _googleLinkErrorMessage(String? code) {
  if (code == null || code.isEmpty) return '구글 계정 연동에 실패했어요.';
  switch (code) {
    case 'cancelled':
      return '연동을 취소했어요.';
    case 'already_linked_elsewhere':
      return '이 구글 계정은 이미 다른 계정에 연동되어 있어요.';
    case 'unsupported_platform':
      return '현재 플랫폼에서는 구글 로그인을 지원하지 않아요.';
    case 'missing_web_client_id':
      return '구글 로그인 설정이 아직 완료되지 않았어요.';
    case 'not_local_account':
      return '일반 계정 로그인 상태에서만 연동할 수 있어요.';
    case 'local_account_missing':
      return '계정 정보를 찾을 수 없어요. 다시 로그인해 주세요.';
    default:
      return '연동 실패: $code';
  }
}

void _openGoogleLinkSheet(BuildContext context, AppState appState) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (sheetContext) => _GoogleLinkSheet(appState: appState),
  );
}

class _GoogleLinkSheet extends StatefulWidget {
  final AppState appState;
  const _GoogleLinkSheet({required this.appState});

  @override
  State<_GoogleLinkSheet> createState() => _GoogleLinkSheetState();
}

class _GoogleLinkSheetState extends State<_GoogleLinkSheet> {
  bool _busy = false;

  Future<void> _link() async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    final ok = await widget.appState.linkGoogleToCurrentLocalAccount();
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) {
      Navigator.pop(context);
      messenger.showSnackBar(
        const SnackBar(content: Text('구글 계정을 연동했어요.')),
      );
    } else {
      messenger.showSnackBar(
        SnackBar(
            content: Text(
                _googleLinkErrorMessage(widget.appState.googleSignInError))),
      );
    }
  }

  Future<void> _unlink() async {
    final messenger = ScaffoldMessenger.of(context);
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dctx) => AlertDialog(
        title: const Text('구글 계정 연동 해제'),
        content: const Text(
          '연동을 해제하면 구글 로그인으로는 이 계정에 자동 접속할 수 없게 돼요. 일반 닉네임 계정은 계속 사용할 수 있어요.',
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(dctx, false),
              child: const Text('취소')),
          FilledButton(
              onPressed: () => Navigator.pop(dctx, true),
              child: const Text('해제')),
        ],
      ),
    );
    if (confirm != true) return;
    setState(() => _busy = true);
    await widget.appState.unlinkGoogleFromCurrentLocalAccount();
    if (!mounted) return;
    setState(() => _busy = false);
    Navigator.pop(context);
    messenger.showSnackBar(
      const SnackBar(content: Text('구글 계정 연동을 해제했어요.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final appState = context.watch<AppState>();
    final linkedEmail = appState.linkedGoogleEmailMasked;
    final isLinked = linkedEmail != null;

    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        4,
        20,
        20 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: isLinked
                      ? Colors.green.shade50
                      : theme.colorScheme.primaryContainer
                          .withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  isLinked ? Icons.check_circle_rounded : Icons.link_rounded,
                  color: isLinked
                      ? Colors.green.shade600
                      : theme.colorScheme.primary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  '구글 계정 연동',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (isLinked) ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.green.shade100),
              ),
              child: Row(
                children: [
                  Icon(Icons.account_circle_rounded,
                      color: Colors.green.shade700, size: 28),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '연동됨',
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: Colors.green.shade700,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          linkedEmail,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Text(
              '일반 로그인과 구글 로그인 모두 같은 계정으로 연결됩니다. 닉네임과 게시판 기록도 함께 유지돼요.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                height: 1.4,
              ),
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: _busy ? null : _unlink,
              icon: const Icon(Icons.link_off_rounded, size: 18),
              label: const Text('연동 해제'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(48),
              ),
            ),
          ] else ...[
            Text(
              '구글 계정을 연동하면 일반 로그인과 구글 로그인 모두 같은 계정으로 이어져서, 다른 기기에서도 같은 데이터를 이어서 사용할 수 있어요.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
                height: 1.5,
              ),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed:
                  (_busy || !appState.supportsGoogleSignIn) ? null : _link,
              icon: _busy
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.link_rounded, size: 18),
              label: Text(_busy ? '연동 중...' : '구글 계정 연동하기'),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(48),
              ),
            ),
            if (!appState.supportsGoogleSignIn) ...[
              const SizedBox(height: 10),
              Text(
                appState.googleSignInMessage,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.error,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ],
        ],
      ),
    );
  }
}
