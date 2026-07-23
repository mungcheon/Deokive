import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../models/goods_catalog_entry.dart';

const _catalogAssetVersion = '20260723-imagefix4';

class CatalogEntryImage extends StatelessWidget {
  final GoodsCatalogEntry entry;
  final double width;
  final double height;
  final double borderRadius;
  final BoxShape shape;
  final IconData placeholderIcon;

  const CatalogEntryImage({
    super.key,
    required this.entry,
    required this.width,
    required this.height,
    this.borderRadius = 12,
    this.shape = BoxShape.rectangle,
    this.placeholderIcon = Icons.inventory_2_outlined,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final placeholder = Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        shape: shape,
        borderRadius: shape == BoxShape.circle
            ? null
            : BorderRadius.circular(borderRadius),
      ),
      child: Icon(
        placeholderIcon,
        color: theme.colorScheme.onSurface.withValues(alpha: 0.46),
        size: width < 50 ? 18 : 26,
      ),
    );

    final localPath = entry.localImagePath?.trim() ?? '';
    final remotePath = entry.imageUrl?.trim() ?? '';
    if (localPath.isEmpty && remotePath.isEmpty) return placeholder;

    final Widget image;
    if (localPath.isNotEmpty) {
      final remoteFallback = _RemoteCatalogImage(
        imageUrl: remotePath,
        width: width,
        height: height,
        placeholder: placeholder,
      );
      if (kIsWeb) {
        image = _PublicCatalogAssetImage(
          assetPath: localPath,
          width: width,
          height: height,
          fallback: remotePath.isEmpty ? placeholder : remoteFallback,
        );
      } else {
        image = Image.asset(
          localPath,
          width: width,
          height: height,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => _PublicCatalogAssetImage(
            assetPath: localPath,
            width: width,
            height: height,
            fallback: remotePath.isEmpty ? placeholder : remoteFallback,
          ),
        );
      }
    } else {
      image = _RemoteCatalogImage(
        imageUrl: remotePath,
        width: width,
        height: height,
        placeholder: placeholder,
      );
    }

    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        shape: shape,
        borderRadius: shape == BoxShape.circle
            ? null
            : BorderRadius.circular(borderRadius),
      ),
      clipBehavior: Clip.antiAlias,
      child: image,
    );
  }
}

class _PublicCatalogAssetImage extends StatelessWidget {
  final String assetPath;
  final double width;
  final double height;
  final Widget fallback;

  const _PublicCatalogAssetImage({
    required this.assetPath,
    required this.width,
    required this.height,
    required this.fallback,
  });

  @override
  Widget build(BuildContext context) {
    if (!assetPath.startsWith('assets/')) return fallback;
    return _FallbackNetworkAssetImage(
      urls: _publicAssetUrls(assetPath),
      width: width,
      height: height,
      fit: BoxFit.cover,
      fallback: fallback,
    );
  }
}

class _FallbackNetworkAssetImage extends StatelessWidget {
  final List<String> urls;
  final double width;
  final double height;
  final BoxFit fit;
  final Widget fallback;

  const _FallbackNetworkAssetImage({
    required this.urls,
    required this.width,
    required this.height,
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
      width: width,
      height: height,
      fit: fit,
      errorBuilder: (_, __, ___) => _buildAt(index + 1),
    );
  }
}

class _RemoteCatalogImage extends StatelessWidget {
  final String imageUrl;
  final double width;
  final double height;
  final Widget placeholder;

  const _RemoteCatalogImage({
    required this.imageUrl,
    required this.width,
    required this.height,
    required this.placeholder,
  });

  @override
  Widget build(BuildContext context) {
    final remotePath = imageUrl.trim();
    if (remotePath.isEmpty) return placeholder;

    return Image.network(
      remotePath.replaceAll('&amp;', '&').replaceFirst(
            RegExp(r'^//'),
            'https://',
          ),
      width: width,
      height: height,
      fit: BoxFit.cover,
      errorBuilder: (_, __, ___) => placeholder,
    );
  }
}

List<String> _publicAssetUrls(String assetPath) {
  final normalizedPath = assetPath.replaceFirst(RegExp(r'^/+'), '');
  final candidates = <String>[
    _versionedAssetUrl(Uri.base.resolve('assets/$normalizedPath')),
    _versionedAssetUrl(Uri.base.resolve(normalizedPath)),
  ];
  final origin = Uri.base.origin;
  if (origin.isNotEmpty) {
    candidates.add(
      _versionedAssetUrl(Uri.parse(origin).resolve('/assets/$normalizedPath')),
    );
    candidates
        .add(_versionedAssetUrl(Uri.parse(origin).resolve('/$normalizedPath')));
    candidates.add(
      _versionedAssetUrl(
          Uri.parse(origin).resolve('/Deokive/assets/$normalizedPath')),
    );
    candidates.add(
      _versionedAssetUrl(Uri.parse(origin).resolve('/Deokive/$normalizedPath')),
    );
  }
  return candidates.toSet().toList(growable: false);
}

String _versionedAssetUrl(Uri uri) {
  return uri.replace(
    queryParameters: {
      ...uri.queryParameters,
      'v': _catalogAssetVersion,
    },
  ).toString();
}
