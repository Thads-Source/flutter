import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:my_app/main.dart';
import 'package:my_app/theme.dart';

/// From the sign-in screen, creates an account with the given role.
Future<void> signUpFromLogin(
  WidgetTester tester, {
  required String email,
  String password = 'supersecret',
  String role = 'Owner',
}) async {
  await tester.tap(find.text('New here? Create an account'));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(const Key('email-field')), email);
  await tester.enterText(find.byKey(const Key('password-field')), password);
  await tester.tap(find.text(role));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Create account'));
  await tester.pumpAndSettle();
}

/// Launches the app and signs up a fresh account, landing on the inventory.
Future<void> createAccount(
  WidgetTester tester, {
  String email = 'me@example.com',
  String password = 'supersecret',
  String role = 'Owner',
}) async {
  await tester.pumpWidget(const MyApp());
  await tester.pumpAndSettle();
  await signUpFromLogin(tester, email: email, password: password, role: role);
}

Future<void> signOut(WidgetTester tester) async {
  await tester.tap(find.byTooltip('Sign out'));
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

  testWidgets('signing up shows inventory, overview, history, and add button', (WidgetTester tester) async {
    await createAccount(tester);

    expect(find.text('Inventory'), findsWidgets);
    expect(find.text('Chicken breast'), findsOneWidget);
    expect(find.text('Overview'), findsOneWidget);
    expect(find.text('History'), findsOneWidget);
    expect(find.text('Add item'), findsOneWidget);
    expect(find.text('Signed in as me@example.com · Owner'), findsOneWidget);
  });

  testWidgets('only one owner account is allowed', (WidgetTester tester) async {
    await createAccount(tester, email: 'owner@example.com');
    await signOut(tester);

    await signUpFromLogin(tester, email: 'second-owner@example.com');

    expect(find.text('This app already has an owner account.'), findsOneWidget);
  });

  testWidgets('manager accounts are capped at three', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();
    for (int i = 1; i <= 3; i++) {
      await signUpFromLogin(
        tester,
        email: 'manager$i@example.com',
        role: 'Manager',
      );
      expect(find.text('Chicken breast'), findsOneWidget);
      await signOut(tester);
    }

    await signUpFromLogin(tester, email: 'manager4@example.com', role: 'Manager');

    expect(find.text('All three manager spots are taken.'), findsOneWidget);
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

  testWidgets('counting stamps the item with who and when', (WidgetTester tester) async {
    await createAccount(tester);

    await tester.ensureVisible(find.byKey(const Key('inc-butter')));
    await tester.tap(find.byKey(const Key('inc-butter')));
    await tester.pump();

    // Signed up as me@example.com, so the card shows "Counted by me".
    expect(find.textContaining('Counted by me'), findsOneWidget);
  });

  testWidgets('every change lands in the History tab', (WidgetTester tester) async {
    await createAccount(tester);

    await tester.ensureVisible(find.byKey(const Key('inc-butter')));
    await tester.tap(find.byKey(const Key('inc-butter')));
    await tester.pump();
    await tester.tap(find.text('History'));
    await tester.pumpAndSettle();

    expect(find.text('Butter: count 2 → 3'), findsOneWidget);
    expect(find.textContaining('me · today'), findsOneWidget);
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

  testWidgets('a new item can be added from the sheet', (WidgetTester tester) async {
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

  testWidgets('an exact count can be set from the edit sheet', (WidgetTester tester) async {
    await createAccount(tester);

    await tester.tap(find.text('Tomatoes'));
    await tester.pumpAndSettle();
    expect(find.text('Edit item'), findsOneWidget);
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
    await signOut(tester);

    await tester.enterText(find.byKey(const Key('email-field')), 'me@example.com');
    await tester.enterText(find.byKey(const Key('password-field')), 'wrongpassword');
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();

    expect(find.text("That password doesn't match. Try again."), findsOneWidget);
  });

  testWidgets('signing out returns to the sign-in screen', (WidgetTester tester) async {
    await createAccount(tester);
    await signOut(tester);

    expect(find.text('Welcome back'), findsOneWidget);
  });
}
