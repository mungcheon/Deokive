import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/deokive_palette.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  final idController = TextEditingController();
  final passwordController = TextEditingController();
  final nicknameController = TextEditingController();
  final confirmPasswordController = TextEditingController();

  bool get signupMode => _tabController.index == 1;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (mounted) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    idController.dispose();
    passwordController.dispose();
    nicknameController.dispose();
    confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> openForgotPasswordDialog() async {
    final resetController = TextEditingController(text: idController.text);

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('비밀번호 찾기'),
          content: TextField(
            controller: resetController,
            decoration: const InputDecoration(
              labelText: '가입한 아이디',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                final id = resetController.text.trim();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      id.isEmpty
                          ? '아이디를 입력해주세요.'
                          : '$id 계정의 비밀번호 찾기 기능은 추후 연결됩니다.',
                    ),
                  ),
                );
              },
              child: const Text('확인'),
            ),
          ],
        );
      },
    );
  }

  Future<void> submit() async {
    final appState = context.read<AppState>();
    final id = idController.text.trim();
    final password = passwordController.text;

    if (id.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('아이디와 비밀번호를 입력해주세요.')),
      );
      return;
    }

    if (!appState.isValidTagText(id)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('아이디는 영문과 숫자만 사용할 수 있습니다.')),
      );
      return;
    }

    if (signupMode) {
      final nickname = nicknameController.text.trim();
      final confirmPassword = confirmPasswordController.text;

      if (nickname.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('닉네임을 입력해주세요.')),
        );
        return;
      }

      if (password != confirmPassword) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('비밀번호 확인이 일치하지 않습니다.')),
        );
        return;
      }

      final success = await appState.signUpLocal(
        nickname: nickname,
        id: id,
        password: password,
      );
      if (!success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('이미 사용 중인 아이디입니다.')),
        );
        return;
      }

      if (!mounted) return;
      Navigator.pop(context, true);
      return;
    }

    final success = await appState.signInLocal(id: id, password: password);
    if (!success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('등록된 계정 정보와 일치하지 않습니다.')),
      );
      return;
    }

    if (!mounted) return;
    Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('로그인'),
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
                  Container(
                    decoration: BoxDecoration(
                      color: palette.softSurface,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: TabBar(
                      controller: _tabController,
                      indicator: BoxDecoration(
                        color: palette.primary,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      indicatorSize: TabBarIndicatorSize.tab,
                      labelColor: palette.text,
                      unselectedLabelColor:
                          theme.colorScheme.onSurface.withValues(alpha: 0.75),
                      dividerColor: Colors.transparent,
                      tabs: const [
                        Tab(text: '로그인'),
                        Tab(text: '회원가입'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (signupMode) ...[
                    TextField(
                      controller: nicknameController,
                      decoration: const InputDecoration(
                        labelText: '닉네임',
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  TextField(
                    controller: idController,
                    decoration: const InputDecoration(
                      labelText: '아이디',
                      helperText: '아이디는 영문과 숫자만 사용할 수 있습니다.',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: passwordController,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: '비밀번호',
                    ),
                  ),
                  if (!signupMode)
                    CheckboxListTile(
                      value: appState.keepSignedIn,
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                      title: const Text('로그인 유지'),
                      onChanged: (value) {
                        if (value == null) return;
                        appState.setKeepSignedIn(value);
                      },
                    ),
                  if (signupMode) ...[
                    const SizedBox(height: 12),
                    TextField(
                      controller: confirmPasswordController,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: '비밀번호 확인',
                      ),
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
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '첫 태그는 ${appState.nextDefaultTag} 로 생성됩니다.',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            '회원가입 순서대로 @deokive 뒤에 번호가 붙고, 이후 설정에서 원하는 태그로 바꿀 수 있습니다. 태그는 영문과 숫자만 사용할 수 있습니다.',
                            style: TextStyle(height: 1.45),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            '일반 회원가입 정보는 로컬 DB에 저장됩니다. 일반 계정은 주기적인 클라우드 백업이 제한될 수 있으며 Google Drive 백업은 구글 로그인 계정에서 사용될 예정입니다.',
                            style: TextStyle(height: 1.45),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 18),
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: FilledButton(
                      onPressed: submit,
                      child: Text(signupMode ? '회원가입 완료' : '로그인'),
                    ),
                  ),
                  if (!signupMode) ...[
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: openForgotPasswordDialog,
                        child: const Text('비밀번호 찾기'),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
