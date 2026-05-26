import 'package:flutter/material.dart';

/// Tier-based showcase background.
///
/// The user's profile level determines the highest tier they have *unlocked*
/// (one tier per 5 levels, 0..5). Within the unlocked range the user can
/// freely pick any earlier tier as their preferred showcase look.
const int kMaxShowcaseBackgroundTier = 5;

int unlockedShowcaseTier(int profileLevel) =>
    (profileLevel ~/ 5).clamp(0, kMaxShowcaseBackgroundTier);

/// Painter that draws the tier-N decorative background. Tier 0 = blank.
class ShowcaseTierBackgroundPainter extends CustomPainter {
  final int tier; // 0..5
  final Color primary;
  final Color accent;

  ShowcaseTierBackgroundPainter({
    required this.tier,
    required this.primary,
    required this.accent,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (tier <= 0) return;
    final rect = Offset.zero & size;

    final wash = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          primary.withValues(alpha: 0.04 + 0.025 * tier),
          accent.withValues(alpha: 0.04 + 0.025 * tier),
        ],
      ).createShader(rect);
    canvas.drawRect(rect, wash);

    if (tier >= 2) {
      final spotlightY = size.height * 0.58;
      for (var i = 0; i < 3; i++) {
        final cx = size.width * (0.18 + 0.32 * i);
        final paint = Paint()
          ..shader = RadialGradient(
            colors: [
              primary.withValues(alpha: 0.08 + 0.025 * (tier - 1)),
              primary.withValues(alpha: 0.0),
            ],
          ).createShader(
            Rect.fromCircle(center: Offset(cx, spotlightY), radius: 90),
          );
        canvas.drawCircle(Offset(cx, spotlightY), 90, paint);
      }
    }

    if (tier >= 3) {
      final rayPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFFD4A656).withValues(alpha: 0.08),
            Colors.transparent,
          ],
        ).createShader(rect);
      final rays = Path();
      for (var i = -1; i < 6; i++) {
        final x = size.width * i / 4;
        rays.moveTo(x, 0);
        rays.lineTo(x + size.width * 0.07, 0);
        rays.lineTo(x + size.width * 0.035, size.height);
        rays.close();
      }
      canvas.drawPath(rays, rayPaint);
    }

    if (tier >= 4) {
      final sparkle = Paint()
        ..color = Colors.white.withValues(alpha: 0.55);
      const spots = [
        Offset(0.10, 0.20),
        Offset(0.34, 0.14),
        Offset(0.62, 0.18),
        Offset(0.86, 0.26),
        Offset(0.22, 0.84),
        Offset(0.78, 0.82),
      ];
      for (final s in spots) {
        _drawSparkle(
          canvas,
          Offset(size.width * s.dx, size.height * s.dy),
          2.4,
          sparkle,
        );
      }
    }

    if (tier >= 5) {
      final halo = Paint()
        ..shader = RadialGradient(
          center: Alignment.center,
          colors: [
            const Color(0xFFFFD978).withValues(alpha: 0.16),
            Colors.transparent,
          ],
        ).createShader(rect);
      canvas.drawRect(rect, halo);
    }
  }

  void _drawSparkle(Canvas canvas, Offset c, double r, Paint paint) {
    final path = Path()
      ..moveTo(c.dx, c.dy - r * 2)
      ..lineTo(c.dx + r * 0.5, c.dy - r * 0.5)
      ..lineTo(c.dx + r * 2, c.dy)
      ..lineTo(c.dx + r * 0.5, c.dy + r * 0.5)
      ..lineTo(c.dx, c.dy + r * 2)
      ..lineTo(c.dx - r * 0.5, c.dy + r * 0.5)
      ..lineTo(c.dx - r * 2, c.dy)
      ..lineTo(c.dx - r * 0.5, c.dy - r * 0.5)
      ..close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant ShowcaseTierBackgroundPainter old) =>
      old.tier != tier ||
      old.primary != primary ||
      old.accent != accent;
}
