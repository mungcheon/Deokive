enum CalendarEventType {
  day,
  personal,
  event,
  release,
  delivery,
}

class CalendarEventItem {
  final String id;
  final DateTime date;
  final DateTime? endDate;
  final String title;
  final String? timeText;
  final String? memo;
  final List<String> tags;
  final CalendarEventType type;
  final int? colorValue;
  final DateTime? startAt;
  final DateTime? endAt;
  final bool isShared;

  const CalendarEventItem({
    required this.id,
    required this.date,
    this.endDate,
    required this.title,
    this.timeText,
    this.memo,
    this.tags = const [],
    this.type = CalendarEventType.personal,
    this.colorValue,
    this.startAt,
    this.endAt,
    this.isShared = false,
  });

  CalendarEventItem copyWith({
    String? id,
    DateTime? date,
    Object? endDate = _sentinel,
    String? title,
    Object? timeText = _sentinel,
    Object? memo = _sentinel,
    List<String>? tags,
    CalendarEventType? type,
    Object? colorValue = _sentinel,
    Object? startAt = _sentinel,
    Object? endAt = _sentinel,
    bool? isShared,
  }) {
    return CalendarEventItem(
      id: id ?? this.id,
      date: date ?? this.date,
      endDate: identical(endDate, _sentinel) ? this.endDate : endDate as DateTime?,
      title: title ?? this.title,
      timeText: identical(timeText, _sentinel) ? this.timeText : timeText as String?,
      memo: identical(memo, _sentinel) ? this.memo : memo as String?,
      tags: tags ?? this.tags,
      type: type ?? this.type,
      colorValue: identical(colorValue, _sentinel) ? this.colorValue : colorValue as int?,
      startAt: identical(startAt, _sentinel) ? this.startAt : startAt as DateTime?,
      endAt: identical(endAt, _sentinel) ? this.endAt : endAt as DateTime?,
      isShared: isShared ?? this.isShared,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'date': date.toIso8601String(),
      'endDate': endDate?.toIso8601String(),
      'title': title,
      'timeText': displayTimeText,
      'memo': memo,
      'tags': tags,
      'type': type.name,
      'colorValue': colorValue,
      'startAt': startAt?.toIso8601String(),
      'endAt': endAt?.toIso8601String(),
      'isShared': isShared,
    };
  }

  factory CalendarEventItem.fromJson(Map<String, dynamic> json) {
    return CalendarEventItem(
      id: json['id'] as String? ?? '',
      date: DateTime.tryParse(json['date'] as String? ?? '') ?? DateTime.now(),
      endDate: DateTime.tryParse(json['endDate'] as String? ?? ''),
      title: json['title'] as String? ?? '',
      timeText: json['timeText'] as String?,
      memo: json['memo'] as String?,
      tags: ((json['tags'] as List<dynamic>?) ?? const [])
          .map((item) => item.toString())
          .toList(),
      type: CalendarEventType.values.firstWhere(
        (value) => value.name == json['type'],
        orElse: () => CalendarEventType.personal,
      ),
      colorValue: json['colorValue'] as int?,
      startAt: DateTime.tryParse(json['startAt'] as String? ?? ''),
      endAt: DateTime.tryParse(json['endAt'] as String? ?? ''),
      isShared: json['isShared'] as bool? ?? false,
    );
  }

  DateTime get normalizedStartDate {
    final value = startAt ?? date;
    return DateTime(value.year, value.month, value.day);
  }

  DateTime get normalizedEndDate {
    final value = endAt ?? endDate ?? startAt ?? date;
    return DateTime(value.year, value.month, value.day);
  }

  DateTime? get effectiveStartAt => startAt ?? _legacyStartAt;

  DateTime? get effectiveEndAt {
    if (endAt != null) return endAt;
    if (_legacyStartAt == null) return null;
    final legacyEnd = _legacyEndTimeParts;
    if (legacyEnd == null) return _legacyStartAt;
    return DateTime(
      normalizedEndDate.year,
      normalizedEndDate.month,
      normalizedEndDate.day,
      legacyEnd.$1,
      legacyEnd.$2,
    );
  }

  String? get displayTimeText {
    final start = effectiveStartAt;
    final end = effectiveEndAt;
    if (start == null && timeText != null && timeText!.trim().isNotEmpty) {
      return timeText!.trim();
    }
    if (start == null) return null;
    final startText = _formatTime(start);
    if (end == null) return startText;
    final endText = _formatTime(end);
    if (startText == endText && !spansMultipleDays) {
      return startText;
    }
    return '$startText - $endText';
  }

  bool occursOn(DateTime targetDate) {
    final day = DateTime(targetDate.year, targetDate.month, targetDate.day);
    return !day.isBefore(normalizedStartDate) && !day.isAfter(normalizedEndDate);
  }

  bool get spansMultipleDays => normalizedStartDate != normalizedEndDate;

  DateTime? get _legacyStartAt {
    final parts = _legacyStartTimeParts;
    if (parts == null) return null;
    return DateTime(date.year, date.month, date.day, parts.$1, parts.$2);
  }

  (int, int)? get _legacyStartTimeParts {
    final value = timeText?.trim();
    if (value == null || value.isEmpty) return null;
    final rangeMatch =
        RegExp(r'^\s*(\d{1,2}):(\d{2})\s*[-~]\s*(\d{1,2}):(\d{2})\s*$')
            .firstMatch(value);
    if (rangeMatch != null) {
      return (
        int.parse(rangeMatch.group(1)!),
        int.parse(rangeMatch.group(2)!),
      );
    }
    final singleMatch = RegExp(r'^\s*(\d{1,2}):(\d{2})\s*$').firstMatch(value);
    if (singleMatch == null) return null;
    return (
      int.parse(singleMatch.group(1)!),
      int.parse(singleMatch.group(2)!),
    );
  }

  (int, int)? get _legacyEndTimeParts {
    final value = timeText?.trim();
    if (value == null || value.isEmpty) return null;
    final rangeMatch =
        RegExp(r'^\s*(\d{1,2}):(\d{2})\s*[-~]\s*(\d{1,2}):(\d{2})\s*$')
            .firstMatch(value);
    if (rangeMatch == null) return null;
    return (
      int.parse(rangeMatch.group(3)!),
      int.parse(rangeMatch.group(4)!),
    );
  }

  static String _formatTime(DateTime value) {
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }
}

const Object _sentinel = Object();
