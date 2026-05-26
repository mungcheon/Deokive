// Shared event/notice data used by both the home news section and the board
// event-calendar tab. Each entry has a concrete date (and optional endDate)
// so the board can render dot markers on a calendar.

class EventNotice {
  final String title;
  final DateTime date;
  final DateTime? endDate;
  final String summary;
  final String content;
  final EventNoticeKind kind;

  const EventNotice({
    required this.title,
    required this.date,
    this.endDate,
    required this.summary,
    required this.content,
    this.kind = EventNoticeKind.event,
  });

  bool occursOn(DateTime day) {
    final d0 = DateTime(date.year, date.month, date.day);
    final d1 = endDate == null
        ? d0
        : DateTime(endDate!.year, endDate!.month, endDate!.day);
    final t = DateTime(day.year, day.month, day.day);
    return !t.isBefore(d0) && !t.isAfter(d1);
  }
}

enum EventNoticeKind { notice, goodsNews, event }

/// Curated demo data. Replace with server-fed content later.
final List<EventNotice> kEventNotices = <EventNotice>[
  EventNotice(
    title: '이번 달 행사 일정 모아보기',
    date: DateTime(2026, 3, 11),
    summary: '팝업, 전시, 팬 이벤트 일정을 한 번에 정리했습니다.',
    content:
        '이번 달 예정된 팝업 스토어, 전시, 팬 이벤트 일정을 확인해보세요.\n\n가고 싶은 일정은 캘린더에 등록해두면 날짜별로 더 쉽게 확인할 수 있습니다.',
  ),
  EventNotice(
    title: '행사 체크 포인트',
    date: DateTime(2026, 3, 8),
    summary: '행사 전에 확인하면 좋은 준비 사항입니다.',
    content:
        '입장 시간, 현장 구매 제한, 특전 수령 조건 등 행사 전 확인이 필요한 항목을 정리했습니다.\n\n행사 일정과 개인 일정은 캘린더에서 색상으로 구분해서 볼 수 있습니다.',
  ),
  EventNotice(
    title: '치이카와샵 용산점 정식 오픈',
    date: DateTime(2026, 2, 27),
    summary: '국내 첫 치이카와 공식 상설 매장이 용산 아이파크몰에 오픈했습니다.',
    content:
        '치이카와샵 용산점이 2026년 2월 27일(금) 정식 오픈했습니다.\n\n'
        '📍 위치: 서울 용산구 한강대로21나길 17, 아이파크몰 용산점 리빙파크 3F 도파민스테이션\n'
        '🕒 운영시간: 10:30 ~ 22:00\n\n'
        '단발성 팝업이 아닌 상시 운영 매장으로, 일본 치이카와 마켓의 공식 굿즈를 국내에서 직접 구매할 수 있습니다.',
  ),
  EventNotice(
    title: '이치방쿠지 신규 발매',
    date: DateTime(2026, 6, 10),
    summary: '치이카와 이치방쿠지 신규 캠페인 발매 안내.',
    content:
        '치이카와 이치방쿠지 신규 캠페인이 6월 10일 발매됩니다.\n\nA상~라스트원상 구성과 매장 정보를 확인하세요.',
  ),
];
