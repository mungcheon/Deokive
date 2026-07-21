import 'dart:convert';

import 'package:http/http.dart' as http;

/// Result of a single Claude API call that produces a cleaned + summarized
/// + translated version of a board post in the target language.
class ProcessedPostFields {
  final String title;
  final String summary;
  final String content;
  final String? detectedSourceLanguage;
  final int cacheReadTokens;
  final int cacheCreationTokens;

  const ProcessedPostFields({
    required this.title,
    required this.summary,
    required this.content,
    this.detectedSourceLanguage,
    this.cacheReadTokens = 0,
    this.cacheCreationTokens = 0,
  });
}

class TranslationException implements Exception {
  final String message;
  const TranslationException(this.message);
  @override
  String toString() => 'TranslationException: $message';
}

/// Calls Claude API to clean up + summarize + translate fandom-goods info
/// posts pulled from official X/Twitter feeds.
///
/// Single endpoint: POST /v1/messages (Anthropic Messages API).
/// Model: claude-haiku-4-5 (fast + cheap, plenty for translation).
/// Output: enforced JSON via `output_config.format` json_schema.
/// Caching: large stable system prompt is marked `cache_control: ephemeral`
/// so repeated calls pay ~0.1× input tokens after the first.
class ClaudeTranslationService {
  static const _endpoint = 'https://api.anthropic.com/v1/messages';
  static const _model = 'claude-haiku-4-5';
  static const _apiVersion = '2023-06-01';

  final String apiKey;
  final http.Client _http;

  ClaudeTranslationService({required this.apiKey, http.Client? client})
      : _http = client ?? http.Client();

  void dispose() => _http.close();

  /// Process a raw or partially-cleaned board post for [targetLanguageCode]
  /// (one of `ko`, `en`, `ja`, `zh_Hans`, `zh_Hant`).
  Future<ProcessedPostFields> process({
    required String rawTitle,
    required String rawSummary,
    required String rawContent,
    required String targetLanguageCode,
    String? sourceHint,
  }) async {
    if (apiKey.isEmpty) {
      throw const TranslationException('Claude API key가 설정되지 않았어요.');
    }

    final targetLabel = _languageLabel(targetLanguageCode);
    final userPrompt = _buildUserPrompt(
      title: rawTitle,
      summary: rawSummary,
      content: rawContent,
      targetLanguageLabel: targetLabel,
      sourceHint: sourceHint,
    );

    final resp = await _http
        .post(
          Uri.parse(_endpoint),
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': apiKey,
            'anthropic-version': _apiVersion,
          },
          body: jsonEncode({
            'model': _model,
            'max_tokens': 2048,
            'system': [
              {
                'type': 'text',
                'text': _systemPrompt,
                // Large stable prefix → cache it. Volatile per-post content
                // sits later in the request and doesn't bust the cache.
                'cache_control': {'type': 'ephemeral'},
              },
            ],
            'output_config': {
              'format': {
                'type': 'json_schema',
                'schema': {
                  'type': 'object',
                  'properties': {
                    'detected_source_language': {
                      'type': 'string',
                      'description': 'BCP-47 ish code of the source language',
                    },
                    'title': {'type': 'string'},
                    'summary': {'type': 'string'},
                    'content': {'type': 'string'},
                  },
                  'required': ['title', 'summary', 'content'],
                  'additionalProperties': false,
                },
              },
            },
            'messages': [
              {'role': 'user', 'content': userPrompt},
            ],
          }),
        )
        .timeout(const Duration(seconds: 30));

    if (resp.statusCode != 200) {
      throw TranslationException(
        'Claude API error ${resp.statusCode}: ${_truncate(resp.body, 200)}',
      );
    }

    final body = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    final contentBlocks = (body['content'] as List<dynamic>?) ?? const [];
    String? text;
    for (final raw in contentBlocks) {
      final block = raw as Map<String, dynamic>;
      if (block['type'] == 'text') {
        text = block['text'] as String?;
        break;
      }
    }
    if (text == null || text.isEmpty) {
      throw const TranslationException('빈 응답을 받았어요.');
    }

    final Map<String, dynamic> parsed;
    try {
      parsed = jsonDecode(text) as Map<String, dynamic>;
    } catch (e) {
      throw TranslationException('응답 JSON 파싱 실패: $e');
    }

    final usage = body['usage'] as Map<String, dynamic>?;
    return ProcessedPostFields(
      title: (parsed['title'] as String?)?.trim() ?? rawTitle,
      summary: (parsed['summary'] as String?)?.trim() ?? rawSummary,
      content: (parsed['content'] as String?)?.trim() ?? rawContent,
      detectedSourceLanguage:
          (parsed['detected_source_language'] as String?)?.trim(),
      cacheReadTokens: (usage?['cache_read_input_tokens'] as int?) ?? 0,
      cacheCreationTokens: (usage?['cache_creation_input_tokens'] as int?) ?? 0,
    );
  }

  /// One-shot connectivity test — minimal call that returns quickly. Used by
  /// the settings screen to verify the API key works.
  Future<bool> testConnection() async {
    try {
      final resp = await _http
          .post(
            Uri.parse(_endpoint),
            headers: {
              'Content-Type': 'application/json',
              'x-api-key': apiKey,
              'anthropic-version': _apiVersion,
            },
            body: jsonEncode({
              'model': _model,
              'max_tokens': 16,
              'messages': [
                {'role': 'user', 'content': 'ping'},
              ],
            }),
          )
          .timeout(const Duration(seconds: 15));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  String _buildUserPrompt({
    required String title,
    required String summary,
    required String content,
    required String targetLanguageLabel,
    String? sourceHint,
  }) {
    final src = sourceHint == null ? '(auto-detect)' : sourceHint;
    return '''
Target language: $targetLanguageLabel
Source language hint: $src

Process this fandom-goods post. Detect source language, write a real summary (1-2 sentences in the target language), clean the title, and produce the full content body in the target language. Return only JSON with keys: detected_source_language, title, summary, content.

ORIGINAL_TITLE:
$title

ORIGINAL_RAW_SUMMARY:
$summary

ORIGINAL_CONTENT:
$content
''';
  }

  String _languageLabel(String code) {
    switch (code) {
      case 'ko':
        return '한국어 (Korean)';
      case 'en':
        return 'English';
      case 'ja':
        return '日本語 (Japanese)';
      case 'zh_Hans':
      case 'zh-Hans':
      case 'zh':
        return '简体中文 (Simplified Chinese)';
      case 'zh_Hant':
      case 'zh-Hant':
        return '繁體中文 (Traditional Chinese)';
      default:
        return code;
    }
  }

  static String _truncate(String s, int max) =>
      s.length <= max ? s : '${s.substring(0, max)}…';

  // ── System prompt (stable; cached on the API side) ─────────────────────
  // Large enough + invariant across calls = high cache hit rate after the
  // first request in a 5-min window.
  static const String _systemPrompt = r'''
You are a localization editor for **Deokive**, a Korean fandom-goods (굿즈)
collection app. You receive raw posts pulled from official X / Twitter feeds
of merchandise brands (Chiikawa Market, Bandai Namco, Ichiban Kuji,
Goodsmile, Pokémon Center, etc.) and turn them into clean, natural-reading
posts in a target language.

# Your job, in order:

1. **Detect** the source language of the input (Japanese, Korean, English,
   Chinese, etc.). Put it in `detected_source_language`.

2. **Title** — Produce a single-line title in the target language:
   - Strip RT prefixes, leading hashtags, dangling URLs, "[속보]"-style
     prefixes if they're just noise.
   - Keep product / character / brand proper nouns intact when they are
     specific (e.g. "치이카와", "하치와레", "Hello Kitty", "넨도로이드",
     "한큐 전철"). Localize generic words around them.
   - Max ~50 characters in the target language.

3. **Summary** — Write a FRESH 1–2 sentence summary of the post in the
   target language. This is the most important field. Rules:
   - It must be a *real summary*, not a truncation of the title.
   - Mention: what product, who it features, price/release window if given.
   - 50–120 characters in the target language. Do not exceed 140.
   - No bullet points, no markdown, no emoji unless they're in the
     original brand name.

4. **Content** — Render the post body in the target language. Rules:
   - Preserve structure: bullet lists stay as lists, line breaks preserved.
   - Translate naturally, not literally. Use community vocabulary, not
     dictionary-direct equivalents.
   - Keep product SKU codes, prices with currency symbols, dates, URLs,
     and @handles intact.
   - Convert relative dates ("来週", "next week") to absolute when the
     post gives enough context; leave alone otherwise.
   - If the input is ALREADY in the target language: still apply the
     cleanup (remove RT junk, normalize spacing, fix obvious typos), but
     do not paraphrase needlessly.

# Tone

- Conversational, collector-to-collector — NOT corporate or machine-stiff.
- Korean: 굿즈 커뮤니티 톤 (~예요/요체, NOT ~합니다체). Use 굿즈, 마스코트,
  봉제 인형, 발매, 재입고, 한정, 예약, 신상.
- English: collector community voice. Use "goods", "merch", "plush",
  "release", "restock", "limited edition", "preorder", "drop".
- Japanese: 「グッズ」「マスコット」「ぬいぐるみ」「発売」「再入荷」
  「限定」「予約」「新作」。です/ます調.
- Chinese (Simp/Trad): 「周边」/「周邊」, 「公仔」, 「玩偶」/「玩偶」,
  「发售」/「發售」, 「补货」/「補貨」, 「限定」, 「预购」/「預購」.

# Don'ts

- Do NOT invent facts not present in the source. If the price is missing,
  don't make one up.
- Do NOT add disclaimers, hedging ("It seems that…"), or meta commentary.
- Do NOT prefix the title with "[정보]", "[공지]" etc. — the app already
  shows a tag chip.
- Do NOT include URLs in the title or summary unless the URL IS the post.
- Do NOT mention that you are an AI or that this is a translation.

# Output

Return ONLY valid JSON matching the provided schema. No markdown, no
preamble, no trailing commentary.
''';
}
