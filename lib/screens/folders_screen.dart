import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_item.dart';
import '../config/monetization_catalog.dart';
import '../services/ad_service.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_header_title.dart';
import 'add_goods_screen.dart';
import 'folder_detail_screen.dart';
import 'folder_editor_screen.dart';
import 'goods_search_screen.dart';

class FoldersScreen extends StatefulWidget {
  const FoldersScreen({super.key});

  @override
  State<FoldersScreen> createState() => _FoldersScreenState();
}

class _FoldersScreenState extends State<FoldersScreen> {
  FolderItem? selectedFolder;
  final List<FolderItem> _folderHistory = [];
  bool favoritesOnly = false;
  bool fabExpanded = false;
  bool folderSelectionMode = false;
  final Set<String> selectedFolderIds = {};

  void _showLoginRequired() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('로그인하세요. 게스트 계정으로는 폴더와 굿즈를 추가할 수 없습니다.'),
      ),
    );
  }

  List<FolderItem> _sortedFolders(AppState appState, List<FolderItem> source) {
    final copied = [...source];
    switch (appState.folderSortType) {
      case FolderSortType.nameAsc:
        copied.sort((a, b) => a.name.compareTo(b.name));
        break;
      case FolderSortType.goodsCountDesc:
        copied.sort((a, b) {
          final aCount = a.isGroup
              ? _groupGoodsCount(appState, a.id)
              : appState.goodsCountForFolder(a.id);
          final bCount = b.isGroup
              ? _groupGoodsCount(appState, b.id)
              : appState.goodsCountForFolder(b.id);
          return bCount.compareTo(aCount);
        });
        break;
    }
    return copied;
  }

  int _groupGoodsCount(AppState appState, String groupId) {
    final childIds = appState.folders
        .where((folder) => folder.parentId == groupId && !folder.isGroup)
        .map((folder) => folder.id)
        .toSet();
    return appState.goodsItems.where((item) => childIds.contains(item.folderId)).length;
  }

  int _groupChildCount(AppState appState, String groupId) {
    return appState.folders.where((folder) => folder.parentId == groupId).length;
  }

  List<FolderItem> _foldersForLevel(AppState appState, String? parentId) {
    final folders =
        appState.folders.where((folder) => folder.parentId == parentId).toList();
    return _sortedFolders(appState, folders);
  }

  String? get _currentParentId => selectedFolder?.id;

  Set<String>? _searchableFolderIds(AppState appState) {
    if (favoritesOnly) return null;

    if (selectedFolder == null) {
      return appState.folders
          .where((folder) => !folder.isGroup)
          .map((folder) => folder.id)
          .toSet();
    }

    if (selectedFolder!.isGroup) {
      return appState.folders
          .where((folder) => folder.parentId == selectedFolder!.id && !folder.isGroup)
          .map((folder) => folder.id)
          .toSet();
    }

    return {selectedFolder!.id};
  }

  Future<void> openGoodsSearch(BuildContext context, AppState appState) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => GoodsSearchScreen(
          folder: selectedFolder != null && !selectedFolder!.isGroup
              ? selectedFolder
              : null,
          favoritesOnly: favoritesOnly,
          folderIds: _searchableFolderIds(appState),
        ),
      ),
    );
  }

  Set<String> _descendantIds(AppState appState, Set<String> rootIds) {
    final descendants = <String>{};
    final queue = <String>[...rootIds];

    while (queue.isNotEmpty) {
      final current = queue.removeLast();
      for (final folder in appState.folders.where((item) => item.parentId == current)) {
        if (descendants.add(folder.id)) {
          queue.add(folder.id);
        }
      }
    }

    return descendants;
  }

  Future<void> openMoveFoldersDialog(AppState appState) async {
    String? selectedParentId = _currentParentId;
    final blockedIds = {
      ...selectedFolderIds,
      ..._descendantIds(appState, selectedFolderIds),
    };
    final selectedFolders = appState.folders
        .where((folder) => selectedFolderIds.contains(folder.id))
        .toList();
    final containsGroupFolder = selectedFolders.any((folder) => folder.isGroup);
    final targetGroups = _sortedFolders(
      appState,
      appState.folders
          .where(
            (folder) =>
                !containsGroupFolder &&
                folder.isGroup &&
                !blockedIds.contains(folder.id),
          )
          .toList(),
    );

    await showDialog(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('폴더 이동'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  RadioListTile<String?>(
                    value: null,
                    groupValue: selectedParentId,
                    title: const Text('폴더'),
                    onChanged: (value) {
                      setDialogState(() {
                        selectedParentId = value;
                      });
                    },
                  ),
                  if (containsGroupFolder)
                    const Padding(
                      padding: EdgeInsets.fromLTRB(16, 4, 16, 8),
                      child: Text(
                        '그룹폴더는 다른 그룹폴더 안으로 이동할 수 없습니다.',
                        style: TextStyle(fontSize: 13),
                      ),
                    ),
                  ...targetGroups.map(
                    (folder) => RadioListTile<String?>(
                      value: folder.id,
                      groupValue: selectedParentId,
                      title: Text(folder.name),
                      onChanged: (value) {
                        setDialogState(() {
                          selectedParentId = value;
                        });
                      },
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () {
                    appState.moveFoldersToParent(selectedFolderIds, selectedParentId);
                    Navigator.pop(dialogContext);
                    _exitFolderSelection();
                  },
                  child: const Text('이동'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> openFolderEditor(
    BuildContext context, {
    FolderItem? initialFolder,
    required bool isGroup,
  }) async {
    final appState = context.read<AppState>();
    if (!appState.isLoggedIn) {
      _showLoginRequired();
      return;
    }

    final result = await Navigator.push<FolderItem>(
      context,
      MaterialPageRoute(
        builder: (_) => FolderEditorScreen(
          initialFolder: initialFolder,
          isGroup: isGroup,
        ),
      ),
    );

    if (result == null) return;

    final nextFolder = result.copyWith(
      id: initialFolder?.id ?? appState.makeId(),
      parentId: initialFolder != null
          ? initialFolder.parentId
          : (selectedFolder != null && selectedFolder!.isGroup && !isGroup
              ? selectedFolder!.id
              : null),
    );

    if (initialFolder == null) {
      appState.addFolder(nextFolder);
      await AdService.instance.showInterstitialIfReady(
        AdPlacement.folderInterstitial,
        appState,
      );
    } else {
      appState.updateFolder(nextFolder);
    }
  }

  void openFolder(FolderItem folder) {
    if (folderSelectionMode) {
      _toggleFolderSelection(folder.id);
      return;
    }

    setState(() {
      if (selectedFolder != null) {
        _folderHistory.add(selectedFolder!);
      }
      selectedFolder = folder;
      favoritesOnly = false;
      fabExpanded = false;
    });
  }

  void openFavorites() {
    setState(() {
      selectedFolder = null;
      _folderHistory.clear();
      favoritesOnly = true;
      fabExpanded = false;
      folderSelectionMode = false;
      selectedFolderIds.clear();
    });
  }

  void closeDetail() {
    setState(() {
      if (favoritesOnly) {
        selectedFolder = null;
        favoritesOnly = false;
        _folderHistory.clear();
      } else if (_folderHistory.isNotEmpty) {
        selectedFolder = _folderHistory.removeLast();
      } else {
        selectedFolder = null;
        favoritesOnly = false;
      }
      fabExpanded = false;
      folderSelectionMode = false;
      selectedFolderIds.clear();
    });
  }

  void _toggleFolderSelection(String id) {
    setState(() {
      if (selectedFolderIds.contains(id)) {
        selectedFolderIds.remove(id);
      } else {
        selectedFolderIds.add(id);
      }
    });
  }

  void _exitFolderSelection() {
    setState(() {
      folderSelectionMode = false;
      selectedFolderIds.clear();
    });
  }

  void _selectAllVisibleFolders(List<FolderItem> folders) {
    setState(() {
      selectedFolderIds
        ..clear()
        ..addAll(folders.map((folder) => folder.id));
    });
  }

  Future<void> openAddGoods(BuildContext context, FolderItem folder) async {
    final appState = context.read<AppState>();
    if (!appState.isLoggedIn) {
      _showLoginRequired();
      return;
    }

    final result = await Navigator.push<GoodsItem>(
      context,
      MaterialPageRoute(
        builder: (_) => AddGoodsScreen(folder: folder),
      ),
    );

    if (result != null) {
      appState.addGoods(result);
      await AdService.instance.showInterstitialIfReady(
        AdPlacement.folderInterstitial,
        appState,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final favoriteCount = appState.favoriteGoods().length;
        final inDetail = selectedFolder != null || favoritesOnly;
        final topFolders = _foldersForLevel(appState, null);
        final childFolders = selectedFolder != null
            ? _foldersForLevel(appState, selectedFolder!.id)
            : <FolderItem>[];
        final visibleFolders = selectedFolder == null ? topFolders : childFolders;
        final showTopActionBar =
            !favoritesOnly && (selectedFolder == null || selectedFolder!.isGroup);

        return Scaffold(
          appBar: AppBar(
            title: const DeokiveHeaderTitle(),
            leading: inDetail
                ? IconButton(
                    onPressed: closeDetail,
                    icon: const Icon(Icons.arrow_back),
                  )
                : null,
            actions: favoritesOnly ? null : const [],
          ),
          floatingActionButton: _buildFab(context),
          body: Column(
            children: [
              if (showTopActionBar)
                _FolderTopActionBarFixed(
                  selectionMode: folderSelectionMode,
                  hasItems: visibleFolders.isNotEmpty,
                  hasSelection: selectedFolderIds.isNotEmpty,
                  allSelected: visibleFolders.isNotEmpty &&
                      selectedFolderIds.length == visibleFolders.length,
                  onSelectTap: () {
                    setState(() {
                      folderSelectionMode = true;
                      selectedFolderIds.clear();
                    });
                  },
                  onSelectAllTap: () => _selectAllVisibleFolders(visibleFolders),
                  onCancelTap: _exitFolderSelection,
                  onMoveTap: () => openMoveFoldersDialog(appState),
                  onSearchTap: () => openGoodsSearch(context, appState),
                  onSortSelected: appState.setFolderSortType,
                ),
              Expanded(
                child: favoritesOnly
                    ? FolderDetailContent(
                        folder: null,
                        favoritesOnly: true,
                        onBack: closeDetail,
                      )
                    : selectedFolder != null && !selectedFolder!.isGroup
                        ? FolderDetailContent(
                            folder: selectedFolder,
                            favoritesOnly: false,
                            onBack: closeDetail,
                          )
                        : Center(
                            child: ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 1300),
                              child: GridView.builder(
                                padding: const EdgeInsets.all(16),
                                itemCount: selectedFolder == null
                                    ? topFolders.length + 1
                                    : childFolders.length,
                                gridDelegate:
                                    const SliverGridDelegateWithMaxCrossAxisExtent(
                                  maxCrossAxisExtent: 220,
                                  mainAxisSpacing: 12,
                                  crossAxisSpacing: 12,
                                  childAspectRatio: 1,
                                ),
                                itemBuilder: (context, index) {
                                  if (selectedFolder == null && index == 0) {
                                    return _SpecialFolderCard(
                                      title: '좋아요',
                                      subtitle: '$favoriteCount개',
                                      icon: Icons.favorite,
                                      color: const Color(0xFFF28482),
                                      onTap: openFavorites,
                                    );
                                  }

                                  final folder = selectedFolder == null
                                      ? topFolders[index - 1]
                                      : childFolders[index];
                                  final subtitle = folder.isGroup
                                      ? '하위 ${_groupChildCount(appState, folder.id)}개'
                                      : '${appState.goodsCountForFolder(folder.id)}개';
                                  final isSelected =
                                      selectedFolderIds.contains(folder.id);

                                  return _FolderGridCard(
                                    folder: folder,
                                    subtitle: subtitle,
                                    selectionMode: folderSelectionMode,
                                    selected: isSelected,
                                    onTap: () => openFolder(folder),
                                    onEdit: () => openFolderEditor(
                                      context,
                                      initialFolder: folder,
                                      isGroup: folder.isGroup,
                                    ),
                                  );
                                },
                              ),
                            ),
                          ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget? _buildFab(BuildContext context) {
    if (favoritesOnly || folderSelectionMode) return null;

    if (selectedFolder != null && selectedFolder!.isGroup) {
      return _ExpandableCircleFab(
        expanded: fabExpanded,
        mainIcon: Icons.folder_rounded,
        actions: [
          _CircleFabAction(
            icon: Icons.create_new_folder_outlined,
            label: '폴더 생성',
            onTap: () async {
              setState(() {
                fabExpanded = false;
              });
              await openFolderEditor(context, isGroup: false);
            },
          ),
        ],
        onMainTap: () {
          setState(() {
            fabExpanded = !fabExpanded;
          });
        },
      );
    }

    if (selectedFolder != null && !selectedFolder!.isGroup) {
      return _ExpandableCircleFab(
        expanded: fabExpanded,
        mainIcon: Icons.inventory_2_rounded,
        actions: [
          _CircleFabAction(
            icon: Icons.add_box_outlined,
            label: '굿즈 생성',
            onTap: () async {
              setState(() {
                fabExpanded = false;
              });
              await openAddGoods(context, selectedFolder!);
            },
          ),
        ],
        onMainTap: () {
          setState(() {
            fabExpanded = !fabExpanded;
          });
        },
      );
    }

    return _ExpandableCircleFab(
      expanded: fabExpanded,
      mainIcon: Icons.folder_rounded,
      actions: [
        _CircleFabAction(
          icon: Icons.create_new_folder_outlined,
          label: '폴더 생성',
          onTap: () async {
            setState(() {
              fabExpanded = false;
            });
            await openFolderEditor(context, isGroup: false);
          },
        ),
        _CircleFabAction(
          icon: Icons.folder_copy_outlined,
          label: '그룹폴더 생성',
          onTap: () async {
            setState(() {
              fabExpanded = false;
            });
            await openFolderEditor(context, isGroup: true);
          },
        ),
      ],
      onMainTap: () {
        setState(() {
          fabExpanded = !fabExpanded;
        });
      },
    );
  }
}

class _FolderTopActionBar extends StatelessWidget {
  final bool selectionMode;
  final bool hasItems;
  final bool hasSelection;
  final bool allSelected;
  final VoidCallback onSelectTap;
  final VoidCallback onSelectAllTap;
  final VoidCallback onCancelTap;
  final VoidCallback onMoveTap;
  final VoidCallback onSearchTap;
  final ValueChanged<FolderSortType> onSortSelected;

  const _FolderTopActionBar({
    required this.selectionMode,
    required this.hasItems,
    required this.hasSelection,
    required this.allSelected,
    required this.onSelectTap,
    required this.onSelectAllTap,
    required this.onCancelTap,
    required this.onMoveTap,
    required this.onSearchTap,
    required this.onSortSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      decoration: BoxDecoration(
        color: theme.scaffoldBackgroundColor,
        border: Border(
          bottom: BorderSide(color: theme.colorScheme.outline.withValues(alpha: 0.4)),
        ),
      ),
      child: Row(
        children: [
          IconButton(
            tooltip: '굿즈 검색',
            onPressed: onSearchTap,
            icon: const Icon(Icons.search_rounded),
          ),
          const Spacer(),
          PopupMenuButton<FolderSortType>(
            tooltip: '정렬',
            onSelected: onSortSelected,
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: FolderSortType.nameAsc,
                child: Text('가나다순'),
              ),
              PopupMenuItem(
                value: FolderSortType.goodsCountDesc,
                child: Text('굿즈 많은순'),
              ),
            ],
            icon: const Icon(Icons.sort),
          ),
          if (!selectionMode)
            TextButton(
              onPressed: hasItems ? onSelectTap : null,
              child: const Text('선택'),
            ),
          if (selectionMode) ...[
            TextButton(
              onPressed: onCancelTap,
              child: const Text('취소'),
            ),
            IconButton(
              tooltip: '폴더 이동',
              onPressed: hasSelection ? onMoveTap : null,
              icon: const Icon(Icons.drive_file_move_outline),
            ),
          ],
        ],
      ),
    );
  }
}

class _FolderTopActionBarFixed extends StatelessWidget {
  final bool selectionMode;
  final bool hasItems;
  final bool hasSelection;
  final bool allSelected;
  final VoidCallback onSelectTap;
  final VoidCallback onSelectAllTap;
  final VoidCallback onCancelTap;
  final VoidCallback onMoveTap;
  final VoidCallback onSearchTap;
  final ValueChanged<FolderSortType> onSortSelected;

  const _FolderTopActionBarFixed({
    required this.selectionMode,
    required this.hasItems,
    required this.hasSelection,
    required this.allSelected,
    required this.onSelectTap,
    required this.onSelectAllTap,
    required this.onCancelTap,
    required this.onMoveTap,
    required this.onSearchTap,
    required this.onSortSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      decoration: BoxDecoration(
        color: theme.scaffoldBackgroundColor,
        border: Border(
          bottom: BorderSide(
            color: theme.colorScheme.outline.withValues(alpha: 0.4),
          ),
        ),
      ),
      child: Row(
        children: [
          IconButton(
            tooltip: '굿즈 검색',
            onPressed: onSearchTap,
            icon: const Icon(Icons.search_rounded),
          ),
          const Spacer(),
          PopupMenuButton<FolderSortType>(
            tooltip: '정렬',
            onSelected: onSortSelected,
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: FolderSortType.nameAsc,
                child: Text('가나다순'),
              ),
              PopupMenuItem(
                value: FolderSortType.goodsCountDesc,
                child: Text('굿즈 많은순'),
              ),
            ],
            icon: const Icon(Icons.sort),
          ),
          if (!selectionMode)
            TextButton(
              onPressed: hasItems ? onSelectTap : null,
              child: const Text('선택'),
            ),
          if (selectionMode) ...[
            TextButton(
              onPressed: hasItems ? onSelectAllTap : null,
              child: Text(allSelected ? '전체선택됨' : '전체선택'),
            ),
            TextButton(
              onPressed: onCancelTap,
              child: const Text('취소'),
            ),
            IconButton(
              tooltip: '폴더 이동',
              onPressed: hasSelection ? onMoveTap : null,
              icon: const Icon(Icons.drive_file_move_outline),
            ),
          ],
        ],
      ),
    );
  }
}

class _FolderGridCard extends StatelessWidget {
  final FolderItem folder;
  final String subtitle;
  final bool selectionMode;
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback onEdit;

  const _FolderGridCard({
    required this.folder,
    required this.subtitle,
    required this.selectionMode,
    required this.selected,
    required this.onTap,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final onSurfaceColor = theme.colorScheme.onSurface;

    return InkWell(
      borderRadius: BorderRadius.circular(24),
      onTap: onTap,
      child: Ink(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: LinearGradient(
            colors: [
              folder.color.withValues(alpha: 0.14),
              theme.colorScheme.surface,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: Border.all(
            color: selected
                ? theme.colorScheme.primary
                : folder.color.withValues(alpha: 0.22),
            width: selected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: folder.color.withValues(alpha: 0.08),
              blurRadius: 14,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Stack(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: folder.color.withValues(alpha: 0.18),
                    child: Icon(
                      folder.icon,
                      color: folder.color,
                      size: 25,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    folder.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      height: 1.25,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Colors.grey.shade700,
                    ),
                  ),
                ],
              ),
            ),
            if (!selectionMode)
              Positioned(
                top: 8,
                right: 8,
                child: IconButton(
                  onPressed: onEdit,
                  style: IconButton.styleFrom(
                    backgroundColor: Colors.transparent,
                    shadowColor: Colors.transparent,
                  ),
                  icon: const Icon(Icons.edit_outlined, size: 18),
                ),
              ),
            if (selectionMode)
              Positioned(
                top: 10,
                right: 10,
                child: CircleAvatar(
                  radius: 14,
                  backgroundColor: selected
                      ? theme.colorScheme.primary
                      : theme.colorScheme.surface.withValues(alpha: 0.9),
                  child: Icon(
                    selected ? Icons.check : Icons.circle_outlined,
                    size: 16,
                    color: selected
                        ? theme.colorScheme.onPrimary
                        : onSurfaceColor.withValues(alpha: 0.6),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SpecialFolderCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _SpecialFolderCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return InkWell(
      borderRadius: BorderRadius.circular(24),
      onTap: onTap,
      child: Ink(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: LinearGradient(
            colors: [
              color.withValues(alpha: 0.14),
              theme.colorScheme.surface,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: Border.all(color: color.withValues(alpha: 0.22)),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.08),
              blurRadius: 14,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: color.withValues(alpha: 0.18),
                child: Icon(
                  icon,
                  color: color,
                  size: 25,
                ),
              ),
              const Spacer(),
              Text(
                title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  height: 1.25,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey.shade700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CircleFabAction {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _CircleFabAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });
}

class _ExpandableCircleFab extends StatelessWidget {
  final bool expanded;
  final IconData mainIcon;
  final List<_CircleFabAction> actions;
  final VoidCallback onMainTap;

  const _ExpandableCircleFab({
    required this.expanded,
    required this.mainIcon,
    required this.actions,
    required this.onMainTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;

    Widget buildMiniFab(_CircleFabAction action) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: palette.primary.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              action.label,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 8),
          FloatingActionButton.small(
            heroTag: null,
            elevation: 0,
            backgroundColor: palette.primary.withValues(alpha: 0.78),
            foregroundColor: palette.text,
            shape: const CircleBorder(),
            onPressed: action.onTap,
            child: Icon(action.icon),
          ),
        ],
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: expanded
              ? Column(
                  key: const ValueKey('circle-fab-actions'),
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    for (final action in actions.reversed) ...[
                      buildMiniFab(action),
                      const SizedBox(height: 10),
                    ],
                  ],
                )
              : const SizedBox.shrink(),
        ),
        FloatingActionButton(
          elevation: 0,
          backgroundColor: palette.primary.withValues(alpha: 0.78),
          foregroundColor: theme.colorScheme.onPrimary,
          shape: const CircleBorder(),
          onPressed: onMainTap,
          child: Icon(expanded ? Icons.close : mainIcon),
        ),
      ],
    );
  }
}
