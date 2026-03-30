import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';

class BarcodeLookupService {
  BarcodeLookupService._();

  static final BarcodeLookupService instance = BarcodeLookupService._();

  static final Uri _upcItemDbUri =
      Uri.parse('https://api.upcitemdb.com/prod/trial/lookup');

  Future<Uint8List?> lookupImageBytes(String barcode) async {
    final trimmed = barcode.trim();
    if (trimmed.isEmpty) return null;

    final imageUrl = await _lookupWithUpcItemDb(trimmed) ??
        await _lookupWithGtinHub(trimmed);

    if (imageUrl == null || imageUrl.isEmpty) {
      return null;
    }

    return _downloadImageBytes(imageUrl);
  }

  Future<String?> _lookupWithUpcItemDb(String barcode) async {
    final client = HttpClient();
    try {
      final request = await client.postUrl(_upcItemDbUri);
      request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.add(
        utf8.encode(
          jsonEncode(<String, dynamic>{'upc': barcode}),
        ),
      );

      final response = await request.close().timeout(const Duration(seconds: 6));
      if (response.statusCode != 200) {
        return null;
      }

      final raw = await response.transform(utf8.decoder).join();
      final json = jsonDecode(raw);
      if (json is! Map<String, dynamic>) return null;

      final items = json['items'];
      if (items is! List || items.isEmpty) return null;

      final first = items.first;
      if (first is! Map) return null;

      return _pickImageUrlFromItem(Map<String, dynamic>.from(first));
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  Future<String?> _lookupWithGtinHub(String barcode) async {
    final client = HttpClient();
    try {
      final uri = Uri.parse('https://gtinhub.com/api/v1/item/$barcode');
      final request = await client.getUrl(uri);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');

      final response = await request.close().timeout(const Duration(seconds: 6));
      if (response.statusCode != 200) {
        return null;
      }

      final raw = await response.transform(utf8.decoder).join();
      final json = jsonDecode(raw);
      if (json is! Map<String, dynamic>) return null;

      final item = json['item'];
      if (item is Map<String, dynamic>) {
        return _pickImageUrlFromItem(item);
      }

      return _pickImageUrlFromItem(json);
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  String? _pickImageUrlFromItem(Map<String, dynamic> item) {
    final images = item['images'];
    if (images is List && images.isNotEmpty) {
      final firstImage = images.first;
      if (firstImage is String && firstImage.isNotEmpty) {
        return firstImage;
      }
      if (firstImage is Map<String, dynamic>) {
        final url = firstImage['url']?.toString();
        if ((url ?? '').isNotEmpty) return url;
      }
    }

    final image = item['image']?.toString();
    if ((image ?? '').isNotEmpty) {
      return image;
    }

    final imageUrl = item['imageUrl']?.toString();
    if ((imageUrl ?? '').isNotEmpty) {
      return imageUrl;
    }

    return null;
  }

  Future<Uint8List?> _downloadImageBytes(String imageUrl) async {
    final client = HttpClient();
    try {
      final request = await client.getUrl(Uri.parse(imageUrl));
      final response = await request.close().timeout(const Duration(seconds: 8));
      if (response.statusCode != 200) {
        return null;
      }

      final bytes = await consolidateHttpClientResponseBytes(response);
      return bytes.isEmpty ? null : bytes;
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }
}
