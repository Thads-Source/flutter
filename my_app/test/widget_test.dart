import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:my_app/main.dart';
import 'package:my_app/theme.dart';

void main() {
  testWidgets('home screen renders with readable header', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.text('Today'), findsOneWidget);
    expect(find.text('3 things left to do'), findsOneWidget);
  });

  testWidgets('primary action meets the 48px minimum tap target', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    final Size buttonSize = tester.getSize(find.widgetWithText(FilledButton, 'Add task'));
    expect(buttonSize.height, greaterThanOrEqualTo(AppTheme.minTapTarget));
    expect(buttonSize.width, greaterThanOrEqualTo(AppTheme.minTapTarget));
  });

  testWidgets('tapping anywhere on a task card marks it done', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('Tap a card to mark it done'));
    await tester.pump();

    expect(find.text('2 things left to do'), findsOneWidget);
  });

  testWidgets('Add task button adds a new task', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('Add task'));
    await tester.pump();

    expect(find.text('New task 1'), findsOneWidget);
    expect(find.text('4 things left to do'), findsOneWidget);
  });
}
