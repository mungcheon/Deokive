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
        content: Text('濡쒓렇?명븯?몄슂. 寃뚯뒪??怨꾩젙?쇰줈???대뜑? 援우쫰瑜?異붽??????놁뒿?덈떎.'),
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
              title: const Text('?대뜑 ?대룞'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  RadioListTile<String?>(
                    value: null,
                    groupValue: selectedParentId,
                    title: const Text('?대뜑'),
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
                        '洹몃９?대뜑???ㅻⅨ 洹몃９?대뜑 ?덉쑝濡??대룞?????놁뒿?덈떎.',
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
                  child: const Text('痍⑥냼'),
                ),
                FilledButton(
                  onPressed: () {
                    appState.moveFoldersToParent(selectedFolderIds, selectedParentId);
                    Navigator.pop(dialogContext);
                    _exitFolderSelection();
                  },
                  child: const Text('?대룞'),
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
            label: '?대뜑 ?앹꽦',
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
            label: '援우쫰 ?앹꽦',
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
          label: '?대뜑 ?앹꽦',
          onTap: () async {
            setState(() {
              fabExpanded = false;
            });
            await openFolderEditor(context, isGroup: false);
          },
        ),
        _CircleFabAction(
          icon: Icons.folder_copy_outlined,
          label: '洹몃９?대뜑 ?앹꽦',
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
            tooltip: '援우쫰 寃??,
            onPressed: onSearchTap,
            icon: const Icon(Icons.search_rounded),
          ),
          const Spacer(),
          PopupMenuButton<FolderSortType>(
            tooltip: '?뺣젹',
            onSelected: onSortSelected,
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: FolderSortType.nameAsc,
                child: Text('媛?섎떎??),
              ),
              PopupMenuItem(
                value: FolderSortType.goodsCountDesc,
                child: Text('援우쫰 留롮???),
              ),
            ],
            icon: const Icon(Icons.sort),
          ),
          if (!selectionMode)
            TextButton(
              onPressed: hasItems ? onSelectTap : null,
              child: const Text('?좏깮'),
            ),
          if (selectionMode) ...[
            TextButton(
              onPressed: onCancelTap,
              child: const Text('痍⑥냼'),
            ),
            IconButton(
              tooltip: '?대뜑 ?대룞',
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
            tooltip: '援우쫰 寃??,
            onPressed: onSearchTap,
            icon: const Icon(Icons.search_rounded),
          ),
          const Spacer(),
          PopupMenuButton<FolderSortType>(
            tooltip: '?뺣젹',
            onSelected: onSortSelected,
            itemBuilder: (context) => const [
              PopupMenuItem(
                value: FolderSortType.nameAsc,
                child: Text('媛?섎떎??),
              ),
              PopupMenuItem(
                value: FolderSortType.goodsCountDesc,
                child: Text('援우쫰 留롮???),
              ),
            ],
            icon: const Icon(Icons.sort),
          ),
          if (!selectionMode)
            TextButton(
              onPressed: hasItems ? onSelectTap : null,
              child: const Text('?좏깮'),
            ),
          if (selectionMode) ...[
            TextButton(
              onPressed: hasItems ? onSelectAllTap : null,
              child: Text(allSelected ? '?꾩껜?좏깮?? : '?꾩껜?좏깮'),
            ),
            TextButton(
              onPressed: onCancelTap,
              child: const Text('痍⑥냼'),
            ),
            IconButton(
              tooltip: '?대뜑 ?대룞',
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
  });

  String _sortLabel(FolderSortType value) {
    switch (value) {
      case FolderSortType.nameAsc:
        return '이름순';
      case FolderSortType.goodsCountDesc:
        return '굿즈 많은순';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>();
    final visibleFolders = selectedFolder == null ? topFolders : childFolders;
    final totalGoods = appState.totalGoodsCount;
    final groupCount = topFolders.where((folder) => folder.isGroup).length;

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
                Row(
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
                      child: _FolderSummaryStatCard(
                        label: '즐겨찾기',
                        value: '$favoriteCount개',
                        accent: const Color(0xFFC89CEB),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _FolderSummaryStatCard(
                        label: '컬렉션',
                        value: '$groupCount개',
                        accent: const Color(0xFFA89CF0),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
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
                gridDelegate:
                    const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 300,
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 0.82,
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
                  );
                },
              ),
              if (palette != null) ...[
                const SizedBox(height: 24),
                Container(
                  height: 1,
                  color: palette.line.withValues(alpha: 0.3),
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

  const _FolderSummaryStatCard({
    required this.label,
    required this.value,
    required this.accent,
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
          Text(
            label,
            style: theme.textTheme.labelLarge?.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
            ),
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
