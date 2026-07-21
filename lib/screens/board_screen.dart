import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/server_config.dart';
import '../data/board_posts.dart';
import '../data/event_notices.dart';
import '../l10n/app_language.dart';
import '../l10n/app_strings.dart';
import '../models/trade_post.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_header_title.dart';
import 'board_post_editor_screen.dart';
import 'news_detail_screen.dart';
import 'trade_post_editor_screen.dart';

class BoardScreen extends StatefulWidget {
  const BoardScreen({super.key});

  @override
  State<BoardScreen> createState() => _BoardScreenState();
}

class _BoardScreenState extends State<BoardScreen> {
  int _currentTab = 0;

  static const _boardTabStorageKey = PageStorageKey<String>('board-free-talk');
  static const _archiveTabStorageKey = PageStorageKey<String>('board-archive');
  static const _eventTabStorageKey = PageStorageKey<String>('board-events');

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final strings = AppStrings.of(appState.appLanguage);
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;

        final sections = <_BoardTab>[
          _BoardTab(
            label: strings.boardSectionFreeTalk,
            icon: Icons.forum_outlined,
          ),
          const _BoardTab(
            label: '글 저장소',
            icon: Icons.bookmark_outline_rounded,
          ),
          _BoardTab(
            label: strings.boardSectionEventSchedule,
            icon: Icons.event_available_rounded,
          ),
        ];

        return Scaffold(
          appBar: AppBar(
            title: const DeokiveHeaderTitle(),
          ),
          floatingActionButton: _buildFab(context, appState, palette),
          body: SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: _BoardTabBar(
                    tabs: sections,
                    currentIndex: _currentTab,
                    accent: palette.primary,
                    onTap: (i) => setState(() => _currentTab = i),
                  ),
                ),
                Expanded(
                  child: IndexedStack(
                    index: _currentTab,
                    children: [
                      _FreeTalkView(
                        key: _boardTabStorageKey,
                        accent: palette.primary,
                        posts: appState.visibleBoardPosts,
                        isAdmin: appState.adminMode,
                        showPendingOnly: false,
                      ),
                      _PostArchiveView(
                        key: _archiveTabStorageKey,
                        accent: palette.primary,
                      ),
                      _EventScheduleView(
                        key: _eventTabStorageKey,
                        accent: palette.primary,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget? _buildFab(
      BuildContext context, AppState appState, DeokivePalette palette) {
    final theme = Theme.of(context);
    if (appState.readOnlyPublicSite) return null;
    // Free-talk tab — any logged-in member can post.
    if (_currentTab == 0) {
      if (!appState.isLoggedIn && !appState.adminMode) return null;
      return FloatingActionButton(
        elevation: 0,
        backgroundColor: palette.primary.withValues(alpha: 0.78),
        foregroundColor: theme.colorScheme.onPrimary,
        shape: const CircleBorder(),
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => const BoardPostEditorScreen(),
            ),
          );
        },
        child: const Icon(Icons.edit_outlined),
      );
    }
    // Archive + Event tabs — no FAB.
    return null;
  }
}

class _BoardTab {
  final String label;
  final IconData icon;

  const _BoardTab({
    required this.label,
    required this.icon,
  });
}

String _formatBoardDateTime(DateTime value) {
  final month = value.month.toString().padLeft(2, '0');
  final day = value.day.toString().padLeft(2, '0');
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '${value.year}.$month.$day $hour:$minute';
}

String _formatRefreshStatusTime(DateTime value) {
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '$hour:$minute';
}

bool _isEdited(DateTime createdAt, DateTime? updatedAt) {
  return updatedAt != null && updatedAt.isAfter(createdAt);
}

String _normalizeBoardImageUrl(String rawUrl) {
  return rawUrl
      .trim()
      .replaceAll('&amp;', '&')
      .replaceFirst(RegExp(r'^//'), 'https://');
}

class _BoardPostImage extends StatefulWidget {
  final BoardPost post;
  final double? width;
  final double? height;
  final BorderRadius borderRadius;

  const _BoardPostImage({
    required this.post,
    this.width,
    this.height,
    required this.borderRadius,
  });

  @override
  State<_BoardPostImage> createState() => _BoardPostImageState();
}

class _BoardPostImageState extends State<_BoardPostImage> {
  int _urlIndex = 0;

  List<String> _candidateUrls() {
    final raw = widget.post.imageUrl?.trim() ?? '';
    if (raw.isEmpty) return const [];
    final normalized = _normalizeBoardImageUrl(raw);
    final urls = <String>{};

    if (normalized.isNotEmpty) {
      urls.add(normalized);
    }

    if (ServerConfig.enabled) {
      urls.add(
        ServerConfig.boardUri('/board/image', {'url': normalized}).toString(),
      );

      final backendBase = ServerConfig.configuredBaseUrl.trim();
      if (backendBase.isNotEmpty) {
        final backendUri = Uri.parse(
          backendBase.endsWith('/')
              ? backendBase.substring(0, backendBase.length - 1)
              : backendBase,
        ).replace(
          path: '/board/image',
          queryParameters: {'url': normalized},
        );
        urls.add(backendUri.toString());
      }
    }

    return urls.toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.post.imageBytes != null) {
      return ClipRRect(
        borderRadius: widget.borderRadius,
        child: Image.memory(
          widget.post.imageBytes!,
          width: widget.width,
          height: widget.height,
          fit: BoxFit.cover,
        ),
      );
    }
    final candidates = _candidateUrls();
    if (candidates.isEmpty) return const SizedBox.shrink();
    final safeIndex = _urlIndex.clamp(0, candidates.length - 1);
    final imageUrl = candidates[safeIndex];
    return ClipRRect(
      borderRadius: widget.borderRadius,
      child: Image.network(
        imageUrl,
        key: ValueKey(imageUrl),
        width: widget.width,
        height: widget.height,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) {
          if (safeIndex + 1 < candidates.length) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (!mounted) return;
              setState(() => _urlIndex = safeIndex + 1);
            });
            return SizedBox(
              width: widget.width,
              height: widget.height,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                ),
              ),
            );
          }
          return SizedBox(
            width: widget.width,
            height: widget.height,
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
              child: const Icon(Icons.broken_image_outlined),
            ),
          );
        },
      ),
    );
  }
}

class _BoardTabBar extends StatelessWidget {
  final List<_BoardTab> tabs;
  final int currentIndex;
  final Color accent;
  final ValueChanged<int> onTap;

  const _BoardTabBar({
    required this.tabs,
    required this.currentIndex,
    required this.accent,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Row(
        children: List.generate(tabs.length, (index) {
          final tab = tabs[index];
          final selected = index == currentIndex;
          return Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => onTap(index),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  color: selected ? accent : Colors.transparent,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      tab.icon,
                      size: 18,
                      color: selected
                          ? Colors.white
                          : accent.withValues(alpha: 0.85),
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        tab.label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: selected
                              ? Colors.white
                              : accent.withValues(alpha: 0.85),
                          fontWeight:
                              selected ? FontWeight.w800 : FontWeight.w600,
                          fontSize: 13.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

// ── Free talk view (notices + info posts, admin-managed) ────────────────

class _FreeTalkView extends StatefulWidget {
  final Color accent;
  final List<BoardPost> posts;
  final bool isAdmin;
  final bool showPendingOnly;

  const _FreeTalkView({
    super.key,
    required this.accent,
    required this.posts,
    required this.isAdmin,
    this.showPendingOnly = false,
  });

  @override
  State<_FreeTalkView> createState() => _FreeTalkViewState();
}

class _FreeTalkViewState extends State<_FreeTalkView> {
  final TextEditingController _searchController = TextEditingController();
  String _query = '';
  BoardSortType _sort = BoardSortType.newest;
  final Set<BoardPostTag> _hiddenTags = <BoardPostTag>{};
  bool _selectionMode = false;
  final Set<String> _selectedPostIds = <String>{};
  bool _isRefreshingPosts = false;
  DateTime? _lastRefreshedAt;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _toggleTag(BoardPostTag tag) {
    setState(() {
      if (_hiddenTags.contains(tag)) {
        _hiddenTags.remove(tag);
      } else {
        _hiddenTags.add(tag);
      }
    });
  }

  void _resetTags() => setState(() {
        _hiddenTags.clear();
      });

  Future<void> _refreshBots() async {
    final appState = context.read<AppState>();
    final added = await appState.refreshInfoBots();
    if (!mounted) return;
    setState(() {
      _lastRefreshedAt = DateTime.now();
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          added == 0
              ? '새로운 정보봇 글이 없어요. (네트워크 / 미러 상태에 따라 실패할 수 있음)'
              : '정보봇 새 글 $added개를 가져왔어요.',
        ),
      ),
    );
  }

  Future<void> _refreshPosts() async {
    if (_isRefreshingPosts) return;
    setState(() => _isRefreshingPosts = true);
    try {
      await context.read<AppState>().syncBoardFromServer();
      if (!mounted) return;
      setState(() {
        _lastRefreshedAt = DateTime.now();
      });
    } finally {
      if (mounted) {
        setState(() => _isRefreshingPosts = false);
      }
    }
  }

  void _toggleSelectionMode() {
    setState(() {
      _selectionMode = !_selectionMode;
      if (!_selectionMode) {
        _selectedPostIds.clear();
      }
    });
  }

  void _togglePostSelection(String postId) {
    setState(() {
      if (_selectedPostIds.contains(postId)) {
        _selectedPostIds.remove(postId);
      } else {
        _selectedPostIds.add(postId);
      }
    });
  }

  void _toggleSelectAll(List<BoardPost> posts) {
    setState(() {
      final visibleIds = posts.map((post) => post.id).toSet();
      final allSelected =
          visibleIds.isNotEmpty && visibleIds.every(_selectedPostIds.contains);
      if (allSelected) {
        _selectedPostIds.removeAll(visibleIds);
      } else {
        _selectedPostIds.addAll(visibleIds);
      }
    });
  }

  Future<void> _approveSelected() async {
    final appState = context.read<AppState>();
    final selectedPendingIds = widget.posts
        .where((post) => _selectedPostIds.contains(post.id) && !post.approved)
        .map((post) => post.id)
        .toList(growable: false);
    if (selectedPendingIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('승인할 게시글을 먼저 선택해 주세요.')),
      );
      return;
    }
    for (final postId in selectedPendingIds) {
      appState.approveBoardPost(postId);
    }
    if (!mounted) return;
    setState(() {
      _selectedPostIds.removeAll(selectedPendingIds);
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('게시글 ${selectedPendingIds.length}개를 승인했어요.')),
    );
  }

  Future<void> _deleteSelectedPosts() async {
    final appState = context.read<AppState>();
    final selectedIds = _selectedPostIds.toList(growable: false);
    if (selectedIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('삭제할 게시글을 먼저 선택해 주세요.')),
      );
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('선택 게시글 삭제'),
          content: Text(
            '선택한 게시글 ${selectedIds.length}개를 삭제할까요?\n이 작업은 되돌릴 수 없어요.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('삭제'),
            ),
          ],
        );
      },
    );
    if (confirmed != true || !mounted) return;
    for (final postId in selectedIds) {
      appState.deleteBoardPost(postId);
    }
    setState(() {
      _selectedPostIds.clear();
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('게시글 ${selectedIds.length}개를 삭제했어요.')),
    );
  }

  Future<void> _openPendingPosts() async {
    final appState = context.read<AppState>();
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _PendingBoardPostsScreen(
          accent: widget.accent,
          posts: appState.pendingBoardPosts,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final visible =
        widget.posts.where((p) => !_hiddenTags.contains(p.tag)).toList();
    final filtered = filterPosts(visible, _query);
    final posts = sortPosts(filtered, _sort);
    final allOn = _hiddenTags.isEmpty;
    final appState = context.watch<AppState>();
    final readOnly = appState.readOnlyPublicSite;
    final allVisibleSelected = posts.isNotEmpty &&
        posts.every((post) => _selectedPostIds.contains(post.id));
    final refreshText = _isRefreshingPosts
        ? '게시글을 불러오는 중이에요...'
        : _lastRefreshedAt == null
            ? '목록은 유지됩니다. 아래로 당겨 새로고침하세요.'
            : '마지막 새로고침 ${_formatRefreshStatusTime(_lastRefreshedAt!)}';

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: Column(
            children: [
              if (widget.showPendingOnly)
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.orange.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: Colors.orange.withValues(alpha: 0.25),
                    ),
                  ),
                  child: Text(
                    '관리자 전용 승인 대기 목록입니다. 승인 전에는 일반 사용자에게 보이지 않아요.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.orange.shade900,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              TextField(
                controller: _searchController,
                onChanged: (v) => setState(() => _query = v),
                decoration: InputDecoration(
                  hintText: '게시글 검색',
                  prefixIcon: const Icon(Icons.search_rounded, size: 20),
                  suffixIcon: _query.isEmpty
                      ? null
                      : IconButton(
                          icon: const Icon(Icons.close_rounded, size: 18),
                          onPressed: () {
                            _searchController.clear();
                            setState(() => _query = '');
                          },
                        ),
                  isDense: true,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(
                      color: theme.colorScheme.outlineVariant,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        _TagFilterChip(
                          label: '전체',
                          selected: allOn,
                          color: widget.accent,
                          onTap: _resetTags,
                        ),
                        for (final tag in BoardPostTag.values)
                          _TagFilterChip(
                            label: tag.label,
                            selected: !_hiddenTags.contains(tag),
                            color: tag.color,
                            onTap: () => _toggleTag(tag),
                          ),
                      ],
                    ),
                  ),
                  PopupMenuButton<BoardSortType>(
                    tooltip: '정렬',
                    onSelected: (s) => setState(() => _sort = s),
                    itemBuilder: (_) => BoardSortType.values
                        .map((s) => PopupMenuItem(
                              value: s,
                              child: Text(s.label),
                            ))
                        .toList(),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.sort_rounded, size: 16),
                          const SizedBox(width: 4),
                          Text(
                            _sort.label,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              if (widget.isAdmin && !readOnly) ...[
                const SizedBox(height: 6),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest
                        .withValues(alpha: 0.55),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: theme.colorScheme.outlineVariant,
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              '관리자 도구',
                              style: theme.textTheme.labelLarge?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _selectionMode
                                  ? '${_selectedPostIds.length}개 선택 중'
                                  : '선택 모드와 승인 대기 목록으로 게시글을 관리하세요.',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.65),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filledTonal(
                        tooltip: '승인 대기 보기',
                        onPressed: _openPendingPosts,
                        icon: Badge(
                          isLabelVisible: appState.pendingBoardPostCount > 0,
                          label: Text('${appState.pendingBoardPostCount}'),
                          child: const Icon(Icons.pending_actions_rounded,
                              size: 18),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filledTonal(
                        tooltip: appState.isRefreshingInfoBots
                            ? '정보봇 동기화 중'
                            : '정보봇 업데이트',
                        onPressed:
                            appState.isRefreshingInfoBots ? null : _refreshBots,
                        icon: appState.isRefreshingInfoBots
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.refresh_rounded, size: 18),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.tonalIcon(
                        onPressed: _toggleSelectionMode,
                        icon: Icon(
                          _selectionMode
                              ? Icons.close_fullscreen_rounded
                              : Icons.checklist_rounded,
                          size: 18,
                        ),
                        label: Text(_selectionMode ? '선택 종료' : '선택'),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.55),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: theme.colorScheme.outlineVariant),
            ),
            child: Row(
              children: [
                SizedBox(
                  width: 18,
                  height: 18,
                  child: _isRefreshingPosts
                      ? const CircularProgressIndicator(strokeWidth: 2)
                      : Icon(
                          Icons.sync_rounded,
                          size: 18,
                          color: theme.colorScheme.primary,
                        ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    refreshText,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color:
                          theme.colorScheme.onSurface.withValues(alpha: 0.72),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        if (widget.isAdmin && _selectionMode)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: theme.colorScheme.outlineVariant),
              ),
              child: Row(
                children: [
                  Checkbox(
                    value: allVisibleSelected,
                    onChanged: (_) => _toggleSelectAll(posts),
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      '전체 선택 · ${_selectedPostIds.length}개 선택됨',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton.filledTonal(
                    tooltip: '선택 게시글 승인',
                    onPressed:
                        _selectedPostIds.isEmpty ? null : _approveSelected,
                    icon: const Icon(Icons.check_circle_rounded, size: 18),
                  ),
                  const SizedBox(width: 6),
                  IconButton.filled(
                    tooltip: '선택 게시글 삭제',
                    onPressed:
                        _selectedPostIds.isEmpty ? null : _deleteSelectedPosts,
                    icon: const Icon(Icons.delete_outline_rounded, size: 18),
                  ),
                ],
              ),
            ),
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _refreshPosts,
            child: posts.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 40, 16, 24),
                    children: [
                      Center(
                        child: Padding(
                          padding: const EdgeInsets.all(32),
                          child: Text(
                            _query.isEmpty ? '아직 등록된 글이 없습니다.' : '검색 결과가 없습니다.',
                            style: TextStyle(color: Colors.grey.shade600),
                          ),
                        ),
                      ),
                    ],
                  )
                : ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                    itemCount: posts.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, i) => _BoardPostCard(
                      post: posts[i],
                      isAdmin: widget.isAdmin,
                      selectionMode: _selectionMode,
                      selected: _selectedPostIds.contains(posts[i].id),
                      onToggleSelection: () =>
                          _togglePostSelection(posts[i].id),
                    ),
                  ),
          ),
        ),
      ],
    );
  }
}

class _PendingBoardPostsScreen extends StatelessWidget {
  final Color accent;
  final List<BoardPost> posts;

  const _PendingBoardPostsScreen({
    required this.accent,
    required this.posts,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('승인 대기'),
      ),
      body: SafeArea(
        child: _FreeTalkView(
          accent: accent,
          posts: posts,
          isAdmin: true,
          showPendingOnly: true,
        ),
      ),
    );
  }
}

class _TagFilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  const _TagFilterChip({
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? color.withValues(alpha: 0.18) : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: selected
                ? color.withValues(alpha: 0.45)
                : Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected
                ? color
                : Theme.of(context)
                    .colorScheme
                    .onSurface
                    .withValues(alpha: 0.75),
            fontSize: 12.5,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _BoardPostCard extends StatelessWidget {
  final BoardPost post;
  final bool isAdmin;
  final bool selectionMode;
  final bool selected;
  final VoidCallback? onToggleSelection;

  const _BoardPostCard({
    required this.post,
    required this.isAdmin,
    this.selectionMode = false,
    this.selected = false,
    this.onToggleSelection,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final appState = context.watch<AppState>();
    final canManagePost = isAdmin ||
        ((post.authorId != null && post.authorId == appState.stableAuthorId) ||
            (post.author == appState.displayName.trim() &&
                appState.isLoggedIn));
    final translation = appState.cachedTranslationFor(
      post.id,
      appState.appLanguage.translationCode,
    );
    final displayTitle = translation?.title ?? post.title;
    final displaySummary = translation?.summary ?? post.summary;
    final dateText = _formatBoardDateTime(post.date);
    final edited = _isEdited(post.date, post.updatedAt);

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          if (selectionMode) {
            onToggleSelection?.call();
            return;
          }
          context.read<AppState>().incrementBoardPostView(post.id);
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => _BoardPostDetailScreen(post: post),
            ),
          );
        },
        onLongPress: canManagePost
            ? () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => BoardPostEditorScreen(existing: post),
                  ),
                );
              }
            : null,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (selectionMode) ...[
                    Padding(
                      padding: const EdgeInsets.only(right: 8, top: 2),
                      child: Checkbox(
                        value: selected,
                        onChanged: (_) => onToggleSelection?.call(),
                      ),
                    ),
                  ],
                  if (post.imageBytes != null ||
                      (post.imageUrl?.trim().isNotEmpty ?? false)) ...[
                    _BoardPostImage(
                      post: post,
                      width: 60,
                      height: 60,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    const SizedBox(width: 10),
                  ],
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: post.tag.color.withValues(alpha: 0.16),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                post.tag.label,
                                style: TextStyle(
                                  color: post.tag.color,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 0.3,
                                ),
                              ),
                            ),
                            if (!post.approved) ...[
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 7, vertical: 3),
                                decoration: BoxDecoration(
                                  color: Colors.orange.withValues(alpha: 0.18),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  '승인 대기',
                                  style: TextStyle(
                                    color: Colors.orange.shade800,
                                    fontSize: 10.5,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ),
                            ],
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                displayTitle,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 14.5,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                            if (post.sourceUrl != null)
                              Padding(
                                padding: const EdgeInsets.only(left: 6),
                                child: Icon(Icons.link_rounded,
                                    size: 14, color: Colors.grey.shade500),
                              ),
                            if (isAdmin)
                              SizedBox(
                                width: 32,
                                height: 28,
                                child: PopupMenuButton<String>(
                                  tooltip: '관리',
                                  padding: EdgeInsets.zero,
                                  icon: Icon(Icons.more_vert_rounded,
                                      size: 18, color: Colors.grey.shade600),
                                  onSelected: (value) {
                                    if (value == 'approve') {
                                      context
                                          .read<AppState>()
                                          .approveBoardPost(post.id);
                                      ScaffoldMessenger.of(context)
                                          .showSnackBar(const SnackBar(
                                        content: Text('글을 승인했어요. 이제 공개됩니다.'),
                                      ));
                                    } else if (value == 'edit') {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) => BoardPostEditorScreen(
                                              existing: post),
                                        ),
                                      );
                                    } else if (value == 'delete') {
                                      _confirmDeletePost(context, post);
                                    }
                                  },
                                  itemBuilder: (_) => [
                                    if (!post.approved)
                                      const PopupMenuItem(
                                        value: 'approve',
                                        child: Row(children: [
                                          Icon(Icons.check_circle_outline,
                                              size: 16, color: Colors.green),
                                          SizedBox(width: 8),
                                          Text('승인',
                                              style: TextStyle(
                                                  color: Colors.green)),
                                        ]),
                                      ),
                                    const PopupMenuItem(
                                      value: 'edit',
                                      child: Row(children: [
                                        Icon(Icons.edit_outlined, size: 16),
                                        SizedBox(width: 8),
                                        Text('수정'),
                                      ]),
                                    ),
                                    const PopupMenuItem(
                                      value: 'delete',
                                      child: Row(children: [
                                        Icon(Icons.delete_outline,
                                            size: 16, color: Colors.red),
                                        SizedBox(width: 8),
                                        Text('삭제',
                                            style:
                                                TextStyle(color: Colors.red)),
                                      ]),
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          displaySummary,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12.5,
                            color: Colors.grey.shade700,
                            height: 1.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  Text(
                    post.author,
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                      color: Colors.grey.shade600,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    edited ? '작성 $dateText · 수정됨' : '작성 $dateText',
                    style: TextStyle(
                      fontSize: 11.5,
                      color: Colors.grey.shade500,
                    ),
                  ),
                  const Spacer(),
                  Icon(Icons.visibility_outlined,
                      size: 13, color: Colors.grey.shade500),
                  const SizedBox(width: 3),
                  Text(
                    '${post.viewCount}',
                    style: TextStyle(
                      fontSize: 11.5,
                      color: Colors.grey.shade500,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _confirmDeletePost(BuildContext context, BoardPost post) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dctx) => AlertDialog(
        title: const Text('게시글 삭제'),
        content: Text(
          '"${post.title}" 글을 삭제할까요?\n삭제한 글은 복구할 수 없어요.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dctx, false),
            child: const Text('취소'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(dctx).colorScheme.error,
            ),
            onPressed: () => Navigator.pop(dctx, true),
            child: const Text('삭제'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      context.read<AppState>().deleteBoardPost(post.id);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('게시글을 삭제했어요.')),
      );
    }
  }
}

// ── Trade view ──────────────────────────────────────────────────────────

/// 글 저장소 — internal sub-tabs: 내가 작성한 글 / 저장한 글.
class _PostArchiveView extends StatefulWidget {
  final Color accent;
  const _PostArchiveView({super.key, required this.accent});

  @override
  State<_PostArchiveView> createState() => _PostArchiveViewState();
}

class _PostArchiveViewState extends State<_PostArchiveView> {
  int _section = 0; // 0=내가 작성한 글, 1=저장한 글

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final appState = context.watch<AppState>();

    if (!appState.isLoggedIn) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Text(
            '로그인 후 작성한 글과 저장한 글을 모아볼 수 있어요.',
            style: TextStyle(
              fontSize: 14,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.65),
            ),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    final myName = appState.displayName.trim();
    final myPosts =
        appState.boardPosts.where((p) => p.author.trim() == myName).toList();
    final saved = appState.bookmarkedPosts;
    final list = _section == 0 ? myPosts : saved;
    final emptyText = _section == 0
        ? '아직 작성한 글이 없어요.\n자유 탭에서 첫 글을 남겨보세요.'
        : '아직 저장한 글이 없어요.\n게시글 상세에서 🔖 아이콘을 눌러 저장하세요.';

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SegmentedButton<int>(
            segments: [
              ButtonSegment(
                value: 0,
                label: Text('내가 쓴 글 (${myPosts.length})'),
                icon: const Icon(Icons.edit_note_rounded, size: 18),
              ),
              ButtonSegment(
                value: 1,
                label: Text('저장한 글 (${saved.length})'),
                icon: const Icon(Icons.bookmark_rounded, size: 18),
              ),
            ],
            selected: {_section},
            onSelectionChanged: (s) => setState(() => _section = s.first),
            style: ButtonStyle(
              backgroundColor: WidgetStateProperty.resolveWith(
                (states) => states.contains(WidgetState.selected)
                    ? widget.accent.withValues(alpha: 0.18)
                    : null,
              ),
            ),
          ),
          const SizedBox(height: 14),
          Expanded(
            child: list.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        emptyText,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          height: 1.6,
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.55),
                        ),
                      ),
                    ),
                  )
                : ListView.separated(
                    itemCount: list.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, i) => _BoardPostCard(
                      post: list[i],
                      isAdmin: false,
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _TradeView extends StatefulWidget {
  final Color accent;
  final List<TradePost> posts;

  const _TradeView({required this.accent, required this.posts});

  @override
  State<_TradeView> createState() => _TradeViewState();
}

enum _TradeSortType { newest, oldest, priceLow, priceHigh }

extension on _TradeSortType {
  String get label {
    switch (this) {
      case _TradeSortType.newest:
        return '최신순';
      case _TradeSortType.oldest:
        return '오래된순';
      case _TradeSortType.priceLow:
        return '가격낮은순';
      case _TradeSortType.priceHigh:
        return '가격높은순';
    }
  }
}

class _TradeViewState extends State<_TradeView> {
  final TextEditingController _searchController = TextEditingController();
  String _query = '';
  _TradeSortType _sort = _TradeSortType.newest;
  final Set<TradeKind> _hiddenKinds = <TradeKind>{};
  bool _hideCompleted = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<TradePost> _filterSort(List<TradePost> posts) {
    var out = posts
        .where((p) => !_hiddenKinds.contains(p.kind))
        .where((p) => !_hideCompleted || p.status != TradeStatus.completed)
        .toList();
    if (_query.trim().isNotEmpty) {
      final q = _query.toLowerCase();
      out = out
          .where((p) =>
              p.title.toLowerCase().contains(q) ||
              p.description.toLowerCase().contains(q) ||
              (p.region ?? '').toLowerCase().contains(q))
          .toList();
    }
    switch (_sort) {
      case _TradeSortType.newest:
        out.sort((a, b) => b.date.compareTo(a.date));
        break;
      case _TradeSortType.oldest:
        out.sort((a, b) => a.date.compareTo(b.date));
        break;
      case _TradeSortType.priceLow:
        out.sort((a, b) => (a.price ?? 0).compareTo(b.price ?? 0));
        break;
      case _TradeSortType.priceHigh:
        out.sort((a, b) => (b.price ?? 0).compareTo(a.price ?? 0));
        break;
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final posts = _filterSort(widget.posts);
    final allOn = _hiddenKinds.isEmpty;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: Column(
            children: [
              TextField(
                controller: _searchController,
                onChanged: (v) => setState(() => _query = v),
                decoration: InputDecoration(
                  hintText: '거래 글 검색',
                  prefixIcon: const Icon(Icons.search_rounded, size: 20),
                  suffixIcon: _query.isEmpty
                      ? null
                      : IconButton(
                          icon: const Icon(Icons.close_rounded, size: 18),
                          onPressed: () {
                            _searchController.clear();
                            setState(() => _query = '');
                          },
                        ),
                  isDense: true,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(
                      color: theme.colorScheme.outlineVariant,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        _TagFilterChip(
                          label: '전체',
                          selected: allOn,
                          color: widget.accent,
                          onTap: () => setState(() => _hiddenKinds.clear()),
                        ),
                        for (final k in TradeKind.values)
                          _TagFilterChip(
                            label: k.label,
                            selected: !_hiddenKinds.contains(k),
                            color: k.color,
                            onTap: () => setState(() {
                              if (_hiddenKinds.contains(k)) {
                                _hiddenKinds.remove(k);
                              } else {
                                _hiddenKinds.add(k);
                              }
                            }),
                          ),
                      ],
                    ),
                  ),
                  PopupMenuButton<_TradeSortType>(
                    tooltip: '정렬',
                    onSelected: (s) => setState(() => _sort = s),
                    itemBuilder: (_) => _TradeSortType.values
                        .map((s) => PopupMenuItem(
                              value: s,
                              child: Text(s.label),
                            ))
                        .toList(),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.sort_rounded, size: 16),
                          const SizedBox(width: 4),
                          Text(
                            _sort.label,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  Switch(
                    value: _hideCompleted,
                    onChanged: (v) => setState(() => _hideCompleted = v),
                  ),
                  const Text('거래완료 숨기기',
                      style: TextStyle(
                          fontSize: 12.5, fontWeight: FontWeight.w700)),
                ],
              ),
            ],
          ),
        ),
        Expanded(
          child: posts.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Text(
                      _query.isEmpty ? '아직 등록된 거래 글이 없어요.' : '검색 결과가 없습니다.',
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                  itemCount: posts.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, i) => _TradePostCard(post: posts[i]),
                ),
        ),
      ],
    );
  }
}

class _TradePostCard extends StatelessWidget {
  final TradePost post;

  const _TradePostCard({required this.post});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final appState = context.read<AppState>();
    final isOwner = appState.isLoggedIn && appState.accountId == post.authorId;
    final isCompleted = post.status == TradeStatus.completed;
    final dateText = '${post.date.year}.${post.date.month}.${post.date.day}';
    final priceText = post.kind == TradeKind.free
        ? '무료'
        : (post.price == null
            ? '가격 미정'
            : '${post.priceCurrencyCode == 'KRW' ? '₩' : ''}${post.price}');

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          context.read<AppState>().incrementTradePostView(post.id);
          showModalBottomSheet<void>(
            context: context,
            isScrollControlled: true,
            shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
            ),
            builder: (sheetCtx) => _TradeDetailSheet(post: post),
          );
        },
        onLongPress: isOwner
            ? () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => TradePostEditorScreen(existing: post),
                  ),
                );
              }
            : null,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (post.imageBytesList.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: Image.memory(
                    post.imageBytesList.first,
                    width: 72,
                    height: 72,
                    fit: BoxFit.cover,
                  ),
                )
              else
                Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child:
                      Icon(Icons.image_outlined, color: Colors.grey.shade400),
                ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: post.kind.color.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            post.kind.label,
                            style: TextStyle(
                              color: post.kind.color,
                              fontSize: 10.5,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.3,
                            ),
                          ),
                        ),
                        if (isCompleted) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 7, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.grey.shade300,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              '거래완료',
                              style: TextStyle(
                                color: Colors.grey.shade700,
                                fontSize: 10.5,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ],
                        const Spacer(),
                        Icon(Icons.visibility_outlined,
                            size: 12, color: Colors.grey.shade500),
                        const SizedBox(width: 3),
                        Text('${post.viewCount}',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey.shade500,
                              fontWeight: FontWeight.w700,
                            )),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      post.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w800,
                        color: isCompleted ? Colors.grey.shade600 : null,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      priceText,
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w900,
                        color: post.kind.color,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        if ((post.region ?? '').isNotEmpty) ...[
                          Icon(Icons.place_outlined,
                              size: 12, color: Colors.grey.shade500),
                          const SizedBox(width: 2),
                          Text(post.region!,
                              style: TextStyle(
                                  fontSize: 11.5, color: Colors.grey.shade600)),
                          const SizedBox(width: 8),
                        ],
                        Text(post.authorName,
                            style: TextStyle(
                                fontSize: 11.5,
                                color: Colors.grey.shade600,
                                fontWeight: FontWeight.w700)),
                        const SizedBox(width: 6),
                        Text(dateText,
                            style: TextStyle(
                                fontSize: 11.5, color: Colors.grey.shade500)),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TradeDetailSheet extends StatelessWidget {
  final TradePost post;

  const _TradeDetailSheet({required this.post});

  Future<void> _openContact(BuildContext context) async {
    final raw = post.contactInfo.trim();
    if (raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    // Try launching as URL if it looks like one.
    if (uri != null && (raw.startsWith('http') || raw.startsWith('https'))) {
      final launched =
          await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('연락 정보: $raw')),
        );
      }
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('연락 정보: $raw')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final priceText = post.kind == TradeKind.free
        ? '무료'
        : (post.price == null
            ? '가격 미정'
            : '${post.priceCurrencyCode == 'KRW' ? '₩' : ''}${post.price}');
    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) => SingleChildScrollView(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: post.kind.color.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    post.kind.label,
                    style: TextStyle(
                      color: post.kind.color,
                      fontSize: 11,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(post.status.label,
                    style: TextStyle(
                        color: Colors.grey.shade600,
                        fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              post.title,
              style: theme.textTheme.titleLarge
                  ?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 4),
            Text(
              priceText,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: post.kind.color,
              ),
            ),
            const SizedBox(height: 16),
            if (post.imageBytesList.isNotEmpty)
              SizedBox(
                height: 220,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: post.imageBytesList.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) => ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child:
                        Image.memory(post.imageBytesList[i], fit: BoxFit.cover),
                  ),
                ),
              ),
            const SizedBox(height: 16),
            if (post.description.isNotEmpty)
              Text(post.description,
                  style: const TextStyle(fontSize: 14, height: 1.5)),
            const SizedBox(height: 16),
            if ((post.region ?? '').isNotEmpty)
              Row(
                children: [
                  const Icon(Icons.place_outlined, size: 18),
                  const SizedBox(width: 6),
                  Text(post.region!,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                ],
              ),
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.person_outline, size: 18),
                const SizedBox(width: 6),
                Text(post.authorName,
                    style: const TextStyle(fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: () => _openContact(context),
              icon: const Icon(Icons.chat_bubble_outline),
              label: const Text('연락하기'),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(46),
              ),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF6E5),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Text(
                '직거래 게시판 — 결제·배송은 당사자 책임. 사기 의심 시 신고해 주세요.',
                style: TextStyle(fontSize: 12, height: 1.4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Event schedule view ─────────────────────────────────────────────────

class _EventScheduleView extends StatefulWidget {
  final Color accent;

  const _EventScheduleView({super.key, required this.accent});

  @override
  State<_EventScheduleView> createState() => _EventScheduleViewState();
}

class _EventScheduleViewState extends State<_EventScheduleView> {
  DateTime _visibleMonth = DateTime(DateTime.now().year, DateTime.now().month);
  DateTime _selectedDate = DateTime(
    DateTime.now().year,
    DateTime.now().month,
    DateTime.now().day,
  );

  List<DateTime> _buildDays(DateTime month) {
    final first = DateTime(month.year, month.month, 1);
    final leadingDays = first.weekday % 7;
    final start = first.subtract(Duration(days: leadingDays));
    return List<DateTime>.generate(42, (i) => start.add(Duration(days: i)));
  }

  bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final days = _buildDays(_visibleMonth);
    final accent = widget.accent;

    final eventsForSelectedDay =
        kEventNotices.where((e) => e.occursOn(_selectedDate)).toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        Card(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: BorderSide(color: theme.colorScheme.outlineVariant),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                Row(
                  children: [
                    IconButton(
                      onPressed: () => setState(() {
                        _visibleMonth = DateTime(
                          _visibleMonth.year,
                          _visibleMonth.month - 1,
                        );
                      }),
                      icon: const Icon(Icons.chevron_left_rounded),
                    ),
                    Expanded(
                      child: Text(
                        '${_visibleMonth.year}년 ${_visibleMonth.month}월',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => setState(() {
                        _visibleMonth = DateTime(
                          _visibleMonth.year,
                          _visibleMonth.month + 1,
                        );
                      }),
                      icon: const Icon(Icons.chevron_right_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Row(
                  children: [
                    _WeekLabel('일'),
                    _WeekLabel('월'),
                    _WeekLabel('화'),
                    _WeekLabel('수'),
                    _WeekLabel('목'),
                    _WeekLabel('금'),
                    _WeekLabel('토'),
                  ],
                ),
                const SizedBox(height: 6),
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: days.length,
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 7,
                    crossAxisSpacing: 4,
                    mainAxisSpacing: 4,
                    childAspectRatio: 0.95,
                  ),
                  itemBuilder: (context, index) {
                    final day = days[index];
                    final inMonth = day.month == _visibleMonth.month;
                    final isSelected = _sameDay(day, _selectedDate);
                    final hasEvent = kEventNotices.any((e) => e.occursOn(day));

                    return InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => setState(() => _selectedDate = day),
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          color: isSelected
                              ? accent.withValues(alpha: 0.18)
                              : Colors.transparent,
                          border: Border.all(
                            color: isSelected
                                ? accent.withValues(alpha: 0.40)
                                : Colors.transparent,
                          ),
                        ),
                        child: Column(
                          children: [
                            Text(
                              '${day.day}',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w700,
                                color: inMonth
                                    ? theme.colorScheme.onSurface
                                    : theme.colorScheme.onSurface
                                        .withValues(alpha: 0.35),
                              ),
                            ),
                            const Spacer(),
                            if (hasEvent)
                              Container(
                                width: 6,
                                height: 6,
                                margin: const EdgeInsets.only(bottom: 2),
                                decoration: BoxDecoration(
                                  color: accent,
                                  shape: BoxShape.circle,
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          _selectedDate.year == DateTime.now().year
              ? '${_selectedDate.month}월 ${_selectedDate.day}일 행사'
              : '${_selectedDate.year}년 ${_selectedDate.month}월 ${_selectedDate.day}일 행사',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 10),
        if (eventsForSelectedDay.isEmpty)
          Card(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: theme.colorScheme.outlineVariant),
            ),
            child: const Padding(
              padding: EdgeInsets.all(18),
              child: Center(child: Text('이 날 등록된 행사가 없습니다.')),
            ),
          )
        else
          ...eventsForSelectedDay.map(
            (event) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _EventNoticeCard(notice: event, accent: accent),
            ),
          ),
      ],
    );
  }
}

class _EventNoticeCard extends StatelessWidget {
  final EventNotice notice;
  final Color accent;

  const _EventNoticeCard({required this.notice, required this.accent});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dateText = notice.endDate == null
        ? '${notice.date.year}.${notice.date.month}.${notice.date.day}'
        : '${notice.date.month}.${notice.date.day} - '
            '${notice.endDate!.month}.${notice.endDate!.day}';

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => NewsDetailScreen(
                title: notice.title,
                date: dateText,
                content: notice.content,
              ),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: accent.withValues(alpha: 0.30)),
                ),
                child: Icon(Icons.event_rounded, color: accent),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      notice.title,
                      style: const TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w800,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      dateText,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: accent,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      notice.summary,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 12.5,
                        color: Colors.grey.shade700,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: Colors.grey),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Board post detail with image + source link ──────────────────────────

class _BoardPostDetailScreen extends StatefulWidget {
  final BoardPost post;

  const _BoardPostDetailScreen({required this.post});

  @override
  State<_BoardPostDetailScreen> createState() => _BoardPostDetailScreenState();
}

class _BoardPostDetailScreenState extends State<_BoardPostDetailScreen> {
  bool _showOriginal = false;
  bool _translating = false;
  String? _translationError;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _maybeTranslate();
    });
  }

  Future<void> _maybeTranslate() async {
    if (!mounted) return;
    final appState = context.read<AppState>();
    final code = appState.appLanguage.translationCode;
    final cached = appState.cachedTranslationFor(widget.post.id, code);
    if (cached != null) return;
    if (!appState.hasClaudeApiKey) return;
    setState(() => _translating = true);
    final result = await appState.translateBoardPost(widget.post, code);
    if (!mounted) return;
    setState(() {
      _translating = false;
      _translationError = result == null ? '번역에 실패했어요.' : null;
    });
  }

  Future<void> _openSource(BuildContext context) async {
    final url = widget.post.sourceUrl;
    if (url == null) return;
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!launched && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('출처를 열 수 없어요: $url')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final post = widget.post;
    final appState = context.watch<AppState>();
    final code = appState.appLanguage.translationCode;
    final cached = appState.cachedTranslationFor(post.id, code);
    final hasTranslation = cached != null;
    final showTranslated = hasTranslation && !_showOriginal;
    final canManagePost = !appState.readOnlyPublicSite &&
        (appState.adminMode ||
            ((post.authorId != null &&
                    post.authorId == appState.stableAuthorId) ||
                (post.author == appState.displayName.trim() &&
                    appState.isLoggedIn)));

    final title = showTranslated ? cached.title : post.title;
    final content = showTranslated ? cached.content : post.content;
    final dateText = _formatBoardDateTime(post.date);
    final edited = _isEdited(post.date, post.updatedAt);

    return Scaffold(
      appBar: AppBar(
        title: const Text('게시글'),
        actions: [
          if (canManagePost)
            IconButton(
              tooltip: '수정',
              icon: const Icon(Icons.edit_outlined),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => BoardPostEditorScreen(existing: post),
                  ),
                );
              },
            ),
          if (canManagePost)
            IconButton(
              tooltip: '삭제',
              icon: const Icon(Icons.delete_outline),
              onPressed: () async {
                final confirmed = await showDialog<bool>(
                  context: context,
                  builder: (dctx) => AlertDialog(
                    title: const Text('게시글 삭제'),
                    content: Text(
                      '"${post.title}" 글을 삭제할까요?\n삭제한 글은 복구할 수 없어요.',
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(dctx, false),
                        child: const Text('취소'),
                      ),
                      FilledButton(
                        style: FilledButton.styleFrom(
                          backgroundColor: Theme.of(dctx).colorScheme.error,
                        ),
                        onPressed: () => Navigator.pop(dctx, true),
                        child: const Text('삭제'),
                      ),
                    ],
                  ),
                );
                if (confirmed == true && context.mounted) {
                  context.read<AppState>().deleteBoardPost(post.id);
                  Navigator.pop(context);
                }
              },
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_translating)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(
                children: [
                  SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  SizedBox(width: 10),
                  Text('번역 중…', style: TextStyle(fontSize: 12.5)),
                ],
              ),
            ),
          if (_translationError != null && !_translating)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Text(
                _translationError!,
                style: TextStyle(color: Colors.red.shade800, fontSize: 12.5),
              ),
            ),
          if (hasTranslation)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _showOriginal
                              ? Icons.subject_rounded
                              : Icons.translate_rounded,
                          size: 13,
                          color: theme.colorScheme.primary,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          _showOriginal
                              ? '원문'
                              : '${appState.appLanguage.label}로 번역됨',
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w700,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  TextButton.icon(
                    onPressed: () =>
                        setState(() => _showOriginal = !_showOriginal),
                    icon: Icon(
                      _showOriginal
                          ? Icons.translate_rounded
                          : Icons.subject_rounded,
                      size: 14,
                    ),
                    label: Text(
                      _showOriginal ? '번역 보기' : '원문 보기',
                      style: const TextStyle(fontSize: 12),
                    ),
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 0),
                      minimumSize: const Size(0, 28),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  ),
                ],
              ),
            ),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: post.tag.color.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  post.tag.label,
                  style: TextStyle(
                    color: post.tag.color,
                    fontSize: 11,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(post.author,
                  style: TextStyle(
                      color: Colors.grey.shade700,
                      fontWeight: FontWeight.w700)),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  edited ? '작성 $dateText · 수정됨' : '작성 $dateText',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: Colors.grey.shade500, fontSize: 12.5),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            title,
            style: theme.textTheme.headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800, height: 1.3),
          ),
          const SizedBox(height: 14),
          if (post.imageBytes != null ||
              (post.imageUrl?.trim().isNotEmpty ?? false))
            _BoardPostImage(
              post: post,
              width: double.infinity,
              borderRadius: BorderRadius.circular(14),
            ),
          if (post.imageBytes != null ||
              (post.imageUrl?.trim().isNotEmpty ?? false))
            const SizedBox(height: 14),
          Text(
            content,
            style: theme.textTheme.bodyLarge?.copyWith(height: 1.65),
          ),
          if (post.sourceUrl != null) ...[
            const SizedBox(height: 18),
            OutlinedButton.icon(
              onPressed: () => _openSource(context),
              icon: const Icon(Icons.open_in_new_rounded, size: 16),
              label: Text(
                '출처 열기 — ${post.sourceUrl}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
          const SizedBox(height: 20),
          _PostActionBar(post: post),
          const SizedBox(height: 20),
          _PostCommentsSection(postId: post.id),
        ],
      ),
    );
  }
}

class _PostActionBar extends StatelessWidget {
  final BoardPost post;
  const _PostActionBar({required this.post});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final appState = context.watch<AppState>();
    final liked = appState.isPostLiked(post.id);
    final saved = appState.isPostBookmarked(post.id);
    final likeCount = appState.likeCountFor(post.id);
    final commentCount = appState.commentCountFor(post.id);
    final canInteract = !appState.readOnlyPublicSite && appState.isLoggedIn;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: canInteract
                ? () => appState.togglePostLike(post.id)
                : null,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              child: Row(
                children: [
                  Icon(
                    liked ? Icons.favorite : Icons.favorite_border,
                    size: 18,
                    color: liked ? Colors.pink : Colors.grey.shade600,
                  ),
                  const SizedBox(width: 4),
                  Text('$likeCount',
                      style: const TextStyle(
                          fontWeight: FontWeight.w700, fontSize: 13)),
                ],
              ),
            ),
          ),
          const SizedBox(width: 12),
          Row(
            children: [
              Icon(Icons.mode_comment_outlined,
                  size: 17, color: Colors.grey.shade600),
              const SizedBox(width: 4),
              Text('$commentCount',
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 13)),
            ],
          ),
          const Spacer(),
          InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: canInteract
                ? () => appState.togglePostBookmark(post.id)
                : null,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              child: Icon(
                saved ? Icons.bookmark_rounded : Icons.bookmark_border_rounded,
                size: 20,
                color: saved ? theme.colorScheme.primary : Colors.grey.shade600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PostCommentsSection extends StatefulWidget {
  final String postId;
  const _PostCommentsSection({required this.postId});

  @override
  State<_PostCommentsSection> createState() => _PostCommentsSectionState();
}

class _PostCommentsSectionState extends State<_PostCommentsSection> {
  final TextEditingController _commentController = TextEditingController();
  bool _isRefreshingComments = false;
  DateTime? _lastRefreshedAt;

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (context.read<AppState>().commentsFor(widget.postId).isEmpty) {
        _refreshComments();
      }
    });
  }

  Future<void> _refreshComments() async {
    if (_isRefreshingComments) return;
    setState(() => _isRefreshingComments = true);
    try {
      await context.read<AppState>().refreshBoardPostComments(widget.postId);
      if (!mounted) return;
      setState(() {
        _lastRefreshedAt = DateTime.now();
      });
    } finally {
      if (mounted) {
        setState(() => _isRefreshingComments = false);
      }
    }
  }

  void _submit() {
    final text = _commentController.text.trim();
    if (text.isEmpty) return;
    context.read<AppState>().addComment(widget.postId, text);
    _commentController.clear();
    FocusScope.of(context).unfocus();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final appState = context.watch<AppState>();
    final readOnly = appState.readOnlyPublicSite;
    final comments = appState.commentsFor(widget.postId);
    final commentCount = appState.commentCountFor(widget.postId);
    final commentRefreshText = _isRefreshingComments
        ? '댓글을 확인하는 중이에요...'
        : _lastRefreshedAt == null
            ? '필요할 때만 새로고침합니다.'
            : '마지막 확인 ${_formatRefreshStatusTime(_lastRefreshedAt!)}';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.mode_comment_outlined, size: 18),
            const SizedBox(width: 6),
            Text(
              '댓글 $commentCount',
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const Spacer(),
            TextButton.icon(
              onPressed: _isRefreshingComments ? null : _refreshComments,
              icon: _isRefreshingComments
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.refresh_rounded, size: 16),
              label: Text(_isRefreshingComments ? '확인 중' : '새로고침'),
              style: TextButton.styleFrom(
                visualDensity: VisualDensity.compact,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          commentRefreshText,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 10),
        if (!readOnly && (appState.isLoggedIn || appState.adminMode))
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: TextField(
                  controller: _commentController,
                  maxLines: 3,
                  minLines: 1,
                  textInputAction: TextInputAction.newline,
                  decoration: const InputDecoration(
                    hintText: '댓글을 남겨주세요',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: _submit,
                child: const Text('등록'),
              ),
            ],
          )
        else
          Text(
            '로그인 후 댓글을 남길 수 있어요.',
            style: TextStyle(
                fontSize: 12.5,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
          ),
        const SizedBox(height: 14),
        if (comments.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 20),
            child: Center(
              child: Text(
                '아직 댓글이 없어요. 첫 댓글을 남겨주세요.',
                style: TextStyle(
                  fontSize: 12.5,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.55),
                ),
              ),
            ),
          )
        else
          for (final c in comments.reversed)
            _CommentTile(
              comment: c,
              canDelete: !readOnly &&
                  (appState.adminMode || c.authorId == appState.stableAuthorId),
              onDelete: () => appState.deleteComment(widget.postId, c.id),
            ),
      ],
    );
  }
}

class _CommentTile extends StatelessWidget {
  final BoardComment comment;
  final bool canDelete;
  final VoidCallback onDelete;
  const _CommentTile({
    required this.comment,
    required this.canDelete,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dateText = _formatBoardDateTime(comment.date);
    final edited = comment.edited || _isEdited(comment.date, comment.updatedAt);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: theme.colorScheme.primary.withValues(alpha: 0.18),
            child: Text(
              comment.author.isEmpty ? '?' : comment.author.characters.first,
              style: TextStyle(
                fontWeight: FontWeight.w800,
                color: theme.colorScheme.primary,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      comment.author,
                      style: const TextStyle(
                          fontWeight: FontWeight.w800, fontSize: 13),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      edited ? '$dateText · 수정됨' : dateText,
                      style: TextStyle(
                          fontSize: 11,
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.5)),
                    ),
                    const Spacer(),
                    if (canDelete)
                      InkWell(
                        onTap: onDelete,
                        borderRadius: BorderRadius.circular(6),
                        child: Padding(
                          padding: const EdgeInsets.all(4),
                          child: Icon(Icons.close_rounded,
                              size: 14, color: Colors.grey.shade500),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  comment.content,
                  style: const TextStyle(fontSize: 13.5, height: 1.45),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _WeekLabel extends StatelessWidget {
  final String text;

  const _WeekLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Center(
          child: Text(
            text,
            style: TextStyle(
              color: Colors.grey.shade600,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }
}
