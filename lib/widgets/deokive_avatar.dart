import 'package:flutter/material.dart';

import '../theme/deokive_palette.dart';

const List<Color> deokiveAvatarHairColors = [
  Color(0xFF5A4A42),
  Color(0xFF3B4252),
  Color(0xFF7A5C45),
  Color(0xFF4D5678),
  Color(0xFFB54C72),
  Color(0xFF7AC7D9),
];

const List<Color> deokiveAvatarAccentColors = [
  Color(0xFFF3D9A4),
  Color(0xFFEED7F7),
  Color(0xFFA7E4D7),
  Color(0xFFF8C3D0),
];

const List<Color> deokiveAvatarSkinColors = [
  Color(0xFFFFFFFF),
  Color(0xFFFFF4EA),
  Color(0xFFFFE8D6),
  Color(0xFFD8A57A),
  Color(0xFF8A5A44),
  Color(0xFFBFD9FF),
  Color(0xFFD6C3FF),
  Color(0xFFFFD6E5),
];

List<Color> deokiveAvatarOutfitColors(DeokivePalette palette) => [
      palette.primary,
      palette.accent,
      const Color(0xFF89A8B2),
      const Color(0xFFC689C6),
      const Color(0xFF94C973),
      const Color(0xFFE9A95E),
    ];

const String deokiveAvatarUnsetAsset = 'assets/avatar/body/미설정.png';

const List<String> deokiveAvatarBodyAssets = [
  'assets/avatar/body/남자 몸.png',
  'assets/avatar/body/여자 몸.png',
];

const List<String> deokiveAvatarBodyLabels = [
  '남자 몸',
  '여자 몸',
];

const List<String> deokiveAvatarHairAssets = [
  'assets/avatar/hair/초코송이 단발.png',
];

const List<String> deokiveAvatarHairLabels = [
  '초코송이 단발',
];

const List<String> deokiveAvatarOutfitLabels = [
  '의상 1',
  '의상 2',
  '의상 3',
  '의상 4',
  '의상 5',
  '의상 6',
];

const List<String> deokiveAvatarAccessoryAssets = [
  'assets/avatar/accessory/루돌프 머리띠.png',
  'assets/avatar/accessory/루돌프 사슴코.png',
  'assets/avatar/accessory/가방.png',
  'assets/avatar/accessory/빨간리본.png',
];

const List<String> deokiveAvatarAccessoryLabels = [
  '루돌프 머리띠',
  '루돌프 사슴코',
  '가방',
  '빨간 리본',
];

const List<String> deokiveAvatarBackgroundAssets = [
  'assets/avatar/background/bg1.png',
  'assets/avatar/background/bg2.png',
  'assets/avatar/background/bg3.png',
  'assets/avatar/background/bg4.png',
  'assets/avatar/background/bg5.png',
  'assets/avatar/background/bg6.png',
];

const List<String> deokiveAvatarBackgroundLabels = [
  '배경 1',
  '배경 2',
  '배경 3',
  '배경 4',
  '배경 5',
  '배경 6',
];

class DeokiveAvatar extends StatelessWidget {
  final DeokivePalette palette;
  final EdgeInsetsGeometry padding;
  final int bodyType;
  final int backgroundType;
  final int hairStyle;
  final int hairColorIndex;
  final int accentColorIndex;
  final int outfitColorIndex;
  final int skinToneIndex;
  final bool hasHat;
  final bool hasCape;
  final bool hasHandheld;
  final bool hasBackRibbon;

  const DeokiveAvatar({
    super.key,
    required this.palette,
    this.padding = const EdgeInsets.fromLTRB(20, 88, 20, 0),
    required this.bodyType,
    required this.backgroundType,
    required this.hairStyle,
    required this.hairColorIndex,
    required this.accentColorIndex,
    required this.outfitColorIndex,
    required this.skinToneIndex,
    required this.hasHat,
    required this.hasCape,
    required this.hasHandheld,
    required this.hasBackRibbon,
  });

  @override
  Widget build(BuildContext context) {
    final bodyAsset = bodyType >= 0 && bodyType < deokiveAvatarBodyAssets.length
        ? deokiveAvatarBodyAssets[bodyType]
        : deokiveAvatarUnsetAsset;
    final hairAsset =
        hairStyle >= 0 && hairStyle < deokiveAvatarHairAssets.length
            ? deokiveAvatarHairAssets[hairStyle]
            : null;
    final skinColor =
        skinToneIndex >= 0 && skinToneIndex < deokiveAvatarSkinColors.length
            ? deokiveAvatarSkinColors[skinToneIndex]
            : deokiveAvatarSkinColors[1];
    final hairColor =
        hairColorIndex >= 0 && hairColorIndex < deokiveAvatarHairColors.length
            ? deokiveAvatarHairColors[hairColorIndex]
            : null;
    final accentColor = accentColorIndex >= 0 &&
            accentColorIndex < deokiveAvatarAccentColors.length
        ? deokiveAvatarAccentColors[accentColorIndex]
        : palette.accent;
    final outfitColors = deokiveAvatarOutfitColors(palette);
    final outfitColor =
        outfitColorIndex >= 0 && outfitColorIndex < outfitColors.length
            ? outfitColors[outfitColorIndex]
            : palette.primary;

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: Stack(
        fit: StackFit.expand,
        children: [
          _AvatarBackground(backgroundType: backgroundType),
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0, -0.4),
                  radius: 1.1,
                  colors: [
                    Colors.white.withValues(alpha: 0.14),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: Padding(
              padding: padding,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  _BodyLayer(
                    assetPath: bodyAsset,
                    skinColor: bodyType >= 0 ? skinColor : null,
                    outfitColor: bodyType >= 0 ? outfitColor : null,
                  ),
                  if (hairAsset != null)
                    _AssetLayer(
                      assetPath: hairAsset,
                      tintColor: hairColor,
                    ),
                  if (hasHat)
                    _AssetLayer(
                      assetPath: deokiveAvatarAccessoryAssets[0],
                      tintColor: accentColor,
                    ),
                  if (hasCape)
                    _AssetLayer(
                      assetPath: deokiveAvatarAccessoryAssets[1],
                      tintColor: accentColor,
                    ),
                  if (hasHandheld)
                    _AssetLayer(
                      assetPath: deokiveAvatarAccessoryAssets[2],
                      tintColor: accentColor,
                    ),
                  if (hasBackRibbon)
                    _AssetLayer(
                      assetPath: deokiveAvatarAccessoryAssets[3],
                      tintColor: accentColor,
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BodyLayer extends StatelessWidget {
  final String assetPath;
  final Color? skinColor;
  final Color? outfitColor;

  const _BodyLayer({
    required this.assetPath,
    required this.skinColor,
    required this.outfitColor,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Image.asset(
          assetPath,
          fit: BoxFit.contain,
          alignment: Alignment.bottomCenter,
          errorBuilder: (context, error, stackTrace) {
            return const SizedBox.shrink();
          },
        ),
        if (outfitColor != null)
          ColorFiltered(
            colorFilter: ColorFilter.mode(
              outfitColor!.withValues(alpha: 0.18),
              BlendMode.modulate,
            ),
            child: Image.asset(
              assetPath,
              fit: BoxFit.contain,
              alignment: Alignment.bottomCenter,
              errorBuilder: (context, error, stackTrace) {
                return const SizedBox.shrink();
              },
            ),
          ),
        if (skinColor != null)
          ColorFiltered(
            colorFilter: ColorFilter.mode(
              skinColor!.withValues(alpha: 0.36),
              BlendMode.softLight,
            ),
            child: Image.asset(
              assetPath,
              fit: BoxFit.contain,
              alignment: Alignment.bottomCenter,
              errorBuilder: (context, error, stackTrace) {
                return const SizedBox.shrink();
              },
            ),
          ),
      ],
    );
  }
}

class _AssetLayer extends StatelessWidget {
  final String assetPath;
  final Color? tintColor;

  const _AssetLayer({
    required this.assetPath,
    this.tintColor,
  });

  @override
  Widget build(BuildContext context) {
    return ColorFiltered(
      colorFilter: ColorFilter.mode(
        tintColor?.withValues(alpha: 0.22) ?? Colors.transparent,
        BlendMode.modulate,
      ),
      child: Image.asset(
        assetPath,
        fit: BoxFit.contain,
        alignment: Alignment.bottomCenter,
        errorBuilder: (context, error, stackTrace) {
          return const SizedBox.shrink();
        },
      ),
    );
  }
}

class _AvatarBackground extends StatelessWidget {
  final int backgroundType;

  const _AvatarBackground({
    required this.backgroundType,
  });

  @override
  Widget build(BuildContext context) {
    if (backgroundType < 0 ||
        backgroundType >= deokiveAvatarBackgroundAssets.length) {
      return const SizedBox.shrink();
    }

    return Image.asset(
      deokiveAvatarBackgroundAssets[backgroundType],
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) {
        return const SizedBox.shrink();
      },
    );
  }
}
