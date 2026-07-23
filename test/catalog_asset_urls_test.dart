import 'package:deokive/utils/catalog_asset_urls.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('catalog asset URLs include Flutter web asset and direct public paths',
      () {
    final urls = publicCatalogAssetUrls('assets/catalog_images/sample.webp');

    expect(
      urls,
      contains(
        endsWith(
          '/assets/assets/catalog_images/sample.webp?v=$catalogAssetVersion',
        ),
      ),
    );
    expect(
      urls,
      contains(
        endsWith('/assets/catalog_images/sample.webp?v=$catalogAssetVersion'),
      ),
    );
  });

  test('catalog asset URLs ignore non-asset references', () {
    expect(publicCatalogAssetUrls('https://example.com/a.webp'), isEmpty);
  });
}
