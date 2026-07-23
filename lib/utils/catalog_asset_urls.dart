const catalogAssetVersion = '20260723-imagefix5';

List<String> publicCatalogAssetUrls(String assetPath) {
  final normalizedPath = assetPath.replaceFirst(RegExp(r'^/+'), '');
  if (!normalizedPath.startsWith('assets/')) {
    return const [];
  }

  final flutterAssetPath = 'assets/$normalizedPath';
  final candidates = <String>[
    _versionedAssetUrl(Uri.base.resolve(flutterAssetPath)),
    _versionedAssetUrl(Uri.base.resolve(normalizedPath)),
  ];

  final base = Uri.base;
  if (base.scheme == 'http' || base.scheme == 'https') {
    final root = Uri.parse(base.origin);
    candidates.add(_versionedAssetUrl(root.resolve('/$flutterAssetPath')));
    candidates.add(_versionedAssetUrl(root.resolve('/$normalizedPath')));
    candidates
        .add(_versionedAssetUrl(root.resolve('/Deokive/$flutterAssetPath')));
    candidates
        .add(_versionedAssetUrl(root.resolve('/Deokive/$normalizedPath')));
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
