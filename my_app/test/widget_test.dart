import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:my_app/main.dart';
import 'package:my_app/theme.dart';

/// Signs up a fresh account and lands on the home screen.
Future<void> createAccount(
  WidgetTester tester, {
  String email = 'me@example.com',
  String password = 'supersecret',
}) async {
  await tester.pumpWidget(const MyApp());
  await tester.pumpAndSettle();
  await tester.tap(find.text('New here? Create an account'));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(const Key('email-field')), email);
  await tester.enterText(find.byKey(const Key('password-field')), password);
  await tester.tap(find.text('Create account'));
  await tester.pumpAndSettle();
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('shows the sign-in screen when signed out', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();

    expect(find.text('Welcome back'), findsOneWidget);
    final Size buttonSize =
        tester.getSize(find.widgetWithText(FilledButton, 'Sign in'));
    expect(buttonSize.height, greaterThanOrEqualTo(AppTheme.minTapTarget));
    expect(buttonSize.width, greaterThanOrEqualTo(AppTheme.minTapTarget));
  });

  testWidgets('creating an account signs you in and shows the task list', (WidgetTester tester) async {
    await createAccount(tester);

    expect(find.text('Today'), findsOneWidget);
    expect(find.text('3 things left to do'), findsOneWidget);
    expect(find.text('Signed in as me@example.com'), findsOneWidget);
  });

  testWidgets('rejects a password that is too short', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('New here? Create an account'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('email-field')), 'me@example.com');
    await tester.enterText(find.byKey(const Key('password-field')), 'short');
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();

    expect(find.text('Use at least 8 characters.'), findsOneWidget);
    expect(find.text('Today'), findsNothing);
  });

  testWidgets('wrong password shows a friendly error', (WidgetTester tester) async {
    await createAccount(tester);
    await tester.tap(find.byTooltip('Sign out'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('email-field')), 'me@example.com');
    await tester.enterText(find.byKey(const Key('password-field')), 'wrongpassword');
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();

    expect(find.text("That password doesn't match. Try again."), findsOneWidget);
    expect(find.text('Today'), findsNothing);
  });

  testWidgets('signing back in with the right password works', (WidgetTester tester) async {
    await createAccount(tester);
    await tester.tap(find.byTooltip('Sign out'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('email-field')), 'me@example.com');
    await tester.enterText(find.byKey(const Key('password-field')), 'supersecret');
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();

    expect(find.text('Today'), findsOneWidget);
  });

  testWidgets('signing out returns to the sign-in screen', (WidgetTester tester) async {
    await createAccount(tester);
    await tester.tap(find.byTooltip('Sign out'));
    await tester.pumpAndSettle();

    expect(find.text('Welcome back'), findsOneWidget);
  });

  testWidgets('tapping anywhere on a task card marks it done', (WidgetTester tester) async {
    await createAccount(tester);

    await tester.tap(find.text('Tap a card to mark it done'));
    await tester.pump();

    expect(find.text('2 things left to do'), findsOneWidget);
  });

  testWidgets('Add task button adds a new task', (WidgetTester tester) async {
    await createAccount(tester);

    await tester.tap(find.text('Add task'));
    await tester.pump();

    expect(find.text('New task 1'), findsOneWidget);
    expect(find.text('4 things left to do'), findsOneWidget);
  });
}
