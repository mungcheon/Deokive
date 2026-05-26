import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';

// Free-board posts (notices + goods info) authored by the admin.
// Events live in `event_notices.dart` and surface on the event-calendar tab.

enum BoardPostTag { notice, info, general }

extension BoardPostTagX on BoardPostTag {
  String get label {
    switch (this) {
      case BoardPostTag.notice:
        return '공지';
      case BoardPostTag.info:
        return '정보';
      case BoardPostTag.general:
        return '일반';
    }
  }

  Color get color {
    switch (this) {
      case BoardPostTag.notice:
        return const Color(0xFFE85C5C);
      case BoardPostTag.info:
        return const Color(0xFF3F8DCC);
      case BoardPostTag.general:
        return const Color(0xFF7BB87B);
    }
  }
}

class BoardPost {
  final String id;
  final BoardPostTag tag;
  final String title;
  final String summary;
  final String content;
  final DateTime date;
  final String author;
  final int viewCount;
  /// Optional source link (e.g. X/Twitter post URL when admin curates from
  /// official channels). Shown as a small chip on the detail screen.
  final String? sourceUrl;
  /// Optional image attached when reposting from an X account. Stored as raw
  /// bytes so we can re-render offline. Persisted as base64 in JSON.
  final Uint8List? imageBytes;
  /// Whether the post is visible to everyone. Info-bot-fetched posts come in
  /// as `false` (pending) and only become visible once an admin approves
  /// them. Manually authored posts default to `true`.
  final bool approved;

  const BoardPost({
    required this.id,
    required this.tag,
    required this.title,
    required this.summary,
    required this.content,
    required this.date,
    this.author = '관리자',
    this.viewCount = 0,
    this.sourceUrl,
    this.imageBytes,
    this.approved = true,
  });

  BoardPost copyWith({
    String? id,
    BoardPostTag? tag,
    String? title,
    String? summary,
    String? content,
    DateTime? date,
    String? author,
    int? viewCount,
    String? sourceUrl,
    Uint8List? imageBytes,
    bool clearImage = false,
    bool? approved,
  }) {
    return BoardPost(
      id: id ?? this.id,
      tag: tag ?? this.tag,
      title: title ?? this.title,
      summary: summary ?? this.summary,
      content: content ?? this.content,
      date: date ?? this.date,
      author: author ?? this.author,
      viewCount: viewCount ?? this.viewCount,
      sourceUrl: sourceUrl ?? this.sourceUrl,
      imageBytes: clearImage ? null : (imageBytes ?? this.imageBytes),
      approved: approved ?? this.approved,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'tag': tag.name,
        'title': title,
        'summary': summary,
        'content': content,
        'date': date.toIso8601String(),
        'author': author,
        'viewCount': viewCount,
        'sourceUrl': sourceUrl,
        'approved': approved,
        if (imageBytes != null) 'imageBytes': base64Encode(imageBytes!),
      };

  factory BoardPost.fromJson(Map<String, dynamic> json) {
    Uint8List? image;
    final imgRaw = json['imageBytes'];
    if (imgRaw is String && imgRaw.isNotEmpty) {
      try {
        image = base64Decode(imgRaw);
      } catch (_) {}
    }
    return BoardPost(
      id: json['id'] as String,
      tag: BoardPostTag.values.firstWhere(
        (t) => t.name == json['tag'],
        orElse: () => BoardPostTag.info,
      ),
      title: json['title'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
      content: json['content'] as String? ?? '',
      date: DateTime.tryParse(json['date'] as String? ?? '') ?? DateTime.now(),
      author: json['author'] as String? ?? '관리자',
      viewCount: (json['viewCount'] as num?)?.toInt() ?? 0,
      sourceUrl: json['sourceUrl'] as String?,
      imageBytes: image,
      // Legacy posts (saved before this field existed) default to visible.
      approved: json['approved'] as bool? ?? true,
    );
  }
}

/// Curated info-bot identities. One bot per official X account — when admin
/// posts a tweet excerpt, the bot acts as the byline so users instantly
/// recognize the source.
///
/// X (Twitter) doesn't offer free RSS, so each bot's [feedUrl] defaults to a
/// public Nitter mirror. Nitter mirrors come and go; admin can configure a
/// working mirror or an alternative RSS source per bot at runtime.
class InfoBot {
  final String id;
  final String label;
  final String sourceHandle;
  final String defaultFeedUrl;

  const InfoBot({
    required this.id,
    required this.label,
    required this.sourceHandle,
    required this.defaultFeedUrl,
  });
}

const List<InfoBot> kInfoBots = [
  InfoBot(
    id: 'chiikawa_market',
    label: '치이카와 마켓 정보봇',
    sourceHandle: '@chiikawa_m_kr',
    defaultFeedUrl: 'https://nitter.net/chiikawa_m_kr/rss',
  ),
  InfoBot(
    id: 'bandai_namco',
    label: '반다이 남코 정보봇',
    sourceHandle: '@bandainamco_kr',
    defaultFeedUrl: 'https://nitter.net/bandainamco_kr/rss',
  ),
  InfoBot(
    id: 'ichibankuji',
    label: '이치방쿠지 정보봇',
    sourceHandle: '@ichibankuji',
    defaultFeedUrl: 'https://nitter.net/ichibankuji/rss',
  ),
  InfoBot(
    id: 'goodsmile',
    label: '굿스마일컴퍼니 정보봇',
    sourceHandle: '@gsc_kr',
    defaultFeedUrl: 'https://nitter.net/gsc_kr/rss',
  ),
  InfoBot(
    id: 'pokemon_center',
    label: '포켓몬센터 정보봇',
    sourceHandle: '@pokemoncenter',
    defaultFeedUrl: 'https://nitter.net/pokemoncenter/rss',
  ),
  InfoBot(
    id: 'chiikawa_kuji',
    label: '치이카와 쿠지 정보봇',
    sourceHandle: '@chiikawa_market',
    defaultFeedUrl: 'https://nitter.net/chiikawa_market/rss',
  ),
  InfoBot(
    id: 'chiikawa_mogumogu',
    label: '치이카와 모구모구 정보봇',
    sourceHandle: '@chiikawamgmg',
    defaultFeedUrl: 'https://nitter.net/chiikawamgmg/rss',
  ),
  InfoBot(
    id: 'nagano_market',
    label: '나가노마켓 정보봇',
    sourceHandle: '@nagano_market',
    defaultFeedUrl: 'https://nitter.net/nagano_market/rss',
  ),
];

InfoBot? infoBotById(String id) {
  for (final b in kInfoBots) {
    if (b.id == id) return b;
  }
  return null;
}

InfoBot? infoBotByLabel(String label) {
  for (final b in kInfoBots) {
    if (b.label == label) return b;
  }
  return null;
}

/// A user comment on a board post.
class BoardComment {
  final String id;
  final String postId;
  final String author;
  final String content;
  final DateTime date;

  const BoardComment({
    required this.id,
    required this.postId,
    required this.author,
    required this.content,
    required this.date,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'postId': postId,
        'author': author,
        'content': content,
        'date': date.toIso8601String(),
      };

  factory BoardComment.fromJson(Map<String, dynamic> json) => BoardComment(
        id: json['id'] as String,
        postId: json['postId'] as String,
        author: json['author'] as String? ?? '익명',
        content: json['content'] as String? ?? '',
        date: DateTime.tryParse(json['date'] as String? ?? '') ?? DateTime.now(),
      );
}

/// Seed posts shipped with the app — only system notices. Info posts come
/// from real bot fetches (see [InfoBotService]) and admin manual entries; no
/// fake placeholder content. AppState copies this into a mutable list on
/// first launch and persists changes to Hive.
final List<BoardPost> kSeedBoardPosts = <BoardPost>[
  BoardPost(
    id: 'notice_001',
    tag: BoardPostTag.notice,
    title: '덕카이브 앱 v1.0 정식 출시 안내',
    summary: '5탭 구조 + 게시판 + 행사 캘린더가 정식 오픈되었습니다.',
    content:
        '덕카이브 v1.0이 정식 출시되었습니다.\n\n홈/게시판/폴더/캘린더/설정 5탭 구조와 굿즈 관리 기능, 배지 시스템이 함께 제공됩니다.\n\n피드백은 설정 > 문의하기에서 보내주세요.',
    date: DateTime(2026, 5, 24),
  ),
  BoardPost(
    id: 'notice_002',
    tag: BoardPostTag.notice,
    title: '정보봇 시스템 안내',
    summary: '공식 X 계정별 정보봇이 굿즈 소식을 가져와 현재 언어로 자동 번역해 줍니다.',
    content:
        '각 공식 X 계정마다 별도의 정보봇이 운영됩니다.\n- 치이카와 마켓 정보봇 (@chiikawa_m_kr)\n- 반다이 남코 정보봇 (@bandainamco_kr)\n- 이치방쿠지 정보봇 (@ichibankuji)\n- 굿스마일컴퍼니 정보봇 (@gsc_kr)\n- 포켓몬센터 정보봇 (@pokemoncenter)\n\n게시판 자유게시판 탭의 "정보봇 새로고침"으로 최신 정보를 가져올 수 있어요 (관리자 전용).\n\n외국어 게시글은 설정의 현재 앱 언어로 자동 번역됩니다. 번역은 무료 서비스를 사용하므로 별도 비용이나 키 설정이 필요 없어요. 게시글 상단의 "원문 보기"로 원문도 언제든 확인할 수 있습니다.\n\n조회수는 0에서 시작해 실제 클릭으로만 증가합니다.',
    date: DateTime(2026, 5, 22),
  ),
  BoardPost(
    id: 'notice_003',
    tag: BoardPostTag.notice,
    title: '닉네임 정책 안내 (최대 15자)',
    summary: '닉네임은 최대 15자까지 입력할 수 있습니다.',
    content:
        '프로필 닉네임은 최대 15자까지만 입력 가능하도록 제한되었습니다.\n\n기존 닉네임이 15자를 넘는 경우 표시 단계에서 자동으로 잘립니다.',
    date: DateTime(2026, 5, 12),
  ),
];

enum BoardSortType { newest, oldest, popular }

extension BoardSortTypeX on BoardSortType {
  String get label {
    switch (this) {
      case BoardSortType.newest:
        return '최신순';
      case BoardSortType.oldest:
        return '오래된순';
      case BoardSortType.popular:
        return '인기순';
    }
  }
}

List<BoardPost> sortPosts(List<BoardPost> posts, BoardSortType sort) {
  final out = [...posts];
  switch (sort) {
    case BoardSortType.newest:
      out.sort((a, b) => b.date.compareTo(a.date));
      break;
    case BoardSortType.oldest:
      out.sort((a, b) => a.date.compareTo(b.date));
      break;
    case BoardSortType.popular:
      out.sort((a, b) => b.viewCount.compareTo(a.viewCount));
      break;
  }
  return out;
}

List<BoardPost> filterPosts(List<BoardPost> posts, String query) {
  if (query.trim().isEmpty) return posts;
  final q = query.toLowerCase();
  return posts
      .where((p) =>
          p.title.toLowerCase().contains(q) ||
          p.summary.toLowerCase().contains(q) ||
          p.content.toLowerCase().contains(q))
      .toList();
}
