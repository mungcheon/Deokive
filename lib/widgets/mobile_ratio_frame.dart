import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

class MobileRatioFrame extends StatelessWidget {
  final Widget child;

  const MobileRatioFrame({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (kIsWeb) {
          final horizontalPadding = constraints.maxWidth >= 1280
              ? 32.0
              : constraints.maxWidth >= 900
                  ? 24.0
                  : 0.0;

          return Container(
            color: Theme.of(context).scaffoldBackgroundColor,
            alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1440),
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
                child: child,
              ),
            ),
          );
        }

        if (constraints.maxWidth < 700) {
          return child;
        }

        const phoneAspectRatio = 9 / 19.5;
        final frameHeight = constraints.maxHeight;
        final frameWidth = frameHeight * phoneAspectRatio;
        final clampedWidth = frameWidth.clamp(390.0, 460.0);

        return Container(
          color: Theme.of(context).scaffoldBackgroundColor,
          alignment: Alignment.center,
          child: Container(
            width: clampedWidth,
            height: frameHeight,
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: Theme.of(context).scaffoldBackgroundColor,
              border: Border.all(
                color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.45),
              ),
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.08),
                  blurRadius: 24,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: child,
          ),
        );
      },
    );
  }
}
