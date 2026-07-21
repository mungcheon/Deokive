import 'package:flutter/material.dart';

class CuteSectionHeader extends StatelessWidget {
  const CuteSectionHeader({
    super.key,
    required this.title,
    this.actionLabel,
    this.onTap,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
          ),
        ),
        const Spacer(),
        if (actionLabel != null)
          TextButton(
            onPressed: onTap,
            child: Text(actionLabel!),
          ),
      ],
    );
  }
}
