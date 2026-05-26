import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../config/admin_config.dart';
import '../l10n/app_language.dart';
import '../l10n/app_strings.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../theme/font_catalog.dart';
import '../widgets/deokive_header_title.dart';
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
                                        : null)
                                    as ImageProvider<Object>?,
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
                        decoration: const InputDecoration(
                          labelText: '닉네임',
                          counterText: '',
                          helperText: '최대 15자',
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
                      id: null,
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

  Future<void> _openPaletteSheet(BuildContext context, AppState appState) async {
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
              final selected =
                  (appState.fontFamily ?? 'pretendard') == font.id;
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
                        if (appState.googleSignInDebugError != null) ...[
                          const SizedBox(height: 8),
                          SelectableText(
                            appState.googleSignInDebugError!,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.error,
                            ),
                          ),
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
                            const SizedBox(width: 8),
                            Expanded(
                              child: FilledButton(
                                onPressed: () => appState.signOut(),
                                child: const Text('로그아웃'),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (appState.isLoggedIn &&
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
                      appState.linkedGoogleEmail ??
                          '구글 로그인으로도 같은 계정에 접속',
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
                      title: const Text('글씨 크기'),
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
                                  f.id ==
                                  (appState.fontFamily ?? 'pretendard'),
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
                    if (appState.isLoggedIn)
                      SwitchListTile(
                        value: appState.adminMode,
                        title: const Text('관리자 모드'),
                        subtitle: Text(
                          appState.adminMode
                              ? '공지/정보 글 작성·수정, 정보봇 글 승인 권한이 켜져 있어요'
                              : '관리자 암호를 입력해야 켤 수 있어요',
                        ),
                        secondary: Icon(
                          appState.adminMode
                              ? Icons.shield_rounded
                              : Icons.shield_outlined,
                          color: appState.adminMode
                              ? palette.primary
                              : null,
                        ),
                        onChanged: (value) {
                          if (!value) {
                            appState.setAdminMode(false);
                            return;
                          }
                          _promptAdminPasscode(context, appState);
                        },
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
                      title: const Text('저작권 / 라이선스'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => showLicensePage(
                        context: context,
                        applicationName: 'Deokive',
                        applicationLegalese:
                            '© 2026 Deokive. All rights reserved.',
                      ),
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
}

const String _kTermsOfService = '''
Deokive 이용약관 (요약)

1. 서비스 목적
Deokive는 굿즈 컬렉션 기록과 정리를 돕기 위한 개인 아카이브 도구입니다.

2. 계정과 책임
이용자는 계정 정보(아이디·태그·닉네임)를 안전하게 관리해야 하며, 부정 사용으로 인한 책임은 이용자 본인에게 있습니다.

3. 콘텐츠
이용자가 업로드한 사진·텍스트는 이용자에게 귀속됩니다. Deokive는 서비스 제공을 위해 필요한 범위 내에서만 데이터를 처리합니다.

4. 금지 행위
타인 권리 침해, 불법 콘텐츠 업로드, 서비스 안정성을 해치는 행위는 금지됩니다.

5. 약관 변경
약관이 변경되면 앱 공지 또는 업데이트를 통해 안내합니다.
''';

const String _kPrivacyPolicy = '''
Deokive 개인정보 처리방침 (요약)

1. 수집 항목
- 계정: 아이디, 닉네임, 태그, 프로필 이미지(선택)
- 굿즈 데이터: 사용자가 입력한 굿즈 정보 및 이미지 (기기 로컬 저장)
- 구글 로그인 시: 구글 계정의 이메일·식별자(이름, 프로필 사진)

2. 이용 목적
서비스 제공, 동기화(공개 프로필만 서버 미러링), 백업, 문의 응대.

3. 저장 위치
대부분의 데이터는 기기 로컬에 저장됩니다. 공개 프로필(닉네임/태그/대표 배지)만 서버에 미러링됩니다.

4. 제3자 제공
법령에 의한 경우를 제외하고 제3자에게 제공하지 않습니다.

5. 권리
이용자는 계정 정보 수정·삭제, 데이터 내려받기, 가입 해지를 언제든 요청할 수 있습니다.

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
  if (code == null || code.isEmpty) return '구글 계정 연동에 실패했습니다.';
  switch (code) {
    case 'cancelled':
      return '연동을 취소했습니다.';
    case 'already_linked_elsewhere':
      return '이 구글 계정은 이미 다른 계정에 연동되어 있습니다.';
    case 'unsupported_platform':
      return '이 플랫폼에서는 구글 로그인이 지원되지 않습니다.';
    case 'missing_web_client_id':
      return '구글 로그인 설정이 누락되었습니다.';
    case 'not_local_account':
      return '아이디 로그인 상태에서만 연동할 수 있습니다.';
    case 'local_account_missing':
      return '계정 정보를 찾을 수 없습니다. 다시 로그인해 주세요.';
    default:
      // Pass through underlying platform errors (network_error, ApiException
      // 10, etc.) so users can report what they actually saw.
      return '연동 실패: $code';
  }
}

Future<void> _promptAdminPasscode(
    BuildContext context, AppState appState) async {
  final controller = TextEditingController();
  var obscure = true;
  final ok = await showDialog<bool>(
    context: context,
    builder: (dctx) => StatefulBuilder(
      builder: (ctx, setDialogState) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.shield_outlined, size: 20),
            SizedBox(width: 8),
            Text('관리자 인증'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('관리자 암호를 입력하세요.',
                style: TextStyle(fontSize: 13)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              obscureText: obscure,
              autofocus: true,
              onSubmitted: (_) => Navigator.pop(dctx, true),
              decoration: InputDecoration(
                labelText: '암호',
                prefixIcon: const Icon(Icons.key_rounded),
                suffixIcon: IconButton(
                  icon: Icon(obscure
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined),
                  onPressed: () =>
                      setDialogState(() => obscure = !obscure),
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dctx, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dctx, true),
            child: const Text('확인'),
          ),
        ],
      ),
    ),
  );
  if (ok != true) return;
  if (!context.mounted) return;
  final messenger = ScaffoldMessenger.of(context);
  if (AdminConfig.verify(controller.text)) {
    appState.setAdminMode(true);
    messenger.showSnackBar(
      const SnackBar(content: Text('관리자 모드가 켜졌어요.')),
    );
  } else {
    messenger.showSnackBar(
      const SnackBar(content: Text('암호가 올바르지 않습니다.')),
    );
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
        const SnackBar(content: Text('구글 계정이 연동되었어요.')),
      );
    } else {
      messenger.showSnackBar(
        SnackBar(
            content:
                Text(_googleLinkErrorMessage(widget.appState.googleSignInError))),
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
            '연동을 해제하면 구글 로그인으로는 이 계정에 자동 접속할 수 없게 됩니다. '
            '아이디 로그인은 계속 가능해요.'),
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
    final linkedEmail = appState.linkedGoogleEmail;
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
                      : theme.colorScheme.primaryContainer.withValues(alpha: 0.6),
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
              '아이디 / 구글 두 가지 방법 모두 같은 계정에 접속됩니다. 폴더·굿즈·뱃지가 자동 공유돼요.',
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
              '구글 계정을 연동하면 아이디 로그인 / 구글 로그인 둘 다 같은 계정으로 접속할 수 있어요. '
              '두 기기에서 데이터를 그대로 이어 받을 수 있어 편리합니다.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
                height: 1.5,
              ),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: (_busy || !appState.supportsGoogleSignIn) ? null : _link,
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
              label: Text(_busy ? '연동 중…' : '구글 계정 연동하기'),
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
