import 'package:flutter/material.dart';

import '../state/app_state.dart';

/// Tappable currency code prefix shown inside a price `TextFormField`.
/// Tapping opens a `PopupMenu` with the supported currencies so users can
/// freely switch between KRW / USD / JPY / EUR / CNY for the goods being
/// entered.
class CurrencyPrefix extends StatelessWidget {
  final Currency currency;
  final ValueChanged<Currency> onSelected;

  const CurrencyPrefix({
    super.key,
    required this.currency,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return PopupMenuButton<Currency>(
      tooltip: '통화 변경',
      initialValue: currency,
      onSelected: onSelected,
      itemBuilder: (context) => Currency.values
          .map(
            (c) => PopupMenuItem<Currency>(
              value: c,
              child: Text('${c.symbol}  ${c.code}'),
            ),
          )
          .toList(),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              currency.code,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(width: 2),
            Icon(
              Icons.arrow_drop_down_rounded,
              size: 18,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ],
        ),
      ),
    );
  }
}
