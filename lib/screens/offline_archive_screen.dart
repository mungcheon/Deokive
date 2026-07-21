import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_item.dart';
import '../state/app_state.dart';

class OfflineArchiveScreen extends StatefulWidget {
  const OfflineArchiveScreen({super.key});

  @override
  State<OfflineArchiveScreen> createState() => _OfflineArchiveScreenState();
}

class _OfflineArchiveScreenState extends State<OfflineArchiveScreen> {
  String? _selectedFolderId;

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final folders = appState.folders
            .where((folder) => !folder.isGroup)
            .toList()
          ..sort((a, b) => a.name.compareTo(b.name));
        final selectedFolder = _resolveSelectedFolder(folders);
        final goods = selectedFolder == null
            ? <GoodsItem>[]
            : appState.goodsForFolder(selectedFolder.id)
              ..sort((a, b) => a.name.compareTo(b.name));

        return Scaffold(
          appBar: AppBar(
            title: const Text('오프라인 보관함'),
            centerTitle: true,
          ),
          body: Column(
            children: [
              Container(
                width: double.infinity,
                margin: const EdgeInsets.fromLTRB(16, 16, 16, 10),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Theme.of(context)
                      .colorScheme
                      .surfaceContainerHighest
                      .withValues(alpha: 0.75),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '서버에 연결할 수 없어 로컬 보관함을 읽기 전용으로 보여주고 있어요.',
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 13.5,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      '이 기기에 저장된 폴더와 굿즈 목록만 볼 수 있고, 작성·수정·동기화 기능은 잠시 사용할 수 없어요.',
                      style: TextStyle(height: 1.45),
                    ),
                  ],
                ),
              ),
              SizedBox(
                height: 106,
                child: ListView.separated(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  scrollDirection: Axis.horizontal,
                  itemCount: folders.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 10),
                  itemBuilder: (context, index) {
                    final folder = folders[index];
                    final selected = selectedFolder?.id == folder.id;
                    final count = appState.goodsCountForFolder(folder.id);
                    return _OfflineFolderChip(
                      folder: folder,
                      count: count,
                      selected: selected,
                      onTap: () {
                        setState(() {
                          _selectedFolderId = folder.id;
                        });
                      },
                    );
                  },
                ),
              ),
              const SizedBox(height: 10),
              Expanded(
                child: selectedFolder == null
                    ? const Center(
                        child: Text('표시할 폴더가 없습니다.'),
                      )
                    : goods.isEmpty
                        ? Center(
                            child: Text(
                              '${selectedFolder.name} 폴더에 저장된 굿즈가 없습니다.',
                            ),
                          )
                        : GridView.builder(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                            itemCount: goods.length,
                            gridDelegate:
                                const SliverGridDelegateWithMaxCrossAxisExtent(
                              maxCrossAxisExtent: 220,
                              mainAxisSpacing: 12,
                              crossAxisSpacing: 12,
                              childAspectRatio: 0.78,
                            ),
                            itemBuilder: (context, index) {
                              final item = goods[index];
                              return _OfflineGoodsCard(item: item);
                            },
                          ),
              ),
            ],
          ),
        );
      },
    );
  }

  FolderItem? _resolveSelectedFolder(List<FolderItem> folders) {
    if (folders.isEmpty) return null;
    final selected = folders.where((folder) => folder.id == _selectedFolderId);
    if (selected.isNotEmpty) return selected.first;
    return folders.first;
  }
}

class _OfflineFolderChip extends StatelessWidget {
  final FolderItem folder;
  final int count;
  final bool selected;
  final VoidCallback onTap;

  const _OfflineFolderChip({
    required this.folder,
    required this.count,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        width: 150,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected
              ? theme.colorScheme.primary.withValues(alpha: 0.14)
              : theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: selected
                ? theme.colorScheme.primary
                : theme.colorScheme.outline.withValues(alpha: 0.18),
            width: selected ? 2 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(folder.icon, color: folder.color, size: 24),
            const Spacer(),
            Text(
              folder.name,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '$count개',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.62),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OfflineGoodsCard extends StatelessWidget {
  final GoodsItem item;

  const _OfflineGoodsCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.18),
        ),
      ),
      child: Column(
        children: [
          Expanded(
            flex: 5,
            child: ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(17)),
              child: Container(
                width: double.infinity,
                color: theme.colorScheme.surfaceContainerHighest,
                child: item.imageBytes != null
                    ? Image.memory(item.imageBytes!, fit: BoxFit.cover)
                    : const Center(
                        child: Icon(Icons.image_outlined, size: 34),
                      ),
              ),
            ),
          ),
          Expanded(
            flex: 3,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    item.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    item.category,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.62),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
