# Kitchen Inventory

Back-of-house inventory tracking for a restaurant, with three roles:

| Role | What they can do |
| --- | --- |
| **Kitchen** | See the inventory, adjust counts with big +/− buttons, set exact counts |
| **Manager** | Everything above, plus add/edit/delete items, set "should have" amounts, see the Overview |
| **Owner** | Same as Manager |

Every item has a **"should have" amount** — how much you want on hand.
Anything under that gets a red "Low" badge in the list, and the **Overview**
tab turns those into a ready-made shopping list showing exactly how much to
order.

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
(Kitchen / Manager / Owner) when creating an account. Accounts are stored on
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
  category, unit, count, and the "should have" amount).
- `lib/inventory/inventory_store.dart` — saving/loading the inventory, plus
  the starter items seeded on first launch.
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
