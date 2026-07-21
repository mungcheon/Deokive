import 'package:flutter/material.dart';

class PlatformNicknameInput extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String>? onSubmitted;
  final bool enabled;

  const PlatformNicknameInput({
    super.key,
    required this.controller,
    this.onSubmitted,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      enabled: enabled,
      maxLength: 20,
      textInputAction: TextInputAction.done,
      onSubmitted: onSubmitted,
      decoration: const InputDecoration(
        labelText: '닉네임',
        helperText: '한글, 영문, 숫자, 밑줄(_) 사용 가능',
        counterText: '',
        prefixIcon: Icon(Icons.badge_outlined),
      ),
    );
  }
}
