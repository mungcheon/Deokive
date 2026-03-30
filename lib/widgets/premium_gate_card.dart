import 'package:flutter/material.dart';

import '../config/monetization_catalog.dart';
import '../theme/deokive_palette.dart';

class PremiumGateCard extends StatelessWidget {
  final PremiumFeature feature;
  final bool unlocked;
  final String? trailingLabel;
  final VoidCallback? onTap;

  const PremiumGateCard({
    super.key,
    required this.feature,
    required this.unlocked,
    this.trailingLabel,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    final spec = MonetizationCatalog.featureOf(feature);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(22),
      child: Ink(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: unlocked ? theme.colorScheme.surface : palette.softSurface,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: unlocked ? palette.primary : theme.colorScheme.outline,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: unlocked
                    ? palette.primary.withValues(alpha: 0.16)
                    : palette.accent.withValues(alpha: 0.24),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(
                unlocked ? Icons.check_circle_outline : Icons.lock_outline,
                color: theme.colorScheme.onSurface,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    spec.label,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    spec.description,
                    style: theme.textTheme.bodyMedium?.copyWith(height: 1.4),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  unlocked ? '사용 중' : '잠금',
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: unlocked ? palette.primary : null,
                  ),
                ),
                if ((trailingLabel ?? '').isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    trailingLabel!,
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
