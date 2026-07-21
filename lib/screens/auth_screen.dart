import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/platform_nickname_input.dart';

enum _NicknameStartChoice {
  applyExisting,
  freshStart,
}

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final nicknameController = TextEditingController();
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    final current = context.read<AppState>().configuredNickname;
    if (current != null && current.isNotEmpty) {
      nicknameController.text = current;
    }
  }

  @override
  void dispose() {
    nicknameController.dispose();
    super.dispose();
  }

  Future<void> _showNicknameBlockedDialog(String message) {
    return showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('닉네임 안내'),
          content: Text(message),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('확인'),
            ),
          ],
        );
      },
    );
  }

  Future<_NicknameStartChoice?> _askHowToUseExistingData() {
    return showDialog<_NicknameStartChoice>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('이전 데이터 발견'),
          content: const Text(
            '이 기기에는 이전 로컬 데이터가 남아 있어요.\n'
            '이 닉네임으로 들어오면서 이전 데이터를 반영할까요?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(
                dialogContext,
                _NicknameStartChoice.freshStart,
              ),
              child: const Text('아니요'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(
                dialogContext,
                _NicknameStartChoice.applyExisting,
              ),
              child: const Text('예'),
            ),
          ],
        );
      },
    );
  }

  Future<void> submit() async {
    if (_submitting) return;
    final messenger = ScaffoldMessenger.of(context);
    final appState = context.read<AppState>();
    final nickname = nicknameController.text.trim();

    if (appState.containsReservedNicknameTerm(nickname)) {
      await _showNicknameBlockedDialog('해당 닉네임을 사용할 수 없습니다.');
      return;
    }

    if (!appState.isValidNickname(nickname)) {
      await _showNicknameBlockedDialog(
        '닉네임은 1~20자의 한글, 영문, 숫자, 밑줄(_)만 사용할 수 있어요.',
      );
      return;
    }

    var discardExistingData = false;
    final existing = appState.configuredNickname;
    if ((existing == null || existing.isEmpty) &&
        appState.hasReusableDeviceData) {
      final choice = await _askHowToUseExistingData();
      if (!mounted || choice == null) return;
      discardExistingData = choice == _NicknameStartChoice.freshStart;
    }

    setState(() => _submitting = true);
    final success = await appState.claimDeviceNickname(
      nickname,
      discardExistingData: discardExistingData,
    );
    if (!mounted) return;
    setState(() => _submitting = false);

    if (!success) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('이미 사용 중인 닉네임이거나 서버 연결이 불안정해요.'),
        ),
      );
      return;
    }

    Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    final appState = context.watch<AppState>();
    final existing = appState.configuredNickname;

    return Scaffold(
      appBar: AppBar(
        title: Text(existing == null ? '닉네임 설정' : '닉네임 변경'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    existing == null
                        ? '처음 사용할 닉네임을 정해 주세요.'
                        : '다른 기기와 겹치지 않는 새 닉네임으로 언제든지 바꿀 수 있어요.',
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 14),
                  PlatformNicknameInput(
                    controller: nicknameController,
                    enabled: !_submitting,
                    onSubmitted: (_) => submit(),
                  ),
                  const SizedBox(height: 14),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: palette.softSurface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: theme.colorScheme.outline),
                    ),
                    child: const Text(
                      '닉네임은 게시물과 댓글 작성 이름으로 사용돼요. 같은 닉네임이 이미 서버에 있으면 사용할 수 없어요.',
                      style: TextStyle(height: 1.45),
                    ),
                  ),
                  const SizedBox(height: 18),
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: FilledButton(
                      onPressed: _submitting ? null : submit,
                      child: _submitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : Text(existing == null ? '설정하기' : '닉네임 변경'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
