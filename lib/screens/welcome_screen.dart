import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import 'auth_screen.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen>
    with TickerProviderStateMixin {
  late final AnimationController _bounceController;
  late final Animation<double> _bounceAnim;
  late final AnimationController _sparkleController;

  @override
  void initState() {
    super.initState();
    _bounceController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat(reverse: true);
    _bounceAnim = Tween<double>(begin: 0.96, end: 1.06).animate(
      CurvedAnimation(parent: _bounceController, curve: Curves.easeInOut),
    );
    _sparkleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 6),
    )..repeat();
  }

  @override
  void dispose() {
    _bounceController.dispose();
    _sparkleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pinkSpec = paletteSpecFor(AppPalette.cherryBlossom);
    final pinkPrimary = pinkSpec.primary;
    final pinkBackground = pinkSpec.background;
    final pinkDeep = Color.lerp(pinkPrimary, Colors.black, 0.25)!;

    final appState = context.watch<AppState>();

    return Theme(
      data: Theme.of(context).copyWith(
        scaffoldBackgroundColor: pinkBackground,
      ),
      child: Scaffold(
        backgroundColor: pinkBackground,
        body: Stack(
          children: [
            Positioned.fill(
              child: AnimatedBuilder(
                animation: _sparkleController,
                builder: (context, _) => CustomPaint(
                  painter: _SparklePainter(
                    progress: _sparkleController.value,
                    color: pinkPrimary,
                  ),
                ),
              ),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 28),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Spacer(flex: 3),
                    Center(
                      child: ScaleTransition(
                        scale: _bounceAnim,
                        child: Image.asset(
                          'lib/logo.png',
                          height: 140,
                          color: pinkPrimary,
                          colorBlendMode: BlendMode.srcIn,
                        ),
                      ),
                    ),
                    const SizedBox(height: 18),
                    Text(
                      '덕카이브',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 34,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2,
                        color: pinkDeep,
                        shadows: [
                          Shadow(
                            color: pinkPrimary.withValues(alpha: 0.30),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '내 손 안의 굿즈 컬렉션',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.6,
                        color: pinkDeep.withValues(alpha: 0.70),
                      ),
                    ),
                    const SizedBox(height: 22),
                    _AboutCard(primary: pinkPrimary, deep: pinkDeep),
                    const Spacer(flex: 3),
                    FilledButton(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const AuthScreen(),
                          ),
                        );
                      },
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        backgroundColor: pinkPrimary,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      child: const Text(
                        '로그인 / 회원가입',
                        style:
                            TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                      ),
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton(
                      onPressed: appState.supportsGoogleSignIn
                          ? () async {
                              final success = await appState.signInWithGoogle();
                              if (!context.mounted || success) return;
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(appState.googleSignInMessage),
                                ),
                              );
                            }
                          : null,
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        foregroundColor: pinkPrimary,
                        side: BorderSide(
                            color: pinkPrimary.withValues(alpha: 0.45)),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      child: const Text(
                        '구글로 로그인',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w800),
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextButton(
                      onPressed: appState.enterGuestSession,
                      style: TextButton.styleFrom(
                        foregroundColor: pinkPrimary.withValues(alpha: 0.75),
                      ),
                      child: const Text(
                        '게스트로 둘러보기',
                        style: TextStyle(
                            fontSize: 13.5, fontWeight: FontWeight.w700),
                      ),
                    ),
                    const SizedBox(height: 10),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AboutCard extends StatelessWidget {
  final Color primary;
  final Color deep;
  const _AboutCard({required this.primary, required this.deep});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.65),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: primary.withValues(alpha: 0.25), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: primary.withValues(alpha: 0.10),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome_rounded, size: 16, color: primary),
              const SizedBox(width: 6),
              Text(
                '덕질의 모든 순간을 기록하다',
                style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w800,
                  color: deep,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '폴더로 정리하고, 캘린더로 발매일을 챙기고, '
            '통계로 컬렉션을 돌아보세요. '
            '나만의 아바타와 전시대로 다른 덕메들에게 자랑할 수 있어요.',
            style: TextStyle(
              fontSize: 12,
              height: 1.55,
              color: deep.withValues(alpha: 0.85),
            ),
          ),
        ],
      ),
    );
  }
}

class _SparklePainter extends CustomPainter {
  final double progress;
  final Color color;
  _SparklePainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final stars = <_StarPos>[
      _StarPos(0.10, 0.08, 4, 0.0),
      _StarPos(0.85, 0.12, 5, 0.15),
      _StarPos(0.18, 0.42, 3, 0.30),
      _StarPos(0.78, 0.55, 4, 0.45),
      _StarPos(0.08, 0.78, 5, 0.60),
      _StarPos(0.92, 0.82, 3, 0.75),
      _StarPos(0.50, 0.06, 3, 0.20),
      _StarPos(0.55, 0.95, 4, 0.55),
      _StarPos(0.30, 0.92, 3, 0.85),
    ];
    final paint = Paint()..style = PaintingStyle.fill;
    for (final s in stars) {
      final phase = (progress + s.phase) % 1.0;
      final twinkle =
          (0.45 + 0.55 * (1 - (phase - 0.5).abs() * 2)).clamp(0.0, 1.0);
      paint.color = color.withValues(alpha: 0.18 * twinkle);
      final cx = size.width * s.x;
      final cy = size.height * s.y;
      _drawStar(canvas, Offset(cx, cy), s.radius.toDouble() + 1.5 * twinkle, paint);
    }
  }

  void _drawStar(Canvas canvas, Offset c, double r, Paint p) {
    canvas.drawCircle(c, r * 0.8, p);
    final p2 = Paint()
      ..color = p.color
      ..strokeWidth = r * 0.55
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    canvas.drawLine(Offset(c.dx - r * 2, c.dy), Offset(c.dx + r * 2, c.dy), p2);
    canvas.drawLine(Offset(c.dx, c.dy - r * 2), Offset(c.dx, c.dy + r * 2), p2);
  }

  @override
  bool shouldRepaint(covariant _SparklePainter old) =>
      old.progress != progress || old.color != color;
}

class _StarPos {
  final double x;
  final double y;
  final int radius;
  final double phase;
  const _StarPos(this.x, this.y, this.radius, this.phase);
}
