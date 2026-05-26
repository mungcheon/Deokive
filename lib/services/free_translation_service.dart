import 'dart:convert';

import 'package:http/http.dart' as http;

import 'claude_translation_service.dart' show ProcessedPostFields, TranslationException;

/// Free translation provider — uses the unofficial Google Translate web
/// endpoint that powers the Chrome built-in translator.
///
/// - No API key, no signup, no quota tracking.
/// - Rate-limited by IP (Google may throttle aggressive usage).
/// - Translation is more literal than an LLM-based service. Quality is
///   usually acceptable for short news/info posts.
/// - Not officially supported by Google — the endpoint shape could change.
///   On failure the caller falls back to the original text.
///
/// Drop-in replacement for `ClaudeTranslationService.process()` — returns
/// the same `ProcessedPostFields` shape so callers don't need to branch.
class FreeTranslationService {
  static const _endpoint =
      'https://translate.googleapis.com/translate_a/single';
  // Sentinel that we use to batch title + summary + content into one round
  // trip. Chosen to be: (a) ASCII-only so it survives any source script,
  // (b) unlikely to appear in real posts, (c) preserved by Google's
  // translator because it's not a translatable token.
  static const _separator = '\n@@DEOKIVE_FIELD@@\n';
  static const _emptyMarker = '__DEOKIVE_EMPTY__';

  final http.Client _http;

  FreeTranslationService({http.Client? client})
      : _http = client ?? http.Client();

  void dispose() => _http.close();

  Future<ProcessedPostFields> process({
    required String rawTitle,
    required String rawSummary,
    required String rawContent,
    required String targetLanguageCode,
    String? sourceHint,
  }) async {
    final tl = _mapLangCode(targetLanguageCode);
    final sl = sourceHint == null ? 'auto' : _mapLangCode(sourceHint);

    // Empty fields use a sentinel so the split lines up after translation —
    // translating an empty string back is unreliable.
    final combined = [
      rawTitle.isEmpty ? _emptyMarker : rawTitle,
      rawSummary.isEmpty ? _emptyMarker : rawSummary,
      rawContent.isEmpty ? _emptyMarker : rawContent,
    ].join(_separator);

    String translated;
    try {
      translated = await _translateText(combined, sl: sl, tl: tl);
    } catch (e) {
      // Some posts are too long for one request (~5000 char cap). Fall back
      // to translating each field separately.
      return _processSeparate(
        rawTitle: rawTitle,
        rawSummary: rawSummary,
        rawContent: rawContent,
        sl: sl,
        tl: tl,
      );
    }

    final parts = translated.split(_separator);
    if (parts.length < 3) {
      // Google may have collapsed the separator on some scripts; retry per
      // field rather than guessing.
      return _processSeparate(
        rawTitle: rawTitle,
        rawSummary: rawSummary,
        rawContent: rawContent,
        sl: sl,
        tl: tl,
      );
    }

    String clean(String s) {
      final t = s.trim();
      return t == _emptyMarker ? '' : t;
    }

    return ProcessedPostFields(
      title: clean(parts[0]).isEmpty ? rawTitle : clean(parts[0]),
      summary: clean(parts[1]),
      content: clean(parts[2]).isEmpty ? rawContent : clean(parts[2]),
    );
  }

  Future<ProcessedPostFields> _processSeparate({
    required String rawTitle,
    required String rawSummary,
    required String rawContent,
    required String sl,
    required String tl,
  }) async {
    Future<String> tx(String text) async {
      if (text.isEmpty) return '';
      try {
        return await _translateText(text, sl: sl, tl: tl);
      } catch (_) {
        return text; // graceful fallback per field
      }
    }

    return ProcessedPostFields(
      title: (await tx(rawTitle)).trim(),
      summary: (await tx(rawSummary)).trim(),
      content: (await tx(rawContent)).trim(),
    );
  }

  Future<String> _translateText(
    String text, {
    required String sl,
    required String tl,
  }) async {
    if (text.trim().isEmpty) return text;
    final uri = Uri.parse(_endpoint).replace(queryParameters: {
      'client': 'gtx',
      'sl': sl,
      'tl': tl,
      'dt': 't',
      'q': text,
    });
    final resp =
        await _http.get(uri).timeout(const Duration(seconds: 20));
    if (resp.statusCode != 200) {
      throw TranslationException(
        '번역 서버 응답 ${resp.statusCode}',
      );
    }
    final body = utf8.decode(resp.bodyBytes);
    final data = jsonDecode(body);
    // Response shape: [[[translated, source, null, null, conf], …], …]
    if (data is! List || data.isEmpty || data[0] is! List) {
      throw const TranslationException('번역 응답을 해석할 수 없어요.');
    }
    final segments = data[0] as List;
    final buf = StringBuffer();
    for (final seg in segments) {
      if (seg is List && seg.isNotEmpty && seg[0] is String) {
        buf.write(seg[0] as String);
      }
    }
    return buf.toString();
  }

  /// One-shot connectivity test — used by settings UI to verify the free
  /// translation endpoint is reachable from this device/network.
  Future<bool> testConnection() async {
    try {
      final result = await _translateText('hello', sl: 'en', tl: 'ko');
      return result.isNotEmpty;
    } catch (_) {
      return false;
    }
  }

  /// Map app language codes (`ko`, `zh_Hans`, …) to Google's codes
  /// (`ko`, `zh-CN`, …).
  String _mapLangCode(String code) {
    switch (code) {
      case 'ko':
        return 'ko';
      case 'en':
        return 'en';
      case 'ja':
        return 'ja';
      case 'zh':
      case 'zh_Hans':
      case 'zh-Hans':
        return 'zh-CN';
      case 'zh_Hant':
      case 'zh-Hant':
        return 'zh-TW';
      default:
        return code;
    }
  }
}
