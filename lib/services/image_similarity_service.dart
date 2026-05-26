import 'dart:async';
import 'dart:io';
import 'dart:ui' show Rect;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:google_mlkit_image_labeling/google_mlkit_image_labeling.dart';
import 'package:google_mlkit_object_detection/google_mlkit_object_detection.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';
import 'package:image/image.dart' as img;
import 'package:onnxruntime/onnxruntime.dart';
import 'package:path_provider/path_provider.dart';
import 'package:crypto/crypto.dart' show sha256;
import 'dart:convert' show utf8;

import '../models/goods_catalog_entry.dart';

/// Image similarity using DINOv2-small (Meta SSL ViT) embeddings.
///
/// Pipeline for a user photo (`analyzeUserPhoto`):
///   1. ML Kit Object Detection → bounding box (crop to subject)
///   2. ML Kit Image Labeling → English labels → category boost set
///   3. ImageNet preprocess on cropped object (resize 256 → center 224)
///   4. ONNX Runtime inference → 384-dim float embedding
///   5. L2-normalize embedding
///   6. Cosine similarity vs catalog embeddings (since both are normalized
///      this is a single dot product per entry)
///
/// Catalog embeddings live in `assets/catalog_embeddings.bin` (built by
/// `python tools/build_dinov2_bundle.py`). Missing entries fall through
/// to Hive disk cache → network fetch + on-device embed.

class DetectedEmbedding {
  final Float32List embedding;     // 384-dim, L2-normalized
  final Set<String> boostCategories;
  const DetectedEmbedding({
    required this.embedding,
    required this.boostCategories,
  });
}

/// Kept for backward-compat with code that still passes `DetectedSignature`.
typedef DetectedSignature = DetectedEmbedding;

class ImageSimilarityService {
  ImageSimilarityService._();
  static final ImageSimilarityService instance = ImageSimilarityService._();

  // ── Model + bundle config ────────────────────────────────────────────
  static const String _modelAsset = 'assets/dinov2_small.onnx';
  static const String _bundleAsset = 'assets/catalog_embeddings.bin';
  static const int _embedDim = 384;
  static const int _inputSize = 224;
  static const int _resizeSize = 256;
  // ImageNet normalization (matches the Python builder exactly)
  static const List<double> _mean = [0.485, 0.456, 0.406];
  static const List<double> _std = [0.229, 0.224, 0.225];
  static const String _hiveBoxName = 'dinov2_embeddings_v1';

  // ── ONNX session (lazy) ──────────────────────────────────────────────
  OrtSession? _ortSession;
  Future<OrtSession?>? _ortInitFuture;
  String? _inputName;

  // ── Bundle + caches ──────────────────────────────────────────────────
  Box<Uint8List>? _diskBox;
  final Map<String, Float32List> _memCache = {};
  Map<String, Float32List>? _bundleIndex; // 8-byte url hash (hex) → embedding
  Future<void>? _bundleLoad;

  Future<OrtSession?> _ensureOrt() async {
    if (_ortSession != null) return _ortSession;
    _ortInitFuture ??= () async {
      try {
        if (kDebugMode) debugPrint('DINOv2: step 1 — OrtEnv.init');
        OrtEnv.instance.init();

        if (kDebugMode) debugPrint('DINOv2: step 2 — load asset bytes');
        final data = await rootBundle.load(_modelAsset);
        final bytes = data.buffer.asUint8List();
        if (kDebugMode) {
          debugPrint(
              'DINOv2: asset loaded, ${bytes.lengthInBytes ~/ 1024 ~/ 1024} MB');
        }

        // Write model to app-cache so we can load via fromFile. Avoids the
        // ~84 MB double-copy in native memory that `fromBuffer` triggers,
        // which OOMs on lower-spec devices and the x86 emulator.
        if (kDebugMode) debugPrint('DINOv2: step 3 — write to cache');
        final tmpDir = await getTemporaryDirectory();
        final modelFile = File('${tmpDir.path}/dinov2_small.onnx');
        if (!modelFile.existsSync() ||
            modelFile.lengthSync() != bytes.lengthInBytes) {
          await modelFile.writeAsBytes(bytes, flush: true);
        }
        if (kDebugMode) {
          debugPrint('DINOv2: cached at ${modelFile.path}, opening session');
        }

        final opts = OrtSessionOptions();
        final session = OrtSession.fromFile(modelFile, opts);
        _inputName = session.inputNames.first;
        if (kDebugMode) {
          debugPrint(
              'DINOv2 loaded — inputs=${session.inputNames} outputs=${session.outputNames}');
        }
        _ortSession = session;
        return session;
      } catch (e, st) {
        debugPrint('DINOv2 load failed: $e');
        if (kDebugMode) debugPrint('$st');
        return null;
      }
    }();
    return _ortInitFuture;
  }

  Future<void> _ensureBundle() async {
    if (_bundleIndex != null) return;
    _bundleLoad ??= () async {
      try {
        final data = await rootBundle.load(_bundleAsset);
        final bytes = data.buffer.asUint8List();
        if (bytes.length < 16 ||
            bytes[0] != 0x44 ||  // D
            bytes[1] != 0x4B ||  // K
            bytes[2] != 0x45 ||  // E
            bytes[3] != 0x32) {  // 2
          if (kDebugMode) debugPrint('Embedding bundle magic mismatch');
          _bundleIndex = {};
          return;
        }
        final bd = ByteData.sublistView(bytes);
        final dim = bd.getUint32(8, Endian.little);
        final count = bd.getUint32(12, Endian.little);
        if (dim != _embedDim) {
          if (kDebugMode) {
            debugPrint('Embedding bundle dim mismatch: $dim vs $_embedDim');
          }
          _bundleIndex = {};
          return;
        }
        final out = <String, Float32List>{};
        var offset = 16;
        final recSize = 8 + dim * 4;
        for (var i = 0; i < count; i++) {
          if (offset + recSize > bytes.length) break;
          final hashHex = _hexOf(bytes, offset, 8);
          offset += 8;
          final vec = Float32List(dim);
          for (var j = 0; j < dim; j++) {
            vec[j] = bd.getFloat32(offset + j * 4, Endian.little);
          }
          offset += dim * 4;
          out[hashHex] = vec;
        }
        _bundleIndex = out;
        if (kDebugMode) {
          debugPrint('DINOv2 bundle: ${out.length} embeddings loaded');
        }
      } catch (e) {
        _bundleIndex = {};
        if (kDebugMode) debugPrint('DINOv2 bundle load skipped: $e');
      }
    }();
    return _bundleLoad;
  }

  Future<void> _ensureDiskBox() async {
    if (_diskBox != null) return;
    try {
      _diskBox = await Hive.openBox<Uint8List>(_hiveBoxName);
    } catch (_) {
      _diskBox = null;
    }
  }

  // ── Crop helpers (reused from ML Kit pipeline) ───────────────────────
  static double _area(Rect r) => r.width * r.height;

  img.Image _centerCrop80(img.Image src) {
    final side = (src.width < src.height ? src.width : src.height) * 8 ~/ 10;
    final cx = src.width ~/ 2;
    final cy = src.height ~/ 2;
    return img.copyCrop(
      src,
      x: cx - side ~/ 2,
      y: cy - side ~/ 2,
      width: side,
      height: side,
    );
  }

  img.Image _cropToBoundingBox(
    img.Image src,
    Rect bbox, {
    double marginPct = 0.10,
  }) {
    final cx = bbox.center.dx;
    final cy = bbox.center.dy;
    final bigger = bbox.width > bbox.height ? bbox.width : bbox.height;
    final side = (bigger * (1 + marginPct)).round();
    final clampedSide =
        side.clamp(8, src.width < src.height ? src.width : src.height);
    var x = (cx - clampedSide / 2).round();
    var y = (cy - clampedSide / 2).round();
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x + clampedSide > src.width) x = src.width - clampedSide;
    if (y + clampedSide > src.height) y = src.height - clampedSide;
    return img.copyCrop(
      src,
      x: x,
      y: y,
      width: clampedSide,
      height: clampedSide,
    );
  }

  /// Resize-256 → center-crop-224 → ImageNet normalize → NCHW float32.
  /// Output shape: [1, 3, 224, 224] flat as length 1*3*224*224 = 150528.
  Float32List _preprocess(img.Image src) {
    final w = src.width;
    final h = src.height;
    final scale = _resizeSize / (w < h ? w : h);
    final nw = (w * scale).round();
    final nh = (h * scale).round();
    final resized = img.copyResize(
      src,
      width: nw,
      height: nh,
      interpolation: img.Interpolation.cubic,
    );
    final left = (nw - _inputSize) ~/ 2;
    final top = (nh - _inputSize) ~/ 2;
    final cropped = img.copyCrop(
      resized,
      x: left,
      y: top,
      width: _inputSize,
      height: _inputSize,
    );

    final out = Float32List(1 * 3 * _inputSize * _inputSize);
    final plane = _inputSize * _inputSize;
    // NCHW layout: channel 0 (R) fully then 1 (G) then 2 (B)
    for (var y = 0; y < _inputSize; y++) {
      for (var x = 0; x < _inputSize; x++) {
        final p = cropped.getPixel(x, y);
        final r = p.r / 255.0;
        final g = p.g / 255.0;
        final b = p.b / 255.0;
        final idx = y * _inputSize + x;
        out[idx] = (r - _mean[0]) / _std[0];
        out[plane + idx] = (g - _mean[1]) / _std[1];
        out[2 * plane + idx] = (b - _mean[2]) / _std[2];
      }
    }
    return out;
  }

  /// L2-normalize the embedding in place. Lets us use dot-product as
  /// cosine similarity at query time without re-normalizing.
  Float32List _l2Normalize(Float32List vec) {
    var sum = 0.0;
    for (final v in vec) {
      sum += v * v;
    }
    final norm = sum > 1e-12 ? 1.0 / (sqrt(sum)) : 1.0;
    for (var i = 0; i < vec.length; i++) {
      vec[i] = vec[i] * norm;
    }
    return vec;
  }

  Future<Float32List?> _embedCropped(img.Image cropped) async {
    final session = await _ensureOrt();
    if (session == null || _inputName == null) return null;
    final input = _preprocess(cropped);
    final shape = [1, 3, _inputSize, _inputSize];
    final tensor = OrtValueTensor.createTensorWithDataList(input, shape);
    try {
      final outputs = session.run(
        OrtRunOptions(),
        {_inputName!: tensor},
      );
      // DINOv2 outputs typically:
      //  - last_hidden_state: [1, 257, 384]  (1 CLS + 256 patches)
      //  - pooler_output:    [1, 384]
      // Some exports also return [1, 384] directly. We accept either shape.
      Float32List? embedding;
      for (final o in outputs) {
        if (o == null) continue;
        final v = o.value;
        if (v is List && v.isNotEmpty) {
          // Unwrap nested lists. The OrtValue list shape mirrors the tensor.
          final flat = _flattenAndTakeCls(v, _embedDim);
          if (flat != null) {
            embedding = flat;
            break;
          }
        }
        o.release();
      }
      if (embedding == null) {
        if (kDebugMode) debugPrint('DINOv2: could not extract embedding');
        return null;
      }
      return _l2Normalize(embedding);
    } catch (e) {
      debugPrint('DINOv2 inference failed: $e');
      return null;
    } finally {
      tensor.release();
    }
  }

  /// Walk the OrtValue's nested list output and return the CLS / pooled
  /// vector of length [dim]. Supports both [1, dim] and [1, N, dim].
  Float32List? _flattenAndTakeCls(dynamic value, int dim) {
    // value is List of length 1 (batch); inside is either List<num> (dim)
    // or List<List<num>> (seq × dim).
    if (value is! List || value.isEmpty) return null;
    final batch0 = value[0];
    if (batch0 is List && batch0.isNotEmpty && batch0[0] is num) {
      if (batch0.length != dim) return null;
      final out = Float32List(dim);
      for (var i = 0; i < dim; i++) {
        out[i] = (batch0[i] as num).toDouble();
      }
      return out;
    }
    if (batch0 is List && batch0.isNotEmpty && batch0[0] is List) {
      final cls = batch0[0]; // first token = CLS
      if (cls is! List || cls.length != dim) return null;
      final out = Float32List(dim);
      for (var i = 0; i < dim; i++) {
        out[i] = (cls[i] as num).toDouble();
      }
      return out;
    }
    return null;
  }

  static String _hexOf(Uint8List bytes, int offset, int len) {
    final sb = StringBuffer();
    for (var i = 0; i < len; i++) {
      sb.write(bytes[offset + i].toRadixString(16).padLeft(2, '0'));
    }
    return sb.toString();
  }

  String _urlKey(String url) {
    final digest = sha256.convert(utf8.encode(url));
    final sb = StringBuffer();
    for (var i = 0; i < 8; i++) {
      sb.write(digest.bytes[i].toRadixString(16).padLeft(2, '0'));
    }
    return sb.toString();
  }

  /// Full analyze pipeline for a user-supplied photo.
  Future<DetectedEmbedding?> analyzeUserPhoto(Uint8List bytes) async {
    try {
      final decoded = img.decodeImage(bytes);
      if (decoded == null) return null;

      File? tempFile;
      Rect? bbox;
      final boostCategories = <String>{};

      try {
        final tmpDir = await getTemporaryDirectory();
        tempFile = File(
            '${tmpDir.path}/__deokive_similarity_query_${DateTime.now().microsecondsSinceEpoch}.jpg');
        await tempFile.writeAsBytes(bytes, flush: true);

        // ── Object detection ─────────────────────────────────────────
        final detector = ObjectDetector(
          options: ObjectDetectorOptions(
            mode: DetectionMode.single,
            classifyObjects: false,
            multipleObjects: false,
          ),
        );
        try {
          final inputImage = InputImage.fromFilePath(tempFile.path);
          final objects = await detector.processImage(inputImage);
          if (objects.isNotEmpty) {
            objects.sort(
                (a, b) => _area(b.boundingBox).compareTo(_area(a.boundingBox)));
            bbox = objects.first.boundingBox;
          }
        } finally {
          await detector.close();
        }

        // ── Image labeling (full image) ──────────────────────────────
        final labeler = ImageLabeler(
          options: ImageLabelerOptions(confidenceThreshold: 0.50),
        );
        try {
          final inputImage = InputImage.fromFilePath(tempFile.path);
          final labels = await labeler.processImage(inputImage);
          for (final l in labels) {
            final hits = _categoriesForLabel(l.label);
            if (hits.isNotEmpty) boostCategories.addAll(hits);
          }
          if (kDebugMode) {
            debugPrint(
                'ImageLabel: ${labels.isEmpty ? "EMPTY" : labels.map((l) => "${l.label}(${l.confidence.toStringAsFixed(2)})").join(", ")} → boost=$boostCategories');
          }
        } finally {
          await labeler.close();
        }
      } catch (e) {
        if (kDebugMode) debugPrint('ML Kit step skipped: $e');
      } finally {
        try {
          await tempFile?.delete();
        } catch (_) {}
      }

      final cropped = bbox != null
          ? _cropToBoundingBox(decoded, bbox, marginPct: 0.10)
          : _centerCrop80(decoded);
      final embedding = await _embedCropped(cropped);
      if (embedding == null) return null;
      return DetectedEmbedding(
        embedding: embedding,
        boostCategories: boostCategories,
      );
    } catch (e) {
      debugPrint('analyzeUserPhoto failed: $e');
      return null;
    }
  }

  // ── Embedding lookup for catalog entries ─────────────────────────────
  Future<Uint8List?> _fetchBytes(String url) async {
    final client = HttpClient();
    try {
      final request = await client.getUrl(Uri.parse(url));
      final response =
          await request.close().timeout(const Duration(seconds: 5));
      if (response.statusCode != 200) return null;
      final out = await consolidateHttpClientResponseBytes(response);
      return out.isEmpty ? null : out;
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  Float32List _bytesToFloat32(Uint8List bytes) {
    final bd = ByteData.sublistView(bytes);
    final out = Float32List(bytes.lengthInBytes ~/ 4);
    for (var i = 0; i < out.length; i++) {
      out[i] = bd.getFloat32(i * 4, Endian.little);
    }
    return out;
  }

  Uint8List _float32ToBytes(Float32List vec) {
    final bd = ByteData(vec.length * 4);
    for (var i = 0; i < vec.length; i++) {
      bd.setFloat32(i * 4, vec[i], Endian.little);
    }
    return bd.buffer.asUint8List();
  }

  Future<Float32List?> embeddingForUrl(String url) async {
    if (_memCache.containsKey(url)) return _memCache[url];
    await _ensureBundle();
    final key = _urlKey(url);
    final fromBundle = _bundleIndex?[key];
    if (fromBundle != null) {
      _memCache[url] = fromBundle;
      return fromBundle;
    }
    await _ensureDiskBox();
    final fromDisk = _diskBox?.get(url);
    if (fromDisk != null && fromDisk.lengthInBytes == _embedDim * 4) {
      final vec = _bytesToFloat32(fromDisk);
      _memCache[url] = vec;
      return vec;
    }
    final bytes = await _fetchBytes(url);
    if (bytes == null) return null;
    final decoded = img.decodeImage(bytes);
    if (decoded == null) return null;
    final embedding = await _embedCropped(_centerCrop80(decoded));
    if (embedding == null) return null;
    _memCache[url] = embedding;
    try {
      await _diskBox?.put(url, _float32ToBytes(embedding));
    } catch (_) {}
    return embedding;
  }

  bool isBundled(String url) {
    if (_bundleIndex == null) return false;
    return _bundleIndex!.containsKey(_urlKey(url));
  }

  /// Cosine similarity (since both vectors are L2-normalized).
  static double _cosine(Float32List a, Float32List b) {
    var dot = 0.0;
    final n = a.length < b.length ? a.length : b.length;
    for (var i = 0; i < n; i++) {
      dot += a[i] * b[i];
    }
    return dot;
  }

  /// Rank catalog entries by cosine similarity to [queryEmbedding].
  /// Higher similarity → smaller "distance" returned to callers (we keep
  /// the legacy "distance" naming for compatibility — internally it's
  /// `(1 - cosine) * 10000` as an integer so existing distance UI keeps
  /// working unchanged).
  Future<List<({GoodsCatalogEntry entry, int distance})>> findSimilar({
    required Float32List queryEmbedding,
    required List<GoodsCatalogEntry> catalog,
    int topN = 5,
    Set<String> boostCategories = const {},
    double boostFactor = 0.65,
    void Function(int done, int total, int cached)? onProgress,
  }) async {
    final withImages = catalog
        .where((e) => (e.imageUrl ?? '').trim().isNotEmpty)
        .toList();

    await _ensureBundle();
    await _ensureDiskBox();

    final results = <({GoodsCatalogEntry entry, int distance})>[];
    var done = 0;
    var cached = 0;

    const concurrency = 12;
    for (var i = 0; i < withImages.length; i += concurrency) {
      final chunk = withImages.sublist(
        i,
        i + concurrency > withImages.length ? withImages.length : i + concurrency,
      );
      await Future.wait(chunk.map((entry) async {
        final url = entry.imageUrl!.trim().replaceAll('&amp;', '&');
        final fixed = url.startsWith('//') ? 'https:$url' : url;
        final wasCached = _memCache.containsKey(fixed) ||
            isBundled(fixed) ||
            (_diskBox?.containsKey(fixed) ?? false);
        if (wasCached) cached++;
        final emb = await embeddingForUrl(fixed);
        if (emb != null && emb.length == _embedDim) {
          var sim = _cosine(queryEmbedding, emb);
          if (boostCategories.isNotEmpty &&
              boostCategories.contains(entry.category)) {
            // Boost similarity (smaller distance) for matching categories.
            // Shift sim toward 1.0 by (1 - boostFactor) of the gap.
            sim = sim + (1 - sim) * (1 - boostFactor);
          }
          // distance ∈ [0, 20000]; 0 = perfect match
          final dist = ((1 - sim) * 10000).round().clamp(0, 20000);
          results.add((entry: entry, distance: dist));
        }
        done++;
        onProgress?.call(done, withImages.length, cached);
      }));
    }

    results.sort((a, b) => a.distance.compareTo(b.distance));

    final seen = <String>{};
    final unique = <({GoodsCatalogEntry entry, int distance})>[];
    for (final r in results) {
      final key = '${r.entry.nameKo}|${r.entry.characterName}|${r.entry.category}';
      if (seen.add(key)) unique.add(r);
      if (unique.length >= topN) break;
    }
    return unique;
  }

  // ── English (ML Kit) label → Korean catalog category mapping ─────────
  static const Map<String, List<String>> _labelToCategories = {
    'plush': ['봉제 인형', '인형', '마스코트', '마스코트 세트', '러버 마스코트'],
    'stuffed': ['봉제 인형', '인형', '마스코트'],
    'doll': ['봉제 인형', '인형', '마스코트'],
    'toy': ['봉제 인형', '인형', '마스코트', '마스코트 세트', '러버 마스코트'],
    'figurine': ['피규어', '미니 피규어', '미니어처', '프라모델'],
    'sculpture': ['피규어', '미니 피규어'],
    'action figure': ['피규어'],
    'cartoon': ['아크릴 스탠드', '일러스트 카드', '캔뱃지', '스티커'],
    'animation': ['아크릴 스탠드', '일러스트 카드', '캔뱃지', '스티커'],
    'clothing': ['의류', '래시가드', '수영복', '머리띠'],
    'shirt': ['의류'],
    't-shirt': ['의류'],
    'sleeve': ['의류'],
    'mug': ['머그컵'],
    'cup': ['머그컵', '식기'],
    'tableware': ['식기', '머그컵'],
    'drinkware': ['머그컵', '클리어 보틀'],
    'bottle': ['클리어 보틀'],
    'bag': ['백팩', '토트백', '에코백', '사코슈', '메신저백', '포셰트', '숄더백', '웨이스트백', '파우치', '랜덤 백'],
    'handbag': ['토트백', '숄더백', '에코백'],
    'backpack': ['백팩'],
    'pouch': ['파우치', '필통'],
    'wallet': ['파우치'],
    'pillow': ['쿠션'],
    'cushion': ['쿠션'],
    'mirror': ['미러'],
    'towel': ['타올'],
    'card': ['트레이딩 카드', '포토카드', '일러스트 카드'],
    'trading card': ['트레이딩 카드', '포토카드'],
    'paper': ['색지', '클리어 파일', '스티커'],
    'sticker': ['스티커'],
    'label': ['스티커'],
    'book': ['앨범', '포토북', '시즌 그리팅'],
    'magazine': ['포토북', '시즌 그리팅'],
    'pen': ['문구'],
    'stationery': ['문구', '필통', '클리어 파일'],
    'fan': ['우치와'],
    'lipstick': ['뷰티'],
    'cosmetic': ['뷰티'],
    'hat': ['모자'],
    'cap': ['모자'],
    'sock': ['양말'],
    'badge': ['캔뱃지'],
    'pin': ['캔뱃지'],
    'button': ['캔뱃지'],
    'flag': ['따쿠스이', '태피스트리'],
    'banner': ['따쿠스이', '태피스트리'],
    'textile': ['따쿠스이', '태피스트리', '타올'],
    'keychain': ['키링', '러버 스트랩'],
    'key ring': ['키링'],
    'jewellery': ['액세서리', '키링'],
    'fashion accessory': ['액세서리', '머리띠'],
    'phone': ['디지털 기기'],
    'mobile phone': ['디지털 기기'],
    'tablet': ['디지털 기기'],
    'gadget': ['디지털 기기'],
    'lighting': ['응원봉', '펜라이트'],
    'lamp': ['응원봉', '펜라이트'],
  };

  static List<String> _categoriesForLabel(String label) {
    final key = label.toLowerCase();
    final out = <String>{};
    _labelToCategories.forEach((labelKey, cats) {
      if (key.contains(labelKey)) out.addAll(cats);
    });
    return out.toList();
  }
}

/// Dart's math.sqrt without importing the math package (lighter footprint).
double sqrt(double x) {
  // Newton-Raphson — adequate precision for normalization.
  if (x <= 0) return 0;
  var g = x / 2;
  for (var i = 0; i < 20; i++) {
    g = (g + x / g) * 0.5;
  }
  return g;
}
