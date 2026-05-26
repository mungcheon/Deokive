import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/server_config.dart';
import '../data/board_posts.dart';

/// HTTP client for the shared board (게시판) on the FastAPI backend.
///
/// Read endpoints are public; write endpoints take a bearer [token] obtained
/// from server login. All calls are no-ops / throw [BoardApiUnavailable] when
/// [ServerConfig.enabled] is false (no server URL configured), so callers can
/// safely fall back to the local Hive board.
class BoardApiUnavailable implements Exception {
  final String message;
  const BoardApiUnavailable([this.message = 'server not configured']);
  @override
  String toString() => 'BoardApiUnavailable: $message';
}

class BoardApiService {
  final http.Client _http;
  BoardApiService({http.Client? client}) : _http = client ?? http.Client();
  void dispose() => _http.close();

  bool get enabled => ServerConfig.enabled;

  Map<String, String> _headers([String? token]) => {
        'Content-Type': 'application/json',
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      };

  /// GET /board/posts — newest first. Public (approved only).
  Future<List<BoardPost>> fetchPosts({String? tag, int limit = 100}) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts', {
      'limit': limit,
      if (tag != null) 'tag': tag,
    });
    final resp = await _http.get(uri).timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('list failed ${resp.statusCode}');
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    if (data is! List) return const [];
    return data
        .whereType<Map<String, dynamic>>()
        .map(_postFromServer)
        .toList();
  }

  /// GET /board/posts/pending — admin only.
  Future<List<BoardPost>> fetchPending(String token) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/pending');
    final resp = await _http
        .get(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('pending failed ${resp.statusCode}');
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    if (data is! List) return const [];
    return data.whereType<Map<String, dynamic>>().map(_postFromServer).toList();
  }

  Future<BoardPost> createPost(String token, BoardPost post) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts');
    final resp = await _http
        .post(uri,
            headers: _headers(token),
            body: jsonEncode({
              'tag': post.tag.name,
              'title': post.title,
              'summary': post.summary,
              'content': post.content,
              'source_url': post.sourceUrl,
            }))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 201) {
      throw BoardApiUnavailable('create failed ${resp.statusCode}');
    }
    return _postFromServer(jsonDecode(utf8.decode(resp.bodyBytes)));
  }

  Future<void> approvePost(String token, String serverId) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/approve');
    final resp = await _http
        .post(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('approve failed ${resp.statusCode}');
    }
  }

  Future<void> deletePost(String token, String serverId) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId');
    await _http
        .delete(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
  }

  Future<({bool liked, int likeCount})> toggleLike(
      String token, String serverId) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/like');
    final resp = await _http
        .post(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('like failed ${resp.statusCode}');
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (
      liked: data['liked'] == true,
      likeCount: (data['like_count'] as num?)?.toInt() ?? 0,
    );
  }

  Future<List<BoardComment>> fetchComments(String serverId) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/comments');
    final resp = await _http.get(uri).timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) return const [];
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    if (data is! List) return const [];
    return data.whereType<Map<String, dynamic>>().map((m) {
      return BoardComment(
        id: '${m['id']}',
        postId: '${m['post_id']}',
        author: m['author'] as String? ?? '익명',
        content: m['content'] as String? ?? '',
        date: DateTime.now(),
      );
    }).toList();
  }

  Future<BoardComment?> addComment(
      String token, String serverId, String content) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/comments');
    final resp = await _http
        .post(uri,
            headers: _headers(token), body: jsonEncode({'content': content}))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 201) return null;
    final m = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return BoardComment(
      id: '${m['id']}',
      postId: '${m['post_id']}',
      author: m['author'] as String? ?? '익명',
      content: m['content'] as String? ?? '',
      date: DateTime.now(),
    );
  }

  // Server post id is an int; we prefix it so it never collides with local
  // ids (which are like 'p_<micros>' / 'bot_<...>' / 'notice_001').
  BoardPost _postFromServer(Map<String, dynamic> m) {
    final tagName = m['tag'] as String? ?? 'general';
    final tag = BoardPostTag.values.firstWhere(
      (t) => t.name == tagName,
      orElse: () => BoardPostTag.general,
    );
    return BoardPost(
      id: 'srv_${m['id']}',
      tag: tag,
      title: m['title'] as String? ?? '',
      summary: m['summary'] as String? ?? '',
      content: m['content'] as String? ?? '',
      date: DateTime.now(),
      author: m['author'] as String? ?? '관리자',
      viewCount: (m['view_count'] as num?)?.toInt() ?? 0,
      sourceUrl: m['source_url'] as String?,
      approved: m['approved'] as bool? ?? true,
    );
  }
}
