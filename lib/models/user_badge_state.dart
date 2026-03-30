class UserBadgeState {
  final String badgeId;
  final bool isUnlocked;
  final bool isEquipped;
  final DateTime? unlockedAt;

  const UserBadgeState({
    required this.badgeId,
    required this.isUnlocked,
    required this.isEquipped,
    required this.unlockedAt,
  });

  UserBadgeState copyWith({
    String? badgeId,
    bool? isUnlocked,
    bool? isEquipped,
    DateTime? unlockedAt,
  }) {
    return UserBadgeState(
      badgeId: badgeId ?? this.badgeId,
      isUnlocked: isUnlocked ?? this.isUnlocked,
      isEquipped: isEquipped ?? this.isEquipped,
      unlockedAt: unlockedAt ?? this.unlockedAt,
    );
  }
}