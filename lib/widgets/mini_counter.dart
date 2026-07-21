import 'package:flutter/material.dart';

class MiniCounter extends StatelessWidget {
  const MiniCounter({
    super.key,
    required this.value,
    required this.onMinus,
    required this.onPlus,
  });

  final int value;
  final VoidCallback? onMinus;
  final VoidCallback onPlus;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Text(
          '개수',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        ),
        const SizedBox(width: 12),
        _CounterButton(icon: Icons.remove, onTap: onMinus),
        SizedBox(
          width: 30,
          child: Center(
            child: Text(
              '$value',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ),
        _CounterButton(icon: Icons.add, onTap: onPlus),
      ],
    );
  }
}

class _CounterButton extends StatelessWidget {
  const _CounterButton({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 26,
      height: 26,
      child: FilledButton.tonal(
        onPressed: onTap,
        style: FilledButton.styleFrom(
          padding: EdgeInsets.zero,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        child: Icon(icon, size: 14),
      ),
    );
  }
}
