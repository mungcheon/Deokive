import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../data/board_posts.dart';

/// Fetches the latest posts from each [InfoBot] and converts them into
/// [BoardPost] drafts ready to be inserted into the board.
///
/// X (Twitter) doesn't offer a free public API, so we fetch from Nitter RSS
/// mirrors instead. Mirrors are unstable — when a feed is down the result is
/// simply an empty list (the call site logs and moves on). Admin can override
/// any bot's [InfoBot.defaultFeedUrl] via [feedOverrides].
class InfoBotService {
  final http.Client _http;
  static const _rssHeaders = {
    'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137.0 Safari/537.36',
    'Accept':
        'application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5',
    'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
  };

  InfoBotService({http.Client? client}) : _http = client ?? http.Client();

  /// Fetch posts for a single bot. Returns an empty list if the feed is
  /// unreachable or unparseable. Network errors are swallowed.
  Future<List<BoardPost>> fetchPostsFor(
    InfoBot bot, {
    String? overrideFeedUrl,
    int maxItems = 10,
  }) async {
    final url = overrideFeedUrl ?? bot.defaultFeedUrl;
    final List<_RssItem> items;
    try {
      final resp = await _http
          .get(Uri.parse(url), headers: _rssHeaders)
          .timeout(const Duration(seconds: 12));
      if (resp.statusCode != 200) return const [];
      items = _parseRss(resp.body);
    } catch (_) {
      return const [];
    }
    final out = <BoardPost>[];
    for (final item in items.take(maxItems)) {
      final id = 'bot_${bot.id}_${item.guidHash}';
      final summary = _stripHtml(item.description).trim();
      Uint8List? image;
      final imgUrl = item.imageUrl;
      if (imgUrl != null) {
        try {
          final imgResp = await _http
              .get(Uri.parse(imgUrl), headers: _rssHeaders)
              .timeout(const Duration(seconds: 12));
          if (imgResp.statusCode == 200 && imgResp.bodyBytes.length < 2000000) {
            image = imgResp.bodyBytes;
          }
        } catch (_) {}
      }
      out.add(BoardPost(
        id: id,
        tag: BoardPostTag.info,
        title: _truncate(_stripHtml(item.title).trim(), 60),
        summary: _truncate(summary, 120),
        content: '$summary\n\n— ${bot.label} (${bot.sourceHandle})',
        date: item.pubDate ?? DateTime.now(),
        author: bot.label,
        sourceUrl: item.link,
        imageBytes: image,
        // Info-bot posts start pending — they appear to the public only
        // after an admin approves them.
        approved: false,
      ));
    }
    return out;
  }

  /// Fetch new posts for every bot, dedup against [existingIds], return them
  /// in newest-first order.
  Future<List<BoardPost>> refreshAll({
    required Set<String> existingIds,
    Map<String, String?> feedOverrides = const {},
  }) async {
    final all = <BoardPost>[];
    for (final bot in kInfoBots) {
      final posts = await fetchPostsFor(
        bot,
        overrideFeedUrl: feedOverrides[bot.id],
      );
      for (final p in posts) {
        if (!existingIds.contains(p.id)) all.add(p);
      }
    }
    all.sort((a, b) => b.date.compareTo(a.date));
    return all;
  }

  void dispose() => _http.close();
}

// ── RSS parsing (no xml package — manual extraction) ─────────────────────

class _RssItem {
  final String title;
  final String link;
  final String description;
  final DateTime? pubDate;
  final String? imageUrl;

  _RssItem({
    required this.title,
    required this.link,
    required this.description,
    required this.pubDate,
    required this.imageUrl,
  });

  String get guidHash {
    // Stable id derived from the link.
    final hash = link.hashCode.toUnsigned(32).toRadixString(16);
    return hash;
  }
}

List<_RssItem> _parseRss(String xml) {
  final items = <_RssItem>[];
  final itemRegex = RegExp(r'<item[\s\S]*?</item>', caseSensitive: false);
  for (final m in itemRegex.allMatches(xml)) {
    final block = m.group(0)!;
    final title = _tag(block, 'title') ?? '';
    final link = _tag(block, 'link') ?? '';
    final description = _tag(block, 'description') ?? '';
    final pubRaw = _tag(block, 'pubDate');
    final pubDate = pubRaw == null ? null : _parseRfc822(pubRaw);
    // Media: prefer <media:thumbnail url="..."/> or <enclosure url="..."/>,
    // fall back to first <img src="..."> in description.
    String? imageUrl;
    final mediaThumb =
        RegExp(r'<media:thumbnail[^>]*url="([^"]+)"', caseSensitive: false)
            .firstMatch(block);
    if (mediaThumb != null) imageUrl = mediaThumb.group(1);
    imageUrl ??=
        RegExp(r'<media:content[^>]*url="([^"]+)"', caseSensitive: false)
            .firstMatch(block)
            ?.group(1);
    imageUrl ??=
        RegExp(r'<enclosure[^>]*url="([^"]+)"', caseSensitive: false)
            .firstMatch(block)
            ?.group(1);
    imageUrl ??= RegExp(r'''<img[^>]*src=["']([^"']+)["']''',
            caseSensitive: false)
        .firstMatch(description)
        ?.group(1);
    items.add(_RssItem(
      title: _unescape(title),
      link: link,
      description: _unescape(description),
      pubDate: pubDate,
      imageUrl: imageUrl,
    ));
  }
  return items;
}

String? _tag(String xml, String name) {
  final cdata = RegExp(
    '<$name>\\s*<!\\[CDATA\\[(.*?)\\]\\]>\\s*</$name>',
    caseSensitive: false,
    dotAll: true,
  ).firstMatch(xml);
  if (cdata != null) return cdata.group(1);
  final plain = RegExp(
    '<$name>(.*?)</$name>',
    caseSensitive: false,
    dotAll: true,
  ).firstMatch(xml);
  return plain?.group(1);
}

String _stripHtml(String s) {
  return s.replaceAll(RegExp(r'<[^>]+>'), '').trim();
}

String _unescape(String s) {
  return s
      .replaceAll('&amp;', '&')
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&quot;', '"')
      .replaceAll('&#39;', "'")
      .replaceAll('&apos;', "'");
}

String _truncate(String s, int max) {
  if (s.length <= max) return s;
  return '${s.substring(0, max - 1)}…';
}

DateTime? _parseRfc822(String raw) {
  // RFC822 e.g. "Mon, 24 May 2026 13:45:00 +0000". Dart can't natively parse
  // this so we do a minimal manual reformat to ISO 8601.
  try {
    final parts = raw.split(' ');
    if (parts.length < 5) return null;
    final day = parts[1].padLeft(2, '0');
    final monthName = parts[2];
    final year = parts[3];
    final time = parts[4];
    const months = {
      'Jan': '01',
      'Feb': '02',
      'Mar': '03',
      'Apr': '04',
      'May': '05',
      'Jun': '06',
      'Jul': '07',
      'Aug': '08',
      'Sep': '09',
      'Oct': '10',
      'Nov': '11',
      'Dec': '12',
    };
    final month = months[monthName];
    if (month == null) return null;
    final iso = '$year-$month-${day}T$time';
    return DateTime.tryParse(iso);
  } catch (_) {
    return null;
  }
}
