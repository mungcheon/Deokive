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

  const CalendarEventItem({
    required this.id,
    required this.date,
    this.endDate,
    required this.title,
    required this.timeText,
    required this.memo,
    this.tags = const [],
    this.type = CalendarEventType.personal,
    this.colorValue,
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
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'date': date.toIso8601String(),
      'endDate': endDate?.toIso8601String(),
      'title': title,
      'timeText': timeText,
      'memo': memo,
      'tags': tags,
      'type': type.name,
      'colorValue': colorValue,
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
    );
  }

  DateTime get normalizedStartDate => DateTime(date.year, date.month, date.day);

  DateTime get normalizedEndDate {
    final value = endDate ?? date;
    return DateTime(value.year, value.month, value.day);
  }

  bool occursOn(DateTime targetDate) {
    final day = DateTime(targetDate.year, targetDate.month, targetDate.day);
    return !day.isBefore(normalizedStartDate) && !day.isAfter(normalizedEndDate);
  }

  bool get spansMultipleDays => normalizedStartDate != normalizedEndDate;
}

const Object _sentinel = Object();
