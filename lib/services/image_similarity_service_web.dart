import 'dart:typed_data';

import '../models/goods_catalog_entry.dart';

class DetectedEmbedding {
  final Float32List embedding;
  final Set<String> boostCategories;

  const DetectedEmbedding({
    required this.embedding,
    required this.boostCategories,
  });
}

typedef DetectedSignature = DetectedEmbedding;

class ImageSimilarityService {
  ImageSimilarityService._();

  static final ImageSimilarityService instance = ImageSimilarityService._();

  Future<DetectedEmbedding?> analyzeUserPhoto(Uint8List bytes) async {
    return null;
  }

  Future<Float32List?> embeddingForUrl(String url) async {
    return null;
  }

  bool isBundled(String url) => false;

  Future<List<({GoodsCatalogEntry entry, int distance})>> findSimilar({
    required Float32List queryEmbedding,
    required List<GoodsCatalogEntry> catalog,
    int topN = 5,
    Set<String> boostCategories = const {},
    double boostFactor = 0.65,
    void Function(int done, int total, int cached)? onProgress,
  }) async {
    return const [];
  }
}
