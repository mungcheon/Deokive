const catalogAssetVersion = '20260723-imagefix8';

List<String> publicCatalogAssetUrls(String assetPath) {
  final normalizedPath = assetPath.replaceFirst(RegExp(r'^/+'), '');
  if (!normalizedPath.startsWith('assets/')) {
    return const [];
  }

  final flutterAssetPath = 'assets/$normalizedPath';
  final candidates = <String>[
    _versionedAssetUrl(Uri.base.resolve(normalizedPath)),
    _versionedAssetUrl(Uri.base.resolve(flutterAssetPath)),
  ];

  final base = Uri.base;
  if (base.scheme == 'http' || base.scheme == 'https') {
    final root = Uri.parse(base.origin);
    candidates.add(_versionedAssetUrl(root.resolve('/$normalizedPath')));
    candidates.add(_versionedAssetUrl(root.resolve('/$flutterAssetPath')));
    candidates
        .add(_versionedAssetUrl(root.resolve('/Deokive/$normalizedPath')));
    candidates
        .add(_versionedAssetUrl(root.resolve('/Deokive/$flutterAssetPath')));
  }

  return candidates.toSet().toList(growable: false);
}

String _versionedAssetUrl(Uri uri) {
  return uri.replace(
    queryParameters: {
      ...uri.queryParameters,
      'v': catalogAssetVersion,
    },
  ).toString();
}
