import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_item.dart';
import '../state/app_state.dart';
import '../utils/csv_exporter.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_header_title.dart';
import 'add_goods_screen.dart';
import 'catalog_database_screen.dart';
import 'folder_detail_screen.dart';
import 'folder_editor_screen.dart';
import 'goods_detail_screen.dart';
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
        content: Text('로그인이 필요합니다. 게스트 계정으로는 폴더나 굿즈를 추가할 수 없습니다.'),
      ),
    );
  }

  Future<void> _confirmDeleteFolder(
    BuildContext context,
    AppState appState,
    FolderItem folder,
  ) async {
    final hasGoods = appState.goodsItems.any((g) => g.folderId == folder.id);
    final hasChildren = appState.folders.any((f) => f.parentId == folder.id);
    if (hasGoods || hasChildren) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('폴더가 비어 있어야 삭제할 수 있습니다.'),
        ),
      );
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('폴더 삭제'),
          content: Text("'${folder.name}' 폴더를 삭제할까요?"),
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
    if (ok == true) {
      appState.deleteFolderById(folder.id);
    }
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
    return appState.goodsItems
        .where((item) => childIds.contains(item.folderId))
        .length;
  }

  int _groupChildCount(AppState appState, String groupId) {
    return appState.folders
        .where((folder) => folder.parentId == groupId)
        .length;
  }

  List<FolderItem> _foldersForLevel(AppState appState, String? parentId) {
    final folders = appState.folders
        .where((folder) => folder.parentId == parentId)
        .toList();
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
          .where((folder) =>
              folder.parentId == selectedFolder!.id && !folder.isGroup)
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
      for (final folder
          in appState.folders.where((item) => item.parentId == current)) {
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
                    appState.moveFoldersToParent(
                        selectedFolderIds, selectedParentId);
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
      parentId:
          initialFolder != null ? initialFolder.parentId : selectedFolder?.id,
    );

    if (initialFolder == null) {
      appState.addFolder(nextFolder);
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
    }
  }

  Future<void> openAddGoodsFromCatalog(BuildContext context) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CatalogDatabaseScreen(
          initialFolder: selectedFolder != null && !selectedFolder!.isGroup
              ? selectedFolder
              : null,
        ),
      ),
    );
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
        final visibleFolders =
            selectedFolder == null ? topFolders : childFolders;
        final showTopActionBar = !favoritesOnly &&
            (selectedFolder == null || selectedFolder!.isGroup);

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
          body: favoritesOnly
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
                  : _FoldersCollectionView(
                      appState: appState,
                      selectedFolder: selectedFolder,
                      topFolders: topFolders,
                      childFolders: childFolders,
                      favoriteCount: favoriteCount,
                      selectionMode: folderSelectionMode,
                      selectedFolderIds: selectedFolderIds,
                      showTopActionBar: showTopActionBar,
                      onSelectTap: () {
                        setState(() {
                          folderSelectionMode = true;
                          selectedFolderIds.clear();
                        });
                      },
                      onSelectAllTap: () =>
                          _selectAllVisibleFolders(visibleFolders),
                      onCancelTap: _exitFolderSelection,
                      onMoveTap: () => openMoveFoldersDialog(appState),
                      onSearchTap: () => openGoodsSearch(context, appState),
                      onSortSelected: appState.setFolderSortType,
                      onOpenFavorites: openFavorites,
                      onOpenFolder: openFolder,
                      onOpenFolderEditor: (folder) => openFolderEditor(
                        context,
                        initialFolder: folder,
                        isGroup: folder.isGroup,
                      ),
                      onDeleteFolder: (folder) =>
                          _confirmDeleteFolder(context, appState, folder),
                    ),
        );
      },
    );
  }

  Widget? _buildFab(BuildContext context) {
    if (favoritesOnly || folderSelectionMode) return null;
    // Guest / signed-out users browse but can't create.
    if (!context.read<AppState>().isLoggedIn) return null;

    if (selectedFolder != null && selectedFolder!.isGroup) {
      return _ExpandableCircleFab(
        expanded: fabExpanded,
        mainIcon: Icons.folder_rounded,
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
          _CircleFabAction(
            icon: Icons.manage_search_rounded,
            label: 'DB 보기',
            onTap: () async {
              setState(() {
                fabExpanded = false;
              });
              await openAddGoodsFromCatalog(context);
            },
          ),
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
          _CircleFabAction(
            icon: Icons.manage_search_rounded,
            label: 'DB 보기',
            onTap: () async {
              setState(() {
                fabExpanded = false;
              });
              await openAddGoodsFromCatalog(context);
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
          icon: Icons.manage_search_rounded,
          label: 'DB 보기',
          onTap: () async {
            setState(() {
              fabExpanded = false;
            });
            await openAddGoodsFromCatalog(context);
          },
        ),
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
          bottom: BorderSide(
              color: theme.colorScheme.outline.withValues(alpha: 0.4)),
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

class _FoldersCollectionView extends StatelessWidget {
  final AppState appState;
  final FolderItem? selectedFolder;
  final List<FolderItem> topFolders;
  final List<FolderItem> childFolders;
  final int favoriteCount;
  final bool selectionMode;
  final Set<String> selectedFolderIds;
  final bool showTopActionBar;
  final VoidCallback onSelectTap;
  final VoidCallback onSelectAllTap;
  final VoidCallback onCancelTap;
  final VoidCallback onMoveTap;
  final VoidCallback onSearchTap;
  final ValueChanged<FolderSortType> onSortSelected;
  final VoidCallback onOpenFavorites;
  final ValueChanged<FolderItem> onOpenFolder;
  final ValueChanged<FolderItem> onOpenFolderEditor;
  final ValueChanged<FolderItem> onDeleteFolder;

  const _FoldersCollectionView({
    required this.appState,
    required this.selectedFolder,
    required this.topFolders,
    required this.childFolders,
    required this.favoriteCount,
    required this.selectionMode,
    required this.selectedFolderIds,
    required this.showTopActionBar,
    required this.onSelectTap,
    required this.onSelectAllTap,
    required this.onCancelTap,
    required this.onMoveTap,
    required this.onSearchTap,
    required this.onSortSelected,
    required this.onOpenFavorites,
    required this.onOpenFolder,
    required this.onOpenFolderEditor,
    required this.onDeleteFolder,
  });

  String _sortLabel(FolderSortType value) {
    switch (value) {
      case FolderSortType.nameAsc:
        return '이름순';
      case FolderSortType.goodsCountDesc:
        return '굿즈 많은순';
    }
  }

  Future<void> _exportGoodsCsv(BuildContext context, AppState appState) async {
    final items = appState.goodsItems;
    if (items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('내보낼 굿즈가 없습니다.')),
      );
      return;
    }
    try {
      await CsvExporter.exportGoodsToShare(items);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('굿즈 목록을 CSV로 저장했습니다.')),
      );
    } catch (_) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('CSV 내보내기에 실패했습니다.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>();
    final visibleFolders = selectedFolder == null ? topFolders : childFolders;
    final totalGoods = appState.totalGoodsCount;
    final totalKrw = appState.totalPaidAmount;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1300),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showTopActionBar && !selectionMode) ...[
                _FolderSearchButton(onTap: onSearchTap),
                const SizedBox(height: 18),
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: _FolderSummaryStatCard(
                          label: '전체 굿즈',
                          value: '$totalGoods개',
                          accent: const Color(0xFFF08B88),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: InkWell(
                          onTap: appState.cycleDisplayCurrency,
                          borderRadius: BorderRadius.circular(20),
                          child: _FolderSummaryStatCard(
                            label: '구매 비용',
                            value: appState.formatInDisplayCurrency(totalKrw),
                            accent: const Color(0xFFC89CEB),
                            trailingIcon: Icons.currency_exchange_rounded,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Text(
                      selectedFolder == null ? '컬렉션' : selectedFolder!.name,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const Spacer(),
                    _FolderSortChip(
                      label: _sortLabel(appState.folderSortType),
                      onSelected: onSortSelected,
                    ),
                  ],
                ),
                const SizedBox(height: 14),
              ],
              if (selectionMode) ...[
                _FolderTopActionBarFixed(
                  selectionMode: selectionMode,
                  hasItems: visibleFolders.isNotEmpty,
                  hasSelection: selectedFolderIds.isNotEmpty,
                  allSelected: visibleFolders.isNotEmpty &&
                      selectedFolderIds.length == visibleFolders.length,
                  onSelectTap: onSelectTap,
                  onSelectAllTap: onSelectAllTap,
                  onCancelTap: onCancelTap,
                  onMoveTap: onMoveTap,
                  onSearchTap: onSearchTap,
                  onSortSelected: onSortSelected,
                ),
                const SizedBox(height: 16),
              ],
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: selectedFolder == null
                    ? topFolders.length + 1
                    : childFolders.length,
                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 300,
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 1.0,
                ),
                itemBuilder: (context, index) {
                  if (selectedFolder == null && index == 0) {
                    return _SpecialFolderCard(
                      title: '즐겨찾기',
                      subtitle: '$favoriteCount개',
                      icon: Icons.favorite_rounded,
                      color: const Color(0xFFF4A4B7),
                      onTap: onOpenFavorites,
                    );
                  }

                  final folder = selectedFolder == null
                      ? topFolders[index - 1]
                      : childFolders[index];
                  final subtitle = folder.isGroup
                      ? '하위 ${appState.folders.where((item) => item.parentId == folder.id).length}개'
                      : '${appState.goodsCountForFolder(folder.id)}개';
                  final isSelected = selectedFolderIds.contains(folder.id);

                  return _FolderGridCard(
                    folder: folder,
                    subtitle: subtitle,
                    selectionMode: selectionMode,
                    selected: isSelected,
                    onTap: () => onOpenFolder(folder),
                    onEdit: () => onOpenFolderEditor(folder),
                    onDelete: () => onDeleteFolder(folder),
                  );
                },
              ),
              if (selectedFolder != null && selectedFolder!.isGroup) ...[
                const SizedBox(height: 24),
                _GroupFolderGoodsSection(
                  appState: appState,
                  group: selectedFolder!,
                ),
              ],
              if (palette != null) ...[
                const SizedBox(height: 24),
                Container(
                  height: 1,
                  color: theme.colorScheme.outline.withValues(alpha: 0.3),
                ),
              ],
              if (showTopActionBar && !selectionMode) ...[
                const SizedBox(height: 16),
                Center(
                  child: TextButton.icon(
                    onPressed: () => _exportGoodsCsv(context, appState),
                    icon: const Icon(Icons.ios_share_rounded, size: 18),
                    label: const Text('CSV 내보내기'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _FolderSearchButton extends StatelessWidget {
  final VoidCallback onTap;

  const _FolderSearchButton({
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return InkWell(
      borderRadius: BorderRadius.circular(26),
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(26),
          border: Border.all(
            color: theme.colorScheme.outline.withValues(alpha: 0.14),
          ),
          boxShadow: [
            BoxShadow(
              color: theme.colorScheme.shadow.withValues(alpha: 0.04),
              blurRadius: 22,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Row(
          children: [
            Icon(
              Icons.search_rounded,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.46),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                '전체 굿즈 검색',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.36),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Icon(
              Icons.favorite_border_rounded,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
            ),
          ],
        ),
      ),
    );
  }
}

class _FolderSummaryStatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color accent;
  final IconData? trailingIcon;

  const _FolderSummaryStatCard({
    required this.label,
    required this.value,
    required this.accent,
    this.trailingIcon,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.12),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: accent,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (trailingIcon != null)
                Icon(trailingIcon, size: 16, color: accent),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w800,
              color: const Color(0xFF7B543A),
            ),
          ),
        ],
      ),
    );
  }
}

class _FolderSortChip extends StatelessWidget {
  final String label;
  final ValueChanged<FolderSortType> onSelected;

  const _FolderSortChip({
    required this.label,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return PopupMenuButton<FolderSortType>(
      onSelected: onSelected,
      itemBuilder: (context) => const [
        PopupMenuItem(
          value: FolderSortType.nameAsc,
          child: Text('이름순'),
        ),
        PopupMenuItem(
          value: FolderSortType.goodsCountDesc,
          child: Text('굿즈 많은순'),
        ),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: theme.colorScheme.outline.withValues(alpha: 0.14),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(width: 12),
            Icon(
              Icons.expand_more_rounded,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ],
        ),
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
  final VoidCallback onDelete;

  const _FolderGridCard({
    required this.folder,
    required this.subtitle,
    required this.selectionMode,
    required this.selected,
    required this.onTap,
    required this.onEdit,
    required this.onDelete,
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
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      height: 1.25,
                      color: onSurfaceColor,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    subtitle,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: onSurfaceColor.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ),
            if (!selectionMode && !folder.isSystemWishlist)
              Positioned(
                top: 4,
                right: 4,
                child: PopupMenuButton<String>(
                  tooltip: '더보기',
                  icon: const Icon(Icons.more_vert_rounded, size: 20),
                  onSelected: (value) {
                    if (value == 'edit') {
                      onEdit();
                    } else if (value == 'delete') {
                      onDelete();
                    }
                  },
                  itemBuilder: (context) => const [
                    PopupMenuItem(value: 'edit', child: Text('수정')),
                    PopupMenuItem(value: 'delete', child: Text('삭제')),
                  ],
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
    final onSurfaceColor = theme.colorScheme.onSurface;

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
                style: theme.textTheme.titleMedium?.copyWith(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  height: 1.25,
                  color: onSurfaceColor,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: onSurfaceColor.withValues(alpha: 0.7),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FavoriteHeroPanel extends StatelessWidget {
  final Color color;
  final IconData icon;

  const _FavoriteHeroPanel({
    required this.color,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            color.withValues(alpha: 0.18),
            color.withValues(alpha: 0.07),
            theme.colorScheme.surfaceContainerLowest,
          ],
        ),
        border: Border.all(color: color.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              'Favorites',
              style: theme.textTheme.labelSmall?.copyWith(
                color: color,
                fontWeight: FontWeight.w800,
                fontSize: 10,
              ),
            ),
          ),
          const Spacer(),
          Center(
            child: Icon(
              icon,
              color: color,
              size: 42,
            ),
          ),
        ],
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

class _GroupFolderGoodsSection extends StatefulWidget {
  final AppState appState;
  final FolderItem group;
  const _GroupFolderGoodsSection({required this.appState, required this.group});

  @override
  State<_GroupFolderGoodsSection> createState() =>
      _GroupFolderGoodsSectionState();
}

class _GroupFolderGoodsSectionState extends State<_GroupFolderGoodsSection> {
  final Set<String> _selectedIds = {};
  bool _selectionMode = false;

  AppState get appState => widget.appState;
  FolderItem get group => widget.group;

  void _exitSelection() {
    setState(() {
      _selectionMode = false;
      _selectedIds.clear();
    });
  }

  void _toggleSelect(String id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else {
        _selectedIds.add(id);
      }
      if (_selectedIds.isEmpty) _selectionMode = false;
    });
  }

  Future<void> _moveSelected() async {
    String? targetId;
    final candidates = appState.folders
        .where((f) => f.id != group.id && !f.isSystemWishlist)
        .toList();
    await showDialog<void>(
      context: context,
      builder: (dctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('폴더 이동'),
          content: candidates.isEmpty
              ? const Text('이동할 폴더가 없습니다.')
              : DropdownButtonFormField<String>(
                  value: targetId,
                  decoration: const InputDecoration(labelText: '이동할 폴더'),
                  items: candidates
                      .map((f) => DropdownMenuItem(
                            value: f.id,
                            child: Text(f.name),
                          ))
                      .toList(),
                  onChanged: (v) => setDialogState(() => targetId = v),
                ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dctx),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: targetId == null
                  ? null
                  : () {
                      appState.moveGoodsToFolder(_selectedIds, targetId!);
                      Navigator.pop(dctx);
                      _exitSelection();
                    },
              child: const Text('이동'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _deleteSelected() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dctx) => AlertDialog(
        title: const Text('굿즈 삭제'),
        content: Text('선택한 ${_selectedIds.length}개 굿즈를 삭제할까요?'),
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
    if (confirm != true) return;
    appState.deleteGoodsByIds(_selectedIds);
    _exitSelection();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final items = appState.goodsForFolder(group.id);
    // Prune stale ids in case parent rebuild dropped some.
    _selectedIds.removeWhere((id) => !items.any((it) => it.id == id));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.inventory_2_outlined, size: 18),
            const SizedBox(width: 6),
            Text(
              '이 그룹의 굿즈',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
            const Spacer(),
            if (_selectionMode) ...[
              Text(
                '${_selectedIds.length}개 선택',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.primary,
                ),
              ),
              TextButton(
                onPressed: _exitSelection,
                child: const Text('취소'),
              ),
            ] else ...[
              Text(
                '${items.length}개',
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                ),
              ),
              if (items.isNotEmpty)
                TextButton(
                  onPressed: () => setState(() => _selectionMode = true),
                  child: const Text('선택'),
                ),
            ],
          ],
        ),
        if (_selectionMode) ...[
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _selectedIds.isEmpty ? null : _moveSelected,
                  icon: const Icon(Icons.drive_file_move_outlined, size: 16),
                  label: const Text('이동'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _selectedIds.isEmpty ? null : _deleteSelected,
                  icon: const Icon(Icons.delete_outline, size: 16),
                  label: const Text('삭제'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: theme.colorScheme.error,
                  ),
                ),
              ),
            ],
          ),
        ],
        const SizedBox(height: 12),
        if (items.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 28),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              children: [
                Icon(
                  Icons.inbox_outlined,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                ),
                const SizedBox(height: 8),
                Text(
                  '아직 굿즈가 없어요. 오른쪽 아래 + 버튼으로 추가해 주세요.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
          )
        else
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: items.length,
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 200,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 0.78,
            ),
            itemBuilder: (context, index) {
              final item = items[index];
              final selected = _selectedIds.contains(item.id);
              return InkWell(
                borderRadius: BorderRadius.circular(16),
                onLongPress: () {
                  setState(() {
                    _selectionMode = true;
                    _selectedIds.add(item.id);
                  });
                },
                onTap: () {
                  if (_selectionMode) {
                    _toggleSelect(item.id);
                    return;
                  }
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => GoodsDetailScreen(
                        item: item,
                        galleryItems: items,
                      ),
                    ),
                  );
                },
                child: Container(
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: selected
                          ? theme.colorScheme.primary
                          : theme.colorScheme.outline.withValues(alpha: 0.25),
                      width: selected ? 2 : 1,
                    ),
                  ),
                  child: Stack(
                    children: [
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          AspectRatio(
                            aspectRatio: 1.0,
                            child: Container(
                              width: double.infinity,
                              clipBehavior: Clip.antiAlias,
                              decoration: BoxDecoration(
                                color:
                                    theme.colorScheme.surfaceContainerHighest,
                                borderRadius: const BorderRadius.vertical(
                                  top: Radius.circular(15),
                                ),
                              ),
                              child: item.imageBytes != null
                                  ? Image.memory(item.imageBytes!,
                                      fit: BoxFit.cover)
                                  : const Center(
                                      child:
                                          Icon(Icons.image_outlined, size: 32),
                                    ),
                            ),
                          ),
                          Expanded(
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 6),
                              child: Center(
                                child: Text(
                                  item.name,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  textAlign: TextAlign.center,
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 12,
                                    color: theme.colorScheme.onSurface,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      if (!_selectionMode)
                        Positioned(
                          top: 8,
                          right: 8,
                          child: GestureDetector(
                            onTap: () => appState.toggleFavorite(item.id),
                            child: CircleAvatar(
                              radius: 13,
                              backgroundColor: theme.colorScheme.surface
                                  .withValues(alpha: 0.92),
                              child: Icon(
                                item.isFavorite
                                    ? Icons.favorite
                                    : Icons.favorite_border,
                                size: 14,
                                color: item.isFavorite
                                    ? Colors.pink
                                    : theme.colorScheme.onSurface
                                        .withValues(alpha: 0.6),
                              ),
                            ),
                          ),
                        ),
                      if (_selectionMode)
                        Positioned(
                          top: 8,
                          right: 8,
                          child: Container(
                            width: 24,
                            height: 24,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: selected
                                  ? theme.colorScheme.primary
                                  : theme.colorScheme.surface
                                      .withValues(alpha: 0.85),
                              border: Border.all(
                                color: selected
                                    ? theme.colorScheme.primary
                                    : theme.colorScheme.outline
                                        .withValues(alpha: 0.4),
                                width: 2,
                              ),
                            ),
                            child: selected
                                ? const Icon(Icons.check,
                                    size: 16, color: Colors.white)
                                : null,
                          ),
                        ),
                    ],
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}
