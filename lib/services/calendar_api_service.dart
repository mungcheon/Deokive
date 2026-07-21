import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/server_config.dart';
import '../models/calendar_event_item.dart';
import 'local_admin_override.dart';

class CalendarApiUnavailable implements Exception {
  final String message;
  const CalendarApiUnavailable([this.message = 'server not configured']);

  @override
  String toString() => 'CalendarApiUnavailable: $message';
}

class CalendarApiService {
  final http.Client _http;

  CalendarApiService({http.Client? client}) : _http = client ?? http.Client();

  void dispose() => _http.close();

  bool get enabled => ServerConfig.enabled;

  Map<String, String> _headers([String? token]) => {
        'Content-Type': 'application/json',
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
        if (localAdminOverrideEnabled) 'X-Deokive-App-Admin': '1',
      };

  Future<List<CalendarEventItem>> fetchSharedEvents() async {
    if (!enabled) throw const CalendarApiUnavailable();
    final uri = ServerConfig.boardUri('/calendar/events');
    final resp = await _http.get(uri).timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw CalendarApiUnavailable('list failed ${resp.statusCode}');
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    if (data is! List) return const [];
    return data.whereType<Map<String, dynamic>>().map(_fromServer).toList();
  }

  Future<CalendarEventItem> createSharedEvent(
    String? token,
    CalendarEventItem event,
  ) async {
    if (!enabled) throw const CalendarApiUnavailable();
    final uri = ServerConfig.boardUri('/calendar/events');
    final resp = await _http
        .post(
          uri,
          headers: _headers(token),
          body: jsonEncode(_payload(event)),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 201) {
      throw CalendarApiUnavailable('create failed ${resp.statusCode}');
    }
    return _fromServer(jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>);
  }

  Future<CalendarEventItem> updateSharedEvent(
    String? token,
    CalendarEventItem event,
  ) async {
    if (!enabled) throw const CalendarApiUnavailable();
    final serverId = _serverId(event.id);
    if (serverId == null) {
      throw const CalendarApiUnavailable('invalid event id');
    }
    final uri = ServerConfig.boardUri('/calendar/events/$serverId');
    final resp = await _http
        .patch(
          uri,
          headers: _headers(token),
          body: jsonEncode(_payload(event)),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw CalendarApiUnavailable('update failed ${resp.statusCode}');
    }
    return _fromServer(jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>);
  }

  Future<void> deleteSharedEvent(String? token, String eventId) async {
    if (!enabled) throw const CalendarApiUnavailable();
    final serverId = _serverId(eventId);
    if (serverId == null) return;
    final uri = ServerConfig.boardUri('/calendar/events/$serverId');
    final resp = await _http
        .delete(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 204) {
      throw CalendarApiUnavailable('delete failed ${resp.statusCode}');
    }
  }

  Map<String, dynamic> _payload(CalendarEventItem event) => {
        'title': event.title,
        'event_type': event.type.name,
        'event_date': event.date.toIso8601String(),
        'end_date': event.endDate?.toIso8601String(),
        'time_text': event.timeText,
        'memo': event.memo,
        'color_value': event.colorValue,
        'start_at': event.startAt?.toIso8601String(),
        'end_at': event.endAt?.toIso8601String(),
      };

  CalendarEventItem _fromServer(Map<String, dynamic> m) {
    return CalendarEventItem(
      id: 'shared_${m['id']}',
      date: DateTime.tryParse(m['event_date'] as String? ?? '') ?? DateTime.now(),
      endDate: DateTime.tryParse(m['end_date'] as String? ?? ''),
      title: m['title'] as String? ?? '',
      timeText: m['time_text'] as String?,
      memo: m['memo'] as String?,
      tags: const ['shared'],
      type: CalendarEventType.values.firstWhere(
        (value) => value.name == (m['event_type'] as String? ?? ''),
        orElse: () => CalendarEventType.personal,
      ),
      colorValue: (m['color_value'] as num?)?.toInt(),
      startAt: DateTime.tryParse(m['start_at'] as String? ?? ''),
      endAt: DateTime.tryParse(m['end_at'] as String? ?? ''),
      isShared: true,
    );
  }

  int? _serverId(String eventId) {
    if (!eventId.startsWith('shared_')) return null;
    return int.tryParse(eventId.substring(7));
  }
}
