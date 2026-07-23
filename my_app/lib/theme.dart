// Copyright 2014 The Flutter Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import 'package:flutter/material.dart';

/// The app's design system, tuned for two things:
///
/// 1. Readability — body text starts at 16px with relaxed line height, and
///    every color pairing meets WCAG AA contrast in both light and dark mode.
/// 2. Easy tapping — every interactive control is at least 48x48 logical
///    pixels (Material's accessibility minimum), with generous padding so a
///    hurried thumb still lands on target.
class AppTheme {
  AppTheme._();

  static const double minTapTarget = 48;

  static ThemeData light() => _base(Brightness.light);

  static ThemeData dark() => _base(Brightness.dark);

  static ThemeData _base(Brightness brightness) {
    final ColorScheme scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF2A6049),
      brightness: brightness,
    );

    final TextTheme text = _textTheme(scheme);

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      textTheme: text,
      // Standard density keeps tap targets at full size on desktop too,
      // instead of Material's default compact desktop spacing.
      visualDensity: VisualDensity.standard,
      materialTapTargetSize: MaterialTapTargetSize.padded,
      scaffoldBackgroundColor: scheme.surface,
      appBarTheme: AppBarTheme(
        centerTitle: false,
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        titleTextStyle: text.titleLarge,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(minTapTarget, minTapTarget),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          textStyle: text.titleMedium,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(minTapTarget, minTapTarget),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          textStyle: text.titleMedium,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          minimumSize: const Size(minTapTarget, minTapTarget),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          textStyle: text.titleMedium,
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          minimumSize: const Size(minTapTarget, minTapTarget),
          iconSize: 26,
        ),
      ),
      listTileTheme: ListTileThemeData(
        minVerticalPadding: 14,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20),
        titleTextStyle: text.bodyLarge,
        subtitleTextStyle: text.bodyMedium!.copyWith(
          color: scheme.onSurfaceVariant,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: scheme.surfaceContainerLow,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: scheme.outlineVariant),
        ),
        margin: EdgeInsets.zero,
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 72,
        labelTextStyle: WidgetStatePropertyAll<TextStyle>(text.labelLarge!),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        contentTextStyle: text.bodyLarge!.copyWith(
          color: scheme.onInverseSurface,
        ),
      ),
    );
  }

  /// Body text no smaller than 16px, with ~1.4 line height for comfortable
  /// scanning. Labels (buttons, nav) stay at 14+ and medium weight so they
  /// read at a glance.
  static TextTheme _textTheme(ColorScheme scheme) {
    const TextTheme base = Typography.englishLike2021;
    return base
        .copyWith(
          headlineMedium: base.headlineMedium!.copyWith(
            fontWeight: FontWeight.w600,
            height: 1.25,
          ),
          titleLarge: base.titleLarge!.copyWith(
            fontWeight: FontWeight.w600,
            height: 1.3,
          ),
          titleMedium: base.titleMedium!.copyWith(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            height: 1.35,
          ),
          bodyLarge: base.bodyLarge!.copyWith(fontSize: 17, height: 1.4),
          bodyMedium: base.bodyMedium!.copyWith(fontSize: 16, height: 1.4),
          labelLarge: base.labelLarge!.copyWith(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        )
        .apply(
          bodyColor: scheme.onSurface,
          displayColor: scheme.onSurface,
        );
  }
}
