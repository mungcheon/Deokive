import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../config/server_config.dart';
import '../data/board_posts.dart';
import 'local_admin_override.dart';

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
        if (localAdminOverrideEnabled) 'X-Deokive-App-Admin': '1',
      };

  Future<({int totalCount, int pendingCount, String? latestUpdatedAt})>
      fetchMeta([String? token]) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/meta');
    final resp = await _http
        .get(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('meta failed ${resp.statusCode}');
    }
    final data =
        jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (
      totalCount: (data['total_count'] as num?)?.toInt() ?? 0,
      pendingCount: (data['pending_count'] as num?)?.toInt() ?? 0,
      latestUpdatedAt: data['latest_updated_at'] as String?,
    );
  }

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
    return data.whereType<Map<String, dynamic>>().map(_postFromServer).toList();
  }

  Future<List<BoardPost>> fetchPending([String? token]) async {
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

  Future<BoardPost> createPost(
    String? token,
    BoardPost post, {
    String? author,
    String? deviceId,
  }) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts');
    final resp = await _http
        .post(
          uri,
          headers: _headers(token),
          body: jsonEncode({
            'tag': post.tag.name,
            'title': post.title,
            'summary': post.summary,
            'content': post.content,
            'author': author,
            'device_id': deviceId,
            'source_url': post.sourceUrl,
            'image_data_base64':
                post.imageBytes == null ? null : base64Encode(post.imageBytes!),
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 201) {
      throw BoardApiUnavailable('create failed ${resp.statusCode}');
    }
    return _postFromServer(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<void> approvePost(String? token, String serverId) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/approve');
    final resp = await _http
        .post(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('approve failed ${resp.statusCode}');
    }
  }

  Future<int> refreshInfoBots([String? token]) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/bots/refresh');
    final resp = await _http
        .post(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 20));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('bot refresh failed ${resp.statusCode}');
    }
    final data =
        jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (data['added'] as num?)?.toInt() ?? 0;
  }

  Future<BoardPost> updatePost(
      String? token, String serverId, BoardPost post) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId');
    final resp = await _http
        .patch(
          uri,
          headers: _headers(token),
          body: jsonEncode({
            'tag': post.tag.name,
            'title': post.title,
            'summary': post.summary,
            'content': post.content,
            'source_url': post.sourceUrl,
            'image_data_base64':
                post.imageBytes == null ? null : base64Encode(post.imageBytes!),
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('update failed ${resp.statusCode}');
    }
    return _postFromServer(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<void> deletePost(
    String? token,
    String serverId, {
    String? deviceId,
  }) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId', {
      if (deviceId != null && deviceId.isNotEmpty) 'device_id': deviceId,
    });
    await _http
        .delete(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
  }

  Future<BoardPost> incrementView(String serverId, {String? deviceId}) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/view', {
      if (deviceId != null && deviceId.isNotEmpty) 'device_id': deviceId,
    });
    final resp = await _http
        .post(uri, headers: _headers())
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('view failed ${resp.statusCode}');
    }
    return _postFromServer(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<({bool liked, int likeCount})> toggleLike(
    String? token,
    String serverId,
    String? deviceId,
  ) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/like', {
      if (deviceId != null && deviceId.isNotEmpty) 'device_id': deviceId,
    });
    final resp = await _http
        .post(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw BoardApiUnavailable('like failed ${resp.statusCode}');
    }
    final data =
        jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
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
    return data
        .whereType<Map<String, dynamic>>()
        .map(_commentFromServer)
        .toList();
  }

  Future<BoardComment?> addComment(
    String? token,
    String serverId,
    String content, {
    String? author,
    String? deviceId,
  }) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/posts/$serverId/comments');
    final resp = await _http
        .post(
          uri,
          headers: _headers(token),
          body: jsonEncode({
            'content': content,
            'author': author,
            'device_id': deviceId,
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 201) return null;
    return _commentFromServer(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<void> deleteComment(
    String? token,
    String commentId, {
    String? deviceId,
  }) async {
    if (!enabled) throw const BoardApiUnavailable();
    final uri = ServerConfig.boardUri('/board/comments/$commentId', {
      if (deviceId != null && deviceId.isNotEmpty) 'device_id': deviceId,
    });
    await _http
        .delete(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
  }

  BoardComment _commentFromServer(Map<String, dynamic> m) {
    return BoardComment(
      id: '${m['id']}',
      postId: 'srv_${m['post_id']}',
      author: m['author'] as String? ?? '익명',
      authorId: (m['author_device_id'] as String?) != null
          ? 'device:${m['author_device_id']}'
          : null,
      content: m['content'] as String? ?? '',
      date:
          DateTime.tryParse(m['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(m['updated_at'] as String? ?? ''),
      edited: m['edited'] as bool? ?? false,
    );
  }

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
      date:
          DateTime.tryParse(m['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(m['updated_at'] as String? ?? ''),
      author: m['author'] as String? ?? '관리자',
      authorId: (m['author_device_id'] as String?) != null
          ? 'device:${m['author_device_id']}'
          : ((m['author_user_id'] as num?) != null
              ? 'user:${(m['author_user_id'] as num).toInt()}'
              : null),
      viewCount: (m['view_count'] as num?)?.toInt() ?? 0,
      likeCount: (m['like_count'] as num?)?.toInt() ?? 0,
      commentCount: (m['comment_count'] as num?)?.toInt() ?? 0,
      sourceUrl: m['source_url'] as String?,
      imageUrl: m['image_url'] as String?,
      imageBytes: _decodeImageBytes(m['image_data_base64'] as String?),
      approved: m['approved'] as bool? ?? true,
    );
  }

  Uint8List? _decodeImageBytes(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    try {
      return base64Decode(raw);
    } catch (_) {
      return null;
    }
  }
}
