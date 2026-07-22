import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/goods_item.dart';
import '../state/app_state.dart';
import 'edit_goods_screen.dart';

class GoodsDetailScreen extends StatefulWidget {
  final GoodsItem item;
  final List<GoodsItem> galleryItems;

  const GoodsDetailScreen({
    super.key,
    required this.item,
    this.galleryItems = const [],
  });

  @override
  State<GoodsDetailScreen> createState() => _GoodsDetailScreenState();
}

class _GoodsDetailScreenState extends State<GoodsDetailScreen> {
  late final PageController _goodsPageController;
  late int _currentPage;

  List<GoodsItem> get _initialGallery {
    final source = widget.galleryItems.isEmpty
        ? <GoodsItem>[widget.item]
        : widget.galleryItems;
    if (source.any((item) => item.id == widget.item.id)) {
      return source;
    }
    return [widget.item, ...source];
  }

  @override
  void initState() {
    super.initState();
    final initialIndex = _initialGallery.indexWhere(
      (candidate) => candidate.id == widget.item.id,
    );
    _currentPage = initialIndex < 0 ? 0 : initialIndex;
    _goodsPageController = PageController(initialPage: _currentPage);
  }

  @override
  void dispose() {
    _goodsPageController.dispose();
    super.dispose();
  }

  String formatDate(DateTime? date) {
    if (date == null) return '-';
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }

  String _formatPrice(int? amount, String currencyCode, AppState appState) {
    if (amount == null) return '-';
    final c = appState.currencyByCode(currencyCode);
    return '${c.symbol}$amount';
  }

  String priceCompareText(GoodsItem item, AppState appState) {
    final official = item.officialPrice;
    final paid = item.paidPrice;
    if (official == null || paid == null) return '-';
    final paidCur = appState.currencyByCode(item.priceCurrencyCode);
    final officialCur =
        appState.currencyByCode(item.effectiveOfficialPriceCurrencyCode);

    final officialInPaid =
        appState.convertCurrency(official, officialCur, paidCur);
    final diff = officialInPaid - paid;
    if (officialInPaid == 0) return '-';
    final ratePct = (diff / officialInPaid) * 100;
    final symbol = paidCur.symbol;

    if (diff == 0) return '정가 구매';
    final crossCurrency = officialCur != paidCur;
    final convertedNote =
        crossCurrency ? ' (정가 환산 $symbol$officialInPaid)' : '';
    if (diff > 0) {
      return '$symbol${diff.abs()} 이득 (${ratePct.abs().toStringAsFixed(1)}%)$convertedNote';
    }
    return '$symbol${diff.abs()} 손해 (${ratePct.abs().toStringAsFixed(1)}%)$convertedNote';
  }

  Future<void> _showPurchaseDialog(
    BuildContext context,
    AppState appState,
    GoodsItem currentItem,
  ) async {
    final targets = appState.owningFolders;
    if (targets.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('이동할 폴더가 없습니다. 먼저 폴더를 만들어 주세요.')),
      );
      return;
    }
    String? selectedFolderId = currentItem.wishlistTargetFolderId ??
        (targets.isNotEmpty ? targets.first.id : null);
    final chosen = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            return AlertDialog(
              title: const Text('구매 완료로 표시'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('어느 폴더로 옮길까요?'),
                  const SizedBox(height: 12),
                  DropdownButton<String>(
                    value: selectedFolderId,
                    isExpanded: true,
                    items: targets
                        .map((folder) => DropdownMenuItem(
                              value: folder.id,
                              child: Text(folder.name),
                            ))
                        .toList(),
                    onChanged: (value) =>
                        setLocalState(() => selectedFolderId = value),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: selectedFolderId == null
                      ? null
                      : () => Navigator.pop(dialogContext, selectedFolderId),
                  child: const Text('이동'),
                ),
              ],
            );
          },
        );
      },
    );
    if (chosen != null) {
      appState.markGoodsAsPurchased(currentItem.id, chosen);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('보유 폴더로 이동했어요.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final gallery = _liveGalleryItems(appState);
        if (_currentPage >= gallery.length) {
          _currentPage = gallery.length - 1;
        }
        final currentItem = gallery[_currentPage];

        return Scaffold(
          appBar: AppBar(
            title: const Text('굿즈 상세'),
            actions: [
              if (currentItem.isWishlistItem)
                IconButton(
                  tooltip: '구매 완료로 표시',
                  onPressed: () =>
                      _showPurchaseDialog(context, appState, currentItem),
                  icon: const Icon(Icons.shopping_bag_outlined),
                ),
              IconButton(
                onPressed: () => appState.toggleFavorite(currentItem.id),
                icon: Icon(
                  currentItem.isFavorite
                      ? Icons.favorite
                      : Icons.favorite_border,
                  color: currentItem.isFavorite ? Colors.pink : null,
                ),
              ),
              IconButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => EditGoodsScreen(item: currentItem),
                    ),
                  );
                },
                icon: const Icon(Icons.edit_outlined),
              ),
            ],
          ),
          body: Stack(
            children: [
              PageView.builder(
                controller: _goodsPageController,
                itemCount: gallery.length,
                onPageChanged: (index) => setState(() => _currentPage = index),
                itemBuilder: (context, index) {
                  final pageItem = gallery[index];
                  return _GoodsDetailPage(
                    item: pageItem,
                    folderName: _folderNameFor(appState, pageItem),
                    appState: appState,
                    formatDate: formatDate,
                    formatPrice: _formatPrice,
                    priceCompareText: priceCompareText,
                  );
                },
              ),
              if (gallery.length > 1)
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 12,
                  child: Center(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .surface
                            .withValues(alpha: 0.92),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: Theme.of(context)
                              .colorScheme
                              .outline
                              .withValues(alpha: 0.2),
                        ),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        child: Text(
                          '${_currentPage + 1} / ${gallery.length}',
                          style: Theme.of(context).textTheme.labelMedium,
                        ),
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

  List<GoodsItem> _liveGalleryItems(AppState appState) {
    final byId = {
      for (final item in appState.goodsItems) item.id: item,
    };
    final items = <GoodsItem>[];
    final seen = <String>{};
    for (final item in _initialGallery) {
      final liveItem = byId[item.id] ?? item;
      if (seen.add(liveItem.id)) {
        items.add(liveItem);
      }
    }
    return items.isEmpty ? [widget.item] : items;
  }

  String _folderNameFor(AppState appState, GoodsItem item) {
    for (final folder in appState.folders) {
      if (folder.id == item.folderId) {
        return folder.name;
      }
    }
    return '-';
  }
}

class _GoodsDetailPage extends StatelessWidget {
  final GoodsItem item;
  final String folderName;
  final AppState appState;
  final String Function(DateTime?) formatDate;
  final String Function(int?, String, AppState) formatPrice;
  final String Function(GoodsItem, AppState) priceCompareText;

  const _GoodsDetailPage({
    required this.item,
    required this.folderName,
    required this.appState,
    required this.formatDate,
    required this.formatPrice,
    required this.priceCompareText,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 56),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Column(
              children: [
                _GoodsImageCarousel(item: item),
                const SizedBox(height: 20),
                _SectionCard(
                  children: [
                    _InfoRow(label: '이름', value: item.name),
                    _InfoRow(
                      label: '시리즈',
                      value: item.seriesName.isEmpty ? '-' : item.seriesName,
                    ),
                    _InfoRow(label: '카테고리', value: item.category),
                    _InfoRow(label: '폴더', value: folderName),
                    _InfoRow(label: '상태', value: item.status),
                    _InfoRow(label: '개수', value: '${item.quantity}'),
                  ],
                ),
                const SizedBox(height: 14),
                _SectionCard(
                  children: [
                    _InfoRow(
                      label: '정가',
                      value: formatPrice(
                        item.officialPrice,
                        item.effectiveOfficialPriceCurrencyCode,
                        appState,
                      ),
                    ),
                    _InfoRow(
                      label: '구매가',
                      value: formatPrice(
                        item.paidPrice,
                        item.priceCurrencyCode,
                        appState,
                      ),
                    ),
                    _InfoRow(
                      label: '가격 비교',
                      value: priceCompareText(item, appState),
                    ),
                    _InfoRow(
                      label: '구매 날짜',
                      value: formatDate(item.purchaseDate),
                    ),
                    _InfoRow(
                      label: '제조사',
                      value: item.companyName ?? '-',
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                _SectionCard(
                  children: [
                    _InfoRow(label: '메모', value: item.memo ?? '-'),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _GoodsImageCarousel extends StatefulWidget {
  final GoodsItem item;

  const _GoodsImageCarousel({required this.item});

  @override
  State<_GoodsImageCarousel> createState() => _GoodsImageCarouselState();
}

class _GoodsImageCarouselState extends State<_GoodsImageCarousel> {
  late final PageController _pageController;
  Timer? _autoSlideTimer;
  int _currentPage = 0;

  List<Uint8List> get _images => widget.item.imageBytesList;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _restartAutoSlide();
  }

  @override
  void didUpdateWidget(covariant _GoodsImageCarousel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.item.id != widget.item.id ||
        oldWidget.item.imageBytesList.length !=
            widget.item.imageBytesList.length) {
      _currentPage = 0;
      _pageController.jumpToPage(0);
      _restartAutoSlide();
    }
  }

  @override
  void dispose() {
    _autoSlideTimer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  void _restartAutoSlide() {
    _autoSlideTimer?.cancel();
    if (_images.length < 2) return;
    _autoSlideTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (!mounted || !_pageController.hasClients) return;
      final nextPage = (_currentPage + 1) % _images.length;
      _pageController.animateToPage(
        nextPage,
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeInOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 280,
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(22),
      ),
      clipBehavior: Clip.antiAlias,
      child: _images.isEmpty
          ? const Center(
              child: Icon(Icons.image_outlined, size: 56),
            )
          : Stack(
              alignment: Alignment.bottomCenter,
              children: [
                PageView.builder(
                  controller: _pageController,
                  itemCount: _images.length,
                  onPageChanged: (index) {
                    setState(() {
                      _currentPage = index;
                    });
                  },
                  itemBuilder: (context, index) {
                    return Image.memory(
                      _images[index],
                      fit: BoxFit.cover,
                    );
                  },
                ),
                if (_images.length > 1)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.28),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: List.generate(_images.length, (index) {
                            final selected = index == _currentPage;
                            return AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              width: selected ? 16 : 6,
                              height: 6,
                              margin: const EdgeInsets.symmetric(horizontal: 2),
                              decoration: BoxDecoration(
                                color: selected
                                    ? Colors.white
                                    : Colors.white.withValues(alpha: 0.45),
                                borderRadius: BorderRadius.circular(999),
                              ),
                            );
                          }),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final List<Widget> children;

  const _SectionCard({required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.12),
        ),
      ),
      child: Column(
        children: children,
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 96,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: Colors.grey.shade700,
                  ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}
