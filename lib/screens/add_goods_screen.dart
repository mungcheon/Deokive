import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/calendar_event_item.dart';
import '../models/folder_item.dart';
import '../models/goods_catalog_entry.dart';
import '../models/goods_item.dart';
import '../state/app_state.dart';
import '../widgets/currency_prefix.dart';
import '../widgets/free_text_autocomplete.dart';
import '../widgets/goods_name_search_field.dart';
import 'image_catalog_search_screen.dart';

class AddGoodsScreen extends StatefulWidget {
  final FolderItem folder;

  const AddGoodsScreen({
    super.key,
    required this.folder,
  });

  @override
  State<AddGoodsScreen> createState() => _AddGoodsScreenState();
}

class _AddGoodsScreenState extends State<AddGoodsScreen> {
  final _formKey = GlobalKey<FormState>();
  final ImagePicker _imagePicker = ImagePicker();

  final TextEditingController nameController = TextEditingController();
  final TextEditingController officialPriceController = TextEditingController();
  final TextEditingController paidPriceController = TextEditingController();
  final TextEditingController seriesController = TextEditingController();
  final TextEditingController characterController = TextEditingController();
  final TextEditingController affiliationController = TextEditingController();
  final TextEditingController kindController = TextEditingController();
  final TextEditingController categoryController = TextEditingController();
  final TextEditingController companyController = TextEditingController();
  final TextEditingController memoController = TextEditingController();

  int quantity = 1;
  bool get _isWishlistFolder => widget.folder.isSystemWishlist;
  late ItemCondition itemCondition =
      _isWishlistFolder ? ItemCondition.wish : ItemCondition.unopened;
  Currency officialPriceCurrency = Currency.krw;
  Currency paidPriceCurrency = Currency.krw;
  DateTime? purchaseDate;
  DateTime? releaseDate;
  DateTime? plannedShippingDate;
  bool showDetail = false;
  bool _currencyAligned = false;

  bool get isPreorder => itemCondition == ItemCondition.preorder;
  final List<Uint8List> selectedImages = [];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // First build only: align both prices with user preference.
    if (!_currencyAligned) {
      _currencyAligned = true;
      final pref = context.read<AppState>().displayCurrency;
      if (pref != Currency.krw) {
        officialPriceCurrency = pref;
        paidPriceCurrency = pref;
      }
    }
  }

  int? get officialPrice =>
      int.tryParse(officialPriceController.text.replaceAll(',', ''));
  int? get paidPrice =>
      int.tryParse(paidPriceController.text.replaceAll(',', ''));

  int? get priceDifference {
    if (officialPrice == null || paidPrice == null) return null;
    if (officialPriceCurrency != paidPriceCurrency) return null;
    return officialPrice! - paidPrice!;
  }

  double? get priceRate {
    if (officialPrice == null || paidPrice == null || officialPrice == 0) {
      return null;
    }
    if (officialPriceCurrency != paidPriceCurrency) return null;
    return ((officialPrice! - paidPrice!) / officialPrice!) * 100;
  }

  String _compareLabel(int diff) {
    if (diff > 0) return '절약';
    if (diff < 0) return '초과';
    return '동일';
  }

  String _formatCompareText(int diff, double rate) {
    final symbol = paidPriceCurrency.symbol;
    return '${_compareLabelFixed(diff)} $symbol${diff.abs()} (${rate.toStringAsFixed(1)}%)';
  }

  String _compareLabelFixed(int diff) {
    if (diff > 0) return '절약';
    if (diff < 0) return '초과';
    return '동일';
  }

  String _conditionLabelFixed(ItemCondition condition) {
    switch (condition) {
      case ItemCondition.wish:
        return '위시';
      case ItemCondition.unopened:
        return '미개봉';
      case ItemCondition.opened:
        return '개봉';
      case ItemCondition.used:
        return '중고';
      case ItemCondition.preorder:
        return '예약구매';
    }
  }

  String _conditionLabel(ItemCondition condition) {
    switch (condition) {
      case ItemCondition.wish:
        return '사고싶다';
      case ItemCondition.unopened:
        return '미개봉';
      case ItemCondition.opened:
        return '단순개봉';
      case ItemCondition.used:
        return '중고';
      case ItemCondition.preorder:
        return '예약구매';
    }
  }

  Future<DateTime?> _pickDate(DateTime? initial) {
    final now = DateTime.now();
    return showDatePicker(
      context: context,
      initialDate: initial ?? now,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
  }

  Future<void> _addImage({required ImageSource source}) async {
    final result = await _imagePicker.pickImage(
      source: source,
      imageQuality: 92,
    );
    if (result == null || !mounted) return;
    final bytes = await result.readAsBytes();
    final edited = await _openGoodsImageEditor(bytes);
    if (edited == null || !mounted) return;
    setState(() {
      selectedImages.add(edited);
    });
  }

  Future<void> _chooseImageSource() async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.photo_camera_outlined),
                title: const Text('카메라로 촬영'),
                onTap: () async {
                  Navigator.pop(sheetContext);
                  await _addImage(source: ImageSource.camera);
                },
              ),
              ListTile(
                leading: const Icon(Icons.photo_library_outlined),
                title: const Text('앨범에서 선택'),
                onTap: () async {
                  Navigator.pop(sheetContext);
                  await _addImage(source: ImageSource.gallery);
                },
              ),
              ListTile(
                leading: const Icon(Icons.collections_bookmark_outlined),
                title: const Text('이미지 검색'),
                onTap: () async {
                  Navigator.pop(sheetContext);
                  await _openCatalogPicker();
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _openCatalogPicker() async {
    final picked = await showGoodsCatalogPicker(
      context,
      catalog: context.read<AppState>().curatedCatalogEntries,
      initialQuery: nameController.text.trim(),
    );
    if (picked == null || !mounted) return;
    nameController.text = picked.nameKo;
    await _applyCatalogEntry(picked);
  }

  Future<void> _openImageSearch() async {
    final picked = await Navigator.push<GoodsCatalogEntry>(
      context,
      MaterialPageRoute(builder: (_) => const ImageCatalogSearchScreen()),
    );
    if (picked == null || !mounted) return;
    nameController.text = picked.nameKo;
    await _applyCatalogEntry(picked);
  }

  Future<bool> _confirmAddShippingSchedule(DateTime shippingDate) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('캘린더에 추가'),
          content: Text(
            '발송 예정일 ${shippingDate.year}-${shippingDate.month.toString().padLeft(2, '0')}-${shippingDate.day.toString().padLeft(2, '0')} 을(를) 캘린더 일정으로 추가할까요?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('추가 안 함'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('추가'),
            ),
          ],
        );
      },
    );
    return result ?? false;
  }

  Future<void> _saveGoods() async {
    if (!_formKey.currentState!.validate()) return;
    if (categoryController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('카테고리를 선택해주세요.')),
      );
      return;
    }
    final item = GoodsItem(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      folderId: widget.folder.id,
      name: nameController.text.trim(),
      category: categoryController.text.trim(),
      kind: kindController.text.trim().isEmpty
          ? null
          : kindController.text.trim(),
      quantity: quantity,
      officialPrice: officialPrice,
      paidPrice: paidPrice,
      purchaseDate: purchaseDate,
      isPreorder: isPreorder,
      itemCondition: itemCondition,
      seriesName: seriesController.text.trim(),
      characterName: characterController.text.trim(),
      affiliation: affiliationController.text.trim().isEmpty
          ? null
          : affiliationController.text.trim(),
      companyName: companyController.text.trim().isEmpty
          ? null
          : companyController.text.trim(),
      purchasePlace: null,
      releaseDate: releaseDate,
      memo: memoController.text.trim().isEmpty
          ? null
          : memoController.text.trim(),
      plannedShippingDate: isPreorder ? plannedShippingDate : null,
      status: _conditionLabelFixed(itemCondition),
      purchaseState: _isWishlistFolder
          ? PurchaseState.wished
          : (isPreorder ? PurchaseState.ordered : PurchaseState.owned),
      wishlistTargetFolderId: null,
      barcode: null,
      storageLocation: null,
      imageBytesList: List<Uint8List>.from(selectedImages),
      isFavorite: false,
      priceCurrencyCode: paidPriceCurrency.code,
      officialPriceCurrencyCode: officialPriceCurrency.code,
    );

    if (isPreorder && plannedShippingDate != null) {
      final shouldAdd = await _confirmAddShippingSchedule(plannedShippingDate!);
      if (!mounted) return;
      if (shouldAdd) {
        final appState = context.read<AppState>();
        appState.addCalendarEvent(
          CalendarEventItem(
            id: appState.makeId(),
            date: plannedShippingDate!,
            title: '${nameController.text.trim()} 발송 예정',
            timeText: null,
            memo: '${widget.folder.name} 폴더 예약구매 굿즈 발송 예정일',
            type: CalendarEventType.release,
          ),
        );
      }
    }

    if (!mounted) return;
    Navigator.pop(context, item);
  }

  @override
  void dispose() {
    nameController.dispose();
    officialPriceController.dispose();
    paidPriceController.dispose();
    seriesController.dispose();
    characterController.dispose();
    affiliationController.dispose();
    kindController.dispose();
    categoryController.dispose();
    companyController.dispose();
    memoController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final curatedCatalog = appState.curatedCatalogEntries;
    final diff = priceDifference;
    final rate = priceRate;

    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.folder.name} 굿즈 추가'),
        actions: [
          IconButton(
            tooltip: '이미지로 비슷한 굿즈 찾기',
            onPressed: _openImageSearch,
            icon: const Icon(Icons.image_search_rounded),
          ),
        ],
      ),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _PhotoStrip(
                images: selectedImages,
                onAdd: _chooseImageSource,
                onRemove: (index) =>
                    setState(() => selectedImages.removeAt(index)),
              ),
              const SizedBox(height: 20),
              GoodsNameSearchField(
                controller: nameController,
                catalog: curatedCatalog,
                onCatalogSelected: _applyCatalogEntry,
              ),
              const SizedBox(height: 16),
              FreeTextAutocomplete(
                controller: seriesController,
                suggestions: _mergedSuggestions(
                  appState.knownSeriesNames,
                  appState.curatedCatalogSeriesNames,
                ),
                labelText: '시리즈',
              ),
              const SizedBox(height: 16),
              FreeTextAutocomplete(
                controller: categoryController,
                suggestions: _categorySuggestions(appState),
                labelText: '카테고리',
                required: true,
              ),
              const SizedBox(height: 16),
              FreeTextAutocomplete(
                controller: kindController,
                suggestions: const [],
                labelText: '종류',
              ),
              const SizedBox(height: 16),
              FreeTextAutocomplete(
                controller: characterController,
                suggestions: _mergedSuggestions(
                  appState.knownCharacterNames,
                  appState.curatedCatalogCharacterNames,
                ),
                labelText: '캐릭터',
              ),
              const SizedBox(height: 16),
              FreeTextAutocomplete(
                controller: affiliationController,
                suggestions: appState.curatedCatalogAffiliations,
                labelText: '소속 (아이돌 그룹/애니메이션 등)',
              ),
              const SizedBox(height: 16),
              _QuantityField(
                quantity: quantity,
                onChanged: (value) => setState(() => quantity = value),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: officialPriceController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        labelText: '정가',
                        prefixIcon: CurrencyPrefix(
                          currency: officialPriceCurrency,
                          onSelected: (c) =>
                              setState(() => officialPriceCurrency = c),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: paidPriceController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        labelText: '실구매가',
                        prefixIcon: CurrencyPrefix(
                          currency: paidPriceCurrency,
                          onSelected: (c) =>
                              setState(() => paidPriceCurrency = c),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              if (diff != null && rate != null) ...[
                const SizedBox(height: 12),
                Card(
                  margin: EdgeInsets.zero,
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const Icon(Icons.calculate_outlined),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _formatCompareText(diff, rate),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              InkWell(
                onTap: () async {
                  final picked = await _pickDate(purchaseDate);
                  if (picked != null) setState(() => purchaseDate = picked);
                },
                child: InputDecorator(
                  decoration: const InputDecoration(labelText: '구매 날짜'),
                  child: Text(
                    purchaseDate == null
                        ? '날짜 선택'
                        : '${purchaseDate!.year}-${purchaseDate!.month.toString().padLeft(2, '0')}-${purchaseDate!.day.toString().padLeft(2, '0')}',
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text('상품 상태',
                  style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: (_isWishlistFolder
                        ? const [ItemCondition.wish]
                        : ItemCondition.values
                            .where((c) => c != ItemCondition.wish))
                    .map((condition) {
                  return ChoiceChip(
                    label: Text(_conditionLabelFixed(condition)),
                    selected: itemCondition == condition,
                    onSelected: _isWishlistFolder
                        ? null
                        : (_) {
                            setState(() {
                              itemCondition = condition;
                              if (!isPreorder) plannedShippingDate = null;
                            });
                          },
                  );
                }).toList(),
              ),
              if (isPreorder) ...[
                const SizedBox(height: 12),
                InkWell(
                  onTap: () async {
                    final picked =
                        await _pickDate(plannedShippingDate ?? purchaseDate);
                    if (picked != null) {
                      setState(() => plannedShippingDate = picked);
                    }
                  },
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: '발송 예정일'),
                    child: Text(
                      plannedShippingDate == null
                          ? '날짜 선택'
                          : '${plannedShippingDate!.year}-${plannedShippingDate!.month.toString().padLeft(2, '0')}-${plannedShippingDate!.day.toString().padLeft(2, '0')}',
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed: () => setState(() => showDetail = !showDetail),
                child: Text(showDetail ? '상세 입력 닫기' : '상세 입력 열기'),
              ),
              if (showDetail) ...[
                const SizedBox(height: 16),
                FreeTextAutocomplete(
                  controller: companyController,
                  suggestions: const [],
                  labelText: '공식 판매처',
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: () async {
                    final picked = await _pickDate(releaseDate);
                    if (picked != null) setState(() => releaseDate = picked);
                  },
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: '발매일'),
                    child: Text(
                      releaseDate == null
                          ? '날짜 선택'
                          : '${releaseDate!.year}-${releaseDate!.month.toString().padLeft(2, '0')}-${releaseDate!.day.toString().padLeft(2, '0')}',
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: memoController,
                  minLines: 3,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    labelText: '메모',
                    alignLabelWithHint: true,
                  ),
                ),
              ],
              const SizedBox(height: 28),
              SizedBox(
                height: 52,
                child: FilledButton(
                  onPressed: _saveGoods,
                  child: const Text('저장'),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  List<String> _categorySuggestions(AppState appState) {
    // Default labels + categories the user has already entered + categories
    // that exist in the curated catalog (Chiikawa goods, etc.).
    const defaultLabels = <String>[
      '피규어',
      '봉제 인형',
      '포스터',
      '카드',
      '뱃지',
      '키링',
      '스티커',
      '스탠디',
      '포토카드',
      '아트북',
      '의류',
      '액세서리',
      '기타',
    ];
    return {
      ...defaultLabels,
      ...appState.knownCategories,
      ...appState.curatedCatalogCategories,
    }.toList()
      ..sort();
  }

  /// Merge user-entered values with curated catalog values, deduped and sorted.
  List<String> _mergedSuggestions(List<String> a, List<String> b) {
    return {...a, ...b}.toList()..sort();
  }

  /// Auto-fill metadata fields when the user picks a catalog entry. Every
  /// catalog-known field overwrites the current input — the user can edit
  /// freely after. Series is intentionally skipped because the curated series
  /// labels aren't trusted yet (per user feedback).
  Future<void> _applyCatalogEntry(GoodsCatalogEntry entry) async {
    setState(() {
      if (entry.normalizedCategory.isNotEmpty) {
        categoryController.text = entry.normalizedCategory;
      }
      if (entry.characterName.isNotEmpty) {
        characterController.text = entry.characterName;
      }
      if (entry.affiliation.isNotEmpty) {
        affiliationController.text = entry.affiliation;
      }
      if (entry.subSeries != null && entry.subSeries!.isNotEmpty) {
        kindController.text = entry.subSeries!;
      }
      if (entry.officialPriceJpy != null) {
        final price = entry.officialPriceJpy.toString();
        officialPriceController.text = price;
        paidPriceController.text = price;
        officialPriceCurrency = Currency.jpy;
        paidPriceCurrency = Currency.jpy;
      } else if (entry.officialPriceKrw != null) {
        final price = entry.officialPriceKrw.toString();
        officialPriceController.text = price;
        paidPriceController.text = price;
        officialPriceCurrency = Currency.krw;
        paidPriceCurrency = Currency.krw;
      } else {
        // Prize/kuji/gashapon figures often have no retail price — default
        // to 0 so the field shows a value instead of being blank. User can
        // overwrite if they know the price.
        officialPriceController.text = '0';
        paidPriceController.text = '0';
      }
      if (entry.sourceStore.isNotEmpty) {
        companyController.text = entry.sourceStore;
      }
      if (entry.officialPriceJpy != null) {
        // Catalog official prices are listed in JPY — align both currencies
        // to JPY by default so the diff calculation is meaningful. User can
        // still change the paid currency afterward.
        officialPriceCurrency = Currency.jpy;
        paidPriceCurrency = Currency.jpy;
      }
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          entry.officialPriceJpy != null
              ? '카탈로그 정보를 채웠습니다. 정가는 ¥${entry.officialPriceJpy} (JPY) — 통화를 확인하세요.'
              : '카탈로그 정보를 채웠습니다. 정가는 0으로 표기 — 필요하면 수정해 주세요.',
        ),
        duration: const Duration(seconds: 3),
      ),
    );
    _maybeWarnDuplicate(entry);
    await _attachCatalogImage(entry);
  }

  Future<void> _attachCatalogImage(GoodsCatalogEntry entry) async {
    final localPath = entry.localImagePath?.trim() ?? '';
    if (localPath.isNotEmpty) {
      final localBytes = await _downloadImageBytes(localPath);
      if (!mounted) return;
      if (localBytes != null) {
        setState(() => selectedImages.add(localBytes));
        return;
      }
    }

    final raw = entry.imageUrl?.trim() ?? '';
    if (raw.isEmpty) return; // catalog entry has no image — nothing to attach
    var url = raw.replaceAll('&amp;', '&');
    if (url.startsWith('//')) url = 'https:$url';
    if (!url.startsWith('http')) return;
    final messenger = ScaffoldMessenger.of(context);
    final bytes = await _downloadImageBytes(url);
    if (!mounted) return;
    if (bytes == null) {
      // Surface the failure instead of silently doing nothing, so the user
      // knows to add a photo manually.
      messenger.showSnackBar(const SnackBar(
        content: Text('카탈로그 이미지를 불러오지 못했어요. 사진을 직접 추가해 주세요.'),
      ));
      return;
    }
    setState(() => selectedImages.add(bytes));
  }

  Future<Uint8List?> _downloadImageBytes(String url) async {
    try {
      final uri = Uri.parse(url);
      final response = await http.get(
        uri.hasScheme ? uri : Uri.base.resolve(url),
        headers: const {
          'User-Agent': 'Mozilla/5.0 (Linux; Android) Deokive/1.0',
          'Accept': 'image/*,*/*',
        },
      ).timeout(const Duration(seconds: 12));
      if (response.statusCode != 200 || response.bodyBytes.isEmpty) {
        return null;
      }
      return response.bodyBytes;
    } catch (_) {
      return null;
    }
  }

  void _maybeWarnDuplicate(GoodsCatalogEntry entry) {
    final appState = context.read<AppState>();
    final pickedName = entry.nameKo.trim();
    if (pickedName.isEmpty) return;
    final matches =
        appState.goodsItems.where((g) => g.name.trim() == pickedName).toList();
    if (matches.isEmpty) return;
    final folderNameById = {
      for (final f in appState.folders) f.id: f.name,
    };
    final folderLines = matches
        .map((g) => folderNameById[g.folderId] ?? '알 수 없는 폴더')
        .toSet()
        .toList();
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('이미 있는 굿즈예요'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '"$pickedName" 굿즈를 이미 ${matches.length}개 가지고 있어요.',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text('보관 폴더: ${folderLines.join(", ")}'),
            const SizedBox(height: 12),
            const Text(
              '상태(개봉/미개봉/예약 등)가 다르면 그대로 새로 추가해도 돼요.',
              style: TextStyle(fontSize: 12),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('확인'),
          ),
        ],
      ),
    );
  }

  Future<Uint8List?> _openGoodsImageEditor(Uint8List originalBytes) async {
    final codec = await ui.instantiateImageCodec(originalBytes);
    final frame = await codec.getNextFrame();
    final image = frame.image;
    const previewSize = 220.0;
    final baseScale = math.max(
      previewSize / image.width,
      previewSize / image.height,
    );
    double zoom = 1;
    double offsetX = 0;
    double offsetY = 0;

    return showDialog<Uint8List>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            double maxOffsetX() {
              final displayedWidth = image.width * baseScale * zoom;
              return math.max(0, (displayedWidth - previewSize) / 2);
            }

            double maxOffsetY() {
              final displayedHeight = image.height * baseScale * zoom;
              return math.max(0, (displayedHeight - previewSize) / 2);
            }

            void clampOffsets() {
              offsetX = offsetX.clamp(-maxOffsetX(), maxOffsetX());
              offsetY = offsetY.clamp(-maxOffsetY(), maxOffsetY());
            }

            final displayedWidth = image.width * baseScale * zoom;
            final displayedHeight = image.height * baseScale * zoom;
            final left = (previewSize - displayedWidth) / 2 + offsetX;
            final top = (previewSize - displayedHeight) / 2 + offsetY;

            Future<Uint8List> exportImage() async {
              final scale = baseScale * zoom;
              final cropLeft =
                  ((image.width * scale - previewSize) / 2 - offsetX) / scale;
              final cropTop =
                  ((image.height * scale - previewSize) / 2 - offsetY) / scale;
              final cropSize = previewSize / scale;
              final srcRect = Rect.fromLTWH(
                cropLeft
                    .clamp(0, math.max(0, image.width - cropSize))
                    .toDouble(),
                cropTop
                    .clamp(0, math.max(0, image.height - cropSize))
                    .toDouble(),
                cropSize.clamp(1, image.width.toDouble()).toDouble(),
                cropSize.clamp(1, image.height.toDouble()).toDouble(),
              );
              const outputSize = 900.0;
              final recorder = ui.PictureRecorder();
              final canvas = Canvas(recorder);
              canvas.drawImageRect(
                image,
                srcRect,
                const Rect.fromLTWH(0, 0, outputSize, outputSize),
                Paint(),
              );
              final rendered = await recorder.endRecording().toImage(
                    outputSize.toInt(),
                    outputSize.toInt(),
                  );
              final byteData =
                  await rendered.toByteData(format: ui.ImageByteFormat.png);
              return byteData!.buffer.asUint8List();
            }

            return AlertDialog(
              title: const Text('굿즈 사진 조정'),
              content: SizedBox(
                width: 360,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: SizedBox(
                          width: previewSize,
                          height: previewSize,
                          child: GestureDetector(
                            onPanUpdate: (details) {
                              setDialogState(() {
                                offsetX += details.delta.dx;
                                offsetY += details.delta.dy;
                                clampOffsets();
                              });
                            },
                            child: Stack(
                              children: [
                                Positioned.fill(
                                  child: Container(color: Colors.black12),
                                ),
                                Positioned(
                                  left: left,
                                  top: top,
                                  child: Image.memory(
                                    originalBytes,
                                    width: displayedWidth,
                                    height: displayedHeight,
                                    fit: BoxFit.cover,
                                  ),
                                ),
                                const Positioned.fill(
                                  child: IgnorePointer(
                                    child: CustomPaint(
                                      painter: _GoodsCropGridPainter(),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      '사진을 드래그해서 위치를 맞춰주세요.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    const Text('확대'),
                    Slider(
                      value: zoom,
                      min: 1,
                      max: 3,
                      onChanged: (value) {
                        setDialogState(() {
                          zoom = value;
                          clampOffsets();
                        });
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () async {
                    final cropped = await exportImage();
                    if (!dialogContext.mounted) return;
                    Navigator.pop(dialogContext, cropped);
                  },
                  child: const Text('적용'),
                ),
              ],
            );
          },
        );
      },
    );
  }
}

class _PhotoStrip extends StatelessWidget {
  final List<Uint8List> images;
  final VoidCallback onAdd;
  final void Function(int index) onRemove;

  const _PhotoStrip({
    required this.images,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: images.length + 1,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (context, index) {
          if (index == images.length) {
            return InkWell(
              onTap: onAdd,
              borderRadius: BorderRadius.circular(16),
              child: Container(
                width: 110,
                height: 110,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outline,
                  ),
                ),
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.add_a_photo_outlined, size: 28),
                    SizedBox(height: 6),
                    Text('사진 추가', style: TextStyle(fontSize: 12)),
                  ],
                ),
              ),
            );
          }
          return Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.memory(
                  images[index],
                  width: 110,
                  height: 110,
                  fit: BoxFit.cover,
                ),
              ),
              Positioned(
                top: 2,
                right: 2,
                child: InkWell(
                  onTap: () => onRemove(index),
                  child: Container(
                    decoration: const BoxDecoration(
                      color: Colors.black54,
                      shape: BoxShape.circle,
                    ),
                    padding: const EdgeInsets.all(4),
                    child:
                        const Icon(Icons.close, color: Colors.white, size: 16),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _QuantityField extends StatelessWidget {
  final int quantity;
  final ValueChanged<int> onChanged;

  const _QuantityField({
    required this.quantity,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Text('개수',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        const SizedBox(width: 12),
        SizedBox(
          width: 28,
          height: 28,
          child: IconButton.filledTonal(
            padding: EdgeInsets.zero,
            visualDensity: VisualDensity.compact,
            onPressed: quantity > 1 ? () => onChanged(quantity - 1) : null,
            icon: const Icon(Icons.remove, size: 14),
          ),
        ),
        SizedBox(
          width: 36,
          child: Center(
            child: Text(
              '$quantity',
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
            ),
          ),
        ),
        SizedBox(
          width: 28,
          height: 28,
          child: IconButton.filledTonal(
            padding: EdgeInsets.zero,
            visualDensity: VisualDensity.compact,
            onPressed: () => onChanged(quantity + 1),
            icon: const Icon(Icons.add, size: 14),
          ),
        ),
      ],
    );
  }
}

class _GoodsCropGridPainter extends CustomPainter {
  const _GoodsCropGridPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final borderPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.9)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.4;
    final gridPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.38)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    canvas.drawRect(Offset.zero & size, borderPaint);
    final thirdX = size.width / 3;
    final thirdY = size.height / 3;
    canvas.drawLine(Offset(thirdX, 0), Offset(thirdX, size.height), gridPaint);
    canvas.drawLine(
        Offset(thirdX * 2, 0), Offset(thirdX * 2, size.height), gridPaint);
    canvas.drawLine(Offset(0, thirdY), Offset(size.width, thirdY), gridPaint);
    canvas.drawLine(
        Offset(0, thirdY * 2), Offset(size.width, thirdY * 2), gridPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
