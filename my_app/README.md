# Kitchen Inventory

Back-of-house inventory tracking for a restaurant. Only four accounts can
exist — **one owner and up to three managers** — and nobody else can sign
up: once the owner spot or all three manager spots are taken, new sign-ups
are politely refused. Everyone with an account has full access: counting
stock, adding/editing/removing items, the Overview, and the History.

Every item has a **"should have" amount** — how much you want on hand.
Anything under that gets a red "Low" badge in the list, and the **Overview**
tab turns those into a ready-made shopping list showing exactly how much to
order.

Every item also shows **who counted it last and when** ("Counted by sam ·
today 2:15 PM"), and the **History** tab — visible to everyone — keeps a
running log of every change: counts, added items, edits, and removals, each
stamped with who did it. The log keeps the most recent 200 changes.

The whole app follows two design rules:

- **Readability** — body text is 16–17px with relaxed line spacing, colors meet
  accessibility contrast guidelines, and light/dark mode both work out of the box.
- **Easy tapping** — every control is at least 48×48 pixels (the accessibility
  minimum), the +/− count buttons are sized for fast flash counts with wet or
  gloved hands in mind, and primary actions sit bottom-center in the thumb zone.

## How to run it

From this folder, with Flutter installed:

```sh
flutter pub get
flutter run
```

To run the tests:

```sh
flutter test
```

(If you're using the Flutter SDK checkout this folder lives inside, use
`../bin/flutter` instead of `flutter`.)

## Login & accounts

The app opens with a sign-in / create-account screen; you pick your role
(Manager / Owner) when creating an account, and the app enforces the limit
of one owner and three managers. Accounts are stored on
the device itself: passwords are never saved — each account keeps a random
salt plus a SHA-256 hash, and signing in re-hashes what you typed and
compares. Sessions survive app restarts; sign out from the top-right button.

Because accounts and inventory live on the device, they don't sync between
phones — two phones each have their own copy. When you're ready for a shared,
multi-device inventory, the swap points are `lib/auth/auth_service.dart`
(→ Firebase Auth, with roles assigned by the owner instead of self-picked at
sign-up) and `lib/inventory/inventory_store.dart` (→ Cloud Firestore). The
rest of the app only talks to those two files.

## Where things live

- `lib/theme.dart` — the design system: colors, text sizes, minimum button
  sizes. Change the `seedColor` to instantly re-color the app.
- `lib/models/inventory_item.dart` — what an inventory item is (name,
  category, unit, count, the "should have" amount, and who counted it last).
- `lib/models/history_entry.dart` — one line of the change log.
- `lib/inventory/inventory_store.dart` — saving/loading the inventory and
  history, plus the starter items seeded on first launch.
- `lib/screens/inventory_home_screen.dart` — the inventory list, the
  Overview/shopping list, and the add/edit sheet.
- `lib/screens/login_screen.dart` — sign-in / create-account with the role
  picker.
- `lib/auth/auth_service.dart` — accounts, password hashing, sessions.

## Do you need another AI or an app builder?

Short answer: no. Claude Code (which built this) can design, write, test, and
restyle the entire app from plain-English requests, and the code is fully
yours. App builders like FlutterFlow are worth it only if you strongly prefer
drag-and-drop over describing changes in words.
