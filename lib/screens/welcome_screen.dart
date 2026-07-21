import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/deokive_palette.dart';

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
  bool _starting = false;

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

  Future<void> _start(BuildContext context) async {
    if (_starting) return;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _starting = true);
    final ok = await context.read<AppState>().startWithAutoNickname();
    if (!mounted) return;
    setState(() => _starting = false);
    if (!ok) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('시작에 실패했어요. 잠시 후 다시 시도해 주세요.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final pinkSpec = paletteSpecFor(AppPalette.zeroTwoPink);
    final pinkPrimary = pinkSpec.primary;
    final pinkBackground = pinkSpec.background;
    final pinkDeep = Color.lerp(pinkPrimary, Colors.black, 0.25)!;

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
              child: LayoutBuilder(
                builder: (context, constraints) {
                  return SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 28,
                      vertical: 24,
                    ),
                    child: ConstrainedBox(
                      constraints: BoxConstraints(
                        minHeight: constraints.maxHeight - 48,
                      ),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 430),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
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
                                'Deokive',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 34,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 2,
                                  color: pinkDeep,
                                  shadows: [
                                    Shadow(
                                      color:
                                          pinkPrimary.withValues(alpha: 0.30),
                                      blurRadius: 8,
                                      offset: const Offset(0, 2),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                '좋아하는 굿즈를 차곡차곡 기록해요',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 0.6,
                                  color: pinkDeep.withValues(alpha: 0.70),
                                ),
                              ),
                              const SizedBox(height: 12),
                              _AboutCard(
                                primary: pinkPrimary,
                                deep: pinkDeep,
                              ),
                              const SizedBox(height: 20),
                              FilledButton(
                                onPressed:
                                    _starting ? null : () => _start(context),
                                style: FilledButton.styleFrom(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 14),
                                  backgroundColor: pinkPrimary,
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                ),
                                child: _starting
                                    ? const SizedBox(
                                        width: 20,
                                        height: 20,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: Colors.white,
                                        ),
                                      )
                                    : const Text(
                                        '시작하기',
                                        style: TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                              ),
                              const SizedBox(height: 10),
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                },
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
                '좋아하는 모든 순간을 기록해요',
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
            '굿즈를 정리하고, 컬렉션의 즐거움까지 게시판에서 함께 나누는 나만의 굿즈 아카이브예요.',
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
      const _StarPos(0.12, 0.16, 1.0),
      const _StarPos(0.84, 0.12, 0.8),
      const _StarPos(0.18, 0.80, 1.2),
      const _StarPos(0.90, 0.74, 1.1),
      const _StarPos(0.54, 0.10, 0.9),
      const _StarPos(0.66, 0.88, 1.0),
    ];
    for (var i = 0; i < stars.length; i++) {
      final star = stars[i];
      final phase = (progress + i * 0.13) % 1.0;
      final alpha = (0.25 + (0.75 * (0.5 + 0.5 * (1 - (phase * 2 - 1).abs()))))
          .clamp(0.0, 1.0);
      final paint = Paint()
        ..color = color.withValues(alpha: alpha * 0.28)
        ..style = PaintingStyle.fill;
      final center = Offset(size.width * star.dx, size.height * star.dy);
      canvas.drawCircle(center, 6 * star.scale, paint);
      canvas.drawCircle(
        center,
        2.2 * star.scale,
        Paint()..color = Colors.white.withValues(alpha: alpha * 0.9),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _SparklePainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.color != color;
  }
}

class _StarPos {
  final double dx;
  final double dy;
  final double scale;

  const _StarPos(this.dx, this.dy, this.scale);
}
