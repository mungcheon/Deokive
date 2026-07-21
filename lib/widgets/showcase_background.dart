import 'package:flutter/material.dart';

/// Tier-based showcase background.
///
/// The user's profile level determines the highest tier they have *unlocked*
/// (one tier per 5 levels, 0..7). Within the unlocked range the user can
/// freely pick any earlier tier as their preferred showcase look.
const int kMaxShowcaseBackgroundTier = 7;

int unlockedShowcaseTier(int profileLevel) =>
    (profileLevel ~/ 5).clamp(0, kMaxShowcaseBackgroundTier);

String showcaseTierLabel(int tier) {
  switch (tier) {
    case 0:
      return '흙';
    case 1:
      return '종이';
    case 2:
      return '돌';
    case 3:
      return '시멘트';
    case 4:
      return '벽돌';
    case 5:
      return '은';
    case 6:
      return '금';
    case 7:
      return '다이아';
    default:
      return '배경';
  }
}

/// Painter that draws the tier-N decorative background.
class ShowcaseTierBackgroundPainter extends CustomPainter {
  final int tier; // -1..7
  final Color primary;
  final Color accent;

  ShowcaseTierBackgroundPainter({
    required this.tier,
    required this.primary,
    required this.accent,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (tier < 0) return;
    final rect = Offset.zero & size;

    if (tier == 0) {
      final soil = Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFFD8B08C),
            Color(0xFFB7865E),
          ],
        ).createShader(rect);
      canvas.drawRect(rect, soil);
      return;
    }

    if (tier == 1) {
      final paper = Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFFF7F0DE),
            Color(0xFFE8DDC2),
          ],
        ).createShader(rect);
      canvas.drawRect(rect, paper);
      final linePaint = Paint()
        ..color = const Color(0xFFD8CBAE).withValues(alpha: 0.7)
        ..strokeWidth = 1;
      for (double y = 14; y < size.height; y += 14) {
        canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);
      }
      return;
    }

    final wash = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          primary.withValues(alpha: 0.04 + 0.015 * tier),
          accent.withValues(alpha: 0.04 + 0.015 * tier),
        ],
      ).createShader(rect);
    canvas.drawRect(rect, wash);

    if (tier >= 2) {
      final pebble = Paint()
        ..color = const Color(0xFF7D8491).withValues(alpha: 0.10);
      for (var i = 0; i < 18; i++) {
        final dx = size.width * ((i * 37) % 100) / 100;
        final dy = size.height * ((i * 23 + 17) % 100) / 100;
        canvas.drawCircle(Offset(dx, dy), 8 + (i % 3).toDouble(), pebble);
      }
    }

    if (tier >= 3) {
      final cement = Paint()
        ..color = const Color(0xFFB8BEC6).withValues(alpha: 0.16)
        ..strokeWidth = 1.2;
      for (var i = 0; i < 8; i++) {
        final y = size.height * i / 7;
        canvas.drawLine(Offset(0, y), Offset(size.width, y + 6), cement);
      }
    }

    if (tier >= 4) {
      final brickPaint = Paint()
        ..color = const Color(0xFFA8553E).withValues(alpha: 0.16);
      const brickH = 22.0;
      const brickW = 44.0;
      for (double y = 0; y < size.height + brickH; y += brickH) {
        final offset = ((y / brickH).round().isEven) ? 0.0 : brickW / 2;
        for (double x = -brickW; x < size.width + brickW; x += brickW) {
          canvas.drawRect(
            Rect.fromLTWH(x + offset, y, brickW - 2, brickH - 2),
            brickPaint,
          );
        }
      }
    }

    if (tier >= 5) {
      final spotlightY = size.height * 0.58;
      for (var i = 0; i < 3; i++) {
        final cx = size.width * (0.18 + 0.32 * i);
        final paint = Paint()
          ..shader = RadialGradient(
            colors: [
              const Color(0xFFE8EDF4).withValues(alpha: 0.18),
              primary.withValues(alpha: 0.0),
            ],
          ).createShader(
            Rect.fromCircle(center: Offset(cx, spotlightY), radius: 90),
          );
        canvas.drawCircle(Offset(cx, spotlightY), 90, paint);
      }
    }

    if (tier >= 6) {
      final rayPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFFFFD978).withValues(alpha: 0.15),
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

    if (tier >= 6) {
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

    if (tier >= 7) {
      final halo = Paint()
        ..shader = RadialGradient(
          center: Alignment.center,
          colors: [
            const Color(0xFFBEEBFF).withValues(alpha: 0.26),
            const Color(0xFFE8F7FF).withValues(alpha: 0.12),
            Colors.transparent,
          ],
        ).createShader(rect);
      canvas.drawRect(rect, halo);
      final gem = Paint()
        ..color = const Color(0xFFEBFAFF).withValues(alpha: 0.55);
      const gemSpots = [
        Offset(0.16, 0.18),
        Offset(0.52, 0.12),
        Offset(0.84, 0.22),
        Offset(0.24, 0.76),
        Offset(0.68, 0.82),
      ];
      for (final s in gemSpots) {
        _drawSparkle(
          canvas,
          Offset(size.width * s.dx, size.height * s.dy),
          3.2,
          gem,
        );
      }
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
