import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/calendar_event_item.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_header_title.dart';

const List<Color> _calendarEventColors = [
  Color(0xFFE53935),
  Color(0xFFFF8F00),
  Color(0xFFFDD835),
  Color(0xFF43A047),
  Color(0xFF1E88E5),
  Color(0xFF3949AB),
  Color(0xFF8E24AA),
];

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  DateTime _visibleMonth = DateTime(DateTime.now().year, DateTime.now().month);
  DateTime _selectedDate = DateTime(
    DateTime.now().year,
    DateTime.now().month,
    DateTime.now().day,
  );
  bool _fabExpanded = false;

  Future<void> _openEditor(
    BuildContext context,
    AppState appState, {
    CalendarEventItem? existingEvent,
  }) async {
    final titleController = TextEditingController(text: existingEvent?.title ?? '');
    final memoController = TextEditingController(text: existingEvent?.memo ?? '');
    final now = DateTime.now();
    final parsedTime = _parseTime(existingEvent?.timeText);
    final hourController = TextEditingController(
      text: (parsedTime?.$1 ?? now.hour).toString().padLeft(2, '0'),
    );
    final minuteController = TextEditingController(
      text: (parsedTime?.$2 ?? now.minute).toString().padLeft(2, '0'),
    );

    DateTime startDate = existingEvent?.date ?? _selectedDate;
    DateTime endDate = existingEvent?.endDate ?? existingEvent?.date ?? _selectedDate;
    int selectedColorIndex = _resolveColorIndex(existingEvent?.colorValue);

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final theme = Theme.of(context);
            final palette = theme.extension<DeokivePalette>()!;

            return AlertDialog(
              title: Text(existingEvent == null ? '일정 생성' : '일정 수정'),
              content: SizedBox(
                width: 440,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: titleController,
                        decoration: const InputDecoration(labelText: '일정명'),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () async {
                                final picked = await showDatePicker(
                                  context: context,
                                  initialDate: startDate,
                                  firstDate: DateTime(2020),
                                  lastDate: DateTime(2100),
                                );
                                if (picked != null) {
                                  setDialogState(() {
                                    startDate = picked;
                                    if (endDate.isBefore(startDate)) {
                                      endDate = startDate;
                                    }
                                  });
                                }
                              },
                              child: Text('시작일 ${_dateText(startDate)}'),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () async {
                                final picked = await showDatePicker(
                                  context: context,
                                  initialDate: endDate,
                                  firstDate: startDate,
                                  lastDate: DateTime(2100),
                                );
                                if (picked != null) {
                                  setDialogState(() => endDate = picked);
                                }
                              },
                              child: Text('종료일 ${_dateText(endDate)}'),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: hourController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: '시',
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: minuteController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: '분',
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Text(
                        '색상 선택',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: List.generate(
                          _calendarEventColors.length,
                          (index) => _ColorChoiceDot(
                            color: _calendarEventColors[index],
                            selected: selectedColorIndex == index,
                            onTap: () => setDialogState(() {
                              selectedColorIndex = index;
                            }),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: memoController,
                        maxLines: 4,
                        decoration: const InputDecoration(labelText: '메모'),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () {
                    final title = titleController.text.trim();
                    final hour = int.tryParse(hourController.text.trim());
                    final minute = int.tryParse(minuteController.text.trim());
                    if (title.isEmpty) return;
                    if (hour == null ||
                        minute == null ||
                        hour < 0 ||
                        hour > 23 ||
                        minute < 0 ||
                        minute > 59) {
                      ScaffoldMessenger.of(dialogContext).showSnackBar(
                        const SnackBar(
                          content: Text('시간은 0-23, 분은 0-59 범위로 입력해주세요.'),
                        ),
                      );
                      return;
                    }

                    final event = CalendarEventItem(
                      id: existingEvent?.id ??
                          DateTime.now().millisecondsSinceEpoch.toString(),
                      date: startDate,
                      endDate: endDate,
                      title: title,
                      timeText:
                          '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}',
                      memo: memoController.text.trim().isEmpty
                          ? null
                          : memoController.text.trim(),
                      type: existingEvent?.type ?? CalendarEventType.personal,
                      tags: const [],
                      colorValue: _calendarEventColors[selectedColorIndex].toARGB32(),
                    );

                    if (existingEvent == null) {
                      appState.addCalendarEvent(event);
                    } else {
                      appState.updateCalendarEvent(event);
                    }
                    Navigator.pop(context);
                  },
                  child: const Text('저장'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;
        final selectedEvents = appState.eventsForDate(_selectedDate);
        final days = _buildDays(_visibleMonth);

        return Scaffold(
          appBar: AppBar(
            title: const DeokiveHeaderTitle(),
            centerTitle: true,
          ),
          floatingActionButton: !appState.isLoggedIn ? null : Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (_fabExpanded)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: palette.primary.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          '일정 생성',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      FloatingActionButton.small(
                        heroTag: 'calendar-create-action',
                        backgroundColor: palette.primary.withValues(alpha: 0.5),
                        foregroundColor: palette.text,
                        onPressed: () {
                          setState(() => _fabExpanded = false);
                          _openEditor(context, appState);
                        },
                        child: const Icon(Icons.add_rounded),
                      ),
                    ],
                  ),
                ),
              FloatingActionButton(
                heroTag: 'calendar-main-action',
                backgroundColor: palette.primary.withValues(alpha: 0.5),
                foregroundColor: palette.text,
                onPressed: () {
                  if (!appState.isLoggedIn) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('로그인 후에만 일정을 추가할 수 있습니다.'),
                      ),
                    );
                    return;
                  }
                  setState(() => _fabExpanded = !_fabExpanded);
                },
                child: const Icon(Icons.calendar_month_rounded),
              ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          IconButton(
                            onPressed: () {
                              setState(() {
                                _visibleMonth = DateTime(
                                  _visibleMonth.year,
                                  _visibleMonth.month - 1,
                                );
                              });
                            },
                            icon: const Icon(Icons.chevron_left_rounded),
                          ),
                          Expanded(
                            child: Text(
                              '${_visibleMonth.year}년 ${_visibleMonth.month}월',
                              textAlign: TextAlign.center,
                              style: theme.textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          IconButton(
                            onPressed: () {
                              setState(() {
                                _visibleMonth = DateTime(
                                  _visibleMonth.year,
                                  _visibleMonth.month + 1,
                                );
                              });
                            },
                            icon: const Icon(Icons.chevron_right_rounded),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Row(
                        children: [
                          _WeekLabel('일'),
                          _WeekLabel('월'),
                          _WeekLabel('화'),
                          _WeekLabel('수'),
                          _WeekLabel('목'),
                          _WeekLabel('금'),
                          _WeekLabel('토'),
                        ],
                      ),
                      const SizedBox(height: 8),
                      GridView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: days.length,
                        gridDelegate:
                            const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 7,
                          crossAxisSpacing: 6,
                          mainAxisSpacing: 6,
                          childAspectRatio: 0.9,
                        ),
                        itemBuilder: (context, index) {
                          final day = days[index];
                          final inMonth = day.month == _visibleMonth.month;
                          final isSelected = _sameDay(day, _selectedDate);
                          final matchingEvents = appState.calendarEvents
                              .where((event) => event.occursOn(day))
                              .toList();
                          final markerColor = matchingEvents.isNotEmpty
                              ? _eventColor(matchingEvents.first, palette.primary)
                              : palette.primary;

                          return InkWell(
                            borderRadius: BorderRadius.circular(14),
                            onTap: () {
                              setState(() => _selectedDate = day);
                            },
                            child: Container(
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                color: isSelected
                                    ? markerColor.withValues(alpha: 0.16)
                                    : palette.softSurface.withValues(
                                        alpha: inMonth ? 0.45 : 0.2,
                                      ),
                                border: Border.all(
                                  color: isSelected
                                      ? markerColor.withValues(alpha: 0.32)
                                      : Colors.transparent,
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${day.day}',
                                    style: theme.textTheme.bodyMedium?.copyWith(
                                      fontWeight: FontWeight.w700,
                                      color: inMonth
                                          ? theme.colorScheme.onSurface
                                          : theme.colorScheme.onSurface.withValues(
                                              alpha: 0.35,
                                            ),
                                    ),
                                  ),
                                  const Spacer(),
                                  if (matchingEvents.isNotEmpty)
                                    _EventMarkerRow(
                                      colors: matchingEvents
                                          .map((event) => _eventColor(event, palette.primary))
                                          .toList(),
                                    ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                _selectedDate.year == DateTime.now().year
                    ? '${_selectedDate.month}월 ${_selectedDate.day}일'
                    : '${_selectedDate.year}년 ${_selectedDate.month}월 ${_selectedDate.day}일',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 12),
              if (selectedEvents.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(18),
                    child: Center(child: Text('등록된 일정이 없습니다.')),
                  ),
                )
              else
                ...selectedEvents.map(
                  (event) => Card(
                    child: ListTile(
                      leading: Container(
                        width: 14,
                        height: 14,
                        decoration: BoxDecoration(
                          color: _eventColor(event, palette.primary),
                          shape: BoxShape.circle,
                        ),
                      ),
                      title: Text(event.title),
                      subtitle: Text(
                        '${event.timeText ?? ''}${(event.memo ?? '').isEmpty ? '' : ' · ${event.memo}'}',
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit_outlined),
                            onPressed: () => _openEditor(
                              context,
                              appState,
                              existingEvent: event,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline_rounded),
                            onPressed: () async {
                              final confirmed = await showDialog<bool>(
                                context: context,
                                builder: (dctx) => AlertDialog(
                                  title: const Text('일정 삭제'),
                                  content: Text(
                                    '"${event.title}" 일정을 삭제할까요?\n삭제한 일정은 복구할 수 없어요.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(dctx, false),
                                      child: const Text('취소'),
                                    ),
                                    FilledButton(
                                      style: FilledButton.styleFrom(
                                        backgroundColor:
                                            Theme.of(dctx).colorScheme.error,
                                      ),
                                      onPressed: () =>
                                          Navigator.pop(dctx, true),
                                      child: const Text('삭제'),
                                    ),
                                  ],
                                ),
                              );
                              if (confirmed == true) {
                                appState.deleteCalendarEvent(event.id);
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  List<DateTime> _buildDays(DateTime month) {
    final firstDay = DateTime(month.year, month.month, 1);
    final startOffset = firstDay.weekday % 7;
    final gridStart = firstDay.subtract(Duration(days: startOffset));
    return List.generate(42, (index) => gridStart.add(Duration(days: index)));
  }

  bool _sameDay(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }

  String _dateText(DateTime date) {
    return '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';
  }

  (int, int)? _parseTime(String? text) {
    if (text == null || text.isEmpty) return null;
    final match = RegExp(r'(\d{1,2}):(\d{1,2})').firstMatch(text);
    if (match == null) return null;
    final hour = int.tryParse(match.group(1)!);
    final minute = int.tryParse(match.group(2)!);
    if (hour == null || minute == null) return null;
    return (hour, minute);
  }

  int _resolveColorIndex(int? colorValue) {
    if (colorValue == null) return 0;
    final index = _calendarEventColors.indexWhere(
      (color) => color.toARGB32() == colorValue,
    );
    return index >= 0 ? index : 0;
  }

  Color _eventColor(CalendarEventItem? event, Color fallback) {
    if (event?.colorValue == null) return fallback;
    return Color(event!.colorValue!);
  }
}

class _WeekLabel extends StatelessWidget {
  final String label;

  const _WeekLabel(this.label);

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Center(
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
        ),
      ),
    );
  }
}

class _ColorChoiceDot extends StatelessWidget {
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  const _ColorChoiceDot({
    required this.color,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Container(
        width: 30,
        height: 30,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          border: Border.all(
            color: selected
                ? theme.colorScheme.onSurface
                : Colors.transparent,
            width: 2.5,
          ),
        ),
        child: selected
            ? Icon(
                Icons.check,
                size: 15,
                color: theme.colorScheme.onSurface,
              )
            : null,
      ),
    );
  }
}

class _EventMarkerRow extends StatelessWidget {
  final List<Color> colors;

  const _EventMarkerRow({
    required this.colors,
  });

  @override
  Widget build(BuildContext context) {
    final visibleColors = colors.take(3).toList();
    final extraCount = colors.length - visibleColors.length;
    final theme = Theme.of(context);

    return Row(
      children: [
        for (final color in visibleColors) ...[
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 3),
        ],
        if (extraCount > 0)
          Text(
            '+$extraCount',
            style: theme.textTheme.labelSmall?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
      ],
    );
  }
}
