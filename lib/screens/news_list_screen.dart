import 'package:flutter/material.dart';

import '../config/monetization_catalog.dart';
import '../widgets/live_banner_ad.dart';
import 'news_detail_screen.dart';

class NewsListScreen extends StatelessWidget {
  final String title;
  final List<Map<String, String>> posts;

  const NewsListScreen({
    super.key,
    required this.title,
    required this.posts,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
      ),
      body: posts.isEmpty
          ? const Center(
              child: Text(
                '아직 등록된 글이 없습니다.',
                style: TextStyle(fontSize: 16),
              ),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                ...List.generate(posts.length, (index) {
                  final post = posts[index];

                  return Padding(
                    padding:
                        EdgeInsets.only(bottom: index == posts.length - 1 ? 0 : 12),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => NewsDetailScreen(
                              title: post['title'] ?? '',
                              date: post['date'] ?? '',
                              content: post['content'] ?? '',
                            ),
                          ),
                        );
                      },
                      child: Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                post['title'] ?? '',
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 6),
                              Text(post['date'] ?? ''),
                              const SizedBox(height: 10),
                              Text(
                                post['summary'] ?? '',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.copyWith(height: 1.4),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                }),
                const SizedBox(height: 16),
                const Center(
                  child: LiveBannerAd(placement: AdPlacement.newsFeedBanner),
                ),
              ],
            ),
    );
  }
}
