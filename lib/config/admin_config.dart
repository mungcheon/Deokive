import 'dart:convert';

import 'package:crypto/crypto.dart' show sha256;

/// Admin-mode gate.
///
/// Admin mode unlocks notice/info posting, info-bot approval, and post
/// edit/delete — so it must NOT be a free toggle. Enabling it requires the
/// admin passcode, verified against a SHA-256 hash (the plaintext passcode
/// is never stored in the app or the source).
///
/// Set your own passcode at build time:
///   flutter run --dart-define=DEOKIVE_ADMIN_PASSCODE=your-secret
/// then compute its hash once and paste it into [_passcodeHash] below
/// (so release builds don't carry the plaintext). The dart-define path is a
/// convenience for development.
class AdminConfig {
  AdminConfig._();

  /// SHA-256 of the admin passcode. Public builds keep this disabled.
  /// Provide a build-time override for private/admin builds.
  static const String _passcodeHash =
      '0000000000000000000000000000000000000000000000000000000000000000';

  /// Optional build-time override. If provided, its hash is checked too, so
  /// you can rotate the passcode without editing the source.
  static const String _envPasscode =
      String.fromEnvironment('DEOKIVE_ADMIN_PASSCODE');

  static String _hash(String input) =>
      sha256.convert(utf8.encode(input.trim())).toString();

  /// True when [input] matches either the compiled hash or the build-time
  /// passcode override.
  static bool verify(String input) {
    if (input.trim().isEmpty) return false;
    final h = _hash(input);
    if (h == _passcodeHash) return true;
    if (_envPasscode.isNotEmpty && input.trim() == _envPasscode.trim()) {
      return true;
    }
    return false;
  }
}
