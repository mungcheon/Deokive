import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';

enum TradeKind { sell, buy, free }

extension TradeKindX on TradeKind {
  String get label {
    switch (this) {
      case TradeKind.sell:
        return '판매';
      case TradeKind.buy:
        return '구매희망';
      case TradeKind.free:
        return '나눔';
    }
  }

  Color get color {
    switch (this) {
      case TradeKind.sell:
        return const Color(0xFF3F8DCC); // blue
      case TradeKind.buy:
        return const Color(0xFFE85C5C); // red
      case TradeKind.free:
        return const Color(0xFF2EA858); // green
    }
  }
}

enum TradeStatus { active, completed }

extension TradeStatusX on TradeStatus {
  String get label {
    switch (this) {
      case TradeStatus.active:
        return '거래중';
      case TradeStatus.completed:
        return '거래완료';
    }
  }
}

class TradePost {
  final String id;
  final String authorId;
  final String authorName;
  final TradeKind kind;
  final TradeStatus status;
  final String title;
  final String description;
  final int? price;
  final String priceCurrencyCode;
  final String? region;
  /// External contact handle so users can DM off-app (e.g. 카톡 오픈채팅 URL,
  /// 인스타 ID, 덕카이브 태그). Free text.
  final String contactInfo;
  final List<Uint8List> imageBytesList;
  final DateTime date;
  final int viewCount;

  const TradePost({
    required this.id,
    required this.authorId,
    required this.authorName,
    required this.kind,
    this.status = TradeStatus.active,
    required this.title,
    required this.description,
    required this.price,
    this.priceCurrencyCode = 'KRW',
    required this.region,
    required this.contactInfo,
    this.imageBytesList = const [],
    required this.date,
    this.viewCount = 0,
  });

  TradePost copyWith({
    String? id,
    String? authorId,
    String? authorName,
    TradeKind? kind,
    TradeStatus? status,
    String? title,
    String? description,
    int? price,
    String? priceCurrencyCode,
    String? region,
    String? contactInfo,
    List<Uint8List>? imageBytesList,
    DateTime? date,
    int? viewCount,
  }) {
    return TradePost(
      id: id ?? this.id,
      authorId: authorId ?? this.authorId,
      authorName: authorName ?? this.authorName,
      kind: kind ?? this.kind,
      status: status ?? this.status,
      title: title ?? this.title,
      description: description ?? this.description,
      price: price ?? this.price,
      priceCurrencyCode: priceCurrencyCode ?? this.priceCurrencyCode,
      region: region ?? this.region,
      contactInfo: contactInfo ?? this.contactInfo,
      imageBytesList: imageBytesList ?? this.imageBytesList,
      date: date ?? this.date,
      viewCount: viewCount ?? this.viewCount,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'authorId': authorId,
        'authorName': authorName,
        'kind': kind.name,
        'status': status.name,
        'title': title,
        'description': description,
        'price': price,
        'priceCurrencyCode': priceCurrencyCode,
        'region': region,
        'contactInfo': contactInfo,
        'imageBytesList':
            imageBytesList.map((b) => base64Encode(b)).toList(growable: false),
        'date': date.toIso8601String(),
        'viewCount': viewCount,
      };

  factory TradePost.fromJson(Map<String, dynamic> json) {
    final imagesRaw = json['imageBytesList'] as List<dynamic>?;
    final images = imagesRaw == null
        ? <Uint8List>[]
        : imagesRaw
            .map((e) => base64Decode(e as String))
            .toList(growable: false);
    return TradePost(
      id: json['id'] as String? ?? '',
      authorId: json['authorId'] as String? ?? '',
      authorName: json['authorName'] as String? ?? '',
      kind: TradeKind.values.firstWhere(
        (k) => k.name == json['kind'],
        orElse: () => TradeKind.sell,
      ),
      status: TradeStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => TradeStatus.active,
      ),
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      price: (json['price'] as num?)?.toInt(),
      priceCurrencyCode: json['priceCurrencyCode'] as String? ?? 'KRW',
      region: json['region'] as String?,
      contactInfo: json['contactInfo'] as String? ?? '',
      imageBytesList: images,
      date:
          DateTime.tryParse(json['date'] as String? ?? '') ?? DateTime.now(),
      viewCount: (json['viewCount'] as num?)?.toInt() ?? 0,
    );
  }
}
