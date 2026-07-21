import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/calendar_event_item.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../widgets/deokive_header_title.dart';

const List<Color> _calendarEventColors = [
  Color(0xFFF4A7A7),
  Color(0xFFF7C89A),
  Color(0xFFF7E6A6),
  Color(0xFFB8E3B1),
  Color(0xFFAED8F2),
  Color(0xFFB8C4F2),
  Color(0xFFD8B4E8),
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

    DateTime startDate = existingEvent?.normalizedStartDate ?? _selectedDate;
    DateTime endDate = existingEvent?.normalizedEndDate ?? _selectedDate;
    TimeOfDay startTime = _timeOfDayFor(existingEvent?.effectiveStartAt) ??
        const TimeOfDay(hour: 9, minute: 0);
    TimeOfDay endTime = _timeOfDayFor(existingEvent?.effectiveEndAt) ??
        TimeOfDay(hour: (startTime.hour + 1) % 24, minute: startTime.minute);
    int selectedColorIndex = _resolveColorIndex(existingEvent?.colorValue);

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final theme = Theme.of(context);

            Future<void> pickDate({required bool isStart}) async {
              final picked = await showDatePicker(
                context: context,
                initialDate: isStart ? startDate : endDate,
                firstDate: DateTime(2020),
                lastDate: DateTime(2100),
              );
              if (picked == null) return;
              setDialogState(() {
                if (isStart) {
                  startDate = picked;
                  final startDateTime = _mergeDateAndTime(startDate, startTime);
                  final currentEnd = _mergeDateAndTime(endDate, endTime);
                  if (currentEnd.isBefore(startDateTime)) {
                    endDate = picked;
                    endTime = TimeOfDay(
                      hour: (startTime.hour + 1) % 24,
                      minute: startTime.minute,
                    );
                  }
                } else {
                  endDate = picked;
                }
              });
            }

            Future<void> pickTime({required bool isStart}) async {
              final picked = await showTimePicker(
                context: context,
                initialTime: isStart ? startTime : endTime,
              );
              if (picked == null) return;
              setDialogState(() {
                if (isStart) {
                  startTime = picked;
                } else {
                  endTime = picked;
                }
              });
            }

            return AlertDialog(
              title: Text(existingEvent == null ? '일정 생성' : '일정 수정'),
              content: SizedBox(
                width: 460,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: titleController,
                        decoration: const InputDecoration(labelText: '일정명'),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        '시작',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => pickDate(isStart: true),
                              child: Text(_dateText(startDate)),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => pickTime(isStart: true),
                              child: Text(_timeOfDayText(startTime)),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Text(
                        '종료',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => pickDate(isStart: false),
                              child: Text(_dateText(endDate)),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => pickTime(isStart: false),
                              child: Text(_timeOfDayText(endTime)),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
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
                      const SizedBox(height: 16),
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
                    if (title.isEmpty) {
                      ScaffoldMessenger.of(dialogContext).showSnackBar(
                        const SnackBar(content: Text('일정명을 입력해 주세요.')),
                      );
                      return;
                    }

                    final startAt = _mergeDateAndTime(startDate, startTime);
                    final endAt = _mergeDateAndTime(endDate, endTime);
                    if (endAt.isBefore(startAt)) {
                      ScaffoldMessenger.of(dialogContext).showSnackBar(
                        const SnackBar(
                          content: Text('종료 시간은 시작 시간보다 늦어야 해요.'),
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
                      timeText: null,
                      memo: memoController.text.trim().isEmpty
                          ? null
                          : memoController.text.trim(),
                      type: existingEvent?.type ?? CalendarEventType.personal,
                      tags: const [],
                      colorValue: _calendarEventColors[selectedColorIndex].toARGB32(),
                      startAt: startAt,
                      endAt: endAt,
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
        final selectedEvents = [...appState.eventsForDate(_selectedDate)]
          ..sort((a, b) {
            final aStart = a.effectiveStartAt ?? a.date;
            final bStart = b.effectiveStartAt ?? b.date;
            return aStart.compareTo(bStart);
          });
        final days = _buildDays(_visibleMonth);

        return Scaffold(
          appBar: AppBar(
            title: const DeokiveHeaderTitle(),
            centerTitle: true,
          ),
          floatingActionButton: !appState.isLoggedIn
              ? null
              : Column(
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
                                          .map((event) =>
                                              _eventColor(event, palette.primary))
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
                      subtitle: Text(_buildSubtitle(event)),
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
                                      onPressed: () => Navigator.pop(dctx, false),
                                      child: const Text('취소'),
                                    ),
                                    FilledButton(
                                      style: FilledButton.styleFrom(
                                        backgroundColor:
                                            Theme.of(dctx).colorScheme.error,
                                      ),
                                      onPressed: () => Navigator.pop(dctx, true),
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

  String _timeOfDayText(TimeOfDay time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  TimeOfDay? _timeOfDayFor(DateTime? value) {
    if (value == null) return null;
    return TimeOfDay(hour: value.hour, minute: value.minute);
  }

  DateTime _mergeDateAndTime(DateTime date, TimeOfDay time) {
    return DateTime(date.year, date.month, date.day, time.hour, time.minute);
  }

  String _buildSubtitle(CalendarEventItem event) {
    final dateText = event.spansMultipleDays
        ? '${_dateText(event.normalizedStartDate)} - ${_dateText(event.normalizedEndDate)}'
        : _dateText(event.normalizedStartDate);
    final timeText = event.displayTimeText;
    final memo = event.memo?.trim();
    final parts = <String>[
      dateText,
      if (timeText != null && timeText.isNotEmpty) timeText,
      if (memo != null && memo.isNotEmpty) memo,
    ];
    return parts.join(' · ');
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
            color: selected ? theme.colorScheme.onSurface : Colors.transparent,
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
