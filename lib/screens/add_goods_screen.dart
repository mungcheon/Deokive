import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/calendar_event_item.dart';
import '../models/folder_item.dart';
import '../models/goods_item.dart';
import '../services/barcode_lookup_service.dart';
import '../state/app_state.dart';
import 'barcode_scan_screen.dart';

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
  final TextEditingController companyController = TextEditingController();
  final TextEditingController storeController = TextEditingController();
  final TextEditingController memoController = TextEditingController();
  final TextEditingController storageLocationController = TextEditingController();

  int quantity = 1;
  String? selectedCategory;
  String selectedStatus = '미개봉';
  DateTime? purchaseDate;
  DateTime? plannedShippingDate;
  bool isPreorder = false;
  bool showDetail = false;
  Uint8List? selectedImageBytes;
  String? scannedBarcodeValue;

  final List<String> categories = const [
    '포토카드 / 지류',
    '피규어 / 굿즈',
    '의류 / 패션',
    '음반 / 출판',
    '문구 / 생활',
    '이벤트 / 한정',
    '기타',
  ];

  final List<String> statuses = const [
    '미개봉',
    '개봉',
    '중고',
  ];

  int? get officialPrice => int.tryParse(officialPriceController.text.replaceAll(',', ''));
  int? get paidPrice => int.tryParse(paidPriceController.text.replaceAll(',', ''));

  int? get priceDifference {
    if (officialPrice == null || paidPrice == null) return null;
    return officialPrice! - paidPrice!;
  }

  double? get priceRate {
    if (officialPrice == null || paidPrice == null || officialPrice == 0) {
      return null;
    }
    return ((officialPrice! - paidPrice!) / officialPrice!) * 100;
  }

  String getCompareLabel(int diff) {
    if (diff > 0) return '절약';
    if (diff < 0) return '초과';
    return '동일';
  }

  Future<void> pickDate() async {
    final now = DateTime.now();
    final result = await showDatePicker(
      context: context,
      initialDate: purchaseDate ?? now,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (result != null) {
      setState(() {
        purchaseDate = result;
      });
    }
  }

  Future<void> pickPlannedShippingDate() async {
    final now = DateTime.now();
    final result = await showDatePicker(
      context: context,
      initialDate: plannedShippingDate ?? purchaseDate ?? now,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (result != null) {
      setState(() {
        plannedShippingDate = result;
      });
    }
  }

  Future<void> pickImage() async {
    final result = await _imagePicker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 92,
    );
    if (result == null || !mounted) return;
    final bytes = await result.readAsBytes();
    final edited = await _openGoodsImageEditor(bytes);
    if (edited == null || !mounted) return;
    setState(() {
      selectedImageBytes = edited;
    });
  }

  Future<void> takePhoto() async {
    final result = await _imagePicker.pickImage(
      source: ImageSource.camera,
      imageQuality: 92,
    );
    if (result == null || !mounted) return;
    final bytes = await result.readAsBytes();
    final edited = await _openGoodsImageEditor(bytes);
    if (edited == null || !mounted) return;
    setState(() {
      selectedImageBytes = edited;
    });
  }

  Future<void> chooseImageSource() async {
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
                  await takePhoto();
                },
              ),
              ListTile(
                leading: const Icon(Icons.photo_library_outlined),
                title: const Text('앨범에서 선택'),
                onTap: () async {
                  Navigator.pop(sheetContext);
                  await pickImage();
                },
              ),
            ],
          ),
        );
      },
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
              final cropLeft = ((image.width * scale - previewSize) / 2 - offsetX) / scale;
              final cropTop = ((image.height * scale - previewSize) / 2 - offsetY) / scale;
              final cropSize = previewSize / scale;
              final srcRect = Rect.fromLTWH(
                cropLeft.clamp(0, math.max(0, image.width - cropSize)).toDouble(),
                cropTop.clamp(0, math.max(0, image.height - cropSize)).toDouble(),
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
              final byteData = await rendered.toByteData(format: ui.ImageByteFormat.png);
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
                    const Text('좌우 위치'),
                    Slider(
                      value: offsetX,
                      min: -maxOffsetX(),
                      max: maxOffsetX() == 0 ? 0.0001 : maxOffsetX(),
                      onChanged: maxOffsetX() == 0
                          ? null
                          : (value) {
                              setDialogState(() {
                                offsetX = value;
                              });
                            },
                    ),
                    const Text('상하 위치'),
                    Slider(
                      value: offsetY,
                      min: -maxOffsetY(),
                      max: maxOffsetY() == 0 ? 0.0001 : maxOffsetY(),
                      onChanged: maxOffsetY() == 0
                          ? null
                          : (value) {
                              setDialogState(() {
                                offsetY = value;
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

  Future<void> scanBarcodeAndFetchImage() async {
    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => const BarcodeScanScreen(),
      ),
    );

    if (result == null || result.isEmpty) return;

    scannedBarcodeValue = result;
    final foundImage = await BarcodeLookupService.instance.lookupImageBytes(result);
    if (!mounted) return;

    if (foundImage == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('해당 상품 이미지를 찾을 수 없습니다.')),
      );
      return;
    }

    final shouldApply = await _confirmFetchedImage(foundImage);
    if (shouldApply == true && mounted) {
      setState(() {
        selectedImageBytes = foundImage;
      });
    }
  }

  Future<bool?> _confirmFetchedImage(Uint8List imageBytes) {
    return showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('상품 이미지 확인'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('조회된 상품 이미지를 굿즈 사진으로 사용할까요?'),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.memory(
                  imageBytes,
                  width: 180,
                  height: 180,
                  fit: BoxFit.cover,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('아니오'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('사용'),
            ),
          ],
        );
      },
    );
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

  Future<void> saveGoods() async {
    if (!_formKey.currentState!.validate()) return;
    if (selectedCategory == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('카테고리를 선택해주세요.')),
      );
      return;
    }
    if (isPreorder && plannedShippingDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('예약구매인 경우 발송 예정일을 선택해주세요.')),
      );
      return;
    }

    final barcodeValue = (scannedBarcodeValue ?? '').trim();
    final item = GoodsItem(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      folderId: widget.folder.id,
      name: nameController.text.trim(),
      category: selectedCategory!,
      quantity: quantity,
      officialPrice: officialPrice,
      paidPrice: paidPrice,
      seriesName: seriesController.text.trim(),
      companyName: companyController.text.trim().isEmpty ? null : companyController.text.trim(),
      purchasePlace: storeController.text.trim().isEmpty ? null : storeController.text.trim(),
      purchaseDate: purchaseDate,
      plannedShippingDate: isPreorder ? plannedShippingDate : null,
      status: isPreorder ? '예약구매' : selectedStatus,
      barcode: barcodeValue.isEmpty ? null : barcodeValue,
      storageLocation: storageLocationController.text.trim().isEmpty ? null : storageLocationController.text.trim(),
      memo: memoController.text.trim().isEmpty ? null : memoController.text.trim(),
      imageBytes: selectedImageBytes,
      isFavorite: false,
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
    companyController.dispose();
    storeController.dispose();
    memoController.dispose();
    storageLocationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final diff = priceDifference;
    final rate = priceRate;

    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.folder.name} 굿즈 추가'),
        actions: [
          IconButton(
            tooltip: '바코드 스캔',
            onPressed: scanBarcodeAndFetchImage,
            icon: const Icon(Icons.qr_code_scanner_rounded),
          ),
        ],
      ),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              GestureDetector(
                onTap: chooseImageSource,
                child: Align(
                  alignment: Alignment.center,
                  child: Container(
                    width: 180,
                    height: 180,
                    clipBehavior: Clip.antiAlias,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Theme.of(context).colorScheme.outline),
                    ),
                    child: selectedImageBytes == null
                        ? const Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.add_a_photo_outlined, size: 28),
                              SizedBox(height: 8),
                              Text('사진 추가'),
                            ],
                          )
                        : Image.memory(selectedImageBytes!, fit: BoxFit.cover),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: seriesController,
                decoration: const InputDecoration(labelText: '시리즈'),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: nameController,
                decoration: const InputDecoration(labelText: '굿즈 이름 *'),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '굿즈 이름은 필수입니다.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: selectedCategory,
                decoration: const InputDecoration(labelText: '카테고리 *'),
                items: categories.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                onChanged: (value) => setState(() => selectedCategory = value),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  const Text(
                    '개수',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 24,
                    height: 24,
                    child: IconButton.filledTonal(
                      padding: EdgeInsets.zero,
                      visualDensity: VisualDensity.compact,
                      onPressed: quantity > 1 ? () => setState(() => quantity--) : null,
                      icon: const Icon(Icons.remove, size: 12),
                    ),
                  ),
                  SizedBox(
                    width: 30,
                    child: Center(
                      child: Text(
                        '$quantity',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ),
                  SizedBox(
                    width: 24,
                    height: 24,
                    child: IconButton.filledTonal(
                      padding: EdgeInsets.zero,
                      visualDensity: VisualDensity.compact,
                      onPressed: () => setState(() => quantity++),
                      icon: const Icon(Icons.add, size: 12),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: officialPriceController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: '정가',
                        prefixText: 'KRW ',
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: paidPriceController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: '실구매가',
                        prefixText: 'KRW ',
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
                            '${getCompareLabel(diff)} ${diff.abs()}원 (${rate.toStringAsFixed(1)}%)',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              InkWell(
                onTap: pickDate,
                child: InputDecorator(
                  decoration: const InputDecoration(labelText: '구매 날짜'),
                  child: Text(
                    purchaseDate == null
                        ? '날짜 선택'
                        : '${purchaseDate!.year}-${purchaseDate!.month.toString().padLeft(2, '0')}-${purchaseDate!.day.toString().padLeft(2, '0')}',
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SwitchListTile(
                value: isPreorder,
                contentPadding: EdgeInsets.zero,
                title: const Text('예약구매'),
                subtitle: const Text('아직 배송되지 않아 현물로 받지 않은 상태'),
                onChanged: (value) {
                  setState(() {
                    isPreorder = value;
                    if (!isPreorder) {
                      plannedShippingDate = null;
                    }
                  });
                },
              ),
              if (isPreorder) ...[
                const SizedBox(height: 12),
                InkWell(
                  onTap: pickPlannedShippingDate,
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
                Wrap(
                  spacing: 8,
                  children: statuses.map((status) {
                    return ChoiceChip(
                      label: Text(status),
                      selected: selectedStatus == status,
                      onSelected: (_) => setState(() => selectedStatus = status),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: companyController,
                  decoration: const InputDecoration(labelText: '공식 판매처'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: storeController,
                  decoration: const InputDecoration(labelText: '구매처'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: storageLocationController,
                  decoration: const InputDecoration(labelText: '보관 위치'),
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
                  onPressed: saveGoods,
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
    canvas.drawLine(Offset(thirdX * 2, 0), Offset(thirdX * 2, size.height), gridPaint);
    canvas.drawLine(Offset(0, thirdY), Offset(size.width, thirdY), gridPaint);
    canvas.drawLine(Offset(0, thirdY * 2), Offset(size.width, thirdY * 2), gridPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
