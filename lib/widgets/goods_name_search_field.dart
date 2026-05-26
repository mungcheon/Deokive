import 'package:flutter/material.dart';

import '../models/goods_catalog_entry.dart';

/// Goods-name input that opens a postcode-search-style picker dialog when
/// tapped. The dialog has its own search bar and shows catalog matches with
/// product images. Selecting a row fires `onCatalogSelected`; free-form
/// typing is still supported via the trailing "직접 입력" button on the
/// dialog (or by typing in the field directly when the dialog isn't open).
class GoodsNameSearchField extends StatefulWidget {
  final TextEditingController controller;
  final List<GoodsCatalogEntry> catalog;
  final ValueChanged<GoodsCatalogEntry>? onCatalogSelected;
  final ValueChanged<String>? onChanged;

  const GoodsNameSearchField({
    super.key,
    required this.controller,
    required this.catalog,
    this.onCatalogSelected,
    this.onChanged,
  });

  @override
  State<GoodsNameSearchField> createState() => _GoodsNameSearchFieldState();
}

class _GoodsNameSearchFieldState extends State<GoodsNameSearchField> {
  Future<void> _openPicker() async {
    final picked = await showDialog<GoodsCatalogEntry>(
      context: context,
      builder: (_) => _GoodsCatalogPickerDialog(
        catalog: widget.catalog,
        initialQuery: widget.controller.text.trim(),
      ),
    );
    if (picked == null) return;
    widget.controller.text = picked.nameKo;
    widget.onCatalogSelected?.call(picked);
    widget.onChanged?.call(picked.nameKo);
  }

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controller,
      onChanged: widget.onChanged,
      decoration: InputDecoration(
        labelText: '굿즈 이름 *',
        helperText: '직접 입력하거나 돋보기를 눌러 카탈로그에서 검색하세요',
        prefixIcon: const Icon(Icons.inventory_2_outlined),
        suffixIcon: IconButton(
          tooltip: '카탈로그 검색',
          icon: const Icon(Icons.search_rounded),
          onPressed: _openPicker,
        ),
      ),
      validator: (value) {
        if (value == null || value.trim().isEmpty) {
          return '굿즈 이름은 필수입니다.';
        }
        return null;
      },
    );
  }
}

/// Open the catalog picker dialog standalone (without the text field).
/// Useful when triggering catalog browse from an AppBar icon, etc.
/// Returns the picked entry, or null on cancel.
Future<GoodsCatalogEntry?> showGoodsCatalogPicker(
  BuildContext context, {
  required List<GoodsCatalogEntry> catalog,
  String initialQuery = '',
}) {
  return showDialog<GoodsCatalogEntry>(
    context: context,
    builder: (_) => _GoodsCatalogPickerDialog(
      catalog: catalog,
      initialQuery: initialQuery,
    ),
  );
}

// ── Picker dialog ───────────────────────────────────────────────────────

class _GoodsCatalogPickerDialog extends StatefulWidget {
  final List<GoodsCatalogEntry> catalog;
  final String initialQuery;

  const _GoodsCatalogPickerDialog({
    required this.catalog,
    required this.initialQuery,
  });

  @override
  State<_GoodsCatalogPickerDialog> createState() =>
      _GoodsCatalogPickerDialogState();
}

class _GoodsCatalogPickerDialogState extends State<_GoodsCatalogPickerDialog> {
  late final TextEditingController _searchController;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(text: widget.initialQuery);
    _query = widget.initialQuery;
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  bool _matches(GoodsCatalogEntry entry, String q) {
    final lower = q.toLowerCase();
    if (entry.nameKo.toLowerCase().contains(lower)) return true;
    if (entry.nameJa != null && entry.nameJa!.toLowerCase().contains(lower)) {
      return true;
    }
    if (entry.nameEn != null && entry.nameEn!.toLowerCase().contains(lower)) {
      return true;
    }
    if (entry.characterName.toLowerCase().contains(lower)) return true;
    if (entry.affiliation.toLowerCase().contains(lower)) return true;
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final q = _query.trim();
    // No cap — the result list is a lazy ListView.separated, so even a
    // few thousand matches only build the rows actually on screen.
    final results = q.isEmpty
        ? const <GoodsCatalogEntry>[]
        : widget.catalog.where((e) => _matches(e, q)).toList();

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520, maxHeight: 640),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
              child: Row(
                children: [
                  const Icon(Icons.search_rounded),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      '굿즈 검색',
                      style: TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w800),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                controller: _searchController,
                autofocus: true,
                onChanged: (v) => setState(() => _query = v),
                decoration: InputDecoration(
                  hintText: '이름·캐릭터·소속으로 검색',
                  isDense: true,
                  prefixIcon: const Icon(Icons.search_rounded, size: 18),
                  suffixIcon: _query.isEmpty
                      ? null
                      : IconButton(
                          icon: const Icon(Icons.close_rounded, size: 16),
                          onPressed: () {
                            _searchController.clear();
                            setState(() => _query = '');
                          },
                        ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: q.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          '굿즈 이름이나 캐릭터를 검색해 보세요.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: theme.colorScheme.onSurface
                                .withValues(alpha: 0.55),
                            fontSize: 13,
                          ),
                        ),
                      ),
                    )
                  : results.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              '검색 결과가 없어요. 직접 입력으로 추가할 수 있어요.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.55),
                                fontSize: 13,
                              ),
                            ),
                          ),
                        )
                      : ListView.separated(
                          itemCount: results.length,
                          separatorBuilder: (_, __) =>
                              Divider(height: 1, color: theme.dividerColor),
                          itemBuilder: (context, i) =>
                              _CatalogRow(entry: results[i]),
                        ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.symmetric(
                  horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  if (q.isNotEmpty)
                    Expanded(
                      child: Text(
                        '결과 ${results.length}개',
                        style: TextStyle(
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.6),
                          fontSize: 12,
                        ),
                      ),
                    )
                  else
                    const Spacer(),
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('취소'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CatalogRow extends StatelessWidget {
  final GoodsCatalogEntry entry;

  const _CatalogRow({required this.entry});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final subtitle = [
      if (entry.characterName.isNotEmpty) entry.characterName,
      if (entry.affiliation.isNotEmpty) entry.affiliation,
      if (entry.sourceStore.isNotEmpty) entry.sourceStore,
    ].join(' · ');
    final priceText = entry.officialPriceJpy == null
        ? null
        : '¥${entry.officialPriceJpy}';
    return InkWell(
      onTap: () => Navigator.pop(context, entry),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Thumbnail(imageUrl: entry.imageUrl),
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
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      height: 1.3,
                    ),
                  ),
                  if (subtitle.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11.5,
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.65),
                      ),
                    ),
                  ],
                  if (entry.category.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      entry.category,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11,
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.45),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (priceText != null) ...[
              const SizedBox(width: 8),
              Text(
                priceText,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Thumbnail extends StatelessWidget {
  final String? imageUrl;

  const _Thumbnail({required this.imageUrl});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final placeholder = Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(
        Icons.inventory_2_outlined,
        color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
        size: 24,
      ),
    );

    final url = imageUrl;
    if (url == null || url.isEmpty) return placeholder;

    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: Image.network(
        url,
        width: 56,
        height: 56,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => placeholder,
        loadingBuilder: (context, child, progress) {
          if (progress == null) return child;
          return Container(
            width: 56,
            height: 56,
            color: theme.colorScheme.surfaceContainerHighest,
            child: const Center(
              child: SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          );
        },
      ),
    );
  }
}
