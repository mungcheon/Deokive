class SupportInquiryItem {
  final String id;
  final String title;
  final String content;
  final String email;
  final DateTime createdAt;
  final String? answer;
  final DateTime? answeredAt;

  const SupportInquiryItem({
    required this.id,
    required this.title,
    required this.content,
    required this.email,
    required this.createdAt,
    this.answer,
    this.answeredAt,
  });

  bool get isAnswered => answer != null;

  SupportInquiryItem copyWith({
    String? id,
    String? title,
    String? content,
    String? email,
    DateTime? createdAt,
    String? answer,
    DateTime? answeredAt,
  }) {
    return SupportInquiryItem(
      id: id ?? this.id,
      title: title ?? this.title,
      content: content ?? this.content,
      email: email ?? this.email,
      createdAt: createdAt ?? this.createdAt,
      answer: answer ?? this.answer,
      answeredAt: answeredAt ?? this.answeredAt,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'content': content,
      'email': email,
      'createdAt': createdAt.toIso8601String(),
      'answer': answer,
      'answeredAt': answeredAt?.toIso8601String(),
    };
  }

  factory SupportInquiryItem.fromJson(Map<String, dynamic> json) {
    return SupportInquiryItem(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      content: json['content'] as String? ?? '',
      email: json['email'] as String? ?? '',
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? '') ?? DateTime.now(),
      answer: json['answer'] as String?,
      answeredAt: json['answeredAt'] == null
          ? null
          : DateTime.tryParse(json['answeredAt'] as String),
    );
  }
}
