import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import '../models/goods_catalog_entry.dart';

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
        image = _RemoteCatalogImage(
          imageUrl: localPath,
          width: width,
          height: height,
          placeholder: remotePath.isEmpty ? placeholder : remoteFallback,
        );
      } else {
        image = Image.asset(
          localPath,
          width: width,
          height: height,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) =>
              remotePath.isEmpty ? placeholder : remoteFallback,
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
