import 'dart:async';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

class PlatformNicknameInput extends StatefulWidget {
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
  State<PlatformNicknameInput> createState() => _PlatformNicknameInputState();
}

class _PlatformNicknameInputState extends State<PlatformNicknameInput> {
  late final String _viewType;
  late final html.InputElement _input;
  StreamSubscription<html.Event>? _inputSub;
  StreamSubscription<html.KeyboardEvent>? _keySub;

  bool get _useStandaloneHtmlInput {
    return html.window.matchMedia('(display-mode: standalone)').matches;
  }

  @override
  void initState() {
    super.initState();
    _viewType = 'nickname-input-${DateTime.now().microsecondsSinceEpoch}';
    _input = html.InputElement()
      ..value = widget.controller.text
      ..maxLength = 20
      ..autocomplete = 'off'
      ..spellcheck = false
      ..disabled = !widget.enabled
      ..placeholder = '닉네임'
      ..style.display = 'block'
      ..style.width = '100%'
      ..style.height = '100%'
      ..style.margin = '0'
      ..style.padding = '0 16px 0 44px'
      ..style.boxSizing = 'border-box'
      ..style.fontSize = '16px'
      ..style.lineHeight = '24px'
      ..style.border = '1px solid #e4b8c7'
      ..style.borderRadius = '16px'
      ..style.outline = 'none'
      ..style.backgroundColor = '#ffffff'
      ..style.color = '#5b4752';

    _inputSub = _input.onInput.listen((_) {
      final value = _input.value ?? '';
      if (widget.controller.text == value) return;
      widget.controller.value = TextEditingValue(
        text: value,
        selection: TextSelection.collapsed(offset: value.length),
      );
    });
    _keySub = _input.onKeyDown.listen((event) {
      if (event.key == 'Enter') {
        widget.onSubmitted?.call(_input.value ?? '');
      }
    });
    widget.controller.addListener(_syncFromController);

    ui_web.platformViewRegistry.registerViewFactory(
      _viewType,
      (int _) => _input,
    );
  }

  @override
  void didUpdateWidget(covariant PlatformNicknameInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    _input.disabled = !widget.enabled;
    _syncFromController();
  }

  void _syncFromController() {
    final text = widget.controller.text;
    if (_input.value == text) return;
    _input.value = text;
  }

  @override
  void dispose() {
    widget.controller.removeListener(_syncFromController);
    _inputSub?.cancel();
    _keySub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_useStandaloneHtmlInput) {
      return TextField(
        controller: widget.controller,
        enabled: widget.enabled,
        maxLength: 20,
        textInputAction: TextInputAction.done,
        onSubmitted: widget.onSubmitted,
        decoration: const InputDecoration(
          labelText: '닉네임',
          helperText: '한글, 영문, 숫자, 밑줄(_) 사용 가능',
          counterText: '',
          prefixIcon: Icon(Icons.badge_outlined),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '닉네임',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 56,
          child: Stack(
            children: [
              Positioned.fill(
                child: HtmlElementView(viewType: _viewType),
              ),
              const Positioned(
                left: 14,
                top: 18,
                child: IgnorePointer(
                  child: Icon(Icons.badge_outlined, size: 20),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 6),
        Text(
          '한글, 영문, 숫자, 밑줄(_) 사용 가능',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}
