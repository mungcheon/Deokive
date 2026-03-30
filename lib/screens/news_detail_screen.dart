import 'package:flutter/material.dart';

import '../config/monetization_catalog.dart';
import '../widgets/live_banner_ad.dart';

class NewsDetailScreen extends StatelessWidget {
  final String title;
  final String date;
  final String content;

  const NewsDetailScreen({
    super.key,
    required this.title,
    required this.date,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('소식 상세'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                          height: 1.3,
                        ),
                  ),
                  const SizedBox(height: 10),
                  Text(date),
                  const SizedBox(height: 20),
                  Text(
                    content,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          height: 1.65,
                        ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Center(
            child: LiveBannerAd(placement: AdPlacement.newsFeedBanner),
          ),
        ],
      ),
    );
  }
}
