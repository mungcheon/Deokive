import 'package:flutter/material.dart';

/// Tier-based showcase background.
///
/// The user's profile level determines the highest tier they have *unlocked*
/// (one tier per 5 levels, 0..4). Within the unlocked range the user can
/// freely pick any earlier tier as their preferred showcase look.
const int kMaxShowcaseBackgroundTier = 4;

int unlockedShowcaseTier(int profileLevel) =>
    (profileLevel ~/ 5).clamp(0, kMaxShowcaseBackgroundTier);

String showcaseTierLabel(int tier) {
  switch (tier) {
    case 0:
      return '무색';
    case 1:
      return '아이언';
    case 2:
      return '브론즈';
    case 3:
      return '실버';
    case 4:
      return '골드';
    default:
      return '배경';
  }
}

/// Painter that draws the tier-N decorative background.
class ShowcaseTierBackgroundPainter extends CustomPainter {
  final int tier; // -1..4
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
    final style = _rankStyle(tier);

    final base = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          style.backdropTop,
          style.backdropBottom,
        ],
      ).createShader(rect);
    canvas.drawRect(rect, base);

    final vignette = Paint()
      ..shader = RadialGradient(
        center: Alignment.topCenter,
        radius: 1.0,
        colors: [
          style.glow.withValues(alpha: 0.34),
          style.backdropBottom.withValues(alpha: 0.06),
          Colors.black.withValues(alpha: 0.10),
        ],
        stops: const [0, 0.48, 1],
      ).createShader(rect);
    canvas.drawRect(rect, vignette);

    _drawRankBeams(canvas, size, style);
    _drawSideBlades(canvas, size, style);
    _drawCentralCrest(canvas, size, style);
    _drawBadgeShelf(canvas, size, style);

    if (tier >= 3) {
      final sparkle = Paint()
        ..color = style.highlight.withValues(alpha: tier >= 6 ? 0.70 : 0.48);
      const spots = [
        Offset(0.13, 0.26),
        Offset(0.30, 0.18),
        Offset(0.70, 0.18),
        Offset(0.87, 0.27),
        Offset(0.22, 0.78),
        Offset(0.78, 0.78),
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
  }

  void _drawRankBeams(Canvas canvas, Size size, _RankTierStyle style) {
    final center = Offset(size.width / 2, size.height * 0.46);
    final beamPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          style.glow.withValues(alpha: 0.18),
          style.glow.withValues(alpha: 0.04),
          Colors.transparent,
        ],
      ).createShader(
          Rect.fromCircle(center: center, radius: size.width * 0.62));
    canvas.drawCircle(center, size.width * 0.62, beamPaint);

    final linePaint = Paint()
      ..color = style.highlight.withValues(alpha: 0.15)
      ..strokeWidth = 1.1;
    for (var i = 0; i < 7; i++) {
      final x = size.width * (i + 0.5) / 7;
      canvas.drawLine(
        Offset(x, size.height * 0.12),
        Offset(size.width / 2, size.height * 0.88),
        linePaint,
      );
    }
  }

  void _drawSideBlades(Canvas canvas, Size size, _RankTierStyle style) {
    final bladePaint = Paint()..color = style.darkMetal.withValues(alpha: 0.22);
    final edgePaint = Paint()
      ..color = style.highlight.withValues(alpha: 0.26)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;

    for (final side in [-1, 1]) {
      final leftSide = side < 0;
      final x0 = leftSide ? 0.0 : size.width;
      final path = Path()
        ..moveTo(x0, size.height * 0.18)
        ..lineTo(x0 + side * size.width * -0.16, size.height * 0.05)
        ..lineTo(x0 + side * size.width * -0.27, size.height * 0.46)
        ..lineTo(x0 + side * size.width * -0.12, size.height * 0.92)
        ..lineTo(x0, size.height * 0.76)
        ..close();
      canvas.drawPath(path, bladePaint);
      canvas.drawPath(path, edgePaint);

      if (style.tier >= 4) {
        final wingPaint = Paint()..color = style.accent.withValues(alpha: 0.20);
        for (var i = 0; i < 3; i++) {
          final y = size.height * (0.30 + i * 0.16);
          final feather = Path()
            ..moveTo(x0, y)
            ..quadraticBezierTo(
              x0 + side * size.width * -0.20,
              y + size.height * 0.02,
              x0 + side * size.width * -0.30,
              y + size.height * 0.10,
            )
            ..quadraticBezierTo(
              x0 + side * size.width * -0.12,
              y + size.height * 0.09,
              x0,
              y + size.height * 0.15,
            )
            ..close();
          canvas.drawPath(feather, wingPaint);
        }
      }
    }
  }

  void _drawCentralCrest(Canvas canvas, Size size, _RankTierStyle style) {
    final centerX = size.width / 2;
    final top = size.height * 0.12;
    final width = size.width * (0.30 + style.tier * 0.012);
    final height = size.height * 0.56;

    final shadow = Paint()
      ..color = Colors.black.withValues(alpha: 0.16)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10);
    final shadowPath = _crestPath(centerX, top + 5, width, height);
    canvas.drawPath(shadowPath, shadow);

    final crestPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          style.highlight.withValues(alpha: 0.90),
          style.accent.withValues(alpha: 0.72),
          style.darkMetal.withValues(alpha: 0.88),
        ],
        stops: const [0, 0.56, 1],
      ).createShader(Rect.fromLTWH(centerX - width, top, width * 2, height));
    final crest = _crestPath(centerX, top, width, height);
    canvas.drawPath(crest, crestPaint);

    final outline = Paint()
      ..color = style.highlight.withValues(alpha: 0.80)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8;
    canvas.drawPath(crest, outline);

    final inner = _crestPath(centerX, top + 10, width * 0.62, height * 0.62);
    canvas.drawPath(
      inner,
      Paint()
        ..color = Colors.white.withValues(alpha: 0.10)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2,
    );
  }

  Path _crestPath(double centerX, double top, double width, double height) {
    return Path()
      ..moveTo(centerX, top)
      ..lineTo(centerX + width * 0.82, top + height * 0.18)
      ..lineTo(centerX + width * 0.64, top + height * 0.66)
      ..lineTo(centerX, top + height)
      ..lineTo(centerX - width * 0.64, top + height * 0.66)
      ..lineTo(centerX - width * 0.82, top + height * 0.18)
      ..close();
  }

  void _drawBadgeShelf(Canvas canvas, Size size, _RankTierStyle style) {
    final shelfRect = Rect.fromLTWH(
      size.width * 0.12,
      size.height * 0.66,
      size.width * 0.76,
      size.height * 0.13,
    );
    final shelfPaint = Paint()
      ..shader = LinearGradient(
        colors: [
          style.darkMetal.withValues(alpha: 0.12),
          style.highlight.withValues(alpha: 0.34),
          style.darkMetal.withValues(alpha: 0.12),
        ],
      ).createShader(shelfRect);
    canvas.drawRRect(
      RRect.fromRectAndRadius(shelfRect, const Radius.circular(999)),
      shelfPaint,
    );

    final line = Paint()
      ..color = style.highlight.withValues(alpha: 0.50)
      ..strokeWidth = 1.4;
    canvas.drawLine(
      Offset(shelfRect.left + 8, shelfRect.center.dy),
      Offset(shelfRect.right - 8, shelfRect.center.dy),
      line,
    );
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
      old.tier != tier || old.primary != primary || old.accent != accent;
}

class _RankTierStyle {
  final int tier;
  final Color backdropTop;
  final Color backdropBottom;
  final Color darkMetal;
  final Color accent;
  final Color highlight;
  final Color glow;

  const _RankTierStyle({
    required this.tier,
    required this.backdropTop,
    required this.backdropBottom,
    required this.darkMetal,
    required this.accent,
    required this.highlight,
    required this.glow,
  });
}

_RankTierStyle _rankStyle(int tier) {
  const styles = [
    _RankTierStyle(
      tier: 0,
      backdropTop: Color(0xFFF7F8FA),
      backdropBottom: Color(0xFFE8EBEF),
      darkMetal: Color(0xFF9AA1AA),
      accent: Color(0xFFCDD3DA),
      highlight: Color(0xFFFFFFFF),
      glow: Color(0xFFE9EEF4),
    ),
    _RankTierStyle(
      tier: 1,
      backdropTop: Color(0xFFE8EBEF),
      backdropBottom: Color(0xFF8D949B),
      darkMetal: Color(0xFF444A50),
      accent: Color(0xFF6F7780),
      highlight: Color(0xFFC8CED5),
      glow: Color(0xFF9CA5AF),
    ),
    _RankTierStyle(
      tier: 2,
      backdropTop: Color(0xFFFFE8D1),
      backdropBottom: Color(0xFFD09A6A),
      darkMetal: Color(0xFF6B3F26),
      accent: Color(0xFFC17B42),
      highlight: Color(0xFFFFD0A0),
      glow: Color(0xFFFFAA68),
    ),
    _RankTierStyle(
      tier: 3,
      backdropTop: Color(0xFFF7FAFC),
      backdropBottom: Color(0xFFB9C4CF),
      darkMetal: Color(0xFF5B6670),
      accent: Color(0xFFCBD5DF),
      highlight: Color(0xFFFFFFFF),
      glow: Color(0xFFDCE8F3),
    ),
    _RankTierStyle(
      tier: 4,
      backdropTop: Color(0xFFFFF2B8),
      backdropBottom: Color(0xFFE0AE3C),
      darkMetal: Color(0xFF725314),
      accent: Color(0xFFE3B94A),
      highlight: Color(0xFFFFF1A6),
      glow: Color(0xFFFFD85C),
    ),
  ];
  return styles[tier.clamp(0, kMaxShowcaseBackgroundTier)];
}
