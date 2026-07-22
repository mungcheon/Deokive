import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import '../models/goods_item.dart';

class GoodsItemImage extends StatelessWidget {
  final GoodsItem item;
  final BoxFit fit;
  final IconData placeholderIcon;
  final double placeholderIconSize;

  const GoodsItemImage({
    super.key,
    required this.item,
    this.fit = BoxFit.cover,
    this.placeholderIcon = Icons.image_outlined,
    this.placeholderIconSize = 32,
  });

  @override
  Widget build(BuildContext context) {
    final imageBytes = item.imageBytes;
    if (imageBytes != null) {
      return Image.memory(imageBytes, fit: fit);
    }

    final imageUrl = item.imageUrl?.trim() ?? '';
    if (imageUrl.isNotEmpty) {
      final normalizedImageUrl = imageUrl.replaceAll('&amp;', '&').replaceFirst(
            RegExp(r'^//'),
            'https://',
          );
      if (_isNetworkUrl(normalizedImageUrl)) {
        return Image.network(
          normalizedImageUrl,
          fit: fit,
          errorBuilder: (_, __, ___) => _placeholder(),
        );
      }
      if (kIsWeb) {
        return Image.network(
          normalizedImageUrl,
          fit: fit,
          errorBuilder: (_, __, ___) => _placeholder(),
        );
      }
      return Image.asset(
        normalizedImageUrl,
        fit: fit,
        errorBuilder: (_, __, ___) => _placeholder(),
      );
    }

    return _placeholder();
  }

  Widget _placeholder() {
    return Center(
      child: Icon(placeholderIcon, size: placeholderIconSize),
    );
  }

  bool _isNetworkUrl(String value) {
    final uri = Uri.tryParse(value);
    return uri != null && (uri.scheme == 'http' || uri.scheme == 'https');
  }
}
