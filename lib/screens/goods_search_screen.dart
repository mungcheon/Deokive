import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_item.dart';
import '../state/app_state.dart';
import '../widgets/goods_item_image.dart';
import 'goods_detail_screen.dart';

class GoodsSearchScreen extends StatefulWidget {
  final FolderItem? folder;
  final bool favoritesOnly;
  final Set<String>? folderIds;

  const GoodsSearchScreen({
    super.key,
    required this.folder,
    required this.favoritesOnly,
    this.folderIds,
  });

  @override
  State<GoodsSearchScreen> createState() => _GoodsSearchScreenState();
}

class _GoodsSearchScreenState extends State<GoodsSearchScreen> {
  final TextEditingController searchController = TextEditingController();
  String query = '';

  @override
  void dispose() {
    searchController.dispose();
    super.dispose();
  }

  List<GoodsItem> _baseItems(AppState appState) {
    if (widget.folderIds != null) {
      return appState.goodsItems
          .where((item) => widget.folderIds!.contains(item.folderId))
          .toList();
    }
    if (widget.favoritesOnly) {
      return appState.favoriteGoods();
    }
    if (widget.folder != null) {
      return appState.goodsForFolder(widget.folder!.id);
    }
    return appState.goodsItems;
  }

  List<GoodsItem> _filteredItems(AppState appState) {
    final normalizedQuery = query.trim().toLowerCase();
    final items = _baseItems(appState);
    if (normalizedQuery.isEmpty) {
      return [];
    }

    final filtered = items.where((item) {
      final target = [
        item.name,
        item.seriesName,
        item.category,
        item.companyName ?? '',
        item.barcode ?? '',
        item.memo ?? '',
        item.storageLocation ?? '',
      ].join(' ').toLowerCase();
      return target.contains(normalizedQuery);
    }).toList();

    return appState.sortGoods(filtered, appState.defaultGoodsSortType);
  }

  String _folderName(AppState appState, GoodsItem item) {
    final folder = appState.folders.where((value) => value.id == item.folderId);
    if (folder.isEmpty) {
      return '폴더 없음';
    }
    return folder.first.name;
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final results = _filteredItems(appState);

        return Scaffold(
          appBar: AppBar(
            title: const Text('굿즈 검색'),
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              TextField(
                controller: searchController,
                autofocus: true,
                onChanged: (value) {
                  setState(() {
                    query = value;
                  });
                },
                decoration: InputDecoration(
                  hintText: '굿즈 이름, 시리즈, 바코드 검색',
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: query.isEmpty
                      ? null
                      : IconButton(
                          onPressed: () {
                            searchController.clear();
                            setState(() {
                              query = '';
                            });
                          },
                          icon: const Icon(Icons.close_rounded),
                        ),
                ),
              ),
              const SizedBox(height: 16),
              if (query.trim().isEmpty)
                const _SearchGuideCard(
                  text: '주소 검색하듯 키워드를 입력하면 연관 굿즈를 바로 찾을 수 있어요.',
                )
              else if (results.isEmpty)
                const _SearchGuideCard(
                  text: '연관된 굿즈가 없어요.',
                )
              else
                ...results.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Card(
                      child: ListTile(
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => GoodsDetailScreen(item: item),
                            ),
                          );
                        },
                        leading: ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: SizedBox(
                            width: 54,
                            height: 54,
                            child: GoodsItemImage(item: item),
                          ),
                        ),
                        title: Text(
                          item.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        subtitle: Text(
                          '${_folderName(appState, item)} · ${item.seriesName.isEmpty ? item.category : item.seriesName}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        trailing: const Icon(Icons.chevron_right),
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
}

class _SearchGuideCard extends StatelessWidget {
  final String text;

  const _SearchGuideCard({required this.text});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          text,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ),
    );
  }
}
