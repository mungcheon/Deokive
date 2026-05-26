import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../l10n/generated/app_localizations.dart';
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

  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  bool _submitting = false;

  bool get signupMode => _tabController.index == 1;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (mounted) setState(() {});
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
    final l = AppLocalizations.of(context);
    final resetController = TextEditingController(text: idController.text);

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(l.authForgotPassword),
          content: TextField(
            controller: resetController,
            decoration: InputDecoration(
              labelText: l.authForgotPasswordEnterId,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: Text(l.cancel),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                final id = resetController.text.trim();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      id.isEmpty
                          ? l.authMsgIdEmptyOnReset
                          : l.authMsgResetSent(id),
                    ),
                  ),
                );
              },
              child: Text(l.save),
            ),
          ],
        );
      },
    );
  }

  Future<void> submit() async {
    if (_submitting) return;
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final appState = context.read<AppState>();
    final id = idController.text.trim();
    final password = passwordController.text;

    if (id.isEmpty || password.isEmpty) {
      messenger.showSnackBar(
        SnackBar(content: Text(l.authMsgIdPasswordRequired)),
      );
      return;
    }

    if (!appState.isValidTagText(id)) {
      messenger.showSnackBar(
        SnackBar(content: Text(l.authMsgIdInvalidChars)),
      );
      return;
    }

    if (signupMode) {
      final nickname = nicknameController.text.trim();
      final confirmPassword = confirmPasswordController.text;

      if (nickname.isEmpty) {
        messenger.showSnackBar(
          SnackBar(content: Text(l.authMsgNicknameRequired)),
        );
        return;
      }

      // Standard minimum password length.
      if (password.length < 6) {
        messenger.showSnackBar(
          SnackBar(content: Text(l.authMsgPasswordTooShort)),
        );
        return;
      }

      if (password != confirmPassword) {
        messenger.showSnackBar(
          SnackBar(content: Text(l.authMsgPasswordMismatch)),
        );
        return;
      }

      setState(() => _submitting = true);
      final success = await appState.signUpLocal(
        nickname: nickname,
        id: id,
        password: password,
      );
      if (!mounted) return;
      setState(() => _submitting = false);
      if (!success) {
        messenger.showSnackBar(
          SnackBar(content: Text(l.authMsgIdTaken)),
        );
        return;
      }

      Navigator.pop(context, true);
      return;
    }

    setState(() => _submitting = true);
    final success = await appState.signInLocal(id: id, password: password);
    if (!mounted) return;
    setState(() => _submitting = false);
    if (!success) {
      messenger.showSnackBar(
        SnackBar(content: Text(l.authMsgLoginFailed)),
      );
      return;
    }

    Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final appState = context.watch<AppState>();
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    return Scaffold(
      appBar: AppBar(title: Text(l.login)),
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
                      tabs: [
                        Tab(text: l.authLoginTab),
                        Tab(text: l.authSignupTab),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (signupMode) ...[
                    TextField(
                      controller: nicknameController,
                      maxLength: 15,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [AutofillHints.nickname],
                      decoration: InputDecoration(
                        labelText: l.authNicknameLabel,
                        counterText: '',
                        prefixIcon: const Icon(Icons.badge_outlined),
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  TextField(
                    controller: idController,
                    textInputAction: TextInputAction.next,
                    keyboardType: TextInputType.visiblePassword,
                    autocorrect: false,
                    enableSuggestions: false,
                    autofillHints: const [AutofillHints.username],
                    decoration: InputDecoration(
                      labelText: l.accountId,
                      helperText: l.accountIdHelp,
                      prefixIcon: const Icon(Icons.alternate_email_rounded),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: passwordController,
                    obscureText: _obscurePassword,
                    textInputAction:
                        signupMode ? TextInputAction.next : TextInputAction.done,
                    autofillHints: const [AutofillHints.password],
                    onSubmitted: (_) {
                      if (!signupMode) submit();
                    },
                    decoration: InputDecoration(
                      labelText: l.authPasswordLabel,
                      prefixIcon: const Icon(Icons.lock_outline_rounded),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                        ),
                        onPressed: () => setState(
                            () => _obscurePassword = !_obscurePassword),
                      ),
                    ),
                  ),
                  if (!signupMode)
                    CheckboxListTile(
                      value: appState.keepSignedIn,
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                      title: Text(l.authKeepSignedIn),
                      onChanged: (value) {
                        if (value == null) return;
                        appState.setKeepSignedIn(value);
                      },
                    ),
                  if (signupMode) ...[
                    const SizedBox(height: 12),
                    TextField(
                      controller: confirmPasswordController,
                      obscureText: _obscureConfirm,
                      textInputAction: TextInputAction.done,
                      autofillHints: const [AutofillHints.password],
                      onSubmitted: (_) => submit(),
                      decoration: InputDecoration(
                        labelText: l.authPasswordConfirmLabel,
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureConfirm
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                          ),
                          onPressed: () => setState(
                              () => _obscureConfirm = !_obscureConfirm),
                        ),
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
                            l.authSignupNoticeTagPrefix(appState.nextDefaultTag),
                            style: theme.textTheme.bodyMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            l.authSignupNoticeTagBody,
                            style: const TextStyle(height: 1.45),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            l.authSignupNoticeBackup,
                            style: const TextStyle(height: 1.45),
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
                          : Text(
                              signupMode ? l.authCompleteSignup : l.login,
                            ),
                    ),
                  ),
                  if (!signupMode) ...[
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: openForgotPasswordDialog,
                        child: Text(l.authForgotPassword),
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
