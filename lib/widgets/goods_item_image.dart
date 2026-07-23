import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../models/goods_item.dart';

const _goodsAssetVersion = '20260723-imagefix3';

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
    final imageUrl = item.imageUrl?.trim() ?? '';
    final imageBytes = item.imageBytes;
    if (imageBytes != null) {
      return Image.memory(
        imageBytes,
        fit: fit,
        errorBuilder: (_, __, ___) => _imageFromReference(imageUrl),
      );
    }

    return _imageFromReference(imageUrl);
  }

  Widget _imageFromReference(String imageUrl) {
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
      if (kIsWeb && normalizedImageUrl.startsWith('assets/')) {
        return _publicAssetFallback(normalizedImageUrl);
      }
      return Image.asset(
        normalizedImageUrl,
        fit: fit,
        errorBuilder: (_, __, ___) => _publicAssetFallback(
          normalizedImageUrl,
        ),
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

  Widget _publicAssetFallback(String assetPath) {
    if (!assetPath.startsWith('assets/')) return _placeholder();
    return _FallbackNetworkAssetImage(
      urls: _publicAssetUrls(assetPath),
      fit: fit,
      fallback: _placeholder(),
    );
  }
}

class _FallbackNetworkAssetImage extends StatelessWidget {
  final List<String> urls;
  final BoxFit fit;
  final Widget fallback;

  const _FallbackNetworkAssetImage({
    required this.urls,
    required this.fit,
    required this.fallback,
  });

  @override
  Widget build(BuildContext context) {
    return _buildAt(0);
  }

  Widget _buildAt(int index) {
    if (index >= urls.length) return fallback;
    return Image.network(
      urls[index],
      fit: fit,
      errorBuilder: (_, __, ___) => _buildAt(index + 1),
    );
  }
}

List<String> _publicAssetUrls(String assetPath) {
  final normalizedPath = assetPath.replaceFirst(RegExp(r'^/+'), '');
  final candidates = <String>[
    _versionedAssetUrl(Uri.base.resolve(normalizedPath)),
    _versionedAssetUrl(Uri.base.resolve('assets/$normalizedPath')),
  ];
  final origin = Uri.base.origin;
  if (origin.isNotEmpty) {
    candidates
        .add(_versionedAssetUrl(Uri.parse(origin).resolve('/$normalizedPath')));
    candidates.add(
      _versionedAssetUrl(Uri.parse(origin).resolve('/assets/$normalizedPath')),
    );
    candidates.add(
      _versionedAssetUrl(Uri.parse(origin).resolve('/Deokive/$normalizedPath')),
    );
    candidates.add(
      _versionedAssetUrl(
          Uri.parse(origin).resolve('/Deokive/assets/$normalizedPath')),
    );
  }
  return candidates.toSet().toList(growable: false);
}

String _versionedAssetUrl(Uri uri) {
  return uri.replace(
    queryParameters: {
      ...uri.queryParameters,
      'v': _goodsAssetVersion,
    },
  ).toString();
}
