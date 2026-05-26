/// Default goods category presets shown in the autocomplete dropdown.
/// Free text input is also allowed — users can type any value and it will be
/// stored exactly as written. Two entries that differ even by whitespace are
/// treated as separate categories at sort/group time, by design.
class GoodsCategoryCatalog {
  const GoodsCategoryCatalog._();

  /// Stable lookup keys; rendered labels come from `app_*.arb`
  /// via `AppLocalizations.categoryXxx`.
  static const List<String> defaultKeys = [
    'figure',
    'plush',
    'poster',
    'card',
    'badge',
    'keyring',
    'sticker',
    'standee',
    'photoCard',
    'artBook',
    'clothing',
    'accessory',
    'other',
  ];
}
