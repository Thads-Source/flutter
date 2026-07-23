import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:my_app/main.dart';
import 'package:my_app/theme.dart';

/// Signs up a fresh account with the given role and lands on the inventory.
Future<void> createAccount(
  WidgetTester tester, {
  String email = 'me@example.com',
  String password = 'supersecret',
  String role = 'Owner',
}) async {
  await tester.pumpWidget(const MyApp());
  await tester.pumpAndSettle();
  await tester.tap(find.text('New here? Create an account'));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(const Key('email-field')), email);
  await tester.enterText(find.byKey(const Key('password-field')), password);
  await tester.tap(find.text(role));
  await tester.pumpAndSettle();
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

  testWidgets('owner sees inventory, overview tab, and add button', (WidgetTester tester) async {
    await createAccount(tester);

    expect(find.text('Inventory'), findsWidgets);
    expect(find.text('Chicken breast'), findsOneWidget);
    expect(find.text('Overview'), findsOneWidget);
    expect(find.text('Add item'), findsOneWidget);
    expect(find.text('Signed in as me@example.com · Owner'), findsOneWidget);
  });

  testWidgets('kitchen staff cannot add items or open the overview', (WidgetTester tester) async {
    await createAccount(tester, role: 'Kitchen');

    expect(find.text('Chicken breast'), findsOneWidget);
    expect(find.text('Add item'), findsNothing);
    expect(find.text('Overview'), findsNothing);
  });

  testWidgets('items running low show a Low badge', (WidgetTester tester) async {
    await createAccount(tester);

    // Seed data has three items running low: ground beef, onions, butter.
    expect(find.text('Low'), findsNWidgets(3));
    expect(find.text('3 items running low'), findsOneWidget);
  });

  testWidgets('plus button increments a count and persists it', (WidgetTester tester) async {
    await createAccount(tester);

    Finder inButterCard(String value) => find.descendant(
          of: find.byKey(const Key('item-butter')),
          matching: find.text(value),
        );

    await tester.ensureVisible(find.byKey(const Key('inc-butter')));
    expect(inButterCard('2'), findsOneWidget);
    await tester.tap(find.byKey(const Key('inc-butter')));
    await tester.pump();
    expect(inButterCard('3'), findsOneWidget);
  });

  testWidgets('overview lists everything running low as a shopping list', (WidgetTester tester) async {
    await createAccount(tester);

    await tester.tap(find.text('Overview'));
    await tester.pumpAndSettle();

    expect(find.text('Shopping list'), findsOneWidget);
    expect(find.text('Running low'), findsOneWidget);
    expect(find.text('Ground beef'), findsOneWidget);
    expect(find.text('Onions'), findsOneWidget);
    expect(find.text('Butter'), findsOneWidget);
  });

  testWidgets('owner can add a new item', (WidgetTester tester) async {
    await createAccount(tester);

    await tester.tap(find.text('Add item'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('name-field')), 'Lemons');
    await tester.enterText(find.byKey(const Key('qty-field')), '10');
    await tester.enterText(find.byKey(const Key('par-field')), '4');
    await tester.tap(find.byKey(const Key('sheet-save')));
    await tester.pumpAndSettle();

    expect(find.text('Lemons'), findsOneWidget);
  });

  testWidgets('kitchen staff can set an exact count from the sheet', (WidgetTester tester) async {
    await createAccount(tester, role: 'Kitchen');

    await tester.tap(find.text('Tomatoes'));
    await tester.pumpAndSettle();
    expect(find.text('Update count'), findsOneWidget);
    expect(find.byKey(const Key('name-field')), findsNothing);
    await tester.enterText(find.byKey(const Key('qty-field')), '12');
    await tester.tap(find.byKey(const Key('sheet-save')));
    await tester.pumpAndSettle();

    expect(
      find.descendant(
        of: find.byKey(const Key('item-tomatoes')),
        matching: find.text('12'),
      ),
      findsOneWidget,
    );
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
  });

  testWidgets('signing out returns to the sign-in screen', (WidgetTester tester) async {
    await createAccount(tester);
    await tester.tap(find.byTooltip('Sign out'));
    await tester.pumpAndSettle();

    expect(find.text('Welcome back'), findsOneWidget);
  });
}
