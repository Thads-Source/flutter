# My App

A starter Flutter app built around two goals:

- **Readability** — body text is 16–17px with relaxed line spacing, colors meet
  accessibility contrast guidelines, and light/dark mode both work out of the box.
- **Easy tapping** — every button and card is at least 48×48 pixels (the
  accessibility minimum), whole cards are tappable so you don't have to aim for
  a tiny checkbox, and the main action button sits at the bottom center of the
  screen where a thumb naturally rests.

## How to run it

From this folder, with Flutter installed:

```sh
flutter run
```

(If you're using the Flutter SDK checkout this folder lives inside, use
`../bin/flutter run` instead.)

To run the tests:

```sh
flutter test
```

## Where the design decisions live

- `lib/theme.dart` — the whole design system: colors, text sizes, minimum
  button sizes. Change the `seedColor` there to instantly re-color the app.
- `lib/screens/home_screen.dart` — the home screen, showing the patterns in
  practice (big tap targets, bottom-anchored primary action, clear hierarchy).

## Do you need another AI or an app builder?

Short answer: no.

- **Claude Code** (what built this) can design, write, test, and restyle the
  entire app from plain-English requests, and the code is fully yours.
- **App builders** like FlutterFlow are worth it only if you strongly prefer
  drag-and-drop over describing changes in words. They're quicker for the first
  hour and slower for everything after, and most charge a subscription.
- Whatever you use, the things that make an app feel good are the same:
  48px+ tap targets, primary buttons in the thumb zone, 16px+ text with real
  contrast, and instant visual feedback when you tap. This app is a working
  reference for all of them.
