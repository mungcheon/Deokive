import 'package:flutter/material.dart';

import '../theme/deokive_palette.dart';

class DeokiveHeaderTitle extends StatefulWidget {
  const DeokiveHeaderTitle({super.key});

  @override
  State<DeokiveHeaderTitle> createState() => _DeokiveHeaderTitleState();
}

class _DeokiveHeaderTitleState extends State<DeokiveHeaderTitle> {
  bool _expanded = false;

  Future<void> _animateOnce() async {
    if (_expanded) return;
    setState(() {
      _expanded = true;
    });
    await Future<void>.delayed(const Duration(milliseconds: 140));
    if (!mounted) return;
    setState(() {
      _expanded = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final palette = Theme.of(context).extension<DeokivePalette>();

    return GestureDetector(
      onTap: _animateOnce,
      child: AnimatedScale(
        scale: _expanded ? 1.08 : 1,
        duration: const Duration(milliseconds: 140),
        curve: Curves.easeOut,
        child: Image.asset(
          'lib/logo.png',
          height: 28,
          fit: BoxFit.contain,
          color: palette?.primary,
          colorBlendMode: BlendMode.srcIn,
        ),
      ),
    );
  }
}
