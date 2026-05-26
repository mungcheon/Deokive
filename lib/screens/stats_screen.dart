import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';

class StatsScreen extends StatelessWidget {
  const StatsScreen({super.key});

  static const List<Color> _palette = [
    Color(0xFFF08B88),
    Color(0xFFC89CEB),
    Color(0xFFA89CF0),
    Color(0xFF87CEEB),
    Color(0xFFFFB7C5),
    Color(0xFFA0E7E5),
    Color(0xFFFFD699),
    Color(0xFFB5EAD7),
    Color(0xFFE0BBE4),
    Color(0xFFFFB6B9),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('통계')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [StatsContent()],
      ),
    );
  }
}

/// Inline stats charts that can be embedded inside other screens (e.g. home).
/// 2-level drill-down: 소속 차트에서 막대를 탭하면 해당 소속의 캐릭터 분포로
/// 전환. 캐릭터가 폭증해도 한 화면에 항상 ~20개 이하만 표시되도록 설계.
class StatsContent extends StatefulWidget {
  const StatsContent({super.key});

  @override
  State<StatsContent> createState() => _StatsContentState();
}

class _StatsContentState extends State<StatsContent> {
  String? _drilledAffiliation;

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final affiliationMap = appState.goodsCountByAffiliation;
        final categoryMap = appState.goodsCountByCategory;
        final characterMapAll = appState.goodsCountByCharacter;
        final ownerName =
            appState.isLoggedIn ? appState.displayName : 'Guest';
        final theme = Theme.of(context);

        // Drill-down: when an affiliation is selected, show its characters.
        Map<String, int>? characterMap;
        if (_drilledAffiliation != null) {
          characterMap = appState
              .goodsCountByCharacterInAffiliation(_drilledAffiliation!);
        }

        // Top 3 most-collected characters → 최애의 전당.
        final podium = characterMapAll.entries.toList()
          ..sort((a, b) => b.value.compareTo(a.value));
        final top3 = podium.take(3).toList();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 0, 4, 14),
              child: Text(
                '$ownerName 의 폴더 통계',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            _FavoriteHallCard(top: top3),
            const SizedBox(height: 18),
            if (_drilledAffiliation == null)
              _ChartCard(
                title: '소속별 굿즈 수',
                data: affiliationMap,
                chartBuilder: (entries) => _CategoryBarChart(
                  entries: entries,
                  onTapBar: (label) =>
                      setState(() => _drilledAffiliation = label),
                ),
              )
            else
              _ChartCard(
                title: '$_drilledAffiliation 캐릭터별 굿즈 수',
                data: characterMap ?? const {},
                trailing: TextButton.icon(
                  onPressed: () =>
                      setState(() => _drilledAffiliation = null),
                  icon: const Icon(Icons.arrow_back_rounded, size: 16),
                  label: const Text('소속으로'),
                ),
                chartBuilder: (entries) => _CategoryBarChart(entries: entries),
              ),
            const SizedBox(height: 18),
            _ChartCard(
              title: '카테고리별 굿즈 수',
              data: categoryMap,
              chartBuilder: (entries) =>
                  _CategoryBarChart(entries: entries),
            ),
          ],
        );
      },
    );
  }
}

class _ChartCard extends StatelessWidget {
  final String title;
  final Widget? trailing;
  final Map<String, int> data;
  final Widget Function(List<MapEntry<String, int>> entries) chartBuilder;

  const _ChartCard({
    required this.title,
    required this.data,
    required this.chartBuilder,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final entries = data.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    // Top-10 + (rest aggregated as 기타) so the chart stays readable even
    // when there are 100+ entries.
    const showCount = 10;
    final top = entries.take(showCount).toList();
    final rest = entries.skip(showCount).toList();
    if (rest.isNotEmpty) {
      final restSum = rest.fold<int>(0, (sum, e) => sum + e.value);
      top.add(MapEntry('기타 (${rest.length})', restSum));
    }

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: Theme.of(context).colorScheme.outline),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w800),
                  ),
                ),
                if (trailing != null) trailing!,
              ],
            ),
            const SizedBox(height: 14),
            if (top.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 32),
                child: Center(child: Text('아직 표시할 데이터가 없습니다.')),
              )
            else
              chartBuilder(top),
          ],
        ),
      ),
    );
  }
}


class _CategoryBarChart extends StatelessWidget {
  final List<MapEntry<String, int>> entries;
  final ValueChanged<String>? onTapBar;

  const _CategoryBarChart({required this.entries, this.onTapBar});

  @override
  Widget build(BuildContext context) {
    final maxValue = entries.first.value.toDouble();
    final maxY = maxValue + (maxValue * 0.2).clamp(1, 999999);
    // Pick a clean integer interval so the left axis shows whole numbers
    // (e.g. 0, 1, 2 instead of 0.0, 0.5, 1.0).
    int leftInterval = (maxY / 5).ceil();
    if (leftInterval < 1) leftInterval = 1;
    final reservedLeft = maxY >= 1000 ? 40.0 : (maxY >= 100 ? 34.0 : 28.0);
    return SizedBox(
      height: 240,
      child: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: maxY,
          barTouchData: BarTouchData(
            enabled: true,
            handleBuiltInTouches: false,
            touchCallback: (event, response) {
              if (!event.isInterestedForInteractions) return;
              final spot = response?.spot;
              if (spot == null) return;
              if (event is FlTapUpEvent && onTapBar != null) {
                final i = spot.touchedBarGroupIndex;
                if (i < 0 || i >= entries.length) return;
                final key = entries[i].key;
                // Don't drill into the "기타 (N)" aggregate bucket.
                if (key.startsWith('기타 ')) return;
                onTapBar!(key);
              }
            },
          ),
          barGroups: [
            for (var i = 0; i < entries.length; i++)
              BarChartGroupData(
                x: i,
                barRods: [
                  BarChartRodData(
                    toY: entries[i].value.toDouble(),
                    color: StatsScreen._palette[i % StatsScreen._palette.length],
                    width: 18,
                    borderRadius: BorderRadius.circular(6),
                  ),
                ],
              ),
          ],
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: reservedLeft,
                interval: leftInterval.toDouble(),
                getTitlesWidget: (value, meta) {
                  // Only render whole numbers; skip the very top to avoid
                  // overlap with the chart frame.
                  if (value < 0) return const SizedBox.shrink();
                  final n = value.round();
                  if ((value - n).abs() > 0.01) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: Text(
                      '$n',
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            rightTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  final i = value.toInt();
                  if (i < 0 || i >= entries.length) {
                    return const SizedBox.shrink();
                  }
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      entries[i].key,
                      style: const TextStyle(fontSize: 10),
                      overflow: TextOverflow.ellipsis,
                    ),
                  );
                },
              ),
            ),
          ),
          gridData: const FlGridData(show: true),
          borderData: FlBorderData(show: false),
        ),
      ),
    );
  }
}

// ── 최애의 전당 (top-3 characters by goods count) ───────────────────────

class _FavoriteHallCard extends StatelessWidget {
  final List<MapEntry<String, int>> top;

  const _FavoriteHallCard({required this.top});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // Podium order on screen: 2nd | 1st | 3rd. Center is tallest.
    final first = top.isNotEmpty ? top[0] : null;
    final second = top.length >= 2 ? top[1] : null;
    final third = top.length >= 3 ? top[2] : null;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: theme.colorScheme.outline),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('👑',
                    style: TextStyle(fontSize: 18)),
                const SizedBox(width: 6),
                Text(
                  '최애의 전당',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(width: 6),
                Text(
                  'TOP 3',
                  style: TextStyle(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.55),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            if (first == null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16),
                child: Center(
                  child: Text(
                    '캐릭터 정보가 있는 굿즈를 추가하면 전당이 채워져요.',
                    style: TextStyle(
                      color:
                          theme.colorScheme.onSurface.withValues(alpha: 0.6),
                      fontSize: 13,
                    ),
                  ),
                ),
              )
            else
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: _PodiumSlot(
                      rank: 2,
                      entry: second,
                      height: 96,
                      rankColor: const Color(0xFFB4BCC2),
                    ),
                  ),
                  Expanded(
                    child: _PodiumSlot(
                      rank: 1,
                      entry: first,
                      height: 124,
                      rankColor: const Color(0xFFE6B23A),
                    ),
                  ),
                  Expanded(
                    child: _PodiumSlot(
                      rank: 3,
                      entry: third,
                      height: 76,
                      rankColor: const Color(0xFFC98A52),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _PodiumSlot extends StatelessWidget {
  final int rank;
  final MapEntry<String, int>? entry;
  final double height;
  final Color rankColor;

  const _PodiumSlot({
    required this.rank,
    required this.entry,
    required this.height,
    required this.rankColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final filled = entry != null;
    final medal = rank == 1 ? '🥇' : (rank == 2 ? '🥈' : '🥉');

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Text(medal, style: const TextStyle(fontSize: 28)),
          const SizedBox(height: 4),
          Text(
            filled ? entry!.key : '—',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w800,
              color: filled
                  ? theme.colorScheme.onSurface
                  : theme.colorScheme.onSurface.withValues(alpha: 0.4),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            filled ? '${entry!.value}개' : '',
            style: TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              color: filled
                  ? rankColor
                  : theme.colorScheme.onSurface.withValues(alpha: 0.4),
            ),
          ),
          const SizedBox(height: 6),
          Container(
            height: height,
            decoration: BoxDecoration(
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(12)),
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: filled
                    ? [
                        rankColor.withValues(alpha: 0.85),
                        rankColor.withValues(alpha: 0.55),
                      ]
                    : [
                        theme.colorScheme.onSurface.withValues(alpha: 0.08),
                        theme.colorScheme.onSurface.withValues(alpha: 0.04),
                      ],
              ),
              border: Border(
                top: BorderSide(
                  color: filled
                      ? Colors.white.withValues(alpha: 0.6)
                      : Colors.transparent,
                  width: 2,
                ),
              ),
            ),
            child: Center(
              child: Text(
                '$rank',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                  color: filled
                      ? Colors.white
                      : theme.colorScheme.onSurface.withValues(alpha: 0.3),
                  shadows: filled
                      ? const [
                          Shadow(color: Colors.black26, blurRadius: 2)
                        ]
                      : null,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

