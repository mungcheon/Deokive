import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_catalog_entry.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../utils/catalog_goods_importer.dart';

class CatalogDatabaseScreen extends StatefulWidget {
  final FolderItem? initialFolder;

  const CatalogDatabaseScreen({
    super.key,
    this.initialFolder,
  });

  @override
  State<CatalogDatabaseScreen> createState() => _CatalogDatabaseScreenState();
}

class _CatalogDatabaseScreenState extends State<CatalogDatabaseScreen> {
  final TextEditingController _searchController = TextEditingController();
  String _query = '';
  String? _category;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<GoodsCatalogEntry> _filteredEntries(AppState appState) {
    final normalizedQuery = _query.trim().toLowerCase();
    final normalizedCategory = _category?.trim();
    final entries = appState.curatedCatalogEntries.where((entry) {
      if (normalizedCategory != null &&
          normalizedCategory.isNotEmpty &&
          entry.normalizedCategory != normalizedCategory) {
        return false;
      }

      if (normalizedQuery.isEmpty) return true;
      final target = [
        entry.nameKo,
        entry.nameJa ?? '',
        entry.nameEn ?? '',
        entry.normalizedCategory,
        entry.characterName,
        entry.affiliation,
        entry.seriesName ?? '',
        entry.subSeries ?? '',
        entry.sourceStore,
        entry.barcode ?? '',
      ].join(' ').toLowerCase();
      return target.contains(normalizedQuery);
    }).toList();

    entries.sort((a, b) {
      final bySeries = (a.seriesName ?? '').compareTo(b.seriesName ?? '');
      if (bySeries != 0) return bySeries;
      return a.nameKo.compareTo(b.nameKo);
    });
    return entries;
  }

  Future<void> _showAddSheet(
    BuildContext context,
    AppState appState,
    GoodsCatalogEntry entry,
  ) async {
    final ownedCount = matchingCatalogGoodsItems(
      goodsItems: appState.goodsItems,
      entry: entry,
    ).fold<int>(0, (sum, item) => sum + item.quantity);

    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) {
        final theme = Theme.of(sheetContext);
        final palette = theme.extension<DeokivePalette>()!;
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
              18,
              4,
              18,
              18 + MediaQuery.of(sheetContext).viewInsets.bottom,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _CatalogImage(entry: entry, size: 72),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            entry.nameKo,
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _entrySubtitle(entry),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurface
                                  .withValues(alpha: 0.62),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                Text(
                  '이 굿즈를 내 굿즈함에 추가하겠습니까?',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  widget.initialFolder == null
                      ? '다음 단계에서 저장할 폴더를 고를 수 있어요. 가장 위 폴더가 기본값이에요.'
                      : "'${widget.initialFolder!.name}' 폴더가 기본 저장 위치로 먼저 선택돼요.",
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.62),
                  ),
                ),
                if (ownedCount > 0) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 9,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF4D8),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.info_outline_rounded,
                          size: 18,
                          color: Color(0xFF9A6A12),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '이미 내 굿즈함에 $ownedCount개 있어요. 그래도 추가할 수 있어요.',
                            style: const TextStyle(
                              color: Color(0xFF6E4A08),
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 18),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.pop(sheetContext),
                        child: const Text('취소'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      flex: 2,
                      child: FilledButton.icon(
                        onPressed: () async {
                          Navigator.pop(sheetContext);
                          await showCatalogGoodsImportFlowForEntry(
                            context,
                            entry: entry,
                            initialFolder: widget.initialFolder,
                          );
                        },
                        icon: const Icon(Icons.add_rounded),
                        label: const Text('내 굿즈에 추가하기'),
                        style: FilledButton.styleFrom(
                          backgroundColor: palette.primary,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;
        final entries = _filteredEntries(appState);
        final categories = appState.curatedCatalogCategories.take(18).toList();

        return Scaffold(
          appBar: AppBar(
            title: const Text('DB 보기'),
            actions: [
              Padding(
                padding: const EdgeInsets.only(right: 14),
                child: Center(
                  child: Text(
                    '${entries.length}/${appState.curatedCatalogEntries.length}',
                    style: theme.textTheme.labelLarge?.copyWith(
                      color:
                          theme.colorScheme.onSurface.withValues(alpha: 0.62),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ],
          ),
          body: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
                child: TextField(
                  controller: _searchController,
                  onChanged: (value) => setState(() => _query = value),
                  textInputAction: TextInputAction.search,
                  decoration: InputDecoration(
                    hintText: '굿즈명, 작품, 캐릭터, 바코드 검색',
                    prefixIcon: const Icon(Icons.search_rounded),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            tooltip: '검색어 지우기',
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _query = '');
                            },
                            icon: const Icon(Icons.close_rounded),
                          ),
                  ),
                ),
              ),
              SizedBox(
                height: 42,
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  scrollDirection: Axis.horizontal,
                  children: [
                    _FilterChip(
                      label: '전체',
                      selected: _category == null,
                      color: palette.primary,
                      onTap: () => setState(() => _category = null),
                    ),
                    for (final category in categories) ...[
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: category,
                        selected: _category == category,
                        color: palette.primary,
                        onTap: () => setState(() => _category = category),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: entries.isEmpty
                    ? const _EmptyCatalogResult()
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
                        itemCount: entries.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, index) {
                          final entry = entries[index];
                          final ownedCount = matchingCatalogGoodsItems(
                            goodsItems: appState.goodsItems,
                            entry: entry,
                          ).fold<int>(0, (sum, item) => sum + item.quantity);
                          return _CatalogListTile(
                            entry: entry,
                            ownedCount: ownedCount,
                            onTap: () =>
                                _showAddSheet(context, appState, entry),
                          );
                        },
                      ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _CatalogListTile extends StatelessWidget {
  final GoodsCatalogEntry entry;
  final int ownedCount;
  final VoidCallback onTap;

  const _CatalogListTile({
    required this.entry,
    required this.ownedCount,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    return Material(
      color: theme.colorScheme.surface,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: ownedCount > 0
                  ? palette.primary.withValues(alpha: 0.32)
                  : theme.colorScheme.outline.withValues(alpha: 0.5),
            ),
          ),
          child: Row(
            children: [
              _CatalogImage(entry: entry, size: 58),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.nameKo,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 14.5,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      _entrySubtitle(entry),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.58),
                      ),
                    ),
                    if (ownedCount > 0) ...[
                      const SizedBox(height: 7),
                      Text(
                        '내 굿즈함 $ownedCount개',
                        style: TextStyle(
                          color: palette.primary,
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                Icons.add_circle_outline_rounded,
                color: palette.primary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CatalogImage extends StatelessWidget {
  final GoodsCatalogEntry entry;
  final double size;

  const _CatalogImage({
    required this.entry,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final placeholder = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Icon(
        Icons.inventory_2_outlined,
        color: theme.colorScheme.onSurface.withValues(alpha: 0.48),
      ),
    );

    final raw = entry.imageUrl?.trim() ?? '';
    if (raw.isEmpty) return placeholder;
    final url = raw.replaceAll('&amp;', '&').replaceFirst(
          RegExp(r'^//'),
          'https://',
        );

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Image.network(
        url,
        width: size,
        height: size,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => placeholder,
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      onPressed: onTap,
      label: Text(label),
      avatar: selected ? const Icon(Icons.check_rounded, size: 16) : null,
      backgroundColor:
          selected ? color.withValues(alpha: 0.13) : Colors.transparent,
      side: BorderSide(
        color: selected
            ? color.withValues(alpha: 0.45)
            : Theme.of(context).colorScheme.outline.withValues(alpha: 0.55),
      ),
      labelStyle: TextStyle(
        color: selected ? color : Theme.of(context).colorScheme.onSurface,
        fontWeight: FontWeight.w800,
      ),
    );
  }
}

class _EmptyCatalogResult extends StatelessWidget {
  const _EmptyCatalogResult();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search_off_rounded,
              size: 42,
              color: Theme.of(context)
                  .colorScheme
                  .onSurface
                  .withValues(alpha: 0.34),
            ),
            const SizedBox(height: 12),
            const Text(
              '검색 결과가 없어요',
              style: TextStyle(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 4),
            Text(
              '검색어를 줄이거나 다른 분류를 선택해 보세요.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

String _entrySubtitle(GoodsCatalogEntry entry) {
  final parts = [
    entry.seriesName,
    entry.characterName,
    entry.normalizedCategory,
    entry.sourceStore,
  ]
      .whereType<String>()
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toList();
  if (parts.isEmpty) return '상세 정보 없음';
  return parts.join(' · ');
}
