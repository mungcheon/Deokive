import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/goods_catalog_entry.dart';
import '../state/app_state.dart';
import '../services/image_similarity_service_web.dart';
import '../widgets/catalog_entry_image.dart';

/// Standalone screen for image-based catalog lookup. User picks a photo,
/// service computes a perceptual signature, then ranks catalog entries.
/// On tap, returns the picked GoodsCatalogEntry to the previous screen.
class ImageCatalogSearchScreen extends StatefulWidget {
  const ImageCatalogSearchScreen({super.key});

  @override
  State<ImageCatalogSearchScreen> createState() =>
      _ImageCatalogSearchScreenState();
}

class _ImageCatalogSearchScreenState extends State<ImageCatalogSearchScreen> {
  Uint8List? _queryBytes;
  bool _searching = false;
  bool _unsupportedOnWeb = false;
  int _done = 0;
  int _total = 0;
  List<({GoodsCatalogEntry entry, int distance})> _results = const [];

  Future<void> _pickAndSearch(ImageSource source) async {
    final picker = ImagePicker();
    final xfile = await picker.pickImage(source: source, imageQuality: 85);
    if (xfile == null) return;
    final bytes = await xfile.readAsBytes();
    if (!mounted) return;
    setState(() {
      _queryBytes = bytes;
      _searching = true;
      _unsupportedOnWeb = false;
      _done = 0;
      _total = 0;
      _results = const [];
    });

    final svc = ImageSimilarityService.instance;
    final analyzed = await svc.analyzeUserPhoto(bytes);
    if (analyzed == null) {
      if (!mounted) return;
      setState(() {
        _searching = false;
        _unsupportedOnWeb = true;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('이 이미지 검색은 현재 모바일 앱에서만 지원돼요.'),
        ),
      );
      return;
    }

    final ranked = await svc.findSimilar(
      queryEmbedding: analyzed.embedding,
      catalog: context.read<AppState>().curatedCatalogEntries,
      topN: 5,
      boostCategories: analyzed.boostCategories,
      onProgress: (done, total, cached) {
        if (!mounted) return;
        setState(() {
          _done = done;
          _total = total;
        });
      },
    );
    if (!mounted) return;
    setState(() {
      _results = ranked;
      _searching = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('이미지 검색'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _SearchHeader(
            queryBytes: _queryBytes,
            onCamera: () => _pickAndSearch(ImageSource.camera),
            onGallery: () => _pickAndSearch(ImageSource.gallery),
          ),
          const SizedBox(height: 16),
          if (_searching) ...[
            LinearProgressIndicator(
              value: _total == 0 ? null : _done / _total,
              minHeight: 6,
            ),
            const SizedBox(height: 8),
            const Text(
              '비슷한 굿즈를 찾는 중...',
              style: TextStyle(fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ],
          if (!_searching && _results.isNotEmpty) ...[
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Text(
                '비슷한 굿즈 추천',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
              ),
            ),
            for (final r in _results)
              _ResultTile(
                entry: r.entry,
                distance: r.distance,
                onTap: () => Navigator.pop(context, r.entry),
              ),
          ],
          if (!_searching && _queryBytes != null && _results.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Center(
                child: Text(
                  _unsupportedOnWeb
                      ? '웹에서는 아직 이미지 기반 카탈로그 검색을 지원하지 않아요.\n모바일 앱에서 이용해 주세요.'
                      : '비슷한 항목을 찾지 못했어요.\n다른 사진으로 다시 시도해 보세요.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 13),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _SearchHeader extends StatelessWidget {
  final Uint8List? queryBytes;
  final VoidCallback onCamera;
  final VoidCallback onGallery;

  const _SearchHeader({
    required this.queryBytes,
    required this.onCamera,
    required this.onGallery,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Container(
          height: 200,
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(18),
          ),
          clipBehavior: Clip.antiAlias,
          child: queryBytes != null
              ? Image.memory(queryBytes!, fit: BoxFit.cover)
              : const Center(child: Icon(Icons.image_outlined, size: 48)),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: onCamera,
                icon: const Icon(Icons.photo_camera_outlined),
                label: const Text('카메라'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: FilledButton.icon(
                onPressed: onGallery,
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('앨범에서'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ResultTile extends StatelessWidget {
  final GoodsCatalogEntry entry;
  final int distance;
  final VoidCallback onTap;

  const _ResultTile({
    required this.entry,
    required this.distance,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 72,
                  height: 72,
                  child: CatalogEntryImage(
                    entry: entry,
                    width: 72,
                    height: 72,
                    borderRadius: 8,
                    placeholderIcon: Icons.image_outlined,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.nameKo,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      [
                        if (entry.characterName.isNotEmpty) entry.characterName,
                        if (entry.affiliation.isNotEmpty) entry.affiliation,
                        if (entry.sourceStore.isNotEmpty) entry.sourceStore,
                      ].join(' · '),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11.5,
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.65),
                      ),
                    ),
                  ],
                ),
              ),
              if (entry.officialPriceJpy != null)
                Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: Text(
                    '¥${entry.officialPriceJpy}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
