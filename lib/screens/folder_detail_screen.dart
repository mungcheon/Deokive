import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_item.dart';
import '../state/app_state.dart';
import 'add_goods_screen.dart';
import 'goods_detail_screen.dart';
import 'goods_search_screen.dart';

class FolderDetailContent extends StatefulWidget {
  final FolderItem? folder;
  final bool favoritesOnly;
  final VoidCallback onBack;

  const FolderDetailContent({
    super.key,
    required this.folder,
    required this.favoritesOnly,
    required this.onBack,
  });

  @override
  State<FolderDetailContent> createState() => _FolderDetailContentState();
}

class _FolderDetailContentState extends State<FolderDetailContent> {
  bool selectionMode = false;
  final Set<String> selectedIds = {};
  GoodsSortType? sortType;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    sortType ??= context.read<AppState>().defaultGoodsSortType;
  }

  void toggleSelection(String id) {
    setState(() {
      if (selectedIds.contains(id)) {
        selectedIds.remove(id);
      } else {
        selectedIds.add(id);
      }
    });
  }

  void exitSelectionMode() {
    setState(() {
      selectionMode = false;
      selectedIds.clear();
    });
  }

  Future<void> openMoveDialog(AppState appState) async {
    String? selectedFolderId;
    final targetFolders = appState.folders
        .where(
          (folder) =>
              !folder.isGroup &&
              (widget.favoritesOnly || folder.id != widget.folder!.id),
        )
        .toList();

    await showDialog(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('폴더 이동'),
              content: targetFolders.isEmpty
                  ? const Text('이동할 폴더가 없습니다.')
                  : DropdownButtonFormField<String>(
                      value: selectedFolderId,
                      decoration: const InputDecoration(
                        labelText: '이동할 폴더',
                      ),
                      items: targetFolders
                          .map(
                            (folder) => DropdownMenuItem(
                              value: folder.id,
                              child: Text(folder.name),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        setDialogState(() {
                          selectedFolderId = value;
                        });
                      },
                    ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: selectedFolderId == null
                      ? null
                      : () {
                          appState.moveGoodsToFolder(selectedIds, selectedFolderId!);
                          Navigator.pop(dialogContext);
                          exitSelectionMode();
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

  Future<void> openAddGoods(AppState appState) async {
    if (widget.folder == null) return;

    final result = await Navigator.push<GoodsItem>(
      context,
      MaterialPageRoute(
        builder: (_) => AddGoodsScreen(folder: widget.folder!),
      ),
    );

    if (result != null) {
      appState.addGoods(result);
    }
  }

  Future<void> openGoodsSearch(AppState appState) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => GoodsSearchScreen(
          folder: widget.favoritesOnly ? null : widget.folder,
          favoritesOnly: widget.favoritesOnly,
          folderIds: widget.favoritesOnly
              ? null
              : widget.folder == null
                  ? null
                  : {widget.folder!.id},
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        List<GoodsItem> items = widget.favoritesOnly
            ? appState.favoriteGoods()
            : appState.goodsForFolder(widget.folder!.id);

        final appliedSort = sortType ?? appState.defaultGoodsSortType;
        items = appState.sortGoods(items, appliedSort);

        return Column(
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              decoration: BoxDecoration(
                color: Theme.of(context).scaffoldBackgroundColor,
                border: Border(
                  bottom: BorderSide(
                    color: Theme.of(context)
                        .colorScheme
                        .outline
                        .withValues(alpha: 0.4),
                  ),
                ),
              ),
              child: Row(
                children: [
                  IconButton(
                    tooltip: '굿즈 검색',
                    onPressed: () => openGoodsSearch(appState),
                    icon: const Icon(Icons.search_rounded),
                  ),
                  const Spacer(),
                  PopupMenuButton<GoodsSortType>(
                    tooltip: '정렬',
                    initialValue: appliedSort,
                    onSelected: (value) {
                      setState(() {
                        sortType = value;
                      });
                    },
                    itemBuilder: (context) => const [
                      PopupMenuItem(
                        value: GoodsSortType.nameAsc,
                        child: Text('가나다순'),
                      ),
                      PopupMenuItem(
                        value: GoodsSortType.priceAsc,
                        child: Text('가격 낮은순'),
                      ),
                      PopupMenuItem(
                        value: GoodsSortType.priceDesc,
                        child: Text('가격 높은순'),
                      ),
                      PopupMenuItem(
                        value: GoodsSortType.seriesAsc,
                        child: Text('시리즈 가나다순'),
                      ),
                      PopupMenuItem(
                        value: GoodsSortType.purchaseDateNewest,
                        child: Text('구매일 최신순'),
                      ),
                      PopupMenuItem(
                        value: GoodsSortType.purchaseDateOldest,
                        child: Text('구매일 오래된순'),
                      ),
                    ],
                    icon: const Icon(Icons.sort),
                  ),
                  if (!selectionMode)
                    TextButton(
                      onPressed: items.isEmpty
                          ? null
                          : () {
                              setState(() {
                                selectionMode = true;
                              });
                            },
                      child: const Text('선택'),
                    ),
                  if (selectionMode) ...[
                    TextButton(
                      onPressed: exitSelectionMode,
                      child: const Text('취소'),
                    ),
                    IconButton(
                      onPressed:
                          selectedIds.isEmpty ? null : () => openMoveDialog(appState),
                      icon: const Icon(Icons.drive_file_move_outline),
                    ),
                    IconButton(
                      onPressed: selectedIds.isEmpty
                          ? null
                          : () {
                              appState.deleteGoodsByIds(selectedIds);
                              exitSelectionMode();
                            },
                      icon: const Icon(Icons.delete_outline),
                    ),
                  ],
                ],
              ),
            ),
            Expanded(
              child: items.isEmpty
                  ? const Center(
                      child: Text(
                        '굿즈가 없습니다.',
                        style: TextStyle(fontSize: 16),
                      ),
                    )
                  : Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1300),
                        child: GridView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: items.length,
                          gridDelegate:
                              const SliverGridDelegateWithMaxCrossAxisExtent(
                            maxCrossAxisExtent: 220,
                            mainAxisSpacing: 12,
                            crossAxisSpacing: 12,
                            childAspectRatio: 0.82,
                          ),
                          itemBuilder: (context, index) {
                            final item = items[index];
                            final selected = selectedIds.contains(item.id);

                            return InkWell(
                              borderRadius: BorderRadius.circular(18),
                              onTap: () {
                                if (selectionMode) {
                                  toggleSelection(item.id);
                                } else {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => GoodsDetailScreen(item: item),
                                    ),
                                  );
                                }
                              },
                              child: Container(
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(18),
                                  border: Border.all(
                                    color: selected
                                        ? Theme.of(context).colorScheme.primary
                                        : Colors.grey.shade300,
                                    width: selected ? 2 : 1,
                                  ),
                                ),
                                child: Stack(
                                  children: [
                                    Column(
                                      children: [
                                        Expanded(
                                          child: Container(
                                            width: double.infinity,
                                            clipBehavior: Clip.antiAlias,
                                            decoration: BoxDecoration(
                                              color: Colors.grey.shade100,
                                              borderRadius:
                                                  const BorderRadius.vertical(
                                                top: Radius.circular(17),
                                              ),
                                            ),
                                            child: item.imageBytes != null
                                                ? Image.memory(
                                                    item.imageBytes!,
                                                    fit: BoxFit.cover,
                                                  )
                                                : const Center(
                                                    child: Icon(
                                                      Icons.image_outlined,
                                                      size: 34,
                                                    ),
                                                  ),
                                          ),
                                        ),
                                        Padding(
                                          padding: const EdgeInsets.all(12),
                                          child: Text(
                                            item.name,
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                            textAlign: TextAlign.center,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w700,
                                              fontSize: 14,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    if (!selectionMode)
                                      Positioned(
                                        top: 10,
                                        right: 10,
                                        child: GestureDetector(
                                          onTap: () => appState.toggleFavorite(item.id),
                                          child: CircleAvatar(
                                            radius: 14,
                                            backgroundColor:
                                                Colors.white.withValues(alpha: 0.92),
                                            child: Icon(
                                              item.isFavorite
                                                  ? Icons.favorite
                                                  : Icons.favorite_border,
                                              size: 16,
                                              color: item.isFavorite
                                                  ? Colors.pink
                                                  : Colors.grey,
                                            ),
                                          ),
                                        ),
                                      ),
                                    if (selectionMode)
                                      Positioned(
                                        top: 10,
                                        right: 10,
                                        child: CircleAvatar(
                                          radius: 13,
                                          backgroundColor: selected
                                              ? Theme.of(context).colorScheme.primary
                                              : Colors.white,
                                          child: Icon(
                                            selected
                                                ? Icons.check
                                                : Icons.circle_outlined,
                                            size: 16,
                                            color: selected
                                                ? Colors.white
                                                : Colors.grey,
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
            ),
          ],
        );
      },
    );
  }
}
